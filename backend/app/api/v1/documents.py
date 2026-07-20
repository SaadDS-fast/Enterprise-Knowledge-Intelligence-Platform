from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, Request, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.tenancy import Tenant
from app.db.session import get_db
from app.exceptions.base import ForbiddenError, NotFoundError
from app.jobs.service import dispatch_ingestion
from app.models.schemas import DocumentRead, DocumentVersionRead, MessageResponse, UploadResponse
from app.repositories.documents import get_document, list_documents
from app.security.authorization import can_manage_documents
from app.services.document_service import create_document_upload, delete_document_and_objects

router = APIRouter()


@router.get("", response_model=list[DocumentRead])
async def documents(
    tenant: Tenant, session: Annotated[AsyncSession, Depends(get_db)]
) -> list[DocumentRead]:
    return [
        DocumentRead.model_validate(item)
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
    dispatch_ingestion(
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


@router.get("/{document_id}", response_model=DocumentRead)
async def document_detail(
    document_id: UUID, tenant: Tenant, session: Annotated[AsyncSession, Depends(get_db)]
) -> DocumentRead:
    document = await get_document(session, tenant.workspace_id, document_id)
    if not document:
        raise NotFoundError("Document not found")
    return DocumentRead.model_validate(document)


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
