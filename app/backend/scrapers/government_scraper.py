"""
VigilAI 政府竞赛爬虫
支持Challenge.gov、中国创新创业大赛、创客中国等平台

Validates: Requirements 6.1, 6.2, 6.3, 10.1, 10.2, 10.3
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


class GovernmentScraper(BaseScraper):
    """
    政府竞赛爬虫
    
    支持平台:
    - Challenge.gov (美国)
    - 中国创新创业大赛
    - 创客中国
    
    功能:
    - 中文编码处理
    - 赛事阶段、奖金、报名要求提取
    """
    
    async def scrape(self) -> List[Activity]:
        """抓取政府竞赛信息"""
        try:
            html = await self.fetch_url(self.source_url)
            if not html:
                return []
            
            soup = BeautifulSoup(html, 'html.parser')
            activities = []
            
            if 'challenge.gov' in self.source_url:
                activities = self._parse_challenge_gov(soup)
            elif '创新创业' in self.source_name or 'cxcyds' in self.source_url:
                activities = self._parse_innovation_competition(soup)
            elif '创客中国' in self.source_name or 'cnmaker' in self.source_url:
                activities = self._parse_maker_china(soup)
            else:
                logger.warning(f"No parser for URL: {self.source_url}")
            
            logger.info(f"Scraped {len(activities)} government competitions from {self.source_name}")
            return activities
            
        except Exception as e:
            if self.handle_error(e, "scrape"):
                await self.add_random_delay()
                return await self.scrape()
            return []
    
    def _parse_challenge_gov(self, soup: BeautifulSoup) -> List[Activity]:
        """
        解析Challenge.gov
        Validates: Requirements 6.1
        """
        activities = []
        
        challenge_items = soup.select('.challenge, .card, [class*="challenge"]')
        
        if not challenge_items:
            challenge_items = soup.select('article, .item, .listing')
        
        for item in challenge_items:
            try:
                title_elem = item.select_one('h2, h3, .title, [class*="title"]')
                title = title_elem.get_text(strip=True) if title_elem else None
                
                if not title:
                    continue
                
                link_elem = item.select_one('a[href]')
                url = link_elem.get('href', '') if link_elem else ''
                if url and not url.startswith('http'):
                    url = f"https://www.challenge.gov{url}"
                
                # 提取机构
                agency_elem = item.select_one('.agency, [class*="agency"]')
                agency = agency_elem.get_text(strip=True) if agency_elem else ''
                
                # 提取奖金
                prize_elem = item.select_one('.prize, [class*="prize"]')
                prize_text = prize_elem.get_text(strip=True) if prize_elem else ''
                
                # 提取截止日期
                deadline_elem = item.select_one('.deadline, [class*="deadline"], [class*="date"]')
                deadline_text = deadline_elem.get_text(strip=True) if deadline_elem else ''
                
                desc_elem = item.select_one('.description, p')
                description = desc_elem.get_text(strip=True) if desc_elem else ''
                
                activity = self.create_activity(
                    url=url or self.source_url,
                    title=title,
                    description=f"{description} 机构: {agency}".strip(),
                    prize_amount=self._normalize_prize(prize_text),
                    prize_currency='USD',
                    prize_description=prize_text,
                    deadline=self._parse_deadline(deadline_text),
                    organizer=agency or 'US Government',
                    tags=['government', 'challenge', 'usa'],
                )
                activities.append(activity)
                
            except Exception as e:
                logger.warning(f"Failed to parse Challenge.gov item: {e}")
                continue
        
        return activities
    
    def _parse_innovation_competition(self, soup: BeautifulSoup) -> List[Activity]:
        """
        解析中国创新创业大赛
        Validates: Requirements 6.2
        """
        activities = []
        
        competition_items = soup.select('.competition, .race, [class*="competition"]')
        
        if not competition_items:
            competition_items = soup.select('article, .card, .item')
        
        for item in competition_items:
            try:
                title_elem = item.select_one('h2, h3, .title, [class*="title"]')
                title = title_elem.get_text(strip=True) if title_elem else None
                
                if not title:
                    continue
                
                link_elem = item.select_one('a[href]')
                url = link_elem.get('href', '') if link_elem else ''
                if url and not url.startswith('http'):
                    url = f"http://www.cxcyds.com{url}"
                
                # 提取赛事阶段
                stage_elem = item.select_one('.stage, [class*="stage"], [class*="phase"]')
                stage = stage_elem.get_text(strip=True) if stage_elem else ''
                
                # 提取奖金
                prize_elem = item.select_one('.prize, [class*="prize"], [class*="bonus"]')
                prize_text = prize_elem.get_text(strip=True) if prize_elem else ''
                
                # 提取报名要求
                req_elem = item.select_one('.requirement, [class*="requirement"]')
                requirement = req_elem.get_text(strip=True) if req_elem else ''
                
                # 提取截止日期
                deadline_elem = item.select_one('.deadline, [class*="deadline"], [class*="date"]')
                deadline_text = deadline_elem.get_text(strip=True) if deadline_elem else ''
                
                desc_elem = item.select_one('.description, p')
                description = desc_elem.get_text(strip=True) if desc_elem else ''
                
                full_desc = description
                if stage:
                    full_desc += f" | 阶段: {stage}"
                if requirement:
                    full_desc += f" | 要求: {requirement}"
                
                activity = self.create_activity(
                    url=url or self.source_url,
                    title=title,
                    description=full_desc.strip(),
                    prize_amount=self._normalize_prize(prize_text),
                    prize_currency='CNY',
                    prize_description=prize_text,
                    deadline=self._parse_deadline(deadline_text),
                    organizer='中国创新创业大赛组委会',
                    tags=['government', 'innovation', 'startup', 'china'],
                )
                activities.append(activity)
                
            except Exception as e:
                logger.warning(f"Failed to parse innovation competition: {e}")
                continue
        
        return activities
    
    def _parse_maker_china(self, soup: BeautifulSoup) -> List[Activity]:
        """
        解析创客中国平台
        Validates: Requirements 6.3
        """
        activities = []
        
        competition_items = soup.select('.competition, .race, [class*="competition"]')
        
        if not competition_items:
            competition_items = soup.select('article, .card, .item')
        
        for item in competition_items:
            try:
                title_elem = item.select_one('h2, h3, .title, [class*="title"]')
                title = title_elem.get_text(strip=True) if title_elem else None
                
                if not title:
                    continue
                
                link_elem = item.select_one('a[href]')
                url = link_elem.get('href', '') if link_elem else ''
                if url and not url.startswith('http'):
                    url = f"https://www.cnmaker.org.cn{url}"
                
                # 提取奖金
                prize_elem = item.select_one('.prize, [class*="prize"]')
                prize_text = prize_elem.get_text(strip=True) if prize_elem else ''
                
                # 提取截止日期
                deadline_elem = item.select_one('.deadline, [class*="deadline"], [class*="date"]')
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
                    organizer='工业和信息化部',
                    tags=['government', 'maker', 'sme', 'china'],
                )
                activities.append(activity)
                
            except Exception as e:
                logger.warning(f"Failed to parse Maker China competition: {e}")
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

