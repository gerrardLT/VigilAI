"""
VigilAI GovernmentScraper单元测试
测试政府竞赛爬虫基本功能

Validates: Requirements 15.1, 15.2
"""

import pytest
from datetime import datetime
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scrapers.government_scraper import GovernmentScraper
from models import Activity


def create_test_scraper(source_id='challenge_gov', config_override=None):
    """创建测试用爬虫实例"""
    config = {
        'name': 'Test Government Scraper',
        'url': 'https://www.challenge.gov',
        'type': 'government',
        'category': 'competition',
    }
    if config_override:
        config.update(config_override)
    return GovernmentScraper(source_id, config)


class TestGovernmentScraperInit:
    """GovernmentScraper初始化测试"""
    
    def test_basic_init(self):
        """测试基本初始化"""
        scraper = create_test_scraper()
        assert scraper.source_id == 'challenge_gov'
        assert scraper.source_type == 'government'
    
    def test_init_china_innovation(self):
        """测试中国创新创业大赛初始化"""
        scraper = create_test_scraper('china_innovation', config_override={
            'name': '中国创新创业大赛',
            'url': 'http://www.cxcyds.com'
        })
        assert scraper.source_id == 'china_innovation'


class TestGovernmentScraperAttributes:
    """GovernmentScraper属性测试"""
    
    def test_source_name(self):
        """测试source_name属性"""
        scraper = create_test_scraper()
        assert scraper.source_name == 'Test Government Scraper'
    
    def test_source_url(self):
        """测试source_url属性"""
        scraper = create_test_scraper()
        assert scraper.source_url == 'https://www.challenge.gov'
    
    def test_category(self):
        """测试category属性"""
        scraper = create_test_scraper()
        assert scraper.category == 'competition'


class TestGovernmentScraperMethods:
    """GovernmentScraper方法测试"""
    
    def test_normalize_text(self):
        """测试文本标准化"""
        scraper = create_test_scraper()
        
        assert scraper._normalize_text('  创新创业大赛  ') == '创新创业大赛'
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
        
        assert scraper._normalize_prize('$100,000') == 100000.0
        assert scraper._normalize_prize(50000) == 50000.0


class TestGovernmentScraperCreateActivity:
    """GovernmentScraper创建活动测试"""
    
    def test_create_activity_basic(self):
        """测试基本活动创建"""
        scraper = create_test_scraper()
        
        activity = scraper.create_activity(
            url='https://www.challenge.gov/challenge/123',
            title='NASA Space Challenge',
            description='Space innovation challenge',
        )
        
        assert isinstance(activity, Activity)
        assert activity.title == 'NASA Space Challenge'
        assert activity.source_name == 'Test Government Scraper'
    
    def test_create_activity_with_prize(self):
        """测试带奖金的活动创建"""
        scraper = create_test_scraper()
        
        activity = scraper.create_activity(
            url='https://www.challenge.gov/challenge/123',
            title='NASA Space Challenge',
            prize_amount=100000,
            prize_currency='USD',
        )
        
        assert activity.prize is not None
        assert activity.prize.amount == 100000
    
    def test_create_activity_with_tags(self):
        """测试带标签的活动创建"""
        scraper = create_test_scraper()
        
        activity = scraper.create_activity(
            url='https://www.challenge.gov/challenge/123',
            title='NASA Space Challenge',
            tags=['government', 'challenge', 'usa'],
        )
        
        assert 'government' in activity.tags
        assert 'challenge' in activity.tags


class TestChineseEncodingHandling:
    """中文编码处理测试"""
    
    def test_normalize_chinese_text(self):
        """测试中文文本标准化"""
        scraper = create_test_scraper()
        
        text = '  中国创新创业大赛  '
        normalized = scraper._normalize_text(text)
        assert normalized == '中国创新创业大赛'
    
    def test_normalize_chinese_date(self):
        """测试中文日期标准化"""
        scraper = create_test_scraper()
        
        result = scraper._normalize_date('2025年12月31日')
        assert result is not None


class TestGovernmentScraperErrorHandling:
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
