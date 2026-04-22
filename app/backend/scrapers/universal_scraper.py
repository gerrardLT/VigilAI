"""
VigilAI 通用Firecrawl爬虫
使用Firecrawl抓取任意网站，通过规则提取活动信息

适用于:
- 没有专门爬虫的网站
- 结构复杂的网站
- 需要JS渲染的网站
"""

import logging
import re
from typing import List, Optional
from datetime import datetime
from dateutil import parser as date_parser

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scrapers.firecrawl_scraper import FirecrawlScraper
from models import Activity
from config import FETCH_DETAIL_CONTENT, DETAIL_FETCH_MAX_COUNT, DETAIL_FETCH_DELAY
from utils.content_cleaning import build_description_from_text, looks_like_invalid_activity_candidate

logger = logging.getLogger(__name__)


class UniversalScraper(FirecrawlScraper):
    """
    通用Firecrawl爬虫
    使用Firecrawl抓取页面内容，然后通过规则提取活动信息
    """
    
    ACTIVITY_KEYWORDS = [
        'hackathon', 'competition', 'contest', 'challenge',
        'airdrop', 'bounty', 'grant', 'prize', 'reward',
        '黑客松', '竞赛', '比赛', '空投', '赏金', '奖金',
        '活动', '大赛', '挑战', '招募', '计划', '激励',
        '征集', '创新', '开发者', '训练营', '工作坊',
        '峰会', '论坛', '沙龙',
    ]
    
    DATE_KEYWORDS = [
        'deadline', 'ends', 'due', 'until', 'before',
        '截止', '结束', '报名',
    ]
    
    def __init__(self, source_id: str, source_config: dict):
        super().__init__(source_id, source_config)
        # 是否抓取详情页内容（可通过配置或参数控制）
        self.fetch_details = source_config.get('fetch_details', FETCH_DETAIL_CONTENT)
        self.detail_max_count = source_config.get('detail_max_count', DETAIL_FETCH_MAX_COUNT)
        self.detail_delay = source_config.get('detail_delay', DETAIL_FETCH_DELAY)
    
    async def scrape(self) -> List[Activity]:
        """抓取并解析活动"""
        result = await self.scrape_url(self.source_url)
        if not result:
            return []
        
        markdown = result.get('markdown', '')
        html = result.get('html', '')
        
        activities = self._extract_activities(markdown, html)
        
        # 如果启用了详情抓取，为活动补充详细内容
        if self.fetch_details and activities:
            logger.info(f"Fetching detail content for {self.source_name}...")
            activities = await self.enrich_activities_with_details(
                activities,
                max_count=self.detail_max_count,
                delay_between=self.detail_delay
            )
        
        return activities
    
    def _extract_activities(self, markdown: str, html: str) -> List[Activity]:
        """从内容中提取活动信息"""
        activities = []
        
        # 根据来源URL选择合适的解析方法
        source_url_lower = self.source_url.lower()
        
        # 华为开发者
        if 'developer.huawei.com' in source_url_lower:
            activities = self._extract_huawei_style(markdown)
            if activities:
                return activities
        
        # DoraHacks
        if 'dorahacks.io' in source_url_lower:
            activities = self._extract_dorahacks_style(markdown)
            if activities:
                return activities
        
        # MLH
        if 'mlh.io' in source_url_lower or 'mlh.com' in source_url_lower:
            activities = self._extract_mlh_style(markdown)
            if activities:
                return activities
        
        # Hackathon.com
        if 'hackathon.com' in source_url_lower:
            activities = self._extract_hackathon_com_style(markdown)
            if activities:
                return activities
        
        # ETHGlobal
        if 'ethglobal.com' in source_url_lower:
            activities = self._extract_ethglobal_style(markdown)
            if activities:
                return activities
        
        # Devpost
        if 'devpost.com' in source_url_lower:
            activities = self._extract_devpost_style(markdown)
            if activities:
                return activities
        
        # HackQuest
        if 'hackquest.io' in source_url_lower:
            activities = self._extract_hackquest_style(markdown)
            if activities:
                return activities
        
        # Taikai
        if 'taikai.network' in source_url_lower:
            activities = self._extract_taikai_style(markdown)
            if activities:
                return activities
        
        # Unstop
        if 'unstop.com' in source_url_lower:
            activities = self._extract_unstop_style(markdown)
            if activities:
                return activities
        
        # Immunefi
        if 'immunefi.com' in source_url_lower:
            activities = self._extract_immunefi_style(markdown)
            if activities:
                return activities
        
        # Airdrops.io
        if 'airdrops.io' in source_url_lower:
            activities = self._extract_airdrops_style(markdown)
            if activities:
                return activities
        
        # 通用方法：尝试所有解析器
        # 首先尝试提取DoraHacks风格的复杂链接
        dorahacks_activities = self._extract_dorahacks_style(markdown)
        if dorahacks_activities:
            return dorahacks_activities
        
        # 尝试提取Hackathon.com风格的活动
        hackathon_com_activities = self._extract_hackathon_com_style(markdown)
        if hackathon_com_activities:
            return hackathon_com_activities
        
        # 尝试提取MLH风格的活动
        mlh_activities = self._extract_mlh_style(markdown)
        if mlh_activities:
            return mlh_activities
        
        # 尝试提取通用列表项活动
        list_activities = self._extract_list_items(markdown)
        if list_activities:
            return list_activities
        
        # 回退到原有的链接提取方式
        links = self.extract_links(markdown, self.source_url)
        
        for link in links:
            title = link['text']
            url = link['url']
            
            if self._is_navigation_link(title, url):
                continue
            
            if self._looks_like_activity(title):
                activity = self._create_activity_from_link(title, url, markdown)
                if activity:
                    activities.append(activity)
        
        if not activities:
            activities = self._extract_from_structure(markdown)
        
        return activities
    
    def _extract_ethglobal_style(self, markdown: str) -> List[Activity]:
        """提取ETHGlobal风格的活动"""
        activities = []
        
        # ETHGlobal格式: **活动名称** \\ \\ 地点类型 \\ \\ Apply to Attend](URL)
        # 查找所有包含**标题**的链接
        pattern = r'\*\*([^*]+)\*\*\s*\\\\[^]]*?\]\((https://ethglobal\.com/events/[^)]+)\)'
        matches = re.findall(pattern, markdown, re.DOTALL)
        
        seen_urls = set()
        for title, url in matches:
            # 去重
            if url in seen_urls:
                continue
            seen_urls.add(url)
            
            # 清理标题
            title = title.strip()
            
            activity = self.create_activity(
                url=url,
                title=title,
                description=f"ETHGlobal活动: {title}",
                tags=['hackathon', 'ethereum', 'web3'],
            )
            
            if activity:
                activities.append(activity)
        
        # 备用方法：直接查找ethglobal.com/events/链接
        if not activities:
            url_pattern = r'https://ethglobal\.com/events/([a-zA-Z0-9_-]+)'
            urls = re.findall(url_pattern, markdown)
            
            seen_slugs = set()
            for slug in urls:
                if slug in seen_slugs:
                    continue
                seen_slugs.add(slug)
                
                url = f"https://ethglobal.com/events/{slug}"
                
                # 从上下文提取标题
                title = self._extract_ethglobal_title(markdown, url)
                if not title:
                    title = slug.replace('-', ' ').title()
                
                activity = self.create_activity(
                    url=url,
                    title=title,
                    description=f"ETHGlobal活动: {title}",
                    tags=['hackathon', 'ethereum', 'web3'],
                )
                
                if activity:
                    activities.append(activity)
        
        return activities
    
    def _extract_ethglobal_title(self, content: str, url: str) -> Optional[str]:
        """从ETHGlobal内容中提取标题"""
        pos = content.find(url)
        if pos == -1:
            return None
        
        # 向前查找**标题**
        before = content[max(0, pos-300):pos]
        
        # 查找最后一个**标题**
        title_match = re.search(r'\*\*([^*]+)\*\*', before)
        if title_match:
            return title_match.group(1).strip()
        
        return None
    
    def _extract_devpost_style(self, markdown: str) -> List[Activity]:
        """提取Devpost风格的活动"""
        activities = []
        
        # Devpost格式: **活动名称** \\ \\ 剩余时间 \\ \\ 地点 \\ \\ 奖金 \\ \\ 参与人数](URL)
        # 查找所有devpost.com的hackathon链接
        pattern = r'\*\*([^*]+)\*\*\s*\\\\[^]]*?\]\((https://[a-zA-Z0-9_-]+\.devpost\.com/[^)]*)\)'
        matches = re.findall(pattern, markdown, re.DOTALL)
        
        seen_urls = set()
        for title, url in matches:
            # 去重
            if url in seen_urls:
                continue
            seen_urls.add(url)
            
            # 清理标题
            title = title.strip()
            
            # 跳过纯数字（参与人数）
            if re.match(r'^\d+$', title):
                continue
            
            # 提取奖金
            prize_amount, prize_currency = self._extract_devpost_prize(markdown, url)
            
            activity = self.create_activity(
                url=url,
                title=title,
                description=f"Devpost黑客松: {title}",
                prize_amount=prize_amount,
                prize_currency=prize_currency,
                tags=['hackathon'],
            )
            
            if activity:
                activities.append(activity)
        
        return activities
    
    def _extract_devpost_prize(self, content: str, url: str) -> tuple:
        """从Devpost内容中提取奖金"""
        pos = content.find(url)
        if pos == -1:
            return None, 'USD'
        
        # 查找URL前面的内容
        before = content[max(0, pos-500):pos]
        
        # 查找奖金模式 (如 $100,000 in prizes)
        prize_pattern = r'\$([\d,]+)\s*(?:in\s*prizes)?'
        match = re.search(prize_pattern, before, re.IGNORECASE)
        
        if match:
            try:
                amount = float(match.group(1).replace(',', ''))
                return amount, 'USD'
            except ValueError:
                pass
        
        return None, 'USD'
    
    def _extract_dorahacks_style(self, markdown: str) -> List[Activity]:
        """
        提取DoraHacks风格的黑客松列表
        格式: - [![](图片)\\...\\标题\\...\\🏆 Prize Pool金额](URL)
        """
        activities = []
        
        # 匹配DoraHacks的复杂链接格式
        # 格式: - [![](...内容...🏆 Prize Pool金额](URL)
        pattern = r'-\s*\[!\[\]\([^)]+\)\\\\[^]]*?\\\\([^\\]+?)\\\\[^]]*?(?:🏆\s*Prize\s*Pool\s*([\d,]+)\s*(\w+))?\]\(([^)]+)\)'
        
        matches = re.findall(pattern, markdown, re.DOTALL)
        
        for match in matches:
            title = match[0].strip() if match[0] else ""
            prize_str = match[1].replace(',', '') if match[1] else ""
            currency = match[2] if match[2] else "USD"
            url = match[3].strip() if match[3] else ""
            
            if not title or not url:
                continue
            
            # 跳过非活动链接
            if 'cdn.dorahacks.io' in url or url.endswith(('.png', '.jpg', '.webp')):
                continue
            
            # 解析奖金
            prize_amount = None
            if prize_str:
                try:
                    prize_amount = float(prize_str)
                except ValueError:
                    pass
            
            # 从完整匹配中提取更多信息
            full_text = match[0] if isinstance(match, tuple) else str(match)
            
            # 提取状态
            status = "upcoming"
            if "Ongoing" in markdown[:markdown.find(url)] if url in markdown else "":
                status = "active"
            elif "Ended" in markdown[:markdown.find(url)] if url in markdown else "":
                status = "ended"
            
            activity = self.create_activity(
                url=url,
                title=title,
                description=f"DoraHacks黑客松活动",
                prize_amount=prize_amount,
                prize_currency=currency,
                status=status,
                tags=self._extract_tags(title),
            )
            
            if activity:
                activities.append(activity)
        
        # 如果正则没匹配到，尝试更宽松的方式
        if not activities:
            activities = self._extract_dorahacks_loose(markdown)
        
        return activities
    
    def _extract_dorahacks_loose(self, markdown: str) -> List[Activity]:
        """
        宽松方式提取DoraHacks活动
        直接查找dorahacks.io/hackathon/开头的URL，并从上下文提取标题
        """
        activities = []
        
        # 查找所有dorahacks hackathon链接
        url_pattern = r'https://dorahacks\.io/hackathon/([a-zA-Z0-9_-]+)'
        
        # 按列表项分割内容
        items = re.split(r'\n-\s*\[', markdown)
        
        for item in items[1:]:  # 跳过第一个（不是列表项）
            # 查找URL
            url_match = re.search(url_pattern, item)
            if not url_match:
                continue
            
            slug = url_match.group(1)
            url = f"https://dorahacks.io/hackathon/{slug}"
            
            # 从列表项中提取标题
            title = self._extract_title_from_dorahacks_item(item)
            if not title:
                title = slug.replace('-', ' ').title()
            
            # 提取奖金
            prize_amount, prize_currency = self._extract_prize_from_item(item)
            
            # 提取状态
            status = "upcoming"
            item_lower = item.lower()
            if "ongoing" in item_lower:
                status = "active"
            elif "ended" in item_lower:
                status = "ended"
            
            # 提取地点
            location = "Virtual"
            if "virtual" not in item_lower:
                # 尝试提取地点
                loc_match = re.search(r'\\\\([^\\]+(?:,\s*[^\\]+)?(?:,\s*[A-Z][a-z]+)+)\\\\', item)
                if loc_match:
                    location = loc_match.group(1).strip()
            
            activity = self.create_activity(
                url=url,
                title=title,
                description=f"DoraHacks黑客松: {title}",
                prize_amount=prize_amount,
                prize_currency=prize_currency,
                status=status,
                location=location,
                tags=['hackathon', 'web3'],
            )
            
            if activity:
                activities.append(activity)
        
        return activities
    
    def _extract_title_from_dorahacks_item(self, item: str) -> Optional[str]:
        """
        从DoraHacks列表项中提取标题
        标题通常在数字（参与人数）之后，Virtual/地点之前
        格式: ...\\数字\\\\标题\\\\Virtual...
        """
        # 按\\\\分割
        parts = item.split('\\\\')
        
        # 查找标题：通常在数字之后，位置/Virtual之前
        found_number = False
        for i, part in enumerate(parts):
            part = part.strip()
            
            # 跳过空白
            if not part:
                continue
            
            # 跳过图片
            if part.startswith('!') or part.startswith('!['):
                continue
            
            # 跳过CDN链接
            if 'cdn.dorahacks.io' in part or part.endswith(('.png', '.jpg', '.webp')):
                continue
            
            # 检查是否是纯数字（参与人数）
            if re.match(r'^\d+$', part):
                found_number = True
                continue
            
            # 如果已经找到数字，下一个非空、非Virtual、非地点的就是标题
            if found_number:
                # 跳过Virtual
                if part.lower() == 'virtual':
                    continue
                # 跳过地点（包含逗号的通常是地点）
                if ',' in part and any(c.isupper() for c in part):
                    continue
                # 跳过标签（通常是单个小写词）
                if part.islower() and len(part) < 20:
                    continue
                # 跳过奖金信息
                if '🏆' in part or 'prize' in part.lower():
                    continue
                # 跳过包含](的格式错误
                if '](http' in part:
                    continue
                
                # 这应该是标题
                if len(part) >= 5:
                    # 清理标题
                    title = part.replace('\\|', ' - ').replace('\\', '').strip()
                    # 移除末尾的奖金信息
                    title = re.sub(r'\s*🏆.*$', '', title)
                    title = re.sub(r'\s*\]\(https?://[^)]+\)$', '', title)
                    if title and len(title) >= 3:
                        return title
        
        # 备用方案：查找包含Hackathon关键词的行
        for part in parts:
            part = part.strip()
            # 跳过图片
            if part.startswith('!') or 'cdn.dorahacks.io' in part:
                continue
            # 跳过包含](的格式错误
            if '](http' in part and not any(kw in part.lower() for kw in ['hackathon', 'hack']):
                continue
            if any(kw in part.lower() for kw in ['hackathon', 'hack', 'challenge', 'bounty', 'grant']):
                if len(part) >= 5 and len(part) <= 150:
                    title = part.replace('\\|', ' - ').replace('\\', '').strip()
                    # 移除末尾的奖金信息
                    title = re.sub(r'\s*🏆.*$', '', title)
                    title = re.sub(r'\s*\]\(https?://[^)]+\)$', '', title)
                    if title and len(title) >= 3:
                        return title
        
        return None
    
    def _extract_prize_from_item(self, item: str) -> tuple:
        """从列表项中提取奖金信息"""
        # 查找奖金模式
        prize_pattern = r'(?:Prize\s*Pool|🏆)[^\d]*([\d,]+)\s*(USD|USDT|ETH|BTC)?'
        match = re.search(prize_pattern, item, re.IGNORECASE)
        
        if match:
            try:
                amount = float(match.group(1).replace(',', ''))
                currency = match.group(2) or 'USD'
                return amount, currency
            except ValueError:
                pass
        
        return None, 'USD'
    
    def _extract_mlh_style(self, markdown: str) -> List[Activity]:
        """提取MLH风格的活动列表"""
        activities = []
        
        # MLH格式: [地点\\...\\**活动名称**\\...](URL)
        # 查找所有包含**标题**的链接，URL不是图片
        # 使用更精确的模式
        pattern = r'\[([^\]]*?\*\*([^*]+)\*\*[^\]]*?)\]\((https?://[^)]+)\)'
        matches = re.findall(pattern, markdown, re.DOTALL)
        
        seen_urls = set()
        for full_text, title, url in matches:
            # 跳过图片链接
            if url.endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg')):
                continue
            
            # 跳过CDN链接
            if 'mlhusercontent.com' in url:
                continue
            
            # 跳过导航链接
            if self._is_navigation_link(title, url):
                continue
            
            # 去重
            if url in seen_urls:
                continue
            seen_urls.add(url)
            
            # 清理标题 - 移除可能混入的其他内容
            title = title.strip()
            # 如果标题包含换行或多个活动信息，只取第一部分
            if '\\\\' in title:
                title = title.split('\\\\')[0].strip()
            # 移除图片标记
            title = re.sub(r'!\[[^\]]*\]\([^)]+\)', '', title)
            # 移除日期格式
            title = re.sub(r'[A-Z]{3}\s+\d{1,2}\s*-\s*\d{1,2}', '', title)
            # 移除地点格式
            title = re.sub(r'[A-Z][a-z]+,\s*[A-Z]{2}', '', title)
            # 移除In-Person/Digital/Hybrid
            title = re.sub(r'In-Person|Digital|Hybrid', '', title)
            # 移除多余的空白和换行
            title = re.sub(r'\s+', ' ', title)
            title = title.strip()
            
            # 如果清理后标题为空、太短或包含异常字符，跳过
            if not title or len(title) < 3:
                continue
            # 跳过包含markdown格式残留的标题
            if '](http' in title or '![' in title:
                continue
            # 跳过以反斜杠开头的标题（包括\\和\n）
            if title[0] == '\\':
                continue
            # 跳过包含日期格式残留的标题
            if re.match(r'^[A-Z]{3}\s+\d', title):
                continue
            
            # 从full_text中提取日期和地点
            location = "Virtual"
            date_str = None
            
            parts = full_text.split('\\\\')
            for part in parts:
                part = part.strip()
                # 查找日期 (如 JUN 27 - 29, APR 26 - 27)
                if re.match(r'^[A-Z]{3}\s+\d{1,2}\s*-\s*\d{1,2}$', part):
                    date_str = part
                # 查找地点 (包含逗号的通常是地点)
                elif ',' in part and not part.startswith('!'):
                    location = part
                # 查找类型
                elif part in ['In-Person', 'Digital', 'Hybrid']:
                    if part == 'Digital':
                        location = "Virtual"
            
            activity = self.create_activity(
                url=url,
                title=title,
                description=f"MLH黑客松: {title}",
                location=location,
                tags=['hackathon', 'student', 'mlh'],
            )
            
            if activity:
                activities.append(activity)
        
        # 如果上面的方法没有找到活动，尝试备用方法
        if not activities:
            activities = self._extract_mlh_fallback(markdown)
        
        return activities
    
    def _extract_mlh_fallback(self, markdown: str) -> List[Activity]:
        """MLH备用提取方法 - 直接查找活动URL"""
        activities = []
        
        # 查找所有非图片的外部链接
        # MLH活动链接通常指向各个黑客松的官网
        link_pattern = r'\]\((https?://(?!mlhusercontent)[^)]+)\)'
        urls = re.findall(link_pattern, markdown)
        
        seen_urls = set()
        for url in urls:
            # 跳过图片
            if url.endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg')):
                continue
            
            # 跳过MLH内部链接
            if 'mlh.com' in url or 'mlh.io' in url:
                continue
            
            # 去重
            if url in seen_urls:
                continue
            seen_urls.add(url)
            
            # 从URL前面的内容提取标题
            title = self._extract_mlh_title_before_url(markdown, url)
            if not title:
                continue
            
            # 提取地点
            location = self._extract_mlh_location_before_url(markdown, url)
            
            activity = self.create_activity(
                url=url,
                title=title,
                description=f"MLH黑客松: {title}",
                location=location,
                tags=['hackathon', 'student', 'mlh'],
            )
            
            if activity:
                activities.append(activity)
        
        return activities
    
    def _extract_mlh_title_before_url(self, content: str, url: str) -> Optional[str]:
        """从MLH内容中提取URL前面的标题"""
        pos = content.find(url)
        if pos == -1:
            return None
        
        # 向前查找**标题**格式
        before = content[max(0, pos-500):pos]
        
        # 查找最后一个**标题**
        title_match = re.search(r'\*\*([^*]+)\*\*', before)
        if title_match:
            title = title_match.group(1).strip()
            
            # 清理标题中的格式残留
            # 移除反斜杠和换行符
            title = re.sub(r'\\+n?', '', title)
            title = title.strip()
            
            # 过滤无效标题
            if not title:
                return None
            # 标题以反斜杠开头
            if title.startswith('\\'):
                return None
            # 标题包含日期格式（如"FEB 08 - 09"）但没有实际名称
            if re.match(r'^[A-Z]{3}\s+\d+', title):
                return None
            # 标题太短
            if len(title) < 3:
                return None
            
            return title
        
        return None
    
    def _extract_mlh_location_before_url(self, content: str, url: str) -> str:
        """从MLH内容中提取URL前面的地点"""
        pos = content.find(url)
        if pos == -1:
            return "Virtual"
        
        before = content[max(0, pos-500):pos]
        
        # 查找地点（包含逗号的行）
        parts = before.split('\\\\')
        for part in reversed(parts):
            part = part.strip()
            if ',' in part and not part.startswith('!') and len(part) < 100:
                return part
        
        # 检查是否是Digital
        if 'Digital' in before:
            return "Virtual"
        
        return "Virtual"
    
    def _extract_hackathon_com_style(self, markdown: str) -> List[Activity]:
        """提取Hackathon.com风格的活动"""
        activities = []
        
        # Hackathon.com格式: [活动名称](https://www.hackathon.com/event/...)
        pattern = r'\[([^\]]+)\]\((https://www\.hackathon\.com/event/[^)]+)\)'
        matches = re.findall(pattern, markdown)
        
        seen_urls = set()
        for title, url in matches:
            # 跳过"More details"和"See event page"
            if title.lower() in ['more details', 'see event page']:
                continue
            
            # 去重
            if url in seen_urls:
                continue
            seen_urls.add(url)
            
            # 清理标题
            title = title.strip()
            
            activity = self.create_activity(
                url=url,
                title=title,
                description=f"Hackathon.com活动: {title}",
                tags=['hackathon'],
            )
            
            if activity:
                activities.append(activity)
        
        return activities
    
    def _extract_list_items(self, markdown: str) -> List[Activity]:
        """从Markdown列表项中提取活动"""
        activities = []
        
        # 匹配列表项中的链接
        list_pattern = r'^[-*]\s+\[([^\]]+)\]\(([^)]+)\)'
        matches = re.findall(list_pattern, markdown, re.MULTILINE)
        
        for title, url in matches:
            # 清理标题
            title = re.sub(r'!\[\]\([^)]+\)', '', title).strip()
            
            if not title or len(title) < 3:
                continue

            if looks_like_invalid_activity_candidate(title, url, markdown, source_id=self.source_id):
                continue

            if self._is_navigation_link(title, url):
                continue
            
            # 跳过图片链接
            if url.endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg')):
                continue
            
            if self._looks_like_activity(title) or 'hackathon' in url.lower():
                activity = self._create_activity_from_link(title, url, markdown)
                if activity:
                    activities.append(activity)
        
        return activities
    
    def _is_navigation_link(self, title: str, url: str) -> bool:
        """判断是否是导航链接"""
        nav_keywords = [
            'home', 'about', 'contact', 'login', 'signup', 'register',
            'faq', 'help', 'terms', 'privacy', 'blog', 'news',
            '首页', '关于', '联系', '登录', '注册', '帮助',
        ]
        title_lower = title.lower()
        return (
            any(kw in title_lower for kw in nav_keywords)
            or len(title) < 3
            or looks_like_invalid_activity_candidate(title, url, source_id=self.source_id)
        )
    
    def _looks_like_activity(self, title: str) -> bool:
        """判断标题是否像活动"""
        title_lower = title.lower()
        
        if any(kw in title_lower for kw in self.ACTIVITY_KEYWORDS):
            return True
        
        if re.search(r'202[4-9]', title):
            return True
        
        if re.search(r'\$[\d,]+|\d+k|\d+万', title_lower):
            return True
        
        return False

    def _create_activity_from_link(
        self, 
        title: str, 
        url: str, 
        context: str
    ) -> Optional[Activity]:
        """从链接创建活动"""
        raw_context = self._extract_context(title, context)
        description = build_description_from_text(raw_context, title=title, max_length=500) or raw_context
        if looks_like_invalid_activity_candidate(title, url, description, source_id=self.source_id):
            return None
        deadline = self._extract_deadline(description)
        prize_amount, prize_currency = self._extract_prize(description)
        
        return self.create_activity(
            url=url,
            title=title,
            description=description[:500] if description else None,
            deadline=deadline,
            prize_amount=prize_amount,
            prize_currency=prize_currency,
            tags=self._extract_tags(title + ' ' + (description or '')),
        )
    
    def _extract_context(self, title: str, content: str, chars: int = 300) -> str:
        """提取标题周围的上下文"""
        pos = content.find(title)
        if pos == -1:
            return ""
        
        start = max(0, pos - 50)
        end = min(len(content), pos + len(title) + chars)
        context = content[start:end]
        
        context = re.sub(r'\s+', ' ', context).strip()
        return context
    
    def _extract_deadline(self, text: str) -> Optional[datetime]:
        """从文本中提取截止日期"""
        if not text:
            return None
        
        patterns = [
            r'deadline[:\s]+([A-Za-z]+\s+\d{1,2},?\s+\d{4})',
            r'ends?\s+([A-Za-z]+\s+\d{1,2},?\s+\d{4})',
            r'until\s+([A-Za-z]+\s+\d{1,2},?\s+\d{4})',
            r'(\d{4}[-/]\d{1,2}[-/]\d{1,2})',
            r'(\d{1,2}[-/]\d{1,2}[-/]\d{4})',
            r'截止[：:]\s*(\d{4}年\d{1,2}月\d{1,2}日)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    return date_parser.parse(match.group(1), fuzzy=True)
                except Exception:
                    continue
        
        return None
    
    def _extract_prize(self, text: str) -> tuple:
        """从文本中提取奖金信息"""
        if not text:
            return None, 'USD'
        
        patterns = [
            (r'\$\s*([\d,]+(?:\.\d{2})?)\s*(?:k|K)?', 'USD'),
            (r'([\d,]+)\s*(?:USD|usd)', 'USD'),
            (r'([\d,]+)\s*(?:USDT|usdt)', 'USDT'),
            (r'([\d,]+)\s*(?:ETH|eth)', 'ETH'),
            (r'([\d,]+)\s*万', 'CNY'),
            (r'¥\s*([\d,]+)', 'CNY'),
        ]
        
        for pattern, currency in patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    amount_str = match.group(1).replace(',', '')
                    amount = float(amount_str)
                    
                    if 'k' in text[match.end():match.end()+2].lower():
                        amount *= 1000
                    if currency == 'CNY' and '万' in text:
                        amount *= 10000
                    
                    return amount, currency
                except Exception:
                    continue
        
        return None, 'USD'

    def _extract_tags(self, text: str) -> List[str]:
        """从文本中提取标签"""
        tags = []
        text_lower = text.lower()
        
        tag_keywords = {
            'hackathon': ['hackathon', '黑客松'],
            'ai': ['ai', 'artificial intelligence', '人工智能', 'machine learning'],
            'web3': ['web3', 'blockchain', 'crypto', '区块链'],
            'defi': ['defi', 'decentralized finance'],
            'nft': ['nft'],
            'gaming': ['game', 'gaming', '游戏'],
            'mobile': ['mobile', 'ios', 'android'],
            'cloud': ['cloud', 'aws', 'azure', 'gcp'],
            'security': ['security', 'bounty', '安全'],
            'data': ['data', 'analytics', '数据'],
        }
        
        for tag, keywords in tag_keywords.items():
            if any(kw in text_lower for kw in keywords):
                tags.append(tag)
        
        return tags[:5]
    
    def _extract_from_structure(self, markdown: str) -> List[Activity]:
        """从Markdown结构中提取活动"""
        activities = []
        
        sections = re.split(r'^#{1,3}\s+', markdown, flags=re.MULTILINE)
        
        for section in sections[1:]:
            lines = section.strip().split('\n')
            if not lines:
                continue
            
            title = lines[0].strip()
            if not title or len(title) < 5:
                continue
            
            if not self._looks_like_activity(title):
                continue
            
            content = '\n'.join(lines[1:])
            
            urls = re.findall(r'https?://[^\s\)]+', content)
            url = urls[0] if urls else self.source_url
            
            activity = self._create_activity_from_link(title, url, content)
            if activity:
                activities.append(activity)
        
        return activities
    
    def _extract_hackquest_style(self, markdown: str) -> List[Activity]:
        """
        提取HackQuest风格的活动
        格式: [**标题** \\ ... \\ Total Prize \\ 金额 USD \\ ...](URL)
        """
        activities = []
        
        # 匹配HackQuest链接格式
        # [**标题** \\ ... ](https://www.hackquest.io/hackathons/xxx)
        # 使用[\s\S]*?来匹配包括换行在内的任意字符
        pattern = r'\[\*\*([^*]+)\*\*[\s\S]*?\]\((https://www\.hackquest\.io/hackathons/[a-zA-Z0-9_%-]+)\)'
        matches = re.findall(pattern, markdown, re.DOTALL)
        
        seen_urls = set()
        for title, url in matches:
            # 跳过图片链接
            if url.endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg')):
                continue
            
            # 跳过assets链接
            if 'assets.hackquest.io' in url:
                continue
            
            # 去重
            if url in seen_urls:
                continue
            seen_urls.add(url)
            
            # 清理标题
            title = title.strip()
            
            # 跳过过短的标题
            if len(title) < 3:
                continue
            
            # 从URL前面的内容提取奖金和状态
            prize_amount, prize_currency = self._extract_hackquest_prize(markdown, url)
            status = self._extract_hackquest_status(markdown, url)
            location = self._extract_hackquest_location(markdown, url)
            
            activity = self.create_activity(
                url=url,
                title=title,
                description=f"HackQuest黑客松: {title}",
                prize_amount=prize_amount,
                prize_currency=prize_currency,
                status=status,
                location=location,
                tags=['hackathon', 'web3'],
            )
            
            if activity:
                activities.append(activity)
        
        return activities
    
    def _extract_hackquest_prize(self, content: str, url: str) -> tuple:
        """从HackQuest内容中提取奖金"""
        pos = content.find(url)
        if pos == -1:
            return None, 'USD'
        
        # 查找URL前面的内容
        before = content[max(0, pos-800):pos]
        
        # 查找奖金模式 (如 Total Prize \\ 18,000 USD)
        prize_pattern = r'Total\s*Prize\\+\s*([\d,]+)\s*(USD|USDT)?'
        match = re.search(prize_pattern, before, re.IGNORECASE)
        
        if match:
            try:
                amount = float(match.group(1).replace(',', ''))
                currency = match.group(2) or 'USD'
                return amount, currency
            except ValueError:
                pass
        
        return None, 'USD'
    
    def _extract_hackquest_status(self, content: str, url: str) -> str:
        """从HackQuest内容中提取状态"""
        pos = content.find(url)
        if pos == -1:
            return "upcoming"
        
        before = content[max(0, pos-500):pos].lower()
        
        if 'live' in before:
            return "active"
        elif 'ended' in before:
            return "ended"
        elif 'voting' in before:
            return "voting"
        elif 'upcoming' in before:
            return "upcoming"
        
        return "upcoming"
    
    def _extract_hackquest_location(self, content: str, url: str) -> str:
        """从HackQuest内容中提取地点"""
        pos = content.find(url)
        if pos == -1:
            return "Online"
        
        before = content[max(0, pos-500):pos].upper()
        
        if 'HYBRID' in before:
            return "Hybrid"
        elif 'ONLINE' in before:
            return "Online"
        
        return "Online"
    
    def _extract_taikai_style(self, markdown: str) -> List[Activity]:
        """
        提取Taikai风格的活动
        格式: [图片...\\**标题** \\ ... \\ Prize \\ 金额$](URL)
        注意：Taikai的**标题**在链接内容的中间位置
        """
        activities = []
        
        # 匹配Taikai链接格式
        # **标题** ... ](https://taikai.network/en/.../hackathons/...)
        # 使用[\s\S]*?来匹配包括换行在内的任意字符
        # URL格式: https://taikai.network/en/org/hackathons/slug/
        pattern = r'\*\*([^*]+)\*\*[\s\S]*?\]\((https://taikai\.network/en/[a-zA-Z0-9_-]+/hackathons/[a-zA-Z0-9_-]+/?)\)'
        matches = re.findall(pattern, markdown, re.DOTALL)
        
        seen_urls = set()
        for title, url in matches:
            # 跳过图片链接
            if '_next/image' in url or url.endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg')):
                continue
            
            # 跳过CDN链接
            if 'taikai.azureedge.net' in url:
                continue
            
            # 去重
            if url in seen_urls:
                continue
            seen_urls.add(url)
            
            # 清理标题
            title = title.strip()
            
            # 跳过过短的标题
            if len(title) < 3:
                continue
            
            # 从URL前面的内容提取奖金
            prize_amount, prize_currency = self._extract_taikai_prize(markdown, url)
            
            # 提取标签
            tags = self._extract_taikai_tags(markdown, url)
            
            activity = self.create_activity(
                url=url,
                title=title,
                description=f"Taikai黑客松: {title}",
                prize_amount=prize_amount,
                prize_currency=prize_currency,
                location="Online",
                tags=['hackathon'] + tags,
            )
            
            if activity:
                activities.append(activity)
        
        return activities
    
    def _extract_taikai_prize(self, content: str, url: str) -> tuple:
        """从Taikai内容中提取奖金"""
        pos = content.find(url)
        if pos == -1:
            return None, 'USD'
        
        # 查找URL前面的内容
        before = content[max(0, pos-600):pos]
        
        # 查找奖金模式 (如 Prize \\ 15,000$ 或 Prize \\ 9,000€)
        prize_pattern = r'Prize\\+\s*([\d,]+)\s*(\$|€|EUR)?'
        match = re.search(prize_pattern, before, re.IGNORECASE)
        
        if match:
            try:
                amount = float(match.group(1).replace(',', ''))
                currency_symbol = match.group(2) if match.group(2) else '$'
                currency = 'EUR' if currency_symbol in ['€', 'EUR'] else 'USD'
                return amount, currency
            except ValueError:
                pass
        
        return None, 'USD'
        
        if match:
            try:
                amount = float(match.group(1).replace(',', ''))
                return amount, 'USD'
            except ValueError:
                pass
        
        return None, 'USD'
    
    def _extract_taikai_tags(self, content: str, url: str) -> List[str]:
        """从Taikai内容中提取标签"""
        pos = content.find(url)
        if pos == -1:
            return []
        
        before = content[max(0, pos-600):pos].lower()
        
        tags = []
        tag_map = {
            'blockchain': 'blockchain',
            'web3': 'web3',
            'fintech': 'fintech',
            'cryptocurrency': 'crypto',
            'artificial intelligence': 'ai',
            'gaming': 'gaming',
            'health': 'health',
            'education': 'education',
        }
        
        for keyword, tag in tag_map.items():
            if keyword in before:
                tags.append(tag)
        
        return tags[:3]
    
    def _extract_unstop_style(self, markdown: str) -> List[Activity]:
        """
        提取Unstop风格的活动
        格式: [**标题** \\ 组织 \\ ... \\ ![图片](图片URL) \\ ... \\ 时间](真正的URL)
        真正的URL在链接末尾，以数字ID结尾
        """
        activities = []
        
        # 先找到所有 unstop.com/hackathons 的 URL
        url_pattern = r'https://unstop\.com/hackathons/[^\s\)]+\d+'
        urls = re.findall(url_pattern, markdown)
        
        seen_urls = set()
        for url in urls:
            # 去重
            if url in seen_urls:
                continue
            seen_urls.add(url)
            
            pos = markdown.find(url)
            if pos == -1:
                continue
            
            # 向前查找 [**标题**
            before = markdown[max(0, pos-2000):pos]
            
            # 找到最后一个 [**
            last_bracket = before.rfind('[**')
            if last_bracket == -1:
                continue
            
            # 提取标题
            title_start = last_bracket + 3
            title_end = before.find('**', title_start)
            if title_end == -1:
                continue
            
            title = before[title_start:title_end]
            title = title.replace('\\|', '|').replace('\\', '').strip()
            
            # 跳过过短的标题
            if len(title) < 3:
                continue
            
            # 提取内容块（从 [** 到 URL）
            content_block = before[last_bracket:] + url
            
            # 从内容中提取奖金和地点
            prize_amount, prize_currency = self._extract_unstop_prize_from_block(content_block)
            location = self._extract_unstop_location_from_block(content_block)
            
            # 提取标签
            tags = self._extract_unstop_tags_from_block(content_block)
            
            activity = self.create_activity(
                url=url,
                title=title,
                description=f"Unstop黑客松: {title}",
                prize_amount=prize_amount,
                prize_currency=prize_currency,
                location=location,
                tags=['hackathon'] + tags,
            )
            
            if activity:
                activities.append(activity)
        
        return activities
    
    def _extract_unstop_prize_from_block(self, block: str) -> tuple:
        """从Unstop活动块中提取奖金"""
        # 查找奖金模式 (如 Prizes worth 40,000)
        prize_pattern = r'Prizes?\s*worth\s*([\d,]+)'
        match = re.search(prize_pattern, block, re.IGNORECASE)
        
        if match:
            try:
                amount = float(match.group(1).replace(',', ''))
                return amount, 'INR'  # Unstop主要是印度平台，默认INR
            except ValueError:
                pass
        
        return None, 'INR'
    
    def _extract_unstop_location_from_block(self, block: str) -> str:
        """从Unstop活动块中提取地点"""
        # 检查是否是线上
        if 'online' in block.lower():
            return "Online"
        
        # 查找地点 (如 Hyderabad, Telangana, India)
        loc_pattern = r'([A-Za-z\s]+,\s*[A-Za-z\s]+,\s*India)'
        match = re.search(loc_pattern, block)
        if match:
            return match.group(1).strip()
        
        return "India"
    
    def _extract_unstop_tags_from_block(self, block: str) -> List[str]:
        """从Unstop活动块中提取标签"""
        block_lower = block.lower()
        
        tags = []
        tag_map = {
            'data analytics': 'data',
            'data science': 'data',
            'programming': 'programming',
            'ai': 'ai',
            'machine learning': 'ai',
            'web development': 'web',
            'mobile': 'mobile',
            'blockchain': 'blockchain',
            'cybersecurity': 'security',
            'ctf': 'security',
        }
        
        for keyword, tag in tag_map.items():
            if keyword in block_lower and tag not in tags:
                tags.append(tag)
        
        return tags[:3]

    
    def _extract_huawei_style(self, markdown: str) -> List[Activity]:
        """
        提取华为开发者风格的活动
        从整个页面提取所有活动相关链接
        """
        activities = []
        seen_titles = set()
        seen_urls = set()
        
        # 1. 首先提取精选活动部分(图片alt文本中的活动)
        # 格式: ![HUAWEI 活动名称](图片URL) ... ## 活动名称 ... 日期 ... 描述 ... 报名
        featured_pattern = r'!\[HUAWEI ([^\]]+)\]\(([^)]+)\)[^#]*?##\s*([^\n]+)\n+([^\n]*\d{1,2}[月日][^\n]*)\n*([^\n]*)\n'
        featured_matches = re.findall(featured_pattern, markdown, re.DOTALL)
        
        for alt_title, img_url, section_title, date_str, location in featured_matches:
            # 使用section标题(更准确)
            title = section_title.strip()
            
            # 跳过已有的
            if title in seen_titles:
                continue
            seen_titles.add(title)
            
            # 清理描述
            description = ""
            title_pos = markdown.find(f'## {title}')
            if title_pos != -1:
                after_title = markdown[title_pos:title_pos+1500]
                # 提取描述(在日期和"报名"之间)
                desc_match = re.search(r'线上\s*\n+(?:第\d+期\s*\n+)?([^\n]+?)(?:\n+报名|\n+探索更多)', after_title)
                if desc_match:
                    description = desc_match.group(1).strip()
            
            if not description:
                description = f"华为开发者活动: {title}"
            
            # 生成活动URL(基于标题生成唯一标识)
            # 由于精选活动没有直接链接,使用活动概览页面+标题hash
            # 使用hashlib确保跨运行的稳定性
            import hashlib
            title_hash = hashlib.md5(title.encode('utf-8')).hexdigest()[:8]
            url = f"https://developer.huawei.com/consumer/cn/activity/#featured-{title_hash}"
            
            category = self._determine_huawei_category(title)
            tags = ['huawei', 'harmonyos', 'developer', 'featured']
            if '计划' in title:
                tags.append('program')
            if '挑战' in title or '竞赛' in title:
                tags.append('challenge')
            if '招募' in title:
                tags.append('recruitment')
            
            activity = self.create_activity(
                url=url,
                title=title,
                description=description[:300],
                organizer="华为",
                tags=tags,
                category=category,
                image_url=img_url if not img_url.endswith('.svg') else None,
            )
            
            if activity:
                activities.append(activity)
                seen_urls.add(url)
        
        # 2. 提取侧边栏"活动"部分的链接
        activity_section_match = re.search(r'活动\n\n- \[活动概览\].*?(?=友情链接|$)', markdown, re.DOTALL)
        if activity_section_match:
            activity_section = activity_section_match.group(0)
            
            # 提取所有链接
            pattern = r'-\s*\[([^\]]+)\]\((https://[^)]+)\)'
            matches = re.findall(pattern, activity_section)
            
            for title, url in matches:
                title = title.strip()
                
                # 跳过已有的
                if title in seen_titles or url in seen_urls:
                    continue
                seen_titles.add(title)
                seen_urls.add(url)
                
                # 跳过过短的标题
                if len(title) < 2:
                    continue
                
                category = self._determine_huawei_category(title)
                tags = ['huawei', 'harmonyos', 'developer']
                if '大会' in title or 'HDC' in title:
                    tags.append('conference')
                elif 'Talk' in title:
                    tags.append('meetup')
                elif '计划' in title:
                    tags.append('program')
                
                activity = self.create_activity(
                    url=url,
                    title=title,
                    description=f"华为开发者活动: {title}",
                    organizer="华为",
                    tags=tags,
                    category=category,
                )
                
                if activity:
                    activities.append(activity)
        
        # 3. 提取Programs部分的开发者计划
        programs_section_match = re.search(r'Programs\n\n.*?(?=活动\n|$)', markdown, re.DOTALL)
        if programs_section_match:
            programs_section = programs_section_match.group(0)
            
            pattern = r'-\s*\[([^\]]+)\]\((https://[^)]+)\)'
            matches = re.findall(pattern, programs_section)
            
            for title, url in matches:
                title = title.strip()
                
                if title in seen_titles or url in seen_urls:
                    continue
                seen_titles.add(title)
                seen_urls.add(url)
                
                if len(title) < 2:
                    continue
                
                tags = ['huawei', 'harmonyos', 'developer', 'program']
                
                activity = self.create_activity(
                    url=url,
                    title=title,
                    description=f"华为开发者计划: {title}",
                    organizer="华为",
                    tags=tags,
                    category='dev_event',
                )
                
                if activity:
                    activities.append(activity)
        
        logger.info(f"从华为开发者页面提取了 {len(activities)} 个活动")
        return activities
    
    def _determine_huawei_category(self, title: str) -> str:
        """
        根据标题判断华为活动类别
        """
        title_lower = title.lower()
        
        # 编程竞赛关键词
        competition_keywords = ['大赛', '创新赛', '竞赛', '比赛', 'competition', 'contest', 'challenge']
        if any(kw in title_lower for kw in competition_keywords):
            return 'coding_competition'
        
        # 默认为开发者活动
        return 'dev_event'

    def _extract_immunefi_style(self, markdown: str) -> List[Activity]:
        """
        提取Immunefi风格的漏洞赏金项目
        从URL中提取项目名称，因为页面上的标题都是"View bounty"
        """
        activities = []
        seen_urls = set()
        
        # 查找所有bug-bounty链接
        pattern = r'https://immunefi\.com/bug-bounty/([a-zA-Z0-9_-]+)/information/'
        matches = re.findall(pattern, markdown)
        
        for slug in matches:
            url = f"https://immunefi.com/bug-bounty/{slug}/information/"
            
            if url in seen_urls:
                continue
            seen_urls.add(url)
            
            # 从slug提取项目名称
            title = slug.replace('-', ' ').title()
            
            # 尝试从上下文提取奖金信息
            prize_amount = None
            prize_currency = 'USD'
            
            # 查找URL附近的奖金信息
            url_pos = markdown.find(url)
            if url_pos != -1:
                context = markdown[max(0, url_pos-500):url_pos+200]
                # 查找奖金模式
                prize_match = re.search(r'\$([\d,]+(?:\.\d+)?)\s*(?:k|K|M)?', context)
                if prize_match:
                    try:
                        amount_str = prize_match.group(1).replace(',', '')
                        prize_amount = float(amount_str)
                        # 检查是否有k或M后缀
                        suffix = context[prize_match.end():prize_match.end()+2].lower()
                        if 'k' in suffix:
                            prize_amount *= 1000
                        elif 'm' in suffix:
                            prize_amount *= 1000000
                    except ValueError:
                        pass
            
            activity = self.create_activity(
                url=url,
                title=f"{title} Bug Bounty",
                description=f"Immunefi漏洞赏金项目: {title}",
                prize_amount=prize_amount,
                prize_currency=prize_currency,
                tags=['bounty', 'security', 'web3', 'smart-contract'],
                category='bounty',
            )
            
            if activity:
                activities.append(activity)
        
        # 也提取audit-competition链接
        audit_pattern = r'https://immunefi\.com/audit-competition/([a-zA-Z0-9_-]+)/'
        audit_matches = re.findall(audit_pattern, markdown)
        
        for slug in audit_matches:
            url = f"https://immunefi.com/audit-competition/{slug}/"
            
            if url in seen_urls:
                continue
            seen_urls.add(url)
            
            title = slug.replace('-', ' ').title()
            
            activity = self.create_activity(
                url=url,
                title=f"{title} Audit Competition",
                description=f"Immunefi审计竞赛: {title}",
                tags=['audit', 'security', 'web3', 'competition'],
                category='bounty',
            )
            
            if activity:
                activities.append(activity)
        
        logger.info(f"从Immunefi提取了 {len(activities)} 个赏金项目")
        return activities
    
    def _extract_airdrops_style(self, markdown: str) -> List[Activity]:
        """
        提取Airdrops.io风格的空投信息
        """
        activities = []
        seen_urls = set()
        
        # 查找所有airdrops.io的项目链接
        pattern = r'\[([^\]]+)\]\((https://airdrops\.io/[a-zA-Z0-9_-]+/)\)'
        matches = re.findall(pattern, markdown)
        
        # 需要跳过的导航链接和按钮文本
        skip_titles = [
            'join now', 'start now', 'claim now', 'get started',
            'find the latest airdrops', 'find the hottest airdrops',
            'home', 'about', 'contact', 'faq', 'blog',
            'latest', 'exclusive', 'speculative', 'ended', 'hot',
            'finding', 'find'
        ]
        
        # 需要跳过的URL路径
        skip_paths = ['latest', 'exclusive', 'speculative', 'ended', 'hot', 'about', 'contact', 'faq']
        
        for title, url in matches:
            if url in seen_urls:
                continue
            
            # 清理标题
            title = title.strip()
            # 移除markdown加粗标记
            title = re.sub(r'\*\*([^*]+)\*\*', r'\1', title)
            title = title.strip()
            
            # 跳过导航链接和按钮
            if title.lower() in skip_titles:
                continue
            
            # 跳过太短的标题
            if len(title) < 2:
                continue
            
            # 从URL中提取slug作为备用标题
            slug_match = re.search(r'airdrops\.io/([a-zA-Z0-9_-]+)/', url)
            if slug_match:
                slug = slug_match.group(1)
                # 跳过导航页面
                if slug.lower() in skip_paths:
                    continue
                # 如果标题看起来不像项目名，使用slug
                if title.lower() in skip_titles or len(title) < 3:
                    title = slug.replace('-', ' ').title()
            
            seen_urls.add(url)
            
            # 生成空投相关的标签
            tags = ['airdrop', 'crypto', 'web3']
            title_lower = title.lower()
            if 'defi' in title_lower:
                tags.append('defi')
            if 'nft' in title_lower:
                tags.append('nft')
            if 'token' in title_lower:
                tags.append('token')
            if 'exchange' in title_lower or any(ex in title_lower for ex in ['binance', 'coinbase', 'bybit', 'mexc', 'bitget']):
                tags.append('exchange')
            
            activity = self.create_activity(
                url=url,
                title=title,
                description=f"加密货币空投: {title}",
                tags=tags,
                category='airdrop',
            )
            
            if activity:
                activities.append(activity)
        
        # 备用方法：直接查找airdrops.io链接
        if not activities:
            url_pattern = r'https://airdrops\.io/([a-zA-Z0-9_-]+)/'
            urls = re.findall(url_pattern, markdown)
            
            seen_slugs = set()
            for slug in urls:
                if slug in seen_slugs or slug.lower() in skip_titles:
                    continue
                seen_slugs.add(slug)
                
                url = f"https://airdrops.io/{slug}/"
                title = slug.replace('-', ' ').title()
                
                activity = self.create_activity(
                    url=url,
                    title=title,
                    description=f"加密货币空投: {title}",
                    tags=['airdrop', 'crypto', 'web3'],
                    category='airdrop',
                )
                
                if activity:
                    activities.append(activity)
        
        logger.info(f"从Airdrops.io提取了 {len(activities)} 个空投")
        return activities
