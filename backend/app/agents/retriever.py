from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.rag.hybrid_retriever import retrieve


async def retrieve_for_agent(session: AsyncSession, workspace_id: UUID, question: str):
    return await retrieve(session, workspace_id=workspace_id, query=question)
