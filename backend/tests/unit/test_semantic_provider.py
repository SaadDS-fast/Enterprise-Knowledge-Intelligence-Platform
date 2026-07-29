import math

import pytest

from app.rag.semantic_provider import (
    DETERMINISTIC_VERSION,
    DeterministicEmbeddingProvider,
    LocalSentenceTransformerProvider,
    embed_with_fallback,
    embedding_metadata_is_current,
)


@pytest.mark.asyncio
async def test_deterministic_provider_batches_normalized_versioned_embeddings():
    provider = DeterministicEmbeddingProvider()
    vectors = await provider.embed(["meal allowance", "function definition"])
    assert len(vectors) == 2
    assert all(len(vector) == 384 for vector in vectors)
    assert all(
        math.isclose(math.sqrt(sum(value * value for value in vector)), 1.0) for vector in vectors
    )
    assert provider.identity.version == DETERMINISTIC_VERSION
    metadata = provider.identity.metadata(indexing_version="2.0")
    assert metadata["embedding_provider"] == "deterministic"
    assert metadata["embedding_dimension"] == 384
    assert metadata["indexing_version"] == "2.0"
    assert metadata["embedding_created_at"]


def test_local_model_allowlist_rejects_operator_typo():
    with pytest.raises(ValueError, match="allowlist"):
        LocalSentenceTransformerProvider("../../untrusted-model")


def test_stronger_local_model_is_explicitly_allowlisted():
    provider = LocalSentenceTransformerProvider("bge-small-en-v1.5")
    assert provider.model_id == "BAAI/bge-small-en-v1.5"
    assert provider.identity.dimension == 384


def test_local_model_dimension_must_match_index(monkeypatch):
    monkeypatch.setattr("app.rag.semantic_provider.settings.semantic_embedding_dimension", 768)
    with pytest.raises(ValueError, match="dimension"):
        LocalSentenceTransformerProvider("all-minilm-l6-v2")


def test_obsolete_embedding_metadata_is_detected():
    current = DeterministicEmbeddingProvider().identity
    assert embedding_metadata_is_current(
        {
            "embedding_provider": current.provider,
            "embedding_model": current.model_alias,
            "embedding_dimension": current.dimension,
            "embedding_version": current.version,
        }
    )
    assert not embedding_metadata_is_current(
        {
            "embedding_provider": "local",
            "embedding_model": "all-minilm-l6-v2",
            "embedding_dimension": 384,
            "embedding_version": "st-v1",
        }
    )


@pytest.mark.asyncio
async def test_embedding_timeout_uses_deterministic_fallback(monkeypatch):
    class TimedOutProvider:
        identity = DeterministicEmbeddingProvider().identity

        async def embed(self, texts):
            raise TimeoutError

    monkeypatch.setattr(
        "app.rag.semantic_provider.configured_embedding_provider",
        lambda: TimedOutProvider(),
    )
    vectors, provider, fallback_used = await embed_with_fallback(["bounded query"])
    assert len(vectors) == 1
    assert provider.identity.version == DETERMINISTIC_VERSION
    assert fallback_used is True
