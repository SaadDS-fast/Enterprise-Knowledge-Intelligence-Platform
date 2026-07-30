from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, model_validator


class PrimaryResponseState(StrEnum):
    SUPPORTED = "SUPPORTED"
    SUPPORTED_COMPOSITE = "SUPPORTED_COMPOSITE"
    CONFLICTING_EVIDENCE = "CONFLICTING_EVIDENCE"
    KNOWLEDGE_ABSENT = "KNOWLEDGE_ABSENT"
    RETRIEVAL_FAILURE = "RETRIEVAL_FAILURE"
    AMBIGUOUS_QUERY = "AMBIGUOUS_QUERY"
    LOW_QUALITY_SOURCE = "LOW_QUALITY_SOURCE"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    PROCESSING_FAILED = "PROCESSING_FAILED"
    CANCELLED = "CANCELLED"


class EvidenceDecision(StrEnum):
    SUFFICIENT = "SUFFICIENT"
    PARTIAL = "PARTIAL"
    ABSENT = "ABSENT"
    CONFLICTING = "CONFLICTING"
    UNAVAILABLE = "UNAVAILABLE"


class ConflictCategory(StrEnum):
    VALUE_CONFLICT = "VALUE_CONFLICT"
    DATE_CONFLICT = "DATE_CONFLICT"
    ROLE_CONFLICT = "ROLE_CONFLICT"
    POLICY_RULE_CONFLICT = "POLICY_RULE_CONFLICT"
    VERSION_CONFLICT = "VERSION_CONFLICT"
    DEFINITION_CONFLICT = "DEFINITION_CONFLICT"
    SCOPE_CONFLICT = "SCOPE_CONFLICT"
    NO_CONFLICT = "NO_CONFLICT"


class ConfidenceBand(StrEnum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class NormalizedClaim(BaseModel):
    claim_id: str
    text: str
    subject: str | None = None
    attribute: str | None = None
    value: str | None = None
    unit: str | None = None
    currency: str | None = None
    date: str | None = None
    date_type: str | None = None
    role: str | None = None
    action: str | None = None
    negated: bool = False
    policy_version: str | None = None
    source_applicability: str = "applicable"
    document_status: str = "current"
    effective_period: str | None = None
    citation_ids: list[str] = Field(default_factory=list)


class ClaimSupport(BaseModel):
    claim_id: str
    text: str
    citation_ids: list[str] = Field(min_length=1)


class ConflictSide(BaseModel):
    claim_id: str
    text: str
    citation_ids: list[str] = Field(min_length=1)
    applicability: str = "applicable"


class ConflictResult(BaseModel):
    category: ConflictCategory = ConflictCategory.NO_CONFLICT
    unresolved: bool = False
    material: bool = False
    sides: list[ConflictSide] = Field(default_factory=list)
    resolution: str | None = None


class ConfidenceComponents(BaseModel):
    retrieval: ConfidenceBand = ConfidenceBand.NOT_APPLICABLE
    evidence_support: ConfidenceBand = ConfidenceBand.NOT_APPLICABLE
    conflict: ConfidenceBand = ConfidenceBand.NOT_APPLICABLE
    final: ConfidenceBand = ConfidenceBand.NOT_APPLICABLE


class RetrievalState(BaseModel):
    mode: str = "unknown"
    semantic_applied: bool = False
    reranker_applied: bool = False
    lexical_fallback_used: bool = False
    recovery_attempted: bool = False
    recovery_succeeded: bool = False
    failure_category: str | None = None


class ScopeState(BaseModel):
    selected_document_scope: bool = False
    authorized_document_ids: list[str] = Field(default_factory=list)


class CanonicalResponseState(BaseModel):
    primary_state: PrimaryResponseState
    answer: str | None = None
    claims: list[ClaimSupport] = Field(default_factory=list)
    citation_ids: list[str] = Field(default_factory=list)
    citation_document_ids: dict[str, str] = Field(default_factory=dict)
    evidence_decision: EvidenceDecision
    conflict: ConflictResult = Field(default_factory=ConflictResult)
    confidence: ConfidenceComponents = Field(default_factory=ConfidenceComponents)
    retrieval: RetrievalState = Field(default_factory=RetrievalState)
    scope: ScopeState = Field(default_factory=ScopeState)
    diagnostics: dict[str, Any] = Field(default_factory=dict)
    user_message: str

    @model_validator(mode="after")
    def enforce_invariants(self) -> CanonicalResponseState:
        errors = validate_response_state(self)
        if errors:
            raise ValueError("; ".join(errors))
        return self


_SUPPORTED = {
    PrimaryResponseState.SUPPORTED,
    PrimaryResponseState.SUPPORTED_COMPOSITE,
}


def validate_response_state(state: CanonicalResponseState) -> list[str]:
    errors: list[str] = []
    citation_ids = set(state.citation_ids)
    selected_ids = set(state.scope.authorized_document_ids)
    claim_citations = {citation for claim in state.claims for citation in claim.citation_ids}

    if state.primary_state in _SUPPORTED:
        if not state.answer or not state.answer.strip():
            errors.append("supported response requires an answer")
        if not state.claims:
            errors.append("supported response requires a claim")
        if state.evidence_decision != EvidenceDecision.SUFFICIENT:
            errors.append("supported response requires sufficient evidence")
        if state.conflict.unresolved:
            errors.append("supported response cannot contain an unresolved conflict")
        if state.confidence.final not in {ConfidenceBand.HIGH, ConfidenceBand.MEDIUM}:
            errors.append("supported response requires high or medium confidence")
        if not claim_citations or not claim_citations.issubset(citation_ids):
            errors.append("every supported claim must map to a returned citation")
    if state.primary_state == PrimaryResponseState.SUPPORTED_COMPOSITE:
        if len(state.claims) < 2:
            errors.append("composite response requires multiple supported components")
        if any(not claim.citation_ids for claim in state.claims):
            errors.append("every composite component requires a citation")
    if state.primary_state == PrimaryResponseState.CONFLICTING_EVIDENCE:
        if state.evidence_decision != EvidenceDecision.CONFLICTING:
            errors.append("conflict response requires conflicting evidence decision")
        if (
            state.conflict.category == ConflictCategory.NO_CONFLICT
            or not state.conflict.unresolved
            or not state.conflict.material
        ):
            errors.append("conflict response requires a material unresolved typed conflict")
        if len(state.conflict.sides) < 2:
            errors.append("conflict response requires two cited sides")
        if state.confidence.final == ConfidenceBand.HIGH:
            errors.append("unresolved conflict cannot have high final confidence")
    if state.primary_state == PrimaryResponseState.KNOWLEDGE_ABSENT:
        if state.answer or state.claims or state.citation_ids:
            errors.append("knowledge absence cannot return answer support")
        if state.evidence_decision != EvidenceDecision.ABSENT:
            errors.append("knowledge absence requires absent evidence decision")
        if state.retrieval.failure_category:
            errors.append("retrieval failure cannot be classified as knowledge absence")
    if state.primary_state == PrimaryResponseState.RETRIEVAL_FAILURE:
        if state.answer or state.claims:
            errors.append("retrieval failure cannot return a factual answer")
        if state.evidence_decision != EvidenceDecision.UNAVAILABLE:
            errors.append("retrieval failure requires unavailable evidence")
        if not state.retrieval.failure_category:
            errors.append("retrieval failure requires a sanitized failure category")
    if state.primary_state == PrimaryResponseState.AMBIGUOUS_QUERY:
        if state.answer or state.citation_ids:
            errors.append("ambiguous query cannot return factual answer support")
        if state.confidence.final == ConfidenceBand.HIGH:
            errors.append("ambiguous query cannot have high final confidence")
    if state.primary_state in {
        PrimaryResponseState.PROCESSING_FAILED,
        PrimaryResponseState.CANCELLED,
    } and (state.answer or state.claims or state.citation_ids):
        errors.append("failed or cancelled response cannot return answer support")
    if state.retrieval.semantic_applied and state.retrieval.lexical_fallback_used:
        errors.append("semantic retrieval and lexical-only fallback are mutually exclusive")
    if state.scope.selected_document_scope:
        cited_documents = {
            document_id
            for citation_id, document_id in state.citation_document_ids.items()
            if citation_id in citation_ids
        }
        if not selected_ids or not cited_documents.issubset(selected_ids):
            errors.append("citation falls outside selected-document scope")
    return errors


def safe_response_state(**values: Any) -> CanonicalResponseState:
    try:
        return CanonicalResponseState(**values)
    except (TypeError, ValueError):
        return CanonicalResponseState(
            primary_state=PrimaryResponseState.PROCESSING_FAILED,
            evidence_decision=EvidenceDecision.UNAVAILABLE,
            confidence=ConfidenceComponents(),
            retrieval=RetrievalState(failure_category="response_invariant_violation"),
            user_message="The response could not be completed safely.",
            diagnostics={"reason_code": "response_invariant_violation"},
        )


def response_state_from_legacy(
    *,
    answer: str | None,
    outcome: str,
    citations: list[dict[str, Any]],
    claims: list[dict[str, Any]] | None = None,
    conflicts: list[dict[str, Any]] | None = None,
    confidence_category: str = "none",
    retrieval_diagnosis: dict[str, Any] | None = None,
    selected_document_ids: list[str] | None = None,
    fallback_used: bool = False,
    status: str | None = None,
) -> CanonicalResponseState:
    diagnosis = retrieval_diagnosis or {}
    legacy_outcome = outcome.upper()
    diagnosis_status = str(diagnosis.get("status", "")).upper()
    primary = _primary_state(
        legacy_outcome,
        diagnosis_status,
        status,
        has_answer=bool(answer and answer.strip()),
        has_citations=bool(citations),
    )
    sufficiency_decision = str(diagnosis.get("sufficiency_decision", "")).upper()
    if sufficiency_decision == "LOW_QUALITY_SOURCE":
        primary = PrimaryResponseState.LOW_QUALITY_SOURCE
    elif (
        sufficiency_decision == "SUFFICIENT_COMPOSITE" and primary == PrimaryResponseState.SUPPORTED
    ):
        primary = PrimaryResponseState.SUPPORTED_COMPOSITE
    citation_ids, citation_documents = _citation_identity(citations)
    normalized_claims = _claim_support(claims or [], answer, citation_ids, citations)
    conflict = _legacy_conflict(conflicts or [], normalized_claims, citation_ids)
    if conflict.unresolved:
        primary = PrimaryResponseState.CONFLICTING_EVIDENCE
    final_confidence = _confidence_band(confidence_category)
    evidence_decision = _evidence_decision(primary)
    supported_answer = answer if primary in _SUPPORTED else None
    supported_claims = normalized_claims if primary in _SUPPORTED else []
    supported_citations = citation_ids if primary in _SUPPORTED else []
    if primary == PrimaryResponseState.CONFLICTING_EVIDENCE:
        supported_citations = citation_ids
    if primary in _SUPPORTED and final_confidence not in {
        ConfidenceBand.HIGH,
        ConfidenceBand.MEDIUM,
    }:
        final_confidence = ConfidenceBand.MEDIUM
    selected_ids = [str(item) for item in selected_document_ids or []]
    retrieval = RetrievalState(
        mode=str(diagnosis.get("retrieval_mode", "unknown")),
        semantic_applied=bool(diagnosis.get("semantic_used", False)),
        reranker_applied=bool(diagnosis.get("reranker_used", False)),
        lexical_fallback_used=bool(fallback_used or diagnosis.get("fallback_used", False))
        and not diagnosis.get("semantic_used", False),
        recovery_attempted=bool(diagnosis.get("retry_performed", False)),
        recovery_succeeded=diagnosis_status == "RETRIEVAL_FAILURE_RECOVERED",
        failure_category=(
            "retrieval_unavailable"
            if primary == PrimaryResponseState.RETRIEVAL_FAILURE
            else (
                "processing_failed" if primary == PrimaryResponseState.PROCESSING_FAILED else None
            )
        ),
    )
    if primary not in _SUPPORTED and primary != PrimaryResponseState.CONFLICTING_EVIDENCE:
        final_confidence = (
            ConfidenceBand.LOW
            if primary
            in {
                PrimaryResponseState.AMBIGUOUS_QUERY,
                PrimaryResponseState.INSUFFICIENT_EVIDENCE,
                PrimaryResponseState.LOW_QUALITY_SOURCE,
            }
            else ConfidenceBand.NOT_APPLICABLE
        )
    user_message = _user_message(primary, supported_answer, legacy_message=answer)
    values = {
        "primary_state": primary,
        "answer": supported_answer,
        "claims": supported_claims,
        "citation_ids": supported_citations,
        "citation_document_ids": citation_documents,
        "evidence_decision": evidence_decision,
        "conflict": conflict,
        "confidence": ConfidenceComponents(
            retrieval=_confidence_band_from_score(diagnosis.get("final_support_score")),
            evidence_support=final_confidence
            if primary in _SUPPORTED
            else ConfidenceBand.NOT_APPLICABLE,
            conflict=(
                ConfidenceBand.HIGH if conflict.unresolved else ConfidenceBand.NOT_APPLICABLE
            ),
            final=final_confidence,
        ),
        "retrieval": retrieval,
        "scope": ScopeState(
            selected_document_scope=bool(selected_ids),
            authorized_document_ids=selected_ids,
        ),
        "diagnostics": {
            "diagnosis_status": diagnosis_status or None,
            "reason_code": diagnosis.get("reason_code"),
        },
        "user_message": user_message,
    }
    return safe_response_state(**values)


def normalize_claim(
    text: str,
    *,
    claim_id: str = "claim-1",
    citation_ids: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> NormalizedClaim:
    metadata = metadata or {}
    compact = " ".join(text.split())
    lowered = compact.casefold()
    currency = next(
        (code for code in ("PKR", "USD", "EUR", "GBP") if code.casefold() in lowered), None
    )
    number_match = re.search(r"(?<!\w)(\d[\d,]*(?:\.\d+)?)", compact)
    value = _decimal_string(number_match.group(1)) if number_match else None
    unit = None
    if re.search(r"\b(per day|daily)\b", lowered):
        unit = "per_day"
    elif re.search(r"\b(per month|monthly)\b", lowered):
        unit = "per_month"
    elif re.search(r"\b(per year|annually|annual)\b", lowered):
        unit = "per_year"
    date_match = re.search(r"\b(\d{4}-\d{2}-\d{2}|\d{1,2}\s+[A-Za-z]+\s+\d{4})\b", compact)
    date_type = None
    if "effective" in lowered:
        date_type = "effective_date"
    elif "published" in lowered:
        date_type = "publication_date"
    attribute = _attribute(lowered)
    role = _approval_role(compact)
    action = "approve" if re.search(r"\b(approve|approves|approved|approval)\b", lowered) else None
    return NormalizedClaim(
        claim_id=claim_id,
        text=compact,
        subject=_subject(lowered, attribute),
        attribute=attribute,
        value=value,
        unit=unit,
        currency=currency,
        date=date_match.group(1) if date_match else None,
        date_type=date_type,
        role=role,
        action=action,
        negated=bool(re.search(r"\b(no|not|never|must not|does not)\b", lowered)),
        policy_version=_string_or_none(metadata.get("policy_version")),
        source_applicability=str(metadata.get("source_applicability", "applicable")),
        document_status=str(metadata.get("document_status", "current")).casefold(),
        effective_period=_string_or_none(metadata.get("effective_period")),
        citation_ids=citation_ids or [],
    )


def classify_claim_conflict(left: NormalizedClaim, right: NormalizedClaim) -> ConflictResult:
    if left.document_status != right.document_status and {
        left.document_status,
        right.document_status,
    } & {"superseded", "obsolete"}:
        current = left if left.document_status == "current" else right
        return ConflictResult(
            resolution=f"{current.claim_id} is the current authoritative version",
        )
    if left.source_applicability != right.source_applicability:
        return ConflictResult(
            category=ConflictCategory.SCOPE_CONFLICT,
            unresolved=False,
            material=False,
            resolution="Claims apply to different scopes.",
        )
    if not left.attribute or left.attribute != right.attribute:
        return ConflictResult()
    sides = [
        ConflictSide(
            claim_id=claim.claim_id,
            text=claim.text,
            citation_ids=claim.citation_ids,
            applicability=claim.source_applicability,
        )
        for claim in (left, right)
        if claim.citation_ids
    ]
    category = ConflictCategory.NO_CONFLICT
    if (
        left.action == right.action == "approve"
        and left.role
        and right.role
        and left.role != right.role
    ):
        category = ConflictCategory.ROLE_CONFLICT
    elif left.date_type == right.date_type and left.date and right.date and left.date != right.date:
        category = ConflictCategory.DATE_CONFLICT
    elif (
        left.value is not None
        and right.value is not None
        and (left.value, left.currency, left.unit) != (right.value, right.currency, right.unit)
    ):
        category = ConflictCategory.VALUE_CONFLICT
    elif left.negated != right.negated:
        category = ConflictCategory.POLICY_RULE_CONFLICT
    if category == ConflictCategory.NO_CONFLICT:
        return ConflictResult()
    return ConflictResult(
        category=category,
        unresolved=True,
        material=True,
        sides=sides,
    )


def legacy_fields(state: CanonicalResponseState) -> dict[str, Any]:
    outcome = {
        PrimaryResponseState.SUPPORTED: "ANSWER_SUPPORTED",
        PrimaryResponseState.SUPPORTED_COMPOSITE: "ANSWER_SUPPORTED",
        PrimaryResponseState.CONFLICTING_EVIDENCE: "CONFLICTING_EVIDENCE",
        PrimaryResponseState.KNOWLEDGE_ABSENT: "KNOWLEDGE_ABSENT",
        PrimaryResponseState.AMBIGUOUS_QUERY: "CLARIFICATION_REQUIRED",
        PrimaryResponseState.PROCESSING_FAILED: "FAILED",
        PrimaryResponseState.CANCELLED: "FAILED",
    }.get(state.primary_state, "INSUFFICIENT_EVIDENCE")
    return {
        "outcome": outcome,
        "abstained": state.primary_state not in _SUPPORTED,
        "sufficient_evidence": state.primary_state in _SUPPORTED,
        "confidence_category": state.confidence.final.value.casefold().replace(
            "not_applicable", "none"
        ),
        "answer": state.answer or state.user_message,
    }


def _primary_state(
    outcome: str,
    diagnosis_status: str,
    run_status: str | None,
    *,
    has_answer: bool,
    has_citations: bool,
) -> PrimaryResponseState:
    if str(run_status or "").upper() in {"CANCELLED", "CANCELED"}:
        return PrimaryResponseState.CANCELLED
    if str(run_status or "").upper() in {"FAILED", "ERROR"} or outcome == "FAILED":
        return PrimaryResponseState.PROCESSING_FAILED
    diagnosis_mapping = {
        "RETRIEVAL_FAILURE_UNRESOLVED": PrimaryResponseState.RETRIEVAL_FAILURE,
        "KNOWLEDGE_ABSENT": PrimaryResponseState.KNOWLEDGE_ABSENT,
        "AMBIGUOUS_QUERY": PrimaryResponseState.AMBIGUOUS_QUERY,
        "CONFLICTING_EVIDENCE": PrimaryResponseState.CONFLICTING_EVIDENCE,
    }
    if (
        outcome in {"ANSWER_SUPPORTED", "ANSWER_PARTIALLY_SUPPORTED"}
        and has_answer
        and has_citations
        and diagnosis_status
        not in {
            "CONFLICTING_EVIDENCE",
            "AMBIGUOUS_QUERY",
            "RETRIEVAL_FAILURE_UNRESOLVED",
            "PARTIAL_EVIDENCE",
        }
    ):
        return PrimaryResponseState.SUPPORTED
    if diagnosis_status in diagnosis_mapping:
        return diagnosis_mapping[diagnosis_status]
    if (
        diagnosis_status in {"SUFFICIENT_EVIDENCE", "RETRIEVAL_FAILURE_RECOVERED"}
        and has_answer
        and has_citations
    ):
        return PrimaryResponseState.SUPPORTED
    return {
        "ANSWER_SUPPORTED": PrimaryResponseState.SUPPORTED,
        "CONFLICTING_EVIDENCE": PrimaryResponseState.CONFLICTING_EVIDENCE,
        "KNOWLEDGE_ABSENT": PrimaryResponseState.KNOWLEDGE_ABSENT,
        "CLARIFICATION_REQUIRED": PrimaryResponseState.AMBIGUOUS_QUERY,
        "LOW_QUALITY_SOURCE": PrimaryResponseState.LOW_QUALITY_SOURCE,
        "RETRIEVAL_FAILURE": PrimaryResponseState.RETRIEVAL_FAILURE,
        "FAILED": PrimaryResponseState.PROCESSING_FAILED,
    }.get(outcome, PrimaryResponseState.INSUFFICIENT_EVIDENCE)


def _evidence_decision(primary: PrimaryResponseState) -> EvidenceDecision:
    if primary in _SUPPORTED:
        return EvidenceDecision.SUFFICIENT
    if primary == PrimaryResponseState.CONFLICTING_EVIDENCE:
        return EvidenceDecision.CONFLICTING
    if primary == PrimaryResponseState.KNOWLEDGE_ABSENT:
        return EvidenceDecision.ABSENT
    if primary in {
        PrimaryResponseState.RETRIEVAL_FAILURE,
        PrimaryResponseState.PROCESSING_FAILED,
        PrimaryResponseState.CANCELLED,
    }:
        return EvidenceDecision.UNAVAILABLE
    return EvidenceDecision.PARTIAL


def _citation_identity(citations: list[dict[str, Any]]) -> tuple[list[str], dict[str, str]]:
    ids: list[str] = []
    documents: dict[str, str] = {}
    for index, citation in enumerate(citations, 1):
        base_id = str(
            citation.get("citation_id")
            or citation.get("citation_label")
            or citation.get("external_source_label")
            or citation.get("chunk_id")
            or f"C{index}"
        )
        citation_id = base_id
        duplicate_index = 2
        while citation_id in ids:
            citation_id = f"{base_id}:{duplicate_index}"
            duplicate_index += 1
        ids.append(citation_id)
        if citation.get("document_id"):
            documents[citation_id] = str(citation["document_id"])
    return ids, documents


def _claim_support(
    claims: list[dict[str, Any]],
    answer: str | None,
    citation_ids: list[str],
    citations: list[dict[str, Any]],
) -> list[ClaimSupport]:
    supported: list[ClaimSupport] = []
    for index, claim in enumerate(claims, 1):
        claim_citations = [
            str(item)
            for item in (
                claim.get("citation_ids")
                or claim.get("citations")
                or claim.get("supporting_evidence_ids")
                or []
            )
            if str(item) in citation_ids
        ]
        if not claim_citations and citation_ids:
            claim_citations = citation_ids[:1]
        text = str(claim.get("claim_text") or claim.get("text") or "").strip()
        if text and claim_citations:
            supported.append(
                ClaimSupport(
                    claim_id=str(claim.get("claim_id") or f"claim-{index}"),
                    text=text,
                    citation_ids=claim_citations,
                )
            )
    if not supported and answer and citation_ids:
        for index, citation_id in enumerate(citation_ids):
            citation = citations[index] if index < len(citations) else {}
            text = str(citation.get("supports_claim") or citation.get("excerpt") or answer).strip()
            supported.append(
                ClaimSupport(
                    claim_id=f"claim-{index + 1}",
                    text=text,
                    citation_ids=[citation_id],
                )
            )
    return supported


def _legacy_conflict(
    conflicts: list[dict[str, Any]],
    claims: list[ClaimSupport],
    citation_ids: list[str],
) -> ConflictResult:
    confirmed = next(
        (
            item
            for item in conflicts
            if str(item.get("status", "CONFIRMED_CONFLICT")).upper()
            in {"CONFIRMED_CONFLICT", "CONFLICTING_EVIDENCE"}
        ),
        None,
    )
    if not confirmed:
        return ConflictResult()
    category_name = str(
        confirmed.get("category") or confirmed.get("conflict_type") or "VALUE_CONFLICT"
    ).upper()
    aliases = {
        "NUMERIC_VALUE": "VALUE_CONFLICT",
        "DATE": "DATE_CONFLICT",
        "OWNER_ENTITY": "ROLE_CONFLICT",
    }
    category_name = aliases.get(category_name, category_name)
    category = (
        ConflictCategory(category_name)
        if category_name in ConflictCategory._value2member_map_
        else ConflictCategory.POLICY_RULE_CONFLICT
    )
    sides = [
        ConflictSide(claim_id=claim.claim_id, text=claim.text, citation_ids=claim.citation_ids)
        for claim in claims[:2]
    ]
    if len(sides) < 2 and citation_ids:
        values = confirmed.get("values") or ["Claim A", "Claim B"]
        sides = [
            ConflictSide(
                claim_id=f"conflict-{index + 1}",
                text=str(values[index] if index < len(values) else f"Claim {index + 1}"),
                citation_ids=[citation_ids[min(index, len(citation_ids) - 1)]],
            )
            for index in range(2)
        ]
    return ConflictResult(
        category=category,
        unresolved=True,
        material=True,
        sides=sides,
    )


def _confidence_band(value: str) -> ConfidenceBand:
    return {
        "high": ConfidenceBand.HIGH,
        "medium": ConfidenceBand.MEDIUM,
        "low": ConfidenceBand.LOW,
    }.get(str(value).casefold(), ConfidenceBand.NOT_APPLICABLE)


def _confidence_band_from_score(value: Any) -> ConfidenceBand:
    try:
        score = float(value)
    except (TypeError, ValueError):
        return ConfidenceBand.NOT_APPLICABLE
    if score >= 0.8:
        return ConfidenceBand.HIGH
    if score >= 0.55:
        return ConfidenceBand.MEDIUM
    return ConfidenceBand.LOW


def _user_message(
    primary: PrimaryResponseState,
    answer: str | None,
    *,
    legacy_message: str | None = None,
) -> str:
    if primary in _SUPPORTED and answer:
        return answer
    if legacy_message and primary not in {
        PrimaryResponseState.CONFLICTING_EVIDENCE,
        PrimaryResponseState.RETRIEVAL_FAILURE,
        PrimaryResponseState.PROCESSING_FAILED,
        PrimaryResponseState.CANCELLED,
    }:
        return legacy_message
    return {
        PrimaryResponseState.CONFLICTING_EVIDENCE: (
            "Authorized sources contain conflicting information."
        ),
        PrimaryResponseState.KNOWLEDGE_ABSENT: (
            "The requested information was not found in the selected authorized documents "
            "after bounded retrieval."
        ),
        PrimaryResponseState.RETRIEVAL_FAILURE: (
            "Reliable retrieval could not be completed. "
            "This does not mean the information is absent."
        ),
        PrimaryResponseState.AMBIGUOUS_QUERY: (
            "The query needs clarification before a reliable answer can be given."
        ),
        PrimaryResponseState.LOW_QUALITY_SOURCE: (
            "The available source quality is insufficient for a reliable answer."
        ),
        PrimaryResponseState.INSUFFICIENT_EVIDENCE: (
            "The available evidence is insufficient for a reliable answer."
        ),
        PrimaryResponseState.PROCESSING_FAILED: "The response could not be completed safely.",
        PrimaryResponseState.CANCELLED: (
            "The request was cancelled before a response was completed."
        ),
    }[primary]


def _attribute(text: str) -> str | None:
    patterns = (
        ("annual_revenue", r"\bannual revenue\b"),
        ("annual_budget", r"\bannual budget\b"),
        ("meal_allowance", r"\b(?:travel |domestic )?meal allowance\b"),
        (
            "travel_approval",
            r"\b(?:official )?travel (?:requests? )?(?:require|must|approve|approval)",
        ),
        ("procurement_approval", r"\bprocurement requests?\b"),
        ("finance_director", r"\bfinance director\b"),
        ("limit", r"\blimit\b"),
    )
    return next((name for name, pattern in patterns if re.search(pattern, text)), None)


def _subject(text: str, attribute: str | None) -> str | None:
    if attribute:
        return attribute.rsplit("_", 1)[0]
    return None


def _approval_role(text: str) -> str | None:
    role_match = re.search(
        r"\b((?:employee'?s?\s+)?department manager|finance director|operations director)\b",
        text,
        re.IGNORECASE,
    )
    if not role_match:
        return None
    return re.sub(r"^employee'?s?\s+", "", role_match.group(1).casefold())


def _decimal_string(value: str) -> str | None:
    try:
        normalized = Decimal(value.replace(",", ""))
    except InvalidOperation:
        return None
    return format(normalized.normalize(), "f")


def _string_or_none(value: Any) -> str | None:
    return str(value) if value is not None else None
