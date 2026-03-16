"""
Firecrawl API Key 轮换池
支持多个API Key轮流使用，平均分配请求次数
"""

import logging
import threading
from typing import List, Optional
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class ApiKeyStats:
    """API Key使用统计"""
    key: str
    request_count: int = 0
    success_count: int = 0
    error_count: int = 0
    last_used: Optional[datetime] = None
    last_error: Optional[str] = None
    
    @property
    def masked_key(self) -> str:
        """返回脱敏的key（只显示前8位和后4位）"""
        if len(self.key) > 12:
            return f"{self.key[:8]}...{self.key[-4:]}"
        return "***"


class ApiKeyPool:
    """
    API Key轮换池
    
    使用方式:
    1. 在.env中配置多个key，用逗号分隔:
       FIRECRAWL_API_KEYS=key1,key2,key3
    
    2. 或者保持原有单key配置:
       FIRECRAWL_API_KEY=your_key
    
    3. 代码中使用:
       pool = ApiKeyPool.get_instance()
       key = pool.get_next_key()
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __init__(self, api_keys: List[str] = None):
        """
        初始化API Key池
        
        Args:
            api_keys: API Key列表
        """
        self._keys: List[ApiKeyStats] = []
        self._current_index = 0
        self._index_lock = threading.Lock()
        
        if api_keys:
            for key in api_keys:
                key = key.strip()
                if key:
                    self._keys.append(ApiKeyStats(key=key))
        
        if self._keys:
            logger.info(f"ApiKeyPool initialized with {len(self._keys)} keys")
        else:
            logger.warning("ApiKeyPool initialized with no keys")
    
    @classmethod
    def get_instance(cls) -> 'ApiKeyPool':
        """获取单例实例"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls._create_from_env()
        return cls._instance
    
    @classmethod
    def _create_from_env(cls) -> 'ApiKeyPool':
        """从环境变量创建实例"""
        import os
        
        # 优先使用多key配置
        keys_str = os.getenv("FIRECRAWL_API_KEYS", "")
        if keys_str:
            keys = [k.strip() for k in keys_str.split(",") if k.strip()]
            if keys:
                return cls(keys)
        
        # 回退到单key配置
        single_key = os.getenv("FIRECRAWL_API_KEY", "")
        if single_key:
            return cls([single_key])
        
        return cls([])
    
    @classmethod
    def reset_instance(cls):
        """重置单例（用于测试）"""
        with cls._lock:
            cls._instance = None
    
    @property
    def key_count(self) -> int:
        """返回可用key数量"""
        return len(self._keys)
    
    @property
    def has_keys(self) -> bool:
        """是否有可用key"""
        return len(self._keys) > 0
    
    def get_next_key(self) -> Optional[str]:
        """
        获取下一个API Key（轮询方式）
        
        Returns:
            API Key字符串，如果没有可用key返回None
        """
        if not self._keys:
            return None
        
        with self._index_lock:
            key_stats = self._keys[self._current_index]
            key_stats.request_count += 1
            key_stats.last_used = datetime.now()
            
            # 移动到下一个key
            self._current_index = (self._current_index + 1) % len(self._keys)
            
            return key_stats.key
    
    def get_current_key(self) -> Optional[str]:
        """获取当前key（不移动索引）"""
        if not self._keys:
            return None
        return self._keys[self._current_index].key
    
    def report_success(self, key: str):
        """报告请求成功"""
        for key_stats in self._keys:
            if key_stats.key == key:
                key_stats.success_count += 1
                key_stats.last_error = None
                break
    
    def report_error(self, key: str, error_msg: str):
        """报告请求失败"""
        for key_stats in self._keys:
            if key_stats.key == key:
                key_stats.error_count += 1
                key_stats.last_error = error_msg
                break
    
    def get_stats(self) -> List[dict]:
        """获取所有key的使用统计"""
        return [
            {
                "key": stats.masked_key,
                "request_count": stats.request_count,
                "success_count": stats.success_count,
                "error_count": stats.error_count,
                "success_rate": f"{stats.success_count / stats.request_count * 100:.1f}%" 
                    if stats.request_count > 0 else "N/A",
                "last_used": stats.last_used.isoformat() if stats.last_used else None,
                "last_error": stats.last_error,
            }
            for stats in self._keys
        ]
    
    def get_total_stats(self) -> dict:
        """获取汇总统计"""
        total_requests = sum(s.request_count for s in self._keys)
        total_success = sum(s.success_count for s in self._keys)
        total_errors = sum(s.error_count for s in self._keys)
        
        return {
            "key_count": len(self._keys),
            "total_requests": total_requests,
            "total_success": total_success,
            "total_errors": total_errors,
            "success_rate": f"{total_success / total_requests * 100:.1f}%" 
                if total_requests > 0 else "N/A",
        }
    
    def print_stats(self):
        """打印统计信息"""
        print(f"\n{'=' * 60}")
        print("Firecrawl API Key Pool 统计")
        print(f"{'=' * 60}")
        
        total = self.get_total_stats()
        print(f"Key数量: {total['key_count']}")
        print(f"总请求: {total['total_requests']}")
        print(f"成功: {total['total_success']}")
        print(f"失败: {total['total_errors']}")
        print(f"成功率: {total['success_rate']}")
        
        print(f"\n{'=' * 60}")
        print("各Key详情:")
        print(f"{'=' * 60}")
        
        for i, stats in enumerate(self.get_stats(), 1):
            print(f"\nKey {i}: {stats['key']}")
            print(f"  请求: {stats['request_count']}, 成功: {stats['success_count']}, 失败: {stats['error_count']}")
            print(f"  成功率: {stats['success_rate']}")
            if stats['last_error']:
                print(f"  最后错误: {stats['last_error']}")
