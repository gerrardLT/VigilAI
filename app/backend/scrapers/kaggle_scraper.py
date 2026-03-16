"""
VigilAI Kaggle爬虫
使用Kaggle API获取竞赛信息
"""

import os
import logging
from typing import List, Optional
from datetime import datetime

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scrapers.base import BaseScraper
from models import Activity

logger = logging.getLogger(__name__)


class KaggleScraper(BaseScraper):
    """Kaggle竞赛爬虫"""
    
    def __init__(self, source_id: str, source_config: dict):
        super().__init__(source_id, source_config)
        self._api = None
        self._credentials_checked = False
        self._has_credentials = False
    
    def _check_credentials(self) -> bool:
        """
        检查Kaggle API凭证是否存在
        凭证文件位置：~/.kaggle/kaggle.json
        """
        if self._credentials_checked:
            return self._has_credentials
        
        self._credentials_checked = True
        
        # 检查环境变量
        if os.environ.get('KAGGLE_USERNAME') and os.environ.get('KAGGLE_KEY'):
            self._has_credentials = True
            return True
        
        # 检查凭证文件
        kaggle_json = os.path.expanduser('~/.kaggle/kaggle.json')
        if os.path.exists(kaggle_json):
            self._has_credentials = True
            return True
        
        # Windows路径
        kaggle_json_win = os.path.join(os.environ.get('USERPROFILE', ''), '.kaggle', 'kaggle.json')
        if os.path.exists(kaggle_json_win):
            self._has_credentials = True
            return True
        
        logger.warning(
            "Kaggle API credentials not found. "
            "Please set KAGGLE_USERNAME and KAGGLE_KEY environment variables, "
            "or create ~/.kaggle/kaggle.json"
        )
        self._has_credentials = False
        return False
    
    def _get_api(self):
        """获取Kaggle API实例"""
        if self._api is not None:
            return self._api
        
        try:
            from kaggle.api.kaggle_api_extended import KaggleApi
            self._api = KaggleApi()
            self._api.authenticate()
            return self._api
        except ImportError:
            logger.error("kaggle package not installed. Run: pip install kaggle")
            return None
        except Exception as e:
            logger.error(f"Failed to initialize Kaggle API: {e}")
            return None
    
    async def scrape(self) -> List[Activity]:
        """
        使用Kaggle API获取竞赛列表
        只返回active和upcoming状态的竞赛
        """
        if not self._check_credentials():
            logger.warning("Kaggle credentials not available, returning empty list")
            return []
        
        api = self._get_api()
        if not api:
            return []
        
        activities = []
        
        try:
            # 获取竞赛列表
            competitions = api.competitions_list()
            
            for comp in competitions:
                try:
                    # 过滤状态
                    if not self._is_active_or_upcoming(comp):
                        continue
                    
                    activity = self._parse_competition(comp)
                    if activity:
                        activities.append(activity)
                        
                except Exception as e:
                    logger.warning(f"Error parsing Kaggle competition: {e}")
                    continue
            
            logger.info(f"Scraped {len(activities)} Kaggle competitions")
            return activities
            
        except Exception as e:
            logger.error(f"Error fetching Kaggle competitions: {e}")
            return []
    
    def _is_active_or_upcoming(self, comp) -> bool:
        """检查竞赛是否为active或upcoming状态"""
        now = datetime.now()
        
        # 检查截止日期
        deadline = getattr(comp, 'deadline', None)
        if deadline:
            if isinstance(deadline, str):
                from dateutil import parser as date_parser
                try:
                    deadline = date_parser.parse(deadline)
                except (ValueError, TypeError):
                    pass
            
            if isinstance(deadline, datetime) and deadline < now:
                return False
        
        # 检查是否已启用提交
        enabled = getattr(comp, 'enabledDate', None)
        if enabled:
            if isinstance(enabled, str):
                from dateutil import parser as date_parser
                try:
                    enabled = date_parser.parse(enabled)
                except (ValueError, TypeError):
                    pass
        
        return True
    
    def _parse_competition(self, comp) -> Optional[Activity]:
        """将Kaggle竞赛转换为Activity"""
        # 提取基本信息
        title = getattr(comp, 'title', None)
        ref = getattr(comp, 'ref', None)
        
        if not title or not ref:
            return None
        
        url = f"https://www.kaggle.com/competitions/{ref}"
        description = getattr(comp, 'description', None)
        
        # 提取奖金
        reward = getattr(comp, 'reward', None)
        prize_amount, prize_currency = self._parse_reward(reward)
        
        # 提取日期
        deadline = getattr(comp, 'deadline', None)
        if deadline and isinstance(deadline, str):
            from dateutil import parser as date_parser
            try:
                deadline = date_parser.parse(deadline)
            except (ValueError, TypeError):
                deadline = None
        
        enabled_date = getattr(comp, 'enabledDate', None)
        if enabled_date and isinstance(enabled_date, str):
            from dateutil import parser as date_parser
            try:
                enabled_date = date_parser.parse(enabled_date)
            except (ValueError, TypeError):
                enabled_date = None
        
        # 提取标签
        tags = ['kaggle', 'competition', 'data-science']
        category = getattr(comp, 'category', None)
        if category:
            tags.append(category.lower())
        
        # 确定状态
        status = "upcoming"
        if enabled_date and isinstance(enabled_date, datetime):
            if enabled_date <= datetime.now():
                status = "active"
        
        return self.create_activity(
            url=url,
            title=title,
            description=description,
            prize_amount=prize_amount,
            prize_currency=prize_currency,
            start_date=enabled_date if isinstance(enabled_date, datetime) else None,
            deadline=deadline if isinstance(deadline, datetime) else None,
            tags=tags,
            organizer="Kaggle",
            status=status
        )
    
    def _parse_reward(self, reward: str) -> tuple:
        """解析奖金字符串"""
        if not reward:
            return None, "USD"
        
        import re
        
        # 匹配美元金额
        match = re.search(r'\$\s*([\d,]+)', reward)
        if match:
            try:
                amount = float(match.group(1).replace(',', ''))
                return amount, "USD"
            except ValueError:
                pass
        
        # 检查是否为知识/荣誉竞赛
        if 'knowledge' in reward.lower() or 'kudos' in reward.lower():
            return None, "USD"
        
        return None, "USD"
