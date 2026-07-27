from typing import Annotated
from uuid import UUID

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    Header,
    Query,
    Request,
    UploadFile,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.tenancy import Tenant
from app.db.models import Chunk
from app.db.session import get_db
from app.exceptions.base import ForbiddenError, NotFoundError
from app.ingestion.versions import LATEST_PIPELINE
from app.jobs.service import dispatch_ingestion_safely
from app.models.schemas import (
    DocumentRead,
    DocumentVersionRead,
    MessageResponse,
    ReprocessResponse,
    StructureChunkRead,
    UploadResponse,
)
from app.repositories.documents import get_document, list_documents
from app.security.authorization import can_manage_documents
from app.services.document_service import (
    create_document_upload,
    create_reprocess_job,
    delete_document_and_objects,
    document_summary,
)

router = APIRouter()


@router.get("", response_model=list[DocumentRead])
async def documents(
    tenant: Tenant, session: Annotated[AsyncSession, Depends(get_db)]
) -> list[DocumentRead]:
    return [
        DocumentRead.model_validate(document_summary(item))
        for item in await list_documents(session, tenant.workspace_id)
    ]


@router.post("", response_model=UploadResponse, status_code=202)
async def upload_document(
    request: Request,
    background_tasks: BackgroundTasks,
    tenant: Tenant,
    session: Annotated[AsyncSession, Depends(get_db)],
    file: Annotated[UploadFile, File()],
    title: Annotated[str | None, Form()] = None,
    description: Annotated[str | None, Form()] = None,
) -> UploadResponse:
    if not can_manage_documents(tenant.role):
        raise ForbiddenError("Document upload requires editor access")
    data = await file.read()
    document, version, job = await create_document_upload(
        session,
        workspace_id=tenant.workspace_id,
        user_id=tenant.user_id,
        filename=file.filename or "upload",
        mime_type=file.content_type or "application/octet-stream",
        data=data,
        title=title,
        description=description,
    )
    await dispatch_ingestion_safely(
        session,
        job.id,
        background_tasks,
        request_id=getattr(request.state, "request_id", None),
    )
    return UploadResponse(
        document=DocumentRead.model_validate(document),
        version=DocumentVersionRead.model_validate(version),
        job_id=job.id,
        status="accepted",
    )


@router.post("/{document_id}/reprocess", response_model=ReprocessResponse, status_code=202)
async def reprocess_document(
    document_id: UUID,
    request: Request,
    background_tasks: BackgroundTasks,
    tenant: Tenant,
    session: Annotated[AsyncSession, Depends(get_db)],
    idempotency_key: Annotated[str | None, Header(max_length=200)] = None,
) -> ReprocessResponse:
    if not can_manage_documents(tenant.role):
        raise ForbiddenError("Document reprocessing requires editor access")
    document = await get_document(session, tenant.workspace_id, document_id)
    if not document:
        raise NotFoundError("Document not found")
    job, idempotent = await create_reprocess_job(session, document, idempotency_key=idempotency_key)
    if not idempotent:
        await dispatch_ingestion_safely(
            session,
            job.id,
            background_tasks,
            request_id=getattr(request.state, "request_id", None),
        )
    return ReprocessResponse(
        document_id=document.id,
        job_id=job.id,
        status="completed" if job.status == "completed" else "accepted",
        idempotent=idempotent,
    )


@router.get("/{document_id}/structure", response_model=list[StructureChunkRead])
async def inspect_document_structure(
    document_id: UUID,
    tenant: Tenant,
    session: Annotated[AsyncSession, Depends(get_db)],
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
) -> list[StructureChunkRead]:
    document = await get_document(session, tenant.workspace_id, document_id)
    if not document:
        raise NotFoundError("Document not found")
    if not document.versions:
        return []
    version = document.versions[-1]
    chunks = (
        await session.scalars(
            select(Chunk)
            .where(
                Chunk.workspace_id == tenant.workspace_id,
                Chunk.document_version_id == version.id,
            )
            .order_by(Chunk.ordinal)
            .limit(limit)
        )
    ).all()
    return [
        StructureChunkRead(
            page=item.metadata_json.get("page"),
            heading=item.metadata_json.get("heading"),
            section=item.metadata_json.get("section"),
            question_number=item.metadata_json.get("question_number"),
            chunk_order=item.ordinal,
            excerpt=item.content[:500],
            quality_status=item.metadata_json.get("extraction_quality"),
            pipeline_version={
                key: item.metadata_json.get(key) for key in LATEST_PIPELINE.as_dict()
            },
        )
        for item in chunks
    ]


@router.get("/{document_id}", response_model=DocumentRead)
async def document_detail(
    document_id: UUID, tenant: Tenant, session: Annotated[AsyncSession, Depends(get_db)]
) -> DocumentRead:
    document = await get_document(session, tenant.workspace_id, document_id)
    if not document:
        raise NotFoundError("Document not found")
    return DocumentRead.model_validate(document_summary(document))


@router.delete("/{document_id}", response_model=MessageResponse)
async def delete_document(
    document_id: UUID, tenant: Tenant, session: Annotated[AsyncSession, Depends(get_db)]
) -> MessageResponse:
    if not can_manage_documents(tenant.role):
        raise ForbiddenError("Document deletion requires editor access")
    document = await get_document(session, tenant.workspace_id, document_id)
    if not document:
        raise NotFoundError("Document not found")
    await delete_document_and_objects(session, document)
    return MessageResponse(message="Document deleted")
