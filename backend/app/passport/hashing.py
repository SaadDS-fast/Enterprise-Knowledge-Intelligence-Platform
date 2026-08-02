"""Domain-separated content hashes for Verifiable Answer Passports."""

from __future__ import annotations

import base64
import binascii
import hashlib

ALLOWED_DOMAINS = frozenset(
    {"PASSPORT", "ANSWER", "CLAIM", "EVIDENCE_SPAN", "DOCUMENT", "SCOPE", "CONFIG"}
)


def b64url_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def b64url_decode(value: str) -> bytes:
    alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"
    if (
        not value
        or "=" in value
        or any(character.isspace() for character in value)
        or any(character not in alphabet for character in value)
    ):
        raise ValueError("invalid_base64url")
    try:
        decoded = base64.b64decode(value + "=" * (-len(value) % 4), altchars=b"-_", validate=True)
        if b64url_encode(decoded) != value:
            raise ValueError("noncanonical_base64url")
        return decoded
    except (ValueError, binascii.Error) as exc:
        raise ValueError("invalid_base64url") from exc


def content_digest(domain: str, content: bytes, *, protocol_version: str = "VAP1") -> str:
    """Hash content using the VAP-1 field-domain prefix and return unpadded base64url."""

    normalized = domain.upper()
    if normalized not in ALLOWED_DOMAINS:
        raise ValueError("unsupported_hash_domain")
    if not protocol_version or "\0" in protocol_version or not protocol_version.isascii():
        raise ValueError("invalid_protocol_version")
    digest = hashlib.sha256(
        protocol_version.encode("ascii") + b"\0" + normalized.encode("ascii") + b"\0" + content
    ).digest()
    return b64url_encode(digest)
