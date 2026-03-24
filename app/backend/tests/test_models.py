"""
模型属性测试
Feature: vigilai-core
"""

import pytest
from hypothesis import given, strategies as st, settings
from datetime import datetime
from pydantic import ValidationError

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import (
    Activity, Source, Prize, ActivityDates,
    Category, Priority, SourceType, SourceStatus
)


# 自定义策略
@st.composite
def valid_activity_data(draw):
    """生成有效的Activity数据"""
    source_id = draw(st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('L', 'N'))))
    url = draw(st.text(min_size=5, max_size=200, alphabet=st.characters(whitelist_categories=('L', 'N', 'P'))))
    url = f"https://example.com/{url}"
    
    return {
        "id": Activity.generate_id(source_id, url),
        "title": draw(st.text(min_size=1, max_size=200)),
        "description": draw(st.one_of(st.none(), st.text(max_size=1000))),
        "source_id": source_id,
        "source_name": draw(st.text(min_size=1, max_size=100)),
        "url": url,
        "category": draw(st.sampled_from(list(Category))),
        "tags": draw(st.lists(st.text(min_size=1, max_size=50), max_size=10)),
        "status": "upcoming",
        "created_at": datetime.now(),
        "updated_at": datetime.now()
    }


@st.composite
def valid_source_data(draw):
    """生成有效的Source数据"""
    return {
        "id": draw(st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('L', 'N')))),
        "name": draw(st.text(min_size=1, max_size=100)),
        "type": draw(st.sampled_from(list(SourceType))),
        "url": f"https://example.com/{draw(st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('L', 'N'))))}",
        "priority": draw(st.sampled_from(list(Priority))),
        "update_interval": draw(st.integers(min_value=60, max_value=86400)),
        "enabled": draw(st.booleans()),
        "status": draw(st.sampled_from(list(SourceStatus))),
        "activity_count": draw(st.integers(min_value=0, max_value=10000))
    }


class TestModelFieldValidation:
    """
    Property 2: Model Field Validation
    For any Activity or Source object, all required fields defined in the model 
    should be present and have valid types.
    Validates: Requirements 1.1, 1.2
    """
    
    @given(data=valid_activity_data())
    @settings(max_examples=100)
    def test_activity_model_fields(self, data):
        """测试Activity模型包含所有必需字段"""
        activity = Activity(**data)
        
        # 验证所有必需字段存在
        assert hasattr(activity, 'id')
        assert hasattr(activity, 'title')
        assert hasattr(activity, 'description')
        assert hasattr(activity, 'source_id')
        assert hasattr(activity, 'source_name')
        assert hasattr(activity, 'url')
        assert hasattr(activity, 'category')
        assert hasattr(activity, 'tags')
        assert hasattr(activity, 'prize')
        assert hasattr(activity, 'dates')
        assert hasattr(activity, 'location')
        assert hasattr(activity, 'organizer')
        assert hasattr(activity, 'status')
        assert hasattr(activity, 'created_at')
        assert hasattr(activity, 'updated_at')
        
        # 验证字段类型
        assert isinstance(activity.id, str)
        assert isinstance(activity.title, str)
        assert isinstance(activity.source_id, str)
        assert isinstance(activity.source_name, str)
        assert isinstance(activity.url, str)
        assert isinstance(activity.category, Category)
        assert isinstance(activity.tags, list)
        assert isinstance(activity.created_at, datetime)
        assert isinstance(activity.updated_at, datetime)
    
    @given(data=valid_source_data())
    @settings(max_examples=100)
    def test_source_model_fields(self, data):
        """测试Source模型包含所有必需字段"""
        source = Source(**data)
        
        # 验证所有必需字段存在
        assert hasattr(source, 'id')
        assert hasattr(source, 'name')
        assert hasattr(source, 'type')
        assert hasattr(source, 'url')
        assert hasattr(source, 'priority')
        assert hasattr(source, 'update_interval')
        assert hasattr(source, 'enabled')
        assert hasattr(source, 'last_run')
        assert hasattr(source, 'last_success')
        assert hasattr(source, 'status')
        assert hasattr(source, 'error_message')
        assert hasattr(source, 'activity_count')
        
        # 验证字段类型
        assert isinstance(source.id, str)
        assert isinstance(source.name, str)
        assert isinstance(source.type, SourceType)
        assert isinstance(source.url, str)
        assert isinstance(source.priority, Priority)
        assert isinstance(source.update_interval, int)
        assert isinstance(source.enabled, bool)
        assert isinstance(source.status, SourceStatus)
        assert isinstance(source.activity_count, int)


class TestEnumValidation:
    """
    Property 3: Category and Priority Enum Validation
    For any Activity, the category field should only accept values from the Category enum.
    For any Source, the priority field should only accept values from the Priority enum.
    Validates: Requirements 1.4, 1.5
    """
    
    @given(category=st.sampled_from(list(Category)))
    @settings(max_examples=100)
    def test_valid_category_values(self, category):
        """测试Category枚举只接受有效值"""
        data = {
            "id": "test_id",
            "title": "Test Activity",
            "source_id": "test_source",
            "source_name": "Test Source",
            "url": "https://example.com/test",
            "category": category,
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }
        activity = Activity(**data)
        assert activity.category in list(Category)
        assert activity.category.value in [
            "hackathon",
            "data_competition",
            "coding_competition",
            "other_competition",
            "airdrop",
            "bounty",
            "grant",
            "dev_event",
            "news",
        ]
    
    @given(priority=st.sampled_from(list(Priority)))
    @settings(max_examples=100)
    def test_valid_priority_values(self, priority):
        """测试Priority枚举只接受有效值"""
        data = {
            "id": "test_id",
            "name": "Test Source",
            "type": SourceType.RSS,
            "url": "https://example.com/feed",
            "priority": priority,
            "update_interval": 3600
        }
        source = Source(**data)
        assert source.priority in list(Priority)
        assert source.priority.value in ["high", "medium", "low"]
    
    def test_invalid_category_rejected(self):
        """测试无效的Category值被拒绝"""
        data = {
            "id": "test_id",
            "title": "Test Activity",
            "source_id": "test_source",
            "source_name": "Test Source",
            "url": "https://example.com/test",
            "category": "invalid_category",
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }
        with pytest.raises(ValidationError):
            Activity(**data)
    
    def test_invalid_priority_rejected(self):
        """测试无效的Priority值被拒绝"""
        data = {
            "id": "test_id",
            "name": "Test Source",
            "type": SourceType.RSS,
            "url": "https://example.com/feed",
            "priority": "invalid_priority",
            "update_interval": 3600
        }
        with pytest.raises(ValidationError):
            Source(**data)


class TestActivityIdGeneration:
    """
    Property 1: Activity ID Uniqueness
    For any two activities with the same source_id and url combination, 
    the generated id should be identical.
    Validates: Requirements 1.3
    """
    
    @given(
        source_id=st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('L', 'N'))),
        url=st.text(min_size=1, max_size=200, alphabet=st.characters(whitelist_categories=('L', 'N')))
    )
    @settings(max_examples=100)
    def test_same_input_same_id(self, source_id, url):
        """相同的source_id和url应生成相同的ID"""
        id1 = Activity.generate_id(source_id, url)
        id2 = Activity.generate_id(source_id, url)
        assert id1 == id2
    
    @given(
        source_id1=st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('L', 'N'))),
        source_id2=st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('L', 'N'))),
        url=st.text(min_size=1, max_size=200, alphabet=st.characters(whitelist_categories=('L', 'N')))
    )
    @settings(max_examples=100)
    def test_different_source_different_id(self, source_id1, source_id2, url):
        """不同的source_id应生成不同的ID（除非source_id相同）"""
        id1 = Activity.generate_id(source_id1, url)
        id2 = Activity.generate_id(source_id2, url)
        if source_id1 != source_id2:
            assert id1 != id2
        else:
            assert id1 == id2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
