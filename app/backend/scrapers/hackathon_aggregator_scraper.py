"""
VigilAI 黑客松聚合爬虫
支持MLH、Hackathon.com等平台

Validates: Requirements 3.1, 3.2, 3.3, 3.4, 10.1, 10.2, 10.3
"""

import logging
from typing import List, Optional
from datetime import datetime
from bs4 import BeautifulSoup

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scrapers.base import BaseScraper
from models import Activity

logger = logging.getLogger(__name__)


class HackathonAggregatorScraper(BaseScraper):
    """
    黑客松聚合爬虫
    
    支持平台:
    - MLH (Major League Hacking)
    - Hackathon.com
    
    功能:
    - 过期活动过滤
    - 地点、时间、主题提取
    - 奖金、赞助商、技术栈识别
    """
    
    async def scrape(self) -> List[Activity]:
        """抓取黑客松信息"""
        try:
            html = await self.fetch_url(self.source_url)
            if not html:
                return []
            
            soup = BeautifulSoup(html, 'html.parser')
            activities = []
            
            if 'mlh.io' in self.source_url:
                activities = self._parse_mlh(soup)
            elif 'hackathon.com' in self.source_url:
                activities = self._parse_hackathon_com(soup)
            else:
                logger.warning(f"No parser for URL: {self.source_url}")
            
            # 过滤已结束的活动
            current_time = datetime.utcnow()
            activities = [act for act in activities if self._is_active(act, current_time)]
            
            logger.info(f"Scraped {len(activities)} hackathons from {self.source_name}")
            return activities
            
        except Exception as e:
            if self.handle_error(e, "scrape"):
                await self.add_random_delay()
                return await self.scrape()
            return []
    
    def _is_active(self, activity: Activity, current_time: datetime) -> bool:
        """
        检查活动是否仍然有效
        Validates: Requirements 3.4
        """
        if not activity.dates or not activity.dates.deadline:
            return True  # 如果没有截止日期，保留
        
        try:
            deadline = activity.dates.deadline
            if isinstance(deadline, str):
                deadline = datetime.fromisoformat(deadline.replace('Z', '+00:00'))
            return deadline > current_time
        except:
            return True  # 解析失败时保留
    
    def _parse_mlh(self, soup: BeautifulSoup) -> List[Activity]:
        """
        解析MLH平台
        Validates: Requirements 3.1
        """
        activities = []
        
        # MLH事件卡片选择器
        event_cards = soup.select('.event, .event-card, [class*="event"]')
        
        if not event_cards:
            event_cards = soup.select('article, .card, .item')
        
        for card in event_cards:
            try:
                # 提取标题
                title_elem = card.select_one('h3, h2, .event-name, [class*="title"]')
                title = title_elem.get_text(strip=True) if title_elem else None
                
                if not title:
                    continue
                
                # 提取URL
                link_elem = card.select_one('a[href]')
                url = link_elem.get('href', '') if link_elem else ''
                if url and not url.startswith('http'):
                    url = f"https://mlh.io{url}"
                
                # 提取日期
                date_elem = card.select_one('.event-date, [class*="date"]')
                date_text = date_elem.get_text(strip=True) if date_elem else ''
                
                # 提取地点
                location_elem = card.select_one('.event-location, [class*="location"]')
                location = location_elem.get_text(strip=True) if location_elem else ''
                
                # 提取模式（线上/线下）
                mode_elem = card.select_one('[class*="mode"], [class*="type"]')
                mode = mode_elem.get_text(strip=True) if mode_elem else ''
                
                # 提取图片（可能包含赞助商信息）
                img_elem = card.select_one('img')
                img_alt = img_elem.get('alt', '') if img_elem else ''
                
                tags = ['hackathon', 'mlh']
                if 'online' in location.lower() or 'virtual' in location.lower():
                    tags.append('online')
                else:
                    tags.append('in-person')
                
                activity = self.create_activity(
                    url=url or self.source_url,
                    title=title,
                    description=f"{date_text} - {location} {mode}".strip(),
                    location=location,
                    deadline=self._parse_deadline(date_text),
                    tags=tags,
                )
                activities.append(activity)
                
            except Exception as e:
                logger.warning(f"Failed to parse MLH event: {e}")
                continue
        
        return activities
    
    def _parse_hackathon_com(self, soup: BeautifulSoup) -> List[Activity]:
        """
        解析Hackathon.com
        Validates: Requirements 3.2, 3.3
        """
        activities = []
        
        # Hackathon.com事件选择器
        event_items = soup.select('.hackathon, .event, [class*="hackathon"]')
        
        if not event_items:
            event_items = soup.select('article, .card, .item')
        
        for item in event_items:
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
                    url = f"https://www.hackathon.com{url}"
                
                # 提取地点（线上/线下）
                location_elem = item.select_one('.location, [class*="location"]')
                location = location_elem.get_text(strip=True) if location_elem else ''
                
                # 提取时间
                time_elem = item.select_one('.date, .time, [class*="date"]')
                time_text = time_elem.get_text(strip=True) if time_elem else ''
                
                # 提取主题
                theme_elem = item.select_one('.theme, .topic, [class*="theme"]')
                theme = theme_elem.get_text(strip=True) if theme_elem else ''
                
                # 提取奖金
                prize_elem = item.select_one('.prize, [class*="prize"]')
                prize_text = prize_elem.get_text(strip=True) if prize_elem else ''
                
                # 提取赞助商
                sponsor_elem = item.select_one('.sponsor, [class*="sponsor"]')
                sponsor = sponsor_elem.get_text(strip=True) if sponsor_elem else ''
                
                # 提取技术栈
                tech_elem = item.select_one('.tech, .stack, [class*="tech"]')
                tech_stack = tech_elem.get_text(strip=True) if tech_elem else ''
                
                tags = ['hackathon']
                if theme:
                    tags.append(theme.lower().replace(' ', '-'))
                if 'online' in location.lower() or 'virtual' in location.lower():
                    tags.append('online')
                else:
                    tags.append('in-person')
                
                description = f"{time_text}"
                if theme:
                    description += f" | 主题: {theme}"
                if sponsor:
                    description += f" | 赞助商: {sponsor}"
                if tech_stack:
                    description += f" | 技术栈: {tech_stack}"
                
                activity = self.create_activity(
                    url=url or self.source_url,
                    title=title,
                    description=description.strip(),
                    location=location,
                    organizer=sponsor,
                    prize_amount=self._normalize_prize(prize_text),
                    prize_currency=self.extract_currency(prize_text),
                    prize_description=prize_text,
                    deadline=self._parse_deadline(time_text),
                    tags=tags,
                )
                activities.append(activity)
                
            except Exception as e:
                logger.warning(f"Failed to parse Hackathon.com event: {e}")
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

