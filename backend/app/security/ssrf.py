from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse

from app.exceptions.base import AppError
from app.exceptions.codes import ErrorCode

ALLOWED_SCHEMES = {"http", "https"}


def validate_outbound_url(url: str, allowed_hosts: set[str] | None = None) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in ALLOWED_SCHEMES or not parsed.hostname:
        raise AppError(ErrorCode.UNSAFE_INPUT, "Only absolute HTTP(S) URLs are permitted", 400)
    hostname = parsed.hostname.lower()
    if allowed_hosts is not None and hostname not in allowed_hosts:
        raise AppError(ErrorCode.UNSAFE_INPUT, "The destination host is not allowlisted", 400)
    try:
        addresses = {item[4][0] for item in socket.getaddrinfo(hostname, parsed.port or 443)}
    except socket.gaierror as exc:
        raise AppError(
            ErrorCode.UNSAFE_INPUT, "The destination host could not be resolved", 400
        ) from exc
    for raw in addresses:
        ip = ipaddress.ip_address(raw)
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
            raise AppError(
                ErrorCode.UNSAFE_INPUT, "Private or reserved network destinations are blocked", 400
            )
    return url
