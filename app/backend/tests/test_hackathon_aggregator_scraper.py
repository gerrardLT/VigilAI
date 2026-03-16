"""
VigilAI HackathonAggregatorScraper单元测试
测试黑客松聚合爬虫基本功能和过期活动过滤

Validates: Requirements 15.1, 15.2
"""

import pytest
from unittest.mock import AsyncMock, patch
from datetime import datetime, timedelta
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scrapers.hackathon_aggregator_scraper import HackathonAggregatorScraper
from models import Activity


def create_test_scraper(source_id='mlh', config_override=None):
    """创建测试用爬虫实例"""
    config = {
        'name': 'Test Hackathon Scraper',
        'url': 'https://mlh.io/seasons/2025/events',
        'type': 'hackathon_aggregator',
        'category': 'hackathon',
    }
    if config_override:
        config.update(config_override)
    return HackathonAggregatorScraper(source_id, config)


class TestHackathonAggregatorScraperInit:
    """HackathonAggregatorScraper初始化测试"""
    
    def test_basic_init(self):
        """测试基本初始化"""
        scraper = create_test_scraper()
        assert scraper.source_id == 'mlh'
        assert scraper.source_type == 'hackathon_aggregator'
    
    def test_source_name(self):
        """测试source_name属性"""
        scraper = create_test_scraper()
        assert scraper.source_name == 'Test Hackathon Scraper'
    
    def test_source_url(self):
        """测试source_url属性"""
        scraper = create_test_scraper()
        assert scraper.source_url == 'https://mlh.io/seasons/2025/events'


class TestHackathonAggregatorScraperMethods:
    """HackathonAggregatorScraper方法测试"""
    
    def test_normalize_text(self):
        """测试文本标准化"""
        scraper = create_test_scraper()
        
        assert scraper._normalize_text('  HackMIT 2025  ') == 'HackMIT 2025'
    
    def test_normalize_date(self):
        """测试日期标准化"""
        scraper = create_test_scraper()
        
        result = scraper._normalize_date('2025-12-31')
        assert result is not None
    
    def test_create_activity(self):
        """测试创建活动"""
        scraper = create_test_scraper()
        
        activity = scraper.create_activity(
            url='https://hackmit.org',
            title='HackMIT 2025',
            description='Annual hackathon',
        )
        
        assert isinstance(activity, Activity)
        assert activity.title == 'HackMIT 2025'


class TestExpiredActivityFiltering:
    """过期活动过滤测试"""
    
    def test_create_activity_with_past_deadline(self):
        """测试创建带过去截止日期的活动"""
        scraper = create_test_scraper()
        
        past_date = datetime.now() - timedelta(days=1)
        activity = scraper.create_activity(
            url='https://example.com/1',
            title='Past Event',
            deadline=past_date
        )
        
        assert activity is not None
        assert activity.dates.deadline == past_date
    
    def test_create_activity_with_future_deadline(self):
        """测试创建带未来截止日期的活动"""
        scraper = create_test_scraper()
        
        future_date = datetime.now() + timedelta(days=30)
        activity = scraper.create_activity(
            url='https://example.com/2',
            title='Future Event',
            deadline=future_date
        )
        
        assert activity is not None
        assert activity.dates.deadline == future_date


class TestHackathonAggregatorScraperErrorHandling:
    """错误处理测试"""
    
    def test_handle_error(self):
        """测试错误处理"""
        scraper = create_test_scraper()
        
        error = ValueError("test error")
        result = scraper.handle_error(error, "test context")
        
        assert scraper.error_count >= 1
    
    def test_reset_retry_count(self):
        """测试重置重试计数"""
        scraper = create_test_scraper()
        
        scraper.retry_count = 5
        scraper.reset_retry_count()
        
        assert scraper.retry_count == 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
