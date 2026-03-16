"""
VigilAI RSS爬虫
解析RSS/Atom订阅源获取活动信息
"""

import logging
import re
from typing import List, Optional
from datetime import datetime
from dateutil import parser as date_parser
import feedparser

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scrapers.base import BaseScraper
from models import Activity

logger = logging.getLogger(__name__)


class RssScraper(BaseScraper):
    """RSS订阅源爬虫"""
    
    def get_headers(self) -> dict:
        """获取RSS请求头，包含正确的Accept类型"""
        return {
            'User-Agent': self.get_random_user_agent(),
            'Accept': 'application/rss+xml, application/xml, text/xml, application/atom+xml, */*',
            'Accept-Language': 'en-US,en;q=0.5,zh-CN;q=0.3',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        }
    
    async def scrape(self) -> List[Activity]:
        """
        解析RSS feed并返回活动列表
        """
        try:
            # 获取RSS内容
            content = await self.fetch_url(self.source_url, delay=0)
            if not content:
                logger.warning(f"Failed to fetch RSS feed from {self.source_url}")
                return []
            
            # 解析RSS
            return self.parse_feed(content)
            
        except Exception as e:
            logger.error(f"Error scraping RSS feed {self.source_url}: {e}")
            return []
    
    def parse_feed(self, content: str) -> List[Activity]:
        """
        解析RSS/Atom feed内容
        
        Args:
            content: RSS feed的XML内容
            
        Returns:
            活动列表，解析失败返回空列表
        """
        try:
            feed = feedparser.parse(content)
            
            # 检查解析是否成功
            if feed.bozo and not feed.entries:
                logger.warning(f"Malformed RSS feed: {feed.bozo_exception}")
                return []
            
            activities = []
            for entry in feed.entries:
                try:
                    activity = self._parse_entry(entry)
                    if activity:
                        activities.append(activity)
                except Exception as e:
                    logger.warning(f"Error parsing RSS entry: {e}")
                    continue
            
            return activities
            
        except Exception as e:
            logger.error(f"Error parsing RSS feed: {e}")
            return []
    
    def _parse_entry(self, entry) -> Optional[Activity]:
        """
        将RSS entry转换为Activity
        
        Args:
            entry: feedparser解析的entry对象
            
        Returns:
            Activity对象，解析失败返回None
        """
        # 提取必需字段
        title = getattr(entry, 'title', None)
        link = getattr(entry, 'link', None)
        
        if not title or not link:
            return None
        
        # 提取描述
        description = None
        if hasattr(entry, 'summary'):
            description = self._clean_html(entry.summary)
        elif hasattr(entry, 'description'):
            description = self._clean_html(entry.description)
        
        # 提取图片URL
        image_url = self._extract_image(entry)
        
        # 提取发布日期
        published_date = None
        if hasattr(entry, 'published_parsed') and entry.published_parsed:
            published_date = datetime(*entry.published_parsed[:6])
        elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
            published_date = datetime(*entry.updated_parsed[:6])
        
        # 提取标签
        tags = []
        if hasattr(entry, 'tags'):
            tags = [tag.term for tag in entry.tags if hasattr(tag, 'term')]
        
        # 尝试从内容中提取奖金信息
        prize_amount, prize_currency = self._extract_prize(
            f"{title} {description or ''}"
        )
        
        # 尝试提取截止日期
        deadline = self._extract_deadline(f"{title} {description or ''}")
        
        return self.create_activity(
            url=link,
            title=title,
            description=description,
            tags=tags,
            prize_amount=prize_amount,
            prize_currency=prize_currency,
            deadline=deadline,
            start_date=published_date,
            image_url=image_url
        )
    
    def _extract_image(self, entry) -> Optional[str]:
        """
        从RSS entry中提取图片URL
        
        Args:
            entry: feedparser解析的entry对象
            
        Returns:
            图片URL或None
        """
        # 1. 检查media:content或media:thumbnail
        if hasattr(entry, 'media_content') and entry.media_content:
            for media in entry.media_content:
                if media.get('medium') == 'image' or media.get('type', '').startswith('image/'):
                    return media.get('url')
        
        if hasattr(entry, 'media_thumbnail') and entry.media_thumbnail:
            for thumb in entry.media_thumbnail:
                if thumb.get('url'):
                    return thumb.get('url')
        
        # 2. 检查enclosure
        if hasattr(entry, 'enclosures') and entry.enclosures:
            for enc in entry.enclosures:
                if enc.get('type', '').startswith('image/'):
                    return enc.get('href') or enc.get('url')
        
        # 3. 从content或summary中提取img标签
        content_html = None
        if hasattr(entry, 'content') and entry.content:
            content_html = entry.content[0].get('value', '')
        elif hasattr(entry, 'summary'):
            content_html = entry.summary
        
        if content_html:
            img_match = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', content_html, re.IGNORECASE)
            if img_match:
                return img_match.group(1)
        
        return None
    
    def _clean_html(self, html: str) -> str:
        """清理HTML标签"""
        if not html:
            return ""
        # 移除HTML标签
        clean = re.sub(r'<[^>]+>', '', html)
        # 清理多余空白
        clean = re.sub(r'\s+', ' ', clean).strip()
        return clean[:1000]  # 限制长度
    
    def _extract_prize(self, text: str) -> tuple:
        """
        从文本中提取奖金信息
        
        Returns:
            (amount, currency) 元组
        """
        if not text:
            return None, "USD"
        
        # 匹配美元金额
        usd_patterns = [
            r'\$\s*([\d,]+(?:\.\d{2})?)\s*(?:USD|usd)?',
            r'([\d,]+(?:\.\d{2})?)\s*(?:USD|usd|dollars?)',
        ]
        
        for pattern in usd_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                amount_str = match.group(1).replace(',', '')
                try:
                    return float(amount_str), "USD"
                except ValueError:
                    continue
        
        # 匹配人民币金额
        cny_patterns = [
            r'¥\s*([\d,]+(?:\.\d{2})?)',
            r'([\d,]+(?:\.\d{2})?)\s*(?:元|人民币|CNY|RMB)',
        ]
        
        for pattern in cny_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                amount_str = match.group(1).replace(',', '')
                try:
                    return float(amount_str), "CNY"
                except ValueError:
                    continue
        
        return None, "USD"
    
    def _extract_deadline(self, text: str) -> Optional[datetime]:
        """
        从文本中提取截止日期
        """
        if not text:
            return None
        
        # 常见的截止日期模式
        patterns = [
            r'deadline[:\s]+([A-Za-z]+\s+\d{1,2},?\s+\d{4})',
            r'due[:\s]+([A-Za-z]+\s+\d{1,2},?\s+\d{4})',
            r'ends?[:\s]+([A-Za-z]+\s+\d{1,2},?\s+\d{4})',
            r'截止[：:\s]*(\d{4}[-/年]\d{1,2}[-/月]\d{1,2})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    return date_parser.parse(match.group(1))
                except (ValueError, TypeError):
                    continue
        
        return None
    
    @staticmethod
    def parse_date(date_str: str) -> Optional[datetime]:
        """
        将各种日期格式转换为datetime
        支持多种格式，输出ISO 8601格式
        
        Args:
            date_str: 日期字符串
            
        Returns:
            datetime对象，解析失败返回None
        """
        if not date_str:
            return None
        
        try:
            # 使用dateutil的智能解析
            return date_parser.parse(date_str)
        except (ValueError, TypeError, OverflowError) as e:
            logger.debug(f"Failed to parse date '{date_str}': {e}")
            return None
