"""
VigilAI CodingCompetitionScraper单元测试
测试编程竞赛爬虫基本功能

Validates: Requirements 15.1, 15.2
"""

import pytest
from datetime import datetime
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scrapers.coding_competition_scraper import CodingCompetitionScraper
from models import Activity


def create_test_scraper(source_id='hackerearth', config_override=None):
    """创建测试用爬虫实例"""
    config = {
        'name': 'Test Coding Competition Scraper',
        'url': 'https://www.hackerearth.com/challenges',
        'type': 'coding_competition',
        'category': 'competition',
    }
    if config_override:
        config.update(config_override)
    return CodingCompetitionScraper(source_id, config)


class TestCodingCompetitionScraperInit:
    """CodingCompetitionScraper初始化测试"""
    
    def test_basic_init(self):
        """测试基本初始化"""
        scraper = create_test_scraper()
        assert scraper.source_id == 'hackerearth'
        assert scraper.source_type == 'coding_competition'
    
    def test_init_topcoder(self):
        """测试TopCoder初始化"""
        scraper = create_test_scraper('topcoder', config_override={
            'name': 'TopCoder',
            'url': 'https://www.topcoder.com/challenges'
        })
        assert scraper.source_id == 'topcoder'


class TestCodingCompetitionScraperAttributes:
    """CodingCompetitionScraper属性测试"""
    
    def test_source_name(self):
        """测试source_name属性"""
        scraper = create_test_scraper()
        assert scraper.source_name == 'Test Coding Competition Scraper'
    
    def test_source_url(self):
        """测试source_url属性"""
        scraper = create_test_scraper()
        assert scraper.source_url == 'https://www.hackerearth.com/challenges'
    
    def test_category(self):
        """测试category属性"""
        scraper = create_test_scraper()
        assert scraper.category == 'competition'


class TestCodingCompetitionScraperMethods:
    """CodingCompetitionScraper方法测试"""
    
    def test_normalize_text(self):
        """测试文本标准化"""
        scraper = create_test_scraper()
        
        assert scraper._normalize_text('  Coding Challenge  ') == 'Coding Challenge'
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


class TestCompetitionStatusMarking:
    """竞赛状态标记测试"""
    
    def test_is_active_status_active(self):
        """测试活跃状态识别"""
        scraper = create_test_scraper()
        
        assert scraper._is_active_status('active') is True
        assert scraper._is_active_status('Active') is True
        assert scraper._is_active_status('ACTIVE') is True
    
    def test_is_active_status_live(self):
        """测试进行中状态识别"""
        scraper = create_test_scraper()
        
        assert scraper._is_active_status('live') is True
        assert scraper._is_active_status('ongoing') is True
        assert scraper._is_active_status('running') is True
    
    def test_is_active_status_chinese(self):
        """测试中文状态识别"""
        scraper = create_test_scraper()
        
        assert scraper._is_active_status('进行中') is True
        assert scraper._is_active_status('正在进行') is True
    
    def test_is_active_status_inactive(self):
        """测试非活跃状态识别"""
        scraper = create_test_scraper()
        
        assert scraper._is_active_status('upcoming') is False
        assert scraper._is_active_status('ended') is False
        assert scraper._is_active_status('') is False


class TestCodingCompetitionScraperCreateActivity:
    """CodingCompetitionScraper创建活动测试"""
    
    def test_create_activity_basic(self):
        """测试基本活动创建"""
        scraper = create_test_scraper()
        
        activity = scraper.create_activity(
            url='https://www.hackerearth.com/challenge/123',
            title='Coding Challenge',
            description='Algorithm challenge',
        )
        
        assert isinstance(activity, Activity)
        assert activity.title == 'Coding Challenge'
        assert activity.source_name == 'Test Coding Competition Scraper'
    
    def test_create_activity_with_prize(self):
        """测试带奖金的活动创建"""
        scraper = create_test_scraper()
        
        activity = scraper.create_activity(
            url='https://www.hackerearth.com/challenge/123',
            title='Coding Challenge',
            prize_amount=1000,
            prize_currency='USD',
        )
        
        assert activity.prize is not None
        assert activity.prize.amount == 1000
    
    def test_create_activity_with_tags(self):
        """测试带标签的活动创建"""
        scraper = create_test_scraper()
        
        activity = scraper.create_activity(
            url='https://www.hackerearth.com/challenge/123',
            title='Coding Challenge',
            tags=['coding', 'algorithm', 'hackerearth'],
        )
        
        assert 'coding' in activity.tags
        assert 'algorithm' in activity.tags


class TestCodingCompetitionScraperErrorHandling:
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
