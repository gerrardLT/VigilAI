"""
测试单个信息源
用法: python test_single_source.py <source_id>
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import SOURCES_CONFIG
from scrapers.universal_scraper import UniversalScraper
from scrapers.rss_scraper import RssScraper
from scrapers.kaggle_scraper import KaggleScraper
from scrapers.data_competition_scraper import DataCompetitionScraper
from scrapers.coding_competition_scraper import CodingCompetitionScraper
from scrapers.government_scraper import GovernmentScraper
from scrapers.bounty_scraper import BountyScraper
from scrapers.design_competition_scraper import DesignCompetitionScraper


def get_scraper(source_id: str, config: dict):
    """根据类型获取对应的爬虫"""
    scraper_type = config.get('type', 'firecrawl')
    
    if scraper_type == 'rss':
        return RssScraper(source_id, config)
    elif scraper_type == 'kaggle':
        return KaggleScraper(source_id, config)
    elif scraper_type == 'data_competition':
        return DataCompetitionScraper(source_id, config)
    elif scraper_type == 'coding_competition':
        return CodingCompetitionScraper(source_id, config)
    elif scraper_type == 'government':
        return GovernmentScraper(source_id, config)
    elif scraper_type == 'bounty':
        return BountyScraper(source_id, config)
    elif scraper_type == 'design_competition':
        return DesignCompetitionScraper(source_id, config)
    else:
        return UniversalScraper(source_id, config)


async def test_source(source_id: str):
    """测试单个信息源"""
    if source_id not in SOURCES_CONFIG:
        print(f"错误: 未找到信息源 {source_id}")
        print(f"可用的信息源: {list(SOURCES_CONFIG.keys())}")
        return
    
    config = SOURCES_CONFIG[source_id]
    
    print(f"{'='*60}")
    print(f"测试: {config['name']} ({source_id})")
    print(f"URL: {config['url']}")
    print(f"类型: {config.get('type', 'firecrawl')}")
    print(f"{'='*60}")
    
    try:
        scraper = get_scraper(source_id, config)
        activities = await scraper.scrape()
        
        print(f"\n抓取结果: {len(activities)} 个活动\n")
        
        for i, activity in enumerate(activities, 1):
            print(f"{i}. {activity.title}")
            print(f"   URL: {activity.url}")
            if hasattr(activity, 'prize_amount') and activity.prize_amount:
                print(f"   奖金: {activity.prize_amount} {getattr(activity, 'prize_currency', 'USD')}")
            if hasattr(activity, 'deadline') and activity.deadline:
                print(f"   截止: {activity.deadline}")
            if hasattr(activity, 'tags') and activity.tags:
                print(f"   标签: {activity.tags}")
            print("-" * 60)
        
    except Exception as e:
        import traceback
        print(f"错误: {str(e)}")
        traceback.print_exc()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python test_single_source.py <source_id>")
        print(f"\n可用的信息源:")
        for sid, cfg in SOURCES_CONFIG.items():
            print(f"  {sid}: {cfg['name']}")
        sys.exit(1)
    
    source_id = sys.argv[1]
    asyncio.run(test_source(source_id))
