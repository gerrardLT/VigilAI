"""
VigilAI BountyScraper单元测试
测试漏洞赏金爬虫基本功能

Validates: Requirements 15.1, 15.2
"""

import pytest
from unittest.mock import AsyncMock, patch
from datetime import datetime
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scrapers.bounty_scraper import BountyScraper
from models import Activity


def create_test_scraper(source_id='hackerone', config_override=None):
    """创建测试用爬虫实例"""
    config = {
        'name': 'Test Bounty Scraper',
        'url': 'https://hackerone.com/directory/programs',
        'type': 'bounty',
        'category': 'bounty',
    }
    if config_override:
        config.update(config_override)
    return BountyScraper(source_id, config)


class TestBountyScraperInit:
    """BountyScraper初始化测试"""
    
    def test_basic_init(self):
        """测试基本初始化"""
        scraper = create_test_scraper()
        assert scraper.source_id == 'hackerone'
        assert scraper.source_type == 'bounty'
    
    def test_source_name(self):
        """测试source_name属性"""
        scraper = create_test_scraper()
        assert scraper.source_name == 'Test Bounty Scraper'
    
    def test_source_url(self):
        """测试source_url属性"""
        scraper = create_test_scraper()
        assert scraper.source_url == 'https://hackerone.com/directory/programs'


class TestBountyScraperMethods:
    """BountyScraper方法测试"""
    
    def test_normalize_text(self):
        """测试文本标准化"""
        scraper = create_test_scraper()
        
        assert scraper._normalize_text('  Bug Bounty Program  ') == 'Bug Bounty Program'
    
    def test_normalize_prize(self):
        """测试奖金标准化"""
        scraper = create_test_scraper()
        
        assert scraper._normalize_prize('$10,000') == 10000.0
    
    def test_create_activity(self):
        """测试创建活动"""
        scraper = create_test_scraper()
        
        activity = scraper.create_activity(
            url='https://hackerone.com/test-program',
            title='Test Bug Bounty',
            description='Security research program',
        )
        
        assert isinstance(activity, Activity)
        assert activity.title == 'Test Bug Bounty'
    
    def test_create_activity_with_prize(self):
        """测试带奖金的活动创建"""
        scraper = create_test_scraper()
        
        activity = scraper.create_activity(
            url='https://hackerone.com/test-program',
            title='Test Bug Bounty',
            prize_amount=10000,
            prize_currency='USD',
        )
        
        assert activity.prize is not None
        assert activity.prize.amount == 10000


class TestBountyScraperErrorHandling:
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
