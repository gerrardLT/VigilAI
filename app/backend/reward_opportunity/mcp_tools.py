"""Local MCP-style tool functions for reward-opportunity agents."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Callable
from urllib.parse import urlparse

import feedparser
import requests

from .agent_reach import search_urls


SearchFn = Callable[[str, int], list[str]]
FetchFn = Callable[[str], str]
AgentReachRunner = Callable[[str, str, int], list[dict[str, Any]]]


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def tool_envelope(
    *,
    ok: bool,
    data: Any = None,
    source: str,
    failure_type: str | None = None,
    error_message: str | None = None,
) -> dict[str, Any]:
    return {
        "ok": ok,
        "data": data if data is not None else {},
        "source": source,
        "failure_type": failure_type,
        "error_message": error_message,
        "fetched_at": _now_iso(),
    }


def _domain_allowed(url: str, domains: list[str] | None) -> bool:
    if not domains:
        return True
    host = urlparse(url).netloc.lower()
    return any(host == domain.lower() or host.endswith(f".{domain.lower()}") for domain in domains)


def search_web(
    query: str,
    *,
    domains: list[str] | None = None,
    max_results: int = 10,
    search_fn: SearchFn | None = None,
) -> dict[str, Any]:
    try:
        active_search = search_fn or (lambda active_query, limit: search_urls(active_query, max_results=limit))
        urls = [url for url in active_search(query, max_results) if _domain_allowed(url, domains)]
        return tool_envelope(ok=True, data={"query": query, "results": urls[:max_results]}, source="search_web")
    except Exception as exc:
        return tool_envelope(ok=False, source="search_web", failure_type="tool_error", error_message=str(exc))


def search_github(query: str, *, max_results: int = 10, search_fn: SearchFn | None = None) -> dict[str, Any]:
    github_query = query if "site:github.com" in query else f"site:github.com {query}"
    return search_web(github_query, domains=["github.com"], max_results=max_results, search_fn=search_fn)


def read_rss(feed_url: str, *, limit: int = 20, parser: Callable[[str], Any] | None = None) -> dict[str, Any]:
    try:
        parsed = (parser or feedparser.parse)(feed_url)
        entries = []
        for entry in list(getattr(parsed, "entries", []) or [])[:limit]:
            entries.append(
                {
                    "title": getattr(entry, "title", None) or entry.get("title"),
                    "link": getattr(entry, "link", None) or entry.get("link"),
                    "summary": getattr(entry, "summary", None) or entry.get("summary"),
                }
            )
        return tool_envelope(ok=True, data={"feed_url": feed_url, "entries": entries}, source="read_rss")
    except Exception as exc:
        return tool_envelope(ok=False, source="read_rss", failure_type="tool_error", error_message=str(exc))


def _default_agent_reach_runner(platform: str, query: str, limit: int) -> list[dict[str, Any]]:
    urls = search_urls(f"site:{platform}.com {query}", max_results=limit)
    return [{"url": url} for url in urls]


def agent_reach_search(
    platform: str,
    query: str,
    *,
    limit: int = 10,
    runner: AgentReachRunner | None = None,
) -> dict[str, Any]:
    try:
        active_runner = runner or _default_agent_reach_runner
        results = active_runner(platform, query, limit)
        return tool_envelope(ok=True, data={"platform": platform, "query": query, "results": results[:limit]}, source="agent_reach_search")
    except FileNotFoundError as exc:
        return tool_envelope(ok=False, source="agent_reach_search", failure_type="unavailable", error_message=str(exc))
    except Exception as exc:
        return tool_envelope(ok=False, source="agent_reach_search", failure_type="tool_error", error_message=str(exc))


def fetch_page_markdown(url: str, *, fetch_fn: FetchFn | None = None) -> dict[str, Any]:
    try:
        if fetch_fn is None:
            response = requests.get(url, timeout=20)
            response.raise_for_status()
            markdown = response.text
        else:
            markdown = fetch_fn(url)
        return tool_envelope(ok=True, data={"url": url, "markdown": markdown}, source="fetch_page_markdown")
    except Exception as exc:
        return tool_envelope(ok=False, source="fetch_page_markdown", failure_type="tool_error", error_message=str(exc))


def lookup_source_health(source_id: str, *, lookup_fn: Callable[[str], dict[str, Any] | None] | None = None) -> dict[str, Any]:
    try:
        data = lookup_fn(source_id) if lookup_fn else {"source_id": source_id, "status": "unknown"}
        return tool_envelope(ok=True, data=data or {}, source="lookup_source_health")
    except Exception as exc:
        return tool_envelope(ok=False, source="lookup_source_health", failure_type="tool_error", error_message=str(exc))


def store_raw_document(payload: dict[str, Any], *, store_fn: Callable[[dict[str, Any]], str] | None = None) -> dict[str, Any]:
    try:
        document_id = store_fn(payload) if store_fn else str(payload.get("id") or "")
        return tool_envelope(ok=True, data={"document_id": document_id}, source="store_raw_document")
    except Exception as exc:
        return tool_envelope(ok=False, source="store_raw_document", failure_type="tool_error", error_message=str(exc))

