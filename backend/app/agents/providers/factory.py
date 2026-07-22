from __future__ import annotations

from app.agents.providers.base import ExternalProvider, ExternalProviderError
from app.agents.providers.deterministic import DeterministicProvider
from app.agents.providers.disabled import DisabledProvider
from app.agents.providers.searxng import SearxngProvider
from app.core.config import WebSearchProvider, settings


def build_web_search_provider() -> ExternalProvider:
    if settings.web_search_provider is WebSearchProvider.DISABLED:
        return DisabledProvider()
    if settings.web_search_provider is WebSearchProvider.DETERMINISTIC:
        return DeterministicProvider()
    if settings.web_search_provider is WebSearchProvider.SEARXNG:
        return SearxngProvider(
            base_url=settings.searxng_url,
            timeout_seconds=settings.web_search_timeout_seconds,
            max_response_bytes=settings.web_search_max_response_bytes,
        )
    raise ExternalProviderError(str(settings.web_search_provider), "unknown_provider")
