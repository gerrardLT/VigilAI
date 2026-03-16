"""
VigilAI 爬虫基类
提供通用的爬虫功能和接口定义

增强功能:
- 反爬虫策略支持（代理池、User-Agent轮换）
- 随机延迟方法
- 增强错误处理和重试机制
- 数据标准化方法

Validates: Requirements 10.1, 10.2, 10.3, 10.5, 11.3, 12.1, 12.4
"""

import asyncio
import hashlib
import logging
import random
import re
import time
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime

import httpx
from dateutil import parser as date_parser

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import Activity, Category
from config import (
    USER_AGENTS, REQUEST_TIMEOUT, REQUEST_DELAY, MAX_RETRIES
)
from utils.proxy_pool import ProxyPool
from utils.user_agent_rotator import UserAgentRotator
from utils.error_handler import ErrorHandler, ErrorType

logger = logging.getLogger(__name__)


class BaseScraper(ABC):
    """
    爬虫基类，定义通用接口和功能
    
    增强功能:
    - 反爬虫策略支持（代理池、User-Agent轮换）
    - 随机延迟方法
    - 增强错误处理和重试机制
    - 数据标准化方法
    """
    
    def __init__(self, source_id: str, source_config: dict):
        self.source_id = source_id
        self.config = source_config
        self.source_name = source_config.get('name', source_id)
        self.source_url = source_config.get('url', '')
        self.source_type = source_config.get('type', 'web')
        self.category = source_config.get('category', 'event')
        self._client: Optional[httpx.AsyncClient] = None
        
        # 反爬虫策略组件
        self.proxy_pool: Optional[ProxyPool] = None
        if source_config.get('use_proxy', False):
            proxy_list = source_config.get('proxy_list', [])
            self.proxy_pool = ProxyPool(proxy_list)
        
        self.user_agent_rotator = UserAgentRotator(USER_AGENTS.copy())
        
        # 请求延迟配置 (min, max) 秒
        delay_config = source_config.get('request_delay', (1.0, 3.0))
        if isinstance(delay_config, (int, float)):
            self.request_delay = (delay_config, delay_config)
        else:
            self.request_delay = tuple(delay_config)
        
        # 错误处理配置
        self.max_retries = source_config.get('max_retries', MAX_RETRIES)
        self.retry_count = 0
        self.last_error: Optional[Exception] = None
        self.error_count = 0
        
        # 请求统计
        self.request_count = 0
        self.success_count = 0
        self.start_time: Optional[float] = None
        
        logger.debug(f"Initialized scraper for {self.source_name}")
    
    @property
    def client(self) -> httpx.AsyncClient:
        """获取HTTP客户端（懒加载）"""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=REQUEST_TIMEOUT,
                follow_redirects=True
            )
        return self._client
    
    async def close(self):
        """关闭HTTP客户端"""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    def get_random_user_agent(self) -> str:
        """获取随机User-Agent"""
        return self.user_agent_rotator.get_random()
    
    def get_headers(self) -> dict:
        """获取请求头，包含随机User-Agent"""
        return {
            'User-Agent': self.get_random_user_agent(),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5,zh-CN;q=0.3',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        }
    
    def get_proxy(self) -> Optional[Dict[str, str]]:
        """获取代理配置"""
        if self.proxy_pool and self.proxy_pool.has_available():
            return self.proxy_pool.get_random_proxy()
        return None
    
    async def add_random_delay(self) -> float:
        """
        在请求之间添加随机延迟
        
        Returns:
            实际延迟时间（秒）
        """
        min_delay, max_delay = self.request_delay
        delay = random.uniform(min_delay, max_delay)
        await asyncio.sleep(delay)
        return delay
    
    def generate_activity_id(self, url: str) -> str:
        """基于source_id和url生成唯一活动ID"""
        return hashlib.md5(f"{self.source_id}:{url}".encode()).hexdigest()
    
    def get_category(self) -> Category:
        """获取活动类别"""
        category_map = {
            'hackathon': Category.HACKATHON,
            'data_competition': Category.DATA_COMPETITION,
            'coding_competition': Category.CODING_COMPETITION,
            'other_competition': Category.OTHER_COMPETITION,
            'airdrop': Category.AIRDROP,
            'bounty': Category.BOUNTY,
            'grant': Category.GRANT,
            'dev_event': Category.DEV_EVENT,
            'news': Category.NEWS,
        }
        return category_map.get(self.category, Category.DEV_EVENT)
    
    def handle_error(self, error: Exception, context: str = "") -> bool:
        """
        统一的错误处理
        
        Args:
            error: 异常对象
            context: 错误上下文
            
        Returns:
            是否应该重试
        """
        self.last_error = error
        self.error_count += 1
        self.retry_count += 1
        
        ErrorHandler.log_error(self.source_name, error, context)
        
        if self.retry_count >= self.max_retries:
            logger.error(f"Max retries ({self.max_retries}) reached for {self.source_name}")
            return False
        
        return ErrorHandler.is_retryable(error)
    
    def reset_retry_count(self):
        """重置重试计数"""
        self.retry_count = 0
    
    async def fetch_url(
        self, 
        url: str, 
        retries: int = None,
        delay: float = None,
        use_proxy: bool = True
    ) -> Optional[str]:
        """
        获取URL内容，带重试和指数退避
        
        Args:
            url: 要获取的URL
            retries: 重试次数，默认使用配置值
            delay: 请求前延迟，默认使用配置值
            use_proxy: 是否使用代理
            
        Returns:
            响应文本内容，失败返回None
        """
        retries = retries if retries is not None else self.max_retries
        
        # 请求前添加随机延迟
        if delay is None:
            await self.add_random_delay()
        elif delay > 0:
            await asyncio.sleep(delay)
        
        current_proxy = None
        
        for attempt in range(retries):
            try:
                self.request_count += 1
                
                # 获取代理
                proxy_config = None
                if use_proxy and self.proxy_pool:
                    proxy_dict = self.get_proxy()
                    if proxy_dict:
                        current_proxy = proxy_dict.get('http')
                        proxy_config = current_proxy
                
                response = await self.client.get(
                    url,
                    headers=self.get_headers(),
                    # httpx使用proxy参数
                )
                response.raise_for_status()
                
                self.success_count += 1
                
                # 标记代理成功
                if current_proxy and self.proxy_pool:
                    self.proxy_pool.mark_success(current_proxy)
                
                return response.text
                
            except httpx.HTTPStatusError as e:
                is_retryable = ErrorHandler.handle_network_error(e, self.source_name, url)
                
                # 标记代理失败
                if current_proxy and self.proxy_pool:
                    self.proxy_pool.mark_failed(current_proxy)
                
                if not is_retryable:
                    return None
                    
            except httpx.RequestError as e:
                ErrorHandler.handle_network_error(e, self.source_name, url)
                
                # 标记代理失败
                if current_proxy and self.proxy_pool:
                    self.proxy_pool.mark_failed(current_proxy)
                    
            except Exception as e:
                logger.error(
                    f"Unexpected error fetching {url}: {e}, "
                    f"attempt {attempt + 1}/{retries}"
                )
            
            # 指数退避
            if attempt < retries - 1:
                wait_time = ErrorHandler.get_retry_delay(
                    e if 'e' in dir() else Exception(), 
                    attempt
                )
                logger.info(f"Waiting {wait_time:.1f}s before retry...")
                await asyncio.sleep(wait_time)
        
        logger.error(f"Failed to fetch {url} after {retries} attempts")
        return None
    
    # ==================== 数据标准化方法 ====================
    
    def normalize_activity(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        标准化活动数据
        
        Args:
            raw_data: 原始数据字典
            
        Returns:
            标准化后的数据字典
        """
        return {
            'title': self._normalize_text(raw_data.get('title', '')),
            'source': self.source_name,
            'source_id': self.source_id,
            'url': raw_data.get('url', ''),
            'deadline': self._normalize_date(raw_data.get('deadline')),
            'description': self._normalize_text(raw_data.get('description', '')),
            'prize': self._normalize_prize(raw_data.get('prize')),
            'prize_currency': raw_data.get('prize_currency', 'USD'),
            'type': raw_data.get('type') or self._infer_type(),
            'tags': raw_data.get('tags', []),
            'start_date': self._normalize_date(raw_data.get('start_date')),
            'end_date': self._normalize_date(raw_data.get('end_date')),
            'location': raw_data.get('location'),
            'organizer': raw_data.get('organizer'),
            'created_at': datetime.utcnow().isoformat(),
        }
    
    def _normalize_text(self, text: Any) -> str:
        """标准化文本，去除多余空白"""
        if text is None:
            return ''
        return str(text).strip()
    
    def _normalize_date(self, date_value: Any) -> Optional[str]:
        """
        标准化日期格式为ISO 8601
        
        Args:
            date_value: 日期值（字符串、datetime或None）
            
        Returns:
            ISO 8601格式的日期字符串或None
        """
        if date_value is None:
            return None
        
        if isinstance(date_value, datetime):
            return date_value.isoformat()
        
        if isinstance(date_value, str):
            date_str = date_value.strip()
            if not date_str:
                return None
            
            try:
                # 使用dateutil解析各种日期格式
                parsed = date_parser.parse(date_str, fuzzy=True)
                return parsed.isoformat()
            except (ValueError, TypeError):
                pass
            
            # 尝试解析中文日期格式
            chinese_date = self._parse_chinese_date(date_str)
            if chinese_date:
                return chinese_date.isoformat()
        
        return None
    
    def _parse_chinese_date(self, date_str: str) -> Optional[datetime]:
        """解析中文日期格式"""
        patterns = [
            r'(\d{4})年(\d{1,2})月(\d{1,2})日',
            r'(\d{4})-(\d{1,2})-(\d{1,2})',
            r'(\d{4})/(\d{1,2})/(\d{1,2})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, date_str)
            if match:
                try:
                    year, month, day = map(int, match.groups())
                    return datetime(year, month, day)
                except (ValueError, TypeError):
                    continue
        
        return None
    
    def _normalize_prize(self, prize_data: Any) -> Optional[float]:
        """
        标准化奖金信息，提取数值
        
        Args:
            prize_data: 奖金数据（字符串、数字或None）
            
        Returns:
            奖金数值或None
        """
        if prize_data is None:
            return None
        
        if isinstance(prize_data, (int, float)):
            return float(prize_data)
        
        if isinstance(prize_data, str):
            # 移除货币符号和逗号
            cleaned = re.sub(r'[,$¥€£]', '', prize_data)
            cleaned = cleaned.replace(',', '').strip()
            
            # 提取数字
            match = re.search(r'[\d.]+', cleaned)
            if match:
                try:
                    value = float(match.group())
                    
                    # 处理单位（k, m, b）
                    lower_prize = prize_data.lower()
                    if 'k' in lower_prize or '千' in lower_prize:
                        value *= 1000
                    elif 'm' in lower_prize or '百万' in lower_prize:
                        value *= 1000000
                    elif 'b' in lower_prize or '十亿' in lower_prize:
                        value *= 1000000000
                    elif '万' in lower_prize:
                        value *= 10000
                    elif '亿' in lower_prize:
                        value *= 100000000
                    
                    return value
                except (ValueError, TypeError):
                    pass
        
        return None
    
    def extract_currency(self, text: str) -> str:
        """
        从文本中提取货币单位
        
        Args:
            text: 包含货币信息的文本
            
        Returns:
            货币代码（USD、CNY、ETH等）
        """
        if not text:
            return 'USD'
        
        text_lower = text.lower()
        
        # 货币符号和代码映射 - 注意顺序，更具体的模式放前面
        currency_patterns = [
            (r'\busdt\b|泰达币', 'USDT'),  # USDT必须在USD之前
            (r'\busdc\b', 'USDC'),
            (r'\$|(?<!\w)usd(?!\w)|美元|美金', 'USD'),
            (r'¥|cny|rmb|人民币|元', 'CNY'),
            (r'€|eur|欧元', 'EUR'),
            (r'£|gbp|英镑', 'GBP'),
            (r'\beth\b|以太', 'ETH'),
            (r'\bbtc\b|比特币', 'BTC'),
        ]
        
        for pattern, currency in currency_patterns:
            if re.search(pattern, text_lower):
                return currency
        
        return 'USD'
    
    def _infer_type(self) -> str:
        """
        根据信息源推断活动类型
        
        Returns:
            活动类型字符串
        """
        source_lower = self.source_name.lower()
        category_lower = self.category.lower()
        
        type_keywords = {
            'airdrop': ['airdrop', '空投', 'galxe', 'zealy'],
            'hackathon': ['hackathon', '黑客松', 'hack', 'devpost', 'mlh', 'ethglobal'],
            'data_competition': ['kaggle', 'tianchi', '天池', 'data', 'datafountain', 'datacastle'],
            'coding_competition': ['coding', 'programming', 'topcoder', 'hackerearth'],
            'other_competition': ['competition', '竞赛', '比赛', 'contest', 'challenge'],
            'bounty': ['bounty', '赏金', 'hackerone', 'bugcrowd', 'immunefi', 'code4rena'],
            'grant': ['grant', '资助', 'gitcoin', 'funding'],
            'dev_event': ['developer', '开发者', 'huawei', 'microsoft', 'google'],
            'news': ['news', '新闻', '36kr', 'huxiu', 'panews'],
        }
        
        for activity_type, keywords in type_keywords.items():
            for keyword in keywords:
                if keyword in source_lower or keyword in category_lower:
                    return activity_type
        
        return 'dev_event'
    
    def create_activity(
        self,
        url: str,
        title: str,
        description: str = None,
        tags: List[str] = None,
        prize_amount: float = None,
        prize_currency: str = "USD",
        prize_description: str = None,
        start_date: datetime = None,
        end_date: datetime = None,
        deadline: datetime = None,
        location: str = None,
        organizer: str = None,
        image_url: str = None,
        status: str = "upcoming"
    ) -> Activity:
        """
        创建Activity对象的便捷方法
        """
        from models import Prize, ActivityDates
        
        activity_id = self.generate_activity_id(url)
        now = datetime.now()
        
        # 构建Prize对象
        prize = None
        if prize_amount is not None or prize_description:
            prize = Prize(
                amount=prize_amount,
                currency=prize_currency,
                description=prize_description
            )
        
        # 构建ActivityDates对象
        dates = None
        if start_date or end_date or deadline:
            dates = ActivityDates(
                start_date=start_date,
                end_date=end_date,
                deadline=deadline
            )
        
        return Activity(
            id=activity_id,
            title=title,
            description=description,
            source_id=self.source_id,
            source_name=self.source_name,
            url=url,
            category=self.get_category(),
            tags=tags or [],
            prize=prize,
            dates=dates,
            location=location,
            organizer=organizer,
            image_url=image_url,
            status=status,
            created_at=now,
            updated_at=now
        )
    
    @abstractmethod
    async def scrape(self) -> List[Activity]:
        """
        执行爬取操作，子类必须实现
        
        Returns:
            活动列表
        """
        raise NotImplementedError("Subclasses must implement scrape()")
    
    async def run(self) -> List[Activity]:
        """
        运行爬虫的入口方法，包含错误处理和统计
        """
        self.start_time = time.time()
        self.request_count = 0
        self.success_count = 0
        self.error_count = 0
        
        try:
            logger.info(f"Starting scraper for {self.source_name} ({self.source_id})")
            activities = await self.scrape()
            
            elapsed_time = time.time() - self.start_time
            ErrorHandler.log_success(self.source_name, len(activities), elapsed_time)
            
            return activities
        except Exception as e:
            ErrorHandler.log_error(self.source_name, e, "run")
            return []
        finally:
            await self.close()
    
    def get_stats(self) -> Dict[str, Any]:
        """获取爬虫统计信息"""
        elapsed = time.time() - self.start_time if self.start_time else 0
        return {
            'source_name': self.source_name,
            'source_id': self.source_id,
            'request_count': self.request_count,
            'success_count': self.success_count,
            'error_count': self.error_count,
            'elapsed_time': elapsed,
            'retry_count': self.retry_count,
        }
