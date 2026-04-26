"""
Opportunity-domain services and agent tools.
"""

from .service import OpportunityDomainService
from .tools import (
    OpportunityExplainTool,
    OpportunityNextActionTool,
    OpportunitySearchTool,
    build_opportunity_tool_registry,
)

__all__ = [
    "OpportunityDomainService",
    "OpportunityExplainTool",
    "OpportunityNextActionTool",
    "OpportunitySearchTool",
    "build_opportunity_tool_registry",
]
