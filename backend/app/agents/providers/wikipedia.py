from __future__ import annotations

from datetime import UTC, datetime
from urllib.parse import urlencode

from app.agents.providers.base import ExternalProvider, ExternalProviderError, ProviderResponse
from app.agents.providers.http import fetch_limited
from app.agents.schemas import ExternalSource


class WikipediaProvider(ExternalProvider):
    name = "wikipedia"

    def __init__(self, *, timeout_seconds: float, max_response_bytes: int) -> None:
        self.timeout_seconds = timeout_seconds
        self.max_response_bytes = max_response_bytes

    async def search(self, query: str, *, max_results: int) -> ProviderResponse:
        url = "https://en.wikipedia.org/w/api.php?" + urlencode(
            {
                "action": "query",
                "format": "json",
                "generator": "search",
                "gsrsearch": query,
                "gsrlimit": max_results,
                "prop": "extracts|info",
                "exintro": "1",
                "explaintext": "1",
                "inprop": "url",
                "redirects": "1",
            }
        )
        response = await fetch_limited(
            url,
            provider=self.name,
            allowed_hosts={"en.wikipedia.org"},
            allowed_content_types=("application/json",),
            timeout_seconds=self.timeout_seconds,
            max_response_bytes=self.max_response_bytes,
        )
        try:
            payload = response.json()
        except ValueError as exc:
            raise ExternalProviderError(self.name, "malformed_response") from exc
        return ProviderResponse(
            provider=self.name,
            status="success",
            results=parse_wikipedia_results(payload, max_results=max_results),
        )


def parse_wikipedia_results(payload: dict, *, max_results: int) -> list[ExternalSource]:
    now = datetime.now(UTC)
    pages = list((payload.get("query") or {}).get("pages", {}).values())
    pages.sort(key=lambda item: item.get("index", 10_000))
    results: list[ExternalSource] = []
    for index, page in enumerate(pages[:max_results], 1):
        title = str(page.get("title") or "Wikipedia result")
        url = str(page.get("fullurl") or f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}")
        excerpt = str(page.get("extract") or "")
        results.append(
            ExternalSource(
                source_id=f"wikipedia:{page.get('pageid', index)}",
                provider="wikipedia",
                title=title,
                canonical_url=url,
                excerpt=excerpt[:2000],
                source_type="encyclopedia",
                retrieval_timestamp=now,
                trust_category="public_reference",
                rank=index,
            )
        )
    return results
