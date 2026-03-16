"""
VigilAI DesignCompetitionScraper单元测试
测试设计竞赛爬虫基本功能

Validates: Requirements 15.1, 15.2
"""

import pytest
from datetime import datetime
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scrapers.design_competition_scraper import DesignCompetitionScraper
from models import Activity


def create_test_scraper(source_id='shejijingsai', config_override=None):
    """创建测试用爬虫实例"""
    config = {
        'name': 'Test Design Competition Scraper',
        'url': 'https://www.shejijingsai.com',
        'type': 'design_competition',
        'category': 'competition',
    }
    if config_override:
        config.update(config_override)
    return DesignCompetitionScraper(source_id, config)


class TestDesignCompetitionScraperInit:
    """DesignCompetitionScraper初始化测试"""
    
    def test_basic_init(self):
        """测试基本初始化"""
        scraper = create_test_scraper()
        assert scraper.source_id == 'shejijingsai'
        assert scraper.source_type == 'design_competition'


class TestDesignCompetitionScraperAttributes:
    """DesignCompetitionScraper属性测试"""
    
    def test_source_name(self):
        """测试source_name属性"""
        scraper = create_test_scraper()
        assert scraper.source_name == 'Test Design Competition Scraper'
    
    def test_source_url(self):
        """测试source_url属性"""
        scraper = create_test_scraper()
        assert scraper.source_url == 'https://www.shejijingsai.com'
    
    def test_category(self):
        """测试category属性"""
        scraper = create_test_scraper()
        assert scraper.category == 'competition'


class TestDesignCompetitionScraperMethods:
    """DesignCompetitionScraper方法测试"""
    
    def test_normalize_text(self):
        """测试文本标准化"""
        scraper = create_test_scraper()
        
        assert scraper._normalize_text('  UI设计大赛  ') == 'UI设计大赛'
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
        
        assert scraper._normalize_prize('¥100,000') == 100000.0
        assert scraper._normalize_prize(50000) == 50000.0


class TestDesignTypeExtraction:
    """设计类型提取测试"""
    
    def test_extract_design_type_ui(self):
        """测试提取UI设计类型"""
        scraper = create_test_scraper()
        
        tags = scraper._extract_design_type('UI设计', 'UI设计大赛')
        assert 'ui-ux' in tags
    
    def test_extract_design_type_graphic(self):
        """测试提取平面设计类型"""
        scraper = create_test_scraper()
        
        tags = scraper._extract_design_type('平面设计', '平面设计竞赛')
        assert 'graphic-design' in tags
    
    def test_extract_design_type_industrial(self):
        """测试提取工业设计类型"""
        scraper = create_test_scraper()
        
        tags = scraper._extract_design_type('工业设计', '工业设计大赛')
        assert 'industrial-design' in tags
    
    def test_extract_design_type_default(self):
        """测试默认设计类型"""
        scraper = create_test_scraper()
        
        tags = scraper._extract_design_type('', '普通竞赛')
        assert 'design' in tags
        assert 'competition' in tags


class TestDesignCompetitionScraperCreateActivity:
    """DesignCompetitionScraper创建活动测试"""
    
    def test_create_activity_basic(self):
        """测试基本活动创建"""
        scraper = create_test_scraper()
        
        activity = scraper.create_activity(
            url='https://www.shejijingsai.com/competition/123',
            title='UI设计大赛',
            description='用户界面设计竞赛',
        )
        
        assert isinstance(activity, Activity)
        assert activity.title == 'UI设计大赛'
        assert activity.source_name == 'Test Design Competition Scraper'
    
    def test_create_activity_with_prize(self):
        """测试带奖金的活动创建"""
        scraper = create_test_scraper()
        
        activity = scraper.create_activity(
            url='https://www.shejijingsai.com/competition/123',
            title='UI设计大赛',
            prize_amount=100000,
            prize_currency='CNY',
        )
        
        assert activity.prize is not None
        assert activity.prize.amount == 100000
    
    def test_create_activity_with_tags(self):
        """测试带标签的活动创建"""
        scraper = create_test_scraper()
        
        activity = scraper.create_activity(
            url='https://www.shejijingsai.com/competition/123',
            title='UI设计大赛',
            tags=['design', 'ui-ux', 'competition'],
        )
        
        assert 'design' in activity.tags
        assert 'ui-ux' in activity.tags


class TestDesignCompetitionScraperErrorHandling:
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
