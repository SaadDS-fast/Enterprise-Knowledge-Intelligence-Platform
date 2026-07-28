from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import Document, DocumentVersion


async def list_documents(session: AsyncSession, workspace_id: UUID) -> list[Document]:
    return list(
        (
            await session.scalars(
                select(Document)
                .options(selectinload(Document.versions))
                .where(Document.workspace_id == workspace_id)
                .order_by(Document.created_at.desc())
            )
        ).all()
    )


async def get_document(
    session: AsyncSession, workspace_id: UUID, document_id: UUID
) -> Document | None:
    return await session.scalar(
        select(Document)
        .options(selectinload(Document.versions))
        .where(Document.id == document_id, Document.workspace_id == workspace_id)
    )


async def latest_version(session: AsyncSession, document_id: UUID) -> DocumentVersion | None:
    return await session.scalar(
        select(DocumentVersion)
        .where(DocumentVersion.document_id == document_id)
        .order_by(DocumentVersion.version_number.desc())
        .limit(1)
    )
