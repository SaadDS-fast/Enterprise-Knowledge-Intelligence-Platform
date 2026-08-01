"""Narrow detached-JWS profile for VAP-1 Ed25519 signatures."""

from __future__ import annotations

from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

from app.passport.canonical import canonicalize, parse_json_strict
from app.passport.hashing import b64url_decode, b64url_encode


class JWSError(ValueError):
    """Raised for an invalid or unsupported VAP-1 JWS envelope."""


def _protected_header(key_id: str) -> dict[str, str]:
    if not key_id or len(key_id) > 200:
        raise JWSError("invalid_key_id")
    return {"alg": "EdDSA", "kid": key_id, "typ": "application/vap+jws"}


def sign_detached(payload: bytes, private_key: Ed25519PrivateKey, key_id: str) -> str:
    """Sign canonical manifest bytes and return compact JWS with a detached payload."""

    protected = b64url_encode(canonicalize(_protected_header(key_id)))
    signing_input = protected.encode("ascii") + b"." + b64url_encode(payload).encode("ascii")
    signature = private_key.sign(signing_input)
    return f"{protected}..{b64url_encode(signature)}"


def parse_header(detached_jws: str) -> dict[str, Any]:
    parts = detached_jws.split(".")
    if len(parts) != 3 or parts[1] != "":
        raise JWSError("jws_must_have_detached_payload")
    try:
        header = parse_json_strict(b64url_decode(parts[0]))
    except ValueError as exc:
        raise JWSError("invalid_protected_header") from exc
    if not isinstance(header, dict):
        raise JWSError("invalid_protected_header")
    if header.get("alg") != "EdDSA":
        raise JWSError("unsupported_algorithm")
    if header != _protected_header(str(header.get("kid", ""))):
        raise JWSError("unsupported_protected_header")
    return header


def verify_detached(payload: bytes, detached_jws: str, public_key: Ed25519PublicKey) -> str:
    """Verify a detached JWS and return its protected key identifier."""

    header = parse_header(detached_jws)
    protected, _, encoded_signature = detached_jws.split(".")
    try:
        signature = b64url_decode(encoded_signature)
        if len(signature) != 64:
            raise JWSError("invalid_ed25519_signature_length")
        signing_input = protected.encode("ascii") + b"." + b64url_encode(payload).encode("ascii")
        public_key.verify(signature, signing_input)
    except InvalidSignature as exc:
        raise JWSError("signature_verification_failed") from exc
    return str(header["kid"])
