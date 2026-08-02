"""Internal-only, post-support passport issuance integration.

This module consumes finalized server state. It performs no retrieval, generation, persistence,
or network operations and deliberately exposes no API model.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Literal, Protocol
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Chunk, Document, DocumentVersion, Workspace
from app.models.schemas import SearchResponse
from app.passport.canonical import canonicalize
from app.passport.hashing import content_digest
from app.passport.schema import (
    AnswerBinding,
    Applicability,
    AssuranceBinding,
    CitationBinding,
    ClaimBinding,
    FreshnessBinding,
    PassportManifest,
    ScopeBinding,
    SigningBinding,
)

SUPPORT_GATE_VERSION = "static-support-0.72-v1"
CLAIM_VERIFIER_VERSION = "canonical-response-state-v1"
ANSWER_NORMALIZATION_VERSION = "utf8-exact-v1"
EXPORT_POLICY_ID = "base-manifest-no-evidence-v1"
FRESHNESS_POLICY_ID = "answer-passport-30d-v1"


class IssuanceStatus(StrEnum):
    NOT_REQUESTED_OR_DISABLED = "NOT_REQUESTED_OR_DISABLED"
    ISSUED = "ISSUED"
    INELIGIBLE = "INELIGIBLE"
    SIGNER_UNAVAILABLE = "SIGNER_UNAVAILABLE"
    FAILED = "FAILED"


class IneligibilityReason(StrEnum):
    FEATURE_DISABLED = "FEATURE_DISABLED"
    RESULT_NOT_SUPPORTED = "RESULT_NOT_SUPPORTED"
    CONFLICT_NOT_ELIGIBLE = "CONFLICT_NOT_ELIGIBLE"
    INCOMPLETE_CLAIM_MAPPING = "INCOMPLETE_CLAIM_MAPPING"
    INCOMPLETE_CITATION_MAPPING = "INCOMPLETE_CITATION_MAPPING"
    MISSING_SCOPE = "MISSING_SCOPE"
    SIGNER_UNAVAILABLE = "SIGNER_UNAVAILABLE"
    ISSUANCE_ERROR = "ISSUANCE_ERROR"


class ProjectionRejected(ValueError):
    def __init__(self, reason: IneligibilityReason) -> None:
        self.reason = reason
        super().__init__(reason.value)


class ProjectedCitation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    citation_id: str = Field(min_length=1, max_length=200)
    evidence_id: str = Field(min_length=1, max_length=200)
    evidence_span: bytes = Field(min_length=1, max_length=100_000)
    document_id: str = Field(min_length=1, max_length=200)
    document_version: str = Field(min_length=1, max_length=200)
    document_checksum: str = Field(pattern=r"^[0-9a-f]{64}$")
    applicability_policy_id: str = Field(min_length=1, max_length=200)


class ProjectedClaim(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    claim_id: str = Field(min_length=1, max_length=200)
    normalized_text: str = Field(min_length=1, max_length=100_000)
    verified: Literal[True]
    citations: tuple[ProjectedCitation, ...] = Field(min_length=1, max_length=100)


class SupportedAnswerProjection(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    decision: Literal["supported"]
    support_decision_final: Literal[True]
    answer: bytes = Field(min_length=1, max_length=1_000_000)
    answer_media_type: Literal["text/plain; charset=utf-8"]
    answer_normalization_version: Literal["utf8-exact-v1"]
    claims: tuple[ProjectedClaim, ...] = Field(min_length=1, max_length=1_000)
    tenant_id: str = Field(min_length=1, max_length=200)
    workspace_id: str = Field(min_length=1, max_length=200)
    audience_policy_id: str = Field(min_length=1, max_length=200)
    export_policy_id: Literal["base-manifest-no-evidence-v1"]
    support_gate_version: str = Field(min_length=1, max_length=200)
    claim_verifier_version: str = Field(min_length=1, max_length=200)
    retrieval_configuration: bytes = Field(min_length=1, max_length=100_000)
    generation_provider_alias: str = Field(min_length=1, max_length=200)
    approved_model_digest: str | None = None
    completed_at: datetime
    correlation_id: str | None = Field(default=None, max_length=200)

    @model_validator(mode="after")
    def validate_projection(self) -> SupportedAnswerProjection:
        if self.completed_at.tzinfo is None:
            raise ValueError("completion_timestamp_requires_timezone")
        claim_ids = [claim.claim_id for claim in self.claims]
        citation_ids = [
            citation.citation_id for claim in self.claims for citation in claim.citations
        ]
        if len(claim_ids) != len(set(claim_ids)):
            raise ValueError("duplicate_claim_id")
        if len(citation_ids) != len(set(citation_ids)):
            raise ValueError("duplicate_citation_id")
        return self


class InternalIssuanceResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    status: IssuanceStatus
    reason: IneligibilityReason | None = None
    manifest: bytes | None = None
    detached_signature: str | None = None
    passport_id: str | None = None
    signer_key_id: str | None = None
    schema_version: Literal["vap-1"] | None = None


class PassportSigner(Protocol):
    @property
    def key_id(self) -> str: ...

    async def sign(self, payload: bytes) -> str: ...


AuditSink = Callable[[dict[str, str | None]], Awaitable[None]]


class IssuanceContext:
    """Request-scoped at-most-once state; never share this object across requests."""

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._result: InternalIssuanceResult | None = None

    async def run_once(
        self, operation: Callable[[], Awaitable[InternalIssuanceResult]]
    ) -> InternalIssuanceResult:
        async with self._lock:
            if self._result is None:
                try:
                    self._result = await operation()
                except asyncio.CancelledError:
                    self._result = InternalIssuanceResult(
                        status=IssuanceStatus.FAILED,
                        reason=IneligibilityReason.ISSUANCE_ERROR,
                    )
                    raise
            return self._result


def _normalize_claim(value: str) -> str:
    return " ".join(value.split())


def _citation_identifier(citation: dict, index: int) -> str:
    return str(
        citation.get("citation_id")
        or citation.get("citation_label")
        or citation.get("external_source_label")
        or citation.get("chunk_id")
        or f"C{index}"
    )


def response_eligibility_reason(response: SearchResponse) -> IneligibilityReason | None:
    """Classify finalized state using neutral passport terminology."""

    state = response.response_state
    if state is None:
        return IneligibilityReason.RESULT_NOT_SUPPORTED
    if (
        state.conflict.unresolved
        or response.conflicts
        or state.primary_state == "CONFLICTING_EVIDENCE"
    ):
        return IneligibilityReason.CONFLICT_NOT_ELIGIBLE
    if state.primary_state not in {"SUPPORTED", "SUPPORTED_COMPOSITE"}:
        return IneligibilityReason.RESULT_NOT_SUPPORTED
    if not state.answer or not state.claims:
        return IneligibilityReason.INCOMPLETE_CLAIM_MAPPING
    if not response.citations or any(not claim.citation_ids for claim in state.claims):
        return IneligibilityReason.INCOMPLETE_CITATION_MAPPING
    displayed_ids = {
        _citation_identifier(citation, index)
        for index, citation in enumerate(response.citations, 1)
    }
    mapped_ids = {citation_id for claim in state.claims for citation_id in claim.citation_ids}
    if displayed_ids != set(state.citation_ids) or mapped_ids != displayed_ids:
        return IneligibilityReason.INCOMPLETE_CITATION_MAPPING
    if response.generation_used and (
        response.generation_verification != "verified" or not response.claim_verification_passed
    ):
        return IneligibilityReason.INCOMPLETE_CLAIM_MAPPING
    return None


async def project_search_response(
    session: AsyncSession,
    *,
    response: SearchResponse,
    workspace_id: UUID,
    completed_at: datetime,
    retrieval_configuration: dict[str, object],
) -> SupportedAnswerProjection:
    """Adapt final displayed state using authoritative database scope and document metadata."""

    state = response.response_state
    if state is None or state.primary_state not in {"SUPPORTED", "SUPPORTED_COMPOSITE"}:
        raise ProjectionRejected(IneligibilityReason.RESULT_NOT_SUPPORTED)
    if state.conflict.unresolved or response.conflicts:
        raise ProjectionRejected(IneligibilityReason.CONFLICT_NOT_ELIGIBLE)
    if not state.answer or not state.claims or not response.citations:
        raise ProjectionRejected(IneligibilityReason.INCOMPLETE_CLAIM_MAPPING)

    workspace = await session.get(Workspace, workspace_id)
    if workspace is None:
        raise ProjectionRejected(IneligibilityReason.MISSING_SCOPE)
    displayed: dict[str, dict] = {}
    chunk_ids: list[UUID] = []
    for index, citation in enumerate(response.citations, 1):
        citation_id = _citation_identifier(citation, index)
        if citation_id in displayed:
            raise ProjectionRejected(IneligibilityReason.INCOMPLETE_CITATION_MAPPING)
        try:
            chunk_id = UUID(str(citation["chunk_id"]))
        except (KeyError, TypeError, ValueError) as exc:
            raise ProjectionRejected(IneligibilityReason.INCOMPLETE_CITATION_MAPPING) from exc
        displayed[citation_id] = citation
        chunk_ids.append(chunk_id)

    rows = (
        await session.execute(
            select(Chunk, DocumentVersion, Document)
            .join(DocumentVersion, Chunk.document_version_id == DocumentVersion.id)
            .join(Document, DocumentVersion.document_id == Document.id)
            .where(Chunk.id.in_(chunk_ids), Document.workspace_id == workspace_id)
        )
    ).all()
    authoritative = {str(row.Chunk.id): row for row in rows}
    if len(authoritative) != len(chunk_ids):
        raise ProjectionRejected(IneligibilityReason.INCOMPLETE_CITATION_MAPPING)

    projected_claims: list[ProjectedClaim] = []
    for claim in state.claims:
        projected_citations: list[ProjectedCitation] = []
        for citation_id in claim.citation_ids:
            displayed_citation = displayed.get(citation_id)
            if displayed_citation is None:
                raise ProjectionRejected(IneligibilityReason.INCOMPLETE_CLAIM_MAPPING)
            row = authoritative.get(str(displayed_citation.get("chunk_id")))
            if row is None or str(displayed_citation.get("document_id")) != str(row.Document.id):
                raise ProjectionRejected(IneligibilityReason.INCOMPLETE_CITATION_MAPPING)
            excerpt = str(displayed_citation.get("excerpt") or "").encode("utf-8")
            projected_citations.append(
                ProjectedCitation(
                    citation_id=citation_id,
                    evidence_id=str(row.Chunk.id),
                    evidence_span=excerpt,
                    document_id=str(row.Document.id),
                    document_version=str(row.DocumentVersion.version_number),
                    document_checksum=row.DocumentVersion.checksum_sha256.lower(),
                    applicability_policy_id=EXPORT_POLICY_ID,
                )
            )
        projected_claims.append(
            ProjectedClaim(
                claim_id=claim.claim_id,
                normalized_text=_normalize_claim(claim.text),
                verified=True,
                citations=tuple(projected_citations),
            )
        )

    generation_alias = response.generation_provider or "extractive"
    approved_model_digest = (
        content_digest("CONFIG", response.generation_model.encode())
        if response.generation_used and response.generation_model
        else None
    )
    return SupportedAnswerProjection(
        decision="supported",
        support_decision_final=True,
        answer=state.answer.encode("utf-8"),
        answer_media_type="text/plain; charset=utf-8",
        answer_normalization_version=ANSWER_NORMALIZATION_VERSION,
        claims=tuple(projected_claims),
        tenant_id=str(workspace.organization_id),
        workspace_id=str(workspace_id),
        audience_policy_id=EXPORT_POLICY_ID,
        export_policy_id=EXPORT_POLICY_ID,
        support_gate_version=SUPPORT_GATE_VERSION,
        claim_verifier_version=CLAIM_VERIFIER_VERSION,
        retrieval_configuration=canonicalize(retrieval_configuration),
        generation_provider_alias=generation_alias,
        approved_model_digest=approved_model_digest,
        completed_at=completed_at,
        correlation_id=response.request_id,
    )


def eligibility_reason(
    projection: SupportedAnswerProjection | None,
    *,
    enabled: bool,
    signer: PassportSigner | None,
) -> IneligibilityReason | None:
    if not enabled:
        return IneligibilityReason.FEATURE_DISABLED
    if signer is None:
        return IneligibilityReason.SIGNER_UNAVAILABLE
    if projection is None:
        return IneligibilityReason.RESULT_NOT_SUPPORTED
    return None


def manifest_from_projection(
    projection: SupportedAnswerProjection, *, certificate_id: UUID, signer_key_id: str
) -> PassportManifest:
    scope = content_digest(
        "SCOPE",
        canonicalize({"tenant_id": projection.tenant_id, "workspace_id": projection.workspace_id}),
    )
    return PassportManifest(
        schema_version="vap-1",
        certificate_id=f"urn:uuid:{certificate_id}",
        answer=AnswerBinding(
            media_type=projection.answer_media_type,
            sha256=content_digest("ANSWER", projection.answer),
        ),
        claims=[
            ClaimBinding(
                claim_id=claim.claim_id,
                normalized_sha256=content_digest("CLAIM", claim.normalized_text.encode()),
                citations=[
                    CitationBinding(
                        evidence_id=citation.evidence_id,
                        evidence_span_sha256=content_digest(
                            "EVIDENCE_SPAN", citation.evidence_span
                        ),
                        document_id=citation.document_id,
                        document_version=citation.document_version,
                        document_sha256=content_digest(
                            "DOCUMENT", citation.document_checksum.encode()
                        ),
                        scope_fingerprint=scope,
                        applicability=Applicability(policy_id=citation.applicability_policy_id),
                    )
                    for citation in claim.citations
                ],
            )
            for claim in projection.claims
        ],
        scope=ScopeBinding(
            tenant_workspace_fingerprint=scope, audience=projection.audience_policy_id
        ),
        assurance=AssuranceBinding(
            support_gate_version=projection.support_gate_version,
            verifier_version=projection.claim_verifier_version,
            retrieval_configuration_sha256=content_digest(
                "CONFIG", projection.retrieval_configuration
            ),
            generation_provider_alias=projection.generation_provider_alias,
            approved_model_digest=projection.approved_model_digest,
        ),
        issued_at=projection.completed_at,
        freshness=FreshnessBinding(
            policy_id=FRESHNESS_POLICY_ID, not_after=projection.completed_at + timedelta(days=30)
        ),
        signing=SigningBinding(algorithm="EdDSA", key_id=signer_key_id),
    )


class PassportIssuanceCoordinator:
    def __init__(
        self,
        *,
        enabled: bool,
        signer: PassportSigner | None = None,
        clock: Callable[[], datetime] | None = None,
        identifier: Callable[[], UUID] | None = None,
        audit_sink: AuditSink | None = None,
    ) -> None:
        self.enabled = enabled
        self.signer = signer
        self.clock = clock or (lambda: datetime.now(UTC))
        self.identifier = identifier or uuid4
        self.audit_sink = audit_sink

    async def issue(
        self,
        projection: SupportedAnswerProjection | None,
        *,
        context: IssuanceContext,
        ineligibility_reason: IneligibilityReason | None = None,
    ) -> InternalIssuanceResult:
        return await context.run_once(lambda: self._issue(projection, ineligibility_reason))

    async def _issue(
        self,
        projection: SupportedAnswerProjection | None,
        ineligibility_reason: IneligibilityReason | None,
    ) -> InternalIssuanceResult:
        if ineligibility_reason is not None:
            return InternalIssuanceResult(
                status=IssuanceStatus.INELIGIBLE, reason=ineligibility_reason
            )
        reason = eligibility_reason(projection, enabled=self.enabled, signer=self.signer)
        if reason == IneligibilityReason.FEATURE_DISABLED:
            return InternalIssuanceResult(
                status=IssuanceStatus.NOT_REQUESTED_OR_DISABLED, reason=reason
            )
        if reason == IneligibilityReason.SIGNER_UNAVAILABLE:
            return InternalIssuanceResult(status=IssuanceStatus.SIGNER_UNAVAILABLE, reason=reason)
        if reason is not None or projection is None:
            return InternalIssuanceResult(status=IssuanceStatus.INELIGIBLE, reason=reason)
        signer = self.signer
        if signer is None:  # narrowed above; keeps type and runtime fail-closed
            return InternalIssuanceResult(
                status=IssuanceStatus.SIGNER_UNAVAILABLE,
                reason=IneligibilityReason.SIGNER_UNAVAILABLE,
            )
        try:
            certificate_id = self.identifier()
            manifest = manifest_from_projection(
                projection, certificate_id=certificate_id, signer_key_id=signer.key_id
            )
            payload = canonicalize(manifest.model_dump(mode="json"))
            signature = await signer.sign(payload)
            result = InternalIssuanceResult(
                status=IssuanceStatus.ISSUED,
                manifest=payload,
                detached_signature=signature,
                passport_id=manifest.certificate_id,
                signer_key_id=signer.key_id,
                schema_version="vap-1",
            )
            if self.audit_sink is not None:
                await self.audit_sink(
                    {
                        "event_type": "answer_passport.issued",
                        "passport_id": result.passport_id,
                        "schema_version": result.schema_version,
                        "issuance_status": result.status.value,
                        "scope_fingerprint": manifest.scope.tenant_workspace_fingerprint,
                        "signer_key_id": result.signer_key_id,
                        "correlation_id": projection.correlation_id,
                        "timestamp": self.clock().isoformat(),
                    }
                )
            return result
        except asyncio.CancelledError:
            raise
        except Exception:
            return InternalIssuanceResult(
                status=IssuanceStatus.FAILED, reason=IneligibilityReason.ISSUANCE_ERROR
            )
