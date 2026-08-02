"""Provider-neutral VAP signing-key lifecycle foundation.

Only public metadata crosses the registry boundary.  The included signing provider is an
ephemeral, process-local test reference and intentionally has no export operation.
"""

from __future__ import annotations

import asyncio
import hashlib
from collections.abc import Awaitable, Callable, Sequence
from datetime import UTC, datetime
from enum import StrEnum
from typing import Literal, Protocol, TypeVar
from uuid import uuid4

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.passport.canonical import canonicalize
from app.passport.hashing import b64url_decode, b64url_encode
from app.passport.jws import sign_detached


class KeyLifecycleError(ValueError):
    """A lifecycle invariant or provider boundary was violated."""


class SigningKeyState(StrEnum):
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    RETIRED = "RETIRED"
    REVOKED = "REVOKED"


class RevocationReason(StrEnum):
    KEY_COMPROMISE = "KEY_COMPROMISE"
    SUPERSEDED = "SUPERSEDED"
    CESSATION_OF_OPERATION = "CESSATION_OF_OPERATION"
    POLICY_VIOLATION = "POLICY_VIOLATION"
    UNSPECIFIED = "UNSPECIFIED"


class LifecycleEventType(StrEnum):
    KEY_REGISTERED = "KEY_REGISTERED"
    KEY_ACTIVATED = "KEY_ACTIVATED"
    KEY_ROTATED = "KEY_ROTATED"
    KEY_RETIRED = "KEY_RETIRED"
    KEY_REVOKED = "KEY_REVOKED"
    TRUST_BUNDLE_GENERATED = "TRUST_BUNDLE_GENERATED"
    TRUST_BUNDLE_VALIDATED = "TRUST_BUNDLE_VALIDATED"
    TRUST_BUNDLE_REJECTED = "TRUST_BUNDLE_REJECTED"


ALLOWED_TRANSITIONS = frozenset(
    {
        (SigningKeyState.PENDING, SigningKeyState.ACTIVE),
        (SigningKeyState.PENDING, SigningKeyState.REVOKED),
        (SigningKeyState.ACTIVE, SigningKeyState.RETIRED),
        (SigningKeyState.ACTIVE, SigningKeyState.REVOKED),
        (SigningKeyState.RETIRED, SigningKeyState.REVOKED),
    }
)


def _utc(value: datetime, name: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
        raise ValueError(f"{name}_must_be_utc")
    return value


class SigningKeyMetadata(BaseModel):
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
    activated_at: datetime | None = None
    retired_at: datetime | None = None
    revoked_at: datetime | None = None
    revocation_reason: RevocationReason | None = None
    rotation_generation: int = Field(ge=1)
    predecessor_key_id: str | None = Field(default=None, min_length=1, max_length=200)
    successor_key_id: str | None = Field(default=None, min_length=1, max_length=200)
    metadata_checksum: str

    @field_validator("public_key")
    @classmethod
    def validate_public_key(cls, value: str) -> str:
        if len(b64url_decode(value)) != 32:
            raise ValueError("ed25519_public_key_must_be_32_bytes")
        return value

    @field_validator("metadata_checksum")
    @classmethod
    def validate_checksum_encoding(cls, value: str) -> str:
        if len(b64url_decode(value)) != 32:
            raise ValueError("metadata_checksum_must_be_sha256")
        return value

    @model_validator(mode="after")
    def validate_metadata(self) -> SigningKeyMetadata:
        for name in ("created_at", "not_before", "not_after"):
            _utc(getattr(self, name), name)
        for name in ("activated_at", "retired_at", "revoked_at"):
            value = getattr(self, name)
            if value is not None:
                _utc(value, name)
        if self.not_after <= self.not_before or self.created_at > self.not_after:
            raise ValueError("invalid_key_validity_interval")
        state = self.lifecycle_state
        if state is SigningKeyState.PENDING and any(
            value is not None for value in (self.activated_at, self.retired_at, self.revoked_at)
        ):
            raise ValueError("pending_key_has_terminal_timestamp")
        if state is SigningKeyState.ACTIVE and (
            self.activated_at is None or self.retired_at is not None or self.revoked_at is not None
        ):
            raise ValueError("invalid_active_timestamps")
        if state is SigningKeyState.RETIRED and (
            self.activated_at is None or self.retired_at is None or self.revoked_at is not None
        ):
            raise ValueError("invalid_retired_timestamps")
        if state is SigningKeyState.REVOKED and self.revoked_at is None:
            raise ValueError("revoked_key_requires_timestamp")
        if (self.revoked_at is None) != (self.revocation_reason is None):
            raise ValueError("revocation_timestamp_and_reason_required_together")
        if self.activated_at is not None and not (
            self.not_before <= self.activated_at < self.not_after
        ):
            raise ValueError("activation_outside_validity_interval")
        if self.retired_at is not None and (
            self.activated_at is None or self.retired_at < self.activated_at
        ):
            raise ValueError("retirement_precedes_activation")
        if self.revoked_at is not None and self.revoked_at < self.created_at:
            raise ValueError("revocation_precedes_creation")
        if self.predecessor_key_id == self.key_id or self.successor_key_id == self.key_id:
            raise ValueError("self_referential_key_link")
        if metadata_checksum(self) != self.metadata_checksum:
            raise ValueError("metadata_checksum_mismatch")
        return self


def metadata_checksum(value: SigningKeyMetadata | dict[str, object]) -> str:
    data = value.model_dump(mode="json") if isinstance(value, SigningKeyMetadata) else dict(value)
    data.pop("metadata_checksum", None)
    data = {
        key: item.astimezone(UTC).isoformat().replace("+00:00", "Z")
        if isinstance(item, datetime)
        else item
        for key, item in data.items()
    }
    return b64url_encode(hashlib.sha256(canonicalize(data)).digest())


def build_key_metadata(**values: object) -> SigningKeyMetadata:
    data = dict(values)
    data["metadata_checksum"] = metadata_checksum(data)
    return SigningKeyMetadata.model_validate(data)


class LifecycleAuditEvent(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    event_type: LifecycleEventType
    event_id: str = Field(min_length=1, max_length=200)
    issuer_id: str = Field(min_length=1, max_length=200)
    timestamp: datetime
    key_id: str | None = Field(default=None, max_length=200)
    previous_key_id: str | None = Field(default=None, max_length=200)
    lifecycle_state: SigningKeyState | None = None
    bundle_version: int | None = Field(default=None, ge=1)
    checksum: str | None = None
    reason_code: RevocationReason | None = None
    actor_id: str | None = Field(default=None, max_length=200)
    correlation_id: str | None = Field(default=None, max_length=200)

    @field_validator("timestamp")
    @classmethod
    def validate_timestamp(cls, value: datetime) -> datetime:
        return _utc(value, "timestamp")


LifecycleAuditSink = Callable[[LifecycleAuditEvent], Awaitable[None]]


class PrivateSigningProvider(Protocol):
    async def public_key(self, key_id: str) -> str: ...

    async def sign(self, key_id: str, payload: bytes) -> str: ...


class EphemeralSigningProvider:
    """Process-local reference provider. Private material has no serialization API."""

    def __init__(self) -> None:
        self.__keys: dict[str, Ed25519PrivateKey] = {}
        self.__lock = asyncio.Lock()

    async def create(self, key_id: str) -> str:
        async with self.__lock:
            if key_id in self.__keys:
                raise KeyLifecycleError("provider_key_id_exists")
            key = Ed25519PrivateKey.generate()
            self.__keys[key_id] = key
            return _public_key(key)

    async def inject(self, key_id: str, key: Ed25519PrivateKey) -> str:
        """Inject a deterministic in-memory test key without serializing it."""
        async with self.__lock:
            if key_id in self.__keys:
                raise KeyLifecycleError("provider_key_id_exists")
            self.__keys[key_id] = key
            return _public_key(key)

    async def public_key(self, key_id: str) -> str:
        async with self.__lock:
            key = self.__keys.get(key_id)
            if key is None:
                raise KeyLifecycleError("private_signer_unavailable")
            return _public_key(key)

    async def sign(self, key_id: str, payload: bytes) -> str:
        async with self.__lock:
            key = self.__keys.get(key_id)
            if key is None:
                raise KeyLifecycleError("private_signer_unavailable")
            return sign_detached(payload, key, key_id)


def _public_key(key: Ed25519PrivateKey) -> str:
    raw = key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw
    )
    return b64url_encode(raw)


T = TypeVar("T")
RegistryMutation = Callable[
    [tuple[SigningKeyMetadata, ...], frozenset[str]],
    tuple[Sequence[SigningKeyMetadata], T],
]


class KeyMetadataRegistry(Protocol):
    async def list(self, issuer_id: str) -> tuple[SigningKeyMetadata, ...]: ...

    async def mutate(self, issuer_id: str, operation: RegistryMutation[T]) -> T: ...


class InMemoryKeyMetadataRegistry:
    """Atomic reference registry; future stores must give ``mutate`` the same semantics."""

    def __init__(self) -> None:
        self.__records: dict[str, dict[str, SigningKeyMetadata]] = {}
        self.__used_ids: dict[str, set[str]] = {}
        self.__locks: dict[str, asyncio.Lock] = {}

    def _lock(self, issuer_id: str) -> asyncio.Lock:
        return self.__locks.setdefault(issuer_id, asyncio.Lock())

    async def list(self, issuer_id: str) -> tuple[SigningKeyMetadata, ...]:
        async with self._lock(issuer_id):
            return tuple(
                sorted(self.__records.get(issuer_id, {}).values(), key=lambda item: item.key_id)
            )

    async def mutate(self, issuer_id: str, operation: RegistryMutation[T]) -> T:
        async with self._lock(issuer_id):
            current = tuple(self.__records.get(issuer_id, {}).values())
            used = frozenset(self.__used_ids.get(issuer_id, set()))
            proposed, result = operation(current, used)
            records = tuple(proposed)
            _validate_registry(issuer_id, records)
            current_ids = {item.key_id for item in current}
            proposed_ids = {item.key_id for item in records}
            removed = current_ids - proposed_ids
            if removed:
                raise KeyLifecycleError("historical_key_removal_forbidden")
            new_ids = proposed_ids - current_ids
            if new_ids & used:
                raise KeyLifecycleError("key_id_reuse")
            self.__records[issuer_id] = {item.key_id: item for item in records}
            self.__used_ids.setdefault(issuer_id, set()).update(proposed_ids)
            return result


def _validate_registry(issuer_id: str, records: Sequence[SigningKeyMetadata]) -> None:
    if any(item.issuer_id != issuer_id for item in records):
        raise KeyLifecycleError("cross_issuer_key_injection")
    ids = [item.key_id for item in records]
    if len(ids) != len(set(ids)):
        raise KeyLifecycleError("duplicate_key_id")
    generations = [item.rotation_generation for item in records]
    if len(generations) != len(set(generations)):
        raise KeyLifecycleError("duplicate_rotation_generation")
    if sum(item.lifecycle_state is SigningKeyState.ACTIVE for item in records) > 1:
        raise KeyLifecycleError("multiple_active_keys")
    by_id = {item.key_id: item for item in records}
    for item in records:
        if item.predecessor_key_id is not None:
            predecessor = by_id.get(item.predecessor_key_id)
            if predecessor is None or (
                item.lifecycle_state is not SigningKeyState.PENDING
                and predecessor.successor_key_id != item.key_id
            ):
                raise KeyLifecycleError("invalid_predecessor_link")
        if item.successor_key_id is not None:
            successor = by_id.get(item.successor_key_id)
            if successor is None or successor.predecessor_key_id != item.key_id:
                raise KeyLifecycleError("invalid_successor_link")


def _replace(record: SigningKeyMetadata, **updates: object) -> SigningKeyMetadata:
    data = record.model_dump(mode="json")
    data.update(updates)
    data.pop("metadata_checksum", None)
    return build_key_metadata(**data)


class KeyLifecycleService:
    def __init__(
        self,
        registry: KeyMetadataRegistry,
        provider: PrivateSigningProvider,
        *,
        clock: Callable[[], datetime] | None = None,
        identifier: Callable[[], str] | None = None,
        audit_sink: LifecycleAuditSink | None = None,
    ) -> None:
        self.registry = registry
        self.provider = provider
        self.clock = clock or (lambda: datetime.now(UTC))
        self.identifier = identifier or (lambda: str(uuid4()))
        self.audit_sink = audit_sink

    async def _audit(self, event_type: LifecycleEventType, issuer_id: str, **data: object) -> None:
        if self.audit_sink is not None:
            await self.audit_sink(
                LifecycleAuditEvent(
                    event_type=event_type,
                    event_id=self.identifier(),
                    issuer_id=issuer_id,
                    timestamp=self.clock(),
                    **data,
                )
            )

    async def register_pending(
        self,
        *,
        issuer_id: str,
        key_id: str,
        not_before: datetime,
        not_after: datetime,
        predecessor_key_id: str | None = None,
        actor_id: str | None = None,
    ) -> SigningKeyMetadata:
        now = _utc(self.clock(), "clock")
        public_key = await self.provider.public_key(key_id)

        def operation(
            records: tuple[SigningKeyMetadata, ...], used: frozenset[str]
        ) -> tuple[Sequence[SigningKeyMetadata], SigningKeyMetadata]:
            if key_id in used or any(item.key_id == key_id for item in records):
                raise KeyLifecycleError("key_id_reuse")
            generation = max((item.rotation_generation for item in records), default=0) + 1
            if predecessor_key_id is not None and not any(
                item.key_id == predecessor_key_id for item in records
            ):
                raise KeyLifecycleError("unknown_predecessor")
            record = build_key_metadata(
                metadata_schema_version="vap-key-metadata-1",
                issuer_id=issuer_id,
                key_id=key_id,
                algorithm="EdDSA",
                public_key=public_key,
                lifecycle_state=SigningKeyState.PENDING,
                created_at=now,
                not_before=_utc(not_before, "not_before"),
                not_after=_utc(not_after, "not_after"),
                activated_at=None,
                retired_at=None,
                revoked_at=None,
                revocation_reason=None,
                rotation_generation=generation,
                predecessor_key_id=predecessor_key_id,
                successor_key_id=None,
            )
            return (*records, record), record

        record = await self.registry.mutate(issuer_id, operation)
        await self._audit(
            LifecycleEventType.KEY_REGISTERED,
            issuer_id,
            key_id=key_id,
            lifecycle_state=SigningKeyState.PENDING,
            actor_id=actor_id,
        )
        return record

    async def _validate_correspondence(self, record: SigningKeyMetadata) -> None:
        challenge = canonicalize(
            {"issuer_id": record.issuer_id, "key_id": record.key_id, "purpose": "vap-key-check-1"}
        )
        envelope = await self.provider.sign(record.key_id, challenge)
        from app.passport.jws import verify_detached

        try:
            verify_detached(
                challenge,
                envelope,
                Ed25519PublicKey.from_public_bytes(b64url_decode(record.public_key)),
            )
        except (InvalidSignature, ValueError) as exc:
            raise KeyLifecycleError("private_public_key_mismatch") from exc

    async def activate(
        self, issuer_id: str, key_id: str, *, actor_id: str | None = None
    ) -> SigningKeyMetadata:
        records = await self.registry.list(issuer_id)
        pending = next((item for item in records if item.key_id == key_id), None)
        if pending is None:
            raise KeyLifecycleError("unknown_key")
        await self._validate_correspondence(pending)
        await asyncio.sleep(0)  # explicit cancellation point before the atomic commit
        now = _utc(self.clock(), "clock")

        def operation(
            records: tuple[SigningKeyMetadata, ...], used: frozenset[str]
        ) -> tuple[Sequence[SigningKeyMetadata], SigningKeyMetadata]:
            del used
            current = next((item for item in records if item.key_id == key_id), None)
            if current is None or current.lifecycle_state is not SigningKeyState.PENDING:
                raise KeyLifecycleError("transition_not_allowed")
            if any(item.lifecycle_state is SigningKeyState.ACTIVE for item in records):
                raise KeyLifecycleError("active_key_exists_use_rotation")
            if not (current.not_before <= now < current.not_after):
                raise KeyLifecycleError("activation_outside_validity_interval")
            activated = _replace(current, lifecycle_state=SigningKeyState.ACTIVE, activated_at=now)
            return tuple(
                activated if item.key_id == key_id else item for item in records
            ), activated

        active = await self.registry.mutate(issuer_id, operation)
        await self._audit(
            LifecycleEventType.KEY_ACTIVATED,
            issuer_id,
            key_id=key_id,
            lifecycle_state=SigningKeyState.ACTIVE,
            actor_id=actor_id,
        )
        return active

    async def rotate(
        self,
        *,
        issuer_id: str,
        key_id: str,
        not_before: datetime,
        not_after: datetime,
        actor_id: str | None = None,
    ) -> SigningKeyMetadata:
        before = await self.registry.list(issuer_id)
        prior = next(
            (item for item in before if item.lifecycle_state is SigningKeyState.ACTIVE), None
        )
        pending = await self.register_pending(
            issuer_id=issuer_id,
            key_id=key_id,
            not_before=not_before,
            not_after=not_after,
            predecessor_key_id=prior.key_id if prior else None,
            actor_id=actor_id,
        )
        await self._validate_correspondence(pending)
        await asyncio.sleep(0)
        now = _utc(self.clock(), "clock")

        def operation(
            records: tuple[SigningKeyMetadata, ...], used: frozenset[str]
        ) -> tuple[Sequence[SigningKeyMetadata], SigningKeyMetadata]:
            del used
            new = next((item for item in records if item.key_id == key_id), None)
            old = next(
                (item for item in records if item.lifecycle_state is SigningKeyState.ACTIVE), None
            )
            if new is None or new.lifecycle_state is not SigningKeyState.PENDING:
                raise KeyLifecycleError("rotation_key_not_pending")
            if not (new.not_before <= now < new.not_after):
                raise KeyLifecycleError("activation_outside_validity_interval")
            activated = _replace(
                new,
                lifecycle_state=SigningKeyState.ACTIVE,
                activated_at=now,
                predecessor_key_id=old.key_id if old else None,
            )
            changed: list[SigningKeyMetadata] = []
            for item in records:
                if item.key_id == new.key_id:
                    changed.append(activated)
                elif old is not None and item.key_id == old.key_id:
                    changed.append(
                        _replace(
                            old,
                            lifecycle_state=SigningKeyState.RETIRED,
                            retired_at=now,
                            successor_key_id=new.key_id,
                        )
                    )
                else:
                    changed.append(item)
            return changed, activated

        active = await self.registry.mutate(issuer_id, operation)
        await self._audit(
            LifecycleEventType.KEY_ROTATED,
            issuer_id,
            key_id=key_id,
            previous_key_id=prior.key_id if prior else None,
            lifecycle_state=SigningKeyState.ACTIVE,
            actor_id=actor_id,
        )
        return active

    async def transition(
        self,
        issuer_id: str,
        key_id: str,
        target: SigningKeyState,
        *,
        reason: RevocationReason | None = None,
        actor_id: str | None = None,
    ) -> SigningKeyMetadata:
        now = _utc(self.clock(), "clock")

        def operation(
            records: tuple[SigningKeyMetadata, ...], used: frozenset[str]
        ) -> tuple[Sequence[SigningKeyMetadata], SigningKeyMetadata]:
            del used
            record = next((item for item in records if item.key_id == key_id), None)
            if record is None:
                raise KeyLifecycleError("unknown_key")
            if (record.lifecycle_state, target) not in ALLOWED_TRANSITIONS:
                raise KeyLifecycleError("transition_not_allowed")
            if target is SigningKeyState.ACTIVE:
                raise KeyLifecycleError("activation_requires_correspondence_validation")
            if target is SigningKeyState.RETIRED:
                changed = _replace(record, lifecycle_state=target, retired_at=now)
            else:
                if reason is None:
                    raise KeyLifecycleError("revocation_reason_required")
                changed = _replace(
                    record,
                    lifecycle_state=target,
                    revoked_at=now,
                    revocation_reason=reason,
                )
            return tuple(changed if item.key_id == key_id else item for item in records), changed

        result = await self.registry.mutate(issuer_id, operation)
        event = (
            LifecycleEventType.KEY_RETIRED
            if target is SigningKeyState.RETIRED
            else LifecycleEventType.KEY_REVOKED
        )
        await self._audit(
            event,
            issuer_id,
            key_id=key_id,
            lifecycle_state=target,
            reason_code=reason,
            actor_id=actor_id,
        )
        return result

    async def resolve_active(self, issuer_id: str, at: datetime) -> SigningKeyMetadata:
        at = _utc(at, "issuance_time")
        records = await self.registry.list(issuer_id)
        active = [item for item in records if item.lifecycle_state is SigningKeyState.ACTIVE]
        if len(active) != 1:
            raise KeyLifecycleError("active_signer_unavailable")
        record = active[0]
        if not (record.not_before <= at < record.not_after):
            raise KeyLifecycleError("active_signer_outside_validity_interval")
        if await self.provider.public_key(record.key_id) != record.public_key:
            raise KeyLifecycleError("private_public_key_mismatch")
        return record


class LifecyclePassportSigner:
    """Phase 2 resolved-key signer; selection is server-side and rechecked before signing."""

    def __init__(self, issuer_id: str, service: KeyLifecycleService) -> None:
        self.issuer_id = issuer_id
        self.service = service

    async def resolve_key_id(self, at: datetime) -> str:
        return (await self.service.resolve_active(self.issuer_id, at)).key_id

    async def sign_for_key(self, payload: bytes, key_id: str, at: datetime) -> str:
        active = await self.service.resolve_active(self.issuer_id, at)
        if active.key_id != key_id:
            raise KeyLifecycleError("resolved_key_changed")
        return await self.service.provider.sign(key_id, payload)
