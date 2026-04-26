"""
Opportunity-domain tool registry for the shared agent platform.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .service import OpportunityDomainService

if TYPE_CHECKING:
    from agent_platform.models import AgentSession
    from analysis.run_manager import AnalysisRunManager
    from data_manager import DataManager


class OpportunitySearchTool:
    name = "opportunity_search"

    def __init__(self, service: OpportunityDomainService) -> None:
        self.service = service

    def run(self, *, session: AgentSession, user_message: str) -> dict[str, Any]:
        return self.service.search_opportunities(user_message)


class OpportunityExplainTool:
    name = "opportunity_explain"

    def __init__(self, service: OpportunityDomainService) -> None:
        self.service = service

    def run(self, *, session: AgentSession, user_message: str) -> dict[str, Any]:
        return self.service.explain_opportunity(query=user_message)


class OpportunityNextActionTool:
    name = "opportunity_next_action"

    def __init__(self, service: OpportunityDomainService) -> None:
        self.service = service

    def run(self, *, session: AgentSession, user_message: str) -> dict[str, Any]:
        return self.service.suggest_next_action(query=user_message)


def build_opportunity_tool_registry(
    data_manager: DataManager,
    run_manager: AnalysisRunManager | None = None,
) -> dict[str, object]:
    service = OpportunityDomainService(data_manager=data_manager, run_manager=run_manager)
    tools = [
        OpportunitySearchTool(service),
        OpportunityExplainTool(service),
        OpportunityNextActionTool(service),
    ]
    return {tool.name: tool for tool in tools}
