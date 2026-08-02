"""Tenant-scoped immutable persistence and controlled VAP export."""

from __future__ import annotations

import hashlib
import io
import re
import zipfile
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from enum import StrEnum
from typing import Protocol
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.db.models.answer_passport import AnswerPassport
from app.passport.canonical import canonicalize, parse_json_strict
from app.passport.hashing import b64url_decode, content_digest
from app.passport.issuance import InternalIssuanceResult, IssuanceStatus, SupportedAnswerProjection
from app.passport.jws import parse_header
from app.passport.schema import PassportManifest, TrustBundle
from app.passport.trust_lifecycle import (
    LifecycleTrustBundle,
    TrustBundleSignature,
    TrustBundleStatus,
    validate_trust_bundle,
)
from app.passport.verifier import verify_passport
from app.repositories.answer_passports import AnswerPassportRepository

MAX_MANIFEST_BYTES = 1_048_576
MAX_SIGNATURE_CHARS = 8_192
MAX_VERIFIER_BUNDLE_BYTES = 1_048_576
MAX_LIFECYCLE_BUNDLE_BYTES = 4_194_304
MAX_LIFECYCLE_SIGNATURE_BYTES = 16_384
MAX_EXPORT_PACKAGE_BYTES = 6_291_456
EXPORT_MEDIA_TYPE = "application/vnd.ekip.answer-passport+zip"
AuditSink = Callable[[dict[str, object]], Awaitable[None]]


class PassportPersistenceStatus(StrEnum):
    PERSISTED = "PERSISTED"
    DUPLICATE = "DUPLICATE"
    NOT_PERSISTED = "NOT_PERSISTED"
    FAILED = "FAILED"


class StoredArtifactError(ValueError):
    pass


class PersistenceResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, arbitrary_types_allowed=True)
    status: PassportPersistenceStatus
    record: AnswerPassport | None = None


class TrustMaterial(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    verifier_bundle: bytes
    lifecycle_bundle: bytes | None = None
    lifecycle_signature: bytes | None = None
    bundle_version: int | None = None
    bundle_checksum: str | None = None
    trust_mode: str = "unsigned-development"


class TrustMaterialProvider(Protocol):
    async def current(self, organization_id: UUID, workspace_id: UUID) -> TrustMaterial: ...


def validate_trust_material(trust: TrustMaterial, *, organization_id: UUID) -> TrustMaterial:
    """Reject oversized, non-canonical, substituted, or inconsistent public trust material."""

    if len(trust.verifier_bundle) > MAX_VERIFIER_BUNDLE_BYTES:
        raise StoredArtifactError("verifier_bundle_size_limit")
    try:
        verifier_data = parse_json_strict(trust.verifier_bundle)
        if canonicalize(verifier_data) != trust.verifier_bundle:
            raise StoredArtifactError("verifier_bundle_not_canonical")
        TrustBundle.model_validate(verifier_data)
    except (ValueError, UnicodeError) as exc:
        raise StoredArtifactError("invalid_verifier_bundle") from exc
    if trust.lifecycle_bundle is None:
        if trust.lifecycle_signature is not None:
            raise StoredArtifactError("orphan_trust_bundle_signature")
        return trust
    if len(trust.lifecycle_bundle) > MAX_LIFECYCLE_BUNDLE_BYTES or (
        trust.lifecycle_signature is not None
        and len(trust.lifecycle_signature) > MAX_LIFECYCLE_SIGNATURE_BYTES
    ):
        raise StoredArtifactError("trust_bundle_size_limit")
    try:
        parsed = parse_json_strict(trust.lifecycle_bundle)
        if canonicalize(parsed) != trust.lifecycle_bundle:
            raise StoredArtifactError("trust_bundle_not_canonical")
        bundle = LifecycleTrustBundle.model_validate(parsed)
        if trust.lifecycle_signature is not None:
            TrustBundleSignature.model_validate(parse_json_strict(trust.lifecycle_signature))
    except (ValueError, UnicodeError) as exc:
        raise StoredArtifactError("invalid_trust_material") from exc
    result = validate_trust_bundle(
        trust.lifecycle_bundle,
        signature_bytes=trust.lifecycle_signature,
        at=bundle.generated_at,
        allow_unsigned_test_bundle=trust.lifecycle_signature is None,
    )
    if result.status not in {
        TrustBundleStatus.VALID,
        TrustBundleStatus.VALID_UNSIGNED_TEST_BUNDLE,
        # The provider boundary supplies the anchor-authenticated material; this layer
        # still verifies canonical schema/checksum/signature shape and issuer binding.
        TrustBundleStatus.UNKNOWN_TRUST_ANCHOR,
    }:
        raise StoredArtifactError("invalid_trust_bundle_integrity")
    if bundle.issuer_id != str(organization_id):
        raise StoredArtifactError("trust_bundle_issuer_mismatch")
    if (
        trust.bundle_version != bundle.bundle_version
        or trust.bundle_checksum != bundle.bundle_checksum
    ):
        raise StoredArtifactError("trust_bundle_metadata_mismatch")
    return trust


def _hex_digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def artifact_checksum(manifest: bytes, signature: str) -> str:
    return _hex_digest(b"VAP3B\0ARTIFACT\0" + manifest + b"\0" + signature.encode("ascii"))


def persistence_idempotency_key(
    *, scope_fingerprint: str, correlation_id: str | None, answer_hash: str, schema_version: str
) -> str:
    material = canonicalize(
        {
            "domain": "VAP3B_PERSISTENCE_V1",
            "scope_fingerprint": scope_fingerprint,
            "correlation_id": correlation_id or "",
            "answer_hash": answer_hash,
            "schema_version": schema_version,
            "policy_version": "passport-persistence-v1",
        }
    )
    return _hex_digest(material)


def validate_issued_artifact(
    issuance: InternalIssuanceResult,
    *,
    organization_id: UUID,
    workspace_id: UUID,
) -> tuple[PassportManifest, str]:
    if issuance.status is not IssuanceStatus.ISSUED:
        raise StoredArtifactError("only_issued_artifacts_may_persist")
    if not issuance.manifest or not issuance.detached_signature or not issuance.passport_id:
        raise StoredArtifactError("incomplete_issued_artifact")
    if (
        len(issuance.manifest) > MAX_MANIFEST_BYTES
        or len(issuance.detached_signature) > MAX_SIGNATURE_CHARS
    ):
        raise StoredArtifactError("artifact_size_limit")
    try:
        parsed = parse_json_strict(issuance.manifest)
        if canonicalize(parsed) != issuance.manifest:
            raise StoredArtifactError("manifest_not_canonical")
        manifest = PassportManifest.model_validate(parsed)
        header = parse_header(issuance.detached_signature)
    except (ValueError, UnicodeError) as exc:
        raise StoredArtifactError("invalid_issued_artifact") from exc
    expected_scope = content_digest(
        "SCOPE",
        canonicalize({"tenant_id": str(organization_id), "workspace_id": str(workspace_id)}),
    )
    if manifest.scope.tenant_workspace_fingerprint != expected_scope:
        raise StoredArtifactError("scope_mismatch")
    if manifest.certificate_id != issuance.passport_id:
        raise StoredArtifactError("passport_id_mismatch")
    if manifest.signing.key_id != issuance.signer_key_id or header["kid"] != issuance.signer_key_id:
        raise StoredArtifactError("signer_key_id_mismatch")
    if re.fullmatch(r"[A-Za-z0-9._:@/-]{1,200}", manifest.signing.key_id) is None:
        raise StoredArtifactError("unsafe_signer_key_id")
    # Parsing the signature bytes enforces canonical Base64URL and the bounded Ed25519 length.
    if len(b64url_decode(issuance.detached_signature.rsplit(".", 1)[1])) != 64:
        raise StoredArtifactError("signature_length")
    return manifest, expected_scope


class PassportPersistenceCoordinator:
    def __init__(
        self,
        repository: AnswerPassportRepository,
        *,
        enabled: bool,
        clock: Callable[[], datetime] | None = None,
        audit_sink: AuditSink | None = None,
    ) -> None:
        self.repository = repository
        self.enabled = enabled
        self.clock = clock or (lambda: datetime.now(UTC))
        self.audit_sink = audit_sink

    async def persist_issued(
        self,
        issuance: InternalIssuanceResult,
        projection: SupportedAnswerProjection,
        *,
        organization_id: UUID,
        workspace_id: UUID,
        actor_id: UUID | None = None,
    ) -> PersistenceResult:
        if not self.enabled or issuance.status is not IssuanceStatus.ISSUED:
            return PersistenceResult(status=PassportPersistenceStatus.NOT_PERSISTED)
        try:
            if not await self.repository.scope_exists(organization_id, workspace_id):
                raise StoredArtifactError("workspace_organization_mismatch")
            manifest, scope = validate_issued_artifact(
                issuance, organization_id=organization_id, workspace_id=workspace_id
            )
            signature = issuance.detached_signature
            manifest_bytes = issuance.manifest
            if manifest_bytes is None or signature is None:
                raise StoredArtifactError("incomplete_issued_artifact")
            checksum = artifact_checksum(manifest_bytes, signature)
            key = persistence_idempotency_key(
                scope_fingerprint=scope,
                correlation_id=projection.correlation_id,
                answer_hash=manifest.answer.sha256,
                schema_version=manifest.schema_version,
            )
            record = AnswerPassport(
                passport_id=manifest.certificate_id,
                organization_id=organization_id,
                workspace_id=workspace_id,
                issuer_id=str(organization_id),
                schema_version=manifest.schema_version,
                envelope_type="application/vap+jws",
                signer_key_id=manifest.signing.key_id,
                manifest_bytes=manifest_bytes,
                detached_signature=signature,
                manifest_sha256=_hex_digest(manifest_bytes),
                signature_sha256=_hex_digest(signature.encode("ascii")),
                artifact_checksum=checksum,
                scope_fingerprint=scope,
                answer_hash=manifest.answer.sha256,
                issued_at=manifest.issued_at,
                expires_at=manifest.freshness.not_after,
                correlation_id=projection.correlation_id,
                idempotency_key=key,
                created_by=actor_id,
                created_at=self.clock(),
                record_version=1,
            )
            stored, created = await self.repository.persist(record)
            await self._audit("PASSPORT_PERSISTED", stored, actor_id, created=created)
            return PersistenceResult(
                status=(
                    PassportPersistenceStatus.PERSISTED
                    if created
                    else PassportPersistenceStatus.DUPLICATE
                ),
                record=stored,
            )
        except Exception:
            await self._audit("PASSPORT_PERSISTENCE_FAILED", None, actor_id)
            return PersistenceResult(status=PassportPersistenceStatus.FAILED)

    async def _audit(
        self, event: str, record: AnswerPassport | None, actor_id: UUID | None, **extra: object
    ) -> None:
        if self.audit_sink is None:
            return
        payload: dict[str, object] = {
            "event_type": event,
            "passport_id": record.passport_id if record else None,
            "workspace_id": str(record.workspace_id) if record else None,
            "organization_id": str(record.organization_id) if record else None,
            "artifact_checksum": record.artifact_checksum if record else None,
            "actor_id": str(actor_id) if actor_id else None,
            **extra,
        }
        try:
            await self.audit_sink(payload)
        except Exception:
            return


def validate_stored_record(record: AnswerPassport) -> PassportManifest:
    try:
        if _hex_digest(record.manifest_bytes) != record.manifest_sha256:
            raise StoredArtifactError("manifest_checksum_mismatch")
        if _hex_digest(record.detached_signature.encode("ascii")) != record.signature_sha256:
            raise StoredArtifactError("signature_checksum_mismatch")
        if (
            artifact_checksum(record.manifest_bytes, record.detached_signature)
            != record.artifact_checksum
        ):
            raise StoredArtifactError("artifact_checksum_mismatch")
        parsed = parse_json_strict(record.manifest_bytes)
        if canonicalize(parsed) != record.manifest_bytes:
            raise StoredArtifactError("manifest_not_canonical")
        manifest = PassportManifest.model_validate(parsed)
        header = parse_header(record.detached_signature)
    except (ValueError, UnicodeError) as exc:
        raise StoredArtifactError("stored_artifact_invalid") from exc
    if (
        manifest.certificate_id != record.passport_id
        or manifest.signing.key_id != record.signer_key_id
    ):
        raise StoredArtifactError("stored_index_mismatch")
    if manifest.scope.tenant_workspace_fingerprint != record.scope_fingerprint:
        raise StoredArtifactError("stored_scope_mismatch")
    if manifest.answer.sha256 != record.answer_hash:
        raise StoredArtifactError("stored_answer_hash_mismatch")

    def normalized(value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value

    if normalized(manifest.issued_at) != normalized(record.issued_at) or normalized(
        manifest.freshness.not_after
    ) != normalized(record.expires_at):
        raise StoredArtifactError("stored_time_mismatch")
    if header["kid"] != record.signer_key_id:
        raise StoredArtifactError("stored_signer_mismatch")
    return manifest


def current_status(
    record: AnswerPassport,
    manifest: PassportManifest,
    *,
    now: datetime,
    trust: TrustMaterial | None,
) -> tuple[str, str, str]:
    freshness = "CURRENT"
    expires_at = record.expires_at
    if expires_at is not None and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    if expires_at is not None and now > expires_at:
        freshness = "EXPIRED"
    if trust is None:
        return "TRUST_UNAVAILABLE", freshness, "UNKNOWN"
    result = verify_passport(
        record.manifest_bytes, record.detached_signature, trust.verifier_bundle, at=now
    )
    if not result.signature_valid:
        return "ARTIFACT_INVALID", freshness, "UNKNOWN"
    if result.status == "REVOKED":
        return "KEY_REVOKED", freshness, "REVOKED"
    if result.overall == "invalid":
        return "ARTIFACT_INVALID", freshness, "UNKNOWN"
    key_state = "RETIRED" if result.key_status == "retired" else "ACTIVE"
    if freshness == "EXPIRED":
        return "EXPIRED", freshness, key_state
    if key_state == "RETIRED":
        return "KEY_RETIRED", freshness, key_state
    return "VERIFIED", freshness, key_state


def build_export_package(
    record: AnswerPassport,
    *,
    now: datetime,
    status: str,
    freshness: str,
    key_status: str,
    trust: TrustMaterial | None,
) -> bytes:
    files: dict[str, bytes] = {
        "passport.json": record.manifest_bytes,
        "passport.sig": record.detached_signature.encode("ascii"),
    }
    if trust is not None and trust.lifecycle_bundle is not None:
        files["trust-bundle.json"] = trust.lifecycle_bundle
    export_manifest = {
        "schema_version": "vap-export-1",
        "passport_id": record.passport_id,
        "exported_at": now.astimezone(UTC).isoformat().replace("+00:00", "Z"),
        "status": status,
        "freshness": freshness,
        "key_lifecycle_status": key_status,
        "files": [
            {"filename": name, "sha256": _hex_digest(content), "size_bytes": len(content)}
            for name, content in sorted(files.items())
        ],
        "trust_bundle_included": "trust-bundle.json" in files,
        "trust_bootstrap_notice": (
            "Trust-anchor authenticity requires an independently trusted channel."
        ),
    }
    files["export-manifest.json"] = canonicalize(export_manifest)
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_STORED) as archive:
        for name, content in sorted(files.items()):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.external_attr = 0o100600 << 16
            archive.writestr(info, content)
    package = output.getvalue()
    if len(package) > MAX_EXPORT_PACKAGE_BYTES:
        raise StoredArtifactError("export_package_size_limit")
    return package


def safe_download_name(passport_id: str) -> str:
    value = passport_id.removeprefix("urn:uuid:")
    if re.fullmatch(r"[0-9a-fA-F-]{36}", value) is None:
        raise StoredArtifactError("invalid_passport_id")
    return f"answer-passport-{value.lower()}.zip"
