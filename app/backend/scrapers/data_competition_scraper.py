"""
VigilAI 数据竞赛爬虫
支持天池、DataFountain、DataCastle、DrivenData等平台

Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5, 10.1, 10.2, 10.3
"""

import logging
import re
from typing import List, Optional
from datetime import datetime
from bs4 import BeautifulSoup

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scrapers.base import BaseScraper
from models import Activity

logger = logging.getLogger(__name__)


class DataCompetitionScraper(BaseScraper):
    """
    数据竞赛爬虫
    
    支持平台:
    - 天池 (Tianchi)
    - DataFountain
    - DataCastle
    - DrivenData
    
    功能:
    - 中文编码处理
    - 竞赛类型和难度提取
    - 奖金和截止日期解析
    """
    
    async def scrape(self) -> List[Activity]:
        """抓取数据竞赛信息"""
        try:
            html = await self.fetch_url(self.source_url)
            if not html:
                return []
            
            soup = BeautifulSoup(html, 'html.parser')
            activities = []
            
            if 'tianchi' in self.source_url or '天池' in self.source_name:
                activities = self._parse_tianchi(soup)
            elif 'datafountain' in self.source_url:
                activities = self._parse_datafountain(soup)
            elif 'datacastle' in self.source_url:
                activities = self._parse_datacastle(soup)
            elif 'drivendata' in self.source_url:
                activities = self._parse_drivendata(soup)
            else:
                logger.warning(f"No parser for URL: {self.source_url}")
            
            logger.info(f"Scraped {len(activities)} competitions from {self.source_name}")
            return activities
            
        except Exception as e:
            if self.handle_error(e, "scrape"):
                await self.add_random_delay()
                return await self.scrape()
            return []
    
    def _parse_tianchi(self, soup: BeautifulSoup) -> List[Activity]:
        """
        解析天池竞赛页面
        Validates: Requirements 2.1
        """
        activities = []
        
        # 尝试多种选择器
        competition_items = soup.select('.competition-item, .card, [class*="competition"]')
        
        if not competition_items:
            competition_items = soup.select('article, .item, .listing')
        
        for item in competition_items:
            try:
                # 提取标题
                title_elem = item.select_one('h2, h3, .title, [class*="title"]')
                title = title_elem.get_text(strip=True) if title_elem else None
                
                if not title:
                    continue
                
                # 提取URL
                link_elem = item.select_one('a[href]')
                url = link_elem.get('href', '') if link_elem else ''
                if url and not url.startswith('http'):
                    url = f"https://tianchi.aliyun.com{url}"
                
                # 提取奖金
                prize_elem = item.select_one('.prize, [class*="prize"], [class*="bonus"]')
                prize_text = prize_elem.get_text(strip=True) if prize_elem else ''
                
                # 提取截止日期
                deadline_elem = item.select_one('.deadline, .date, [class*="deadline"], [class*="time"]')
                deadline_text = deadline_elem.get_text(strip=True) if deadline_elem else ''
                
                # 提取描述
                desc_elem = item.select_one('.description, p, [class*="desc"]')
                description = desc_elem.get_text(strip=True) if desc_elem else ''
                
                # 提取参赛要求
                req_elem = item.select_one('[class*="requirement"], [class*="condition"]')
                requirement = req_elem.get_text(strip=True) if req_elem else ''
                
                activity = self.create_activity(
                    url=url or self.source_url,
                    title=title,
                    description=f"{description} {requirement}".strip(),
                    prize_amount=self._normalize_prize(prize_text),
                    prize_currency=self.extract_currency(prize_text) or 'CNY',
                    prize_description=prize_text,
                    deadline=self._parse_deadline(deadline_text),
                    tags=['data-science', 'tianchi', 'competition'],
                )
                activities.append(activity)
                
            except Exception as e:
                logger.warning(f"Failed to parse Tianchi competition: {e}")
                continue
        
        return activities
    
    def _parse_datafountain(self, soup: BeautifulSoup) -> List[Activity]:
        """
        解析DataFountain页面
        Validates: Requirements 2.2
        """
        activities = []
        
        competition_items = soup.select('.competition-card, .card, [class*="competition"]')
        
        for item in competition_items:
            try:
                title_elem = item.select_one('h2, h3, .title, [class*="title"]')
                title = title_elem.get_text(strip=True) if title_elem else None
                
                if not title:
                    continue
                
                link_elem = item.select_one('a[href]')
                url = link_elem.get('href', '') if link_elem else ''
                if url and not url.startswith('http'):
                    url = f"https://www.datafountain.cn{url}"
                
                prize_elem = item.select_one('.prize, [class*="prize"]')
                prize_text = prize_elem.get_text(strip=True) if prize_elem else ''
                
                deadline_elem = item.select_one('.deadline, [class*="time"]')
                deadline_text = deadline_elem.get_text(strip=True) if deadline_elem else ''
                
                desc_elem = item.select_one('.description, p')
                description = desc_elem.get_text(strip=True) if desc_elem else ''
                
                activity = self.create_activity(
                    url=url or self.source_url,
                    title=title,
                    description=description,
                    prize_amount=self._normalize_prize(prize_text),
                    prize_currency='CNY',
                    prize_description=prize_text,
                    deadline=self._parse_deadline(deadline_text),
                    tags=['data-science', 'datafountain', 'competition'],
                )
                activities.append(activity)
                
            except Exception as e:
                logger.warning(f"Failed to parse DataFountain competition: {e}")
                continue
        
        return activities
    
    def _parse_datacastle(self, soup: BeautifulSoup) -> List[Activity]:
        """
        解析DataCastle页面
        Validates: Requirements 2.3
        """
        activities = []
        
        competition_items = soup.select('.race-item, .card, [class*="race"]')
        
        for item in competition_items:
            try:
                title_elem = item.select_one('h2, h3, .title, [class*="title"]')
                title = title_elem.get_text(strip=True) if title_elem else None
                
                if not title:
                    continue
                
                link_elem = item.select_one('a[href]')
                url = link_elem.get('href', '') if link_elem else ''
                if url and not url.startswith('http'):
                    url = f"https://www.datacastle.cn{url}"
                
                # 提取竞赛类型
                type_elem = item.select_one('.type, [class*="type"], [class*="category"]')
                comp_type = type_elem.get_text(strip=True) if type_elem else ''
                
                # 提取难度等级
                difficulty_elem = item.select_one('.difficulty, [class*="level"]')
                difficulty = difficulty_elem.get_text(strip=True) if difficulty_elem else ''
                
                prize_elem = item.select_one('.prize, [class*="prize"]')
                prize_text = prize_elem.get_text(strip=True) if prize_elem else ''
                
                desc_elem = item.select_one('.description, p')
                description = desc_elem.get_text(strip=True) if desc_elem else ''
                
                tags = ['data-science', 'datacastle', 'competition']
                if comp_type:
                    tags.append(comp_type.lower())
                if difficulty:
                    tags.append(f"difficulty-{difficulty.lower()}")
                
                activity = self.create_activity(
                    url=url or self.source_url,
                    title=title,
                    description=f"{description} 类型: {comp_type} 难度: {difficulty}".strip(),
                    prize_amount=self._normalize_prize(prize_text),
                    prize_currency='CNY',
                    prize_description=prize_text,
                    tags=tags,
                )
                activities.append(activity)
                
            except Exception as e:
                logger.warning(f"Failed to parse DataCastle competition: {e}")
                continue
        
        return activities
    
    def _parse_drivendata(self, soup: BeautifulSoup) -> List[Activity]:
        """
        解析DrivenData页面
        Validates: Requirements 2.4
        """
        activities = []
        
        competition_items = soup.select('.competition, .card, [class*="competition"]')
        
        for item in competition_items:
            try:
                title_elem = item.select_one('h2, h3, .title, [class*="title"]')
                title = title_elem.get_text(strip=True) if title_elem else None
                
                if not title:
                    continue
                
                link_elem = item.select_one('a[href]')
                url = link_elem.get('href', '') if link_elem else ''
                if url and not url.startswith('http'):
                    url = f"https://www.drivendata.org{url}"
                
                # 提取影响力指标
                impact_elem = item.select_one('.impact, [class*="impact"]')
                impact = impact_elem.get_text(strip=True) if impact_elem else ''
                
                prize_elem = item.select_one('.prize, [class*="prize"]')
                prize_text = prize_elem.get_text(strip=True) if prize_elem else ''
                
                desc_elem = item.select_one('.description, p')
                description = desc_elem.get_text(strip=True) if desc_elem else ''
                
                deadline_elem = item.select_one('.deadline, [class*="deadline"]')
                deadline_text = deadline_elem.get_text(strip=True) if deadline_elem else ''
                
                activity = self.create_activity(
                    url=url or self.source_url,
                    title=title,
                    description=f"{description} 影响力: {impact}".strip(),
                    prize_amount=self._normalize_prize(prize_text),
                    prize_currency='USD',
                    prize_description=prize_text,
                    deadline=self._parse_deadline(deadline_text),
                    tags=['data-science', 'drivendata', 'social-good', 'competition'],
                )
                activities.append(activity)
                
            except Exception as e:
                logger.warning(f"Failed to parse DrivenData competition: {e}")
                continue
        
        return activities
    
    def _parse_deadline(self, text: str) -> Optional[datetime]:
        """解析截止日期文本"""
        if not text:
            return None
        
        normalized = self._normalize_date(text)
        if normalized:
            try:
                return datetime.fromisoformat(normalized.replace('Z', '+00:00'))
            except:
                pass
        return None

