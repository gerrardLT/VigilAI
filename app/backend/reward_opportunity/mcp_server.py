"""MCP stdio server exposing real reward-opportunity tools."""

from __future__ import annotations

from typing import Any

from .browser_collector import BrowserCollectConstraints, browser_collect
from .mcp_tools import (
    agent_reach_search,
    fetch_page_markdown,
    lookup_source_health,
    read_rss,
    search_github,
    search_web,
    store_raw_document,
)


def build_mcp_server() -> Any:
    try:
        from mcp.server.fastmcp import FastMCP
    except Exception as exc:
        raise RuntimeError("mcp package is required to run the reward-opportunity MCP server") from exc

    mcp = FastMCP("reward-opportunity-tools")

    @mcp.tool()
    def reward_search_web(query: str, domains: list[str] | None = None, max_results: int = 10) -> dict[str, Any]:
        return search_web(query, domains=domains, max_results=max_results)

    @mcp.tool()
    def reward_search_github(query: str, max_results: int = 10) -> dict[str, Any]:
        return search_github(query, max_results=max_results)

    @mcp.tool()
    def reward_read_rss(feed_url: str, limit: int = 20) -> dict[str, Any]:
        return read_rss(feed_url, limit=limit)

    @mcp.tool()
    def reward_agent_reach_search(platform: str, query: str, limit: int = 10) -> dict[str, Any]:
        return agent_reach_search(platform, query, limit=limit)

    @mcp.tool()
    def reward_fetch_page_markdown(url: str) -> dict[str, Any]:
        return fetch_page_markdown(url)

    @mcp.tool()
    def reward_browser_collect(url: str, objective: str, allowed_domains: list[str] | None = None) -> dict[str, Any]:
        return browser_collect(
            url,
            objective,
            constraints=BrowserCollectConstraints(allowed_domains=allowed_domains or []),
        )

    @mcp.tool()
    def reward_lookup_source_health(source_id: str) -> dict[str, Any]:
        return lookup_source_health(source_id)

    @mcp.tool()
    def reward_store_raw_document(payload: dict[str, Any]) -> dict[str, Any]:
        return store_raw_document(payload)

    return mcp


def main() -> None:
    build_mcp_server().run()


if __name__ == "__main__":
    main()

