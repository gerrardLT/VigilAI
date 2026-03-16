"""
VigilAI User-Agent轮换组件
实现User-Agent的随机选择和轮换功能

Validates: Requirements 11.2
"""

import random
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)


# 预定义的User-Agent列表，涵盖主流浏览器和操作系统
DEFAULT_USER_AGENTS = [
    # Chrome on Windows
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36',
    
    # Firefox on Windows
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:119.0) Gecko/20100101 Firefox/119.0',
    
    # Chrome on macOS
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
    
    # Safari on macOS
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15',
    
    # Chrome on Linux
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
    
    # Firefox on Linux
    'Mozilla/5.0 (X11; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0',
    
    # Edge on Windows
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0',
    
    # Mobile User Agents
    'Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1',
    'Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
]


class UserAgentRotator:
    """
    User-Agent轮换器
    
    功能:
    - 随机选择User-Agent
    - 支持自定义User-Agent列表
    - 避免连续使用相同的User-Agent
    """
    
    def __init__(self, user_agents: Optional[List[str]] = None):
        """
        初始化User-Agent轮换器
        
        Args:
            user_agents: 自定义User-Agent列表，为None时使用默认列表
        """
        self.user_agents: List[str] = user_agents or DEFAULT_USER_AGENTS.copy()
        self.last_used: Optional[str] = None
        self.use_count: dict = {}
        
        logger.info(f"UserAgentRotator initialized with {len(self.user_agents)} user agents")
    
    def get_random(self) -> str:
        """
        获取随机User-Agent
        
        Returns:
            随机选择的User-Agent字符串
        """
        if not self.user_agents:
            # 如果列表为空，返回默认值
            return DEFAULT_USER_AGENTS[0]
        
        if len(self.user_agents) == 1:
            return self.user_agents[0]
        
        # 尝试选择与上次不同的User-Agent
        available = [ua for ua in self.user_agents if ua != self.last_used]
        if not available:
            available = self.user_agents
        
        selected = random.choice(available)
        self.last_used = selected
        self.use_count[selected] = self.use_count.get(selected, 0) + 1
        
        logger.debug(f"Selected User-Agent: {selected[:50]}...")
        return selected
    
    def add_user_agent(self, user_agent: str) -> None:
        """添加User-Agent到列表"""
        if user_agent and user_agent not in self.user_agents:
            self.user_agents.append(user_agent)
            logger.debug(f"Added User-Agent: {user_agent[:50]}...")
    
    def add_user_agents(self, user_agents: List[str]) -> None:
        """批量添加User-Agent"""
        for ua in user_agents:
            self.add_user_agent(ua)
    
    def remove_user_agent(self, user_agent: str) -> None:
        """从列表中移除User-Agent"""
        if user_agent in self.user_agents:
            self.user_agents.remove(user_agent)
            self.use_count.pop(user_agent, None)
    
    def reset(self) -> None:
        """重置为默认User-Agent列表"""
        self.user_agents = DEFAULT_USER_AGENTS.copy()
        self.last_used = None
        self.use_count.clear()
        logger.info("Reset to default User-Agent list")
    
    def get_stats(self) -> dict:
        """获取使用统计"""
        return {
            'total': len(self.user_agents),
            'use_count': self.use_count.copy(),
            'last_used': self.last_used,
        }
    
    def __len__(self) -> int:
        """返回User-Agent列表大小"""
        return len(self.user_agents)
    
    def __bool__(self) -> bool:
        """检查是否有可用的User-Agent"""
        return len(self.user_agents) > 0
