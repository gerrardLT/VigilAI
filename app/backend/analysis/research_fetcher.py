"""
Guarded research fetcher primitives for agent-analysis.
"""

from __future__ import annotations

from copy import deepcopy

from pydantic import BaseModel


class FetchedDocument(BaseModel):
    source_type: str
    url: str
    title: str | None = None
    snippet: str | None = None
    trust_score: float | None = None
    supports_claim: bool | None = None


class ResearchFetcher:
    def __init__(self, *, documents: list[FetchedDocument] | None = None) -> None:
        self.documents = list(documents or [])

    def fetch_candidates(
        self,
        query: str,
        *,
        limit: int,
        allowed_source_classes: set[str] | None = None,
    ) -> list[FetchedDocument]:
        del query
        allowed = {value for value in (allowed_source_classes or set()) if value}
        candidates = self.documents
        if allowed:
            candidates = [document for document in candidates if document.source_type in allowed]
        return [deepcopy(document) for document in candidates[: max(limit, 0)]]
