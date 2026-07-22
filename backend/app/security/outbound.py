from __future__ import annotations

import ipaddress
import socket
from dataclasses import dataclass
from urllib.parse import urlparse, urlunparse

from app.observability.metrics import AGENT_SSRF_BLOCKS

BLOCKED_HOSTNAMES = {
    "localhost",
    "metadata",
    "metadata.google.internal",
    "169.254.169.254",
    "backend",
    "frontend",
    "postgres",
    "redis",
    "minio",
    "prometheus",
    "grafana",
    "otel-collector",
    "host.docker.internal",
}
ALLOWED_SCHEMES = {"http", "https"}
PUBLIC_HOSTS_REQUIRING_HTTPS = {"wikipedia.org", "api.wikimedia.org", "export.arxiv.org"}


class OutboundRequestBlocked(ValueError):
    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(reason)


@dataclass(frozen=True, slots=True)
class ValidatedURL:
    url: str
    hostname: str
    scheme: str


def validate_outbound_url(
    url: str,
    *,
    allowed_hosts: set[str],
    provider: str,
    require_https: bool = True,
    allow_private_hosts: bool = False,
) -> ValidatedURL:
    parsed = urlparse(url.strip())
    hostname = (parsed.hostname or "").lower().rstrip(".")
    scheme = parsed.scheme.lower()
    try:
        if scheme not in ALLOWED_SCHEMES:
            raise OutboundRequestBlocked("unsupported_scheme")
        if require_https and scheme != "https":
            raise OutboundRequestBlocked("https_required")
        if not hostname:
            raise OutboundRequestBlocked("missing_hostname")
        if hostname not in allowed_hosts and not any(
            hostname.endswith(f".{h}") for h in allowed_hosts
        ):
            raise OutboundRequestBlocked("host_not_allowlisted")
        if hostname in BLOCKED_HOSTNAMES and not allow_private_hosts:
            raise OutboundRequestBlocked("blocked_hostname")
        if _is_ip_blocked(hostname) and not allow_private_hosts:
            raise OutboundRequestBlocked("blocked_ip_literal")
        if _requires_https(hostname) and scheme != "https":
            raise OutboundRequestBlocked("public_https_required")
        if not allow_private_hosts:
            _validate_dns(hostname)
    except OutboundRequestBlocked as exc:
        AGENT_SSRF_BLOCKS.labels(provider=provider, outcome=exc.reason).inc()
        raise
    normalized = urlunparse(
        (
            scheme,
            parsed.netloc,
            parsed.path or "/",
            "",
            parsed.query,
            "",
        )
    )
    return ValidatedURL(url=normalized, hostname=hostname, scheme=scheme)


def validate_redirect_chain(
    url: str,
    *,
    allowed_hosts: set[str],
    provider: str,
    require_https: bool = True,
    allow_private_hosts: bool = False,
) -> ValidatedURL:
    return validate_outbound_url(
        url,
        allowed_hosts=allowed_hosts,
        provider=provider,
        require_https=require_https,
        allow_private_hosts=allow_private_hosts,
    )


def _validate_dns(hostname: str) -> None:
    try:
        infos = socket.getaddrinfo(hostname, None)
    except socket.gaierror as exc:
        raise OutboundRequestBlocked("dns_resolution_failed") from exc
    for info in infos:
        address = info[4][0]
        if _is_ip_blocked(address):
            raise OutboundRequestBlocked("dns_resolved_private")


def _is_ip_blocked(value: str) -> bool:
    try:
        ip = ipaddress.ip_address(value)
    except ValueError:
        return False
    return (
        ip.is_loopback
        or ip.is_private
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )


def _requires_https(hostname: str) -> bool:
    return hostname in PUBLIC_HOSTS_REQUIRING_HTTPS or any(
        hostname.endswith(f".{host}") for host in PUBLIC_HOSTS_REQUIRING_HTTPS
    )
