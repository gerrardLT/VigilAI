"""
检查数据库中的活动分类
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data_manager import DataManager

def check_categories():
    """检查数据库中的活动分类分布"""
    data_manager = DataManager()
    
    # 获取所有活动
    activities, total = data_manager.get_activities(page=1, page_size=1000)
    
    print(f"{'='*70}")
    print(f"数据库中共有 {total} 个活动")
    print(f"{'='*70}\n")
    
    # 按分类统计
    category_counts = {}
    for activity in activities:
        category = activity.category.value
        category_counts[category] = category_counts.get(category, 0) + 1
    
    # 显示统计
    print("分类统计:")
    for category, count in sorted(category_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"  {category}: {count} 个活动")
    
    print(f"\n{'='*70}")
    
    # 显示每个分类的示例
    print("\n每个分类的示例活动:\n")
    for category in sorted(category_counts.keys()):
        print(f"{category.upper()}:")
        category_activities = [a for a in activities if a.category.value == category]
        for i, activity in enumerate(category_activities[:3], 1):
            print(f"  {i}. {activity.title[:60]}")
            print(f"     来源: {activity.source_name}")
            print(f"     URL: {activity.url[:80]}")
        print()

if __name__ == "__main__":
    check_categories()
