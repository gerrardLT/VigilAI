"""
Product-selection repository tests.
"""

from __future__ import annotations

import os
import sqlite3
import sys
import uuid

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_manager import DataManager  # noqa: E402
from product_selection.repository import ProductSelectionRepository  # noqa: E402


@pytest.fixture
def temp_db():
    temp_root = os.path.join(os.path.dirname(__file__), ".tmp")
    os.makedirs(temp_root, exist_ok=True)
    db_path = os.path.join(temp_root, f"{uuid.uuid4().hex}.db")
    try:
        yield db_path
    finally:
        if os.path.exists(db_path):
            os.remove(db_path)


def test_create_selection_query_persists_platform_scope(temp_db):
    repo = ProductSelectionRepository(temp_db)

    query = repo.create_query(
        query_type="keyword",
        query_text="蓝牙标签",
        platform_scope="both",
    )

    assert query.id
    assert query.query_type.value == "keyword"
    assert query.query_text == "蓝牙标签"
    assert query.platform_scope.value == "both"
    assert query.status.value == "running"


def test_store_selection_opportunity_links_to_query(temp_db):
    repo = ProductSelectionRepository(temp_db)
    query = repo.create_query(
        query_type="keyword",
        query_text="蓝牙标签",
        platform_scope="both",
    )

    item = repo.create_opportunity(
        query_id=query.id,
        platform="taobao",
        platform_item_id="tb-001",
        title="蓝牙防丢器",
        opportunity_score=72,
        confidence_score=68,
    )

    assert item.id
    assert item.query_id == query.id
    assert item.platform == "taobao"
    assert repo.get_opportunity(item.id).title == "蓝牙防丢器"


def test_data_manager_initializes_product_selection_tables(temp_db):
    DataManager(db_path=temp_db)

    conn = sqlite3.connect(temp_db)
    try:
        table_names = {
            row[0]
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
        }
    finally:
        conn.close()

    assert "selection_queries" in table_names
    assert "selection_opportunities" in table_names
    assert "selection_opportunity_signals" in table_names
    assert "selection_tracking_items" in table_names
