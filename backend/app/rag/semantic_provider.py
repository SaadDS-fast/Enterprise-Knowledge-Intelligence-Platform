"""Bounded, operator-configured local sentence embedding providers."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime
from functools import lru_cache
from typing import Protocol

from app.core.config import LocalInferenceProvider, settings
from app.rag.embeddings import embed_text

ALLOWED_MODELS: dict[str, tuple[str, int, str]] = {
    "all-minilm-l6-v2": ("sentence-transformers/all-MiniLM-L6-v2", 384, "st-v1"),
    "multi-qa-minilm-l6-cos-v1": (
        "sentence-transformers/multi-qa-MiniLM-L6-cos-v1",
        384,
        "st-v1",
    ),
    "bge-small-en-v1.5": ("BAAI/bge-small-en-v1.5", 384, "bge-v1.5"),
}
DETERMINISTIC_VERSION = "deterministic-hash-v1"


@dataclass(frozen=True, slots=True)
class EmbeddingIdentity:
    provider: str
    model_alias: str
    dimension: int
    version: str

    def metadata(self, *, indexing_version: str) -> dict[str, str | int]:
        return {
            "embedding_provider": self.provider,
            "embedding_model": self.model_alias,
            "embedding_dimension": self.dimension,
            "embedding_version": self.version,
            "indexing_version": indexing_version,
            "embedding_created_at": datetime.now(UTC).isoformat(),
        }


@dataclass(frozen=True, slots=True)
class ProviderStatus:
    enabled: bool
    ready: bool
    provider: str
    model_alias: str
    version: str
    detail: str


class SentenceEmbeddingProvider(Protocol):
    @property
    def identity(self) -> EmbeddingIdentity: ...

    async def embed(self, texts: list[str]) -> list[list[float]]: ...

    def status(self) -> ProviderStatus: ...


class DeterministicEmbeddingProvider:
    def __init__(self, *, fallback: bool = False) -> None:
        self.fallback = fallback
        self._identity = EmbeddingIdentity(
            provider="deterministic",
            model_alias="blake2b-token-hash",
            dimension=settings.embedding_dimension,
            version=DETERMINISTIC_VERSION,
        )

    @property
    def identity(self) -> EmbeddingIdentity:
        return self._identity

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [embed_text(_bounded_text(text), self.identity.dimension) for text in texts]

    def status(self) -> ProviderStatus:
        return ProviderStatus(
            enabled=True,
            ready=True,
            provider=self.identity.provider,
            model_alias=self.identity.model_alias,
            version=self.identity.version,
            detail="deterministic fallback" if self.fallback else "deterministic test provider",
        )


class LocalSentenceTransformerProvider:
    def __init__(self, alias: str) -> None:
        if alias not in ALLOWED_MODELS:
            raise ValueError("Semantic embedding model is not in the operator allowlist")
        model_id, dimension, version = ALLOWED_MODELS[alias]
        if dimension != settings.semantic_embedding_dimension:
            raise ValueError("Configured semantic embedding dimension does not match model")
        if dimension != settings.embedding_dimension:
            raise ValueError("Semantic model dimension is incompatible with the chunk index")
        self.alias = alias
        self.model_id = model_id
        self._identity = EmbeddingIdentity("local", alias, dimension, version)
        self._model = None
        self._load_error: str | None = None

    @property
    def identity(self) -> EmbeddingIdentity:
        return self._identity

    def _load(self):
        if self._model is not None:
            return self._model
        try:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(
                self.model_id,
                device="cpu",
                local_files_only=True,
            )
            self._model.max_seq_length = settings.semantic_embedding_max_length
            return self._model
        except Exception as exc:
            self._load_error = type(exc).__name__
            raise RuntimeError("Local semantic embedding model is unavailable") from exc

    async def embed(self, texts: list[str]) -> list[list[float]]:
        bounded = [_bounded_text(text) for text in texts]
        output: list[list[float]] = []
        for start in range(0, len(bounded), settings.semantic_embedding_batch_size):
            batch = bounded[start : start + settings.semantic_embedding_batch_size]
            encoded = await asyncio.wait_for(
                asyncio.to_thread(
                    self._load().encode,
                    batch,
                    batch_size=settings.semantic_embedding_batch_size,
                    normalize_embeddings=settings.semantic_embedding_normalize,
                    show_progress_bar=False,
                ),
                timeout=settings.semantic_embedding_timeout_seconds,
            )
            output.extend(row.tolist() for row in encoded)
        return output

    def status(self) -> ProviderStatus:
        return ProviderStatus(
            enabled=True,
            ready=self._model is not None and self._load_error is None,
            provider="local",
            model_alias=self.alias,
            version=self.identity.version,
            detail=(
                "ready" if self._model is not None else (self._load_error or "lazy-load pending")
            ),
        )


def _bounded_text(text: str) -> str:
    # A character bound is enforced before the tokenizer's model-specific token bound.
    return " ".join(text.split())[: settings.semantic_embedding_max_length * 8]


def embedding_metadata_is_current(metadata: dict | None) -> bool:
    values = metadata or {}
    identity = configured_embedding_provider().identity
    return (
        values.get("embedding_provider") == identity.provider
        and values.get("embedding_model") == identity.model_alias
        and values.get("embedding_dimension") == identity.dimension
        and values.get("embedding_version") == identity.version
    )


@lru_cache(maxsize=1)
def configured_embedding_provider() -> SentenceEmbeddingProvider:
    if settings.semantic_embedding_provider is LocalInferenceProvider.DETERMINISTIC:
        return DeterministicEmbeddingProvider()
    if not settings.semantic_embeddings_enabled:
        return DeterministicEmbeddingProvider(fallback=True)
    try:
        return LocalSentenceTransformerProvider(settings.semantic_embedding_model.strip().lower())
    except (ValueError, RuntimeError):
        if settings.semantic_embedding_fallback_enabled:
            return DeterministicEmbeddingProvider(fallback=True)
        raise


async def embed_with_fallback(
    texts: list[str],
) -> tuple[list[list[float]], SentenceEmbeddingProvider, bool]:
    provider = configured_embedding_provider()
    for attempt in range(settings.semantic_embedding_max_retries + 1):
        try:
            return (
                await provider.embed(texts),
                provider,
                isinstance(provider, DeterministicEmbeddingProvider) and provider.fallback,
            )
        except (RuntimeError, TimeoutError):
            if attempt < settings.semantic_embedding_max_retries:
                await asyncio.sleep(0.05 * (attempt + 1))
    if not settings.semantic_embedding_fallback_enabled:
        raise RuntimeError("Semantic embedding failed and fallback is disabled")
    fallback = DeterministicEmbeddingProvider(fallback=True)
    return await fallback.embed(texts), fallback, True
