"""
VigilAI Scheduler单元测试和属性测试
测试调度器的动态注册、状态维护和告警机制

Validates: Requirements 13.1, 13.2, 13.4, 13.5, 11.5, 12.5, 15.1, 15.2
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scheduler import TaskScheduler, ScraperState
from scrapers.base import BaseScraper
from data_manager import DataManager


class ConcreteTestScraper(BaseScraper):
    """用于测试的具体爬虫实现"""
    async def scrape(self):
        return []


def create_mock_data_manager():
    """创建模拟的DataManager"""
    mock = MagicMock(spec=DataManager)
    mock.update_source_status = MagicMock()
    mock.add_activity = MagicMock(return_value=True)
    return mock


class TestScraperState:
    """ScraperState数据类测试"""
    
    def test_init_default(self):
        """测试默认初始化"""
        state = ScraperState(source_id='test')
        
        assert state.source_id == 'test'
        assert state.last_run is None
        assert state.error_count == 0
        assert state.consecutive_failures == 0
        assert state.is_paused is False
    
    def test_to_dict(self):
        """测试转换为字典"""
        state = ScraperState(
            source_id='test',
            error_count=5,
            consecutive_failures=3
        )
        
        result = state.to_dict()
        
        assert result['source_id'] == 'test'
        assert result['error_count'] == 5
        assert result['consecutive_failures'] == 3
    
    def test_to_dict_with_dates(self):
        """测试带日期的字典转换"""
        now = datetime.utcnow()
        state = ScraperState(
            source_id='test',
            last_run=now,
            last_success=now
        )
        
        result = state.to_dict()
        
        assert result['last_run'] is not None
        assert result['last_success'] is not None


class TestTaskSchedulerInit:
    """TaskScheduler初始化测试"""
    
    def test_basic_init(self):
        """测试基本初始化"""
        dm = create_mock_data_manager()
        scheduler = TaskScheduler(dm)
        
        assert scheduler.data_manager == dm
        assert scheduler._running is False
        assert len(scheduler.scraper_states) == 0
    
    def test_default_scraper_classes(self):
        """测试默认爬虫类型映射"""
        dm = create_mock_data_manager()
        scheduler = TaskScheduler(dm)
        
        # 验证所有新爬虫类型已注册
        assert 'airdrop' in scheduler._scraper_classes
        assert 'data_competition' in scheduler._scraper_classes
        assert 'hackathon_aggregator' in scheduler._scraper_classes
        assert 'bounty' in scheduler._scraper_classes
        assert 'enterprise' in scheduler._scraper_classes
        assert 'government' in scheduler._scraper_classes
        assert 'design_competition' in scheduler._scraper_classes
        assert 'coding_competition' in scheduler._scraper_classes


class TestDynamicScraperRegistration:
    """动态爬虫注册测试 - Validates: Requirements 13.4"""
    
    def test_register_scraper_type(self):
        """测试注册新爬虫类型"""
        dm = create_mock_data_manager()
        scheduler = TaskScheduler(dm)
        
        scheduler.register_scraper_type('custom', ConcreteTestScraper)
        
        assert 'custom' in scheduler._scraper_classes
        assert scheduler._scraper_classes['custom'] == ConcreteTestScraper
    
    def test_register_invalid_scraper_type(self):
        """测试注册无效爬虫类型"""
        dm = create_mock_data_manager()
        scheduler = TaskScheduler(dm)
        
        with pytest.raises(ValueError):
            scheduler.register_scraper_type('invalid', dict)
    
    def test_unregister_scraper_type(self):
        """测试注销爬虫类型"""
        dm = create_mock_data_manager()
        scheduler = TaskScheduler(dm)
        
        scheduler.register_scraper_type('custom', ConcreteTestScraper)
        result = scheduler.unregister_scraper_type('custom')
        
        assert result is True
        assert 'custom' not in scheduler._scraper_classes
    
    def test_unregister_nonexistent_type(self):
        """测试注销不存在的类型"""
        dm = create_mock_data_manager()
        scheduler = TaskScheduler(dm)
        
        result = scheduler.unregister_scraper_type('nonexistent')
        assert result is False
    
    def test_get_registered_types(self):
        """测试获取已注册类型"""
        dm = create_mock_data_manager()
        scheduler = TaskScheduler(dm)
        
        types = scheduler.get_registered_types()
        
        assert isinstance(types, dict)
        assert 'rss' in types
        assert 'web' in types
    
    @settings(max_examples=20)
    @given(st.text(min_size=1, max_size=20, alphabet='abcdefghijklmnopqrstuvwxyz_'))
    def test_property_dynamic_registration(self, scraper_type):
        """
        Property 13: Dynamic Scraper Registration
        验证动态注册的爬虫类型可以被正确使用
        Validates: Requirements 13.4
        """
        assume(scraper_type.strip())
        
        dm = create_mock_data_manager()
        scheduler = TaskScheduler(dm)
        
        # 注册新类型
        scheduler.register_scraper_type(scraper_type, ConcreteTestScraper)
        
        # 验证注册成功
        assert scraper_type in scheduler._scraper_classes
        assert scheduler._scraper_classes[scraper_type] == ConcreteTestScraper


class TestScraperStateManagement:
    """爬虫状态管理测试 - Validates: Requirements 13.5"""
    
    def test_get_or_create_state(self):
        """测试获取或创建状态"""
        dm = create_mock_data_manager()
        scheduler = TaskScheduler(dm)
        
        state = scheduler._get_or_create_state('test_source')
        
        assert state.source_id == 'test_source'
        assert 'test_source' in scheduler.scraper_states
    
    def test_get_scraper_state(self):
        """测试获取爬虫状态"""
        dm = create_mock_data_manager()
        scheduler = TaskScheduler(dm)
        
        scheduler._get_or_create_state('test_source')
        state = scheduler.get_scraper_state('test_source')
        
        assert state is not None
        assert state.source_id == 'test_source'
    
    def test_get_all_states(self):
        """测试获取所有状态"""
        dm = create_mock_data_manager()
        scheduler = TaskScheduler(dm)
        
        scheduler._get_or_create_state('source1')
        scheduler._get_or_create_state('source2')
        
        states = scheduler.get_all_states()
        
        assert len(states) == 2
        assert 'source1' in states
        assert 'source2' in states
    
    def test_reset_scraper_state(self):
        """测试重置爬虫状态"""
        dm = create_mock_data_manager()
        scheduler = TaskScheduler(dm)
        
        state = scheduler._get_or_create_state('test_source')
        state.error_count = 10
        
        result = scheduler.reset_scraper_state('test_source')
        
        assert result is True
        assert scheduler.scraper_states['test_source'].error_count == 0
    
    @settings(max_examples=20)
    @given(st.text(min_size=1, max_size=30, alphabet='abcdefghijklmnopqrstuvwxyz_'))
    def test_property_state_maintenance(self, source_id):
        """
        Property 14: Scraper State Maintenance
        验证每个信息源维护独立的调度状态
        Validates: Requirements 13.5
        """
        assume(source_id.strip())
        
        dm = create_mock_data_manager()
        scheduler = TaskScheduler(dm)
        
        # 创建状态
        state = scheduler._get_or_create_state(source_id)
        
        # 验证状态独立
        assert state.source_id == source_id
        assert source_id in scheduler.scraper_states
        
        # 修改状态
        state.error_count = 5
        
        # 验证修改被保留
        retrieved_state = scheduler.get_scraper_state(source_id)
        assert retrieved_state.error_count == 5


class TestAlertMechanism:
    """告警机制测试 - Validates: Requirements 11.5, 12.5"""
    
    def test_handle_scraper_success(self):
        """测试处理爬虫成功"""
        dm = create_mock_data_manager()
        scheduler = TaskScheduler(dm)
        
        # 先模拟一些失败
        state = scheduler._get_or_create_state('test_source')
        state.consecutive_failures = 2
        
        # 处理成功
        scheduler._handle_scraper_success('test_source', 10)
        
        # 验证状态重置
        assert state.consecutive_failures == 0
        assert state.last_activity_count == 10
        assert state.is_paused is False
    
    def test_handle_scraper_failure(self):
        """测试处理爬虫失败"""
        dm = create_mock_data_manager()
        scheduler = TaskScheduler(dm)
        
        scheduler._handle_scraper_failure('test_source', 'Test error')
        
        state = scheduler.get_scraper_state('test_source')
        assert state.error_count == 1
        assert state.consecutive_failures == 1
        assert state.last_error == 'Test error'
    
    def test_alert_triggered_on_threshold(self):
        """测试达到阈值触发告警"""
        dm = create_mock_data_manager()
        scheduler = TaskScheduler(dm)
        
        alert_called = []
        def alert_callback(source_id, state, message):
            alert_called.append((source_id, message))
        
        scheduler.register_alert_callback(alert_callback)
        
        # 连续失败3次
        for i in range(3):
            scheduler._handle_scraper_failure('test_source', f'Error {i+1}')
        
        # 验证告警被触发
        assert len(alert_called) == 1
        assert alert_called[0][0] == 'test_source'
    
    def test_scraper_paused_after_threshold(self):
        """测试达到阈值后爬虫暂停"""
        dm = create_mock_data_manager()
        scheduler = TaskScheduler(dm)
        
        # 连续失败3次
        for i in range(3):
            scheduler._handle_scraper_failure('test_source', f'Error {i+1}')
        
        state = scheduler.get_scraper_state('test_source')
        assert state.is_paused is True
        assert state.pause_until is not None
    
    def test_force_unpause(self):
        """测试强制解除暂停"""
        dm = create_mock_data_manager()
        scheduler = TaskScheduler(dm)
        
        # 触发暂停
        for i in range(3):
            scheduler._handle_scraper_failure('test_source', f'Error {i+1}')
        
        # 强制解除
        result = scheduler.force_unpause('test_source')
        
        assert result is True
        state = scheduler.get_scraper_state('test_source')
        assert state.is_paused is False
    
    def test_get_paused_scrapers(self):
        """测试获取暂停的爬虫"""
        dm = create_mock_data_manager()
        scheduler = TaskScheduler(dm)
        
        # 触发暂停
        for i in range(3):
            scheduler._handle_scraper_failure('test_source', f'Error {i+1}')
        
        paused = scheduler.get_paused_scrapers()
        
        assert len(paused) == 1
        assert paused[0]['source_id'] == 'test_source'
    
    def test_get_failed_scrapers(self):
        """测试获取失败的爬虫"""
        dm = create_mock_data_manager()
        scheduler = TaskScheduler(dm)
        
        scheduler._handle_scraper_failure('source1', 'Error 1')
        scheduler._handle_scraper_failure('source1', 'Error 2')
        scheduler._handle_scraper_failure('source2', 'Error 1')
        
        failed = scheduler.get_failed_scrapers(min_failures=2)
        
        assert len(failed) == 1
        assert failed[0]['source_id'] == 'source1'
    
    @settings(max_examples=20)
    @given(st.integers(min_value=1, max_value=10))
    def test_property_failure_alert_threshold(self, failure_count):
        """
        Property 11: Failure Alert Threshold
        验证连续失败达到阈值时触发告警
        Validates: Requirements 11.5, 12.5
        """
        dm = create_mock_data_manager()
        scheduler = TaskScheduler(dm)
        
        alert_triggered = []
        def alert_callback(source_id, state, message):
            alert_triggered.append(source_id)
        
        scheduler.register_alert_callback(alert_callback)
        
        # 模拟连续失败
        for i in range(failure_count):
            scheduler._handle_scraper_failure('test_source', f'Error {i+1}')
        
        # 验证告警触发条件
        if failure_count >= scheduler.FAILURE_ALERT_THRESHOLD:
            assert len(alert_triggered) >= 1
        else:
            assert len(alert_triggered) == 0


class TestScraperTypeMapping:
    """爬虫类型映射测试 - Validates: Requirements 13.1, 13.2"""
    
    @settings(max_examples=20)
    @given(st.sampled_from([
        'rss', 'web', 'web3', 'kaggle', 'api', 'tech_media',
        'airdrop', 'data_competition', 'hackathon_aggregator',
        'bounty', 'enterprise', 'government',
        'design_competition', 'coding_competition'
    ]))
    def test_property_scraper_type_mapping(self, scraper_type):
        """
        Property 13: Scraper Type Mapping
        验证所有爬虫类型都有对应的类映射
        Validates: Requirements 13.1, 13.2
        """
        dm = create_mock_data_manager()
        scheduler = TaskScheduler(dm)
        
        assert scraper_type in scheduler._scraper_classes
        assert issubclass(scheduler._scraper_classes[scraper_type], BaseScraper)


class TestCheckAndUnpause:
    """检查和解除暂停测试"""
    
    def test_check_unpause_not_paused(self):
        """测试未暂停的爬虫"""
        dm = create_mock_data_manager()
        scheduler = TaskScheduler(dm)
        
        state = scheduler._get_or_create_state('test_source')
        result = scheduler._check_and_unpause(state)
        
        assert result is True
    
    def test_check_unpause_still_paused(self):
        """测试仍在暂停中的爬虫"""
        dm = create_mock_data_manager()
        scheduler = TaskScheduler(dm)
        
        state = scheduler._get_or_create_state('test_source')
        state.is_paused = True
        state.pause_until = datetime.utcnow() + timedelta(minutes=30)
        
        result = scheduler._check_and_unpause(state)
        
        assert result is False
    
    def test_check_unpause_expired(self):
        """测试暂停时间已过的爬虫"""
        dm = create_mock_data_manager()
        scheduler = TaskScheduler(dm)
        
        state = scheduler._get_or_create_state('test_source')
        state.is_paused = True
        state.pause_until = datetime.utcnow() - timedelta(minutes=1)
        
        result = scheduler._check_and_unpause(state)
        
        assert result is True
        assert state.is_paused is False


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
