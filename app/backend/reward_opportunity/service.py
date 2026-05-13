"""Application service for reward-opportunity APIs."""

from __future__ import annotations

from .repository import RewardOpportunityRepository


class RewardOpportunityService:
    def __init__(self, repository: RewardOpportunityRepository):
        self.repository = repository

    def get_overview(self) -> dict[str, object]:
        stats = self.repository.get_overview_stats()
        return {
            "source_count": stats["source_count"],
            "opportunity_count": stats["opportunity_count"],
            "candidate_count": 0,
            "high_value_count": 0,
        }

    def list_opportunities(self) -> dict[str, object]:
        items = [item.model_dump(mode="json") for item in self.repository.list_opportunities()]
        return {"items": items, "total": len(items)}

    def get_opportunity(self, opportunity_id: str) -> dict[str, object] | None:
        opportunity = self.repository.get_opportunity(opportunity_id)
        if opportunity is None:
            return None
        return opportunity.model_dump(mode="json")

    def get_operations(self) -> dict[str, object]:
        return {"sources": [], "recent_jobs": []}

