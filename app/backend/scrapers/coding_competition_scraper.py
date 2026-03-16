"""
VigilAI 编程竞赛爬虫
支持HackerEarth、TopCoder等平台

Validates: Requirements 8.1, 8.2, 8.3, 10.1, 10.2, 10.3
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


class CodingCompetitionScraper(BaseScraper):
    """
    编程竞赛爬虫
    
    支持平台:
    - HackerEarth
    - TopCoder
    
    功能:
    - 竞赛状态标记（进行中/即将开始/已结束）
    - 难度、时长、奖励提取
    - SRM和Marathon赛事识别
    """
    
    async def scrape(self) -> List[Activity]:
        """抓取编程竞赛信息"""
        try:
            html = await self.fetch_url(self.source_url)
            if not html:
                return []
            
            soup = BeautifulSoup(html, 'html.parser')
            activities = []
            
            if 'hackerearth' in self.source_url:
                activities = self._parse_hackerearth(soup)
            elif 'topcoder' in self.source_url:
                activities = self._parse_topcoder(soup)
            else:
                logger.warning(f"No parser for URL: {self.source_url}")
            
            logger.info(f"Scraped {len(activities)} coding competitions from {self.source_name}")
            return activities
            
        except Exception as e:
            if self.handle_error(e, "scrape"):
                await self.add_random_delay()
                return await self.scrape()
            return []
    
    def _parse_hackerearth(self, soup: BeautifulSoup) -> List[Activity]:
        """
        解析HackerEarth
        Validates: Requirements 8.1
        """
        activities = []
        
        challenge_items = soup.select('.challenge, .event, [class*="challenge"]')
        
        if not challenge_items:
            challenge_items = soup.select('article, .card, .item')
        
        for item in challenge_items:
            try:
                title_elem = item.select_one('h2, h3, .title, [class*="title"]')
                title = title_elem.get_text(strip=True) if title_elem else None
                
                if not title:
                    continue
                
                link_elem = item.select_one('a[href]')
                url = link_elem.get('href', '') if link_elem else ''
                if url and not url.startswith('http'):
                    url = f"https://www.hackerearth.com{url}"
                
                # 提取难度
                difficulty_elem = item.select_one('.difficulty, [class*="difficulty"], [class*="level"]')
                difficulty = difficulty_elem.get_text(strip=True) if difficulty_elem else ''
                
                # 提取时长
                duration_elem = item.select_one('.duration, [class*="duration"], [class*="time"]')
                duration = duration_elem.get_text(strip=True) if duration_elem else ''
                
                # 提取奖励
                prize_elem = item.select_one('.prize, [class*="prize"], [class*="reward"]')
                prize_text = prize_elem.get_text(strip=True) if prize_elem else ''
                
                # 提取状态
                status_elem = item.select_one('.status, [class*="status"]')
                status = status_elem.get_text(strip=True) if status_elem else ''
                
                desc_elem = item.select_one('.description, p')
                description = desc_elem.get_text(strip=True) if desc_elem else ''
                
                full_desc = description
                if difficulty:
                    full_desc += f" | 难度: {difficulty}"
                if duration:
                    full_desc += f" | 时长: {duration}"
                
                tags = ['coding', 'algorithm', 'hackerearth']
                if difficulty:
                    tags.append(f"difficulty-{difficulty.lower()}")
                if self._is_active_status(status):
                    tags.append('active')
                
                activity = self.create_activity(
                    url=url or self.source_url,
                    title=title,
                    description=full_desc.strip(),
                    prize_amount=self._normalize_prize(prize_text),
                    prize_currency=self.extract_currency(prize_text),
                    prize_description=prize_text,
                    status='active' if self._is_active_status(status) else 'upcoming',
                    tags=tags,
                )
                activities.append(activity)
                
            except Exception as e:
                logger.warning(f"Failed to parse HackerEarth challenge: {e}")
                continue
        
        return activities
    
    def _parse_topcoder(self, soup: BeautifulSoup) -> List[Activity]:
        """
        解析TopCoder
        Validates: Requirements 8.2, 8.3
        """
        activities = []
        
        challenge_items = soup.select('.challenge-item, .challenge, [class*="challenge"]')
        
        if not challenge_items:
            challenge_items = soup.select('article, .card, .item, tr')
        
        for item in challenge_items:
            try:
                title_elem = item.select_one('h2, h3, .title, [class*="title"], .name')
                title = title_elem.get_text(strip=True) if title_elem else None
                
                if not title:
                    continue
                
                link_elem = item.select_one('a[href]')
                url = link_elem.get('href', '') if link_elem else ''
                if url and not url.startswith('http'):
                    url = f"https://www.topcoder.com{url}"
                
                # 提取竞赛类型（SRM或Marathon）
                type_elem = item.select_one('.type, [class*="type"], [class*="track"]')
                challenge_type = type_elem.get_text(strip=True) if type_elem else ''
                
                # 提取奖金
                prize_elem = item.select_one('.prize, [class*="prize"]')
                prize_text = prize_elem.get_text(strip=True) if prize_elem else ''
                
                # 提取截止时间
                deadline_elem = item.select_one('.end-time, [class*="deadline"], [class*="end"]')
                deadline_text = deadline_elem.get_text(strip=True) if deadline_elem else ''
                
                # 提取状态
                status_elem = item.select_one('.status, [class*="status"]')
                status = status_elem.get_text(strip=True) if status_elem else ''
                
                desc_elem = item.select_one('.description, p')
                description = desc_elem.get_text(strip=True) if desc_elem else ''
                
                tags = ['coding', 'algorithm', 'topcoder']
                
                # 识别SRM或Marathon
                if 'srm' in challenge_type.lower() or 'single round' in challenge_type.lower():
                    tags.append('srm')
                elif 'marathon' in challenge_type.lower():
                    tags.append('marathon')
                
                # 标记正在进行的竞赛
                if self._is_active_status(status):
                    tags.append('active')
                
                activity = self.create_activity(
                    url=url or self.source_url,
                    title=title,
                    description=f"{description} | 类型: {challenge_type}".strip(),
                    prize_amount=self._normalize_prize(prize_text),
                    prize_currency=self.extract_currency(prize_text),
                    prize_description=prize_text,
                    deadline=self._parse_deadline(deadline_text),
                    status='active' if self._is_active_status(status) else 'upcoming',
                    tags=tags,
                )
                activities.append(activity)
                
            except Exception as e:
                logger.warning(f"Failed to parse TopCoder challenge: {e}")
                continue
        
        return activities
    
    def _is_active_status(self, status: str) -> bool:
        """
        检查竞赛是否正在进行
        Validates: Requirements 8.3
        """
        if not status:
            return False
        
        status_lower = status.lower()
        active_keywords = ['active', 'live', 'ongoing', 'running', '进行中', '正在进行']
        
        return any(keyword in status_lower for keyword in active_keywords)
    
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

