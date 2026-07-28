"""Bounded local cross-encoder reranking with deterministic safe fallback."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from functools import lru_cache

from app.core.config import LocalInferenceProvider, settings
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
                    local_files_only=settings.is_production,
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


async def rerank(query: str, contents: list[str], fused_scores: list[float]) -> RerankResult:
    if not settings.reranker_enabled:
        scores = [
            rerank_score(query, content, score)
            for content, score in zip(contents, fused_scores, strict=True)
        ]
        return RerankResult(scores, False, False, "lexical-calibrator-v1")
    if settings.reranker_provider is LocalInferenceProvider.DETERMINISTIC:
        scores = [
            rerank_score(query, content, score)
            for content, score in zip(contents, fused_scores, strict=True)
        ]
        return RerankResult(scores, True, False, "deterministic-reranker-v1")
    try:
        model = configured_reranker()
        if model is None:
            raise RuntimeError("Configured reranker is unavailable")
        scores = await model.score(query, contents)
        return RerankResult(scores, True, False, model.version)
    except (RuntimeError, TimeoutError, ValueError):
        if not settings.reranker_fallback_enabled:
            raise
        return RerankResult(fused_scores, False, True, "fused-fallback-v1")


def _minmax(values: list[float]) -> list[float]:
    if not values:
        return []
    low, high = min(values), max(values)
    if high == low:
        return [0.5 for _ in values]
    return [(value - low) / (high - low) for value in values]
