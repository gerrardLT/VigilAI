"""
VigilAI EnterpriseScraper单元测试
测试企业开发者平台爬虫基本功能

Validates: Requirements 15.1, 15.2
"""

import pytest
from datetime import datetime
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scrapers.enterprise_scraper import EnterpriseScraper
from models import Activity


def create_test_scraper(source_id='huawei_developer', config_override=None):
    """创建测试用爬虫实例"""
    config = {
        'name': 'Test Enterprise Scraper',
        'url': 'https://developer.huawei.com',
        'type': 'enterprise',
        'category': 'hackathon',
    }
    if config_override:
        config.update(config_override)
    return EnterpriseScraper(source_id, config)


class TestEnterpriseScraperInit:
    """EnterpriseScraper初始化测试"""
    
    def test_basic_init(self):
        """测试基本初始化"""
        scraper = create_test_scraper()
        assert scraper.source_id == 'huawei_developer'
        assert scraper.source_type == 'enterprise'
    
    def test_init_with_api_config(self):
        """测试带API配置初始化"""
        scraper = create_test_scraper(config_override={
            'api_url': 'https://api.example.com/events'
        })
        assert scraper.config.get('api_url') == 'https://api.example.com/events'


class TestEnterpriseScraperAttributes:
    """EnterpriseScraper属性测试"""
    
    def test_source_name(self):
        """测试source_name属性"""
        scraper = create_test_scraper()
        assert scraper.source_name == 'Test Enterprise Scraper'
    
    def test_source_url(self):
        """测试source_url属性"""
        scraper = create_test_scraper()
        assert scraper.source_url == 'https://developer.huawei.com'
    
    def test_category(self):
        """测试category属性"""
        scraper = create_test_scraper()
        assert scraper.category == 'hackathon'


class TestEnterpriseScraperMethods:
    """EnterpriseScraper方法测试"""
    
    def test_normalize_text(self):
        """测试文本标准化"""
        scraper = create_test_scraper()
        
        assert scraper._normalize_text('  华为开发者大赛  ') == '华为开发者大赛'
        assert scraper._normalize_text(None) == ''
    
    def test_normalize_date(self):
        """测试日期标准化"""
        scraper = create_test_scraper()
        
        result = scraper._normalize_date('2025-12-31')
        assert result is not None
        assert '2025' in result
    
    def test_normalize_prize(self):
        """测试奖金标准化"""
        scraper = create_test_scraper()
        
        assert scraper._normalize_prize('$10,000') == 10000.0
        assert scraper._normalize_prize(5000) == 5000.0


class TestEnterpriseScraperCreateActivity:
    """EnterpriseScraper创建活动测试"""
    
    def test_create_activity_basic(self):
        """测试基本活动创建"""
        scraper = create_test_scraper()
        
        activity = scraper.create_activity(
            url='https://developer.huawei.com/event/123',
            title='华为开发者大赛',
            description='创新挑战赛',
        )
        
        assert isinstance(activity, Activity)
        assert activity.title == '华为开发者大赛'
        assert activity.source_name == 'Test Enterprise Scraper'
    
    def test_create_activity_with_prize(self):
        """测试带奖金的活动创建"""
        scraper = create_test_scraper()
        
        activity = scraper.create_activity(
            url='https://developer.huawei.com/event/123',
            title='华为开发者大赛',
            prize_amount=1000000,
            prize_currency='CNY',
        )
        
        assert activity.prize is not None
        assert activity.prize.amount == 1000000
    
    def test_create_activity_with_tags(self):
        """测试带标签的活动创建"""
        scraper = create_test_scraper()
        
        activity = scraper.create_activity(
            url='https://developer.huawei.com/event/123',
            title='华为开发者大赛',
            tags=['enterprise', 'huawei', 'competition'],
        )
        
        assert 'enterprise' in activity.tags
        assert 'huawei' in activity.tags


class TestEnterpriseScraperErrorHandling:
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
