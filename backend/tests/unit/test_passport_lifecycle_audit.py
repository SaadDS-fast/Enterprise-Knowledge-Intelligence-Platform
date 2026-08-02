from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from app.passport.canonical import canonicalize, parse_json_strict
from app.passport.hashing import b64url_encode
from app.passport.jws import parse_header
from app.passport.key_lifecycle import (
    EphemeralSigningProvider,
    InMemoryKeyMetadataRegistry,
    KeyLifecycleError,
    KeyLifecycleService,
    LifecycleAuditEvent,
    LifecycleEventType,
    LifecyclePassportSigner,
    RevocationReason,
    SigningKeyState,
)
from app.passport.trust_lifecycle import (
    InMemoryTrustBundleSeries,
    TrustBundleBuilder,
    TrustBundleStatus,
    TrustedBundleState,
    _bundle_checksum,
    validate_trust_bundle,
)

NOW = datetime(2026, 8, 2, 12, tzinfo=UTC)


async def active_service(
    *, provider: EphemeralSigningProvider | None = None
) -> tuple[KeyLifecycleService, EphemeralSigningProvider, InMemoryKeyMetadataRegistry]:
    signer = provider or EphemeralSigningProvider()
    registry = InMemoryKeyMetadataRegistry()
    service = KeyLifecycleService(registry, signer, clock=lambda: NOW)
    await signer.create("key-1")
    await service.register_pending(
        issuer_id="issuer-a",
        key_id="key-1",
        not_before=NOW - timedelta(days=1),
        not_after=NOW + timedelta(days=30),
    )
    await service.activate("issuer-a", "key-1")
    return service, signer, registry


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("initial", "target"),
    [
        (SigningKeyState.PENDING, SigningKeyState.RETIRED),
        (SigningKeyState.ACTIVE, SigningKeyState.PENDING),
        (SigningKeyState.ACTIVE, SigningKeyState.ACTIVE),
        (SigningKeyState.RETIRED, SigningKeyState.ACTIVE),
        (SigningKeyState.RETIRED, SigningKeyState.PENDING),
        (SigningKeyState.RETIRED, SigningKeyState.RETIRED),
        (SigningKeyState.REVOKED, SigningKeyState.PENDING),
        (SigningKeyState.REVOKED, SigningKeyState.ACTIVE),
        (SigningKeyState.REVOKED, SigningKeyState.RETIRED),
        (SigningKeyState.REVOKED, SigningKeyState.REVOKED),
    ],
)
async def test_complete_rejected_transition_matrix(
    initial: SigningKeyState, target: SigningKeyState
) -> None:
    provider = EphemeralSigningProvider()
    registry = InMemoryKeyMetadataRegistry()
    service = KeyLifecycleService(registry, provider, clock=lambda: NOW)
    await provider.create("key-1")
    await service.register_pending(
        issuer_id="issuer-a", key_id="key-1", not_before=NOW, not_after=NOW + timedelta(days=2)
    )
    if initial is not SigningKeyState.PENDING:
        await service.activate("issuer-a", "key-1")
    if initial in {SigningKeyState.RETIRED, SigningKeyState.REVOKED}:
        await service.transition("issuer-a", "key-1", SigningKeyState.RETIRED)
    if initial is SigningKeyState.REVOKED:
        await service.transition(
            "issuer-a", "key-1", SigningKeyState.REVOKED, reason=RevocationReason.UNSPECIFIED
        )
    with pytest.raises(KeyLifecycleError, match="transition_not_allowed"):
        await service.transition("issuer-a", "key-1", target)


@pytest.mark.asyncio
async def test_revocation_chronology_and_reason_are_strict() -> None:
    current = NOW
    provider = EphemeralSigningProvider()
    registry = InMemoryKeyMetadataRegistry()
    service = KeyLifecycleService(registry, provider, clock=lambda: current)
    await provider.create("key-1")
    await service.register_pending(
        issuer_id="issuer-a", key_id="key-1", not_before=NOW, not_after=NOW + timedelta(days=1)
    )
    await service.activate("issuer-a", "key-1")
    current = NOW - timedelta(seconds=1)
    with pytest.raises(ValidationError, match="revocation_precedes_(creation|activation)"):
        await service.transition(
            "issuer-a", "key-1", SigningKeyState.REVOKED, reason=RevocationReason.UNSPECIFIED
        )
    current = NOW
    with pytest.raises(KeyLifecycleError, match="revocation_reason_required"):
        await service.transition("issuer-a", "key-1", SigningKeyState.REVOKED)


@pytest.mark.asyncio
@pytest.mark.parametrize("target", [SigningKeyState.RETIRED, SigningKeyState.REVOKED])
async def test_sign_and_terminal_transition_are_registry_linearized(
    target: SigningKeyState,
) -> None:
    class BlockingProvider(EphemeralSigningProvider):
        def __init__(self) -> None:
            super().__init__()
            self.started = asyncio.Event()
            self.release = asyncio.Event()

        async def sign(self, key_id: str, payload: bytes) -> str:
            if payload == b"passport":
                self.started.set()
                await self.release.wait()
            return await super().sign(key_id, payload)

    provider = BlockingProvider()
    service, _, registry = await active_service(provider=provider)
    signer = LifecyclePassportSigner("issuer-a", service)
    sign_task = asyncio.create_task(signer.sign_for_key(b"passport", "key-1", NOW))
    await provider.started.wait()
    transition_task = asyncio.create_task(
        service.transition(
            "issuer-a",
            "key-1",
            target,
            reason=RevocationReason.KEY_COMPROMISE if target is SigningKeyState.REVOKED else None,
        )
    )
    await asyncio.sleep(0)
    assert not transition_task.done()
    provider.release.set()
    assert await sign_task
    assert (await transition_task).lifecycle_state is target
    assert (await registry.list("issuer-a"))[0].lifecycle_state is target


@pytest.mark.asyncio
async def test_sign_and_rotation_are_registry_linearized_without_key_switch() -> None:
    class BlockingProvider(EphemeralSigningProvider):
        def __init__(self) -> None:
            super().__init__()
            self.started = asyncio.Event()
            self.release = asyncio.Event()

        async def sign(self, key_id: str, payload: bytes) -> str:
            if payload == b"passport":
                self.started.set()
                await self.release.wait()
            return await super().sign(key_id, payload)

    provider = BlockingProvider()
    service, _, registry = await active_service(provider=provider)
    await provider.create("key-2")
    signer = LifecyclePassportSigner("issuer-a", service)
    sign_task = asyncio.create_task(signer.sign_for_key(b"passport", "key-1", NOW))
    await provider.started.wait()
    rotation = asyncio.create_task(
        service.rotate(
            issuer_id="issuer-a",
            key_id="key-2",
            not_before=NOW,
            not_after=NOW + timedelta(days=60),
        )
    )
    await asyncio.sleep(0)
    provider.release.set()
    signature = await sign_task
    assert parse_header(signature)["kid"] == "key-1"
    assert (await rotation).key_id == "key-2"
    records = await registry.list("issuer-a")
    assert sum(item.lifecycle_state is SigningKeyState.ACTIVE for item in records) == 1


@pytest.mark.asyncio
async def test_activation_loses_deterministically_to_pending_revocation() -> None:
    class GateProvider(EphemeralSigningProvider):
        def __init__(self) -> None:
            super().__init__()
            self.validation_started = asyncio.Event()
            self.release = asyncio.Event()

        async def sign(self, key_id: str, payload: bytes) -> str:
            self.validation_started.set()
            await self.release.wait()
            return await super().sign(key_id, payload)

    provider = GateProvider()
    registry = InMemoryKeyMetadataRegistry()
    service = KeyLifecycleService(registry, provider, clock=lambda: NOW)
    await provider.create("key-1")
    await service.register_pending(
        issuer_id="issuer-a", key_id="key-1", not_before=NOW, not_after=NOW + timedelta(days=1)
    )
    activation = asyncio.create_task(service.activate("issuer-a", "key-1"))
    await provider.validation_started.wait()
    revoked = await service.transition(
        "issuer-a", "key-1", SigningKeyState.REVOKED, reason=RevocationReason.UNSPECIFIED
    )
    provider.release.set()
    assert revoked.lifecycle_state is SigningKeyState.REVOKED
    with pytest.raises(KeyLifecycleError, match="transition_not_allowed"):
        await activation


@pytest.mark.asyncio
async def test_cancellation_after_validation_leaves_only_pending_state() -> None:
    class NotifyingProvider(EphemeralSigningProvider):
        def __init__(self) -> None:
            super().__init__()
            self.validated = asyncio.Event()

        async def sign(self, key_id: str, payload: bytes) -> str:
            result = await super().sign(key_id, payload)
            self.validated.set()
            return result

    provider = NotifyingProvider()
    registry = InMemoryKeyMetadataRegistry()
    service = KeyLifecycleService(registry, provider, clock=lambda: NOW)
    await provider.create("key-1")
    await service.register_pending(
        issuer_id="issuer-a", key_id="key-1", not_before=NOW, not_after=NOW + timedelta(days=1)
    )
    activation = asyncio.create_task(service.activate("issuer-a", "key-1"))
    await provider.validated.wait()
    activation.cancel()
    with pytest.raises(asyncio.CancelledError):
        await activation
    assert (await registry.list("issuer-a"))[0].lifecycle_state is SigningKeyState.PENDING


@pytest.mark.asyncio
async def test_rotation_failure_preserves_old_active_and_pending_successor() -> None:
    class FailingProvider(EphemeralSigningProvider):
        async def sign(self, key_id: str, payload: bytes) -> str:
            if key_id == "key-2":
                raise RuntimeError("provider_failure")
            return await super().sign(key_id, payload)

    provider = FailingProvider()
    service, _, registry = await active_service(provider=provider)
    await provider.create("key-2")
    with pytest.raises(RuntimeError, match="provider_failure"):
        await service.rotate(
            issuer_id="issuer-a",
            key_id="key-2",
            not_before=NOW,
            not_after=NOW + timedelta(days=30),
        )
    records = await registry.list("issuer-a")
    assert (
        next(item for item in records if item.key_id == "key-1").lifecycle_state
        is SigningKeyState.ACTIVE
    )
    assert (
        next(item for item in records if item.key_id == "key-2").lifecycle_state
        is SigningKeyState.PENDING
    )


@pytest.mark.asyncio
async def test_bundle_series_advances_with_lifecycle_revision_and_chains() -> None:
    service, provider, registry = await active_service()
    series = InMemoryTrustBundleSeries(registry, TrustBundleBuilder(clock=lambda: NOW))
    first = await series.build(
        issuer_id="issuer-a",
        next_update=NOW + timedelta(days=1),
        valid_until=NOW + timedelta(days=2),
    )
    await provider.create("key-2")
    await service.rotate(
        issuer_id="issuer-a",
        key_id="key-2",
        not_before=NOW,
        not_after=NOW + timedelta(days=60),
    )
    second = await series.build(
        issuer_id="issuer-a",
        next_update=NOW + timedelta(days=1),
        valid_until=NOW + timedelta(days=2),
    )
    parsed = parse_json_strict(second.bundle)
    assert second.bundle_version > first.bundle_version
    assert parsed["previous_bundle_checksum"] == first.bundle_checksum
    assert {item["key_id"] for item in parsed["keys"]} == {"key-1", "key-2"}


@pytest.mark.asyncio
async def test_compound_trust_failure_precedence() -> None:
    service, _, registry = await active_service()
    artifact = await TrustBundleBuilder(clock=lambda: NOW).build(
        issuer_id="issuer-a",
        records=await registry.list("issuer-a"),
        bundle_version=2,
        next_update=NOW + timedelta(seconds=1),
        valid_until=NOW + timedelta(seconds=2),
    )
    parsed = parse_json_strict(artifact.bundle)
    parsed["next_update"] = "2026-08-01T00:00:00Z"
    assert (
        validate_trust_bundle(canonicalize(parsed), at=NOW + timedelta(days=3)).status
        is TrustBundleStatus.CHECKSUM_MISMATCH
    )
    state = TrustedBundleState(
        issuer_id="issuer-a",
        latest_bundle_version=3,
        latest_bundle_checksum=b64url_encode(b"n" * 32),
        latest_generated_at=NOW,
        retained_key_ids=frozenset({"key-1"}),
    )
    assert (
        validate_trust_bundle(
            artifact.bundle, at=NOW + timedelta(days=3), trusted_state=state
        ).status
        is TrustBundleStatus.VERSION_ROLLBACK
    )


def test_audit_event_rejects_log_forging_and_unsafe_payload_fields() -> None:
    base = {
        "event_type": LifecycleEventType.KEY_REVOKED,
        "event_id": "event-1",
        "issuer_id": "issuer-a",
        "timestamp": NOW,
        "key_id": "key-1",
        "lifecycle_state": SigningKeyState.REVOKED,
        "reason_code": RevocationReason.KEY_COMPROMISE,
    }
    for field in ("event_id", "issuer_id", "key_id", "actor_id", "correlation_id"):
        with pytest.raises(ValidationError):
            LifecycleAuditEvent.model_validate({**base, field: "safe\naccess_token=secret"})
    for unsafe in ("private_key", "seed", "answer_text", "evidence_text", "passport"):
        with pytest.raises(ValidationError):
            LifecycleAuditEvent.model_validate({**base, unsafe: "prohibited"})
    with pytest.raises(ValidationError, match="checksum_must_be_sha256"):
        LifecycleAuditEvent.model_validate({**base, "checksum": "unsafe\nchecksum"})


@pytest.mark.asyncio
async def test_unsafe_audit_actor_is_rejected_before_registry_commit() -> None:
    provider = EphemeralSigningProvider()
    registry = InMemoryKeyMetadataRegistry()
    service = KeyLifecycleService(registry, provider, clock=lambda: NOW)
    await provider.create("key-1")
    with pytest.raises(KeyLifecycleError, match="unsafe_actor_id"):
        await service.register_pending(
            issuer_id="issuer-a",
            key_id="key-1",
            not_before=NOW,
            not_after=NOW + timedelta(days=1),
            actor_id="operator\nforged=true",
        )
    assert await registry.list("issuer-a") == ()


@pytest.mark.asyncio
async def test_trusted_state_same_version_replay_and_fork_policy() -> None:
    _, _, registry = await active_service()
    artifact = await TrustBundleBuilder(clock=lambda: NOW).build(
        issuer_id="issuer-a",
        records=await registry.list("issuer-a"),
        bundle_version=2,
        next_update=NOW + timedelta(days=1),
        valid_until=NOW + timedelta(days=2),
    )
    state = TrustedBundleState(
        issuer_id="issuer-a",
        latest_bundle_version=2,
        latest_bundle_checksum=artifact.bundle_checksum,
        latest_generated_at=NOW,
        retained_key_ids=frozenset({"key-1"}),
    )
    replay = validate_trust_bundle(
        artifact.bundle, at=NOW, trusted_state=state, allow_unsigned_test_bundle=True
    )
    assert replay.status is TrustBundleStatus.VALID_UNSIGNED_TEST_BUNDLE
    parsed = parse_json_strict(artifact.bundle)
    parsed["generated_at"] = "2026-08-02T12:00:01Z"
    parsed["bundle_checksum"] = _bundle_checksum(parsed)
    fork = validate_trust_bundle(
        canonicalize(parsed), at=NOW, trusted_state=state, allow_unsigned_test_bundle=True
    )
    assert fork.status is TrustBundleStatus.VERSION_ROLLBACK
