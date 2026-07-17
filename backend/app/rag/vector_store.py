from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.chunk import Chunk


async def replace_version_chunks(
    session: AsyncSession, version_id: UUID, chunks: list[Chunk]
) -> None:
    await session.execute(delete(Chunk).where(Chunk.document_version_id == version_id))
    session.add_all(chunks)


async def list_workspace_chunks(session: AsyncSession, workspace_id: UUID) -> list[Chunk]:
    return list(
        (await session.scalars(select(Chunk).where(Chunk.workspace_id == workspace_id))).all()
    )
