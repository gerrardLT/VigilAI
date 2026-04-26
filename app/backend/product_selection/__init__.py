"""
Product-selection bounded context.
"""

from .models import (
    PlatformScope,
    ProductOpportunity,
    ProductOpportunitySignal,
    ProductResearchQuery,
    ProductTrackingState,
    QueryType,
    ResearchJobStatus,
)
from .repository import ProductSelectionRepository, ensure_product_selection_tables
from .service import ProductSelectionService

__all__ = [
    "PlatformScope",
    "ProductOpportunity",
    "ProductOpportunitySignal",
    "ProductResearchQuery",
    "ProductSelectionRepository",
    "ProductSelectionService",
    "ProductTrackingState",
    "QueryType",
    "ResearchJobStatus",
    "ensure_product_selection_tables",
]
