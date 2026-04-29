"""
Provider registry exports for agent-analysis.
"""

from __future__ import annotations

from config import ANALYSIS_PROVIDER

from analysis.providers.base import AnalysisProvider, ProviderModelRoute, ProviderResponse, ProviderUsage
from analysis.providers.deterministic_provider import DeterministicTestAnalysisProvider
from analysis.providers.disabled_provider import DisabledAnalysisProvider
from analysis.providers.openai_provider import OpenAIAnalysisProvider
from analysis.providers.router import AnalysisModelRouter

PROVIDER_REGISTRY = {
    "disabled": "analysis.providers.disabled_provider:DisabledAnalysisProvider",
    "mock": "analysis.providers.deterministic_provider:DeterministicTestAnalysisProvider",
    "openai": "analysis.providers.openai_provider:OpenAIAnalysisProvider",
    "test": "analysis.providers.deterministic_provider:DeterministicTestAnalysisProvider",
}


def _resolve_provider_class(provider_name: str) -> type[AnalysisProvider]:
    target = PROVIDER_REGISTRY.get(provider_name)
    if target is None:
        raise ValueError(f"Unsupported analysis provider: {provider_name}")
    module_name, class_name = target.split(":", 1)
    module = __import__(module_name, fromlist=[class_name])
    provider_cls = getattr(module, class_name, None)
    if provider_cls is None:
        raise ValueError(f"Provider class {class_name} not found in {module_name}")
    return provider_cls


def build_analysis_provider(provider_name: str | None = None, **kwargs) -> AnalysisProvider:
    resolved_name = (provider_name or ANALYSIS_PROVIDER or "disabled").lower()
    provider_cls = _resolve_provider_class(resolved_name)
    return provider_cls(**kwargs)


__all__ = [
    "AnalysisModelRouter",
    "AnalysisProvider",
    "DeterministicTestAnalysisProvider",
    "DisabledAnalysisProvider",
    "OpenAIAnalysisProvider",
    "PROVIDER_REGISTRY",
    "ProviderModelRoute",
    "ProviderResponse",
    "ProviderUsage",
    "build_analysis_provider",
]
