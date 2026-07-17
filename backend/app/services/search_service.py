from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions.base import AppError
from app.exceptions.codes import ErrorCode
from app.llm.base import GenerationRequest
from app.llm.gateway import get_llm_gateway
from app.models.schemas import EvidenceItem, SearchResponse
from app.rag.abstention import abstention_message
from app.rag.evidence import evidence_is_sufficient
from app.rag.hybrid_retriever import retrieve
from app.rag.query_rewrite import rewrite_query
from app.security.prompt_security import scan_prompt


async def search_and_answer(
    session: AsyncSession,
    *,
    workspace_id: UUID,
    query: str,
    top_k: int | None = None,
    document_ids: list[UUID] | None = None,
    request_id: str | None = None,
) -> SearchResponse:
    scan = scan_prompt(query)
    if not scan.safe:
        raise AppError(
            ErrorCode.UNSAFE_INPUT,
            "The query contains instructions that conflict with platform security controls",
            400,
        )
    rewritten = rewrite_query(query)
    evidence = await retrieve(
        session, workspace_id=workspace_id, query=rewritten, top_k=top_k, document_ids=document_ids
    )
    sufficient = evidence_is_sufficient(
        [e.score for e in evidence], query, [e.content for e in evidence]
    )
    if not sufficient:
        return SearchResponse(
            answer=abstention_message(query),
            evidence=[
                EvidenceItem(
                    chunk_id=e.chunk_id,
                    document_id=e.document_id,
                    document_title=e.document_title,
                    content=e.content,
                    score=e.score,
                    metadata=e.metadata,
                )
                for e in evidence
            ],
            sufficient_evidence=False,
            abstained=True,
            request_id=request_id,
        )
    result = await get_llm_gateway().answer(GenerationRequest(question=query, evidence=evidence))
    return SearchResponse(
        answer=result.text,
        evidence=[
            EvidenceItem(
                chunk_id=e.chunk_id,
                document_id=e.document_id,
                document_title=e.document_title,
                content=e.content,
                score=e.score,
                metadata=e.metadata,
            )
            for e in evidence
        ],
        sufficient_evidence=True,
        abstained=False,
        request_id=request_id,
    )
