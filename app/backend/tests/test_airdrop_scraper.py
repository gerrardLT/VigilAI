"""
VigilAI AirdropScraper单元测试
测试空投聚合爬虫基本功能

Validates: Requirements 15.1, 15.2, 15.4
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scrapers.airdrop_scraper import AirdropScraper
from models import Activity


def create_test_scraper(source_id='airdrops_io', config_override=None):
    """创建测试用爬虫实例"""
    config = {
        'name': 'Test Airdrop Scraper',
        'url': 'https://airdrops.io',
        'type': 'airdrop',
        'category': 'airdrop',
    }
    if config_override:
        config.update(config_override)
    return AirdropScraper(source_id, config)


class TestAirdropScraperInit:
    """AirdropScraper初始化测试"""
    
    def test_basic_init(self):
        """测试基本初始化"""
        scraper = create_test_scraper()
        assert scraper.source_id == 'airdrops_io'
        assert scraper.source_type == 'airdrop'
    
    def test_init_with_selenium(self):
        """测试带Selenium配置初始化"""
        scraper = create_test_scraper(config_override={'use_selenium': True})
        assert scraper.use_selenium is True
    
    def test_init_without_selenium(self):
        """测试不带Selenium配置初始化"""
        scraper = create_test_scraper(config_override={'use_selenium': False})
        assert scraper.use_selenium is False


class TestAirdropScraperAttributes:
    """AirdropScraper属性测试"""
    
    def test_source_name(self):
        """测试source_name属性"""
        scraper = create_test_scraper()
        assert scraper.source_name == 'Test Airdrop Scraper'
    
    def test_source_url(self):
        """测试source_url属性"""
        scraper = create_test_scraper()
        assert scraper.source_url == 'https://airdrops.io'
    
    def test_category(self):
        """测试category属性"""
        scraper = create_test_scraper()
        assert scraper.category == 'airdrop'


class TestAirdropScraperMethods:
    """AirdropScraper方法测试"""
    
    def test_normalize_text(self):
        """测试文本标准化"""
        scraper = create_test_scraper()
        
        assert scraper._normalize_text('  hello world  ') == 'hello world'
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


class TestAirdropScraperCreateActivity:
    """AirdropScraper创建活动测试"""
    
    def test_create_activity_basic(self):
        """测试基本活动创建"""
        scraper = create_test_scraper()
        
        activity = scraper.create_activity(
            url='https://example.com/airdrop',
            title='Test Airdrop',
            description='Free tokens',
        )
        
        assert isinstance(activity, Activity)
        assert activity.title == 'Test Airdrop'
        assert activity.source_name == 'Test Airdrop Scraper'
    
    def test_create_activity_with_prize(self):
        """测试带奖金的活动创建"""
        scraper = create_test_scraper()
        
        activity = scraper.create_activity(
            url='https://example.com/airdrop',
            title='Test Airdrop',
            prize_amount=1000,
            prize_currency='USD',
        )
        
        assert activity.prize is not None
        assert activity.prize.amount == 1000
    
    def test_create_activity_with_tags(self):
        """测试带标签的活动创建"""
        scraper = create_test_scraper()
        
        activity = scraper.create_activity(
            url='https://example.com/airdrop',
            title='Test Airdrop',
            tags=['airdrop', 'crypto', 'free'],
        )
        
        assert 'airdrop' in activity.tags
        assert 'crypto' in activity.tags


class TestAirdropScraperErrorHandling:
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
