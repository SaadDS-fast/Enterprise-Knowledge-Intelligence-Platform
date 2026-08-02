"""Strict VAP-1 manifest and local trust-bundle schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.passport.hashing import b64url_decode


class StrictModel(BaseModel):
    # Datetimes are carried as RFC 3339 JSON strings and therefore require Pydantic's JSON-style
    # parsing. Field types and the forbidden-extra policy still keep the wire profile narrow.
    model_config = ConfigDict(extra="forbid")


def _digest(value: str) -> str:
    if len(b64url_decode(value)) != 32:
        raise ValueError("digest_must_be_sha256")
    return value


class AnswerBinding(StrictModel):
    media_type: Literal["text/plain; charset=utf-8"]
    sha256: str

    _validate_sha256 = field_validator("sha256")(_digest)


class Applicability(StrictModel):
    policy_id: str = Field(min_length=1, max_length=200)


class CitationBinding(StrictModel):
    evidence_id: str = Field(min_length=1, max_length=200)
    evidence_span_sha256: str
    document_id: str = Field(min_length=1, max_length=200)
    document_version: str = Field(min_length=1, max_length=200)
    document_sha256: str
    scope_fingerprint: str
    applicability: Applicability | None = None

    _validate_span_sha256 = field_validator("evidence_span_sha256")(_digest)
    _validate_document_sha256 = field_validator("document_sha256")(_digest)
    _validate_scope_fingerprint = field_validator("scope_fingerprint")(_digest)


class ClaimBinding(StrictModel):
    claim_id: str = Field(min_length=1, max_length=200)
    normalized_sha256: str
    citations: list[CitationBinding] = Field(min_length=1, max_length=100)

    _validate_sha256 = field_validator("normalized_sha256")(_digest)

    @model_validator(mode="after")
    def unique_evidence_ids(self) -> ClaimBinding:
        identifiers = [citation.evidence_id for citation in self.citations]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("duplicate_evidence_id_within_claim")
        return self


class ScopeBinding(StrictModel):
    tenant_workspace_fingerprint: str
    audience: str = Field(min_length=1, max_length=200)

    _validate_fingerprint = field_validator("tenant_workspace_fingerprint")(_digest)


class AssuranceBinding(StrictModel):
    support_gate_version: str = Field(min_length=1, max_length=200)
    verifier_version: str = Field(min_length=1, max_length=200)
    retrieval_configuration_sha256: str
    generation_provider_alias: str = Field(min_length=1, max_length=200)
    approved_model_digest: str | None = None

    _validate_configuration = field_validator("retrieval_configuration_sha256")(_digest)

    @field_validator("approved_model_digest")
    @classmethod
    def validate_optional_digest(cls, value: str | None) -> str | None:
        return _digest(value) if value is not None else None


class FreshnessBinding(StrictModel):
    policy_id: str = Field(min_length=1, max_length=200)
    not_after: datetime | None = None


class SigningBinding(StrictModel):
    algorithm: Literal["EdDSA"]
    key_id: str = Field(min_length=1, max_length=200)


class PassportManifest(StrictModel):
    schema_version: Literal["vap-1"]
    certificate_id: str
    answer: AnswerBinding
    claims: list[ClaimBinding] = Field(min_length=1, max_length=1_000)
    scope: ScopeBinding
    assurance: AssuranceBinding
    issued_at: datetime
    freshness: FreshnessBinding
    signing: SigningBinding

    @field_validator("certificate_id")
    @classmethod
    def validate_certificate_id(cls, value: str) -> str:
        prefix = "urn:uuid:"
        if not value.startswith(prefix):
            raise ValueError("certificate_id_must_be_uuid_urn")
        UUID(value[len(prefix) :])
        return value

    @model_validator(mode="after")
    def validate_manifest(self) -> PassportManifest:
        claim_ids = [claim.claim_id for claim in self.claims]
        if len(claim_ids) != len(set(claim_ids)):
            raise ValueError("duplicate_claim_id")
        if self.issued_at.tzinfo is None:
            raise ValueError("issued_at_must_have_timezone")
        if self.freshness.not_after is not None:
            if self.freshness.not_after.tzinfo is None:
                raise ValueError("not_after_must_have_timezone")
            if self.freshness.not_after < self.issued_at:
                raise ValueError("not_after_precedes_issued_at")
        return self


class TrustKey(StrictModel):
    key_id: str = Field(min_length=1, max_length=200)
    algorithm: Literal["EdDSA"]
    public_key: str
    status: Literal["trusted", "retired", "revoked"]
    not_before: datetime
    not_after: datetime
    retired_at: datetime | None = None
    revoked_at: datetime | None = None

    @field_validator("public_key")
    @classmethod
    def validate_public_key(cls, value: str) -> str:
        if len(b64url_decode(value)) != 32:
            raise ValueError("ed25519_public_key_must_be_32_bytes")
        return value

    @model_validator(mode="after")
    def validate_lifecycle(self) -> TrustKey:
        if self.not_before.tzinfo is None or self.not_after.tzinfo is None:
            raise ValueError("key_validity_requires_timezone")
        if self.not_after <= self.not_before:
            raise ValueError("invalid_key_validity_interval")
        if self.status == "revoked" and self.revoked_at is None:
            raise ValueError("revoked_key_requires_revoked_at")
        if self.retired_at is not None:
            if self.retired_at.tzinfo is None:
                raise ValueError("retired_at_requires_timezone")
            if self.retired_at < self.not_before:
                raise ValueError("retired_at_precedes_validity_interval")
        if self.revoked_at is not None and self.revoked_at.tzinfo is None:
            raise ValueError("revoked_at_requires_timezone")
        return self


class TrustBundle(StrictModel):
    schema_version: Literal["vap-trust-1"]
    generated_at: datetime
    keys: list[TrustKey] = Field(min_length=1, max_length=1_000)

    @model_validator(mode="after")
    def unique_key_ids(self) -> TrustBundle:
        identifiers = [key.key_id for key in self.keys]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("duplicate_key_id")
        if self.generated_at.tzinfo is None:
            raise ValueError("generated_at_must_have_timezone")
        return self


class SnapshotDocument(StrictModel):
    document_id: str = Field(min_length=1, max_length=200)
    document_version: str = Field(min_length=1, max_length=200)
    document_sha256: str
    content_base64url: str

    _validate_document_sha256 = field_validator("document_sha256")(_digest)

    @field_validator("content_base64url")
    @classmethod
    def validate_content(cls, value: str) -> str:
        b64url_decode(value)
        return value


class SnapshotEvidence(StrictModel):
    evidence_id: str = Field(min_length=1, max_length=200)
    document_id: str = Field(min_length=1, max_length=200)
    document_version: str = Field(min_length=1, max_length=200)
    evidence_span_sha256: str
    content_base64url: str

    _validate_span_sha256 = field_validator("evidence_span_sha256")(_digest)

    @field_validator("content_base64url")
    @classmethod
    def validate_content(cls, value: str) -> str:
        b64url_decode(value)
        return value


class EvidenceSnapshot(StrictModel):
    schema_version: Literal["vap-snapshot-1"]
    certificate_id: str
    scope_fingerprint: str
    documents: list[SnapshotDocument] = Field(min_length=1, max_length=1_000)
    evidence: list[SnapshotEvidence] = Field(min_length=1, max_length=10_000)

    _validate_scope = field_validator("scope_fingerprint")(_digest)

    @model_validator(mode="after")
    def validate_uniqueness(self) -> EvidenceSnapshot:
        document_keys = [(item.document_id, item.document_version) for item in self.documents]
        if len(document_keys) != len(set(document_keys)):
            raise ValueError("duplicate_snapshot_document")
        evidence_ids = [item.evidence_id for item in self.evidence]
        if len(evidence_ids) != len(set(evidence_ids)):
            raise ValueError("duplicate_snapshot_evidence_id")
        return self
