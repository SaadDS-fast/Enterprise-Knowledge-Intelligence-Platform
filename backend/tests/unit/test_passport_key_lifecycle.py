from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
from pydantic import ValidationError

from app.passport.hashing import b64url_decode, b64url_encode
from app.passport.jws import verify_detached
from app.passport.key_lifecycle import (
    EphemeralSigningProvider,
    InMemoryKeyMetadataRegistry,
    KeyLifecycleError,
    KeyLifecycleService,
    LifecyclePassportSigner,
    RevocationReason,
    SigningKeyState,
    build_key_metadata,
)

NOW = datetime(2026, 8, 2, 12, tzinfo=UTC)


def clock() -> datetime:
    return NOW


async def setup_service() -> tuple[KeyLifecycleService, EphemeralSigningProvider]:
    provider = EphemeralSigningProvider()
    service = KeyLifecycleService(InMemoryKeyMetadataRegistry(), provider, clock=clock)
    return service, provider


async def pending(service: KeyLifecycleService, provider: EphemeralSigningProvider, key_id: str):
    await provider.create(key_id)
    return await service.register_pending(
        issuer_id="issuer-a",
        key_id=key_id,
        not_before=NOW - timedelta(days=1),
        not_after=NOW + timedelta(days=30),
    )


@pytest.mark.asyncio
async def test_register_activate_and_sign_with_resolved_key() -> None:
    service, provider = await setup_service()
    record = await pending(service, provider, "key-1")
    assert record.lifecycle_state is SigningKeyState.PENDING
    with pytest.raises(KeyLifecycleError, match="active_signer_unavailable"):
        await service.resolve_active("issuer-a", NOW)
    active = await service.activate("issuer-a", "key-1")
    signer = LifecyclePassportSigner("issuer-a", service)
    assert await signer.resolve_key_id(NOW) == "key-1"
    signature = await signer.sign_for_key(b"canonical", "key-1", NOW)
    verify_detached(
        b"canonical",
        signature,
        Ed25519PublicKey.from_public_bytes(b64url_decode(active.public_key)),
    )


@pytest.mark.asyncio
async def test_pending_retired_revoked_and_expired_keys_cannot_sign() -> None:
    service, provider = await setup_service()
    await pending(service, provider, "key-1")
    signer = LifecyclePassportSigner("issuer-a", service)
    with pytest.raises(KeyLifecycleError):
        await signer.resolve_key_id(NOW)
    await service.activate("issuer-a", "key-1")
    await service.transition("issuer-a", "key-1", SigningKeyState.RETIRED)
    with pytest.raises(KeyLifecycleError):
        await signer.resolve_key_id(NOW)
    await service.transition(
        "issuer-a", "key-1", SigningKeyState.REVOKED, reason=RevocationReason.SUPERSEDED
    )
    with pytest.raises(KeyLifecycleError):
        await signer.resolve_key_id(NOW)


@pytest.mark.asyncio
async def test_rotation_is_atomic_and_retains_history() -> None:
    service, provider = await setup_service()
    await pending(service, provider, "key-1")
    await service.activate("issuer-a", "key-1")
    await provider.create("key-2")
    active = await service.rotate(
        issuer_id="issuer-a",
        key_id="key-2",
        not_before=NOW,
        not_after=NOW + timedelta(days=60),
    )
    records = await service.registry.list("issuer-a")
    assert active.key_id == "key-2"
    assert sum(item.lifecycle_state is SigningKeyState.ACTIVE for item in records) == 1
    old = next(item for item in records if item.key_id == "key-1")
    assert old.lifecycle_state is SigningKeyState.RETIRED
    assert old.successor_key_id == "key-2"


@pytest.mark.asyncio
async def test_concurrent_rotations_never_create_two_active_keys() -> None:
    service, provider = await setup_service()
    await pending(service, provider, "key-1")
    await service.activate("issuer-a", "key-1")
    await provider.create("key-2")
    await provider.create("key-3")

    async def rotate(key_id: str) -> object:
        return await service.rotate(
            issuer_id="issuer-a",
            key_id=key_id,
            not_before=NOW,
            not_after=NOW + timedelta(days=90),
        )

    results = await asyncio.gather(rotate("key-2"), rotate("key-3"), return_exceptions=True)
    assert any(not isinstance(item, Exception) for item in results)
    records = await service.registry.list("issuer-a")
    assert sum(item.lifecycle_state is SigningKeyState.ACTIVE for item in records) == 1
    assert {item.key_id for item in records} == {"key-1", "key-2", "key-3"}


@pytest.mark.asyncio
async def test_concurrent_activation_attempts_have_one_winner() -> None:
    service, provider = await setup_service()
    await pending(service, provider, "key-1")
    await pending(service, provider, "key-2")
    results = await asyncio.gather(
        service.activate("issuer-a", "key-1"),
        service.activate("issuer-a", "key-2"),
        return_exceptions=True,
    )
    assert sum(not isinstance(item, Exception) for item in results) == 1
    records = await service.registry.list("issuer-a")
    assert sum(item.lifecycle_state is SigningKeyState.ACTIVE for item in records) == 1


@pytest.mark.asyncio
async def test_revocation_between_resolution_and_signing_fails_closed() -> None:
    service, provider = await setup_service()
    await pending(service, provider, "key-1")
    await service.activate("issuer-a", "key-1")
    signer = LifecyclePassportSigner("issuer-a", service)
    selected = await signer.resolve_key_id(NOW)
    await service.transition(
        "issuer-a",
        "key-1",
        SigningKeyState.REVOKED,
        reason=RevocationReason.KEY_COMPROMISE,
    )
    with pytest.raises(KeyLifecycleError, match="active_signer_unavailable"):
        await signer.sign_for_key(b"canonical", selected, NOW)


@pytest.mark.asyncio
async def test_private_public_correspondence_mismatch_fails_activation() -> None:
    class MismatchedProvider:
        def __init__(self) -> None:
            self.declared = Ed25519PrivateKey.generate()
            self.actual = Ed25519PrivateKey.generate()

        async def public_key(self, key_id: str) -> str:
            del key_id
            return b64url_encode(
                self.declared.public_key().public_bytes(
                    serialization.Encoding.Raw, serialization.PublicFormat.Raw
                )
            )

        async def sign(self, key_id: str, payload: bytes) -> str:
            from app.passport.jws import sign_detached

            return sign_detached(payload, self.actual, key_id)

    provider = MismatchedProvider()
    service = KeyLifecycleService(InMemoryKeyMetadataRegistry(), provider, clock=clock)
    await service.register_pending(
        issuer_id="issuer-a",
        key_id="mismatch",
        not_before=NOW,
        not_after=NOW + timedelta(days=1),
    )
    with pytest.raises(KeyLifecycleError, match="private_public_key_mismatch"):
        await service.activate("issuer-a", "mismatch")
    records = await service.registry.list("issuer-a")
    assert records[0].lifecycle_state is SigningKeyState.PENDING


@pytest.mark.asyncio
async def test_key_id_reuse_and_duplicate_registration_fail_closed() -> None:
    service, provider = await setup_service()
    await pending(service, provider, "key-1")
    with pytest.raises(KeyLifecycleError, match="provider_key_id_exists"):
        await provider.create("key-1")
    with pytest.raises(KeyLifecycleError, match="key_id_reuse"):
        await service.register_pending(
            issuer_id="issuer-a",
            key_id="key-1",
            not_before=NOW,
            not_after=NOW + timedelta(days=1),
        )


@pytest.mark.asyncio
async def test_impossible_transitions_and_reactivation_are_rejected() -> None:
    service, provider = await setup_service()
    await pending(service, provider, "key-1")
    await service.activate("issuer-a", "key-1")
    await service.transition("issuer-a", "key-1", SigningKeyState.RETIRED)
    with pytest.raises(KeyLifecycleError, match="transition_not_allowed"):
        await service.transition("issuer-a", "key-1", SigningKeyState.ACTIVE)
    await service.transition(
        "issuer-a", "key-1", SigningKeyState.REVOKED, reason=RevocationReason.KEY_COMPROMISE
    )
    with pytest.raises(KeyLifecycleError, match="transition_not_allowed"):
        await service.transition("issuer-a", "key-1", SigningKeyState.ACTIVE)


@pytest.mark.asyncio
async def test_activation_time_boundaries_and_expiry() -> None:
    service, provider = await setup_service()
    await provider.create("future")
    await service.register_pending(
        issuer_id="issuer-a",
        key_id="future",
        not_before=NOW + timedelta(seconds=1),
        not_after=NOW + timedelta(days=1),
    )
    with pytest.raises(KeyLifecycleError, match="activation_outside"):
        await service.activate("issuer-a", "future")


def test_metadata_rejects_tampering_algorithm_confusion_and_bad_key() -> None:
    key = Ed25519PrivateKey.generate()
    public = b64url_encode(
        key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    )
    record = build_key_metadata(
        metadata_schema_version="vap-key-metadata-1",
        issuer_id="issuer-a",
        key_id="key-1",
        algorithm="EdDSA",
        public_key=public,
        lifecycle_state="PENDING",
        created_at=NOW,
        not_before=NOW,
        not_after=NOW + timedelta(days=1),
        activated_at=None,
        retired_at=None,
        revoked_at=None,
        revocation_reason=None,
        rotation_generation=1,
        predecessor_key_id=None,
        successor_key_id=None,
    )
    changed = record.model_dump(mode="json")
    changed["not_after"] = (NOW + timedelta(days=2)).isoformat()
    with pytest.raises(ValidationError, match="metadata_checksum_mismatch"):
        type(record).model_validate(changed)
    for field, value in (("algorithm", "RS256"), ("public_key", "AA")):
        changed = record.model_dump(mode="json")
        changed[field] = value
        with pytest.raises(ValidationError):
            type(record).model_validate(changed)


@pytest.mark.asyncio
async def test_audit_event_is_bounded_public_metadata_only() -> None:
    events = []

    async def audit(event):
        events.append(event)

    provider = EphemeralSigningProvider()
    service = KeyLifecycleService(
        InMemoryKeyMetadataRegistry(), provider, clock=clock, audit_sink=audit
    )
    await pending(service, provider, "key-1")
    serialized = repr(events)
    assert "private" not in serialized.lower()
    assert "seed" not in serialized.lower()
    assert "answer" not in serialized.lower()


def test_ephemeral_provider_has_no_private_serialization_api() -> None:
    public_names = {name for name in dir(EphemeralSigningProvider()) if not name.startswith("_")}
    assert public_names == {"create", "inject", "public_key", "sign"}
