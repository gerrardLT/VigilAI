"""
VigilAI 漏洞赏金爬虫
支持HackerOne、Bugcrowd、Code4rena、IssueHunt、Bountysource等平台

Validates: Requirements 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 10.1, 10.2, 10.3
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


class BountyScraper(BaseScraper):
    """
    漏洞赏金爬虫
    
    支持平台:
    - HackerOne
    - Bugcrowd
    - Code4rena
    - IssueHunt
    - Bountysource
    
    功能:
    - 仅抓取公开可见项目
    - 奖金范围和响应时间提取
    - 严重性等级和支付条件解析
    """
    
    async def scrape(self) -> List[Activity]:
        """抓取漏洞赏金信息"""
        try:
            html = await self.fetch_url(self.source_url)
            if not html:
                return []
            
            soup = BeautifulSoup(html, 'html.parser')
            activities = []
            
            if 'hackerone' in self.source_url:
                activities = self._parse_hackerone(soup)
            elif 'bugcrowd' in self.source_url:
                activities = self._parse_bugcrowd(soup)
            elif 'code4rena' in self.source_url:
                activities = self._parse_code4rena(soup)
            elif 'issuehunt' in self.source_url:
                activities = self._parse_issuehunt(soup)
            elif 'bountysource' in self.source_url:
                activities = self._parse_bountysource(soup)
            else:
                logger.warning(f"No parser for URL: {self.source_url}")
            
            logger.info(f"Scraped {len(activities)} bounties from {self.source_name}")
            return activities
            
        except Exception as e:
            if self.handle_error(e, "scrape"):
                await self.add_random_delay()
                return await self.scrape()
            return []
    
    def _parse_hackerone(self, soup: BeautifulSoup) -> List[Activity]:
        """
        解析HackerOne公开赏金项目
        Validates: Requirements 4.1
        """
        activities = []
        
        program_items = soup.select('.program, .directory-item, [class*="program"]')
        
        if not program_items:
            program_items = soup.select('article, .card, .item, tr')
        
        for item in program_items:
            try:
                # 提取项目名称
                title_elem = item.select_one('h2, h3, .name, [class*="name"]')
                title = title_elem.get_text(strip=True) if title_elem else None
                
                if not title:
                    continue
                
                # 提取URL
                link_elem = item.select_one('a[href]')
                url = link_elem.get('href', '') if link_elem else ''
                if url and not url.startswith('http'):
                    url = f"https://hackerone.com{url}"
                
                # 提取赏金范围
                bounty_elem = item.select_one('.bounty, [class*="bounty"], [class*="reward"]')
                bounty_text = bounty_elem.get_text(strip=True) if bounty_elem else ''
                
                # 提取响应时间
                response_elem = item.select_one('.response-time, [class*="response"]')
                response_time = response_elem.get_text(strip=True) if response_elem else ''
                
                # 提取范围/类型
                scope_elem = item.select_one('.scope, [class*="scope"]')
                scope = scope_elem.get_text(strip=True) if scope_elem else ''
                
                description = f"赏金范围: {bounty_text}"
                if response_time:
                    description += f" | 响应时间: {response_time}"
                if scope:
                    description += f" | 范围: {scope}"
                
                activity = self.create_activity(
                    url=url or self.source_url,
                    title=f"{title} Bug Bounty",
                    description=description.strip(),
                    prize_amount=self._normalize_prize(bounty_text),
                    prize_currency=self.extract_currency(bounty_text),
                    prize_description=bounty_text,
                    tags=['bounty', 'security', 'hackerone'],
                )
                activities.append(activity)
                
            except Exception as e:
                logger.warning(f"Failed to parse HackerOne program: {e}")
                continue
        
        return activities
    
    def _parse_bugcrowd(self, soup: BeautifulSoup) -> List[Activity]:
        """
        解析Bugcrowd项目
        Validates: Requirements 4.2
        """
        activities = []
        
        program_items = soup.select('.program, .bounty-item, [class*="program"]')
        
        if not program_items:
            program_items = soup.select('article, .card, .item, tr')
        
        for item in program_items:
            try:
                title_elem = item.select_one('h2, h3, .name, [class*="name"]')
                title = title_elem.get_text(strip=True) if title_elem else None
                
                if not title:
                    continue
                
                link_elem = item.select_one('a[href]')
                url = link_elem.get('href', '') if link_elem else ''
                if url and not url.startswith('http'):
                    url = f"https://www.bugcrowd.com{url}"
                
                # 提取严重性等级
                severity_elem = item.select_one('.severity, [class*="severity"]')
                severity = severity_elem.get_text(strip=True) if severity_elem else ''
                
                # 提取支付条件
                payout_elem = item.select_one('.payout, [class*="payout"], [class*="reward"]')
                payout = payout_elem.get_text(strip=True) if payout_elem else ''
                
                description = f"支付: {payout}"
                if severity:
                    description += f" | 严重性: {severity}"
                
                tags = ['bounty', 'security', 'bugcrowd']
                if severity:
                    tags.append(f"severity-{severity.lower()}")
                
                activity = self.create_activity(
                    url=url or self.source_url,
                    title=f"{title} Bug Bounty",
                    description=description.strip(),
                    prize_amount=self._normalize_prize(payout),
                    prize_currency=self.extract_currency(payout),
                    prize_description=payout,
                    tags=tags,
                )
                activities.append(activity)
                
            except Exception as e:
                logger.warning(f"Failed to parse Bugcrowd program: {e}")
                continue
        
        return activities
    
    def _parse_code4rena(self, soup: BeautifulSoup) -> List[Activity]:
        """
        解析Code4rena智能合约审计竞赛
        Validates: Requirements 4.3
        """
        activities = []
        
        contest_items = soup.select('.contest, .audit, [class*="contest"]')
        
        if not contest_items:
            contest_items = soup.select('article, .card, .item')
        
        for item in contest_items:
            try:
                title_elem = item.select_one('h2, h3, .title, [class*="title"]')
                title = title_elem.get_text(strip=True) if title_elem else None
                
                if not title:
                    continue
                
                link_elem = item.select_one('a[href]')
                url = link_elem.get('href', '') if link_elem else ''
                if url and not url.startswith('http'):
                    url = f"https://code4rena.com{url}"
                
                # 提取奖池
                prize_elem = item.select_one('.prize-pool, [class*="prize"], [class*="pool"]')
                prize_text = prize_elem.get_text(strip=True) if prize_elem else ''
                
                # 提取时间线
                timeline_elem = item.select_one('.timeline, [class*="time"], [class*="date"]')
                timeline = timeline_elem.get_text(strip=True) if timeline_elem else ''
                
                # 提取状态
                status_elem = item.select_one('.status, [class*="status"]')
                status = status_elem.get_text(strip=True) if status_elem else ''
                
                description = f"奖池: {prize_text}"
                if timeline:
                    description += f" | 时间: {timeline}"
                if status:
                    description += f" | 状态: {status}"
                
                tags = ['bounty', 'smart-contract', 'audit', 'web3', 'code4rena']
                if 'active' in status.lower() or 'live' in status.lower():
                    tags.append('active')
                
                activity = self.create_activity(
                    url=url or self.source_url,
                    title=title,
                    description=description.strip(),
                    prize_amount=self._normalize_prize(prize_text),
                    prize_currency=self.extract_currency(prize_text) or 'USDC',
                    prize_description=prize_text,
                    deadline=self._parse_deadline(timeline),
                    tags=tags,
                )
                activities.append(activity)
                
            except Exception as e:
                logger.warning(f"Failed to parse Code4rena contest: {e}")
                continue
        
        return activities
    
    def _parse_issuehunt(self, soup: BeautifulSoup) -> List[Activity]:
        """
        解析IssueHunt开源项目赏金
        Validates: Requirements 4.4
        """
        activities = []
        
        issue_items = soup.select('.issue, .bounty, [class*="issue"]')
        
        if not issue_items:
            issue_items = soup.select('article, .card, .item')
        
        for item in issue_items:
            try:
                title_elem = item.select_one('h2, h3, .title, [class*="title"]')
                title = title_elem.get_text(strip=True) if title_elem else None
                
                if not title:
                    continue
                
                link_elem = item.select_one('a[href]')
                url = link_elem.get('href', '') if link_elem else ''
                if url and not url.startswith('http'):
                    url = f"https://issuehunt.io{url}"
                
                # 提取赏金金额
                bounty_elem = item.select_one('.bounty-amount, [class*="bounty"], [class*="amount"]')
                bounty_text = bounty_elem.get_text(strip=True) if bounty_elem else ''
                
                # 提取技术要求
                tech_elem = item.select_one('.tech, .language, [class*="tech"]')
                tech = tech_elem.get_text(strip=True) if tech_elem else ''
                
                # 提取项目名
                project_elem = item.select_one('.project, .repo, [class*="project"]')
                project = project_elem.get_text(strip=True) if project_elem else ''
                
                description = f"赏金: {bounty_text}"
                if tech:
                    description += f" | 技术: {tech}"
                if project:
                    description += f" | 项目: {project}"
                
                tags = ['bounty', 'opensource', 'issuehunt']
                if tech:
                    tags.append(tech.lower())
                
                activity = self.create_activity(
                    url=url or self.source_url,
                    title=title,
                    description=description.strip(),
                    prize_amount=self._normalize_prize(bounty_text),
                    prize_currency=self.extract_currency(bounty_text),
                    prize_description=bounty_text,
                    tags=tags,
                )
                activities.append(activity)
                
            except Exception as e:
                logger.warning(f"Failed to parse IssueHunt issue: {e}")
                continue
        
        return activities
    
    def _parse_bountysource(self, soup: BeautifulSoup) -> List[Activity]:
        """
        解析Bountysource众筹赏金
        Validates: Requirements 4.5
        """
        activities = []
        
        bounty_items = soup.select('.bounty, .issue, [class*="bounty"]')
        
        if not bounty_items:
            bounty_items = soup.select('article, .card, .item')
        
        for item in bounty_items:
            try:
                title_elem = item.select_one('h2, h3, .title, [class*="title"]')
                title = title_elem.get_text(strip=True) if title_elem else None
                
                if not title:
                    continue
                
                link_elem = item.select_one('a[href]')
                url = link_elem.get('href', '') if link_elem else ''
                if url and not url.startswith('http'):
                    url = f"https://www.bountysource.com{url}"
                
                # 提取当前金额
                amount_elem = item.select_one('.amount, [class*="amount"], [class*="bounty"]')
                amount_text = amount_elem.get_text(strip=True) if amount_elem else ''
                
                # 提取支持者数量
                backers_elem = item.select_one('.backers, [class*="backer"], [class*="supporter"]')
                backers = backers_elem.get_text(strip=True) if backers_elem else ''
                
                description = f"当前金额: {amount_text}"
                if backers:
                    description += f" | 支持者: {backers}"
                
                activity = self.create_activity(
                    url=url or self.source_url,
                    title=title,
                    description=description.strip(),
                    prize_amount=self._normalize_prize(amount_text),
                    prize_currency=self.extract_currency(amount_text),
                    prize_description=amount_text,
                    tags=['bounty', 'opensource', 'crowdfunding', 'bountysource'],
                )
                activities.append(activity)
                
            except Exception as e:
                logger.warning(f"Failed to parse Bountysource bounty: {e}")
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

