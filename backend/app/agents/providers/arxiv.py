from __future__ import annotations

from datetime import UTC, datetime
from urllib.parse import urlencode

from defusedxml import ElementTree as ET

from app.agents.providers.base import ExternalProvider, ExternalProviderError, ProviderResponse
from app.agents.providers.http import fetch_limited
from app.agents.schemas import ExternalSource

ATOM = "{http://www.w3.org/2005/Atom}"


class ArxivProvider(ExternalProvider):
    name = "arxiv"

    def __init__(self, *, timeout_seconds: float, max_response_bytes: int) -> None:
        self.timeout_seconds = timeout_seconds
        self.max_response_bytes = max_response_bytes

    async def search(self, query: str, *, max_results: int) -> ProviderResponse:
        url = "https://export.arxiv.org/api/query?" + urlencode(
            {
                "search_query": f"all:{query}",
                "start": 0,
                "max_results": max_results,
            }
        )
        response = await fetch_limited(
            url,
            provider=self.name,
            allowed_hosts={"export.arxiv.org"},
            allowed_content_types=("application/atom+xml", "application/xml", "text/xml"),
            timeout_seconds=self.timeout_seconds,
            max_response_bytes=self.max_response_bytes,
        )
        return ProviderResponse(
            provider=self.name,
            status="success",
            results=parse_arxiv_results(response.text, max_results=max_results),
        )


def parse_arxiv_results(payload: str, *, max_results: int) -> list[ExternalSource]:
    try:
        root = ET.fromstring(payload)
    except ET.ParseError as exc:
        raise ExternalProviderError("arxiv", "malformed_response") from exc
    now = datetime.now(UTC)
    results: list[ExternalSource] = []
    for index, entry in enumerate(root.findall(f"{ATOM}entry")[:max_results], 1):
        title = _text(entry, "title") or "arXiv result"
        url = _text(entry, "id") or ""
        excerpt = _text(entry, "summary") or ""
        published = _text(entry, "published")
        authors = [
            _text(author, "name")
            for author in entry.findall(f"{ATOM}author")
            if _text(author, "name")
        ]
        if not url:
            continue
        results.append(
            ExternalSource(
                source_id=f"arxiv:{url.rsplit('/', 1)[-1]}",
                provider="arxiv",
                title=" ".join(title.split()),
                canonical_url=url,
                excerpt=" ".join(excerpt.split())[:2000],
                source_type="paper",
                retrieval_timestamp=now,
                trust_category="public_research",
                rank=index,
                publication_date=published,
                authors=authors[:20],
            )
        )
    return results


def _text(node: ET.Element, name: str) -> str | None:
    child = node.find(f"{ATOM}{name}")
    return child.text.strip() if child is not None and child.text else None
