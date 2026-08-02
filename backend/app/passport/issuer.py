"""Synthetic-only VAP-1 manifest construction and issuance eligibility checks.

This module is deliberately not connected to application answers, services, APIs, or persistence.
It exists to make the cryptographic boundary and rejection rules executable in Phase 1 fixtures.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.passport.schema import (
    AnswerBinding,
    AssuranceBinding,
    ClaimBinding,
    FreshnessBinding,
    PassportManifest,
    ScopeBinding,
    SigningBinding,
)


class IssuanceRejected(ValueError):
    """Raised when a synthetic decision is ineligible for passport construction."""


class SyntheticIssuanceInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["vap-1"]
    decision: Literal["supported", "refused", "unsupported", "operational_error"]
    certificate_id: str
    answer: AnswerBinding
    claims: list[ClaimBinding] = Field(min_length=1, max_length=1_000)
    scope: ScopeBinding
    assurance: AssuranceBinding
    issued_at: datetime
    freshness: FreshnessBinding
    signing: SigningBinding
    support_gate_passed: bool

    @model_validator(mode="after")
    def validate_eligibility(self) -> SyntheticIssuanceInput:
        if self.decision != "supported" or not self.support_gate_passed:
            raise ValueError("only_supported_decisions_are_eligible")
        if not self.assurance.support_gate_version.strip():
            raise ValueError("missing_support_gate_metadata")
        for claim in self.claims:
            for citation in claim.citations:
                if citation.scope_fingerprint != self.scope.tenant_workspace_fingerprint:
                    raise ValueError("cross_scope_citation_mapping")
        versions: dict[str, str] = {}
        for citation in (citation for claim in self.claims for citation in claim.citations):
            previous = versions.setdefault(citation.document_id, citation.document_version)
            if previous != citation.document_version:
                raise ValueError("inconsistent_document_version")
        return self


def build_synthetic_manifest(data: dict[str, Any]) -> PassportManifest:
    """Build a manifest from an explicitly synthetic supported-decision fixture."""

    try:
        request = SyntheticIssuanceInput.model_validate(data)
        payload = request.model_dump(exclude={"decision", "support_gate_passed"})
        return PassportManifest.model_validate(payload)
    except ValueError as exc:
        raise IssuanceRejected("synthetic_issuance_rejected") from exc
