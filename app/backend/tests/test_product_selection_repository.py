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


def test_selection_opportunity_persists_source_provenance(temp_db):
    repo = ProductSelectionRepository(temp_db)
    query = repo.create_query(
        query_type="keyword",
        query_text="storage box",
        platform_scope="taobao",
    )

    item = repo.create_opportunity(
        query_id=query.id,
        platform="taobao",
        platform_item_id="tb-live-1",
        title="Storage Box",
        opportunity_score=70,
        confidence_score=66,
        sales_volume=120,
        seller_count=8,
        seller_type="enterprise",
        seller_name="Storage Box Flagship",
        source_mode="live",
        source_diagnostics={"listing_url": "https://item.taobao.com/item.htm?id=1"},
    )

    loaded = repo.get_opportunity(item.id)
    assert loaded is not None
    assert loaded.source_mode == "live"
    assert loaded.sales_volume == 120
    assert loaded.seller_count == 8
    assert loaded.seller_type == "enterprise"
    assert loaded.seller_name == "Storage Box Flagship"
    assert loaded.source_diagnostics["listing_url"] == "https://item.taobao.com/item.htm?id=1"


def test_list_opportunities_filters_by_source_mode_and_fallback_reason(temp_db):
    repo = ProductSelectionRepository(temp_db)
    query = repo.create_query(
        query_type="keyword",
        query_text="desk lamp",
        platform_scope="both",
    )

    live_item = repo.create_opportunity(
        query_id=query.id,
        platform="taobao",
        platform_item_id="tb-live-2",
        title="Desk Lamp Live",
        source_mode="live",
        source_diagnostics={"listing_url": "https://item.taobao.com/item.htm?id=2"},
    )
    fallback_item = repo.create_opportunity(
        query_id=query.id,
        platform="xianyu",
        platform_item_id="xy-fallback-1",
        title="Desk Lamp Fallback",
        source_mode="fallback",
        source_diagnostics={"fallback_reason": "search_shell_only"},
    )

    live_rows, live_total = repo.list_opportunities(source_mode="live")
    fallback_rows, fallback_total = repo.list_opportunities(fallback_reason="search_shell_only")

    assert live_total == 1
    assert [item.id for item in live_rows] == [live_item.id]
    assert fallback_total == 1
    assert [item.id for item in fallback_rows] == [fallback_item.id]
