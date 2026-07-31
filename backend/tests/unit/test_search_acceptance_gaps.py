from uuid import uuid4

from app.llm.answer_plan import build_answer_plan
from app.llm.grounded import build_evidence_packet
from app.models.domain import RetrievedEvidence
from app.rag.evidence import RequestedAttribute, SupportStatus, assess_evidence_support
from app.rag.evidence_diagnosis import has_conflicting_signals
from app.rag.evidence_sufficiency import SufficiencyDecision, assess_sufficiency
from app.rag.query_intent import QueryIntent, classify_query_intent


def test_supported_definition_preserves_unicode_equation_and_condition():
    content = (
        "Topic: Quadratic Equations\nDefinition:\n"
        "A quadratic equation has the form ax² + bx + c = 0, where a is not zero."
    )

    support = assess_evidence_support([0.99], "What is a quadratic equation?", [content])

    assert support.status is SupportStatus.SUPPORTED
    assert support.attribute is RequestedAttribute.DEFINITION
    assert support.answer_value == (
        "A quadratic equation has the form ax² + bx + c = 0, where a is not zero"
    )
    assert "ax² + bx + c = 0" in support.facts[0].matched_text
    assert "a is not zero" in support.facts[0].matched_text

    evidence = [
        RetrievedEvidence(
            chunk_id=uuid4(),
            document_id=uuid4(),
            document_title="Quadratic Equations",
            content=part,
            score=0.99,
            metadata={},
        )
        for part in ("Topic: Quadratic Equations", support.facts[0].matched_text)
    ]
    assert not has_conflicting_signals("What is a quadratic equation?", evidence)


def test_supported_negated_obligation_has_a_claim_linked_fact():
    support = assess_evidence_support(
        [0.99],
        "What is prohibited?",
        ["Employees must not exceed the approved travel limit."],
    )

    assert classify_query_intent("What is prohibited?") is QueryIntent.FACT
    assert support.status is SupportStatus.SUPPORTED
    assert support.facts[0].attribute is RequestedAttribute.OBLIGATION
    assert support.facts[0].matched_text == ("Employees must not exceed the approved travel limit.")


def test_single_source_owner_effective_date_is_complete_typed_support():
    query = "Who owns the policy and when does it become effective?"
    content = (
        "Policy Owner:\nThe policy owner is Ayesha Khan.\n"
        "Effective Date:\nThe policy is effective from 1 February 2026."
    )
    support = assess_evidence_support([0.99], query, [content])
    sufficiency = assess_sufficiency(
        intent=classify_query_intent(query),
        support=support,
        candidate_count=1,
        retry_performed=False,
    )

    assert support.status is SupportStatus.SUPPORTED
    assert {(fact.attribute, fact.value) for fact in support.facts} == {
        (RequestedAttribute.OWNER, "Ayesha Khan"),
        (RequestedAttribute.DATE, "1 February 2026"),
    }
    assert sufficiency.decision is SufficiencyDecision.SUFFICIENT_COMPOSITE


def test_owner_date_answer_plan_has_two_components_and_effective_date_fact():
    query = "Who owns the policy and when does it become effective?"
    evidence = RetrievedEvidence(
        chunk_id=uuid4(),
        document_id=uuid4(),
        document_title="Policy",
        content=(
            "Policy Owner:\nThe policy owner is Ayesha Khan.\n"
            "Effective Date:\nThe policy is effective from 1 February 2026."
        ),
        score=0.99,
        metadata={"section": "Policy details"},
    )
    plan = build_answer_plan(query, build_evidence_packet([evidence]))

    assert plan.query_intent == "multi_component"
    assert [component.text for component in plan.components] == [
        "The policy owner is Ayesha Khan.",
        "The policy is effective from 1 February 2026.",
    ]
    effective_date = next(fact for fact in plan.facts if fact.date_type == "effective")
    assert effective_date.text == "1 February 2026"
    assert plan.composite is False


def test_comparison_still_requires_two_distinct_sources():
    query = "Who owns the policy and when does it become effective?"
    support = assess_evidence_support(
        [0.99],
        query,
        [
            "Policy Owner:\nThe policy owner is Ayesha Khan.\n"
            "Effective Date:\nThe policy is effective from 1 February 2026."
        ],
    )
    sufficiency = assess_sufficiency(
        intent=QueryIntent.COMPARISON,
        support=support,
        candidate_count=1,
        retry_performed=True,
    )

    assert support.status is SupportStatus.SUPPORTED
    assert {fact.source_index for fact in support.facts} == {0}
    assert sufficiency.sufficient is False
    assert sufficiency.reason == "incomplete_composite"
