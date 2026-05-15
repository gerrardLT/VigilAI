"""Opportunity merge helpers for reward-opportunity discovery."""

from __future__ import annotations

import hashlib
import re
from typing import Any


def normalize_title(title: str) -> str:
    return re.sub(r"\s+", " ", title.strip().lower())


def build_dedupe_key(*, title: str, canonical_url: str | None, source_platform: str) -> str:
    stable = canonical_url or f"{source_platform}:{normalize_title(title)}"
    return hashlib.sha1(stable.encode("utf-8")).hexdigest()


def build_content_hash(title: str, body: str | None) -> str:
    return hashlib.sha1(f"{title}\n{body or ''}".encode("utf-8")).hexdigest()


def merge_opportunity_payload(existing: dict[str, Any] | None, incoming: dict[str, Any]) -> dict[str, Any]:
    if not existing:
        return incoming
    merged = dict(existing)
    for key, value in incoming.items():
        if value in (None, "", [], {}):
            continue
        if key in {"ai_missing_evidence", "ai_risk_flags", "external_links"}:
            merged[key] = list(dict.fromkeys([*(merged.get(key) or []), *value]))
        elif key == "ai_structured_evidence":
            merged[key] = {**(merged.get(key) or {}), **value}
        elif key == "ai_confidence":
            merged[key] = max(float(merged.get(key) or 0), float(value))
        else:
            merged[key] = value
    return merged
