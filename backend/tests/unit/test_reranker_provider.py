import pytest

from app.core.config import LocalInferenceProvider
from app.rag.reranker_provider import rerank


@pytest.mark.asyncio
async def test_reranker_disabled_uses_legacy_lexical_calibrator(monkeypatch):
    monkeypatch.setattr("app.rag.reranker_provider.settings.reranker_enabled", False)
    result = await rerank("query", ["first", "second"], [0.9, 0.2])
    assert result.scores[0] > result.scores[1]
    assert result.used is False
    assert result.fallback_used is False


@pytest.mark.asyncio
async def test_deterministic_reranker_is_available_for_normal_tests(monkeypatch):
    monkeypatch.setattr("app.rag.reranker_provider.settings.reranker_enabled", True)
    monkeypatch.setattr(
        "app.rag.reranker_provider.settings.reranker_provider",
        LocalInferenceProvider.DETERMINISTIC,
    )
    result = await rerank("meal allowance", ["unrelated", "meal allowance PKR 5,000"], [0.5, 0.5])
    assert result.used is True
    assert result.scores[1] > result.scores[0]
    assert result.version == "deterministic-reranker-v1"


@pytest.mark.asyncio
async def test_local_reranker_timeout_falls_back_to_fused_scores(monkeypatch):
    class TimedOutReranker:
        version = "test"

        async def score(self, query, contents):
            raise TimeoutError

    monkeypatch.setattr("app.rag.reranker_provider.settings.reranker_enabled", True)
    monkeypatch.setattr(
        "app.rag.reranker_provider.settings.reranker_provider", LocalInferenceProvider.LOCAL
    )
    monkeypatch.setattr("app.rag.reranker_provider.configured_reranker", lambda: TimedOutReranker())
    result = await rerank("query", ["first", "second"], [0.8, 0.3])
    assert result.scores == [0.8, 0.3]
    assert result.used is False
    assert result.fallback_used is True
