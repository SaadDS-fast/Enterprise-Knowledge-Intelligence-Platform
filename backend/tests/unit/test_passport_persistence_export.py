from __future__ import annotations

import io
import zipfile
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from app.db.models.answer_passport import AnswerPassport
from app.passport.canonical import canonicalize, parse_json_strict
from app.passport.hashing import b64url_encode
from app.passport.issuance import (
    ANSWER_NORMALIZATION_VERSION,
    CLAIM_VERIFIER_VERSION,
    EXPORT_POLICY_ID,
    SUPPORT_GATE_VERSION,
    InternalIssuanceResult,
    IssuanceContext,
    IssuanceStatus,
    PassportIssuanceCoordinator,
    ProjectedCitation,
    ProjectedClaim,
    SupportedAnswerProjection,
)
from app.passport.jws import sign_detached
from app.passport.persistence import (
    PassportPersistenceCoordinator,
    PassportPersistenceStatus,
    StoredArtifactError,
    TrustMaterial,
    artifact_checksum,
    build_export_package,
    current_status,
    persistence_idempotency_key,
    safe_download_name,
    validate_stored_record,
    validate_trust_material,
)
from app.repositories.answer_passports import PassportPersistenceCollision

NOW = datetime(2026, 8, 2, 12, tzinfo=UTC)


class Signer:
    key_id = "phase3b-test-key"

    def __init__(self) -> None:
        self.private = Ed25519PrivateKey.generate()

    async def sign(self, payload: bytes) -> str:
        return sign_detached(payload, self.private, self.key_id)


class MemoryRepository:
    def __init__(self, organization_id: UUID, workspace_id: UUID) -> None:
        self.organization_id = organization_id
        self.workspace_id = workspace_id
        self.by_key: dict[str, AnswerPassport] = {}
        self.by_id: dict[str, AnswerPassport] = {}

    async def scope_exists(self, organization_id: UUID, workspace_id: UUID) -> bool:
        return organization_id == self.organization_id and workspace_id == self.workspace_id

    async def persist(self, record: AnswerPassport) -> tuple[AnswerPassport, bool]:
        existing = self.by_key.get(record.idempotency_key)
        if existing:
            if existing.artifact_checksum != record.artifact_checksum:
                raise PassportPersistenceCollision("collision")
            return existing, False
        if record.passport_id in self.by_id:
            raise PassportPersistenceCollision("duplicate_passport")
        self.by_key[record.idempotency_key] = record
        self.by_id[record.passport_id] = record
        return record, True

    async def get_scoped(
        self, passport_id: str, organization_id: UUID, workspace_id: UUID
    ) -> AnswerPassport | None:
        if not await self.scope_exists(organization_id, workspace_id):
            return None
        return self.by_id.get(passport_id)


def projection(
    organization_id: UUID, workspace_id: UUID, **updates: object
) -> SupportedAnswerProjection:
    values: dict[str, object] = {
        "decision": "supported",
        "support_decision_final": True,
        "answer": b"Private answer text is not stored directly.",
        "answer_media_type": "text/plain; charset=utf-8",
        "answer_normalization_version": ANSWER_NORMALIZATION_VERSION,
        "claims": (
            ProjectedClaim(
                claim_id="claim-1",
                normalized_text="Private answer text is not stored directly.",
                verified=True,
                citations=(
                    ProjectedCitation(
                        citation_id="citation-1",
                        evidence_id="evidence-1",
                        evidence_span=b"CONFIDENTIAL_EVIDENCE_TEXT",
                        document_id="document-1",
                        document_version="1",
                        document_checksum="a" * 64,
                        applicability_policy_id=EXPORT_POLICY_ID,
                    ),
                ),
            ),
        ),
        "tenant_id": str(organization_id),
        "workspace_id": str(workspace_id),
        "audience_policy_id": EXPORT_POLICY_ID,
        "export_policy_id": EXPORT_POLICY_ID,
        "support_gate_version": SUPPORT_GATE_VERSION,
        "claim_verifier_version": CLAIM_VERIFIER_VERSION,
        "retrieval_configuration": canonicalize({"top_k": 20, "retry_budget": 0}),
        "generation_provider_alias": "extractive",
        "completed_at": NOW,
        "correlation_id": "request-safe-1",
    }
    values.update(updates)
    return SupportedAnswerProjection.model_validate(values)


async def issued(
    organization_id: UUID, workspace_id: UUID, *, signer: Signer | None = None
) -> tuple[InternalIssuanceResult, SupportedAnswerProjection]:
    projected = projection(organization_id, workspace_id)
    result = await PassportIssuanceCoordinator(
        enabled=True, signer=signer or Signer(), clock=lambda: NOW, identifier=uuid4
    ).issue(projected, context=IssuanceContext())
    assert result.status is IssuanceStatus.ISSUED
    return result, projected


@pytest.mark.asyncio
async def test_successful_persistence_is_minimal_immutable_and_idempotent() -> None:
    organization_id, workspace_id = uuid4(), uuid4()
    repository = MemoryRepository(organization_id, workspace_id)
    issuance, projected = await issued(organization_id, workspace_id)
    service = PassportPersistenceCoordinator(repository, enabled=True, clock=lambda: NOW)
    first = await service.persist_issued(
        issuance, projected, organization_id=organization_id, workspace_id=workspace_id
    )
    second = await service.persist_issued(
        issuance, projected, organization_id=organization_id, workspace_id=workspace_id
    )
    assert first.status is PassportPersistenceStatus.PERSISTED
    assert second.status is PassportPersistenceStatus.DUPLICATE
    assert first.record is second.record
    record = first.record
    assert record is not None and record.record_version == 1
    serialized = repr(record.__dict__)
    assert "CONFIDENTIAL_EVIDENCE_TEXT" not in serialized
    assert "Private answer text" not in serialized


@pytest.mark.asyncio
async def test_nonissued_disabled_and_wrong_scope_never_persist() -> None:
    organization_id, workspace_id = uuid4(), uuid4()
    repository = MemoryRepository(organization_id, workspace_id)
    issuance, projected = await issued(organization_id, workspace_id)
    disabled = await PassportPersistenceCoordinator(repository, enabled=False).persist_issued(
        issuance, projected, organization_id=organization_id, workspace_id=workspace_id
    )
    rejected = await PassportPersistenceCoordinator(repository, enabled=True).persist_issued(
        InternalIssuanceResult(status=IssuanceStatus.INELIGIBLE),
        projected,
        organization_id=organization_id,
        workspace_id=workspace_id,
    )
    mismatched = await PassportPersistenceCoordinator(repository, enabled=True).persist_issued(
        issuance, projected, organization_id=organization_id, workspace_id=uuid4()
    )
    assert disabled.status is rejected.status is PassportPersistenceStatus.NOT_PERSISTED
    assert mismatched.status is PassportPersistenceStatus.FAILED
    assert not repository.by_id


@pytest.mark.asyncio
async def test_idempotency_collision_fails_closed_and_cross_tenant_key_differs() -> None:
    organization_id, workspace_id = uuid4(), uuid4()
    repository = MemoryRepository(organization_id, workspace_id)
    issuance, projected = await issued(organization_id, workspace_id)
    service = PassportPersistenceCoordinator(repository, enabled=True, clock=lambda: NOW)
    stored = await service.persist_issued(
        issuance, projected, organization_id=organization_id, workspace_id=workspace_id
    )
    assert stored.record is not None
    stored.record.artifact_checksum = "f" * 64  # simulate a conflicting durable row
    collision = await service.persist_issued(
        issuance, projected, organization_id=organization_id, workspace_id=workspace_id
    )
    assert collision.status is PassportPersistenceStatus.FAILED
    first = persistence_idempotency_key(
        scope_fingerprint="A" * 43,
        correlation_id="same",
        answer_hash="B" * 43,
        schema_version="vap-1",
    )
    second = persistence_idempotency_key(
        scope_fingerprint="C" * 43,
        correlation_id="same",
        answer_hash="B" * 43,
        schema_version="vap-1",
    )
    assert first != second


@pytest.mark.asyncio
async def test_concurrent_duplicate_creates_one_record() -> None:
    import asyncio

    organization_id, workspace_id = uuid4(), uuid4()
    repository = MemoryRepository(organization_id, workspace_id)
    issuance, projected = await issued(organization_id, workspace_id)
    service = PassportPersistenceCoordinator(repository, enabled=True, clock=lambda: NOW)
    results = await asyncio.gather(
        *(
            service.persist_issued(
                issuance, projected, organization_id=organization_id, workspace_id=workspace_id
            )
            for _ in range(8)
        )
    )
    assert len(repository.by_id) == 1
    assert sum(item.status is PassportPersistenceStatus.PERSISTED for item in results) == 1


@pytest.mark.asyncio
async def test_stored_integrity_checks_every_bound_index() -> None:
    organization_id, workspace_id = uuid4(), uuid4()
    repository = MemoryRepository(organization_id, workspace_id)
    issuance, projected = await issued(organization_id, workspace_id)
    result = await PassportPersistenceCoordinator(
        repository, enabled=True, clock=lambda: NOW
    ).persist_issued(
        issuance, projected, organization_id=organization_id, workspace_id=workspace_id
    )
    assert result.record is not None
    validate_stored_record(result.record)
    fields = (
        ("manifest_sha256", "0" * 64),
        ("signature_sha256", "0" * 64),
        ("artifact_checksum", "0" * 64),
        ("passport_id", "urn:uuid:00000000-0000-0000-0000-000000000008"),
        ("signer_key_id", "substituted"),
        ("scope_fingerprint", "A" * 43),
        ("answer_hash", "B" * 43),
        ("issued_at", NOW + timedelta(seconds=1)),
        ("expires_at", NOW + timedelta(days=31)),
    )
    for field, modified in fields:
        original = getattr(result.record, field)
        setattr(result.record, field, modified)
        with pytest.raises(StoredArtifactError):
            validate_stored_record(result.record)
        setattr(result.record, field, original)


@pytest.mark.asyncio
async def test_export_has_fixed_safe_files_checksums_and_no_evidence() -> None:
    organization_id, workspace_id = uuid4(), uuid4()
    repository = MemoryRepository(organization_id, workspace_id)
    issuance, projected = await issued(organization_id, workspace_id)
    result = await PassportPersistenceCoordinator(
        repository, enabled=True, clock=lambda: NOW
    ).persist_issued(
        issuance, projected, organization_id=organization_id, workspace_id=workspace_id
    )
    assert result.record is not None
    manifest = validate_stored_record(result.record)
    status, freshness, key_status = current_status(result.record, manifest, now=NOW, trust=None)
    package = build_export_package(
        result.record,
        now=NOW,
        status=status,
        freshness=freshness,
        key_status=key_status,
        trust=None,
    )
    assert b"CONFIDENTIAL_EVIDENCE_TEXT" not in package
    assert b"Private answer text" not in package
    with zipfile.ZipFile(io.BytesIO(package)) as archive:
        assert archive.namelist() == ["export-manifest.json", "passport.json", "passport.sig"]
        assert all(
            ".." not in name and name.startswith(("export-", "passport."))
            for name in archive.namelist()
        )
        exported = parse_json_strict(archive.read("export-manifest.json"))
        assert exported["trust_bundle_included"] is False
        assert all(item["sha256"] for item in exported["files"])


def test_safe_filename_and_artifact_checksum_are_bounded() -> None:
    assert safe_download_name("urn:uuid:00000000-0000-0000-0000-000000000007") == (
        "answer-passport-00000000-0000-0000-0000-000000000007.zip"
    )
    with pytest.raises(StoredArtifactError):
        safe_download_name("urn:uuid:x\r\nContent-Disposition: bad")
    assert artifact_checksum(b"a", "b") != artifact_checksum(b"ab", "")


def test_oversized_trust_material_is_rejected_before_packaging() -> None:
    with pytest.raises(StoredArtifactError, match="verifier_bundle_size_limit"):
        validate_trust_material(
            TrustMaterial(verifier_bundle=b"x" * 1_048_577), organization_id=uuid4()
        )


@pytest.mark.asyncio
async def test_compound_status_precedence_is_integrity_revocation_then_freshness() -> None:
    organization_id, workspace_id = uuid4(), uuid4()
    repository = MemoryRepository(organization_id, workspace_id)
    signer = Signer()
    issuance, projected = await issued(organization_id, workspace_id, signer=signer)
    result = await PassportPersistenceCoordinator(
        repository, enabled=True, clock=lambda: NOW
    ).persist_issued(
        issuance, projected, organization_id=organization_id, workspace_id=workspace_id
    )
    assert result.record is not None
    manifest = validate_stored_record(result.record)
    public_key = b64url_encode(
        signer.private.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
    )

    def trust(status: str) -> TrustMaterial:
        return TrustMaterial(
            verifier_bundle=canonicalize(
                {
                    "schema_version": "vap-trust-1",
                    "generated_at": NOW.isoformat().replace("+00:00", "Z"),
                    "keys": [
                        {
                            "key_id": signer.key_id,
                            "algorithm": "EdDSA",
                            "public_key": public_key,
                            "status": status,
                            "not_before": (NOW - timedelta(days=1))
                            .isoformat()
                            .replace("+00:00", "Z"),
                            "not_after": (NOW + timedelta(days=365))
                            .isoformat()
                            .replace("+00:00", "Z"),
                            "retired_at": (NOW + timedelta(days=1))
                            .isoformat()
                            .replace("+00:00", "Z")
                            if status == "retired"
                            else None,
                            "revoked_at": (NOW + timedelta(days=1))
                            .isoformat()
                            .replace("+00:00", "Z")
                            if status == "revoked"
                            else None,
                        }
                    ],
                }
            )
        )

    expired_at = NOW + timedelta(days=31)
    assert current_status(result.record, manifest, now=expired_at, trust=trust("revoked"))[0] == (
        "KEY_REVOKED"
    )
    assert current_status(result.record, manifest, now=expired_at, trust=trust("retired"))[0] == (
        "EXPIRED"
    )
    original_signature = result.record.detached_signature
    replacement = "A" if original_signature[-1] != "A" else "B"
    result.record.detached_signature = f"{original_signature[:-1]}{replacement}"
    assert current_status(result.record, manifest, now=expired_at, trust=trust("revoked"))[0] == (
        "ARTIFACT_INVALID"
    )
