"""
SQLite repository for the product-selection bounded context.
"""

from __future__ import annotations

from contextlib import contextmanager
from datetime import UTC, datetime
import json
import os
import sqlite3
import uuid
from typing import Any, Iterator, Optional

from .models import (
    PlatformScope,
    ProductOpportunity,
    ProductOpportunitySignal,
    ProductResearchQuery,
    ProductSourceMode,
    ProductTrackingState,
    ProductTrackingStatus,
    QueryType,
    ResearchJobStatus,
)


def _ensure_columns(conn: sqlite3.Connection, table: str, columns: dict[str, str]) -> None:
    existing = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    for name, column_type in columns.items():
        if name not in existing:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {column_type}")


def ensure_product_selection_tables(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS selection_queries (
            id TEXT PRIMARY KEY,
            query_type TEXT NOT NULL,
            query_text TEXT NOT NULL,
            platform_scope TEXT NOT NULL,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    _ensure_columns(
        conn,
        "selection_queries",
        {
            "query_type": "TEXT",
            "query_text": "TEXT",
            "platform_scope": "TEXT",
            "status": "TEXT",
            "created_at": "TEXT",
            "updated_at": "TEXT",
        },
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS selection_opportunities (
            id TEXT PRIMARY KEY,
            query_id TEXT NOT NULL,
            platform TEXT NOT NULL,
            platform_item_id TEXT NOT NULL,
            title TEXT NOT NULL,
            image_url TEXT,
            category_path TEXT,
            price_low REAL,
            price_mid REAL,
            price_high REAL,
            sales_volume INTEGER,
            seller_count INTEGER,
            seller_type TEXT,
            seller_name TEXT,
            demand_score REAL,
            competition_score REAL,
            price_fit_score REAL,
            risk_score REAL,
            cross_platform_signal_score REAL,
            opportunity_score REAL,
            confidence_score REAL,
            risk_tags TEXT,
            reason_blocks TEXT,
            recommended_action TEXT,
            source_urls TEXT,
            snapshot_at TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(query_id, platform, platform_item_id)
        )
        """
    )
    _ensure_columns(
        conn,
        "selection_opportunities",
        {
            "query_id": "TEXT",
            "platform": "TEXT",
            "platform_item_id": "TEXT",
            "title": "TEXT",
            "image_url": "TEXT",
            "category_path": "TEXT",
            "price_low": "REAL",
            "price_mid": "REAL",
            "price_high": "REAL",
            "sales_volume": "INTEGER",
            "seller_count": "INTEGER",
            "seller_type": "TEXT",
            "seller_name": "TEXT",
            "demand_score": "REAL",
            "competition_score": "REAL",
            "price_fit_score": "REAL",
            "risk_score": "REAL",
            "cross_platform_signal_score": "REAL",
            "opportunity_score": "REAL",
            "confidence_score": "REAL",
            "risk_tags": "TEXT",
            "reason_blocks": "TEXT",
            "recommended_action": "TEXT",
            "source_urls": "TEXT",
            "source_mode": "TEXT",
            "source_diagnostics": "TEXT",
            "snapshot_at": "TEXT",
            "created_at": "TEXT",
            "updated_at": "TEXT",
        },
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS selection_opportunity_signals (
            id TEXT PRIMARY KEY,
            opportunity_id TEXT NOT NULL,
            platform TEXT NOT NULL,
            signal_type TEXT NOT NULL,
            value_json TEXT NOT NULL,
            sample_size INTEGER DEFAULT 0,
            freshness TEXT,
            reliability REAL,
            created_at TEXT NOT NULL
        )
        """
    )
    _ensure_columns(
        conn,
        "selection_opportunity_signals",
        {
            "opportunity_id": "TEXT",
            "platform": "TEXT",
            "signal_type": "TEXT",
            "value_json": "TEXT",
            "sample_size": "INTEGER",
            "freshness": "TEXT",
            "reliability": "REAL",
            "created_at": "TEXT",
        },
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS selection_tracking_items (
            opportunity_id TEXT PRIMARY KEY,
            is_favorited INTEGER DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'saved',
            notes TEXT,
            next_action TEXT,
            remind_at TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    _ensure_columns(
        conn,
        "selection_tracking_items",
        {
            "opportunity_id": "TEXT",
            "is_favorited": "INTEGER",
            "status": "TEXT",
            "notes": "TEXT",
            "next_action": "TEXT",
            "remind_at": "TEXT",
            "created_at": "TEXT",
            "updated_at": "TEXT",
        },
    )

    conn.execute("CREATE INDEX IF NOT EXISTS idx_selection_queries_created ON selection_queries(created_at)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_selection_opportunities_query ON selection_opportunities(query_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_selection_opportunities_platform ON selection_opportunities(platform)")
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_selection_signals_opportunity ON selection_opportunity_signals(opportunity_id)"
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_selection_tracking_status ON selection_tracking_items(status)")


class ProductSelectionRepository:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._ensure_data_dir()
        with self._get_connection() as conn:
            ensure_product_selection_tables(conn)

    def _ensure_data_dir(self) -> None:
        data_dir = os.path.dirname(self.db_path)
        if data_dir:
            os.makedirs(data_dir, exist_ok=True)

    @contextmanager
    def _get_connection(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def create_query(
        self,
        *,
        query_type: str,
        query_text: str,
        platform_scope: str,
        status: str = ResearchJobStatus.RUNNING.value,
    ) -> ProductResearchQuery:
        now = datetime.now(UTC)
        query = ProductResearchQuery(
            id=uuid.uuid4().hex,
            query_type=query_type,
            query_text=query_text,
            platform_scope=platform_scope,
            status=status,
            created_at=now,
            updated_at=now,
        )
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO selection_queries (
                    id, query_type, query_text, platform_scope, status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    query.id,
                    query.query_type.value,
                    query.query_text,
                    query.platform_scope.value,
                    query.status.value,
                    query.created_at.isoformat(),
                    query.updated_at.isoformat(),
                ),
            )
        return query

    def update_query_status(self, query_id: str, status: str) -> ProductResearchQuery:
        with self._get_connection() as conn:
            conn.execute(
                """
                UPDATE selection_queries
                SET status = ?, updated_at = ?
                WHERE id = ?
                """,
                (status, datetime.now(UTC).isoformat(), query_id),
            )
            row = conn.execute("SELECT * FROM selection_queries WHERE id = ?", (query_id,)).fetchone()
        if row is None:
            raise ValueError(f"Selection query {query_id} not found")
        return self._row_to_query(row)

    def get_query(self, query_id: str) -> Optional[ProductResearchQuery]:
        with self._get_connection() as conn:
            row = conn.execute("SELECT * FROM selection_queries WHERE id = ?", (query_id,)).fetchone()
        return self._row_to_query(row) if row else None

    def list_queries(self, limit: int = 20) -> list[ProductResearchQuery]:
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM selection_queries ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [self._row_to_query(row) for row in rows]

    def create_opportunity(
        self,
        *,
        query_id: str,
        platform: str,
        platform_item_id: str,
        title: str,
        image_url: str | None = None,
        category_path: str | None = None,
        price_low: float | None = None,
        price_mid: float | None = None,
        price_high: float | None = None,
        sales_volume: int | None = None,
        seller_count: int | None = None,
        seller_type: str | None = None,
        seller_name: str | None = None,
        demand_score: float = 0,
        competition_score: float = 0,
        price_fit_score: float = 0,
        risk_score: float = 0,
        cross_platform_signal_score: float = 0,
        opportunity_score: float = 0,
        confidence_score: float = 0,
        risk_tags: list[str] | None = None,
        reason_blocks: list[str] | None = None,
        recommended_action: str | None = None,
        source_urls: list[str] | None = None,
        source_mode: str = ProductSourceMode.FALLBACK.value,
        source_diagnostics: dict[str, Any] | None = None,
        snapshot_at: datetime | None = None,
    ) -> ProductOpportunity:
        now = datetime.now(UTC)
        opportunity = ProductOpportunity(
            id=uuid.uuid4().hex,
            query_id=query_id,
            platform=platform,
            platform_item_id=platform_item_id,
            title=title,
            image_url=image_url,
            category_path=category_path,
            price_low=price_low,
            price_mid=price_mid,
            price_high=price_high,
            sales_volume=sales_volume,
            seller_count=seller_count,
            seller_type=seller_type,
            seller_name=seller_name,
            demand_score=demand_score,
            competition_score=competition_score,
            price_fit_score=price_fit_score,
            risk_score=risk_score,
            cross_platform_signal_score=cross_platform_signal_score,
            opportunity_score=opportunity_score,
            confidence_score=confidence_score,
            risk_tags=risk_tags or [],
            reason_blocks=reason_blocks or [],
            recommended_action=recommended_action,
            source_urls=source_urls or [],
            source_mode=source_mode,
            source_diagnostics=source_diagnostics or {},
            snapshot_at=snapshot_at or now,
            created_at=now,
            updated_at=now,
            is_tracking=False,
            is_favorited=False,
        )
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO selection_opportunities (
                    id, query_id, platform, platform_item_id, title, image_url, category_path,
                    price_low, price_mid, price_high, sales_volume, seller_count, seller_type, seller_name,
                    demand_score, competition_score, price_fit_score,
                    risk_score, cross_platform_signal_score, opportunity_score, confidence_score,
                    risk_tags, reason_blocks, recommended_action, source_urls, snapshot_at, created_at, updated_at
                    , source_mode, source_diagnostics
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    opportunity.id,
                    opportunity.query_id,
                    opportunity.platform,
                    opportunity.platform_item_id,
                    opportunity.title,
                    opportunity.image_url,
                    opportunity.category_path,
                    opportunity.price_low,
                    opportunity.price_mid,
                    opportunity.price_high,
                    opportunity.sales_volume,
                    opportunity.seller_count,
                    opportunity.seller_type,
                    opportunity.seller_name,
                    opportunity.demand_score,
                    opportunity.competition_score,
                    opportunity.price_fit_score,
                    opportunity.risk_score,
                    opportunity.cross_platform_signal_score,
                    opportunity.opportunity_score,
                    opportunity.confidence_score,
                    json.dumps(opportunity.risk_tags, ensure_ascii=False),
                    json.dumps(opportunity.reason_blocks, ensure_ascii=False),
                    opportunity.recommended_action,
                    json.dumps(opportunity.source_urls, ensure_ascii=False),
                    opportunity.snapshot_at.isoformat(),
                    opportunity.created_at.isoformat(),
                    opportunity.updated_at.isoformat(),
                    opportunity.source_mode,
                    json.dumps(opportunity.source_diagnostics, ensure_ascii=False),
                ),
            )
        return opportunity

    def list_opportunities(
        self,
        *,
        query_id: str | None = None,
        platform: str | None = None,
        search: str | None = None,
        risk_tag: str | None = None,
        source_mode: str | None = None,
        fallback_reason: str | None = None,
        sort_by: str = "opportunity_score",
        sort_order: str = "desc",
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[ProductOpportunity], int]:
        conditions = []
        params: list[Any] = []
        if query_id:
            conditions.append("o.query_id = ?")
            params.append(query_id)
        if platform:
            conditions.append("o.platform = ?")
            params.append(platform)
        if search:
            conditions.append("(o.title LIKE ? OR o.category_path LIKE ?)")
            term = f"%{search}%"
            params.extend([term, term])
        if source_mode:
            conditions.append("LOWER(o.source_mode) = ?")
            params.append(source_mode.lower())

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        order_map = {
            "created_at": "o.created_at",
            "updated_at": "o.updated_at",
            "confidence_score": "o.confidence_score",
            "price_mid": "o.price_mid",
            "opportunity_score": "o.opportunity_score",
        }
        sort_expression = order_map.get(sort_by, "o.opportunity_score")
        direction = "DESC" if sort_order.lower() == "desc" else "ASC"

        with self._get_connection() as conn:
            rows = conn.execute(
                f"""
                SELECT o.*,
                    CASE WHEN t.opportunity_id IS NULL THEN 0 ELSE 1 END AS is_tracking,
                    COALESCE(t.is_favorited, 0) AS is_favorited
                FROM selection_opportunities o
                LEFT JOIN selection_tracking_items t ON t.opportunity_id = o.id
                {where_clause}
                ORDER BY {sort_expression} {direction}, o.created_at DESC
                """,
                params,
            ).fetchall()

        opportunities = [self._row_to_opportunity(row) for row in rows]
        if risk_tag:
            opportunities = [
                item for item in opportunities if risk_tag in {tag.lower() for tag in item.risk_tags}
            ]
        if fallback_reason:
            opportunities = [
                item
                for item in opportunities
                if str(item.source_diagnostics.get("fallback_reason") or "").lower() == fallback_reason
            ]
        total = len(opportunities)
        start = max(0, (page - 1) * page_size)
        end = start + page_size
        return opportunities[start:end], total

    def get_opportunity(self, opportunity_id: str) -> Optional[ProductOpportunity]:
        with self._get_connection() as conn:
            row = conn.execute(
                """
                SELECT o.*,
                    CASE WHEN t.opportunity_id IS NULL THEN 0 ELSE 1 END AS is_tracking,
                    COALESCE(t.is_favorited, 0) AS is_favorited
                FROM selection_opportunities o
                LEFT JOIN selection_tracking_items t ON t.opportunity_id = o.id
                WHERE o.id = ?
                """,
                (opportunity_id,),
            ).fetchone()
        return self._row_to_opportunity(row) if row else None

    def replace_signals(self, opportunity_id: str, signals: list[dict[str, Any]]) -> list[ProductOpportunitySignal]:
        created_signals: list[ProductOpportunitySignal] = []
        with self._get_connection() as conn:
            conn.execute(
                "DELETE FROM selection_opportunity_signals WHERE opportunity_id = ?",
                (opportunity_id,),
            )
            for signal in signals:
                created_at = datetime.now(UTC)
                entity = ProductOpportunitySignal(
                    id=uuid.uuid4().hex,
                    opportunity_id=opportunity_id,
                    platform=signal["platform"],
                    signal_type=signal["signal_type"],
                    value_json=signal.get("value_json") or {},
                    sample_size=int(signal.get("sample_size") or 0),
                    freshness=signal.get("freshness"),
                    reliability=float(signal["reliability"]) if signal.get("reliability") is not None else None,
                    created_at=created_at,
                )
                conn.execute(
                    """
                    INSERT INTO selection_opportunity_signals (
                        id, opportunity_id, platform, signal_type, value_json,
                        sample_size, freshness, reliability, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        entity.id,
                        entity.opportunity_id,
                        entity.platform,
                        entity.signal_type,
                        json.dumps(entity.value_json, ensure_ascii=False),
                        entity.sample_size,
                        entity.freshness,
                        entity.reliability,
                        entity.created_at.isoformat(),
                    ),
                )
                created_signals.append(entity)
        return created_signals

    def list_signals(self, opportunity_id: str) -> list[ProductOpportunitySignal]:
        with self._get_connection() as conn:
            rows = conn.execute(
                """
                SELECT * FROM selection_opportunity_signals
                WHERE opportunity_id = ?
                ORDER BY created_at ASC
                """,
                (opportunity_id,),
            ).fetchall()
        return [self._row_to_signal(row) for row in rows]

    def upsert_tracking(self, opportunity_id: str, payload: dict[str, Any]) -> ProductTrackingState:
        with self._get_connection() as conn:
            if conn.execute("SELECT id FROM selection_opportunities WHERE id = ?", (opportunity_id,)).fetchone() is None:
                raise ValueError(f"Selection opportunity {opportunity_id} not found")

            existing = conn.execute(
                "SELECT * FROM selection_tracking_items WHERE opportunity_id = ?",
                (opportunity_id,),
            ).fetchone()
            now = datetime.now(UTC).isoformat()
            status = payload.get("status") or (existing["status"] if existing else ProductTrackingStatus.SAVED.value)
            conn.execute(
                """
                INSERT OR REPLACE INTO selection_tracking_items (
                    opportunity_id, is_favorited, status, notes, next_action, remind_at, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    opportunity_id,
                    1
                    if payload.get(
                        "is_favorited",
                        bool(existing["is_favorited"]) if existing else False,
                    )
                    else 0,
                    status,
                    payload.get("notes", existing["notes"] if existing else None),
                    payload.get("next_action", existing["next_action"] if existing else None),
                    payload.get("remind_at", existing["remind_at"] if existing else None),
                    existing["created_at"] if existing else now,
                    now,
                ),
            )
            row = conn.execute(
                "SELECT * FROM selection_tracking_items WHERE opportunity_id = ?",
                (opportunity_id,),
            ).fetchone()
        return self._row_to_tracking(row)

    def get_tracking(self, opportunity_id: str) -> Optional[ProductTrackingState]:
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM selection_tracking_items WHERE opportunity_id = ?",
                (opportunity_id,),
            ).fetchone()
        return self._row_to_tracking(row) if row else None

    def list_tracking(
        self,
        status: str | None = None,
        source_mode: str | None = None,
        fallback_reason: str | None = None,
    ) -> list[dict[str, Any]]:
        conditions: list[str] = []
        params: list[Any] = []
        if status:
            conditions.append("t.status = ?")
            params.append(status)
        if source_mode:
            conditions.append("LOWER(o.source_mode) = ?")
            params.append(source_mode.lower())

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        with self._get_connection() as conn:
            rows = conn.execute(
                f"""
                SELECT t.*, o.*,
                    1 AS is_tracking,
                    COALESCE(t.is_favorited, 0) AS is_favorited
                FROM selection_tracking_items t
                JOIN selection_opportunities o ON o.id = t.opportunity_id
                {where}
                ORDER BY t.updated_at DESC
                """,
                params,
            ).fetchall()
        items = [
            {
                "opportunity": self._row_to_opportunity(row).model_dump(mode="json"),
                **self._row_to_tracking(row).model_dump(),
            }
            for row in rows
        ]
        if fallback_reason:
            lowered_reason = fallback_reason.lower()
            items = [
                item
                for item in items
                if str(item["opportunity"]["source_diagnostics"].get("fallback_reason") or "").lower()
                == lowered_reason
            ]
        return items

    def delete_tracking(self, opportunity_id: str) -> bool:
        with self._get_connection() as conn:
            result = conn.execute(
                "DELETE FROM selection_tracking_items WHERE opportunity_id = ?",
                (opportunity_id,),
            )
        return result.rowcount > 0

    @staticmethod
    def _row_to_query(row: sqlite3.Row) -> ProductResearchQuery:
        return ProductResearchQuery(
            id=row["id"],
            query_type=QueryType(row["query_type"]),
            query_text=row["query_text"],
            platform_scope=PlatformScope(row["platform_scope"]),
            status=ResearchJobStatus(row["status"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    @staticmethod
    def _row_to_opportunity(row: sqlite3.Row) -> ProductOpportunity:
        return ProductOpportunity(
            id=row["id"],
            query_id=row["query_id"],
            platform=row["platform"],
            platform_item_id=row["platform_item_id"],
            title=row["title"],
            image_url=row["image_url"],
            category_path=row["category_path"],
            price_low=row["price_low"],
            price_mid=row["price_mid"],
            price_high=row["price_high"],
            sales_volume=row["sales_volume"],
            seller_count=row["seller_count"],
            seller_type=row["seller_type"],
            seller_name=row["seller_name"],
            demand_score=row["demand_score"] or 0,
            competition_score=row["competition_score"] or 0,
            price_fit_score=row["price_fit_score"] or 0,
            risk_score=row["risk_score"] or 0,
            cross_platform_signal_score=row["cross_platform_signal_score"] or 0,
            opportunity_score=row["opportunity_score"] or 0,
            confidence_score=row["confidence_score"] or 0,
            risk_tags=json.loads(row["risk_tags"]) if row["risk_tags"] else [],
            reason_blocks=json.loads(row["reason_blocks"]) if row["reason_blocks"] else [],
            recommended_action=row["recommended_action"],
            source_urls=json.loads(row["source_urls"]) if row["source_urls"] else [],
            source_mode=(row["source_mode"] or ProductSourceMode.FALLBACK.value),
            source_diagnostics=json.loads(row["source_diagnostics"]) if row["source_diagnostics"] else {},
            snapshot_at=datetime.fromisoformat(row["snapshot_at"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
            is_tracking=bool(row["is_tracking"]) if "is_tracking" in row.keys() else False,
            is_favorited=bool(row["is_favorited"]) if "is_favorited" in row.keys() else False,
        )

    @staticmethod
    def _row_to_signal(row: sqlite3.Row) -> ProductOpportunitySignal:
        return ProductOpportunitySignal(
            id=row["id"],
            opportunity_id=row["opportunity_id"],
            platform=row["platform"],
            signal_type=row["signal_type"],
            value_json=json.loads(row["value_json"]) if row["value_json"] else {},
            sample_size=row["sample_size"] or 0,
            freshness=row["freshness"],
            reliability=row["reliability"],
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    @staticmethod
    def _row_to_tracking(row: sqlite3.Row) -> ProductTrackingState:
        return ProductTrackingState(
            opportunity_id=row["opportunity_id"],
            is_favorited=bool(row["is_favorited"]),
            status=row["status"],
            notes=row["notes"],
            next_action=row["next_action"],
            remind_at=row["remind_at"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
