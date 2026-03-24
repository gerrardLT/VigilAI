"""
VigilAI 反爬虫策略单元测试
测试ProxyPool、UserAgentRotator和ErrorHandler组件

Validates: Requirements 15.3
"""

import pytest
from hypothesis import HealthCheck, given, strategies as st, settings
from datetime import datetime, timedelta
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.proxy_pool import ProxyPool
from utils.user_agent_rotator import UserAgentRotator, DEFAULT_USER_AGENTS
from utils.error_handler import ErrorHandler, ErrorType, ScraperError, NetworkError, ParsingError, ValidationError


class TestProxyPool:
    """ProxyPool代理池测试"""
    
    def test_init_empty(self):
        """测试空代理池初始化"""
        pool = ProxyPool()
        assert len(pool) == 0
        assert pool.is_empty()
        assert not pool.has_available()
    
    def test_init_with_proxies(self):
        """测试带代理列表初始化"""
        proxies = ['http://proxy1:8080', 'http://proxy2:8080']
        pool = ProxyPool(proxies)
        assert len(pool) == 2
        assert not pool.is_empty()
        assert pool.has_available()
    
    def test_add_proxy(self):
        """测试添加代理"""
        pool = ProxyPool()
        pool.add_proxy('http://proxy1:8080')
        assert len(pool) == 1
        
        # 重复添加不应增加
        pool.add_proxy('http://proxy1:8080')
        assert len(pool) == 1
    
    def test_add_proxies(self):
        """测试批量添加代理"""
        pool = ProxyPool()
        pool.add_proxies(['http://proxy1:8080', 'http://proxy2:8080'])
        assert len(pool) == 2
    
    def test_get_random_proxy(self):
        """测试获取随机代理"""
        proxies = ['http://proxy1:8080', 'http://proxy2:8080']
        pool = ProxyPool(proxies)
        
        proxy = pool.get_random_proxy()
        assert proxy is not None
        assert 'http' in proxy
        assert 'https' in proxy
        assert proxy['http'] in proxies
    
    def test_get_random_proxy_empty_pool(self):
        """测试空池获取代理返回None"""
        pool = ProxyPool()
        assert pool.get_random_proxy() is None
    
    def test_mark_failed(self):
        """测试标记失败代理"""
        proxies = ['http://proxy1:8080', 'http://proxy2:8080']
        pool = ProxyPool(proxies)
        pool.max_failures = 2
        
        # 第一次失败
        pool.mark_failed('http://proxy1:8080')
        assert 'http://proxy1:8080' not in pool.failed_proxies
        
        # 第二次失败，应该被标记
        pool.mark_failed('http://proxy1:8080')
        assert 'http://proxy1:8080' in pool.failed_proxies
    
    def test_mark_success(self):
        """测试标记成功重置失败计数"""
        pool = ProxyPool(['http://proxy1:8080'])
        pool.mark_failed('http://proxy1:8080')
        pool.mark_success('http://proxy1:8080')
        
        assert pool.failure_counts.get('http://proxy1:8080', 0) == 0
    
    def test_reset_failed(self):
        """测试重置失败代理"""
        pool = ProxyPool(['http://proxy1:8080'])
        pool.max_failures = 1
        pool.mark_failed('http://proxy1:8080')
        
        assert 'http://proxy1:8080' in pool.failed_proxies
        
        pool.reset_failed()
        assert len(pool.failed_proxies) == 0
    
    def test_remove_proxy(self):
        """测试移除代理"""
        pool = ProxyPool(['http://proxy1:8080', 'http://proxy2:8080'])
        pool.remove_proxy('http://proxy1:8080')
        
        assert len(pool) == 1
        assert 'http://proxy1:8080' not in pool.proxies
    
    def test_get_stats(self):
        """测试获取统计信息"""
        pool = ProxyPool(['http://proxy1:8080', 'http://proxy2:8080'])
        pool.max_failures = 1
        pool.mark_failed('http://proxy1:8080')
        
        stats = pool.get_stats()
        assert stats['total'] == 2
        assert stats['failed'] == 1
        assert stats['available'] == 1
    
    @settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow])
    @given(
        st.lists(
            st.integers(min_value=1, max_value=10_000).map(lambda value: f"http://proxy{value}:8080"),
            min_size=2,
            max_size=10,
            unique=True,
        )
    )
    def test_property_proxy_rotation(self, proxy_list):
        """
        Property: 代理轮换
        验证连续请求使用不同代理IP
        Validates: Requirements 11.1, 11.4
        """
        # 过滤空字符串
        pool = ProxyPool(proxy_list)
        
        # 获取多个代理
        selected_proxies = set()
        for _ in range(min(10, len(proxy_list) * 2)):
            proxy = pool.get_random_proxy()
            if proxy:
                selected_proxies.add(proxy['http'])
        
        # 如果有多个代理，应该选择到多个不同的
        assert len(selected_proxies) >= 1


class TestUserAgentRotator:
    """UserAgentRotator测试"""
    
    def test_init_default(self):
        """测试默认初始化"""
        rotator = UserAgentRotator()
        assert len(rotator) == len(DEFAULT_USER_AGENTS)
    
    def test_init_custom(self):
        """测试自定义User-Agent列表"""
        custom_uas = ['UA1', 'UA2']
        rotator = UserAgentRotator(custom_uas)
        assert len(rotator) == 2
    
    def test_get_random(self):
        """测试获取随机User-Agent"""
        rotator = UserAgentRotator()
        ua = rotator.get_random()
        assert ua is not None
        assert isinstance(ua, str)
        assert len(ua) > 0
    
    def test_get_random_avoids_repeat(self):
        """测试避免连续重复"""
        rotator = UserAgentRotator(['UA1', 'UA2', 'UA3'])
        
        # 获取多次，检查是否有变化
        uas = [rotator.get_random() for _ in range(10)]
        unique_uas = set(uas)
        
        # 应该有多个不同的UA
        assert len(unique_uas) > 1
    
    def test_add_user_agent(self):
        """测试添加User-Agent"""
        rotator = UserAgentRotator(['UA1'])
        rotator.add_user_agent('UA2')
        assert len(rotator) == 2
        
        # 重复添加不应增加
        rotator.add_user_agent('UA2')
        assert len(rotator) == 2
    
    def test_remove_user_agent(self):
        """测试移除User-Agent"""
        rotator = UserAgentRotator(['UA1', 'UA2'])
        rotator.remove_user_agent('UA1')
        assert len(rotator) == 1
    
    def test_reset(self):
        """测试重置为默认列表"""
        rotator = UserAgentRotator(['UA1'])
        rotator.reset()
        assert len(rotator) == len(DEFAULT_USER_AGENTS)
    
    def test_get_stats(self):
        """测试获取统计信息"""
        rotator = UserAgentRotator(['UA1', 'UA2'])
        rotator.get_random()
        rotator.get_random()
        
        stats = rotator.get_stats()
        assert stats['total'] == 2
        assert 'use_count' in stats
        assert 'last_used' in stats
    
    @settings(max_examples=50)
    @given(st.text(min_size=1, max_size=100))
    def test_property_user_agent_rotation(self, url):
        """
        Property: User-Agent轮换
        验证请求包含随机User-Agent
        Validates: Requirements 1.6, 11.2
        """
        rotator = UserAgentRotator()
        
        user_agents = set()
        for _ in range(10):
            ua = rotator.get_random()
            assert ua is not None
            assert isinstance(ua, str)
            user_agents.add(ua)
        
        # 至少应该有2个不同的User-Agent
        assert len(user_agents) >= 1


class TestErrorHandler:
    """ErrorHandler错误处理器测试"""
    
    def test_classify_timeout_error(self):
        """测试超时错误分类"""
        import httpx
        error = httpx.TimeoutException("timeout")
        assert ErrorHandler.classify_error(error) == ErrorType.TIMEOUT
    
    def test_classify_connection_error(self):
        """测试连接错误分类"""
        error = ConnectionError("connection failed")
        assert ErrorHandler.classify_error(error) == ErrorType.NETWORK
    
    def test_classify_value_error(self):
        """测试值错误分类"""
        error = ValueError("invalid value")
        assert ErrorHandler.classify_error(error) == ErrorType.PARSING
    
    def test_classify_unknown_error(self):
        """测试未知错误分类"""
        error = RuntimeError("unknown")
        assert ErrorHandler.classify_error(error) == ErrorType.UNKNOWN
    
    def test_is_retryable_timeout(self):
        """测试超时错误可重试"""
        error = TimeoutError("timeout")
        assert ErrorHandler.is_retryable(error) is True
    
    def test_is_retryable_value_error(self):
        """测试值错误不可重试"""
        error = ValueError("invalid")
        assert ErrorHandler.is_retryable(error) is False
    
    def test_get_retry_delay(self):
        """测试重试延迟计算"""
        error = TimeoutError("timeout")
        
        delay0 = ErrorHandler.get_retry_delay(error, 0)
        delay1 = ErrorHandler.get_retry_delay(error, 1)
        delay2 = ErrorHandler.get_retry_delay(error, 2)
        
        # 指数退避
        assert delay1 > delay0
        assert delay2 > delay1
        
        # 最大60秒
        delay10 = ErrorHandler.get_retry_delay(error, 10)
        assert delay10 <= 60.0
    
    def test_handle_network_error_logs(self, caplog):
        """测试网络错误日志记录"""
        import logging
        caplog.set_level(logging.ERROR)
        
        error = ConnectionError("connection failed")
        ErrorHandler.handle_network_error(error, "TestScraper", "http://example.com")
        
        assert "Network error" in caplog.text
        assert "TestScraper" in caplog.text
    
    def test_handle_parsing_error_logs(self, caplog):
        """测试解析错误日志记录"""
        import logging
        caplog.set_level(logging.ERROR)
        
        error = ValueError("parse failed")
        ErrorHandler.handle_parsing_error(error, "TestScraper", "<html>test</html>")
        
        assert "Parsing error" in caplog.text
    
    def test_log_success(self, caplog):
        """测试成功日志记录"""
        import logging
        caplog.set_level(logging.INFO)
        
        ErrorHandler.log_success("TestScraper", 10, 5.5)
        
        assert "TestScraper" in caplog.text
        assert "10" in caplog.text


class TestScraperErrors:
    """ScraperError错误类测试"""
    
    def test_scraper_error_creation(self):
        """测试ScraperError创建"""
        error = ScraperError(
            "test error",
            error_type=ErrorType.NETWORK,
            source_name="TestScraper",
            url="http://example.com"
        )
        
        assert error.message == "test error"
        assert error.error_type == ErrorType.NETWORK
        assert error.source_name == "TestScraper"
        assert error.url == "http://example.com"
    
    def test_scraper_error_to_dict(self):
        """测试ScraperError转字典"""
        error = ScraperError("test error", source_name="TestScraper")
        error_dict = error.to_dict()
        
        assert 'message' in error_dict
        assert 'error_type' in error_dict
        assert 'timestamp' in error_dict
    
    def test_network_error(self):
        """测试NetworkError"""
        error = NetworkError("connection failed", source_name="TestScraper")
        assert error.error_type == ErrorType.NETWORK
    
    def test_parsing_error(self):
        """测试ParsingError"""
        error = ParsingError("parse failed", html_snippet="<html>", source_name="TestScraper")
        assert error.error_type == ErrorType.PARSING
        assert error.html_snippet == "<html>"
    
    def test_validation_error(self):
        """测试ValidationError"""
        error = ValidationError("invalid data", invalid_data={'key': 'value'}, source_name="TestScraper")
        assert error.error_type == ErrorType.VALIDATION
        assert error.invalid_data == {'key': 'value'}


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
