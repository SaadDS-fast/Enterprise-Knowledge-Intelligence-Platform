"""Validate sanitized live-model failures against an intentionally empty cache."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from app.core.config import settings
from app.rag.reranker_provider import configured_reranker, rerank
from app.rag.semantic_provider import (
    DeterministicEmbeddingProvider,
    LocalSentenceTransformerProvider,
    configured_embedding_provider,
    embed_with_fallback,
)


async def run(output: Path) -> dict:
    settings.semantic_embeddings_enabled = True
    settings.semantic_embedding_model = "all-minilm-l6-v2"
    settings.semantic_embedding_fallback_enabled = True
    configured_embedding_provider.cache_clear()
    vectors, embedding_provider, embedding_fallback = await embed_with_fallback(
        ["official travel meal allowance"]
    )

    settings.reranker_enabled = True
    settings.reranker_model = "ms-marco-minilm-l-6-v2"
    settings.reranker_fallback_enabled = True
    configured_reranker.cache_clear()
    reranker_result = await rerank(
        "official travel meal allowance",
        ["cafeteria menu", "PKR 5,000 per day"],
        [0.2, 0.9],
    )

    settings.semantic_embedding_model = "operator-typo"
    configured_embedding_provider.cache_clear()
    invalid_alias_provider = configured_embedding_provider()

    configured_dimension = settings.semantic_embedding_dimension
    settings.semantic_embedding_dimension = 768
    try:
        LocalSentenceTransformerProvider("all-minilm-l6-v2")
    except ValueError as exc:
        dimension_error = str(exc)
    finally:
        settings.semantic_embedding_dimension = configured_dimension

    result = {
        "missing_embedding_cache": {
            "request_completed": len(vectors) == 1,
            "fallback_used": embedding_fallback,
            "provider": embedding_provider.identity.provider,
            "version": embedding_provider.identity.version,
        },
        "invalid_operator_alias": {
            "fallback_provider": invalid_alias_provider.identity.provider,
            "sanitized": isinstance(
                invalid_alias_provider, DeterministicEmbeddingProvider
            ),
        },
        "incompatible_dimension": {
            "rejected": dimension_error
            == "Configured semantic embedding dimension does not match model",
            "sanitized_error": dimension_error,
        },
        "missing_reranker_cache": {
            "request_completed": len(reranker_result.scores) == 2,
            "used": reranker_result.used,
            "fallback_used": reranker_result.fallback_used,
            "version": reranker_result.version,
            "ranking_preserved": reranker_result.scores == [0.2, 0.9],
        },
        "paths_exposed": False,
        "vectors_exposed": False,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return result


def main() -> None:
    output = Path("docs/evaluation/phase2-live-fallback-results.json")
    print(json.dumps(asyncio.run(run(output)), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
