"""
VigilAI 通用网页爬虫
提供网页抓取和HTML解析功能
"""

import asyncio
import logging
from typing import List, Optional
from bs4 import BeautifulSoup

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scrapers.base import BaseScraper
from models import Activity
from config import REQUEST_DELAY

logger = logging.getLogger(__name__)


class WebScraper(BaseScraper):
    """通用网页爬虫，提供HTML解析功能"""
    
    async def fetch_page(self, url: str, delay: float = None) -> Optional[str]:
        """
        获取网页内容，带请求延迟
        
        Args:
            url: 要获取的URL
            delay: 请求前延迟秒数
            
        Returns:
            网页HTML内容，失败返回None
        """
        delay = delay if delay is not None else REQUEST_DELAY
        return await self.fetch_url(url, delay=delay)
    
    def parse_html(self, html: str) -> Optional[BeautifulSoup]:
        """
        解析HTML内容
        
        Args:
            html: HTML字符串
            
        Returns:
            BeautifulSoup对象，解析失败返回None
        """
        if not html:
            return None
        try:
            return BeautifulSoup(html, 'html.parser')
        except Exception as e:
            logger.error(f"Error parsing HTML: {e}")
            return None
    
    def extract_text(self, element, default: str = "") -> str:
        """
        安全提取元素文本
        
        Args:
            element: BeautifulSoup元素
            default: 默认值
            
        Returns:
            元素文本或默认值
        """
        if element is None:
            return default
        return element.get_text(strip=True) or default
    
    def extract_attr(self, element, attr: str, default: str = "") -> str:
        """
        安全提取元素属性
        
        Args:
            element: BeautifulSoup元素
            attr: 属性名
            default: 默认值
            
        Returns:
            属性值或默认值
        """
        if element is None:
            return default
        return element.get(attr, default) or default
    
    async def scrape(self) -> List[Activity]:
        """
        执行网页爬取，子类应重写此方法实现具体逻辑
        
        Returns:
            活动列表
        """
        logger.warning(f"WebScraper.scrape() not implemented for {self.source_id}")
        return []
