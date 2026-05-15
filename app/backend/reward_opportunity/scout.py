"""Source discovery helpers for reward-opportunity scouting."""

from __future__ import annotations

from typing import Any, Callable
from urllib.parse import urlparse

from .agent_reach import search_urls


SearchFn = Callable[[str], list[str]]

DISCOVERY_QUERY_TEMPLATES = (
    "invite reward program",
    "register reward new user bonus",
    "task reward bounty campaign",
    "site:github.com reward bounty program",
    "site:discord.com invite reward campaign",
    "site:reddit.com reward program referral",
)

SOCIAL_HOST_HINTS = {
    "x.com": "x",
    "twitter.com": "x",
    "t.me": "telegram",
    "telegram.me": "telegram",
    "discord.com": "discord",
    "reddit.com": "reddit",
    "github.com": "github",
}


def discover_source_candidates(
    existing_feeds: list[dict[str, Any]],
    *,
    query_templates: tuple[str, ...] | list[str] | None = None,
    max_candidates: int = 12,
    search_fn: SearchFn | None = None,
) -> list[dict[str, Any]]:
    active_search = search_fn or (lambda query: search_urls(query, max_results=4))
    active_templates = tuple(query_templates or DISCOVERY_QUERY_TEMPLATES)
    existing_urls = {str(feed.get("entry_url") or "").rstrip("/") for feed in existing_feeds if feed.get("entry_url")}
    existing_patterns = {
        _candidate_pattern_key(str(feed.get("entry_url") or "").rstrip("/"))
        for feed in existing_feeds
        if feed.get("entry_url")
    }

    discovered: dict[str, dict[str, Any]] = {}
    for query in active_templates:
        for url in active_search(query):
            normalized = url.rstrip("/")
            pattern_key = _candidate_pattern_key(normalized)
            if not normalized or normalized in existing_urls or pattern_key in existing_patterns:
                continue
            parsed = urlparse(normalized)
            host = parsed.netloc.lower()
            if not host:
                continue
            source_platform = _infer_platform(host)
            source_type = "social" if source_platform in {"x", "telegram", "discord", "reddit"} else "web"
            current = discovered.get(pattern_key)
            if current is None:
                current = {
                    "name": _build_candidate_name(host, parsed.path),
                    "entry_url": normalized,
                    "source_platform": source_platform,
                    "source_type": source_type,
                    "discovery_queries": [],
                    "reasons": [],
                    "score": 0,
                    "dedupe_key": pattern_key,
                    "matched_urls": [],
                }
                discovered[pattern_key] = current
            current["discovery_queries"].append(query)
            current["reasons"].append(f"matched scout query: {query}")
            current["score"] += _score_candidate(normalized, source_platform)
            current["matched_urls"].append(normalized)

    ranked = sorted(discovered.values(), key=lambda item: (-int(item["score"]), item["entry_url"]))
    for item in ranked:
        item["discovery_queries"] = list(dict.fromkeys(item["discovery_queries"]))
        item["reasons"] = list(dict.fromkeys(item["reasons"]))
        item["matched_urls"] = list(dict.fromkeys(item["matched_urls"]))
    return ranked[:max_candidates]


def _infer_platform(host: str) -> str:
    for suffix, platform in SOCIAL_HOST_HINTS.items():
        if host == suffix or host.endswith(f".{suffix}"):
            return platform
    return host.split(".")[-2] if "." in host else host


def _build_candidate_name(host: str, path: str) -> str:
    root = host.replace("www.", "")
    trimmed_path = path.strip("/").split("/")
    if trimmed_path and trimmed_path[0]:
        return f"{root} / {trimmed_path[0]}"
    return root


def _score_candidate(url: str, source_platform: str) -> int:
    score = 1
    lower = url.lower()
    if any(keyword in lower for keyword in ("reward", "rewards", "bonus", "bounty", "invite", "referral", "campaign", "task")):
        score += 3
    if source_platform in {"github", "reddit", "discord", "telegram", "x"}:
        score += 2
    return score


def _candidate_pattern_key(url: str) -> str:
    parsed = urlparse(url)
    host = parsed.netloc.lower().replace("www.", "")
    segments = [segment for segment in parsed.path.strip("/").split("/") if segment]
    prefix = "/".join(segments[:2]) if segments else ""
    return f"{host}|{prefix}"
