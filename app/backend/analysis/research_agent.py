"""
Guarded research agent with URL and domain caps.
"""

from __future__ import annotations

from urllib.parse import urlparse

from analysis.policies import ResearchPolicy
from analysis.research_fetcher import ResearchFetcher
from analysis.schemas import AnalysisContext, ResearchEvidence, ResearchResult, ScreeningResult


def _estimate_relevance(context: AnalysisContext, title: str | None, snippet: str | None) -> float:
    haystack = " ".join(part for part in [title, snippet] if part).lower()
    if not haystack:
        return 0.4
    activity_terms = {
        token
        for token in context.content.title.lower().split()
        if len(token) > 3
    }
    overlap = len(activity_terms.intersection(set(haystack.split())))
    return round(min(0.95, 0.45 + overlap * 0.12), 2)


class ResearchAgent:
    def __init__(self, *, fetcher: ResearchFetcher | None = None) -> None:
        self.fetcher = fetcher or ResearchFetcher()

    def _should_run(self, screening_result: ScreeningResult, policy: ResearchPolicy) -> bool:
        should_deep_research = bool(screening_result.structured.get("should_deep_research"))
        return should_deep_research or policy.default_mode == "deep"

    def run(
        self,
        *,
        context: AnalysisContext,
        screening_result: ScreeningResult,
        policy: ResearchPolicy,
    ) -> ResearchResult:
        if not self._should_run(screening_result, policy):
            return ResearchResult(
                state="not_requested",
                summary="Research was not requested for this screening result.",
            )

        if policy.max_urls_per_item <= 0 or policy.max_queries_per_item <= 0:
            return ResearchResult(
                state="research_unavailable",
                summary="Research budget is exhausted for this item.",
            )

        allowed_source_classes = set(policy.allowed_source_classes or [])
        candidates = self.fetcher.fetch_candidates(
            context.content.title,
            limit=policy.max_urls_per_item,
            allowed_source_classes=allowed_source_classes,
        )

        evidence: list[ResearchEvidence] = []
        domains_used: list[str] = []
        seen_domains: set[str] = set()

        for candidate in candidates:
            domain = urlparse(candidate.url).netloc.lower()
            if domain and domain not in seen_domains and len(seen_domains) >= policy.max_domains:
                continue

            if domain and domain not in seen_domains:
                seen_domains.add(domain)
                domains_used.append(domain)

            evidence.append(
                ResearchEvidence(
                    source_type=candidate.source_type,
                    url=candidate.url,
                    title=candidate.title,
                    snippet=candidate.snippet,
                    relevance_score=_estimate_relevance(context, candidate.title, candidate.snippet),
                    trust_score=candidate.trust_score,
                    supports_claim=candidate.supports_claim,
                )
            )
            if len(evidence) >= policy.max_urls_per_item:
                break

        if not evidence:
            return ResearchResult(
                state="insufficient_evidence",
                summary="Research ran but did not produce usable evidence within the configured caps.",
                evidence=[],
                domains_used=[],
                url_count=0,
                query_count=1,
            )

        return ResearchResult(
            state="completed",
            summary=f"Collected {len(evidence)} bounded research evidence items for review.",
            evidence=evidence,
            domains_used=domains_used,
            url_count=len(evidence),
            query_count=1,
        )
