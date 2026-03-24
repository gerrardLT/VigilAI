"""
数据管理模块属性测试
Feature: vigilai-core
"""

import os
import uuid

import pytest
from hypothesis import given, strategies as st, settings, HealthCheck
from datetime import datetime

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_manager import DataManager
from models import Activity, Category, Prize, ActivityDates


@pytest.fixture
def temp_db():
    """创建临时数据库用于测试"""
    temp_root = os.path.join(os.path.dirname(__file__), ".tmp")
    os.makedirs(temp_root, exist_ok=True)
    db_path = os.path.join(temp_root, f"{uuid.uuid4().hex}.db")
    try:
        yield db_path
    finally:
        if os.path.exists(db_path):
            os.remove(db_path)


@pytest.fixture
def data_manager(temp_db):
    """创建DataManager实例"""
    return DataManager(db_path=temp_db)


def create_test_activity(source_id: str, url: str, title: str = "Test Activity") -> Activity:
    """创建测试用Activity"""
    activity_id = Activity.generate_id(source_id, url)
    return Activity(
        id=activity_id,
        title=title,
        description="Test description",
        source_id=source_id,
        source_name="Test Source",
        url=url,
        category=Category.HACKATHON,
        tags=["test", "hackathon"],
        created_at=datetime.now(),
        updated_at=datetime.now()
    )


class TestActivityIdUniqueness:
    """
    Property 1: Activity ID Uniqueness
    For any two activities with the same source_id and url combination, 
    the generated id should be identical.
    Validates: Requirements 1.3
    """
    
    @given(
        source_id=st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('L', 'N'))),
        url=st.text(min_size=1, max_size=100, alphabet=st.characters(whitelist_categories=('L', 'N')))
    )
    @settings(max_examples=100)
    def test_same_input_produces_same_id(self, source_id, url):
        """相同输入产生相同ID"""
        id1 = DataManager.generate_activity_id(source_id, url)
        id2 = DataManager.generate_activity_id(source_id, url)
        assert id1 == id2
    
    @given(
        source_id1=st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('L', 'N'))),
        source_id2=st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('L', 'N'))),
        url=st.text(min_size=1, max_size=100, alphabet=st.characters(whitelist_categories=('L', 'N')))
    )
    @settings(max_examples=100)
    def test_different_source_produces_different_id(self, source_id1, source_id2, url):
        """不同source_id产生不同ID"""
        id1 = DataManager.generate_activity_id(source_id1, url)
        id2 = DataManager.generate_activity_id(source_id2, url)
        if source_id1 != source_id2:
            assert id1 != id2


class TestDataPersistenceRoundTrip:
    """
    Property 6: Data Persistence Round-Trip
    For any valid Activity object, storing it via DataManager and then loading it 
    by id should produce an equivalent object.
    Validates: Requirements 8.5, 8.6
    """
    
    def test_basic_round_trip(self, data_manager):
        """基本的存储和加载往返测试"""
        activity = create_test_activity("test_source", "https://example.com/test")
        
        # 存储
        data_manager.add_activity(activity)
        
        # 加载
        loaded = data_manager.get_activity_by_id(activity.id)
        
        assert loaded is not None
        assert loaded.id == activity.id
        assert loaded.title == activity.title
        assert loaded.source_id == activity.source_id
        assert loaded.url == activity.url
        assert loaded.category == activity.category
    
    def test_round_trip_with_prize(self, data_manager):
        """带奖金信息的往返测试"""
        activity = create_test_activity("test_source", "https://example.com/prize")
        activity.prize = Prize(amount=10000, currency="USD", description="Grand Prize")
        
        data_manager.add_activity(activity)
        loaded = data_manager.get_activity_by_id(activity.id)
        
        assert loaded.prize is not None
        assert loaded.prize.amount == 10000
        assert loaded.prize.currency == "USD"
    
    def test_round_trip_with_dates(self, data_manager):
        """带日期信息的往返测试"""
        activity = create_test_activity("test_source", "https://example.com/dates")
        activity.dates = ActivityDates(
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 31),
            deadline=datetime(2024, 1, 15)
        )
        
        data_manager.add_activity(activity)
        loaded = data_manager.get_activity_by_id(activity.id)
        
        assert loaded.dates is not None
        assert loaded.dates.start_date == datetime(2024, 1, 1)
        assert loaded.dates.deadline == datetime(2024, 1, 15)


class TestDeduplicationByUrl:
    """
    Property 7: Deduplication by URL
    For any sequence of activities added to DataManager, if two activities have 
    the same url, only one should exist in storage.
    Validates: Requirements 9.1, 9.2
    """
    
    def test_duplicate_url_not_duplicated(self, data_manager):
        """相同URL不会产生重复记录"""
        url = "https://example.com/unique"
        activity1 = create_test_activity("source1", url, "First Title")
        activity2 = create_test_activity("source1", url, "Second Title")
        
        # 添加第一个
        is_new1 = data_manager.add_activity(activity1)
        count1 = data_manager.get_activities_count()
        
        # 添加第二个（相同URL）
        is_new2 = data_manager.add_activity(activity2)
        count2 = data_manager.get_activities_count()
        
        assert is_new1 == True
        assert is_new2 == False
        assert count1 == count2  # 数量不变
    
    def test_different_source_same_url_allowed(self, data_manager):
        """不同source_id相同URL应该被允许（作为不同记录）"""
        url = "https://example.com/shared"
        activity1 = create_test_activity("source1", url)
        activity2 = create_test_activity("source2", url)
        
        data_manager.add_activity(activity1)
        data_manager.add_activity(activity2)
        
        # 由于UNIQUE约束是(source_id, url)，不同source_id应该都能存储
        count = data_manager.get_activities_count()
        assert count == 2
    
    @given(
        urls=st.lists(
            st.text(min_size=5, max_size=50, alphabet=st.characters(whitelist_categories=('L', 'N'))),
            min_size=1,
            max_size=10
        )
    )
    @settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
    def test_unique_urls_all_stored(self, temp_db, urls):
        """所有唯一URL都应该被存储"""
        dm = DataManager(db_path=temp_db)
        dm.clear_all_activities()  # 清空之前的数据
        unique_urls = list(set(urls))
        
        for i, url in enumerate(unique_urls):
            full_url = f"https://example.com/{url}"
            activity = create_test_activity("test_source", full_url, f"Activity {i}")
            dm.add_activity(activity)
        
        count = dm.get_activities_count()
        assert count == len(unique_urls)


class TestCreatedTimestampPreservation:
    """
    Property 8: Created Timestamp Preservation
    For any activity that is updated (duplicate URL), the original created_at 
    timestamp should be preserved while updated_at should change.
    Validates: Requirements 9.4
    """
    
    def test_created_at_preserved_on_update(self, data_manager):
        """更新时保留原始created_at"""
        url = "https://example.com/timestamp"
        
        # 创建第一个活动
        activity1 = create_test_activity("source1", url, "Original Title")
        original_created_at = activity1.created_at
        
        data_manager.add_activity(activity1)
        
        # 等待一小段时间确保时间戳不同
        import time
        time.sleep(0.1)
        
        # 创建更新的活动
        activity2 = create_test_activity("source1", url, "Updated Title")
        data_manager.add_activity(activity2)
        
        # 加载并验证
        loaded = data_manager.get_activity_by_id(activity1.id)
        
        # created_at应该保持不变（与原始时间相同）
        assert loaded.created_at.isoformat() == original_created_at.isoformat()
        # updated_at应该更新
        assert loaded.updated_at > original_created_at


class TestFilteringAndSorting:
    """
    Property 11 & 12: API Filtering and Sorting Correctness
    Validates: Requirements 11.7, 11.8
    """
    
    def test_filter_by_category(self, data_manager):
        """按类别过滤"""
        # 添加不同类别的活动
        hackathon = create_test_activity("s1", "https://example.com/h1")
        hackathon.category = Category.HACKATHON
        
        competition = create_test_activity("s1", "https://example.com/c1")
        competition.category = Category.DATA_COMPETITION
        
        data_manager.add_activity(hackathon)
        data_manager.add_activity(competition)
        
        # 过滤hackathon
        activities, total = data_manager.get_activities(filters={"category": "hackathon"})
        assert all(a.category == Category.HACKATHON for a in activities)
    
    def test_filter_by_source_id(self, data_manager):
        """按信息源过滤"""
        activity1 = create_test_activity("source_a", "https://example.com/a1")
        activity2 = create_test_activity("source_b", "https://example.com/b1")
        
        data_manager.add_activity(activity1)
        data_manager.add_activity(activity2)
        
        activities, total = data_manager.get_activities(filters={"source_id": "source_a"})
        assert all(a.source_id == "source_a" for a in activities)
    
    def test_sort_by_created_at(self, data_manager):
        """按创建时间排序"""
        import time
        
        activity1 = create_test_activity("s1", "https://example.com/first")
        data_manager.add_activity(activity1)
        
        time.sleep(0.1)
        
        activity2 = create_test_activity("s1", "https://example.com/second")
        data_manager.add_activity(activity2)
        
        # 降序排列（最新的在前）
        activities, total = data_manager.get_activities(sort_by="created_at", sort_order="desc")
        if len(activities) >= 2:
            assert activities[0].created_at >= activities[1].created_at


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
