"""
数据库分类迁移脚本
将旧的分类更新为新的细分分类
"""
import sqlite3
from config import DB_PATH

# 分类映射关系
CATEGORY_MAPPING = {
    # 数据竞赛信息源
    'kaggle': 'data_competition',
    'tianchi': 'data_competition',
    'datafountain': 'data_competition',
    'datacastle': 'data_competition',
    'drivendata': 'data_competition',
    
    # 编程竞赛信息源
    'hackerearth': 'coding_competition',
    'topcoder': 'coding_competition',
    'microsoft_imagine': 'coding_competition',
    
    # 其他竞赛信息源
    'challenge_gov': 'other_competition',
    'cxcyds': 'other_competition',
    'cnmaker': 'other_competition',
    'shejijingsai': 'other_competition',
    
    # 开发者活动信息源
    'huawei_dev': 'dev_event',
    'solana': 'dev_event',
    
    # 科技新闻信息源
    '36kr': 'news',
    'huxiu': 'news',
    'panews': 'news',
}

def migrate_categories():
    """执行分类迁移"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("=" * 70)
    print("开始迁移数据库分类")
    print("=" * 70)
    
    # 统计迁移前的分类
    cursor.execute('SELECT category, COUNT(*) FROM activities GROUP BY category')
    print("\n迁移前的分类统计:")
    for row in cursor.fetchall():
        print(f"  {row[0]}: {row[1]} 个活动")
    
    # 执行迁移
    total_updated = 0
    for source_id, new_category in CATEGORY_MAPPING.items():
        cursor.execute(
            'UPDATE activities SET category = ? WHERE source_id = ?',
            (new_category, source_id)
        )
        updated = cursor.rowcount
        if updated > 0:
            print(f"\n✅ {source_id}: 更新 {updated} 个活动 -> {new_category}")
            total_updated += updated
    
    conn.commit()
    
    # 统计迁移后的分类
    cursor.execute('SELECT category, COUNT(*) FROM activities GROUP BY category')
    print("\n" + "=" * 70)
    print("迁移后的分类统计:")
    for row in cursor.fetchall():
        print(f"  {row[0]}: {row[1]} 个活动")
    
    print("\n" + "=" * 70)
    print(f"迁移完成！共更新 {total_updated} 个活动")
    print("=" * 70)
    
    conn.close()

if __name__ == "__main__":
    migrate_categories()
