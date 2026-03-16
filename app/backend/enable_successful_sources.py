"""
启用测试成功的新增信息源
将43个测试成功的信息源加入定时抓取任务
"""

import json
import os

# 测试成功的信息源ID列表
SUCCESSFUL_SOURCES = [
    # Web3 Quest任务平台 (4个)
    "layer3",
    "rabbithole",
    "questn",
    "taskon",
    
    # 空投聚合 (4个)
    "airdropalert",
    "earnifi",
    "dropstab",
    "airdropbob",
    
    # 漏洞赏金 (6个)
    "hackenproof",
    "sherlock",
    "cantina",
    "secure3",
    "butian",
    "vulbox",
    
    # L2生态Grant (6个)
    "arbitrum_grants",
    "polygon_grants",
    "solana_grants",
    "aptos_grants",
    "starknet_grants",
    "mantle_grants",
    
    # 国内大厂开发者平台 (5个)
    "tencent_cloud_dev",
    "aliyun_dev",
    "baidu_dev",
    "netease_open",
    "dingtalk_open",
    
    # 手机厂商 (2个)
    "vivo_dev",
    "honor_dev",
    
    # 国内竞赛/社区 (7个)
    "xfyun_challenge",
    "segmentfault",
    "juejin_events",
    "nowcoder",
    "lanqiao",
    "huaweicloud_competition",
    "tencent_algo",
    
    # 交易所活动 (2个)
    "bybit_rewards",
    "bitget_activity",
    
    # Testnet (3个)
    "monad_testnet",
    "fuel_testnet",
    "eclipse_testnet",
]


def load_test_results():
    """加载测试结果"""
    progress_file = os.path.join(os.path.dirname(__file__), "test_progress.json")
    if not os.path.exists(progress_file):
        print("未找到测试结果文件")
        return None
    
    with open(progress_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    return data


def print_summary():
    """打印启用信息源的汇总"""
    print("=" * 80)
    print("启用测试成功的新增信息源")
    print("=" * 80)
    print()
    print(f"总计: {len(SUCCESSFUL_SOURCES)}个信息源将被启用")
    print()
    
    # 按类别分组
    categories = {
        "Web3 Quest任务平台": ["layer3", "rabbithole", "questn", "taskon"],
        "空投聚合": ["airdropalert", "earnifi", "dropstab", "airdropbob"],
        "漏洞赏金": ["hackenproof", "sherlock", "cantina", "secure3", "butian", "vulbox"],
        "L2生态Grant": ["arbitrum_grants", "polygon_grants", "solana_grants", "aptos_grants", "starknet_grants", "mantle_grants"],
        "国内大厂开发者平台": ["tencent_cloud_dev", "aliyun_dev", "baidu_dev", "netease_open", "dingtalk_open"],
        "手机厂商": ["vivo_dev", "honor_dev"],
        "国内竞赛/社区": ["xfyun_challenge", "segmentfault", "juejin_events", "nowcoder", "lanqiao", "huaweicloud_competition", "tencent_algo"],
        "交易所活动": ["bybit_rewards", "bitget_activity"],
        "Testnet": ["monad_testnet", "fuel_testnet", "eclipse_testnet"],
    }
    
    for category, sources in categories.items():
        print(f"{category} ({len(sources)}个):")
        for source_id in sources:
            print(f"  - {source_id}")
        print()
    
    # 加载测试结果，显示活动数量
    data = load_test_results()
    if data:
        print("=" * 80)
        print("预期活动数量")
        print("=" * 80)
        print()
        
        total_activities = 0
        results_map = {r["source_id"]: r for r in data["results"]}
        
        for category, sources in categories.items():
            category_total = 0
            print(f"{category}:")
            for source_id in sources:
                if source_id in results_map:
                    count = results_map[source_id]["count"]
                    name = results_map[source_id]["name"]
                    category_total += count
                    total_activities += count
                    print(f"  - {name}: {count}个活动")
            print(f"  小计: {category_total}个活动")
            print()
        
        print("=" * 80)
        print(f"预计每次抓取可获得: {total_activities}个活动")
        print("=" * 80)


def verify_config():
    """验证config.py中的配置"""
    from config import SOURCES_CONFIG
    
    print("\n验证配置文件...")
    print()
    
    missing = []
    disabled = []
    
    for source_id in SUCCESSFUL_SOURCES:
        if source_id not in SOURCES_CONFIG:
            missing.append(source_id)
        elif not SOURCES_CONFIG[source_id].get("enabled", True):
            disabled.append(source_id)
    
    if missing:
        print(f"警告: {len(missing)}个信息源在config.py中未找到:")
        for source_id in missing:
            print(f"  - {source_id}")
        print()
    
    if disabled:
        print(f"注意: {len(disabled)}个信息源当前被禁用:")
        for source_id in disabled:
            print(f"  - {source_id}")
        print()
    
    if not missing and not disabled:
        print("所有信息源配置正常!")
        print()
    
    return len(missing) == 0 and len(disabled) == 0


def main():
    print_summary()
    
    # 验证配置
    config_ok = verify_config()
    
    if config_ok:
        print("=" * 80)
        print("下一步操作")
        print("=" * 80)
        print()
        print("1. 确认所有信息源在config.py中已启用 (enabled=True)")
        print("2. 运行scheduler.py启动定时抓取任务")
        print("3. 监控日志文件查看抓取情况")
        print("4. 通过API查询新增的活动数据")
        print()
        print("启动命令:")
        print("  python app/backend/scheduler.py")
        print()
    else:
        print("=" * 80)
        print("请先修复配置问题，然后重新运行此脚本")
        print("=" * 80)


if __name__ == "__main__":
    main()
