"""Canonical JSON profile for VAP-1.

VAP-1 uses the RFC 8785 ordering and compact JSON representation, while deliberately rejecting
floating-point values because the passport schema has no numeric measurements. This removes the
cross-runtime number-serialization ambiguity from the initial profile.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import Any


class CanonicalizationError(ValueError):
    """Raised when a value cannot be represented by the VAP-1 canonical profile."""


MAX_CANONICAL_DEPTH = 64


def _validate(value: Any, *, depth: int = 0) -> None:
    if depth > MAX_CANONICAL_DEPTH:
        raise CanonicalizationError("maximum_json_depth_exceeded")
    if value is None or isinstance(value, (str, bool)):
        return
    if isinstance(value, int) and not isinstance(value, bool):
        if abs(value) > 9_007_199_254_740_991:
            raise CanonicalizationError("integer_outside_i_json_safe_range")
        return
    if isinstance(value, float):
        raise CanonicalizationError("floating_point_values_are_not_allowed_in_vap_1")
    if isinstance(value, Mapping):
        for key, item in value.items():
            if not isinstance(key, str):
                raise CanonicalizationError("object_keys_must_be_strings")
            _validate(item, depth=depth + 1)
        return
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for item in value:
            _validate(item, depth=depth + 1)
        return
    raise CanonicalizationError(f"unsupported_json_type:{type(value).__name__}")


def _string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":"))


def _utf16_sort_key(value: str) -> bytes:
    # RFC 8785 section 3.2.3 orders property names by their raw UTF-16 code units.
    return value.encode("utf-16-be", errors="surrogatepass")


def _render(value: Any) -> str:
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, str):
        return _string(value)
    if isinstance(value, int):
        return str(value)
    if isinstance(value, Mapping):
        members = (
            f"{_string(key)}:{_render(value[key])}" for key in sorted(value, key=_utf16_sort_key)
        )
        return "{" + ",".join(members) + "}"
    return "[" + ",".join(_render(item) for item in value) + "]"


def canonicalize(value: Any) -> bytes:
    """Return canonical UTF-8 JSON bytes for a VAP-1-compatible value."""

    _validate(value)
    try:
        return _render(value).encode("utf-8")
    except (TypeError, ValueError, UnicodeError) as exc:
        raise CanonicalizationError("invalid_json_value") from exc


def parse_json_strict(raw: bytes) -> Any:
    """Parse UTF-8 JSON while rejecting duplicate object keys and non-standard constants."""

    def object_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise CanonicalizationError(f"duplicate_json_key:{key}")
            result[key] = value
        return result

    def reject_constant(value: str) -> None:
        raise CanonicalizationError(f"invalid_json_constant:{value}")

    try:
        return json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=object_pairs,
            parse_constant=reject_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CanonicalizationError("invalid_utf8_json") from exc
