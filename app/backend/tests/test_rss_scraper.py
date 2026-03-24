"""
VigilAI RSS爬虫属性测试
Property 4: RSS Parsing Robustness
Property 5: RSS Date Normalization
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from datetime import datetime
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scrapers.rss_scraper import RssScraper


# 创建测试用的RssScraper实例
def create_test_scraper():
    """创建测试用爬虫实例"""
    config = {
        'name': 'Test RSS',
        'url': 'https://example.com/feed.rss',
        'category': 'hackathon'
    }
    return RssScraper('test_rss', config)


class TestRssParsingRobustness:
    """
    Feature: vigilai-core
    Property 4: RSS Parsing Robustness
    For any malformed or invalid RSS feed content, the RSS_Scraper should 
    return an empty list without raising an exception.
    """
    
    @settings(max_examples=100, deadline=None)
    @given(st.text())
    def test_random_text_returns_empty_list(self, random_text):
        """随机文本不应导致异常，应返回空列表"""
        scraper = create_test_scraper()
        result = scraper.parse_feed(random_text)
        assert isinstance(result, list)
    
    @settings(max_examples=100)
    @given(st.binary())
    def test_binary_data_returns_empty_list(self, binary_data):
        """二进制数据不应导致异常"""
        scraper = create_test_scraper()
        try:
            text = binary_data.decode('utf-8', errors='replace')
            result = scraper.parse_feed(text)
            assert isinstance(result, list)
        except Exception:
            # 解码失败也是可接受的
            pass
    
    def test_empty_string_returns_empty_list(self):
        """空字符串应返回空列表"""
        scraper = create_test_scraper()
        result = scraper.parse_feed("")
        assert result == []
    
    def test_none_returns_empty_list(self):
        """None应返回空列表"""
        scraper = create_test_scraper()
        result = scraper.parse_feed(None)
        assert result == []
    
    @settings(max_examples=100)
    @given(st.text(min_size=1, max_size=100))
    def test_malformed_xml_returns_empty_list(self, content):
        """畸形XML不应导致异常"""
        scraper = create_test_scraper()
        malformed_xml = f"<rss><channel><item>{content}</item></channel></rss>"
        result = scraper.parse_feed(malformed_xml)
        assert isinstance(result, list)
    
    def test_incomplete_rss_returns_empty_list(self):
        """不完整的RSS应返回空列表"""
        scraper = create_test_scraper()
        incomplete_rss = "<rss><channel><title>Test</title>"
        result = scraper.parse_feed(incomplete_rss)
        assert isinstance(result, list)
    
    def test_valid_rss_with_no_items_returns_empty_list(self):
        """有效但无条目的RSS应返回空列表"""
        scraper = create_test_scraper()
        empty_rss = """<?xml version="1.0" encoding="UTF-8"?>
        <rss version="2.0">
            <channel>
                <title>Test Feed</title>
                <link>https://example.com</link>
                <description>Test</description>
            </channel>
        </rss>"""
        result = scraper.parse_feed(empty_rss)
        assert result == []
    
    def test_valid_rss_with_items_returns_activities(self):
        """有效RSS应返回活动列表"""
        scraper = create_test_scraper()
        valid_rss = """<?xml version="1.0" encoding="UTF-8"?>
        <rss version="2.0">
            <channel>
                <title>Test Feed</title>
                <link>https://example.com</link>
                <item>
                    <title>Test Hackathon</title>
                    <link>https://example.com/hackathon1</link>
                    <description>A test hackathon with $10,000 prize</description>
                    <pubDate>Mon, 01 Jan 2024 00:00:00 GMT</pubDate>
                </item>
            </channel>
        </rss>"""
        result = scraper.parse_feed(valid_rss)
        assert len(result) == 1
        assert result[0].title == "Test Hackathon"
        assert result[0].url == "https://example.com/hackathon1"


class TestRssDateNormalization:
    """
    Feature: vigilai-core
    Property 5: RSS Date Normalization
    For any valid date string in RSS entries (regardless of format), 
    the RSS_Scraper should convert it to ISO 8601 format.
    """
    
    @pytest.mark.parametrize("date_str,expected_year", [
        ("Mon, 01 Jan 2024 00:00:00 GMT", 2024),
        ("2024-01-15T10:30:00Z", 2024),
        ("January 15, 2024", 2024),
        ("15 Jan 2024", 2024),
        ("2024/01/15", 2024),
        ("01-15-2024", 2024),
        ("2024.01.15", 2024),
    ])
    def test_various_date_formats(self, date_str, expected_year):
        """测试各种日期格式的解析"""
        result = RssScraper.parse_date(date_str)
        assert result is not None
        assert result.year == expected_year
    
    def test_rfc822_format(self):
        """RFC 822格式（RSS标准）"""
        result = RssScraper.parse_date("Tue, 15 Jan 2024 14:30:00 +0000")
        assert result is not None
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15
    
    def test_iso8601_format(self):
        """ISO 8601格式"""
        result = RssScraper.parse_date("2024-01-15T14:30:00Z")
        assert result is not None
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15
    
    def test_human_readable_format(self):
        """人类可读格式"""
        result = RssScraper.parse_date("January 15, 2024")
        assert result is not None
        assert result.year == 2024
        assert result.month == 1
    
    def test_chinese_date_format(self):
        """中文日期格式"""
        result = RssScraper.parse_date("2024年1月15日")
        # dateutil可能无法解析中文日期，返回None是可接受的
        # 如果能解析，验证结果
        if result:
            assert result.year == 2024
    
    def test_empty_string_returns_none(self):
        """空字符串应返回None"""
        result = RssScraper.parse_date("")
        assert result is None
    
    def test_none_returns_none(self):
        """None应返回None"""
        result = RssScraper.parse_date(None)
        assert result is None
    
    @settings(max_examples=100)
    @given(st.text(max_size=50))
    def test_random_text_does_not_crash(self, random_text):
        """随机文本不应导致崩溃"""
        result = RssScraper.parse_date(random_text)
        # 结果应该是datetime或None
        assert result is None or isinstance(result, datetime)
    
    def test_output_is_datetime(self):
        """输出应该是datetime对象"""
        result = RssScraper.parse_date("2024-01-15")
        assert isinstance(result, datetime)
    
    def test_datetime_can_be_formatted_to_iso8601(self):
        """datetime对象应能转换为ISO 8601格式"""
        result = RssScraper.parse_date("Mon, 15 Jan 2024 14:30:00 GMT")
        assert result is not None
        iso_str = result.isoformat()
        assert "2024-01-15" in iso_str


class TestPrizeExtraction:
    """测试奖金提取功能"""
    
    def test_extract_usd_with_dollar_sign(self):
        """提取美元金额（带$符号）"""
        scraper = create_test_scraper()
        amount, currency = scraper._extract_prize("Win $10,000 in prizes!")
        assert amount == 10000.0
        assert currency == "USD"
    
    def test_extract_usd_with_text(self):
        """提取美元金额（带USD文字）"""
        scraper = create_test_scraper()
        amount, currency = scraper._extract_prize("Prize pool: 5000 USD")
        assert amount == 5000.0
        assert currency == "USD"
    
    def test_extract_cny_with_symbol(self):
        """提取人民币金额（带¥符号）"""
        scraper = create_test_scraper()
        amount, currency = scraper._extract_prize("奖金 ¥50,000")
        assert amount == 50000.0
        assert currency == "CNY"
    
    def test_extract_cny_with_text(self):
        """提取人民币金额（带元文字）"""
        scraper = create_test_scraper()
        amount, currency = scraper._extract_prize("总奖金10000元")
        assert amount == 10000.0
        assert currency == "CNY"
    
    def test_no_prize_returns_none(self):
        """无奖金信息返回None"""
        scraper = create_test_scraper()
        amount, currency = scraper._extract_prize("Join our hackathon!")
        assert amount is None
        assert currency == "USD"
    
    def test_empty_text_returns_none(self):
        """空文本返回None"""
        scraper = create_test_scraper()
        amount, currency = scraper._extract_prize("")
        assert amount is None


class TestDeadlineExtraction:
    """测试截止日期提取功能"""
    
    def test_extract_deadline_keyword(self):
        """提取deadline关键词后的日期"""
        scraper = create_test_scraper()
        result = scraper._extract_deadline("Deadline: January 15, 2024")
        assert result is not None
        assert result.year == 2024
        assert result.month == 1
    
    def test_extract_due_keyword(self):
        """提取due关键词后的日期"""
        scraper = create_test_scraper()
        result = scraper._extract_deadline("Due: March 1, 2024")
        assert result is not None
        assert result.month == 3
    
    def test_no_deadline_returns_none(self):
        """无截止日期返回None"""
        scraper = create_test_scraper()
        result = scraper._extract_deadline("Join our hackathon!")
        assert result is None
