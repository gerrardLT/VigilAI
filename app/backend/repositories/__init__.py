"""Repository layer for VigilAI data access.

Provides async CRUD repositories that use SQLitePool for connection management.
"""

from repositories.analysis_repository import AnalysisRepository
from repositories.digest_repository import DigestRepository
from repositories.opportunity_repository import OpportunityRepository
from repositories.source_repository import SourceRepository

__all__ = [
    "AnalysisRepository",
    "DigestRepository",
    "OpportunityRepository",
    "SourceRepository",
]
