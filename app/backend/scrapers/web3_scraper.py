"""
VigilAI Web3平台爬虫
爬取DoraHacks、Gitcoin等Web3平台的黑客松和Grants信息
"""

import re
import logging
from typing import List, Optional, Tuple
from datetime import datetime

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scrapers.web_scraper import WebScraper
from models import Activity

logger = logging.getLogger(__name__)


class Web3Scraper(WebScraper):
    """Web3平台爬虫（DoraHacks、Gitcoin、ETHGlobal、Immunefi等）"""
    
    async def scrape(self) -> List[Activity]:
        """
        根据source_id调用对应的爬取方法
        """
        source_id = self.source_id.lower()
        
        if 'dorahacks' in source_id:
            return await self.scrape_dorahacks()
        elif 'gitcoin' in source_id:
            return await self.scrape_gitcoin()
        elif 'ethglobal' in source_id:
            return await self.scrape_ethglobal()
        elif 'immunefi' in source_id:
            return await self.scrape_immunefi()
        else:
            logger.warning(f"Unknown Web3 source: {self.source_id}")
            return []
    
    async def scrape_dorahacks(self) -> List[Activity]:
        """
        爬取DoraHacks黑客松列表
        """
        try:
            html = await self.fetch_page(self.source_url)
            if not html:
                return []
            
            soup = self.parse_html(html)
            if not soup:
                return []
            
            activities = []
            
            # DoraHacks黑客松卡片选择器
            # 注意：实际选择器可能需要根据网站结构调整
            cards = soup.select('.hackathon-card, .buidl-card, [class*="hackathon"]')
            
            for card in cards:
                try:
                    activity = self._parse_dorahacks_card(card)
                    if activity:
                        activities.append(activity)
                except Exception as e:
                    logger.warning(f"Error parsing DoraHacks card: {e}")
                    continue
            
            return activities
            
        except Exception as e:
            logger.error(f"Error scraping DoraHacks: {e}")
            return []
    
    def _parse_dorahacks_card(self, card) -> Optional[Activity]:
        """解析DoraHacks黑客松卡片"""
        # 提取标题
        title_elem = card.select_one('h3, h4, .title, [class*="title"]')
        title = self.extract_text(title_elem)
        if not title:
            return None
        
        # 提取链接
        link_elem = card.select_one('a[href]')
        link = self.extract_attr(link_elem, 'href')
        if link and not link.startswith('http'):
            link = f"https://dorahacks.io{link}"
        if not link:
            return None
        
        # 提取描述
        desc_elem = card.select_one('.description, .desc, p')
        description = self.extract_text(desc_elem)
        
        # 提取奖金
        prize_elem = card.select_one('.prize, .reward, [class*="prize"]')
        prize_text = self.extract_text(prize_elem)
        prize_amount, prize_currency = self._extract_prize(prize_text)
        
        # 提取日期
        date_elem = card.select_one('.date, .time, [class*="date"]')
        date_text = self.extract_text(date_elem)
        deadline = self._parse_date_text(date_text)
        
        return self.create_activity(
            url=link,
            title=title,
            description=description,
            prize_amount=prize_amount,
            prize_currency=prize_currency,
            deadline=deadline,
            tags=['web3', 'hackathon', 'dorahacks']
        )
    
    async def scrape_gitcoin(self) -> List[Activity]:
        """
        爬取Gitcoin Grants
        """
        try:
            html = await self.fetch_page(self.source_url)
            if not html:
                return []
            
            soup = self.parse_html(html)
            if not soup:
                return []
            
            activities = []
            
            # Gitcoin grants卡片选择器
            cards = soup.select('.grant-card, .round-card, [class*="grant"]')
            
            for card in cards:
                try:
                    activity = self._parse_gitcoin_card(card)
                    if activity:
                        activities.append(activity)
                except Exception as e:
                    logger.warning(f"Error parsing Gitcoin card: {e}")
                    continue
            
            return activities
            
        except Exception as e:
            logger.error(f"Error scraping Gitcoin: {e}")
            return []
    
    def _parse_gitcoin_card(self, card) -> Optional[Activity]:
        """解析Gitcoin Grant卡片"""
        # 提取标题
        title_elem = card.select_one('h3, h4, .title, [class*="title"]')
        title = self.extract_text(title_elem)
        if not title:
            return None
        
        # 提取链接
        link_elem = card.select_one('a[href]')
        link = self.extract_attr(link_elem, 'href')
        if link and not link.startswith('http'):
            link = f"https://gitcoin.co{link}"
        if not link:
            return None
        
        # 提取描述
        desc_elem = card.select_one('.description, .desc, p')
        description = self.extract_text(desc_elem)
        
        # 提取奖金池
        prize_elem = card.select_one('.matching, .pool, [class*="amount"]')
        prize_text = self.extract_text(prize_elem)
        prize_amount, prize_currency = self._extract_prize(prize_text)
        
        return self.create_activity(
            url=link,
            title=title,
            description=description,
            prize_amount=prize_amount,
            prize_currency=prize_currency,
            tags=['web3', 'grant', 'gitcoin']
        )
    
    def _extract_prize(self, text: str) -> Tuple[Optional[float], str]:
        """
        从文本中提取奖金信息
        支持USD、ETH、USDC等
        """
        if not text:
            return None, "USD"
        
        # 匹配美元
        usd_patterns = [
            r'\$\s*([\d,]+(?:\.\d+)?)\s*(?:k|K)?',
            r'([\d,]+(?:\.\d+)?)\s*(?:USD|USDC|USDT)',
        ]
        
        for pattern in usd_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                amount_str = match.group(1).replace(',', '')
                try:
                    amount = float(amount_str)
                    # 处理k/K后缀
                    if 'k' in text.lower():
                        amount *= 1000
                    return amount, "USD"
                except ValueError:
                    continue
        
        # 匹配ETH
        eth_pattern = r'([\d,]+(?:\.\d+)?)\s*(?:ETH|Ξ)'
        match = re.search(eth_pattern, text, re.IGNORECASE)
        if match:
            try:
                return float(match.group(1).replace(',', '')), "ETH"
            except ValueError:
                pass
        
        return None, "USD"
    
    def _parse_date_text(self, text: str) -> Optional[datetime]:
        """解析日期文本"""
        if not text:
            return None
        
        from dateutil import parser as date_parser
        try:
            return date_parser.parse(text, fuzzy=True)
        except (ValueError, TypeError):
            return None
    
    async def scrape_ethglobal(self) -> List[Activity]:
        """
        爬取ETHGlobal黑客松
        Validates: Requirements 9.3
        """
        try:
            html = await self.fetch_page(self.source_url)
            if not html:
                return []
            
            soup = self.parse_html(html)
            if not soup:
                return []
            
            activities = []
            
            # ETHGlobal黑客松卡片选择器
            cards = soup.select('.event-card, .hackathon-card, [class*="event"], [class*="hackathon"], article')
            
            for card in cards:
                try:
                    activity = self._parse_ethglobal_card(card)
                    if activity:
                        activities.append(activity)
                except Exception as e:
                    logger.warning(f"Error parsing ETHGlobal card: {e}")
                    continue
            
            logger.info(f"Scraped {len(activities)} hackathons from ETHGlobal")
            return activities
            
        except Exception as e:
            logger.error(f"Error scraping ETHGlobal: {e}")
            return []
    
    def _parse_ethglobal_card(self, card) -> Optional[Activity]:
        """
        解析ETHGlobal黑客松卡片
        提取赞助商、赛道和评审标准
        """
        # 提取标题
        title_elem = card.select_one('h2, h3, h4, .title, [class*="title"], [class*="name"]')
        title = self.extract_text(title_elem)
        if not title:
            return None
        
        # 提取链接
        link_elem = card.select_one('a[href]')
        link = self.extract_attr(link_elem, 'href')
        if link and not link.startswith('http'):
            link = f"https://ethglobal.com{link}"
        if not link:
            return None
        
        # 提取描述
        desc_elem = card.select_one('.description, .desc, p, [class*="description"]')
        description = self.extract_text(desc_elem)
        
        # 提取赞助商
        sponsor_elem = card.select_one('.sponsors, [class*="sponsor"], [class*="partner"]')
        sponsors = self.extract_text(sponsor_elem)
        
        # 提取赛道/tracks
        tracks_elem = card.select_one('.tracks, [class*="track"], [class*="category"]')
        tracks = self.extract_text(tracks_elem)
        
        # 提取奖金
        prize_elem = card.select_one('.prize, .reward, [class*="prize"], [class*="reward"]')
        prize_text = self.extract_text(prize_elem)
        prize_amount, prize_currency = self._extract_prize(prize_text)
        
        # 提取日期
        date_elem = card.select_one('.date, .time, [class*="date"], [class*="time"]')
        date_text = self.extract_text(date_elem)
        deadline = self._parse_date_text(date_text)
        
        # 提取地点
        location_elem = card.select_one('.location, [class*="location"], [class*="venue"]')
        location = self.extract_text(location_elem)
        
        # 构建完整描述
        full_desc = description or ''
        if sponsors:
            full_desc += f" | 赞助商: {sponsors}"
        if tracks:
            full_desc += f" | 赛道: {tracks}"
        
        tags = ['web3', 'hackathon', 'ethglobal', 'ethereum']
        if 'online' in (location or '').lower() or 'virtual' in (location or '').lower():
            tags.append('online')
        else:
            tags.append('in-person')
        
        return self.create_activity(
            url=link,
            title=title,
            description=full_desc.strip(),
            prize_amount=prize_amount,
            prize_currency=prize_currency or 'USD',
            deadline=deadline,
            location=location,
            tags=tags
        )
    
    async def scrape_immunefi(self) -> List[Activity]:
        """
        爬取Immunefi漏洞赏金
        Validates: Requirements 9.4
        """
        try:
            html = await self.fetch_page(self.source_url)
            if not html:
                return []
            
            soup = self.parse_html(html)
            if not soup:
                return []
            
            activities = []
            
            # Immunefi赏金项目选择器
            cards = soup.select('.bounty-card, .program-card, [class*="bounty"], [class*="program"], article, tr')
            
            for card in cards:
                try:
                    activity = self._parse_immunefi_card(card)
                    if activity:
                        activities.append(activity)
                except Exception as e:
                    logger.warning(f"Error parsing Immunefi card: {e}")
                    continue
            
            logger.info(f"Scraped {len(activities)} bounties from Immunefi")
            return activities
            
        except Exception as e:
            logger.error(f"Error scraping Immunefi: {e}")
            return []
    
    def _parse_immunefi_card(self, card) -> Optional[Activity]:
        """
        解析Immunefi漏洞赏金卡片
        提取最高奖金和项目类型（DeFi、NFT等）
        """
        # 提取项目名称
        title_elem = card.select_one('h2, h3, h4, .title, [class*="title"], [class*="name"]')
        title = self.extract_text(title_elem)
        if not title:
            return None
        
        # 提取链接
        link_elem = card.select_one('a[href]')
        link = self.extract_attr(link_elem, 'href')
        if link and not link.startswith('http'):
            link = f"https://immunefi.com{link}"
        if not link:
            return None
        
        # 提取描述
        desc_elem = card.select_one('.description, .desc, p, [class*="description"]')
        description = self.extract_text(desc_elem)
        
        # 提取最高奖金
        max_bounty_elem = card.select_one('.max-bounty, [class*="max"], [class*="reward"], [class*="bounty"]')
        max_bounty_text = self.extract_text(max_bounty_elem)
        prize_amount, prize_currency = self._extract_prize(max_bounty_text)
        
        # 提取项目类型（DeFi、NFT、Bridge等）
        type_elem = card.select_one('.type, .category, [class*="type"], [class*="category"]')
        project_type = self.extract_text(type_elem)
        
        # 提取资产范围
        assets_elem = card.select_one('.assets, [class*="asset"], [class*="scope"]')
        assets = self.extract_text(assets_elem)
        
        # 提取TVL或其他指标
        tvl_elem = card.select_one('.tvl, [class*="tvl"], [class*="value"]')
        tvl = self.extract_text(tvl_elem)
        
        # 构建完整描述
        full_desc = description or ''
        if max_bounty_text:
            full_desc += f" | 最高奖金: {max_bounty_text}"
        if project_type:
            full_desc += f" | 类型: {project_type}"
        if assets:
            full_desc += f" | 资产范围: {assets}"
        if tvl:
            full_desc += f" | TVL: {tvl}"
        
        # 根据项目类型添加标签
        tags = ['web3', 'bounty', 'security', 'immunefi']
        if project_type:
            project_type_lower = project_type.lower()
            if 'defi' in project_type_lower:
                tags.append('defi')
            if 'nft' in project_type_lower:
                tags.append('nft')
            if 'bridge' in project_type_lower:
                tags.append('bridge')
            if 'dao' in project_type_lower:
                tags.append('dao')
        
        return self.create_activity(
            url=link,
            title=f"{title} Bug Bounty",
            description=full_desc.strip(),
            prize_amount=prize_amount,
            prize_currency=prize_currency or 'USD',
            prize_description=max_bounty_text,
            tags=tags
        )
