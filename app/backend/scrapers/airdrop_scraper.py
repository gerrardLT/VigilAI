"""
VigilAI 空投聚合爬虫
支持Airdrops.io、CoinMarketCap、Galxe、DeFiLlama、Zealy等平台

Validates: Requirements 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 10.1, 10.2, 10.3
"""

import asyncio
import logging
import re
from typing import List, Optional, Dict, Any
from datetime import datetime
from bs4 import BeautifulSoup

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scrapers.base import BaseScraper
from models import Activity

logger = logging.getLogger(__name__)


class AirdropScraper(BaseScraper):
    """
    空投聚合爬虫
    
    支持平台:
    - Airdrops.io (静态)
    - CoinMarketCap Airdrops (动态)
    - Galxe (动态)
    - DeFiLlama Airdrops (静态)
    - Zealy (动态)
    
    功能:
    - 静态和动态页面抓取
    - 反爬虫策略支持
    - 数据标准化
    """
    
    def __init__(self, source_id: str, source_config: dict):
        super().__init__(source_id, source_config)
        self.use_selenium = source_config.get('use_selenium', False)
        self.driver = None
        
    async def scrape(self) -> List[Activity]:
        """抓取空投信息"""
        try:
            if self.use_selenium:
                return await self._scrape_dynamic()
            else:
                return await self._scrape_static()
        except Exception as e:
            if self.handle_error(e, "scrape"):
                await self.add_random_delay()
                return await self.scrape()
            return []
        finally:
            if self.driver:
                try:
                    self.driver.quit()
                except:
                    pass
                self.driver = None
    
    async def _scrape_static(self) -> List[Activity]:
        """静态页面抓取（Airdrops.io, DeFiLlama）"""
        html = await self.fetch_url(self.source_url)
        if not html:
            return []
        
        soup = BeautifulSoup(html, 'html.parser')
        activities = []
        
        # 根据不同平台使用不同的解析器
        if 'airdrops.io' in self.source_url:
            activities = self._parse_airdrops_io(soup)
        elif 'defillama' in self.source_url:
            activities = self._parse_defillama(soup)
        else:
            logger.warning(f"No parser for URL: {self.source_url}")
        
        logger.info(f"Scraped {len(activities)} airdrops from {self.source_name}")
        return activities
    
    async def _scrape_dynamic(self) -> List[Activity]:
        """动态页面抓取（CoinMarketCap, Galxe, Zealy）"""
        try:
            from selenium import webdriver
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            from selenium.webdriver.chrome.options import Options
        except ImportError:
            logger.error("Selenium not installed. Run: pip install selenium")
            return []
        
        options = Options()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument(f'user-agent={self.get_random_user_agent()}')
        
        # 配置代理
        if self.proxy_pool and self.proxy_pool.has_available():
            proxy = self.proxy_pool.get_random_proxy()
            if proxy:
                options.add_argument(f'--proxy-server={proxy["http"]}')
        
        try:
            self.driver = webdriver.Chrome(options=options)
            self.driver.get(self.source_url)
            
            # 等待页面加载
            await asyncio.sleep(3)
            
            activities = []
            if 'coinmarketcap' in self.source_url:
                activities = self._parse_coinmarketcap(self.driver)
            elif 'galxe' in self.source_url:
                activities = self._parse_galxe(self.driver)
            elif 'zealy' in self.source_url:
                activities = self._parse_zealy(self.driver)
            
            logger.info(f"Scraped {len(activities)} airdrops from {self.source_name}")
            return activities
            
        except Exception as e:
            logger.error(f"Selenium error: {e}")
            return []
    
    def _parse_airdrops_io(self, soup: BeautifulSoup) -> List[Activity]:
        """
        解析Airdrops.io页面
        Validates: Requirements 1.1
        """
        activities = []
        
        # 尝试多种选择器
        airdrop_cards = soup.select('.airdrop-card, .card, [class*="airdrop"]')
        
        if not airdrop_cards:
            # 备用选择器
            airdrop_cards = soup.select('article, .item, .listing')
        
        for card in airdrop_cards:
            try:
                # 提取标题
                title_elem = card.select_one('h2, h3, .title, [class*="title"]')
                title = title_elem.get_text(strip=True) if title_elem else None
                
                if not title:
                    continue
                
                # 提取URL
                link_elem = card.select_one('a[href]')
                url = link_elem.get('href', '') if link_elem else ''
                if url and not url.startswith('http'):
                    url = f"https://airdrops.io{url}"
                
                # 提取描述
                desc_elem = card.select_one('.description, p, [class*="desc"]')
                description = desc_elem.get_text(strip=True) if desc_elem else ''
                
                # 提取奖励
                reward_elem = card.select_one('.reward, .prize, [class*="reward"]')
                prize_text = reward_elem.get_text(strip=True) if reward_elem else ''
                
                # 提取截止日期
                deadline_elem = card.select_one('.deadline, .date, [class*="deadline"]')
                deadline_text = deadline_elem.get_text(strip=True) if deadline_elem else ''
                
                activity = self.create_activity(
                    url=url or self.source_url,
                    title=title,
                    description=description,
                    prize_description=prize_text,
                    prize_amount=self._normalize_prize(prize_text),
                    prize_currency=self.extract_currency(prize_text),
                    deadline=self._parse_deadline(deadline_text),
                    tags=['airdrop', 'crypto'],
                )
                activities.append(activity)
                
            except Exception as e:
                logger.warning(f"Failed to parse airdrop card: {e}")
                continue
        
        return activities
    
    def _parse_coinmarketcap(self, driver) -> List[Activity]:
        """
        解析CoinMarketCap空投页面（动态）
        Validates: Requirements 1.2
        """
        activities = []
        
        try:
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            
            # 等待空投列表加载
            wait = WebDriverWait(driver, 10)
            
            # 尝试多种选择器
            selectors = [
                '[class*="airdrop"]',
                '[class*="campaign"]',
                'table tbody tr',
                '.cmc-table tbody tr',
            ]
            
            elements = []
            for selector in selectors:
                try:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        break
                except:
                    continue
            
            for element in elements[:20]:  # 限制数量
                try:
                    # 提取标题
                    title_elem = element.find_elements(By.CSS_SELECTOR, 'a, h3, .name')
                    title = title_elem[0].text if title_elem else ''
                    
                    if not title:
                        continue
                    
                    # 提取URL
                    link_elem = element.find_elements(By.TAG_NAME, 'a')
                    url = link_elem[0].get_attribute('href') if link_elem else ''
                    
                    # 提取描述
                    desc_elem = element.find_elements(By.CSS_SELECTOR, '.description, p')
                    description = desc_elem[0].text if desc_elem else ''
                    
                    # 提取奖励
                    reward_elem = element.find_elements(By.CSS_SELECTOR, '[class*="reward"], [class*="prize"]')
                    prize_text = reward_elem[0].text if reward_elem else ''
                    
                    activity = self.create_activity(
                        url=url or self.source_url,
                        title=title,
                        description=description,
                        prize_description=prize_text,
                        prize_amount=self._normalize_prize(prize_text),
                        prize_currency=self.extract_currency(prize_text),
                        tags=['airdrop', 'crypto', 'coinmarketcap'],
                    )
                    activities.append(activity)
                    
                except Exception as e:
                    logger.warning(f"Failed to parse CMC airdrop: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error parsing CoinMarketCap: {e}")
        
        return activities
    
    def _parse_galxe(self, driver) -> List[Activity]:
        """
        解析Galxe平台（动态）
        Validates: Requirements 1.3
        """
        activities = []
        
        try:
            from selenium.webdriver.common.by import By
            
            # 等待页面加载
            import time
            time.sleep(3)
            
            # 尝试多种选择器
            selectors = [
                '[class*="campaign"]',
                '[class*="quest"]',
                '[class*="card"]',
                'article',
            ]
            
            elements = []
            for selector in selectors:
                try:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        break
                except:
                    continue
            
            for element in elements[:30]:
                try:
                    # 提取标题
                    title_elem = element.find_elements(By.CSS_SELECTOR, 'h2, h3, [class*="title"]')
                    title = title_elem[0].text if title_elem else ''
                    
                    if not title or len(title) < 3:
                        continue
                    
                    # 提取URL
                    link_elem = element.find_elements(By.TAG_NAME, 'a')
                    url = link_elem[0].get_attribute('href') if link_elem else ''
                    
                    # 提取描述
                    desc_elem = element.find_elements(By.CSS_SELECTOR, 'p, [class*="desc"]')
                    description = desc_elem[0].text if desc_elem else ''
                    
                    # 提取奖励代币
                    reward_elem = element.find_elements(By.CSS_SELECTOR, '[class*="reward"], [class*="token"]')
                    reward_text = reward_elem[0].text if reward_elem else ''
                    
                    # 提取参与人数
                    participants_elem = element.find_elements(By.CSS_SELECTOR, '[class*="participant"]')
                    participants = participants_elem[0].text if participants_elem else ''
                    
                    activity = self.create_activity(
                        url=url or self.source_url,
                        title=title,
                        description=f"{description} {participants}".strip(),
                        prize_description=reward_text,
                        tags=['airdrop', 'galxe', 'web3', 'quest'],
                    )
                    activities.append(activity)
                    
                except Exception as e:
                    logger.warning(f"Failed to parse Galxe campaign: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error parsing Galxe: {e}")
        
        return activities
    
    def _parse_defillama(self, soup: BeautifulSoup) -> List[Activity]:
        """
        解析DeFiLlama空投页面
        Validates: Requirements 1.4
        """
        activities = []
        
        # 尝试多种选择器
        airdrop_rows = soup.select('table tbody tr, [class*="row"], [class*="item"]')
        
        for row in airdrop_rows:
            try:
                # 提取项目名称
                name_elem = row.select_one('td:first-child, .name, [class*="name"]')
                name = name_elem.get_text(strip=True) if name_elem else ''
                
                if not name:
                    continue
                
                # 提取URL
                link_elem = row.select_one('a[href]')
                url = link_elem.get('href', '') if link_elem else ''
                if url and not url.startswith('http'):
                    url = f"https://defillama.com{url}"
                
                # 提取预计空投时间
                time_elem = row.select_one('[class*="time"], [class*="date"]')
                time_text = time_elem.get_text(strip=True) if time_elem else ''
                
                # 提取参与条件
                condition_elem = row.select_one('[class*="condition"], [class*="requirement"]')
                condition = condition_elem.get_text(strip=True) if condition_elem else ''
                
                # 提取TVL或其他指标
                tvl_elem = row.select_one('[class*="tvl"], [class*="value"]')
                tvl = tvl_elem.get_text(strip=True) if tvl_elem else ''
                
                description = f"预计时间: {time_text}. 参与条件: {condition}. TVL: {tvl}".strip()
                
                activity = self.create_activity(
                    url=url or self.source_url,
                    title=f"{name} Airdrop",
                    description=description,
                    deadline=self._parse_deadline(time_text),
                    tags=['airdrop', 'defi', 'defillama'],
                )
                activities.append(activity)
                
            except Exception as e:
                logger.warning(f"Failed to parse DeFiLlama row: {e}")
                continue
        
        return activities
    
    def _parse_zealy(self, driver) -> List[Activity]:
        """
        解析Zealy平台（动态）
        Validates: Requirements 1.5
        """
        activities = []
        
        try:
            from selenium.webdriver.common.by import By
            
            # 等待页面加载
            import time
            time.sleep(3)
            
            # 尝试多种选择器
            selectors = [
                '[class*="community"]',
                '[class*="quest"]',
                '[class*="card"]',
                'article',
            ]
            
            elements = []
            for selector in selectors:
                try:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        break
                except:
                    continue
            
            for element in elements[:30]:
                try:
                    # 提取社区/任务名称
                    title_elem = element.find_elements(By.CSS_SELECTOR, 'h2, h3, [class*="title"], [class*="name"]')
                    title = title_elem[0].text if title_elem else ''
                    
                    if not title or len(title) < 3:
                        continue
                    
                    # 提取URL
                    link_elem = element.find_elements(By.TAG_NAME, 'a')
                    url = link_elem[0].get_attribute('href') if link_elem else ''
                    
                    # 提取描述
                    desc_elem = element.find_elements(By.CSS_SELECTOR, 'p, [class*="desc"]')
                    description = desc_elem[0].text if desc_elem else ''
                    
                    # 提取积分奖励
                    points_elem = element.find_elements(By.CSS_SELECTOR, '[class*="point"], [class*="xp"]')
                    points = points_elem[0].text if points_elem else ''
                    
                    # 提取成员数
                    members_elem = element.find_elements(By.CSS_SELECTOR, '[class*="member"]')
                    members = members_elem[0].text if members_elem else ''
                    
                    activity = self.create_activity(
                        url=url or self.source_url,
                        title=title,
                        description=f"{description} 积分: {points} 成员: {members}".strip(),
                        prize_description=points,
                        tags=['airdrop', 'zealy', 'quest', 'points'],
                    )
                    activities.append(activity)
                    
                except Exception as e:
                    logger.warning(f"Failed to parse Zealy quest: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error parsing Zealy: {e}")
        
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

