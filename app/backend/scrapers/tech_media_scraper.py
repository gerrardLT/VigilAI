"""
VigilAI 科技媒体爬虫
爬取36kr、虎嗅等科技媒体的活动信息
"""

import re
import logging
from typing import List, Optional
from datetime import datetime

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scrapers.rss_scraper import RssScraper
from models import Activity

logger = logging.getLogger(__name__)


# 活动相关关键词
ACTIVITY_KEYWORDS = [
    # 中文关键词
    '黑客松', '编程马拉松', '创业大赛', '创新大赛', '开发者大赛',
    '技术大赛', '算法大赛', '人工智能大赛', 'AI大赛',
    '创业比赛', '路演', '孵化器', '加速器',
    '空投', 'airdrop', '赏金', 'bounty',
    '补贴', '扶持', '资助', 'grant',
    # 英文关键词
    'hackathon', 'competition', 'contest', 'challenge',
    'startup', 'accelerator', 'incubator',
]


class TechMediaScraper(RssScraper):
    """科技媒体爬虫，继承RSS爬虫并添加关键词过滤"""
    
    def __init__(self, source_id: str, source_config: dict):
        super().__init__(source_id, source_config)
        self.keywords = source_config.get('keywords', ACTIVITY_KEYWORDS)
    
    async def scrape(self) -> List[Activity]:
        """
        爬取并过滤科技媒体内容
        只返回包含活动关键词的文章
        """
        # 调用父类方法获取所有RSS条目
        all_activities = await super().scrape()
        
        # 过滤包含关键词的活动
        filtered = []
        for activity in all_activities:
            if self._contains_keywords(activity):
                # 尝试从内容中提取更多信息
                self._enrich_activity(activity)
                filtered.append(activity)
        
        logger.info(
            f"Filtered {len(filtered)} activities from {len(all_activities)} "
            f"RSS entries for {self.source_name}"
        )
        return filtered
    
    def _contains_keywords(self, activity: Activity) -> bool:
        """检查活动是否包含关键词"""
        # 合并标题和描述进行搜索
        text = f"{activity.title} {activity.description or ''}".lower()
        
        for keyword in self.keywords:
            if keyword.lower() in text:
                return True
        
        return False
    
    def _enrich_activity(self, activity: Activity) -> None:
        """
        从活动内容中提取更多信息
        尝试提取日期、奖金等
        """
        text = f"{activity.title} {activity.description or ''}"
        
        # 尝试提取活动日期
        dates = self._extract_activity_dates(text)
        if dates and activity.dates is None:
            from models import ActivityDates
            activity.dates = ActivityDates(**dates)
        
        # 添加来源标签
        if self.source_id not in activity.tags:
            activity.tags.append(self.source_id)
    
    def _extract_activity_dates(self, text: str) -> Optional[dict]:
        """
        从文本中提取活动日期
        """
        if not text:
            return None
        
        from dateutil import parser as date_parser
        
        dates = {}
        
        # 中文日期模式
        patterns = [
            # 报名截止
            (r'报名[截止日期：:\s]*(\d{4}[-/年]\d{1,2}[-/月]\d{1,2})', 'deadline'),
            (r'截止[日期时间：:\s]*(\d{4}[-/年]\d{1,2}[-/月]\d{1,2})', 'deadline'),
            # 活动时间
            (r'活动时间[：:\s]*(\d{4}[-/年]\d{1,2}[-/月]\d{1,2})', 'start_date'),
            (r'开始时间[：:\s]*(\d{4}[-/年]\d{1,2}[-/月]\d{1,2})', 'start_date'),
            (r'结束时间[：:\s]*(\d{4}[-/年]\d{1,2}[-/月]\d{1,2})', 'end_date'),
            # 英文模式
            (r'deadline[:\s]+([A-Za-z]+\s+\d{1,2},?\s+\d{4})', 'deadline'),
            (r'starts?[:\s]+([A-Za-z]+\s+\d{1,2},?\s+\d{4})', 'start_date'),
            (r'ends?[:\s]+([A-Za-z]+\s+\d{1,2},?\s+\d{4})', 'end_date'),
        ]
        
        for pattern, date_type in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                date_str = match.group(1)
                # 处理中文日期格式
                date_str = date_str.replace('年', '-').replace('月', '-').replace('日', '')
                try:
                    parsed = date_parser.parse(date_str)
                    dates[date_type] = parsed
                except (ValueError, TypeError):
                    continue
        
        return dates if dates else None


class Kr36Scraper(TechMediaScraper):
    """36氪爬虫"""
    
    def __init__(self, source_id: str = "36kr", source_config: dict = None):
        if source_config is None:
            source_config = {
                'name': '36氪',
                'url': 'https://36kr.com/feed',
                'category': 'event'
            }
        super().__init__(source_id, source_config)


class HuxiuScraper(TechMediaScraper):
    """虎嗅爬虫"""
    
    def __init__(self, source_id: str = "huxiu", source_config: dict = None):
        if source_config is None:
            source_config = {
                'name': '虎嗅',
                'url': 'https://www.huxiu.com/rss/0.xml',
                'category': 'event'
            }
        super().__init__(source_id, source_config)
