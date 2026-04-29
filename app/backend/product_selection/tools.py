"""
Product-selection tool registry for the shared agent platform.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .service import ProductSelectionService

if TYPE_CHECKING:
    from agent_platform.models import AgentSession
    from data_manager import DataManager


_TAOBAO_TOKENS = ("taobao", "\u6dd8\u5b9d")
_XIANYU_TOKENS = ("xianyu", "\u95f2\u9c7c")
_NOISE_PATTERNS = (
    "\u5e2e\u6211",
    "\u770b\u4e00\u4e0b",
    "\u8fd8\u503c\u5f97\u505a\u5417",
    "\u503c\u5f97\u505a\u5417",
    "\u8fd8\u80fd\u505a\u5417",
    "\u503c\u4e0d\u503c\u5f97",
    "\u5e73\u53f0\u9009\u54c1",
    "\u9009\u54c1",
    "worth doing",
    "worth it",
    "compare",
    "comparison",
    "please",
    "help me",
)
_PATH_TOKEN_RE = re.compile(
    r"([A-Za-z]:\\[^\s\"']+\.(?:html|json)|[./\\][^\s\"']+\.(?:html|json)|app/[^\s\"']+\.(?:html|json)|docs/[^\s\"']+\.(?:html|json))",
    re.IGNORECASE,
)


def _infer_platform_scope(user_message: str) -> str:
    normalized = (user_message or "").lower()
    has_taobao = any(token in normalized for token in _TAOBAO_TOKENS)
    has_xianyu = any(token in normalized for token in _XIANYU_TOKENS)
    if has_taobao and has_xianyu:
        return "both"
    if has_taobao:
        return "taobao"
    if has_xianyu:
        return "xianyu"
    return "both"


def _extract_query_text(user_message: str) -> str:
    normalized = (user_message or "").strip()
    cleaned = _PATH_TOKEN_RE.sub(" ", normalized)
    for noise in _NOISE_PATTERNS:
        cleaned = re.sub(re.escape(noise), " ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" ，。,:;!?")
    return cleaned or normalized or "selection opportunity"

def _extract_local_inputs(user_message: str) -> dict[str, str | None]:
    rendered_snapshot_path: str | None = None
    detail_snapshot_manifest_path: str | None = None
    for raw_token in _PATH_TOKEN_RE.findall(user_message or ""):
        path = _resolve_existing_path(raw_token)
        if path is None:
            continue
        if path.suffix.lower() == ".html" and rendered_snapshot_path is None:
            rendered_snapshot_path = str(path)
        elif path.suffix.lower() == ".json" and detail_snapshot_manifest_path is None:
            detail_snapshot_manifest_path = str(path)
    return {
        "rendered_snapshot_path": rendered_snapshot_path,
        "detail_snapshot_manifest_path": detail_snapshot_manifest_path,
    }


def _resolve_existing_path(raw_token: str) -> Path | None:
    token = raw_token.strip().strip("'\"")
    direct = Path(token)
    if direct.exists():
        return direct.resolve()
    repo_relative = Path.cwd() / token
    if repo_relative.exists():
        return repo_relative.resolve()
    return None


def _read_optional_html(path_value: str | None) -> str | None:
    if not path_value:
        return None
    return Path(path_value).read_text(encoding="utf-8", errors="ignore")


class SelectionQueryTool:
    name = "selection_query"

    def __init__(self, service: ProductSelectionService) -> None:
        self.service = service

    def run(self, *, session: AgentSession, user_message: str) -> dict[str, Any]:
        query_text = _extract_query_text(user_message)
        platform_scope = _infer_platform_scope(user_message)
        local_inputs = _extract_local_inputs(user_message)
        result = self.service.start_research_job(
            query_type="keyword",
            query_text=query_text,
            platform_scope=platform_scope,
            rendered_snapshot_html=_read_optional_html(local_inputs["rendered_snapshot_path"]),
            detail_snapshot_manifest_path=local_inputs["detail_snapshot_manifest_path"],
        )
        return {
            **result,
            "query_text": query_text,
            "platform_scope": platform_scope,
            "local_inputs": local_inputs,
            "shortlist": result["items"][:5],
        }


class SelectionCompareTool:
    name = "selection_compare"

    def __init__(self, service: ProductSelectionService) -> None:
        self.service = service

    def run(self, *, session: AgentSession, user_message: str) -> dict[str, Any]:
        query_text = _extract_query_text(user_message)
        local_inputs = _extract_local_inputs(user_message)
        result = self.service.start_research_job(
            query_type="keyword",
            query_text=query_text,
            platform_scope="both",
            rendered_snapshot_html=_read_optional_html(local_inputs["rendered_snapshot_path"]),
            detail_snapshot_manifest_path=local_inputs["detail_snapshot_manifest_path"],
        )

        compare_rows: list[dict[str, Any]] = []
        seen_platforms: set[str] = set()
        for item in result["items"]:
            platform = item["platform"]
            if platform in seen_platforms:
                continue
            seen_platforms.add(platform)
            compare_rows.append(
                {
                    "id": item["id"],
                    "platform": item["platform"],
                    "title": item["title"],
                    "opportunity_score": item["opportunity_score"],
                    "confidence_score": item["confidence_score"],
                    "recommended_action": item["recommended_action"],
                }
            )

        return {
            **result,
            "query_text": query_text,
            "platform_scope": "both",
            "local_inputs": local_inputs,
            "shortlist": result["items"][:5],
            "compare_rows": compare_rows,
        }


def build_product_selection_tool_registry(data_manager: DataManager) -> dict[str, object]:
    from .repository import ProductSelectionRepository

    repository = ProductSelectionRepository(data_manager.db_path)
    service = ProductSelectionService(repository=repository)
    tools = [SelectionQueryTool(service), SelectionCompareTool(service)]
    return {tool.name: tool for tool in tools}
