import math

import pytest

from app.rag.semantic_provider import (
    DETERMINISTIC_VERSION,
    DeterministicEmbeddingProvider,
    LocalSentenceTransformerProvider,
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


def test_local_model_dimension_must_match_index(monkeypatch):
    monkeypatch.setattr("app.rag.semantic_provider.settings.semantic_embedding_dimension", 768)
    with pytest.raises(ValueError, match="dimension"):
        LocalSentenceTransformerProvider("all-minilm-l6-v2")
