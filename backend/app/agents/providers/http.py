from __future__ import annotations

import httpx

from app.agents.providers.base import ExternalProviderError
from app.security.outbound import validate_outbound_url, validate_redirect_chain


async def fetch_limited(
    url: str,
    *,
    provider: str,
    allowed_hosts: set[str],
    allowed_content_types: tuple[str, ...],
    timeout_seconds: float,
    max_response_bytes: int,
    require_https: bool = True,
    allow_private_hosts: bool = False,
    transport: httpx.AsyncBaseTransport | None = None,
) -> httpx.Response:
    current = validate_outbound_url(
        url,
        allowed_hosts=allowed_hosts,
        provider=provider,
        require_https=require_https,
        allow_private_hosts=allow_private_hosts,
    ).url
    timeout = httpx.Timeout(timeout_seconds, read=timeout_seconds)
    async with httpx.AsyncClient(
        timeout=timeout,
        follow_redirects=False,
        trust_env=False,
        transport=transport,
        headers={"User-Agent": "ekip-agent-external-tools/1.0"},
    ) as client:
        for _ in range(4):
            try:
                response = await client.get(current)
            except httpx.TimeoutException as exc:
                raise TimeoutError(provider) from exc
            if response.is_redirect:
                location = response.headers.get("location")
                if not location:
                    raise ExternalProviderError(provider, "redirect_without_location")
                next_url = str(response.url.join(location))
                current = validate_redirect_chain(
                    next_url,
                    allowed_hosts=allowed_hosts,
                    provider=provider,
                    require_https=require_https,
                    allow_private_hosts=allow_private_hosts,
                ).url
                continue
            content_type = response.headers.get("content-type", "").split(";", 1)[0].strip()
            if content_type not in allowed_content_types:
                raise ExternalProviderError(provider, "invalid_content_type")
            content_length = response.headers.get("content-length")
            if content_length and int(content_length) > max_response_bytes:
                raise ExternalProviderError(provider, "oversized_response")
            if len(response.content) > max_response_bytes:
                raise ExternalProviderError(provider, "oversized_response")
            response.raise_for_status()
            return response
    raise ExternalProviderError(provider, "too_many_redirects")
