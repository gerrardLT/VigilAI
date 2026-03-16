"""
批量测试新增信息源
测试通用爬虫对新增信息源的抓取效果
"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import SOURCES_CONFIG
from scrapers.universal_scraper import UniversalScraper

# 新增的信息源ID列表
NEW_SOURCES = [
    # Web3 Quest任务平台
    "layer3",
    "rabbithole",
    "questn",
    "taskon",
    "intract",
    "port3",
    
    # 空投聚合补充
    "airdropalert",
    "dappradar_airdrops",
    "cryptorank_airdrops",
    "earnifi",
    "dropstab",
    "airdropbob",
    
    # 漏洞赏金补充
    "hackenproof",
    "sherlock",
    "cantina",
    "hats_finance",
    "secure3",
    "butian",
    "vulbox",
    
    # L2生态Grant
    "arbitrum_grants",
    "optimism_retropgf",
    "base_grants",
    "polygon_grants",
    "solana_grants",
    "sui_grants",
    "aptos_grants",
    "near_grants",
    "cosmos_grants",
    "polkadot_treasury",
    "avalanche_grants",
    "bnb_grants",
    "zksync_grants",
    "starknet_grants",
    "scroll_grants",
    "linea_grants",
    "mantle_grants",
    
    # 国内大厂开发者平台
    "tencent_cloud_dev",
    "aliyun_dev",
    "bytedance_dev",
    "baidu_dev",
    "jd_open",
    "meituan_open",
    "netease_open",
    "kuaishou_open",
    "weixin_open",
    "alipay_open",
    "dingtalk_open",
    "feishu_open",
    
    # 手机厂商
    "oppo_dev",
    "vivo_dev",
    "xiaomi_dev",
    "honor_dev",
    "samsung_dev",
    "meizu_open",
    
    # 国内竞赛/社区
    "heywhale",
    "baidu_aistudio",
    "xfyun_challenge",
    "segmentfault",
    "juejin_events",
    "nowcoder",
    "lanqiao",
    "csdn_dev",
    "oschina",
    "infoq_cn",
    "huaweicloud_competition",
    "tencent_algo",
    
    # 交易所活动
    "binance_activity",
    "okx_activity",
    "bybit_rewards",
    "gate_activity",
    "bitget_activity",
    "mexc_activity",
    "kucoin_activity",
    
    # Testnet
    "monad_testnet",
    "berachain_testnet",
    "movement_testnet",
    "fuel_testnet",
    "eclipse_testnet",
    "hyperliquid",
]


async def test_source(source_id: str) -> dict:
    """测试单个信息源"""
    config = SOURCES_CONFIG.get(source_id)
    if not config:
        return {"source_id": source_id, "status": "not_found", "count": 0, "error": "配置不存在"}
    
    try:
        scraper = UniversalScraper(source_id, config)
        activities = await scraper.scrape()
        
        return {
            "source_id": source_id,
            "name": config.get("name"),
            "url": config.get("url"),
            "status": "success" if activities else "empty",
            "count": len(activities),
            "sample": activities[0].title if activities else None,
            "error": None
        }
    except Exception as e:
        return {
            "source_id": source_id,
            "name": config.get("name"),
            "url": config.get("url"),
            "status": "error",
            "count": 0,
            "sample": None,
            "error": str(e)
        }


async def main():
    print("=" * 80)
    print("批量测试新增信息源")
    print("=" * 80)
    print(f"待测试信息源数量: {len(NEW_SOURCES)}")
    print()
    
    results = []
    success_count = 0
    empty_count = 0
    error_count = 0
    
    for i, source_id in enumerate(NEW_SOURCES, 1):
        print(f"[{i}/{len(NEW_SOURCES)}] 测试 {source_id}...", end=" ", flush=True)
        
        result = await test_source(source_id)
        results.append(result)
        
        if result["status"] == "success":
            print(f"[OK] 成功 - {result['count']}个活动")
            success_count += 1
        elif result["status"] == "empty":
            print(f"[WARN] 空结果")
            empty_count += 1
        else:
            print(f"[ERROR] 错误: {result['error'][:50] if result['error'] else 'Unknown'}")
            error_count += 1
        
        # 避免请求过快
        await asyncio.sleep(1)
    
    # 打印汇总
    print()
    print("=" * 80)
    print("测试结果汇总")
    print("=" * 80)
    print(f"成功: {success_count}")
    print(f"空结果: {empty_count}")
    print(f"错误: {error_count}")
    print()
    
    # 打印成功的信息源
    print("[OK] 成功抓取的信息源:")
    for r in results:
        if r["status"] == "success":
            print(f"  - {r['name']}: {r['count']}个活动 (示例: {r['sample'][:30] if r['sample'] else 'N/A'}...)")
    
    print()
    
    # 打印空结果的信息源
    print("[WARN] 空结果的信息源 (可能需要专门适配):")
    for r in results:
        if r["status"] == "empty":
            print(f"  - {r['name']}: {r['url']}")
    
    print()
    
    # 打印错误的信息源
    print("[ERROR] 错误的信息源:")
    for r in results:
        if r["status"] == "error":
            print(f"  - {r['name']}: {r['error'][:80] if r['error'] else 'Unknown'}")
    
    return results


if __name__ == "__main__":
    asyncio.run(main())
