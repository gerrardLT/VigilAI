"""
验证所有信息源的爬取情况
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


async def test_source(source_id: str, config: dict):
    """测试单个信息源"""
    print(f"\n{'='*60}")
    print(f"测试: {config['name']} ({source_id})")
    print(f"URL: {config['url']}")
    print(f"类型: {config.get('type', 'firecrawl')}")
    print(f"{'='*60}")
    
    try:
        scraper = get_scraper(source_id, config)
        activities = await scraper.scrape()
        
        print(f"抓取结果: {len(activities)} 个活动")
        
        if activities:
            # 显示前3个活动
            for i, activity in enumerate(activities[:3], 1):
                print(f"\n  {i}. {activity.title}")
                print(f"     URL: {activity.url[:80]}..." if len(activity.url) > 80 else f"     URL: {activity.url}")
                if activity.prize_amount:
                    print(f"     奖金: {activity.prize_amount} {activity.prize_currency}")
            
            if len(activities) > 3:
                print(f"\n  ... 还有 {len(activities) - 3} 个活动")
        
        return {
            'source_id': source_id,
            'name': config['name'],
            'count': len(activities),
            'status': 'success',
            'activities': activities
        }
        
    except Exception as e:
        print(f"错误: {str(e)}")
        return {
            'source_id': source_id,
            'name': config['name'],
            'count': 0,
            'status': 'error',
            'error': str(e)
        }


async def main():
    """主函数"""
    print("=" * 80)
    print("VigilAI 信息源全面验证")
    print("=" * 80)
    
    # 选择要测试的信息源（排除华为，因为已经修复）
    # 按优先级分组测试
    high_priority = ['devpost', 'dorahacks', 'mlh', 'hackathon_com', 'hackquest', 'taikai', 'unstop']
    medium_priority = ['airdrops_io', 'immunefi', 'gitcoin']
    
    # 先测试高优先级的黑客松平台
    test_sources = high_priority + medium_priority
    
    results = []
    for source_id in test_sources:
        if source_id not in SOURCES_CONFIG:
            continue
        config = SOURCES_CONFIG[source_id]
        if not config.get('enabled', True):
            continue
        
        result = await test_source(source_id, config)
        results.append(result)
        
        # 避免请求过快
        await asyncio.sleep(2)
    
    # 汇总结果
    print("\n" + "=" * 80)
    print("验证结果汇总")
    print("=" * 80)
    
    success_count = 0
    error_count = 0
    total_activities = 0
    
    for result in results:
        status_icon = "✅" if result['status'] == 'success' else "❌"
        print(f"{status_icon} {result['name']}: {result['count']} 个活动")
        
        if result['status'] == 'success':
            success_count += 1
            total_activities += result['count']
        else:
            error_count += 1
            print(f"   错误: {result.get('error', '未知错误')}")
    
    print(f"\n成功: {success_count}, 失败: {error_count}, 总活动数: {total_activities}")
    
    return results


if __name__ == "__main__":
    asyncio.run(main())
