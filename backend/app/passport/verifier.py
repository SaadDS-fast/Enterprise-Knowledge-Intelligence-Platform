"""Deterministic, network-free verification for VAP-1 artifacts."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from pydantic import BaseModel, ConfigDict, Field

from app.passport.canonical import CanonicalizationError, canonicalize, parse_json_strict
from app.passport.hashing import b64url_decode, content_digest
from app.passport.jws import JWSError, parse_header, verify_detached
from app.passport.schema import EvidenceSnapshot, PassportManifest, TrustBundle

MAX_MANIFEST_BYTES = 2 * 1024 * 1024
MAX_SIGNATURE_BYTES = 16 * 1024
MAX_TRUST_BUNDLE_BYTES = 2 * 1024 * 1024
MAX_SNAPSHOT_BYTES = 32 * 1024 * 1024


class VerificationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_valid: bool = False
    canonical_manifest: bool = False
    signature_valid: bool = False
    status: Literal[
        "VERIFIED",
        "VERIFIED_WITHOUT_SNAPSHOT",
        "EXPIRED",
        "STALE",
        "REVOKED",
        "INVALID_SIGNATURE",
        "CONTENT_MODIFIED",
        "SNAPSHOT_MISMATCH",
        "UNKNOWN_KEY",
        "INVALID_SCHEMA",
        "UNSUPPORTED_ALGORITHM",
        "INDETERMINATE",
    ] = "INDETERMINATE"
    key_status: Literal["trusted", "retired", "revoked", "expired", "not_yet_valid", "unknown"] = (
        "unknown"
    )
    historical_key_validity: Literal["valid", "outside_interval", "not_evaluated"] = "not_evaluated"
    content_integrity: Literal["valid", "invalid", "not_supplied"] = "not_supplied"
    snapshot_integrity: Literal["valid", "invalid", "not_supplied"] = "not_supplied"
    scope_match: Literal["valid", "invalid", "not_evaluated"] = "not_evaluated"
    configuration_match: Literal["valid", "invalid", "not_evaluated"] = "not_evaluated"
    freshness: Literal["fresh", "expired", "unknown"] = "unknown"
    overall: Literal["valid", "invalid", "valid_review_required"] = "invalid"
    certificate_id: str | None = None
    key_id: str | None = None
    trust_bundle_generated_at: datetime | None = None
    errors: list[str] = Field(default_factory=list)


def _invalid(error: str, **updates: object) -> VerificationResult:
    return VerificationResult(errors=[error], **updates)


def verify_passport(
    manifest_bytes: bytes,
    detached_jws: str,
    trust_bundle_bytes: bytes,
    *,
    answer_bytes: bytes | None = None,
    snapshot_bytes: bytes | None = None,
    at: datetime | None = None,
    expected_scope_fingerprint: str | None = None,
    expected_configuration_digest: str | None = None,
) -> VerificationResult:
    """Verify a passport without retrieval, generation, persistence, or network access."""

    if len(manifest_bytes) > MAX_MANIFEST_BYTES:
        return _invalid("manifest_too_large")
    if len(detached_jws.encode("ascii", errors="ignore")) > MAX_SIGNATURE_BYTES:
        return _invalid("signature_too_large")
    if len(trust_bundle_bytes) > MAX_TRUST_BUNDLE_BYTES:
        return _invalid("trust_bundle_too_large")
    if snapshot_bytes is not None and len(snapshot_bytes) > MAX_SNAPSHOT_BYTES:
        return _invalid("snapshot_too_large", status="SNAPSHOT_MISMATCH")

    try:
        manifest_data = parse_json_strict(manifest_bytes)
        manifest = PassportManifest.model_validate(manifest_data)
        canonical = canonicalize(manifest_data)
    except (CanonicalizationError, ValueError):
        return _invalid("manifest_schema_error", status="INVALID_SCHEMA")

    base: dict[str, object] = {
        "schema_valid": True,
        "canonical_manifest": canonical == manifest_bytes,
        "certificate_id": manifest.certificate_id,
    }
    if canonical != manifest_bytes:
        return _invalid("manifest_is_not_canonical", status="INVALID_SCHEMA", **base)

    try:
        trust_data = parse_json_strict(trust_bundle_bytes)
        trust_bundle = TrustBundle.model_validate(trust_data)
    except (CanonicalizationError, ValueError):
        return _invalid("trust_or_signature_schema_error", status="INVALID_SCHEMA", **base)
    try:
        header = parse_header(detached_jws)
    except JWSError as exc:
        status = (
            "UNSUPPORTED_ALGORITHM" if str(exc) == "unsupported_algorithm" else "INVALID_SIGNATURE"
        )
        return _invalid(str(exc), status=status, **base)

    key_id = str(header["kid"])
    base.update(key_id=key_id, trust_bundle_generated_at=trust_bundle.generated_at)
    if key_id != manifest.signing.key_id:
        return _invalid(
            "signature_key_id_does_not_match_manifest", status="INVALID_SIGNATURE", **base
        )
    key = next((candidate for candidate in trust_bundle.keys if candidate.key_id == key_id), None)
    if key is None:
        return _invalid("signing_key_not_in_trust_bundle", status="UNKNOWN_KEY", **base)
    base["key_status"] = key.status

    try:
        public_key = Ed25519PublicKey.from_public_bytes(b64url_decode(key.public_key))
        verify_detached(manifest_bytes, detached_jws, public_key)
    except (JWSError, ValueError) as exc:
        status = "UNSUPPORTED_ALGORITHM" if "header" in str(exc) else "INVALID_SIGNATURE"
        return _invalid(str(exc), status=status, **base)
    base["signature_valid"] = True

    if key.status == "revoked":
        return _invalid("signing_key_revoked", status="REVOKED", **base)

    historical_validity = (
        "valid" if key.not_before <= manifest.issued_at <= key.not_after else "outside_interval"
    )
    base["historical_key_validity"] = historical_validity
    if historical_validity == "outside_interval":
        return _invalid("signature_issued_outside_key_validity", status="INVALID_SIGNATURE", **base)

    content_integrity = "not_supplied"
    if answer_bytes is not None:
        answer_matches = content_digest("ANSWER", answer_bytes) == manifest.answer.sha256
        content_integrity = "valid" if answer_matches else "invalid"
    base["content_integrity"] = content_integrity
    if content_integrity == "invalid":
        return _invalid("answer_hash_mismatch", status="CONTENT_MODIFIED", **base)

    scope_match = "not_evaluated"
    if expected_scope_fingerprint is not None:
        scope_match = (
            "valid"
            if expected_scope_fingerprint == manifest.scope.tenant_workspace_fingerprint
            else "invalid"
        )
    base["scope_match"] = scope_match
    if scope_match == "invalid":
        return _invalid("scope_fingerprint_mismatch", status="CONTENT_MODIFIED", **base)

    configuration_match = "not_evaluated"
    if expected_configuration_digest is not None:
        configuration_match = (
            "valid"
            if expected_configuration_digest == manifest.assurance.retrieval_configuration_sha256
            else "invalid"
        )
    base["configuration_match"] = configuration_match
    if configuration_match == "invalid":
        return _invalid("configuration_fingerprint_mismatch", status="CONTENT_MODIFIED", **base)

    now = at or datetime.now(UTC)
    if now.tzinfo is None:
        return _invalid("verification_time_must_have_timezone", **base)
    if now < manifest.issued_at:
        return _invalid("verification_time_precedes_issuance", status="INDETERMINATE", **base)

    if now < key.not_before:
        base["key_status"] = "not_yet_valid"
        return _invalid("key_not_yet_valid", status="INDETERMINATE", **base)
    if now > key.not_after and key.status == "trusted":
        base["key_status"] = "expired"
    not_after = manifest.freshness.not_after
    freshness = "unknown" if not_after is None else ("fresh" if now <= not_after else "expired")
    base["freshness"] = freshness

    if snapshot_bytes is not None:
        snapshot_error = _verify_snapshot(manifest, snapshot_bytes)
        base["snapshot_integrity"] = "invalid" if snapshot_error else "valid"
        if snapshot_error:
            status = (
                "STALE"
                if snapshot_error == "snapshot_document_version_mismatch"
                else "SNAPSHOT_MISMATCH"
            )
            return _invalid(snapshot_error, status=status, **base)

    if freshness == "expired":
        return VerificationResult(
            status="EXPIRED", overall="valid_review_required", errors=[], **base
        )
    if base["key_status"] == "expired":
        return VerificationResult(
            status="EXPIRED", overall="valid_review_required", errors=[], **base
        )
    review_required = freshness != "fresh" or key.status == "retired"
    status = "VERIFIED" if snapshot_bytes is not None else "VERIFIED_WITHOUT_SNAPSHOT"
    if review_required:
        status = "INDETERMINATE"
    return VerificationResult(
        status=status,
        overall="valid_review_required" if review_required else "valid",
        errors=[],
        **base,
    )


def _verify_snapshot(manifest: PassportManifest, raw: bytes) -> str | None:
    try:
        data = parse_json_strict(raw)
        snapshot = EvidenceSnapshot.model_validate(data)
        if canonicalize(data) != raw:
            return "snapshot_is_not_canonical"
    except (CanonicalizationError, ValueError):
        return "snapshot_schema_error"
    if snapshot.certificate_id != manifest.certificate_id:
        return "snapshot_certificate_mismatch"
    if snapshot.scope_fingerprint != manifest.scope.tenant_workspace_fingerprint:
        return "snapshot_scope_mismatch"

    documents = {(item.document_id, item.document_version): item for item in snapshot.documents}
    evidence = {item.evidence_id: item for item in snapshot.evidence}
    referenced_evidence = {
        citation.evidence_id for claim in manifest.claims for citation in claim.citations
    }
    if set(evidence) != referenced_evidence:
        return "snapshot_evidence_set_mismatch"

    referenced_documents: set[tuple[str, str]] = set()
    for claim in manifest.claims:
        for citation in claim.citations:
            key = (citation.document_id, citation.document_version)
            referenced_documents.add(key)
            document = documents.get(key)
            item = evidence.get(citation.evidence_id)
            if document is None:
                same_document = any(
                    candidate.document_id == citation.document_id
                    for candidate in snapshot.documents
                )
                if same_document:
                    return "snapshot_document_version_mismatch"
                return "snapshot_reference_mismatch"
            if item is None:
                return "snapshot_reference_mismatch"
            if item.document_id != citation.document_id:
                return "snapshot_document_mismatch"
            if item.document_version != citation.document_version:
                return "snapshot_document_version_mismatch"
            document_digest = content_digest("DOCUMENT", b64url_decode(document.content_base64url))
            if document_digest != citation.document_sha256:
                return "snapshot_document_checksum_mismatch"
            span_digest = content_digest("EVIDENCE_SPAN", b64url_decode(item.content_base64url))
            if span_digest != citation.evidence_span_sha256:
                return "snapshot_evidence_span_mismatch"
    if set(documents) != referenced_documents:
        return "snapshot_document_set_mismatch"
    return None
