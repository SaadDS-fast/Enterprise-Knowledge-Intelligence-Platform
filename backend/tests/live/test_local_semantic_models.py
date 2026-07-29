"""Opt-in checks for operator-provisioned models; never downloads model data."""

import os

import pytest

from app.rag.reranker_provider import LocalCrossEncoder
from app.rag.semantic_provider import LocalSentenceTransformerProvider

pytestmark = pytest.mark.skipif(
    os.getenv("EKIP_LIVE_SEMANTIC_MODELS") != "1",
    reason="operator-provisioned live semantic models are not enabled",
)


@pytest.mark.asyncio
async def test_provisioned_embedding_model():
    provider = LocalSentenceTransformerProvider(
        os.getenv("SEMANTIC_EMBEDDING_MODEL", "all-minilm-l6-v2")
    )
    vectors = await provider.embed(["meal allowance", "function definition"])
    assert len(vectors) == 2
    assert all(len(vector) == provider.identity.dimension for vector in vectors)


@pytest.mark.asyncio
async def test_provisioned_cross_encoder():
    provider = LocalCrossEncoder(os.getenv("RERANKER_MODEL", "ms-marco-minilm-l-6-v2"))
    scores = await provider.score("meal allowance", ["annual revenue", "PKR 5,000 per day"])
    assert len(scores) == 2
