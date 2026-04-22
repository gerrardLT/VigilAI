"""
Provider registry exports for agent-analysis.
"""

from __future__ import annotations

from config import ANALYSIS_PROVIDER

from analysis.providers.base import AnalysisProvider, ProviderModelRoute, ProviderResponse, ProviderUsage
from analysis.providers.mock_provider import MockAnalysisProvider
from analysis.providers.openai_provider import OpenAIAnalysisProvider
from analysis.providers.router import AnalysisModelRouter

PROVIDER_REGISTRY = {
    "mock": MockAnalysisProvider,
    "openai": OpenAIAnalysisProvider,
}


def build_analysis_provider(provider_name: str | None = None, **kwargs) -> AnalysisProvider:
    resolved_name = (provider_name or ANALYSIS_PROVIDER or "mock").lower()
    provider_cls = PROVIDER_REGISTRY.get(resolved_name)
    if provider_cls is None:
        raise ValueError(f"Unsupported analysis provider: {resolved_name}")
    return provider_cls(**kwargs)


__all__ = [
    "AnalysisModelRouter",
    "AnalysisProvider",
    "MockAnalysisProvider",
    "OpenAIAnalysisProvider",
    "PROVIDER_REGISTRY",
    "ProviderModelRoute",
    "ProviderResponse",
    "ProviderUsage",
    "build_analysis_provider",
]
