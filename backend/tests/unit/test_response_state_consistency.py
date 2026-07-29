from __future__ import annotations

from app.rag.response_state import (
    CanonicalResponseState,
    ClaimSupport,
    ConfidenceBand,
    ConfidenceComponents,
    ConflictCategory,
    ConflictResult,
    ConflictSide,
    EvidenceDecision,
    PrimaryResponseState,
    RetrievalState,
    ScopeState,
    classify_claim_conflict,
    normalize_claim,
    response_state_from_legacy,
    safe_response_state,
    validate_response_state,
)


def _supported_state(**updates) -> CanonicalResponseState:
    values = {
        "primary_state": PrimaryResponseState.SUPPORTED,
        "answer": "Ayesha Khan",
        "claims": [ClaimSupport(claim_id="claim-1", text="Ayesha Khan", citation_ids=["c1"])],
        "citation_ids": ["c1"],
        "citation_document_ids": {"c1": "doc-a"},
        "evidence_decision": EvidenceDecision.SUFFICIENT,
        "confidence": ConfidenceComponents(
            retrieval=ConfidenceBand.HIGH,
            evidence_support=ConfidenceBand.HIGH,
            final=ConfidenceBand.HIGH,
        ),
        "retrieval": RetrievalState(mode="lexical"),
        "scope": ScopeState(),
        "user_message": "Ayesha Khan",
    }
    values.update(updates)
    return CanonicalResponseState(**values)


def test_supported_fact_has_one_terminal_state_and_claim_citation() -> None:
    state = _supported_state()

    assert state.primary_state == PrimaryResponseState.SUPPORTED
    assert state.claims[0].citation_ids == ["c1"]
    assert validate_response_state(state) == []


def test_equivalent_wording_is_not_a_conflict() -> None:
    left = normalize_claim(
        "Travel requests require approval from the department manager.",
        claim_id="a",
        citation_ids=["ca"],
    )
    right = normalize_claim(
        "The employee's department manager must approve official travel.",
        claim_id="b",
        citation_ids=["cb"],
    )

    assert classify_claim_conflict(left, right).category == ConflictCategory.NO_CONFLICT


def test_equivalent_currency_and_unit_wording_is_not_a_conflict() -> None:
    left = normalize_claim(
        "Meal allowance is PKR 5,000 per day.", claim_id="a", citation_ids=["ca"]
    )
    right = normalize_claim("Meal allowance is 5,000 PKR daily.", claim_id="b", citation_ids=["cb"])

    assert left.value == right.value == "5000"
    assert left.unit == right.unit == "per_day"
    assert classify_claim_conflict(left, right).category == ConflictCategory.NO_CONFLICT


def test_true_value_conflict_has_two_cited_sides() -> None:
    left = normalize_claim(
        "Travel meal allowance is PKR 5,000 per day.",
        claim_id="a",
        citation_ids=["ca"],
    )
    right = normalize_claim(
        "Travel meal allowance is PKR 6,000 per day.",
        claim_id="b",
        citation_ids=["cb"],
    )

    conflict = classify_claim_conflict(left, right)

    assert conflict.category == ConflictCategory.VALUE_CONFLICT
    assert conflict.unresolved is True
    assert [side.citation_ids for side in conflict.sides] == [["ca"], ["cb"]]


def test_role_conflict_is_typed() -> None:
    left = normalize_claim(
        "Procurement requests are approved by the Finance Director.",
        claim_id="a",
        citation_ids=["ca"],
    )
    right = normalize_claim(
        "Procurement requests are approved by the Operations Director.",
        claim_id="b",
        citation_ids=["cb"],
    )

    assert classify_claim_conflict(left, right).category == ConflictCategory.ROLE_CONFLICT


def test_current_version_resolves_superseded_value() -> None:
    old = normalize_claim(
        "Meal allowance is PKR 4,000.",
        claim_id="old",
        citation_ids=["cold"],
        metadata={"document_status": "superseded"},
    )
    current = normalize_claim(
        "Meal allowance is PKR 5,000.",
        claim_id="current",
        citation_ids=["ccurrent"],
        metadata={"document_status": "current"},
    )

    conflict = classify_claim_conflict(old, current)

    assert conflict.category == ConflictCategory.NO_CONFLICT
    assert conflict.unresolved is False
    assert "current" in (conflict.resolution or "")


def test_different_attributes_do_not_conflict() -> None:
    budget = normalize_claim("Annual budget is PKR 5,000.", claim_id="budget", citation_ids=["cb"])
    revenue = normalize_claim(
        "Annual revenue is PKR 6,000.", claim_id="revenue", citation_ids=["cr"]
    )

    assert budget.attribute != revenue.attribute
    assert classify_claim_conflict(budget, revenue).category == ConflictCategory.NO_CONFLICT


def test_retrieval_failure_is_not_mapped_to_knowledge_absence() -> None:
    state = response_state_from_legacy(
        answer=None,
        outcome="INSUFFICIENT_EVIDENCE",
        citations=[],
        retrieval_diagnosis={"status": "RETRIEVAL_FAILURE_UNRESOLVED"},
    )

    assert state.primary_state == PrimaryResponseState.RETRIEVAL_FAILURE
    assert state.evidence_decision == EvidenceDecision.UNAVAILABLE
    assert state.retrieval.failure_category == "retrieval_unavailable"


def test_knowledge_absence_returns_no_answer_or_citation() -> None:
    state = response_state_from_legacy(
        answer="Annual budget is PKR 5,000.",
        outcome="KNOWLEDGE_ABSENT",
        citations=[{"chunk_id": "c1", "document_id": "doc-a"}],
        retrieval_diagnosis={"status": "KNOWLEDGE_ABSENT"},
    )

    assert state.primary_state == PrimaryResponseState.KNOWLEDGE_ABSENT
    assert state.answer is None
    assert state.citation_ids == []


def test_composite_requires_multiple_individually_cited_claims() -> None:
    state = _supported_state(
        primary_state=PrimaryResponseState.SUPPORTED_COMPOSITE,
        answer="Allowance: PKR 5,000. Approver: Finance Director.",
        claims=[
            ClaimSupport(claim_id="allowance", text="PKR 5,000", citation_ids=["c1"]),
            ClaimSupport(claim_id="approver", text="Finance Director", citation_ids=["c2"]),
        ],
        citation_ids=["c1", "c2"],
    )

    assert validate_response_state(state) == []


def test_composite_preserves_two_focused_spans_from_one_chunk() -> None:
    state = response_state_from_legacy(
        answer="Launched in March 2025; owned by Operations Analytics.",
        outcome="ANSWER_SUPPORTED",
        citations=[
            {
                "chunk_id": "shared-chunk",
                "document_id": "doc-a",
                "excerpt": "Project Atlas launched in March 2025.",
            },
            {
                "chunk_id": "shared-chunk",
                "document_id": "doc-a",
                "excerpt": "Operations Analytics owns Project Atlas.",
            },
        ],
        confidence_category="high",
        retrieval_diagnosis={
            "status": "SUFFICIENT_EVIDENCE",
            "sufficiency_decision": "SUFFICIENT_COMPOSITE",
        },
    )

    assert state.primary_state == PrimaryResponseState.SUPPORTED_COMPOSITE
    assert state.citation_ids == ["shared-chunk", "shared-chunk:2"]
    assert len(state.claims) == 2


def test_invalid_state_matrix_fails_closed() -> None:
    base = dict(_supported_state().__dict__)
    invalid_cases = [
        {"citation_ids": [], "claims": []},
        {
            "conflict": ConflictResult(
                category=ConflictCategory.VALUE_CONFLICT,
                unresolved=True,
                material=True,
                sides=[
                    ConflictSide(claim_id="a", text="1", citation_ids=["c1"]),
                    ConflictSide(claim_id="b", text="2", citation_ids=["c2"]),
                ],
            )
        },
        {
            "primary_state": PrimaryResponseState.KNOWLEDGE_ABSENT,
            "evidence_decision": EvidenceDecision.ABSENT,
        },
        {
            "primary_state": PrimaryResponseState.AMBIGUOUS_QUERY,
            "answer": None,
            "claims": [],
            "citation_ids": [],
            "evidence_decision": EvidenceDecision.PARTIAL,
            "confidence": ConfidenceComponents(final=ConfidenceBand.HIGH),
        },
        {
            "scope": ScopeState(
                selected_document_scope=True,
                authorized_document_ids=["doc-b"],
            )
        },
        {
            "primary_state": PrimaryResponseState.SUPPORTED_COMPOSITE,
            "claims": [ClaimSupport(claim_id="only", text="one side", citation_ids=["c1"])],
        },
        {
            "retrieval": RetrievalState(
                semantic_applied=True,
                lexical_fallback_used=True,
            )
        },
        {
            "primary_state": PrimaryResponseState.CANCELLED,
            "evidence_decision": EvidenceDecision.UNAVAILABLE,
        },
    ]

    for update in invalid_cases:
        raw = {**base, **update}
        unsafe = CanonicalResponseState.model_construct(**raw)
        assert validate_response_state(unsafe)
        safe = safe_response_state(**raw)
        assert safe.primary_state == PrimaryResponseState.PROCESSING_FAILED
        assert safe.answer is None
