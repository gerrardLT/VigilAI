"""
同步信息源配置到数据库
当config.py中新增信息源后，运行此脚本将新增的信息源同步到数据库
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data_manager import DataManager
from config import SOURCES_CONFIG

def sync_sources():
    """同步信息源配置到数据库"""
    dm = DataManager()
    
    # 获取数据库中已有的信息源
    existing_sources = dm.get_sources_status()
    existing_ids = {s.id for s in existing_sources}
    
    # 获取配置中的信息源
    config_ids = set(SOURCES_CONFIG.keys())
    
    # 找出新增的信息源
    new_ids = config_ids - existing_ids
    
    if not new_ids:
        print("没有新增的信息源需要同步")
        return
    
    print(f"发现 {len(new_ids)} 个新增信息源:")
    for source_id in new_ids:
        config = SOURCES_CONFIG[source_id]
        print(f"  - {source_id}: {config['name']}")
    
    # 重新初始化信息源（会自动添加新的）
    dm._init_sources()
    
    print(f"\n同步完成！新增了 {len(new_ids)} 个信息源")
    
    # 验证
    updated_sources = dm.get_sources_status()
    print(f"\n当前数据库中共有 {len(updated_sources)} 个信息源")

if __name__ == "__main__":
    sync_sources()
