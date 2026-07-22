from __future__ import annotations

from datetime import UTC, datetime
from urllib.parse import urlencode, urlparse

from app.agents.providers.base import ExternalProvider, ExternalProviderError, ProviderResponse
from app.agents.providers.http import fetch_limited
from app.agents.schemas import ExternalSource


class SearxngProvider(ExternalProvider):
    name = "searxng"

    def __init__(
        self,
        *,
        base_url: str,
        timeout_seconds: float,
        max_response_bytes: int,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        parsed = urlparse(self.base_url)
        self.allowed_hosts = {parsed.hostname or "searxng"}
        self.timeout_seconds = timeout_seconds
        self.max_response_bytes = max_response_bytes

    async def search(self, query: str, *, max_results: int) -> ProviderResponse:
        url = f"{self.base_url}/search?{urlencode({'q': query, 'format': 'json'})}"
        response = await fetch_limited(
            url,
            provider=self.name,
            allowed_hosts=self.allowed_hosts,
            allowed_content_types=("application/json",),
            timeout_seconds=self.timeout_seconds,
            max_response_bytes=self.max_response_bytes,
            require_https=False,
            allow_private_hosts=True,
        )
        try:
            payload = response.json()
        except ValueError as exc:
            raise ExternalProviderError(self.name, "malformed_response") from exc
        return ProviderResponse(
            provider=self.name,
            status="success",
            results=parse_searxng_results(payload, max_results=max_results),
        )


def parse_searxng_results(payload: dict, *, max_results: int) -> list[ExternalSource]:
    now = datetime.now(UTC)
    results: list[ExternalSource] = []
    for index, item in enumerate(payload.get("results", [])[:max_results], 1):
        url = str(item.get("url") or "")
        title = str(item.get("title") or "Untitled result")
        excerpt = str(item.get("content") or item.get("snippet") or "")
        if not url:
            continue
        results.append(
            ExternalSource(
                source_id=f"searxng:{index}:{url[:120]}",
                provider="searxng",
                title=title,
                canonical_url=url,
                excerpt=excerpt[:2000],
                source_type="web",
                retrieval_timestamp=now,
                trust_category="untrusted_external",
                rank=index,
            )
        )
    return results
