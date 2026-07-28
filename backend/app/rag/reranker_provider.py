"""Bounded local cross-encoder reranking with deterministic safe fallback."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from functools import lru_cache

from app.core.config import LocalInferenceProvider, settings
from app.rag.query_intent import QueryIntent
from app.rag.reranker import rerank_score

ALLOWED_RERANKERS: dict[str, tuple[str, str]] = {
    "ms-marco-minilm-l-6-v2": ("cross-encoder/ms-marco-MiniLM-L-6-v2", "ce-v1"),
}


@dataclass(frozen=True, slots=True)
class RerankResult:
    scores: list[float]
    used: bool
    fallback_used: bool
    version: str
    policy: str


class LocalCrossEncoder:
    def __init__(self, alias: str) -> None:
        if alias not in ALLOWED_RERANKERS:
            raise ValueError("Reranker model is not in the operator allowlist")
        self.alias = alias
        self.model_id, self.version = ALLOWED_RERANKERS[alias]
        self._model = None

    def _load(self):
        if self._model is None:
            try:
                from sentence_transformers import CrossEncoder

                self._model = CrossEncoder(
                    self.model_id,
                    device="cpu",
                    max_length=settings.reranker_max_length,
                    local_files_only=True,
                )
            except Exception as exc:
                raise RuntimeError("Local reranker model is unavailable") from exc
        return self._model

    async def score(self, query: str, contents: list[str]) -> list[float]:
        pairs = [(query, content[: settings.reranker_max_length * 8]) for content in contents]
        values = await asyncio.wait_for(
            asyncio.to_thread(
                self._load().predict,
                pairs,
                batch_size=settings.reranker_batch_size,
                show_progress_bar=False,
            ),
            timeout=settings.reranker_timeout_seconds,
        )
        raw = [float(value) for value in values]
        return _minmax(raw)


@lru_cache(maxsize=1)
def configured_reranker() -> LocalCrossEncoder | None:
    if not settings.reranker_enabled:
        return None
    if settings.reranker_provider is LocalInferenceProvider.DETERMINISTIC:
        return None
    return LocalCrossEncoder(settings.reranker_model.strip().lower())


async def rerank(
    query: str,
    contents: list[str],
    fused_scores: list[float],
    intent: QueryIntent = QueryIntent.FACT,
) -> RerankResult:
    if not settings.reranker_enabled:
        scores = [
            rerank_score(query, content, score)
            for content, score in zip(contents, fused_scores, strict=True)
        ]
        return RerankResult(scores, False, False, "lexical-calibrator-v1", "disabled")
    if settings.reranker_provider is LocalInferenceProvider.DETERMINISTIC:
        scores = [
            rerank_score(query, content, score)
            for content, score in zip(contents, fused_scores, strict=True)
        ]
        return RerankResult(scores, True, False, "deterministic-reranker-v1", "deterministic")
    if intent in {QueryIntent.AMBIGUOUS, QueryIntent.KNOWLEDGE_ABSENCE_PROBE}:
        return RerankResult(fused_scores, False, False, "fused-policy-v1", "intent_skipped")
    try:
        model = configured_reranker()
        if model is None:
            raise RuntimeError("Configured reranker is unavailable")
        scores = await model.score(query, contents)
        if len(scores) > 1:
            ordered = sorted(scores, reverse=True)
            if ordered[0] - ordered[1] < settings.reranker_min_margin:
                return RerankResult(fused_scores, False, True, model.version, "low_margin_fused")
        weight = settings.reranker_blend_weight
        blended = [
            (1.0 - weight) * fused + weight * cross
            for fused, cross in zip(fused_scores, scores, strict=True)
        ]
        return RerankResult(blended, True, False, model.version, "blended")
    except (RuntimeError, TimeoutError, ValueError):
        if not settings.reranker_fallback_enabled:
            raise
        return RerankResult(fused_scores, False, True, "fused-fallback-v1", "unavailable_fused")


def _minmax(values: list[float]) -> list[float]:
    if not values:
        return []
    low, high = min(values), max(values)
    if high == low:
        return [0.5 for _ in values]
    return [(value - low) / (high - low) for value in values]
