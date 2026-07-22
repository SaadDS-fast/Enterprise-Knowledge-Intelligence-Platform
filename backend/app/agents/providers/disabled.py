from __future__ import annotations

from app.agents.providers.base import ExternalProvider, ProviderResponse


class DisabledProvider(ExternalProvider):
    name = "disabled"

    async def search(self, query: str, *, max_results: int) -> ProviderResponse:
        return ProviderResponse(
            provider=self.name,
            status="disabled",
            disabled=True,
            error="External provider is disabled",
        )
