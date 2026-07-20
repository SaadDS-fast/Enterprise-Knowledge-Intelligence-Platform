from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models import Chunk, Document, DocumentVersion
from app.models.domain import RetrievedEvidence
from app.rag.bm25 import bm25_scores
from app.rag.embeddings import cosine_similarity, embed_text
from app.rag.fusion import weighted_fusion
from app.rag.reranker import rerank_score


async def retrieve(
    session: AsyncSession,
    *,
    workspace_id: UUID,
    query: str,
    top_k: int | None = None,
    document_ids: list[UUID] | None = None,
) -> list[RetrievedEvidence]:
    statement = (
        select(Chunk, DocumentVersion, Document)
        .join(DocumentVersion, Chunk.document_version_id == DocumentVersion.id)
        .join(Document, DocumentVersion.document_id == Document.id)
        .where(Chunk.workspace_id == workspace_id, Document.status == "ready")
    )
    if document_ids:
        statement = statement.where(Document.id.in_(document_ids))
    rows = (await session.execute(statement)).all()
    if not rows:
        return []
    contents = [row.Chunk.content for row in rows]
    lexical = bm25_scores(query, contents)
    query_vector = embed_text(query)
    semantic = [cosine_similarity(query_vector, list(row.Chunk.embedding or [])) for row in rows]
    fused = weighted_fusion(lexical, semantic)
    ranked: list[RetrievedEvidence] = []
    for row, score in zip(rows, fused, strict=True):
        final = rerank_score(query, row.Chunk.content, score)
        ranked.append(
            RetrievedEvidence(
                chunk_id=row.Chunk.id,
                document_id=row.Document.id,
                document_title=row.Document.title,
                content=row.Chunk.content,
                score=final,
                metadata=row.Chunk.metadata_json,
            )
        )
    ranked.sort(key=lambda item: item.score, reverse=True)
    return ranked[: min(top_k or settings.rerank_top_k, settings.retrieval_top_k)]
