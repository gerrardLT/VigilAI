"""
Opportunity pool AI filter service.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, Iterable, List

import httpx

from config import (
    AI_FILTER_ENABLED,
    AI_FILTER_MAX_CANDIDATES,
    AI_FILTER_MODEL,
    AI_FILTER_TIMEOUT_SECONDS,
    OPENAI_API_KEY,
    OPENAI_BASE_URL,
)

logger = logging.getLogger(__name__)


class OpportunityAiFilterError(RuntimeError):
    """Raised when the AI filter service cannot return a valid result."""


def _candidate_payload(candidate: Any) -> Dict[str, Any]:
    data = candidate.model_dump(mode="json") if hasattr(candidate, "model_dump") else dict(candidate)
    prize = data.get("prize") or {}
    dates = data.get("dates") or {}
    analysis_fields = data.get("analysis_fields") or {}

    return {
        "id": data.get("id"),
        "title": data.get("title"),
        "category": data.get("category"),
        "summary": data.get("summary"),
        "description": data.get("description"),
        "tags": data.get("tags") or [],
        "prize": {
            "amount": prize.get("amount"),
            "currency": prize.get("currency"),
            "description": prize.get("description"),
        },
        "deadline": dates.get("deadline"),
        "location": data.get("location"),
        "organizer": data.get("organizer"),
        "source_name": data.get("source_name"),
        "trust_level": data.get("trust_level"),
        "solo_friendliness": analysis_fields.get("solo_friendliness"),
        "reward_clarity": analysis_fields.get("reward_clarity"),
        "effort_level": analysis_fields.get("effort_level"),
        "roi_level": analysis_fields.get("roi_level"),
        "payout_speed": analysis_fields.get("payout_speed"),
    }


def _build_messages(*, candidates: List[Dict[str, Any]], query: str) -> List[Dict[str, str]]:
    system_prompt = (
        "你是 VigilAI 的机会池中文智能筛选代理。"
        "你会根据用户提供的中文筛选条件，在候选机会中逐条判断是否保留。"
        "你必须只输出 JSON 对象，不要输出 Markdown，不要输出额外解释。"
        "JSON 必须包含 parsed_intent_summary、reason_summary、items。"
        "items 是数组，每项包含 id、keep、reason、confidence、uncertainties。"
        "keep 为 true 表示保留，false 表示不保留。"
        "reason 必须是简洁中文。confidence 只能是 high、medium、low。"
    )
    user_payload = {
        "query": query,
        "candidates": candidates,
    }
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
    ]


def _call_ai_provider(*, candidates: List[Dict[str, Any]], query: str) -> Dict[str, Any]:
    if not AI_FILTER_ENABLED or not OPENAI_API_KEY:
        raise OpportunityAiFilterError("AI 精筛暂未配置，请先在后端环境变量中启用相关配置。")

    request_body = {
        "model": AI_FILTER_MODEL,
        "messages": _build_messages(candidates=candidates, query=query),
        "temperature": 0.1,
        "response_format": {"type": "json_object"},
    }

    try:
        with httpx.Client(timeout=AI_FILTER_TIMEOUT_SECONDS) as client:
            response = client.post(
                f"{OPENAI_BASE_URL}/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENAI_API_KEY}",
                    "Content-Type": "application/json",
                },
                json=request_body,
            )
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise OpportunityAiFilterError("AI 精筛服务调用失败，请稍后重试。") from exc

    payload = response.json()
    try:
        content = payload["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise OpportunityAiFilterError("AI 精筛返回格式无效。") from exc

    try:
        return json.loads(content)
    except json.JSONDecodeError as exc:
        raise OpportunityAiFilterError("AI 精筛返回的结果无法解析。") from exc


def _normalize_uncertainties(value: Any) -> List[str]:
    if not isinstance(value, Iterable) or isinstance(value, (str, bytes, dict)):
        return []
    return [str(item) for item in value if item is not None]


def _normalize_ai_filter_result(
    provider_result: Dict[str, Any],
    *,
    query: str,
    candidate_count: int,
) -> Dict[str, Any]:
    items = provider_result.get("items")
    if not isinstance(items, list):
        raise OpportunityAiFilterError("AI 精筛返回格式无效。")

    kept_items: List[Dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict) or not item.get("id"):
            continue
        if not bool(item.get("keep")):
            continue
        kept_items.append(
            {
                "id": str(item["id"]),
                "ai_match_reason": str(item.get("reason") or "符合筛选条件"),
                "ai_match_confidence": str(item.get("confidence") or "medium"),
                "uncertainties": _normalize_uncertainties(item.get("uncertainties")),
            }
        )

    return {
        "query": query,
        "parsed_intent_summary": str(provider_result.get("parsed_intent_summary") or query),
        "reason_summary": str(provider_result.get("reason_summary") or "已按条件保留匹配机会"),
        "candidate_count": candidate_count,
        "matched_count": len(kept_items),
        "discarded_count": max(candidate_count - len(kept_items), 0),
        "items": kept_items,
    }


def filter_opportunities_with_ai(*, candidates: List[Any], query: str) -> Dict[str, Any]:
    normalized_query = query.strip()
    if not normalized_query:
        raise OpportunityAiFilterError("请输入 AI 精筛条件。")
    if len(candidates) > AI_FILTER_MAX_CANDIDATES:
        raise ValueError("candidate limit exceeded")

    compact_candidates = [_candidate_payload(candidate) for candidate in candidates]
    provider_result = _call_ai_provider(candidates=compact_candidates, query=normalized_query)
    return _normalize_ai_filter_result(
        provider_result,
        query=normalized_query,
        candidate_count=len(compact_candidates),
    )
