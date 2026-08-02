from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.passport.canonical import canonicalize, parse_json_strict
from app.passport.hashing import b64url_encode
from app.passport.key_lifecycle import (
    EphemeralSigningProvider,
    InMemoryKeyMetadataRegistry,
    KeyLifecycleService,
)
from app.passport.trust_lifecycle import (
    EphemeralTrustAnchorSigner,
    TrustAnchorState,
    TrustBundleBuilder,
    TrustBundleStatus,
    TrustedBundleState,
    validate_trust_bundle,
)

NOW = datetime(2026, 8, 2, 12, tzinfo=UTC)


async def records():
    provider = EphemeralSigningProvider()
    registry = InMemoryKeyMetadataRegistry()
    service = KeyLifecycleService(registry, provider, clock=lambda: NOW)
    await provider.create("key-1")
    await service.register_pending(
        issuer_id="issuer-a",
        key_id="key-1",
        not_before=NOW - timedelta(days=1),
        not_after=NOW + timedelta(days=30),
    )
    await service.activate("issuer-a", "key-1")
    return await registry.list("issuer-a")


async def built(*, signed: bool = True, version: int = 1, previous: str | None = None):
    anchor = EphemeralTrustAnchorSigner("anchor-1") if signed else None
    artifact = await TrustBundleBuilder(clock=lambda: NOW).build(
        issuer_id="issuer-a",
        records=await records(),
        bundle_version=version,
        next_update=NOW + timedelta(days=1),
        valid_until=NOW + timedelta(days=2),
        previous_bundle_checksum=previous,
        signer=anchor,
    )
    record = (
        anchor.public_record(not_before=NOW - timedelta(days=1), not_after=NOW + timedelta(days=10))
        if anchor
        else None
    )
    return artifact, record


@pytest.mark.asyncio
async def test_signed_bundle_is_deterministic_public_only_and_valid() -> None:
    artifact, anchor = await built()
    assert anchor is not None
    parsed = parse_json_strict(artifact.bundle)
    text = artifact.bundle.decode()
    assert "private" not in text.lower() and "seed" not in text.lower()
    assert [item["key_id"] for item in parsed["keys"]] == ["key-1"]
    result = validate_trust_bundle(
        artifact.bundle, signature_bytes=artifact.signature, anchors=[anchor], at=NOW
    )
    assert result.status is TrustBundleStatus.VALID
    assert result.integrity_valid and result.signature_valid


@pytest.mark.asyncio
async def test_unsigned_bundle_requires_explicit_test_policy() -> None:
    artifact, _ = await built(signed=False)
    denied = validate_trust_bundle(artifact.bundle, at=NOW)
    allowed = validate_trust_bundle(artifact.bundle, at=NOW, allow_unsigned_test_bundle=True)
    assert denied.status is TrustBundleStatus.INDETERMINATE
    assert allowed.status is TrustBundleStatus.VALID_UNSIGNED_TEST_BUNDLE


@pytest.mark.asyncio
async def test_bundle_and_signature_modification_are_rejected_separately() -> None:
    artifact, anchor = await built()
    assert anchor is not None and artifact.signature is not None
    parsed = parse_json_strict(artifact.bundle)
    parsed["bundle_version"] = 2
    modified = canonicalize(parsed)
    assert validate_trust_bundle(modified, at=NOW).status is TrustBundleStatus.CHECKSUM_MISMATCH
    signature = bytearray(artifact.signature)
    signature[-2] = ord("A") if signature[-2] != ord("A") else ord("B")
    result = validate_trust_bundle(
        artifact.bundle, signature_bytes=bytes(signature), anchors=[anchor], at=NOW
    )
    assert result.status is TrustBundleStatus.INVALID_SIGNATURE


@pytest.mark.asyncio
async def test_unknown_revoked_and_expired_anchor_statuses() -> None:
    artifact, anchor = await built()
    assert anchor is not None
    assert (
        validate_trust_bundle(
            artifact.bundle, signature_bytes=artifact.signature, anchors=[], at=NOW
        ).status
        is TrustBundleStatus.UNKNOWN_TRUST_ANCHOR
    )
    revoked = anchor.model_copy(update={"state": TrustAnchorState.REVOKED})
    expired = anchor.model_copy(update={"state": TrustAnchorState.EXPIRED})
    assert (
        validate_trust_bundle(
            artifact.bundle, signature_bytes=artifact.signature, anchors=[revoked], at=NOW
        ).status
        is TrustBundleStatus.INVALID_SIGNATURE
    )
    assert (
        validate_trust_bundle(
            artifact.bundle, signature_bytes=artifact.signature, anchors=[expired], at=NOW
        ).status
        is TrustBundleStatus.EXPIRED
    )


@pytest.mark.asyncio
async def test_freshness_statuses_do_not_corrupt_integrity() -> None:
    artifact, anchor = await built()
    assert anchor is not None
    stale = validate_trust_bundle(
        artifact.bundle,
        signature_bytes=artifact.signature,
        anchors=[anchor],
        at=NOW + timedelta(days=1, seconds=1),
    )
    expired = validate_trust_bundle(
        artifact.bundle,
        signature_bytes=artifact.signature,
        anchors=[anchor],
        at=NOW + timedelta(days=2, seconds=1),
    )
    assert stale.status is TrustBundleStatus.STALE and stale.integrity_valid
    assert expired.status is TrustBundleStatus.EXPIRED and expired.integrity_valid


@pytest.mark.asyncio
async def test_rollback_version_collision_chain_and_issuer_substitution() -> None:
    first, _ = await built(signed=False)
    state = TrustedBundleState(
        issuer_id="issuer-a",
        latest_bundle_version=2,
        latest_bundle_checksum=first.bundle_checksum,
        latest_generated_at=NOW,
        retained_key_ids=frozenset({"key-1"}),
    )
    lower = validate_trust_bundle(first.bundle, at=NOW, trusted_state=state)
    assert lower.status is TrustBundleStatus.VERSION_ROLLBACK
    third, _ = await built(signed=False, version=3, previous=b64url_encode(b"w" * 32))
    broken = validate_trust_bundle(third.bundle, at=NOW, trusted_state=state)
    assert broken.status is TrustBundleStatus.CHAIN_MISMATCH
    parsed = parse_json_strict(third.bundle)
    parsed["issuer_id"] = "issuer-b"
    for key in parsed["keys"]:
        key["issuer_id"] = "issuer-b"
        from app.passport.key_lifecycle import metadata_checksum

        key["metadata_checksum"] = metadata_checksum(key)
    # Rebuilding checksums is an attacker with a valid canonicalizer, not a trust anchor.
    from app.passport.trust_lifecycle import _bundle_checksum

    parsed["bundle_checksum"] = _bundle_checksum(parsed)
    substituted = validate_trust_bundle(canonicalize(parsed), at=NOW, trusted_state=state)
    assert substituted.status is TrustBundleStatus.CHAIN_MISMATCH


@pytest.mark.asyncio
async def test_historical_key_removal_is_rejected() -> None:
    prior = b64url_encode(b"p" * 32)
    artifact, _ = await built(signed=False, version=2, previous=prior)
    state = TrustedBundleState(
        issuer_id="issuer-a",
        latest_bundle_version=1,
        latest_bundle_checksum=prior,
        latest_generated_at=NOW,
        retained_key_ids=frozenset({"key-1", "revoked-old"}),
    )
    result = validate_trust_bundle(artifact.bundle, at=NOW, trusted_state=state)
    assert result.status is TrustBundleStatus.CONFLICTING_KEY_RECORD


@pytest.mark.asyncio
async def test_bundle_output_stable_for_same_inputs_and_clock() -> None:
    key_records = await records()
    builder = TrustBundleBuilder(clock=lambda: NOW)
    kwargs = {
        "issuer_id": "issuer-a",
        "records": key_records,
        "bundle_version": 1,
        "next_update": NOW + timedelta(days=1),
        "valid_until": NOW + timedelta(days=2),
    }
    first = await builder.build(**kwargs)
    second = await builder.build(**kwargs)
    assert first.bundle == second.bundle
    assert first.bundle_checksum == second.bundle_checksum
