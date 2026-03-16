"""
VigilAI 企业开发者平台爬虫
支持华为、Google、AWS、Microsoft等平台

Validates: Requirements 5.1, 5.2, 5.3, 5.4, 5.5, 10.1, 10.2, 10.3
"""

import logging
import asyncio
from typing import List, Optional
from datetime import datetime
from bs4 import BeautifulSoup

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scrapers.base import BaseScraper
from models import Activity

logger = logging.getLogger(__name__)


class EnterpriseScraper(BaseScraper):
    """
    企业开发者平台爬虫
    
    支持平台:
    - 华为开发者平台
    - Google开发者平台
    - AWS开发者平台
    - Microsoft开发者平台
    
    功能:
    - 支持API和网页两种抓取方式
    - 支持Selenium动态渲染（用于SPA网站如华为）
    - 开发者大赛、创新挑战、技术沙龙提取
    """
    
    def __init__(self, source_id: str, source_config: dict):
        super().__init__(source_id, source_config)
        self.use_selenium = source_config.get('use_selenium', False)
        self.driver = None
    
    async def scrape(self) -> List[Activity]:
        """抓取企业开发者竞赛信息"""
        try:
            # 优先使用API
            if self.config.get('api_url'):
                return await self._scrape_api()
            # 如果需要Selenium（如华为SPA）
            elif self.use_selenium:
                return await self._scrape_with_selenium()
            else:
                return await self._scrape_web()
                
        except Exception as e:
            if self.handle_error(e, "scrape"):
                await self.add_random_delay()
                return await self.scrape()
            return []
    
    async def _scrape_with_selenium(self) -> List[Activity]:
        """使用Selenium抓取动态页面（SPA网站）"""
        try:
            from selenium import webdriver
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            from selenium.webdriver.chrome.options import Options
        except ImportError:
            logger.error("Selenium not installed. Run: pip install selenium")
            # 回退到普通网页抓取
            return await self._scrape_web()
        
        activities = []
        
        # 配置Chrome选项
        options = Options()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument(f'user-agent={self.get_random_user_agent()}')
        options.add_argument('--lang=zh-CN')
        
        try:
            self.driver = webdriver.Chrome(options=options)
            self.driver.get(self.source_url)
            
            # 等待页面加载
            wait = WebDriverWait(self.driver, 15)
            
            # 根据不同平台使用不同的解析方法
            if 'huawei' in self.source_url or '华为' in self.source_name:
                activities = await self._parse_huawei_selenium(wait)
            elif 'google' in self.source_url:
                activities = await self._parse_google_selenium(wait)
            elif 'aws' in self.source_url or 'amazon' in self.source_url:
                activities = await self._parse_aws_selenium(wait)
            elif 'microsoft' in self.source_url:
                activities = await self._parse_microsoft_selenium(wait)
            else:
                # 通用Selenium解析
                activities = await self._parse_generic_selenium(wait)
            
            logger.info(f"Scraped {len(activities)} activities from {self.source_name} using Selenium")
            
        except Exception as e:
            logger.error(f"Selenium error for {self.source_name}: {e}")
        finally:
            if self.driver:
                self.driver.quit()
                self.driver = None
        
        return activities
    
    async def _parse_huawei_selenium(self, wait) -> List[Activity]:
        """
        使用Selenium解析华为开发者平台
        华为是Angular SPA，需要等待JS渲染
        Validates: Requirements 5.1
        """
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support import expected_conditions as EC
        
        activities = []
        
        try:
            # 等待活动列表加载 - 华为页面的可能选择器
            possible_selectors = [
                '.activity-list',
                '.activity-item',
                '.event-list',
                '.event-item',
                '[class*="activity"]',
                '[class*="event"]',
                '.card-list',
                '.card-item',
                '.list-item',
                'app-activity-list',
                'app-event-list',
            ]
            
            # 等待页面内容加载
            await asyncio.sleep(3)  # 给Angular时间渲染
            
            # 尝试找到活动容器
            page_source = self.driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')
            
            # 保存页面源码用于调试
            logger.debug(f"Huawei page source length: {len(page_source)}")
            
            # 尝试多种选择器
            event_items = []
            for selector in possible_selectors:
                items = soup.select(selector)
                if items:
                    logger.info(f"Found {len(items)} items with selector: {selector}")
                    event_items = items
                    break
            
            # 如果没找到特定选择器，尝试查找所有链接
            if not event_items:
                # 查找所有可能是活动的链接
                all_links = soup.find_all('a', href=True)
                for link in all_links:
                    href = link.get('href', '')
                    text = link.get_text(strip=True)
                    
                    # 过滤活动相关链接
                    if self._is_activity_link(href, text):
                        event_items.append(link)
            
            # 解析活动
            for item in event_items[:20]:  # 限制数量
                try:
                    activity = self._parse_huawei_item(item, soup)
                    if activity:
                        activities.append(activity)
                except Exception as e:
                    logger.warning(f"Failed to parse Huawei item: {e}")
                    continue
            
        except Exception as e:
            logger.error(f"Error parsing Huawei with Selenium: {e}")
        
        return activities
    
    def _is_activity_link(self, href: str, text: str) -> bool:
        """判断链接是否是活动链接"""
        # 活动关键词
        activity_keywords = ['活动', '大赛', '竞赛', '挑战', '训练营', '峰会', '论坛', 
                           'activity', 'event', 'competition', 'challenge', 'hackathon']
        
        # 排除关键词
        exclude_keywords = ['登录', '注册', '首页', '关于', '帮助', 'login', 'register', 
                          'home', 'about', 'help', 'privacy', 'terms']
        
        href_lower = href.lower()
        text_lower = text.lower()
        
        # 排除导航链接
        if any(kw in text_lower for kw in exclude_keywords):
            return False
        
        # 检查是否包含活动关键词
        if any(kw in href_lower or kw in text_lower for kw in activity_keywords):
            return True
        
        # 检查URL模式
        if '/activity/' in href_lower or '/event/' in href_lower:
            return True
        
        return False
    
    def _parse_huawei_item(self, item, soup) -> Optional[Activity]:
        """解析单个华为活动项"""
        # 获取标题
        title = None
        title_elem = item.select_one('h2, h3, h4, .title, [class*="title"]')
        if title_elem:
            title = title_elem.get_text(strip=True)
        else:
            title = item.get_text(strip=True)
        
        if not title or len(title) < 3:
            return None
        
        # 获取链接
        url = ''
        if item.name == 'a':
            url = item.get('href', '')
        else:
            link_elem = item.select_one('a[href]')
            if link_elem:
                url = link_elem.get('href', '')
        
        if url and not url.startswith('http'):
            url = f"https://developer.huawei.com{url}"
        
        # 获取描述
        desc_elem = item.select_one('.description, .desc, p, [class*="desc"]')
        description = desc_elem.get_text(strip=True) if desc_elem else ''
        
        # 获取日期
        date_elem = item.select_one('.date, .time, [class*="date"], [class*="time"]')
        date_text = date_elem.get_text(strip=True) if date_elem else ''
        
        # 确定标签
        tags = ['enterprise', 'huawei']
        if '大赛' in title or 'competition' in title.lower():
            tags.append('competition')
        elif '挑战' in title or 'challenge' in title.lower():
            tags.append('challenge')
        elif '训练营' in title:
            tags.append('training')
        elif '峰会' in title or '论坛' in title:
            tags.append('conference')
        
        return self.create_activity(
            url=url or self.source_url,
            title=title,
            description=description,
            deadline=self._parse_deadline(date_text),
            organizer='华为',
            tags=tags,
        )
    
    async def _parse_google_selenium(self, wait) -> List[Activity]:
        """使用Selenium解析Google开发者平台"""
        # 获取页面源码后使用BeautifulSoup解析
        page_source = self.driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        return self._parse_google(soup)
    
    async def _parse_aws_selenium(self, wait) -> List[Activity]:
        """使用Selenium解析AWS开发者平台"""
        page_source = self.driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        return self._parse_aws(soup)
    
    async def _parse_microsoft_selenium(self, wait) -> List[Activity]:
        """使用Selenium解析Microsoft开发者平台"""
        page_source = self.driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        return self._parse_microsoft(soup)
    
    async def _parse_generic_selenium(self, wait) -> List[Activity]:
        """通用Selenium解析"""
        page_source = self.driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        
        activities = []
        # 查找所有可能的活动卡片
        cards = soup.select('.card, .item, article, [class*="event"], [class*="activity"]')
        
        for card in cards[:20]:
            try:
                title_elem = card.select_one('h2, h3, h4, .title')
                if not title_elem:
                    continue
                
                title = title_elem.get_text(strip=True)
                if not title:
                    continue
                
                link_elem = card.select_one('a[href]')
                url = link_elem.get('href', '') if link_elem else ''
                
                desc_elem = card.select_one('p, .description')
                description = desc_elem.get_text(strip=True) if desc_elem else ''
                
                activity = self.create_activity(
                    url=url or self.source_url,
                    title=title,
                    description=description,
                    tags=['enterprise'],
                )
                activities.append(activity)
            except Exception as e:
                logger.warning(f"Failed to parse generic item: {e}")
                continue
        
        return activities
    
    async def _scrape_api(self) -> List[Activity]:
        """使用官方API抓取"""
        import httpx
        
        api_url = self.config.get('api_url')
        headers = self.get_headers()
        
        api_key = self.config.get('api_key')
        if api_key:
            headers['Authorization'] = f'Bearer {api_key}'
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(api_url, headers=headers, timeout=30)
                response.raise_for_status()
                
                data = response.json()
                activities = self._parse_api_response(data)
                
                logger.info(f"Scraped {len(activities)} activities from {self.source_name} API")
                return activities
        except Exception as e:
            logger.error(f"API error for {self.source_name}: {e}")
            # 回退到网页抓取
            return await self._scrape_web()
    
    def _parse_api_response(self, data: dict) -> List[Activity]:
        """解析API响应"""
        activities = []
        
        # 通用API响应解析
        items = data.get('data', data.get('items', data.get('results', [])))
        
        for item in items:
            try:
                title = item.get('title', item.get('name', ''))
                if not title:
                    continue
                
                activity = self.create_activity(
                    url=item.get('url', item.get('link', self.source_url)),
                    title=title,
                    description=item.get('description', item.get('summary', '')),
                    prize_amount=self._normalize_prize(item.get('prize')),
                    prize_description=item.get('prize'),
                    start_date=self._parse_api_date(item.get('start_date')),
                    end_date=self._parse_api_date(item.get('end_date')),
                    deadline=self._parse_api_date(item.get('deadline')),
                    tags=['enterprise', self.source_name.lower().replace(' ', '-')],
                )
                activities.append(activity)
            except Exception as e:
                logger.warning(f"Failed to parse API item: {e}")
                continue
        
        return activities
    
    def _parse_api_date(self, date_value) -> Optional[datetime]:
        """解析API日期"""
        if not date_value:
            return None
        
        normalized = self._normalize_date(date_value)
        if normalized:
            try:
                return datetime.fromisoformat(normalized.replace('Z', '+00:00'))
            except:
                pass
        return None
    
    async def _scrape_web(self) -> List[Activity]:
        """网页抓取"""
        html = await self.fetch_url(self.source_url)
        if not html:
            return []
        
        soup = BeautifulSoup(html, 'html.parser')
        activities = []
        
        if 'huawei' in self.source_url or '华为' in self.source_name:
            activities = self._parse_huawei(soup)
        elif 'google' in self.source_url:
            activities = self._parse_google(soup)
        elif 'aws' in self.source_url or 'amazon' in self.source_url:
            activities = self._parse_aws(soup)
        elif 'microsoft' in self.source_url:
            activities = self._parse_microsoft(soup)
        else:
            logger.warning(f"No parser for URL: {self.source_url}")
        
        logger.info(f"Scraped {len(activities)} activities from {self.source_name}")
        return activities
    
    def _parse_huawei(self, soup: BeautifulSoup) -> List[Activity]:
        """
        解析华为开发者平台
        Validates: Requirements 5.1
        """
        activities = []
        
        event_items = soup.select('.activity, .event, [class*="activity"]')
        
        if not event_items:
            event_items = soup.select('article, .card, .item')
        
        for item in event_items:
            try:
                title_elem = item.select_one('h2, h3, .title, [class*="title"]')
                title = title_elem.get_text(strip=True) if title_elem else None
                
                if not title:
                    continue
                
                link_elem = item.select_one('a[href]')
                url = link_elem.get('href', '') if link_elem else ''
                if url and not url.startswith('http'):
                    url = f"https://developer.huawei.com{url}"
                
                # 提取活动类型
                type_elem = item.select_one('.type, [class*="type"]')
                event_type = type_elem.get_text(strip=True) if type_elem else ''
                
                # 提取日期
                date_elem = item.select_one('.date, [class*="date"]')
                date_text = date_elem.get_text(strip=True) if date_elem else ''
                
                desc_elem = item.select_one('.description, p')
                description = desc_elem.get_text(strip=True) if desc_elem else ''
                
                tags = ['enterprise', 'huawei']
                if '大赛' in title or 'competition' in title.lower():
                    tags.append('competition')
                elif '挑战' in title or 'challenge' in title.lower():
                    tags.append('challenge')
                elif '沙龙' in title or 'salon' in title.lower():
                    tags.append('event')
                
                activity = self.create_activity(
                    url=url or self.source_url,
                    title=title,
                    description=f"{description} {event_type}".strip(),
                    deadline=self._parse_deadline(date_text),
                    organizer='华为',
                    tags=tags,
                )
                activities.append(activity)
                
            except Exception as e:
                logger.warning(f"Failed to parse Huawei event: {e}")
                continue
        
        return activities
    
    def _parse_google(self, soup: BeautifulSoup) -> List[Activity]:
        """
        解析Google开发者平台
        Validates: Requirements 5.2
        """
        activities = []
        
        event_items = soup.select('.program, .event, [class*="program"]')
        
        if not event_items:
            event_items = soup.select('article, .card, .item')
        
        for item in event_items:
            try:
                title_elem = item.select_one('h2, h3, .title, [class*="title"]')
                title = title_elem.get_text(strip=True) if title_elem else None
                
                if not title:
                    continue
                
                link_elem = item.select_one('a[href]')
                url = link_elem.get('href', '') if link_elem else ''
                if url and not url.startswith('http'):
                    url = f"https://developers.google.com{url}"
                
                desc_elem = item.select_one('.description, p')
                description = desc_elem.get_text(strip=True) if desc_elem else ''
                
                # 识别生态系统
                tags = ['enterprise', 'google']
                if 'cloud' in title.lower():
                    tags.append('google-cloud')
                elif 'android' in title.lower():
                    tags.append('android')
                elif 'flutter' in title.lower():
                    tags.append('flutter')
                
                activity = self.create_activity(
                    url=url or self.source_url,
                    title=title,
                    description=description,
                    organizer='Google',
                    tags=tags,
                )
                activities.append(activity)
                
            except Exception as e:
                logger.warning(f"Failed to parse Google event: {e}")
                continue
        
        return activities
    
    def _parse_aws(self, soup: BeautifulSoup) -> List[Activity]:
        """
        解析AWS开发者平台
        Validates: Requirements 5.3
        """
        activities = []
        
        event_items = soup.select('.program, .event, [class*="program"]')
        
        if not event_items:
            event_items = soup.select('article, .card, .item')
        
        for item in event_items:
            try:
                title_elem = item.select_one('h2, h3, .title, [class*="title"]')
                title = title_elem.get_text(strip=True) if title_elem else None
                
                if not title:
                    continue
                
                link_elem = item.select_one('a[href]')
                url = link_elem.get('href', '') if link_elem else ''
                if url and not url.startswith('http'):
                    url = f"https://aws.amazon.com{url}"
                
                desc_elem = item.select_one('.description, p')
                description = desc_elem.get_text(strip=True) if desc_elem else ''
                
                tags = ['enterprise', 'aws', 'cloud']
                if 'hackathon' in title.lower():
                    tags.append('hackathon')
                elif 'challenge' in title.lower():
                    tags.append('challenge')
                
                activity = self.create_activity(
                    url=url or self.source_url,
                    title=title,
                    description=description,
                    organizer='Amazon Web Services',
                    tags=tags,
                )
                activities.append(activity)
                
            except Exception as e:
                logger.warning(f"Failed to parse AWS event: {e}")
                continue
        
        return activities
    
    def _parse_microsoft(self, soup: BeautifulSoup) -> List[Activity]:
        """
        解析Microsoft开发者平台
        Validates: Requirements 5.4
        """
        activities = []
        
        event_items = soup.select('.program, .event, [class*="program"]')
        
        if not event_items:
            event_items = soup.select('article, .card, .item')
        
        for item in event_items:
            try:
                title_elem = item.select_one('h2, h3, .title, [class*="title"]')
                title = title_elem.get_text(strip=True) if title_elem else None
                
                if not title:
                    continue
                
                link_elem = item.select_one('a[href]')
                url = link_elem.get('href', '') if link_elem else ''
                if url and not url.startswith('http'):
                    url = f"https://microsoft.com{url}"
                
                desc_elem = item.select_one('.description, p')
                description = desc_elem.get_text(strip=True) if desc_elem else ''
                
                tags = ['enterprise', 'microsoft']
                if 'azure' in title.lower():
                    tags.append('azure')
                elif 'github' in title.lower():
                    tags.append('github')
                elif 'imagine' in title.lower():
                    tags.append('imagine-cup')
                
                activity = self.create_activity(
                    url=url or self.source_url,
                    title=title,
                    description=description,
                    organizer='Microsoft',
                    tags=tags,
                )
                activities.append(activity)
                
            except Exception as e:
                logger.warning(f"Failed to parse Microsoft event: {e}")
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

