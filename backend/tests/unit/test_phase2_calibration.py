from app.rag.evidence import SupportStatus, assess_evidence_support
from app.rag.evidence_sufficiency import SufficiencyDecision, assess_sufficiency
from app.rag.query_intent import QueryIntent, classify_query_intent


def test_query_intents_are_deterministic():
    assert classify_query_intent("Define a mathematical function") is QueryIntent.DEFINITION
    assert classify_query_intent("Compare leave and lodging limits") is QueryIntent.COMPARISON
    assert classify_query_intent("List the policy topics") is QueryIntent.LIST
    assert classify_query_intent("What was annual revenue?") is QueryIntent.KNOWLEDGE_ABSENCE_PROBE
    assert classify_query_intent("status") is QueryIntent.AMBIGUOUS


def test_revenue_is_not_supported_by_budget():
    support = assess_evidence_support(
        [0.95],
        "What was the annual revenue?",
        ["Annual Budget: PKR 8,000,000."],
    )
    assert support.status is not SupportStatus.SUPPORTED
    decision = assess_sufficiency(
        intent=QueryIntent.KNOWLEDGE_ABSENCE_PROBE,
        support=support,
        candidate_count=1,
        retry_performed=True,
    )
    assert decision.decision is SufficiencyDecision.KNOWLEDGE_ABSENT


def test_low_quality_and_incomplete_composite_are_not_sufficient():
    support = assess_evidence_support(
        [0.9],
        "What is the budget?",
        ["Budget: PKR 500,000."],
    )
    low_quality = assess_sufficiency(
        intent=QueryIntent.FACT,
        support=support,
        candidate_count=1,
        retry_performed=True,
        low_quality=True,
    )
    assert low_quality.decision is SufficiencyDecision.LOW_QUALITY_SOURCE
    incomplete = assess_sufficiency(
        intent=QueryIntent.COMPARISON,
        support=support,
        candidate_count=1,
        retry_performed=True,
    )
    assert incomplete.decision is SufficiencyDecision.RETRIEVAL_FAILURE_UNRESOLVED
