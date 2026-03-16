"""
VigilAI 代理池组件
实现代理IP的管理和轮换功能

Validates: Requirements 11.1, 11.4
"""

import random
import logging
from typing import Optional, List, Dict, Set
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class ProxyPool:
    """
    代理池管理类
    
    功能:
    - 代理随机选择
    - 失败代理标记
    - 代理池重置
    - 代理健康检查
    """
    
    def __init__(self, proxy_list: Optional[List[str]] = None):
        """
        初始化代理池
        
        Args:
            proxy_list: 代理列表，格式如 ['http://ip:port', 'http://user:pass@ip:port']
        """
        self.proxies: List[str] = proxy_list or []
        self.failed_proxies: Set[str] = set()
        self.failure_counts: Dict[str, int] = {}
        self.last_used: Dict[str, datetime] = {}
        self.max_failures = 3  # 最大失败次数后标记为失败
        self.cooldown_period = timedelta(minutes=30)  # 失败代理冷却时间
        
        logger.info(f"ProxyPool initialized with {len(self.proxies)} proxies")
    
    def add_proxy(self, proxy: str) -> None:
        """添加代理到池中"""
        if proxy not in self.proxies:
            self.proxies.append(proxy)
            logger.debug(f"Added proxy: {proxy}")
    
    def add_proxies(self, proxies: List[str]) -> None:
        """批量添加代理"""
        for proxy in proxies:
            self.add_proxy(proxy)
    
    def get_random_proxy(self) -> Optional[Dict[str, str]]:
        """
        获取随机代理
        
        Returns:
            代理配置字典 {'http': proxy, 'https': proxy} 或 None
        """
        available_proxies = self._get_available_proxies()
        
        if not available_proxies:
            logger.warning("No available proxies in pool")
            return None
        
        proxy = random.choice(available_proxies)
        self.last_used[proxy] = datetime.utcnow()
        
        logger.debug(f"Selected proxy: {proxy}")
        return {
            'http': proxy,
            'https': proxy,
        }
    
    def _get_available_proxies(self) -> List[str]:
        """获取可用的代理列表（排除失败的代理）"""
        now = datetime.utcnow()
        available = []
        
        for proxy in self.proxies:
            if proxy in self.failed_proxies:
                # 检查是否已过冷却期
                last_failure = self.last_used.get(proxy)
                if last_failure and (now - last_failure) > self.cooldown_period:
                    # 冷却期已过，重新启用
                    self.failed_proxies.discard(proxy)
                    self.failure_counts[proxy] = 0
                    available.append(proxy)
            else:
                available.append(proxy)
        
        return available
    
    def mark_failed(self, proxy: str) -> None:
        """
        标记代理失败
        
        Args:
            proxy: 失败的代理地址
        """
        if proxy not in self.proxies:
            return
        
        self.failure_counts[proxy] = self.failure_counts.get(proxy, 0) + 1
        self.last_used[proxy] = datetime.utcnow()
        
        if self.failure_counts[proxy] >= self.max_failures:
            self.failed_proxies.add(proxy)
            logger.warning(f"Proxy marked as failed after {self.max_failures} failures: {proxy}")
        else:
            logger.debug(f"Proxy failure count: {proxy} = {self.failure_counts[proxy]}")
    
    def mark_success(self, proxy: str) -> None:
        """
        标记代理成功，重置失败计数
        
        Args:
            proxy: 成功的代理地址
        """
        if proxy in self.failure_counts:
            self.failure_counts[proxy] = 0
        if proxy in self.failed_proxies:
            self.failed_proxies.discard(proxy)
    
    def reset_failed(self) -> None:
        """重置所有失败代理状态"""
        self.failed_proxies.clear()
        self.failure_counts.clear()
        logger.info("Reset all failed proxies")
    
    def remove_proxy(self, proxy: str) -> None:
        """从池中移除代理"""
        if proxy in self.proxies:
            self.proxies.remove(proxy)
            self.failed_proxies.discard(proxy)
            self.failure_counts.pop(proxy, None)
            self.last_used.pop(proxy, None)
            logger.debug(f"Removed proxy: {proxy}")
    
    def get_stats(self) -> Dict:
        """获取代理池统计信息"""
        return {
            'total': len(self.proxies),
            'available': len(self._get_available_proxies()),
            'failed': len(self.failed_proxies),
        }
    
    def is_empty(self) -> bool:
        """检查代理池是否为空"""
        return len(self.proxies) == 0
    
    def has_available(self) -> bool:
        """检查是否有可用代理"""
        return len(self._get_available_proxies()) > 0
    
    def __len__(self) -> int:
        """返回代理池大小"""
        return len(self.proxies)
    
    def __bool__(self) -> bool:
        """检查代理池是否有代理"""
        return len(self.proxies) > 0
