"""Canonical public trust-bundle construction and deterministic offline validation."""

from __future__ import annotations

import asyncio
import hashlib
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from enum import StrEnum
from typing import Literal, Protocol

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.passport.canonical import canonicalize, parse_json_strict
from app.passport.hashing import b64url_decode, b64url_encode
from app.passport.key_lifecycle import KeyMetadataRegistry, SigningKeyMetadata, SigningKeyState


class TrustBundleStatus(StrEnum):
    VALID = "VALID"
    VALID_UNSIGNED_TEST_BUNDLE = "VALID_UNSIGNED_TEST_BUNDLE"
    STALE = "STALE"
    EXPIRED = "EXPIRED"
    INVALID_SCHEMA = "INVALID_SCHEMA"
    CHECKSUM_MISMATCH = "CHECKSUM_MISMATCH"
    INVALID_SIGNATURE = "INVALID_SIGNATURE"
    UNKNOWN_TRUST_ANCHOR = "UNKNOWN_TRUST_ANCHOR"
    UNSUPPORTED_ALGORITHM = "UNSUPPORTED_ALGORITHM"
    CONFLICTING_KEY_RECORD = "CONFLICTING_KEY_RECORD"
    INVALID_LIFECYCLE = "INVALID_LIFECYCLE"
    VERSION_ROLLBACK = "VERSION_ROLLBACK"
    CHAIN_MISMATCH = "CHAIN_MISMATCH"
    INDETERMINATE = "INDETERMINATE"


class TrustAnchorState(StrEnum):
    TRUSTED = "TRUSTED"
    REVOKED = "REVOKED"
    EXPIRED = "EXPIRED"


class PublicTrustKey(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    metadata_schema_version: Literal["vap-key-metadata-1"]
    issuer_id: str = Field(min_length=1, max_length=200)
    key_id: str = Field(min_length=1, max_length=200)
    algorithm: Literal["EdDSA"]
    public_key: str
    lifecycle_state: SigningKeyState
    created_at: datetime
    not_before: datetime
    not_after: datetime
    activated_at: datetime | None
    retired_at: datetime | None
    revoked_at: datetime | None
    revocation_reason: str | None
    rotation_generation: int = Field(ge=1)
    predecessor_key_id: str | None
    successor_key_id: str | None
    metadata_checksum: str

    @model_validator(mode="after")
    def validate_as_metadata(self) -> PublicTrustKey:
        SigningKeyMetadata.model_validate(self.model_dump(mode="json"))
        return self


class TrustAnchorReference(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    anchor_id: str = Field(min_length=1, max_length=200)
    algorithm: Literal["EdDSA"]


class LifecycleTrustBundle(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["vap-trust-1"]
    profile: Literal["vap-key-lifecycle-1"]
    issuer_id: str = Field(min_length=1, max_length=200)
    bundle_version: int = Field(ge=1)
    generated_at: datetime
    next_update: datetime
    valid_until: datetime
    supported_algorithms: tuple[Literal["EdDSA"], ...] = Field(min_length=1, max_length=1)
    keys: tuple[PublicTrustKey, ...] = Field(min_length=1, max_length=1_000)
    previous_bundle_checksum: str | None = None
    trust_anchor: TrustAnchorReference | None = None
    bundle_checksum: str

    @field_validator("bundle_checksum")
    @classmethod
    def checksum_is_sha256(cls, value: str) -> str:
        if len(b64url_decode(value)) != 32:
            raise ValueError("bundle_checksum_must_be_sha256")
        return value

    @field_validator("previous_bundle_checksum")
    @classmethod
    def previous_checksum_is_sha256(cls, value: str | None) -> str | None:
        if value is not None and len(b64url_decode(value)) != 32:
            raise ValueError("previous_bundle_checksum_must_be_sha256")
        return value

    @model_validator(mode="after")
    def validate_bundle(self) -> LifecycleTrustBundle:
        times = (self.generated_at, self.next_update, self.valid_until)
        if any(item.tzinfo is None or item.utcoffset() != UTC.utcoffset(item) for item in times):
            raise ValueError("bundle_timestamps_must_be_utc")
        if not self.generated_at < self.next_update <= self.valid_until:
            raise ValueError("invalid_bundle_validity_interval")
        if self.supported_algorithms != ("EdDSA",):
            raise ValueError("unsupported_algorithm")
        if any(item.issuer_id != self.issuer_id for item in self.keys):
            raise ValueError("cross_issuer_key_injection")
        ids = [item.key_id for item in self.keys]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate_key_id")
        generations = [item.rotation_generation for item in self.keys]
        if len(generations) != len(set(generations)):
            raise ValueError("duplicate_rotation_generation")
        if (
            tuple(sorted(self.keys, key=lambda item: (item.rotation_generation, item.key_id)))
            != self.keys
        ):
            raise ValueError("noncanonical_key_order")
        by_id = {item.key_id: item for item in self.keys}
        for item in self.keys:
            if item.predecessor_key_id is not None:
                predecessor = by_id.get(item.predecessor_key_id)
                if predecessor is None or (
                    item.lifecycle_state is not SigningKeyState.PENDING
                    and predecessor.successor_key_id != item.key_id
                ):
                    raise ValueError("invalid_predecessor_link")
            if item.successor_key_id is not None:
                successor = by_id.get(item.successor_key_id)
                if successor is None or successor.predecessor_key_id != item.key_id:
                    raise ValueError("invalid_successor_link")
        return self


class TrustBundleSignature(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["vap-trust-signature-1"]
    anchor_id: str = Field(min_length=1, max_length=200)
    algorithm: Literal["EdDSA"]
    signature: str

    @field_validator("signature")
    @classmethod
    def signature_length(cls, value: str) -> str:
        if len(b64url_decode(value)) != 64:
            raise ValueError("invalid_ed25519_signature_length")
        return value


class TrustAnchorSigner(Protocol):
    @property
    def anchor_id(self) -> str: ...

    async def sign(self, payload: bytes) -> bytes: ...


class EphemeralTrustAnchorSigner:
    """Injected test-only anchor with no private-key export operation."""

    def __init__(self, anchor_id: str, key: Ed25519PrivateKey | None = None) -> None:
        self.anchor_id = anchor_id
        self.__key = key or Ed25519PrivateKey.generate()

    async def sign(self, payload: bytes) -> bytes:
        return self.__key.sign(payload)

    def public_record(
        self,
        *,
        not_before: datetime,
        not_after: datetime,
        state: TrustAnchorState = TrustAnchorState.TRUSTED,
    ) -> TrustAnchorRecord:
        public = self.__key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw
        )
        return TrustAnchorRecord(
            anchor_id=self.anchor_id,
            algorithm="EdDSA",
            public_key=b64url_encode(public),
            state=state,
            not_before=not_before,
            not_after=not_after,
        )


class TrustAnchorRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    anchor_id: str = Field(min_length=1, max_length=200)
    algorithm: Literal["EdDSA"]
    public_key: str
    state: TrustAnchorState
    not_before: datetime
    not_after: datetime

    @model_validator(mode="after")
    def validate_anchor(self) -> TrustAnchorRecord:
        if len(b64url_decode(self.public_key)) != 32:
            raise ValueError("invalid_anchor_public_key")
        if any(
            item.tzinfo is None or item.utcoffset() != UTC.utcoffset(item)
            for item in (self.not_before, self.not_after)
        ):
            raise ValueError("anchor_timestamps_must_be_utc")
        if self.not_after <= self.not_before:
            raise ValueError("invalid_anchor_validity")
        return self


class TrustedBundleState(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    issuer_id: str
    latest_bundle_version: int = Field(ge=1)
    latest_bundle_checksum: str
    latest_generated_at: datetime
    retained_key_ids: frozenset[str] = Field(default_factory=frozenset)

    @field_validator("latest_bundle_checksum")
    @classmethod
    def latest_checksum_is_sha256(cls, value: str) -> str:
        if len(b64url_decode(value)) != 32:
            raise ValueError("latest_bundle_checksum_must_be_sha256")
        return value


class TrustBundleValidationResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    status: TrustBundleStatus
    integrity_valid: bool
    signature_valid: bool | None
    freshness: Literal["fresh", "stale", "expired", "not_evaluated"]
    issuer_id: str | None = None
    bundle_version: int | None = None
    bundle_checksum: str | None = None
    error: str | None = None


class BuiltTrustBundle(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    bundle: bytes
    signature: bytes | None
    verifier_bundle: bytes
    bundle_checksum: str
    bundle_version: int


def _bundle_checksum(data: dict[str, object]) -> str:
    unsigned = dict(data)
    unsigned.pop("bundle_checksum", None)
    return b64url_encode(hashlib.sha256(canonicalize(unsigned)).digest())


def _phase1_verifier_bundle(records: Sequence[SigningKeyMetadata], generated_at: datetime) -> bytes:
    """Project lifecycle metadata into the backward-compatible Phase 1 verifier schema."""

    keys: list[dict[str, object]] = []
    for item in sorted(records, key=lambda record: (record.rotation_generation, record.key_id)):
        if item.lifecycle_state is SigningKeyState.PENDING:
            continue
        status = {
            SigningKeyState.ACTIVE: "trusted",
            SigningKeyState.RETIRED: "retired",
            SigningKeyState.REVOKED: "revoked",
        }[item.lifecycle_state]
        keys.append(
            {
                "key_id": item.key_id,
                "algorithm": "EdDSA",
                "public_key": item.public_key,
                "status": status,
                "not_before": item.not_before,
                "not_after": item.not_after,
                "retired_at": item.retired_at,
                "revoked_at": item.revoked_at,
            }
        )
    if not keys:
        raise ValueError("no_verification_eligible_keys")
    from app.passport.schema import TrustBundle

    bundle = TrustBundle.model_validate(
        {"schema_version": "vap-trust-1", "generated_at": generated_at, "keys": keys}
    )
    return canonicalize(bundle.model_dump(mode="json"))


class TrustBundleBuilder:
    def __init__(self, *, clock: Callable[[], datetime] | None = None) -> None:
        self.clock = clock or (lambda: datetime.now(UTC))

    async def build(
        self,
        *,
        issuer_id: str,
        records: Sequence[SigningKeyMetadata],
        bundle_version: int,
        next_update: datetime,
        valid_until: datetime,
        previous_bundle_checksum: str | None = None,
        signer: TrustAnchorSigner | None = None,
    ) -> BuiltTrustBundle:
        generated_at = self.clock()

        def wire_time(value: datetime) -> str:
            return value.astimezone(UTC).isoformat().replace("+00:00", "Z")

        public_keys = tuple(
            PublicTrustKey.model_validate(item.model_dump(mode="json"))
            for item in sorted(records, key=lambda item: (item.rotation_generation, item.key_id))
        )
        data: dict[str, object] = {
            "schema_version": "vap-trust-1",
            "profile": "vap-key-lifecycle-1",
            "issuer_id": issuer_id,
            "bundle_version": bundle_version,
            "generated_at": wire_time(generated_at),
            "next_update": wire_time(next_update),
            "valid_until": wire_time(valid_until),
            "supported_algorithms": ["EdDSA"],
            "keys": [item.model_dump(mode="json") for item in public_keys],
            "previous_bundle_checksum": previous_bundle_checksum,
            "trust_anchor": {"anchor_id": signer.anchor_id, "algorithm": "EdDSA"}
            if signer
            else None,
        }
        data["bundle_checksum"] = _bundle_checksum(data)
        bundle = LifecycleTrustBundle.model_validate(data)
        raw = canonicalize(bundle.model_dump(mode="json"))
        signature = None
        if signer is not None:
            signature = canonicalize(
                TrustBundleSignature(
                    schema_version="vap-trust-signature-1",
                    anchor_id=signer.anchor_id,
                    algorithm="EdDSA",
                    signature=b64url_encode(await signer.sign(raw)),
                ).model_dump(mode="json")
            )
        return BuiltTrustBundle(
            bundle=raw,
            signature=signature,
            verifier_bundle=_phase1_verifier_bundle(records, generated_at),
            bundle_checksum=bundle.bundle_checksum,
            bundle_version=bundle.bundle_version,
        )


class InMemoryTrustBundleSeries:
    """Test reference that binds bundle versions to atomic registry lifecycle revisions."""

    def __init__(self, registry: KeyMetadataRegistry, builder: TrustBundleBuilder) -> None:
        self.registry = registry
        self.builder = builder
        self.__locks: dict[str, asyncio.Lock] = {}
        self.__latest: dict[str, BuiltTrustBundle] = {}

    async def build(
        self,
        *,
        issuer_id: str,
        next_update: datetime,
        valid_until: datetime,
        signer: TrustAnchorSigner | None = None,
    ) -> BuiltTrustBundle:
        lock = self.__locks.setdefault(issuer_id, asyncio.Lock())
        async with lock:
            version, records = await self.registry.versioned_snapshot(issuer_id)
            if version < 1:
                raise ValueError("empty_lifecycle_registry")
            previous = self.__latest.get(issuer_id)
            if previous is not None and version <= previous.bundle_version:
                raise ValueError("bundle_version_not_advanced")
            artifact = await self.builder.build(
                issuer_id=issuer_id,
                records=records,
                bundle_version=version,
                next_update=next_update,
                valid_until=valid_until,
                previous_bundle_checksum=previous.bundle_checksum if previous else None,
                signer=signer,
            )
            self.__latest[issuer_id] = artifact
            return artifact


def _result(status: TrustBundleStatus, **values: object) -> TrustBundleValidationResult:
    defaults: dict[str, object] = {
        "integrity_valid": False,
        "signature_valid": None,
        "freshness": "not_evaluated",
    }
    defaults.update(values)
    return TrustBundleValidationResult(status=status, **defaults)


def validate_trust_bundle(
    bundle_bytes: bytes,
    *,
    signature_bytes: bytes | None = None,
    anchors: Sequence[TrustAnchorRecord] = (),
    at: datetime,
    trusted_state: TrustedBundleState | None = None,
    allow_unsigned_test_bundle: bool = False,
) -> TrustBundleValidationResult:
    """Validate without network access; the supplied anchor is the independent trust input."""
    try:
        parsed = parse_json_strict(bundle_bytes)
        if not isinstance(parsed, dict) or canonicalize(parsed) != bundle_bytes:
            raise ValueError("bundle_not_canonical")
        expected_checksum = _bundle_checksum(parsed)
        supplied_checksum = parsed.get("bundle_checksum")
        if expected_checksum != supplied_checksum:
            return _result(TrustBundleStatus.CHECKSUM_MISMATCH, error="bundle_checksum_mismatch")
        bundle = LifecycleTrustBundle.model_validate(parsed)
    except Exception as exc:
        message = str(exc)
        status = (
            TrustBundleStatus.UNSUPPORTED_ALGORITHM
            if "unsupported_algorithm" in message
            else TrustBundleStatus.CONFLICTING_KEY_RECORD
            if any(word in message for word in ("duplicate", "cross_issuer"))
            else TrustBundleStatus.INVALID_LIFECYCLE
            if any(
                word in message for word in ("lifecycle", "timestamp", "predecessor", "successor")
            )
            else TrustBundleStatus.INVALID_SCHEMA
        )
        return _result(status, error="invalid_trust_bundle")

    common = {
        "issuer_id": bundle.issuer_id,
        "bundle_version": bundle.bundle_version,
        "bundle_checksum": bundle.bundle_checksum,
    }
    if trusted_state is not None:
        if bundle.issuer_id != trusted_state.issuer_id:
            return _result(TrustBundleStatus.CHAIN_MISMATCH, error="issuer_substitution", **common)
        if bundle.bundle_version < trusted_state.latest_bundle_version:
            return _result(
                TrustBundleStatus.VERSION_ROLLBACK, error="lower_bundle_version", **common
            )
        if bundle.bundle_version == trusted_state.latest_bundle_version:
            if bundle.bundle_checksum != trusted_state.latest_bundle_checksum:
                return _result(
                    TrustBundleStatus.VERSION_ROLLBACK, error="version_collision", **common
                )
        elif bundle.previous_bundle_checksum != trusted_state.latest_bundle_checksum:
            return _result(
                TrustBundleStatus.CHAIN_MISMATCH, error="previous_checksum_mismatch", **common
            )
        if trusted_state.retained_key_ids - {item.key_id for item in bundle.keys}:
            return _result(
                TrustBundleStatus.CONFLICTING_KEY_RECORD,
                error="retained_historical_key_removed",
                **common,
            )
        if bundle.generated_at < trusted_state.latest_generated_at:
            return _result(
                TrustBundleStatus.VERSION_ROLLBACK, error="generated_at_rollback", **common
            )

    signature_valid: bool | None = None
    if bundle.trust_anchor is None:
        if signature_bytes is not None:
            return _result(
                TrustBundleStatus.INVALID_SIGNATURE, error="unexpected_signature", **common
            )
        if not allow_unsigned_test_bundle:
            return _result(TrustBundleStatus.INDETERMINATE, integrity_valid=True, **common)
    else:
        if signature_bytes is None:
            return _result(
                TrustBundleStatus.INVALID_SIGNATURE, error="signature_required", **common
            )
        try:
            raw_signature = parse_json_strict(signature_bytes)
            signature = TrustBundleSignature.model_validate(raw_signature)
        except Exception:
            return _result(
                TrustBundleStatus.INVALID_SIGNATURE, error="invalid_signature_schema", **common
            )
        if signature.anchor_id != bundle.trust_anchor.anchor_id:
            return _result(
                TrustBundleStatus.INVALID_SIGNATURE, error="anchor_substitution", **common
            )
        anchor = next((item for item in anchors if item.anchor_id == signature.anchor_id), None)
        if anchor is None:
            return _result(TrustBundleStatus.UNKNOWN_TRUST_ANCHOR, error="unknown_anchor", **common)
        if anchor.state is TrustAnchorState.REVOKED:
            return _result(TrustBundleStatus.INVALID_SIGNATURE, error="revoked_anchor", **common)
        if anchor.state is TrustAnchorState.EXPIRED or not (
            anchor.not_before <= at < anchor.not_after
        ):
            return _result(TrustBundleStatus.EXPIRED, error="expired_anchor", **common)
        try:
            Ed25519PublicKey.from_public_bytes(b64url_decode(anchor.public_key)).verify(
                b64url_decode(signature.signature), bundle_bytes
            )
            signature_valid = True
        except InvalidSignature:
            return _result(
                TrustBundleStatus.INVALID_SIGNATURE, error="signature_modified", **common
            )

    if at > bundle.valid_until:
        return _result(
            TrustBundleStatus.EXPIRED,
            integrity_valid=True,
            signature_valid=signature_valid,
            freshness="expired",
            **common,
        )
    if at > bundle.next_update:
        return _result(
            TrustBundleStatus.STALE,
            integrity_valid=True,
            signature_valid=signature_valid,
            freshness="stale",
            **common,
        )
    status = (
        TrustBundleStatus.VALID
        if bundle.trust_anchor is not None
        else TrustBundleStatus.VALID_UNSIGNED_TEST_BUNDLE
    )
    return _result(
        status,
        integrity_valid=True,
        signature_valid=signature_valid,
        freshness="fresh",
        **common,
    )
