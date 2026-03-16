"""
VigilAI 设计竞赛爬虫
支持设计竞赛网等平台

Validates: Requirements 7.1, 7.2, 7.3, 10.1, 10.2, 10.3
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


class DesignCompetitionScraper(BaseScraper):
    """
    设计竞赛爬虫
    
    支持平台:
    - 设计竞赛网
    
    功能:
    - 设计类型标签提取（UI/UX、平面、工业设计等）
    - 作品提交格式、评审标准提取
    - 多阶段竞赛时间节点记录
    """
    
    async def scrape(self) -> List[Activity]:
        """抓取设计竞赛信息"""
        try:
            html = await self.fetch_url(self.source_url)
            if not html:
                return []
            
            soup = BeautifulSoup(html, 'html.parser')
            activities = self._parse_design_competitions(soup)
            
            logger.info(f"Scraped {len(activities)} design competitions from {self.source_name}")
            return activities
            
        except Exception as e:
            if self.handle_error(e, "scrape"):
                await self.add_random_delay()
                return await self.scrape()
            return []
    
    def _parse_design_competitions(self, soup: BeautifulSoup) -> List[Activity]:
        """
        解析设计竞赛
        Validates: Requirements 7.1, 7.2, 7.3
        """
        activities = []
        
        competition_items = soup.select('.competition-item, .card, [class*="competition"]')
        
        if not competition_items:
            competition_items = soup.select('article, .item, .listing')
        
        for item in competition_items:
            try:
                title_elem = item.select_one('h2, h3, .title, [class*="title"]')
                title = title_elem.get_text(strip=True) if title_elem else None
                
                if not title:
                    continue
                
                link_elem = item.select_one('a[href]')
                url = link_elem.get('href', '') if link_elem else ''
                if url and not url.startswith('http'):
                    url = f"https://www.shejijingsai.com{url}"
                
                # 提取竞赛类型
                type_elem = item.select_one('.type, [class*="type"], [class*="category"]')
                design_type = type_elem.get_text(strip=True) if type_elem else ''
                
                # 提取奖金
                prize_elem = item.select_one('.prize, [class*="prize"]')
                prize_text = prize_elem.get_text(strip=True) if prize_elem else ''
                
                # 提取截止日期
                deadline_elem = item.select_one('.deadline, [class*="deadline"], [class*="date"]')
                deadline_text = deadline_elem.get_text(strip=True) if deadline_elem else ''
                
                # 提取作品提交格式
                format_elem = item.select_one('.format, [class*="format"], [class*="submission"]')
                submission_format = format_elem.get_text(strip=True) if format_elem else ''
                
                # 提取评审标准
                criteria_elem = item.select_one('.criteria, [class*="criteria"], [class*="judge"]')
                criteria = criteria_elem.get_text(strip=True) if criteria_elem else ''
                
                # 提取多阶段时间节点
                stages = self._extract_stages(item)
                
                desc_elem = item.select_one('.description, p')
                description = desc_elem.get_text(strip=True) if desc_elem else ''
                
                full_desc = description
                if submission_format:
                    full_desc += f" | 提交格式: {submission_format}"
                if criteria:
                    full_desc += f" | 评审标准: {criteria}"
                if stages:
                    full_desc += f" | 阶段: {stages}"
                
                tags = self._extract_design_type(design_type, title)
                
                activity = self.create_activity(
                    url=url or self.source_url,
                    title=title,
                    description=full_desc.strip(),
                    prize_amount=self._normalize_prize(prize_text),
                    prize_currency=self.extract_currency(prize_text) or 'CNY',
                    prize_description=prize_text,
                    deadline=self._parse_deadline(deadline_text),
                    tags=tags,
                )
                activities.append(activity)
                
            except Exception as e:
                logger.warning(f"Failed to parse design competition: {e}")
                continue
        
        return activities
    
    def _extract_design_type(self, type_text: str, title: str) -> List[str]:
        """
        提取设计类型标签
        Validates: Requirements 7.1
        """
        tags = ['design', 'competition']
        
        combined_text = f"{type_text} {title}".lower()
        
        if 'ui' in combined_text or 'ux' in combined_text or '界面' in combined_text:
            tags.append('ui-ux')
        if '平面' in combined_text or 'graphic' in combined_text or '视觉' in combined_text:
            tags.append('graphic-design')
        if '工业' in combined_text or 'industrial' in combined_text or '产品' in combined_text:
            tags.append('industrial-design')
        if '包装' in combined_text or 'packaging' in combined_text:
            tags.append('packaging-design')
        if '室内' in combined_text or 'interior' in combined_text:
            tags.append('interior-design')
        if '建筑' in combined_text or 'architecture' in combined_text:
            tags.append('architecture')
        if '服装' in combined_text or 'fashion' in combined_text:
            tags.append('fashion-design')
        if '插画' in combined_text or 'illustration' in combined_text:
            tags.append('illustration')
        if 'logo' in combined_text or '标志' in combined_text:
            tags.append('logo-design')
        if '海报' in combined_text or 'poster' in combined_text:
            tags.append('poster-design')
        
        return tags
    
    def _extract_stages(self, item) -> str:
        """
        提取多阶段竞赛时间节点
        Validates: Requirements 7.3
        """
        stages = []
        
        # 尝试查找阶段信息
        stage_elems = item.select('.stage, [class*="stage"], [class*="phase"], .timeline li')
        
        for stage_elem in stage_elems:
            stage_name = ''
            stage_date = ''
            
            name_elem = stage_elem.select_one('.name, [class*="name"]')
            if name_elem:
                stage_name = name_elem.get_text(strip=True)
            
            date_elem = stage_elem.select_one('.date, [class*="date"]')
            if date_elem:
                stage_date = date_elem.get_text(strip=True)
            
            if stage_name or stage_date:
                stages.append(f"{stage_name}: {stage_date}".strip(': '))
        
        return ' -> '.join(stages) if stages else ''
    
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

