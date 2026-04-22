"""
VigilAI Firecrawl爬虫基类
使用Firecrawl API进行网页抓取，自动处理反爬虫

功能:
- 自动绕过Cloudflare等反爬虫
- 返回干净的Markdown内容
- 支持异步操作
- 自动处理JS渲染
- 重试机制和错误处理
- 速率限制控制
- 多API Key轮换（平均分配请求）
"""

import asyncio
import hashlib
import logging
import random
import re
import os
import time
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from datetime import datetime

from bs4 import BeautifulSoup

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import Activity, Category
from config import USER_AGENTS, MAX_RETRIES
from utils.error_handler import ErrorHandler
from utils.api_key_pool import ApiKeyPool
from utils.content_cleaning import build_description_from_text, clean_detail_content, looks_like_noisy_scraped_text

logger = logging.getLogger(__name__)

# 尝试导入Firecrawl
try:
    from firecrawl import FirecrawlApp
    FIRECRAWL_AVAILABLE = True
except ImportError:
    FIRECRAWL_AVAILABLE = False
    logger.warning("Firecrawl not installed. Run: pip install firecrawl-py")


class FirecrawlScraper(ABC):
    """
    基于Firecrawl的爬虫基类
    
    优势:
    - 自动处理JS渲染
    - 内置反爬虫绕过
    - 返回干净的Markdown/HTML
    - 重试机制
    - 速率限制
    - 多API Key轮换
    """
    
    DEFAULT_MIN_DELAY = 1.0
    DEFAULT_MAX_DELAY = 3.0
    
    def __init__(self, source_id: str, source_config: dict):
        self.source_id = source_id
        self.config = source_config
        self.source_name = source_config.get('name', source_id)
        self.source_url = source_config.get('url', '')
        self.category = source_config.get('category', 'event')
        
        self.max_retries = source_config.get('max_retries', MAX_RETRIES)
        self.retry_count = 0
        self.last_error: Optional[Exception] = None
        
        delay_config = source_config.get(
            'request_delay', 
            (self.DEFAULT_MIN_DELAY, self.DEFAULT_MAX_DELAY)
        )
        if isinstance(delay_config, (int, float)):
            self.request_delay = (delay_config, delay_config)
        else:
            self.request_delay = tuple(delay_config)
        
        self.user_agents = USER_AGENTS.copy()
        
        # 使用API Key池
        self._api_key_pool = ApiKeyPool.get_instance()
        self._current_api_key: Optional[str] = None
        
        self.request_count = 0
        self.success_count = 0
        self.error_count = 0
        self.start_time: Optional[float] = None
        self.last_request_time: Optional[float] = None
    
    def _get_firecrawl_client(self) -> Optional['FirecrawlApp']:
        """获取Firecrawl客户端，使用轮换的API Key"""
        if not FIRECRAWL_AVAILABLE:
            return None
        
        if not self._api_key_pool.has_keys:
            return None
        
        # 获取下一个API Key
        self._current_api_key = self._api_key_pool.get_next_key()
        if not self._current_api_key:
            return None
        
        try:
            return FirecrawlApp(api_key=self._current_api_key)
        except Exception as e:
            logger.error(f"Failed to create Firecrawl client: {e}")
            return None
    
    @property
    def firecrawl_enabled(self) -> bool:
        return FIRECRAWL_AVAILABLE and self._api_key_pool.has_keys
    
    def get_random_user_agent(self) -> str:
        return random.choice(self.user_agents) if self.user_agents else ""
    
    async def add_random_delay(self) -> float:
        min_delay, max_delay = self.request_delay
        delay = random.uniform(min_delay, max_delay)
        await asyncio.sleep(delay)
        return delay
    
    def generate_activity_id(self, url: str) -> str:
        return hashlib.md5(f"{self.source_id}:{url}".encode()).hexdigest()
    
    def get_category(self) -> Category:
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
        self.last_error = error
        self.error_count += 1
        self.retry_count += 1
        
        ErrorHandler.log_error(self.source_name, error, context)
        
        if self.retry_count >= self.max_retries:
            logger.error(
                f"Max retries ({self.max_retries}) reached for {self.source_name}"
            )
            return False
        
        return ErrorHandler.is_retryable(error)
    
    def reset_retry_count(self):
        self.retry_count = 0

    async def scrape_url(
        self, 
        url: str, 
        formats: List[str] = None,
        retries: int = None
    ) -> Optional[Dict[str, Any]]:
        """
        使用Firecrawl抓取单个URL（自动轮换API Key）
        
        Args:
            url: 要抓取的URL
            formats: 返回格式，如 ["markdown", "html"]
            retries: 重试次数
            
        Returns:
            包含markdown/html内容的字典，失败返回None
        """
        if not self.firecrawl_enabled:
            logger.warning(f"Firecrawl not available, skipping {url}")
            return None
        
        formats = formats or ["markdown", "html"]
        retries = retries if retries is not None else self.max_retries
        
        for attempt in range(retries):
            try:
                if self.last_request_time is not None:
                    await self.add_random_delay()
                
                self.request_count += 1
                self.last_request_time = time.time()
                
                # 获取轮换的Firecrawl客户端
                firecrawl_client = self._get_firecrawl_client()
                if not firecrawl_client:
                    logger.error("Failed to get Firecrawl client")
                    return None
                
                loop = asyncio.get_event_loop()
                
                result = await loop.run_in_executor(
                    None,
                    lambda: firecrawl_client.scrape(url, formats=formats)
                )
                
                self.success_count += 1
                self.reset_retry_count()
                
                # 报告API Key使用成功
                if self._current_api_key:
                    self._api_key_pool.report_success(self._current_api_key)
                
                logger.info(f"Successfully scraped {url}")
                
                if isinstance(result, dict):
                    return {
                        'markdown': result.get('markdown', '') or '',
                        'html': result.get('html', '') or '',
                        'metadata': result.get('metadata'),
                        'links': result.get('links', []) or [],
                    }
                else:
                    return {
                        'markdown': getattr(result, 'markdown', '') or '',
                        'html': getattr(result, 'html', '') or '',
                        'metadata': getattr(result, 'metadata', None),
                        'links': getattr(result, 'links', []) or [],
                    }
                
            except Exception as e:
                # 报告API Key使用失败
                if self._current_api_key:
                    self._api_key_pool.report_error(self._current_api_key, str(e))
                
                should_retry = self.handle_error(
                    e, f"scrape_url attempt {attempt + 1}"
                )
                
                if not should_retry or attempt >= retries - 1:
                    logger.error(
                        f"Failed to scrape {url} after {attempt + 1} attempts: {e}"
                    )
                    return None
                
                wait_time = ErrorHandler.get_retry_delay(e, attempt)
                logger.info(f"Waiting {wait_time:.1f}s before retry...")
                await asyncio.sleep(wait_time)
        
        return None
    
    async def scrape_multiple(
        self, 
        urls: List[str],
        formats: List[str] = None
    ) -> List[Dict[str, Any]]:
        """批量抓取多个URL"""
        results = []
        for url in urls:
            result = await self.scrape_url(url, formats)
            if result:
                results.append(result)
        return results
    
    def parse_markdown(self, markdown: str) -> BeautifulSoup:
        """将Markdown转换为可解析的HTML"""
        if not markdown:
            return BeautifulSoup('', 'html.parser')
        
        html = markdown
        
        # 转换链接
        html = re.sub(
            r'\[([^\]]+)\]\(([^)]+)\)', 
            r'<a href="\2">\1</a>', 
            html
        )
        
        # 转换标题
        html = re.sub(r'^### (.+)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
        html = re.sub(r'^## (.+)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
        html = re.sub(r'^# (.+)$', r'<h1>\1</h1>', html, flags=re.MULTILINE)
        
        # 转换粗体和斜体
        html = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', html)
        html = re.sub(r'\*([^*]+)\*', r'<em>\1</em>', html)
        
        # 转换列表项
        html = re.sub(r'^[-*] (.+)$', r'<li>\1</li>', html, flags=re.MULTILINE)
        
        return BeautifulSoup(html, 'html.parser')
    
    def extract_links(self, content: str, base_url: str = "") -> List[Dict[str, str]]:
        """从内容中提取所有链接"""
        links = []
        if not content:
            return links
        
        md_links = re.findall(r'\[([^\]]+)\]\(([^)]+)\)', content)
        for text, url in md_links:
            if url and not url.startswith('http'):
                if base_url:
                    url = base_url.rstrip('/') + '/' + url.lstrip('/')
                else:
                    continue
            links.append({"text": text.strip(), "url": url})
        
        return links

    def create_activity(
        self,
        url: str,
        title: str,
        description: str = None,
        full_content: str = None,
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
        status: str = "upcoming",
        category: str = None
    ) -> Activity:
        """创建Activity对象"""
        from models import Prize, ActivityDates
        
        activity_id = self.generate_activity_id(url)
        now = datetime.now()
        
        prize = None
        if prize_amount is not None or prize_description:
            prize = Prize(
                amount=prize_amount,
                currency=prize_currency,
                description=prize_description
            )
        
        dates = None
        if start_date or end_date or deadline:
            dates = ActivityDates(
                start_date=start_date,
                end_date=end_date,
                deadline=deadline
            )
        
        # 如果提供了category参数,使用它;否则使用默认的
        if category:
            activity_category = self._get_category_from_string(category)
        else:
            activity_category = self.get_category()
        
        return Activity(
            id=activity_id,
            title=title,
            description=description,
            full_content=full_content,
            source_id=self.source_id,
            source_name=self.source_name,
            url=url,
            category=activity_category,
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
    
    def _get_category_from_string(self, category_str: str) -> Category:
        """将字符串转换为Category枚举"""
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
        return category_map.get(category_str, Category.DEV_EVENT)
    
    @abstractmethod
    async def scrape(self) -> List[Activity]:
        """执行爬取，子类必须实现"""
        raise NotImplementedError("Subclasses must implement scrape()")
    
    async def fetch_detail_content(self, url: str) -> Optional[str]:
        """
        抓取活动详情页的完整内容
        
        Args:
            url: 活动详情页URL
            
        Returns:
            清理后的Markdown内容，失败返回None
        """
        result = await self.scrape_url(url, formats=["markdown"])
        if not result:
            return None
        
        markdown = result.get('markdown', '')
        if not markdown:
            return None
        
        # 清理内容
        cleaned = self._clean_detail_content(markdown)
        return cleaned if cleaned else None
    
    def _clean_detail_content(self, content: str) -> str:
        """
        清理详情页内容，移除导航、页脚等无关内容
        
        Args:
            content: 原始Markdown内容
            
        Returns:
            清理后的内容
        """
        if not content:
            return ""
        
        # 移除常见的导航和页脚模式
        lines = content.split('\n')
        cleaned_lines = []
        skip_section = False
        
        for line in lines:
            line_lower = line.lower().strip()
            
            # 跳过导航区域
            if any(nav in line_lower for nav in ['navigation', 'navbar', 'menu', 'footer', 'copyright']):
                skip_section = True
                continue
            
            # 跳过社交媒体链接区域
            if any(social in line_lower for social in ['follow us', 'share this', 'social media']):
                skip_section = True
                continue
            
            # 遇到主要内容标题时恢复
            if line.startswith('#') and len(line) > 2:
                skip_section = False
            
            if not skip_section:
                cleaned_lines.append(line)
        
        cleaned = '\n'.join(cleaned_lines)
        
        # 移除过多的空行
        cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
        
        # 限制内容长度（最多10000字符）
        if len(cleaned) > 10000:
            cleaned = cleaned[:10000] + "\n\n...(内容已截断)"
        
        return cleaned.strip()

    # Override the legacy implementation above with the shared cleaner so
    # firecrawl detail pages and stored rows use the same normalization rules.
    def _clean_detail_content(self, content: str) -> str:
        return clean_detail_content(content)
    
    async def enrich_activities_with_details(
        self, 
        activities: List[Activity],
        max_count: int = 10,
        delay_between: float = 2.0
    ) -> List[Activity]:
        """
        为活动列表补充详细内容
        
        Args:
            activities: 活动列表
            max_count: 最多抓取多少个详情页（控制API调用成本）
            delay_between: 每次请求之间的延迟（秒）
            
        Returns:
            补充了详细内容的活动列表
        """
        enriched = []
        count = 0
        
        for activity in activities:
            if count < max_count and activity.url:
                logger.info(f"Fetching detail for: {activity.title}")
                
                try:
                    detail_content = await self.fetch_detail_content(activity.url)
                    if detail_content:
                        # 创建新的activity对象，包含详细内容
                        activity_dict = activity.model_dump()
                        activity_dict['full_content'] = detail_content
                        enriched_activity = Activity(**activity_dict)
                        enriched.append(enriched_activity)
                        count += 1
                        
                        # 添加延迟
                        if count < max_count:
                            await asyncio.sleep(delay_between)
                    else:
                        enriched.append(activity)
                except Exception as e:
                    logger.error(f"Failed to fetch detail for {activity.title}: {e}")
                    enriched.append(activity)
            else:
                enriched.append(activity)
        
        logger.info(f"Enriched {count} activities with detail content")
        return enriched

    async def enrich_activities_with_details(
        self,
        activities: List[Activity],
        max_count: int = 10,
        delay_between: float = 2.0
    ) -> List[Activity]:
        enriched = []
        count = 0

        for activity in activities:
            if count < max_count and activity.url:
                logger.info(f"Fetching detail for: {activity.title}")

                try:
                    detail_content = await self.fetch_detail_content(activity.url)
                    if detail_content:
                        activity_dict = activity.model_dump()
                        activity_dict['full_content'] = detail_content
                        if not activity.description or looks_like_noisy_scraped_text(activity.description):
                            detail_excerpt = build_description_from_text(
                                detail_content,
                                title=activity.title,
                                max_length=500,
                            )
                            if detail_excerpt:
                                activity_dict['description'] = detail_excerpt
                        enriched.append(Activity(**activity_dict))
                        count += 1

                        if count < max_count:
                            await asyncio.sleep(delay_between)
                    else:
                        enriched.append(activity)
                except Exception as e:
                    logger.error(f"Failed to fetch detail for {activity.title}: {e}")
                    enriched.append(activity)
            else:
                enriched.append(activity)

        logger.info(f"Enriched {count} activities with detail content")
        return enriched
    
    async def run(self) -> List[Activity]:
        """运行爬虫"""
        self.start_time = time.time()
        self.request_count = 0
        self.success_count = 0
        self.error_count = 0
        self.retry_count = 0
        
        try:
            logger.info(f"Starting Firecrawl scraper for {self.source_name}")
            activities = await self.scrape()
            
            elapsed_time = time.time() - self.start_time
            logger.info(
                f"Scraped {len(activities)} activities from {self.source_name} "
                f"in {elapsed_time:.2f}s (requests: {self.request_count}, "
                f"success: {self.success_count}, errors: {self.error_count})"
            )
            return activities
        except Exception as e:
            logger.error(f"Scraper {self.source_name} failed: {e}")
            return []
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        elapsed = time.time() - self.start_time if self.start_time else 0
        return {
            'source_name': self.source_name,
            'source_id': self.source_id,
            'request_count': self.request_count,
            'success_count': self.success_count,
            'error_count': self.error_count,
            'elapsed_time': elapsed,
            'retry_count': self.retry_count,
            'firecrawl_enabled': self.firecrawl_enabled,
        }
