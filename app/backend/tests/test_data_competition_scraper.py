"""
VigilAI DataCompetitionScraper单元测试
测试数据竞赛爬虫基本功能和中文编码处理

Validates: Requirements 15.1, 15.2
"""

import pytest
from unittest.mock import AsyncMock, patch
from datetime import datetime
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scrapers.data_competition_scraper import DataCompetitionScraper
from models import Activity


def create_test_scraper(source_id='tianchi', config_override=None):
    """创建测试用爬虫实例"""
    config = {
        'name': 'Test Data Competition Scraper',
        'url': 'https://tianchi.aliyun.com',
        'type': 'data_competition',
        'category': 'competition',
    }
    if config_override:
        config.update(config_override)
    return DataCompetitionScraper(source_id, config)


class TestDataCompetitionScraperInit:
    """DataCompetitionScraper初始化测试"""
    
    def test_basic_init(self):
        """测试基本初始化"""
        scraper = create_test_scraper()
        assert scraper.source_id == 'tianchi'
        assert scraper.source_type == 'data_competition'
    
    def test_init_with_encoding(self):
        """测试带编码配置初始化"""
        scraper = create_test_scraper(config_override={'encoding': 'utf-8'})
        assert scraper.config.get('encoding') == 'utf-8'


class TestDataCompetitionScraperAttributes:
    """DataCompetitionScraper属性测试"""
    
    def test_source_name(self):
        """测试source_name属性"""
        scraper = create_test_scraper()
        assert scraper.source_name == 'Test Data Competition Scraper'
    
    def test_source_url(self):
        """测试source_url属性"""
        scraper = create_test_scraper()
        assert scraper.source_url == 'https://tianchi.aliyun.com'


class TestChineseEncodingHandling:
    """中文编码处理测试"""
    
    def test_normalize_chinese_text(self):
        """测试中文文本标准化"""
        scraper = create_test_scraper()
        
        text = '  数据科学竞赛  '
        normalized = scraper._normalize_text(text)
        assert normalized == '数据科学竞赛'
    
    def test_normalize_chinese_date(self):
        """测试中文日期标准化"""
        scraper = create_test_scraper()
        
        result = scraper._normalize_date('2025年12月31日')
        assert result is not None
    
    def test_normalize_chinese_prize(self):
        """测试中文奖金标准化"""
        scraper = create_test_scraper()
        
        result = scraper._normalize_prize('¥100,000')
        assert result == 100000.0


class TestDataCompetitionScraperMethods:
    """DataCompetitionScraper方法测试"""
    
    def test_create_activity(self):
        """测试创建活动"""
        scraper = create_test_scraper()
        
        activity = scraper.create_activity(
            url='https://tianchi.aliyun.com/competition/123',
            title='数据挖掘大赛',
            description='人工智能竞赛',
        )
        
        assert isinstance(activity, Activity)
        assert activity.title == '数据挖掘大赛'
    
    def test_extract_currency_cny(self):
        """测试提取人民币货币"""
        scraper = create_test_scraper()
        
        assert scraper.extract_currency('¥100,000') == 'CNY'
        assert scraper.extract_currency('100000元') == 'CNY'


class TestDataCompetitionScraperErrorHandling:
    """错误处理测试"""
    
    def test_handle_error(self):
        """测试错误处理"""
        scraper = create_test_scraper()
        
        error = ValueError("test error")
        result = scraper.handle_error(error, "test context")
        
        assert scraper.error_count >= 1


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
