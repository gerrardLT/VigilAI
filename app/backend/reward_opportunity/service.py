"""Application service for reward-opportunity APIs and sync workflow."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
import re
from typing import Any
from urllib.parse import urlparse

from .agent_reach import search_urls
from .agent_loop import run_investigation_cycle
from .crawl4ai_collector import collect_documents
from .merger import build_content_hash, build_dedupe_key, merge_opportunity_payload, normalize_title
from .recall import recall_candidate_from_document
from .repository import RewardOpportunityRepository
from .scout import discover_source_candidates
from .telemetry import TraceRecorder

REWARD_WORDS = ("reward", "bonus", "cash", "$", "prize", "airdrop", "bounty", "earn", "incentive", "rebate")
ACTION_WORDS = ("invite", "register", "submit", "complete", "follow", "join", "test", "share", "refer", "quest", "task")
TIME_WORDS = ("deadline", "ends", "until", "before", "may", "june", "july", "2025", "2026", "campaign ends", "valid until")
RULE_WORDS = ("rule", "rules", "faq", "terms", "eligibility", "requirements", "how it works")
ELIGIBILITY_WORDS = ("eligible", "eligibility", "must", "requires", "requirement", "only for", "new users", "region")


def _extract_matching_snippets(text: str, keywords: tuple[str, ...]) -> list[str]:
    snippets: list[str] = []
    for raw_line in re.split(r"[\n銆?!?]+", text):
        line = raw_line.strip()
        lower = line.lower()
        if line and any(keyword in lower for keyword in keywords):
            snippets.append(line)
    return snippets[:5]


def _build_evidence_bundle(documents: list[dict[str, Any]], current: dict[str, Any] | None = None) -> dict[str, Any]:
    bundle = {
        "title": (current or {}).get("title"),
        "source_platform": (current or {}).get("source_platform"),
        "raw_text_excerpt": (current or {}).get("raw_text_excerpt"),
        "reward_snippets": list((current or {}).get("reward_snippets") or []),
        "action_snippets": list((current or {}).get("action_snippets") or []),
        "time_snippets": list((current or {}).get("time_snippets") or []),
        "rule_snippets": list((current or {}).get("rule_snippets") or []),
        "eligibility_snippets": list((current or {}).get("eligibility_snippets") or []),
        "external_links": list((current or {}).get("external_links") or []),
        "priority_links": list((current or {}).get("priority_links") or []),
    }
    for document in documents:
        text = f"{document.get('title', '')}\n{document.get('body', '')}".strip()
        bundle["title"] = bundle.get("title") or document.get("title")
        bundle["source_platform"] = bundle.get("source_platform") or document.get("source_platform")
        bundle["raw_text_excerpt"] = bundle.get("raw_text_excerpt") or (document.get("body") or "")[:280]
        bundle["reward_snippets"] = list(dict.fromkeys(bundle["reward_snippets"] + _extract_matching_snippets(text, REWARD_WORDS)))
        bundle["action_snippets"] = list(dict.fromkeys(bundle["action_snippets"] + _extract_matching_snippets(text, ACTION_WORDS)))
        bundle["time_snippets"] = list(dict.fromkeys(bundle["time_snippets"] + _extract_matching_snippets(text, TIME_WORDS)))
        bundle["rule_snippets"] = list(dict.fromkeys(bundle["rule_snippets"] + _extract_matching_snippets(text, RULE_WORDS)))
        bundle["eligibility_snippets"] = list(
            dict.fromkeys(bundle["eligibility_snippets"] + _extract_matching_snippets(text, ELIGIBILITY_WORDS))
        )
        external_links = list(document.get("metadata", {}).get("external_links", []))
        internal_links = list(document.get("metadata", {}).get("internal_links", []))
        bundle["external_links"] = list(dict.fromkeys(bundle["external_links"] + external_links))
        priority_links = [
            link
            for link in internal_links + external_links
            if any(word in link.lower() for word in ("rule", "faq", "terms", "help", "campaign", "reward", "invite"))
        ]
        bundle["priority_links"] = list(dict.fromkeys(bundle["priority_links"] + priority_links))
    return bundle


def _first_or_none(values: list[Any] | None) -> Any | None:
    return values[0] if values else None


def _health_level(score: int) -> str:
    if score >= 85:
        return "healthy"
    if score >= 60:
        return "watch"
    if score >= 35:
        return "risky"
    return "cold"


def _source_failure_mode(jobs: list[dict[str, Any]]) -> str | None:
    if not jobs:
        return None
    if any(job.get("status") == "completed" for job in jobs):
        return None
    if any(job.get("status") == "failed" for job in jobs):
        return "cold_start_failed"
    return "cold_start_pending"


def _classify_failure_reason(error_message: str | None) -> str | None:
    if not error_message:
        return None
    lower = error_message.lower()
    if any(token in lower for token in ("timeout", "timed out", "deadline exceeded")):
        return "timeout"
    if any(token in lower for token in ("403", "401", "forbidden", "unauthorized", "access denied")):
        return "auth_or_permission"
    if any(token in lower for token in ("404", "not found")):
        return "not_found"
    if any(token in lower for token in ("429", "rate limit", "too many requests")):
        return "rate_limited"
    if any(token in lower for token in ("captcha", "cloudflare", "blocked", "anti bot", "anti-bot", "bot check")):
        return "blocked_or_anti_bot"
    if any(token in lower for token in ("dns", "connection", "network", "unreachable", "refused")):
        return "network"
    if any(token in lower for token in ("empty body", "missing title", "missing content", "invalid content")):
        return "invalid_content_shape"
    if any(token in lower for token in ("parse", "schema", "json", "extract")):
        return "parsing"
    return "unknown"


def _failure_advice(category: str | None) -> str | None:
    advice = {
        "timeout": "建议降低抓取深度，减少 follow-up 链接数量，优先保留入口页和规则页。",
        "auth_or_permission": "建议切换到登录态来源，或补充可公开访问的落地页作为入口。",
        "not_found": "建议检查入口 URL 是否失效，必要时重新导入新的活动页或频道页。",
        "rate_limited": "建议降低同步频率，拆分批次执行，避免短时间重复请求同一站点。",
        "blocked_or_anti_bot": "建议将该来源标记为需私域接入，或改用更稳定的规则页入口。",
        "network": "建议稍后重试，并检查目标站点连通性或上游网络波动。",
        "invalid_content_shape": "建议检查来源是否已变成目录页、跳转页或空白页，并更新入口 URL。",
        "parsing": "建议检查页面结构是否变化，并补充更稳定的标题、正文或规则提取路径。",
        "unknown": "建议先重跑单源复现，再根据最新错误日志决定是否停用来源。",
    }
    return advice.get(category)


def _recommended_action(category: str | None) -> str | None:
    actions = {
        "timeout": "reduce_depth",
        "auth_or_permission": "switch_to_authenticated_source",
        "not_found": "refresh_entry_url",
        "rate_limited": "slow_down_schedule",
        "blocked_or_anti_bot": "switch_to_authenticated_source",
        "network": "retry_later",
        "invalid_content_shape": "refresh_entry_url",
        "parsing": "review_extractor",
        "unknown": "rerun_and_inspect",
    }
    return actions.get(category)


def _coerce_source_config(config: dict[str, Any] | None) -> dict[str, Any]:
    normalized = dict(config or {})
    normalized.setdefault("auto_sync_enabled", True)
    normalized.setdefault("sync_interval_minutes", 30)
    normalized.setdefault("blacklisted", False)
    normalized.setdefault("blacklist_reason", None)
    normalized.setdefault("merge_group_key", None)
    normalized.setdefault("preferred_entry_url", None)
    normalized.setdefault("needs_authentication", False)
    normalized.setdefault("pause_mode", "manual" if normalized.get("disabled") else None)
    normalized.setdefault("import_preview", None)
    return normalized


def _domain_key(url: str | None) -> str:
    parsed = urlparse(url or "")
    return parsed.netloc.lower().replace("www.", "")


def _extract_first_money_amount(text: str) -> str | None:
    match = re.search(r"\$\s?[\d,]+", text)
    if match:
        return match.group(0)
    return None


class RewardOpportunityService:
    def __init__(self, repository: RewardOpportunityRepository):
        self.repository = repository

    def _now(self) -> datetime:
        return datetime.now(UTC)

    def _serialize_source(self, source: dict[str, Any], recent_jobs: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        jobs = recent_jobs or [job.model_dump(mode="json") for job in self.repository.list_recent_crawl_jobs_for_source(source["id"], limit=30)]
        short_jobs = jobs[:6]
        success_count = sum(1 for job in short_jobs if job["status"] == "completed")
        failure_jobs = [job for job in short_jobs if job["status"] == "failed"]
        avg_documents = int(sum(int(job["document_count"]) for job in short_jobs) / len(short_jobs)) if short_jobs else 0
        config = _coerce_source_config(source.get("config"))
        current_failure_category = _classify_failure_reason(source.get("last_error_message"))
        consecutive_failures = 0
        for job in jobs:
            if job["status"] == "failed":
                consecutive_failures += 1
                continue
            break
        score = 40
        score += min(success_count * 12, 36)
        score -= min(len(failure_jobs) * 15, 45)
        if source.get("last_success_at"):
            score += 15
        if avg_documents > 0:
            score += min(avg_documents * 2, 12)
        if source.get("last_error_message"):
            score -= 10
        if config.get("disabled"):
            score -= 5
        score = max(0, min(score, 100))
        trend_points = [
            {
                "job_id": job["id"],
                "created_at": job["created_at"],
                "status": job["status"],
                "document_count": job["document_count"],
                "candidate_count": job["candidate_count"],
                "opportunity_count": job["opportunity_count"],
            }
            for job in jobs[:30]
        ]
        source_domain = _domain_key(source.get("entry_url"))
        merged_candidates = []
        for candidate in self.repository.list_source_feeds():
            candidate_data = candidate.model_dump(mode="json")
            candidate_config = _coerce_source_config(candidate_data.get("config"))
            same_merge_group = bool(config.get("merge_group_key")) and config.get("merge_group_key") == candidate_config.get("merge_group_key")
            same_domain = source_domain and source_domain == _domain_key(candidate_data.get("entry_url"))
            if candidate_data["id"] == source["id"] or same_merge_group or same_domain:
                merged_candidates.append(
                    {
                        "id": candidate_data["id"],
                        "name": candidate_data["name"],
                        "entry_url": candidate_data.get("entry_url"),
                        "preferred": candidate_data.get("entry_url") == config.get("preferred_entry_url"),
                    }
                )
        return {
            **source,
            "config": config,
            "health_score": score,
            "health_level": _health_level(score),
            "recent_failure_reasons": list(dict.fromkeys(job.get("error_message") for job in failure_jobs if job.get("error_message")))[:3],
            "recent_failure_categories": list(
                dict.fromkeys(_classify_failure_reason(job.get("error_message")) for job in failure_jobs if job.get("error_message"))
            )[:3],
            "current_failure_category": current_failure_category,
            "failure_advice": _failure_advice(current_failure_category),
            "recommended_action": _recommended_action(current_failure_category),
            "cold_start_status": _source_failure_mode(short_jobs),
            "is_paused": bool(config.get("disabled")),
            "pause_mode": config.get("pause_mode"),
            "needs_attention": bool(current_failure_category) or consecutive_failures >= 2,
            "consecutive_failures": consecutive_failures,
            "recent_job_stats": {
                "total_runs": len(short_jobs),
                "success_runs": success_count,
                "failed_runs": len(failure_jobs),
                "avg_documents": avg_documents,
            },
            "schedule": {
                "auto_sync_enabled": bool(config.get("auto_sync_enabled", True)),
                "sync_interval_minutes": int(config.get("sync_interval_minutes", 30) or 30),
            },
            "import_preview": config.get("import_preview"),
            "merge_group_key": config.get("merge_group_key"),
            "preferred_entry_url": config.get("preferred_entry_url"),
            "blacklisted": bool(config.get("blacklisted")),
            "blacklist_reason": config.get("blacklist_reason"),
            "needs_authentication": bool(config.get("needs_authentication")),
            "health_trend": trend_points,
            "merged_sources": merged_candidates,
            "audit_summary": self.repository.list_source_audit(source["id"], limit=5),
        }

    def _sort_source_priority(self, source: dict[str, Any]) -> tuple[int, int, int, str]:
        if source.get("pause_mode") == "suggested":
            rank = 0
        elif source.get("cold_start_status") == "cold_start_failed":
            rank = 1
        elif int(source.get("consecutive_failures") or 0) >= 2:
            rank = 2
        elif source.get("health_level") in {"cold", "risky"}:
            rank = 3
        elif source.get("is_paused"):
            rank = 5
        else:
            rank = 4
        return (rank, int(source.get("health_score") or 0), -int(source.get("consecutive_failures") or 0), source["name"])

    def _is_source_due(self, source: dict[str, Any]) -> bool:
        config = _coerce_source_config(source.get("config"))
        if config.get("disabled") or config.get("blacklisted") or not config.get("auto_sync_enabled", True):
            return False
        next_allowed_sync_at = config.get("next_allowed_sync_at")
        now = self._now()
        if next_allowed_sync_at:
            try:
                if datetime.fromisoformat(str(next_allowed_sync_at)) > now:
                    return False
            except ValueError:
                pass
        last_crawled_at = source.get("last_crawled_at")
        if not last_crawled_at:
            return True
        try:
            last_run = datetime.fromisoformat(str(last_crawled_at))
        except ValueError:
            return True
        interval_minutes = max(int(config.get("sync_interval_minutes") or 30), 5)
        return now >= last_run + timedelta(minutes=interval_minutes)

    def get_overview(self) -> dict[str, object]:
        base = self.repository.get_overview_stats()
        operations = self.get_operations()
        sources = operations["sources"]
        failure_category_counts: dict[str, int] = {}
        recommended_action_counts: dict[str, int] = {}
        trend_summary = {"healthy": 0, "watch": 0, "risky": 0, "cold": 0}
        for source in sources:
            if source.get("health_level"):
                trend_summary[str(source["health_level"])] += 1
            category = source.get("current_failure_category")
            if category:
                failure_category_counts[str(category)] = failure_category_counts.get(str(category), 0) + 1
            action = source.get("recommended_action")
            if action:
                recommended_action_counts[str(action)] = recommended_action_counts.get(str(action), 0) + 1
        base.update(
            {
                "paused_source_count": sum(1 for source in sources if source.get("is_paused")),
                "needs_attention_source_count": sum(1 for source in sources if source.get("needs_attention")),
                "failure_category_counts": failure_category_counts,
                "recommended_action_counts": recommended_action_counts,
                "source_health_trend_summary": trend_summary,
            }
        )
        return base

    def list_opportunities(
        self,
        *,
        classification: str | None = None,
        source_platform: str | None = None,
        opportunity_type: str | None = None,
        reward_type: str | None = None,
        evidence_status: str | None = None,
        sort_by: str = "created_at",
    ) -> dict[str, object]:
        items = [
            item.model_dump(mode="json")
            for item in self.repository.list_opportunities(
                classification=classification,
                source_platform=source_platform,
                opportunity_type=opportunity_type,
                reward_type=reward_type,
                evidence_status=evidence_status,
                sort_by=sort_by,
            )
        ]
        return {"items": items, "total": len(items)}

    def get_opportunity(self, opportunity_id: str) -> dict[str, object] | None:
        opportunity = self.repository.get_opportunity(opportunity_id)
        if opportunity is None:
            return None
        payload = opportunity.model_dump(mode="json")
        structured = dict(opportunity.ai_structured_evidence or {})
        run_id = structured.get("investigation_run_id")
        follow_up_urls = list(dict.fromkeys(structured.get("follow_up_urls") or opportunity.external_links or []))
        payload["investigation"] = self.repository.get_investigation_run(str(run_id)) if run_id else None
        payload["follow_up_documents"] = [
            document.model_dump(mode="json")
            for document in self.repository.list_raw_documents_for_urls(follow_up_urls, limit=10)
        ]
        return payload

    def get_operations(self) -> dict[str, object]:
        snapshot = self.repository.get_operations_snapshot()
        enriched_sources = [self._serialize_source(source) for source in snapshot["sources"]]
        enriched_sources.sort(key=self._sort_source_priority)
        failed_jobs = []
        failure_category_counts: dict[str, int] = {}
        recommended_action_counts: dict[str, int] = {}
        for job in snapshot.get("failed_jobs", []):
            category = _classify_failure_reason(job.get("error_message"))
            action = _recommended_action(category)
            if category:
                failure_category_counts[category] = failure_category_counts.get(category, 0) + 1
            if action:
                recommended_action_counts[action] = recommended_action_counts.get(action, 0) + 1
            failed_jobs.append(
                {
                    **job,
                    "failure_category": category,
                    "failure_advice": _failure_advice(category),
                    "recommended_action": action,
                }
            )
        return {
            "sources": enriched_sources,
            "recent_jobs": snapshot["recent_jobs"],
            "failed_jobs": failed_jobs,
            "failure_category_counts": failure_category_counts,
            "recommended_action_counts": recommended_action_counts,
        }

    def get_source_detail(self, source_feed_id: str) -> dict[str, object]:
        feed = self.repository.get_source_feed(source_feed_id)
        if feed is None:
            raise ValueError("source feed not found")
        source = self._serialize_source(feed.model_dump(mode="json"))
        ignored = self.repository.list_ignored_discovery_candidates()
        source["ignored_candidates"] = [item for item in ignored if _domain_key(item.get("entry_url")) == _domain_key(source.get("entry_url"))]
        source["recent_jobs"] = [job.model_dump(mode="json") for job in self.repository.list_recent_crawl_jobs_for_source(source_feed_id, limit=20)]
        source["recent_failed_jobs"] = [job for job in source["recent_jobs"] if job.get("status") == "failed"][:10]
        source["audit"] = self.repository.list_source_audit(source_feed_id, limit=20)
        return source

    def get_source_discovery(self) -> dict[str, object]:
        feeds = [feed.model_dump(mode="json") for feed in self.repository.list_source_feeds()]
        scout_settings = self.repository.get_scout_settings()
        query_templates = scout_settings.get("query_templates") or None
        ignored = {item["dedupe_key"] for item in self.repository.list_ignored_discovery_candidates()}
        candidates = [
            item for item in discover_source_candidates(feeds, query_templates=query_templates) if item.get("dedupe_key") not in ignored
        ]
        return {
            "items": candidates,
            "ignored_items": self.repository.list_ignored_discovery_candidates(),
            "total": len(candidates),
            "query_templates": list(query_templates or ()),
            "settings_updated_at": scout_settings.get("updated_at"),
        }

    def get_scout_settings(self) -> dict[str, object]:
        return self.repository.get_scout_settings()

    def update_scout_settings(self, query_templates: list[str]) -> dict[str, object]:
        return self.repository.update_scout_settings(query_templates)

    def import_discovered_source(self, payload: dict[str, Any]) -> dict[str, object]:
        entry_url = str(payload.get("entry_url") or "").strip()
        if not entry_url:
            raise ValueError("entry_url is required")
        source_platform = str(payload.get("source_platform") or "").strip() or None
        source_type = str(payload.get("source_type") or "web").strip() or "web"
        name = str(payload.get("name") or entry_url).strip()
        feed_id = self.repository.upsert_source_feed(
            {
                "name": name,
                "source_type": source_type,
                "source_platform": source_platform,
                "entry_url": entry_url,
                "status": "idle",
                "config": _coerce_source_config(
                    {
                        "discovery_queries": list(payload.get("discovery_queries") or []),
                        "imported_from": "scout",
                        "preferred_entry_url": entry_url,
                    }
                ),
            }
        )
        feed = self.repository.get_source_feed(feed_id)
        if feed is None:
            raise ValueError("failed to create source feed")
        preview = self.sync_single_source(feed.id, mode="import_preview")
        updated = self.repository.update_source_feed_config(feed.id, {"import_preview": preview})
        self.repository.append_source_audit(feed.id, "import_source", {"entry_url": entry_url, "preview": preview})
        return {
            **(updated.model_dump(mode="json") if updated else feed.model_dump(mode="json")),
            "import_preview": preview,
        }

    def ignore_discovery_candidate(self, payload: dict[str, Any]) -> dict[str, object]:
        dedupe_key = str(payload.get("dedupe_key") or "").strip()
        entry_url = str(payload.get("entry_url") or "").strip()
        if not dedupe_key or not entry_url:
            raise ValueError("dedupe_key and entry_url are required")
        return self.repository.ignore_discovery_candidate(dedupe_key, entry_url, str(payload.get("reason") or "").strip() or None)

    def unignore_discovery_candidate(self, dedupe_key: str) -> dict[str, object]:
        if not dedupe_key:
            raise ValueError("dedupe_key is required")
        return {"success": self.repository.unignore_discovery_candidate(dedupe_key), "dedupe_key": dedupe_key}

    def update_source(self, source_feed_id: str, payload: dict[str, Any]) -> dict[str, object]:
        feed = self.repository.get_source_feed(source_feed_id)
        if feed is None:
            raise ValueError("source feed not found")
        config = _coerce_source_config(feed.config)
        updated = self.repository.update_source_feed_fields(
            source_feed_id,
            {
                "name": payload.get("name", feed.name),
                "source_type": payload.get("source_type", feed.source_type),
                "source_platform": payload.get("source_platform", feed.source_platform),
                "entry_url": payload.get("entry_url", feed.entry_url),
                "config": {
                    **config,
                    "merge_group_key": payload.get("merge_group_key", config.get("merge_group_key")),
                    "preferred_entry_url": payload.get("preferred_entry_url", config.get("preferred_entry_url")),
                },
            },
        )
        if updated is None:
            raise ValueError("source feed not found")
        self.repository.append_source_audit(
            source_feed_id,
            "update_source",
            {key: payload.get(key) for key in ("name", "source_type", "source_platform", "entry_url", "merge_group_key", "preferred_entry_url")},
        )
        return self.get_source_detail(source_feed_id)

    def update_source_schedule(self, source_feed_id: str, payload: dict[str, Any]) -> dict[str, object]:
        feed = self.repository.get_source_feed(source_feed_id)
        if feed is None:
            raise ValueError("source feed not found")
        config = _coerce_source_config(feed.config)
        auto_sync_enabled = bool(payload.get("auto_sync_enabled", config.get("auto_sync_enabled", True)))
        sync_interval_minutes = max(int(payload.get("sync_interval_minutes", config.get("sync_interval_minutes", 30)) or 30), 5)
        updated = self.repository.update_source_feed_config(
            source_feed_id,
            {"auto_sync_enabled": auto_sync_enabled, "sync_interval_minutes": sync_interval_minutes},
        )
        self.repository.append_source_audit(
            source_feed_id,
            "update_schedule",
            {"auto_sync_enabled": auto_sync_enabled, "sync_interval_minutes": sync_interval_minutes},
        )
        if updated is None:
            raise ValueError("source feed not found")
        return {
            "id": updated.id,
            "auto_sync_enabled": auto_sync_enabled,
            "sync_interval_minutes": sync_interval_minutes,
            "updated_at": updated.updated_at.isoformat(),
        }

    def sync_sources(self) -> dict[str, object]:
        eligible = [
            feed
            for feed in self.repository.list_source_feeds()
            if self._is_source_due(feed.model_dump(mode="json"))
        ]
        summary = {
            "source_count": len(eligible),
            "document_count": 0,
            "candidate_count": 0,
            "opportunity_count": 0,
            "job_ids": [],
            "failures": [],
        }
        for feed in eligible:
            result = self._run_source_sync(feed.model_dump(mode="json"), mode="scheduled")
            summary["job_ids"].append(result["job_id"])
            summary["document_count"] += result["document_count"]
            summary["candidate_count"] += result["candidate_count"]
            summary["opportunity_count"] += result["opportunity_count"]
            if result.get("error"):
                summary["failures"].append({"source_feed_id": feed.id, "job_id": result["job_id"], "error": result["error"]})
        return summary

    def sync_single_source(self, source_feed_id: str, mode: str = "manual") -> dict[str, object]:
        feed = self.repository.get_source_feed(source_feed_id)
        if feed is None:
            raise ValueError("source feed not found")
        if bool((feed.config or {}).get("disabled")):
            raise ValueError("source feed is paused")
        return self._run_source_sync(feed.model_dump(mode="json"), mode=mode)

    def execute_recommended_action(self, source_feed_id: str, action: str) -> dict[str, object]:
        feed = self.repository.get_source_feed(source_feed_id)
        if feed is None:
            raise ValueError("source feed not found")
        config = _coerce_source_config(feed.config)
        if action == "reduce_depth":
            updated = self.repository.update_source_feed_config(source_feed_id, {"follow_up_depth": 1})
        elif action == "refresh_entry_url":
            updated = self.repository.update_source_feed_config(source_feed_id, {"suggest_refresh_entry_url": True})
        elif action == "slow_down_schedule":
            updated = self.repository.update_source_feed_config(
                source_feed_id,
                {"sync_interval_minutes": max(int(config.get("sync_interval_minutes", 30) or 30), 30) * 2},
            )
        elif action == "rerun_and_inspect":
            return self.sync_single_source(source_feed_id, mode="manual_recommended")
        elif action == "switch_to_authenticated_source":
            updated = self.repository.update_source_feed_config(source_feed_id, {"needs_authentication": True, "pause_mode": "suggested", "disabled": True})
        elif action == "retry_later":
            updated = self.repository.update_source_feed_config(
                source_feed_id, {"next_allowed_sync_at": (self._now() + timedelta(minutes=30)).isoformat()}
            )
        elif action == "review_extractor":
            updated = self.repository.update_source_feed_config(source_feed_id, {"needs_extractor_review": True})
        else:
            raise ValueError("unsupported recommended action")
        self.repository.append_source_audit(source_feed_id, "execute_recommended_action", {"action": action})
        if updated is None:
            raise ValueError("source feed not found")
        return self.get_source_detail(source_feed_id)

    def set_source_feed_paused(self, source_feed_id: str, paused: bool, pause_mode: str = "manual") -> dict[str, object]:
        feed = self.repository.update_source_feed_config(source_feed_id, {"disabled": paused, "pause_mode": pause_mode if paused else None})
        if feed is None:
            raise ValueError("source feed not found")
        self.repository.append_source_audit(source_feed_id, "pause_source" if paused else "resume_source", {"pause_mode": pause_mode})
        return {
            "id": feed.id,
            "is_paused": bool((feed.config or {}).get("disabled")),
            "status": feed.status,
            "updated_at": feed.updated_at.isoformat(),
        }

    def _run_source_sync(self, feed: dict[str, Any], *, mode: str) -> dict[str, object]:
        config = _coerce_source_config(feed.get("config"))
        runtime_feed = {**feed, "config": config}
        job_id = self.repository.create_crawl_job(
            {"source_feed_id": feed["id"], "status": "running", "mode": mode, "target_url": feed.get("entry_url")}
        )
        started_at = self._now().isoformat()
        self.repository.update_source_feed_runtime(feed["id"], status="running", last_crawled_at=started_at)
        summary = {"source_feed_id": feed["id"], "job_id": job_id, "document_count": 0, "candidate_count": 0, "opportunity_count": 0, "error": None}
        try:
            documents = collect_documents(runtime_feed, mode="list")
            summary["document_count"] = len(documents)
            created_opportunities = 0
            candidate_count = 0
            for document in documents:
                document["crawl_job_id"] = job_id
                raw_document_id = self.repository.create_raw_document(document)
                candidate = recall_candidate_from_document(
                    {
                        "title": document["title"],
                        "body": document.get("body", ""),
                        "source_url": document["source_url"],
                        "source_platform": document["source_platform"],
                    }
                )
                if candidate is None:
                    continue
                candidate["raw_document_id"] = raw_document_id
                candidate_id = self.repository.create_recall_candidate(candidate)
                candidate_count += 1
                evidence_bundle = _build_evidence_bundle([document])
                run_id = self.repository.create_investigation_run({"candidate_id": candidate_id, "status": "running", "current_round": 0})
                agent_run_id = self.repository.create_agent_run(
                    {
                        "thread_id": f"reward:{candidate_id}",
                        "status": "running",
                        "metadata": {
                            "crawl_job_id": job_id,
                            "candidate_id": candidate_id,
                            "source_feed_id": feed["id"],
                            "mode": mode,
                        },
                    }
                )
                trace = TraceRecorder(run_id=agent_run_id)

                def collector(_candidate: dict[str, object], action_state: dict[str, object], _round: int) -> list[dict[str, object]]:
                    planned_actions = list(action_state.get("actions", []))
                    urls = [str(action.get("target_url")) for action in planned_actions if action.get("target_url")]
                    search_queries = [
                        str(action.get("query"))
                        for action in planned_actions
                        if action.get("action_type") == "search_query" and action.get("query")
                    ]
                    for query in search_queries:
                        urls.extend(search_urls(query, max_results=3))
                    unique_urls = list(dict.fromkeys(url for url in urls if url))
                    follow_up_docs = collect_documents(runtime_feed, mode="follow_up", target_urls=unique_urls or None)
                    persisted: list[dict[str, object]] = []
                    for follow_up_document in follow_up_docs:
                        follow_up_document["crawl_job_id"] = job_id
                        follow_up_document["id"] = self.repository.create_raw_document(follow_up_document)
                        persisted.append(follow_up_document)
                    return persisted

                result = run_investigation_cycle(
                    candidate={"title": candidate["title"], "source_url": candidate["source_url"]},
                    evidence_bundle=evidence_bundle,
                    collector=collector,
                    extract_evidence=_build_evidence_bundle,
                )
                trace.record_step(
                    "reward_investigation_graph",
                    {"candidate_id": candidate_id, "evidence_bundle": evidence_bundle},
                    result,
                )
                for step_name in list(result.get("step_names") or []):
                    self.repository.append_agent_step(
                        agent_run_id,
                        {
                            "step_name": str(step_name),
                            "status": "completed" if result.get("status") != "failed" else "failed",
                            "input_payload": {"candidate_id": candidate_id},
                            "output_payload": {"status": result.get("status")},
                        },
                    )
                self.repository.append_evaluator_snapshot(agent_run_id, dict(result.get("evaluation") or {}))
                for collected_document in list(result.get("collected_documents") or []):
                    trace.record_tool_call(
                        "collect_documents",
                        {"source_feed_id": feed["id"]},
                        {"ok": True, "source_url": collected_document.get("source_url")},
                    )
                    self.repository.append_tool_call(
                        agent_run_id,
                        {
                            "tool_name": "collect_documents",
                            "status": "completed",
                            "input_payload": {"source_feed_id": feed["id"]},
                            "output_payload": {"source_url": collected_document.get("source_url")},
                        },
                    )
                if result.get("status") == "failed":
                    self.repository.update_agent_run(agent_run_id, {"status": "failed"})
                    from config import REWARD_AGENT_LANGSMITH_ENABLED

                    if REWARD_AGENT_LANGSMITH_ENABLED:
                        trace.flush_to_langsmith()
                    raise RuntimeError(str((result.get("evaluation") or {}).get("error_message") or "reward agent model evaluation failed"))

                for action in result["actions"]:
                    self.repository.append_investigation_action(run_id, action | {"status": action.get("status", "completed")})
                self.repository.update_investigation_run(run_id, {"status": result["status"], "current_round": result["rounds_used"]})
                evaluation = result["evaluation"]
                self.repository.create_evaluation_run(
                    evaluation
                    | {
                        "candidate_id": candidate_id,
                        "ai_reasoning_brief": evaluation.get("ai_reasoning_brief"),
                        "ai_risk_flags": evaluation.get("ai_risk_flags", []),
                        "ai_structured_evidence": evaluation.get("ai_structured_evidence", {}),
                    }
                )
                opportunity_id = self._merge_candidate_into_opportunity(candidate, document, result, candidate_id=candidate_id, run_id=run_id)
                if opportunity_id:
                    created_opportunities += 1
                self.repository.update_agent_run(agent_run_id, {"status": "completed"})
                from config import REWARD_AGENT_LANGSMITH_ENABLED

                if REWARD_AGENT_LANGSMITH_ENABLED:
                    trace.flush_to_langsmith()

            summary["candidate_count"] = candidate_count
            summary["opportunity_count"] = created_opportunities
            completed_at = self._now().isoformat()
            self.repository.update_crawl_job(
                job_id,
                {
                    "status": "completed",
                    "document_count": len(documents),
                    "candidate_count": candidate_count,
                    "opportunity_count": created_opportunities,
                    "completed_at": completed_at,
                },
            )
            self.repository.update_source_feed_runtime(feed["id"], status="success", last_crawled_at=started_at, last_success_at=completed_at, last_error_message=None)
            self.repository.update_source_feed_config(feed["id"], {"next_allowed_sync_at": None})
        except Exception as exc:
            completed_at = self._now().isoformat()
            error_text = str(exc)
            category = _classify_failure_reason(error_text)
            config_patch: dict[str, Any] = {}
            if category == "timeout":
                config_patch["next_allowed_sync_at"] = (self._now() + timedelta(minutes=20)).isoformat()
            elif category == "rate_limited":
                config_patch["next_allowed_sync_at"] = (self._now() + timedelta(minutes=60)).isoformat()
            self.repository.update_crawl_job(job_id, {"status": "failed", "error_message": error_text, "completed_at": completed_at})
            self.repository.update_source_feed_runtime(feed["id"], status="error", last_crawled_at=started_at, last_error_message=error_text)
            if config_patch:
                self.repository.update_source_feed_config(feed["id"], config_patch)
            summary["error"] = error_text
        return summary

    def _merge_candidate_into_opportunity(
        self,
        candidate: dict[str, Any],
        document: dict[str, Any],
        result: dict[str, Any],
        *,
        candidate_id: str,
        run_id: str,
    ) -> str:
        evaluation = result["evaluation"]
        canonical_url = document.get("canonical_url") or document["source_url"]
        dedupe_key = build_dedupe_key(title=document["title"], canonical_url=canonical_url, source_platform=document["source_platform"])
        existing = self.repository.find_opportunity_by_keys(
            canonical_url=canonical_url,
            dedupe_key=dedupe_key,
            title=document["title"],
            source_platform=document["source_platform"],
        )
        evidence_bundle = result["evidence_bundle"]
        evidence_items = [
            {"evidence_type": "reward", "snippet": snippet, "source_url": document["source_url"], "metadata": {"source": "agent"}}
            for snippet in evidence_bundle.get("reward_snippets", [])
        ] + [
            {"evidence_type": "action", "snippet": snippet, "source_url": document["source_url"], "metadata": {"source": "agent"}}
            for snippet in evidence_bundle.get("action_snippets", [])
        ] + [
            {"evidence_type": "time", "snippet": snippet, "source_url": document["source_url"], "metadata": {"source": "agent"}}
            for snippet in evidence_bundle.get("time_snippets", [])
        ] + [
            {"evidence_type": "rule", "snippet": snippet, "source_url": document["source_url"], "metadata": {"source": "agent"}}
            for snippet in evidence_bundle.get("rule_snippets", [])
        ] + [
            {"evidence_type": "eligibility", "snippet": snippet, "source_url": document["source_url"], "metadata": {"source": "agent"}}
            for snippet in evidence_bundle.get("eligibility_snippets", [])
        ] + [
            {
                "evidence_type": "external_link_result",
                "snippet": follow_up_document.get("summary") or follow_up_document.get("title") or "",
                "source_url": follow_up_document["source_url"],
                "metadata": {"source": "follow_up", "mode": follow_up_document.get("metadata", {}).get("mode")},
            }
            for follow_up_document in result.get("collected_documents", [])
            if follow_up_document.get("summary") or follow_up_document.get("title")
        ]
        structured_evidence = dict(evaluation.get("ai_structured_evidence", {}))
        structured_evidence.update(
            {
                "candidate_id": candidate_id,
                "investigation_run_id": run_id,
                "follow_up_urls": [doc.get("source_url") for doc in result.get("collected_documents", []) if doc.get("source_url")],
            }
        )
        payload = {
            "id": existing.id if existing else None,
            "title": document["title"],
            "normalized_title": normalize_title(document["title"]),
            "source_platform": document["source_platform"],
            "source_type": document.get("source_type"),
            "source_url": document["source_url"],
            "canonical_url": canonical_url,
            "published_at": document.get("published_at"),
            "discovered_at": self._now().isoformat(),
            "content_language": "en",
            "raw_text_excerpt": (document.get("body") or "")[:280],
            "opportunity_type": evaluation.get("opportunity_type") or candidate.get("opportunity_type") or candidate.get("recall_label"),
            "reward_type": evaluation.get("reward_type") or ("cash" if "$" in (document.get("body") or "") else "unknown"),
            "reward_value_text": _extract_first_money_amount(document.get("body") or ""),
            "action_required": _first_or_none(evidence_bundle.get("action_snippets")),
            "eligibility": _first_or_none(evidence_bundle.get("eligibility_snippets")),
            "deadline_text": _first_or_none(evidence_bundle.get("time_snippets")),
            "ai_stage_1_recall_reason": candidate.get("recall_reason"),
            "ai_stage_2_label": evaluation["ai_stage_2_label"],
            "ai_confidence": evaluation["ai_confidence"],
            "ai_summary": evaluation["ai_summary"],
            "ai_reasoning_brief": evaluation.get("ai_reasoning_brief"),
            "ai_missing_evidence": evaluation.get("ai_missing_evidence", []),
            "ai_risk_flags": evaluation.get("ai_risk_flags", []),
            "ai_structured_evidence": structured_evidence,
            "status": "needs_review" if evaluation["needs_investigation"] else "active",
            "dedupe_key": dedupe_key,
            "content_hash": build_content_hash(document["title"], document.get("body")),
            "last_evaluated_at": self._now().isoformat(),
            "recheck_after": (self._now() + timedelta(days=1)).isoformat(),
            "external_links": list(
                dict.fromkeys(
                    list(evidence_bundle.get("priority_links", []))
                    + list(evidence_bundle.get("external_links", []))
                    + structured_evidence.get("follow_up_urls", [])
                )
            ),
        }
        merged = merge_opportunity_payload(existing.model_dump(mode="json") if existing else None, payload)
        opportunity_id = self.repository.upsert_opportunity(merged)
        self.repository.replace_opportunity_evidence(opportunity_id, evidence_items)
        return opportunity_id
