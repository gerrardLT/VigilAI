"""
Normalize legacy product-selection fallback reasons in existing SQLite data.

This script is intentionally narrow:
- it only rewrites historical `seeded_estimate` provenance
- it does not touch current live/failure semantics
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path
import sys

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from config import DB_PATH
from product_selection.repository import ensure_product_selection_tables


LEGACY_FROM = "seeded_estimate"
LEGACY_TO = "legacy_seeded_estimate"


def migrate(db_path: str) -> tuple[int, int]:
    path = Path(db_path)
    if not path.exists():
        raise FileNotFoundError(f"database not found: {db_path}")

    updated_rows = 0
    updated_tracking_rows = 0

    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    try:
        ensure_product_selection_tables(conn)
        table_names = {
            row["name"]
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
        }
        if "selection_opportunities" not in table_names:
            return 0, 0

        rows = conn.execute(
            "SELECT id, source_diagnostics FROM selection_opportunities WHERE source_diagnostics IS NOT NULL"
        ).fetchall()

        for row in rows:
            raw = row["source_diagnostics"] or ""
            try:
                payload = json.loads(raw)
            except Exception:
                continue
            if not isinstance(payload, dict):
                continue
            reason = str(payload.get("fallback_reason") or "").strip().lower()
            if reason != LEGACY_FROM:
                continue
            payload["fallback_reason"] = LEGACY_TO
            conn.execute(
                "UPDATE selection_opportunities SET source_diagnostics = ? WHERE id = ?",
                (json.dumps(payload, ensure_ascii=False), row["id"]),
            )
            updated_rows += 1

        tracking_rows = conn.execute(
            """
            SELECT t.opportunity_id, o.source_diagnostics
            FROM selection_tracking_items t
            JOIN selection_opportunities o ON o.id = t.opportunity_id
            WHERE o.source_diagnostics IS NOT NULL
            """
        ).fetchall()
        for row in tracking_rows:
            raw = row["source_diagnostics"] or ""
            try:
                payload = json.loads(raw)
            except Exception:
                continue
            if not isinstance(payload, dict):
                continue
            reason = str(payload.get("fallback_reason") or "").strip().lower()
            if reason == LEGACY_TO:
                updated_tracking_rows += 1

        conn.commit()
    finally:
        conn.close()

    return updated_rows, updated_tracking_rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Normalize legacy seeded fallback reasons.")
    parser.add_argument("--db-path", default=DB_PATH, help="Path to VigilAI SQLite database.")
    args = parser.parse_args()

    updated_rows, updated_tracking_rows = migrate(args.db_path)
    print(
        f"Updated {updated_rows} selection opportunities; "
        f"{updated_tracking_rows} tracking-linked rows now reference `{LEGACY_TO}`."
    )


if __name__ == "__main__":
    main()
