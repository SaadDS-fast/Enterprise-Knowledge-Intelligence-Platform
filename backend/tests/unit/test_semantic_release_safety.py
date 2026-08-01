import pytest

from app.core.config import LocalInferenceProvider
from app.rag.evidence import SupportStatus, assess_evidence_support
from app.rag.evidence_sufficiency import SufficiencyDecision, assess_sufficiency
from app.rag.query_intent import QueryIntent
from app.rag.reranker_provider import rerank


def test_semantic_similarity_is_not_factual_support_for_absent_revenue():
    support = assess_evidence_support(
        [0.99, 0.91],
        "What was the company's annual revenue?",
        [
            "The annual leave policy covers employee benefits.",
            "The capital expenditure budget is PKR 500,000.",
        ],
    )

    assert support.status is not SupportStatus.SUPPORTED
    decision = assess_sufficiency(
        intent=QueryIntent.KNOWLEDGE_ABSENCE_PROBE,
        support=support,
        candidate_count=2,
        retry_performed=True,
    )
    assert decision.decision is SufficiencyDecision.KNOWLEDGE_ABSENT
    assert decision.sufficient is False


@pytest.mark.asyncio
async def test_local_reranker_blends_once_and_preserves_unique_complete_support(monkeypatch):
    class FixedReranker:
        version = "test-reranker"

        async def score(self, query, contents):
            return [0.31, 1.0]

    monkeypatch.setattr("app.rag.reranker_provider.settings.reranker_enabled", True)
    monkeypatch.setattr(
        "app.rag.reranker_provider.settings.reranker_provider",
        LocalInferenceProvider.LOCAL,
    )
    monkeypatch.setattr("app.rag.reranker_provider.settings.reranker_blend_weight", 0.25)
    monkeypatch.setattr("app.rag.reranker_provider.settings.reranker_min_margin", 0.08)
    monkeypatch.setattr("app.rag.reranker_provider.configured_reranker", lambda: FixedReranker())

    result = await rerank(
        "Which question concerns deformation of a material under force?",
        [
            "A composite wire extends under an applied load. Calculate its extension.",
            "A particle has displacement s(t). Determine its velocity.",
        ],
        [0.82, 0.42],
    )

    assert result.policy == "blended"
    assert result.scores == pytest.approx([0.6925, 0.565])
    assert result.scores[0] > result.scores[1]


@pytest.mark.asyncio
async def test_low_margin_reranker_cannot_replace_fused_order(monkeypatch):
    class LowMarginReranker:
        version = "test-reranker"

        async def score(self, query, contents):
            return [0.49, 0.51]

    monkeypatch.setattr("app.rag.reranker_provider.settings.reranker_enabled", True)
    monkeypatch.setattr(
        "app.rag.reranker_provider.settings.reranker_provider",
        LocalInferenceProvider.LOCAL,
    )
    monkeypatch.setattr("app.rag.reranker_provider.settings.reranker_min_margin", 0.08)
    monkeypatch.setattr(
        "app.rag.reranker_provider.configured_reranker", lambda: LowMarginReranker()
    )

    result = await rerank("query", ["complete", "related"], [0.8, 0.4])

    assert result.policy == "low_margin_fused"
    assert result.scores == [0.8, 0.4]
