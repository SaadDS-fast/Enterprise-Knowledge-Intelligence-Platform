from __future__ import annotations

from pathlib import Path
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Document, DocumentVersion, IngestionJob
from app.ingestion.versions import LATEST_PIPELINE, is_current
from app.integrations.storage import get_storage
from app.integrations.storage.keys import document_object_key
from app.jobs.status import JobStatus
from app.observability.metrics import INGESTION_SUBMITTED
from app.security.file_validation import validate_file
from app.security.malware_scan import scan_bytes
from app.utils.hashing import hash_bytes, hash_text


async def create_document_upload(
    session: AsyncSession,
    *,
    workspace_id: UUID,
    user_id: UUID,
    filename: str,
    mime_type: str,
    data: bytes,
    title: str | None = None,
    description: str | None = None,
) -> tuple[Document, DocumentVersion, IngestionJob]:
    validated = validate_file(filename, mime_type, data)
    scan = await scan_bytes(data)
    if not scan.clean:
        raise ValueError(scan.detail)
    document = Document(
        workspace_id=workspace_id,
        title=(title or Path(validated.filename).stem)[:255],
        description=description,
        created_by=user_id,
        status="pending",
    )
    session.add(document)
    await session.flush()
    checksum = hash_bytes(data)
    version_id = uuid4()
    storage_key = document_object_key(
        group="quarantine",
        workspace_id=workspace_id,
        document_id=document.id,
        version_id=version_id,
        filename=validated.filename,
    )
    await get_storage().put(storage_key, data, validated.mime_type)
    version = DocumentVersion(
        id=version_id,
        document_id=document.id,
        version_number=1,
        filename=validated.filename,
        mime_type=validated.mime_type,
        size_bytes=validated.size_bytes,
        checksum_sha256=checksum,
        storage_key=storage_key,
        metadata_json={"scan_engine": scan.engine, "scan_detail": scan.detail},
    )
    session.add(version)
    await session.flush()
    job = IngestionJob(
        workspace_id=workspace_id, document_version_id=version.id, status="pending", stage="queued"
    )
    session.add(job)
    await session.commit()
    await session.refresh(document)
    await session.refresh(version)
    await session.refresh(job)
    INGESTION_SUBMITTED.inc()
    return document, version, job


async def delete_document_and_objects(session: AsyncSession, document: Document) -> None:
    await session.refresh(document, attribute_names=["versions"])
    storage = get_storage()
    for version in document.versions:
        if await storage.exists(version.storage_key):
            await storage.delete(version.storage_key)
    await session.delete(document)
    await session.commit()


def document_summary(document: Document) -> dict:
    version = document.versions[-1] if document.versions else None
    metadata = version.metadata_json if version else {}
    quality = metadata.get("extraction_quality") or {}
    current = {key: metadata.get(key) for key in LATEST_PIPELINE.as_dict()}
    return {
        "id": document.id,
        "workspace_id": document.workspace_id,
        "title": document.title,
        "status": "reprocessing_recommended"
        if document.status in {"ready", "ready_with_warnings"} and not is_current(metadata)
        else document.status,
        "description": document.description,
        "created_by": document.created_by,
        "created_at": document.created_at,
        "updated_at": document.updated_at,
        "filename": version.filename if version else None,
        "extraction_quality": quality.get("status"),
        "page_count": metadata.get("page_count"),
        "chunk_count": metadata.get("chunk_count", 0),
        "pipeline_version": current,
        "latest_pipeline_version": LATEST_PIPELINE.as_dict(),
        "reprocessing_recommended": bool(
            version
            and (
                not is_current(metadata)
                or metadata.get("embedding_version") is None
                or metadata.get("embedding_dimension") is None
            )
        ),
        "processing_progress": "processing" if document.status == "processing" else None,
        "error_category": metadata.get("error_category"),
    }


async def create_reprocess_job(
    session: AsyncSession,
    document: Document,
    *,
    idempotency_key: str | None = None,
    operation: str = "reprocess",
) -> tuple[IngestionJob, bool]:
    if not document.versions:
        raise ValueError("Document has no uploaded version")
    version = document.versions[-1]
    jobs = (
        await session.scalars(
            select(IngestionJob)
            .where(
                IngestionJob.workspace_id == document.workspace_id,
                IngestionJob.document_version_id == version.id,
            )
            .order_by(IngestionJob.created_at.desc())
        )
    ).all()
    key_hash = hash_text(idempotency_key) if idempotency_key else None
    replay = next(
        (
            item
            for item in jobs
            if key_hash and (item.result_json or {}).get("idempotency_key_hash") == key_hash
        ),
        None,
    )
    if replay:
        return replay, True
    active = next(
        (
            item
            for item in jobs
            if item.status
            in {
                JobStatus.PENDING,
                JobStatus.RUNNING,
                JobStatus.RETRY_PENDING,
                JobStatus.DISPATCH_FAILED,
            }
        ),
        None,
    )
    if active:
        return active, True
    job = IngestionJob(
        workspace_id=document.workspace_id,
        document_version_id=version.id,
        status=JobStatus.PENDING,
        stage="queued",
        result_json={
            "operation": operation,
            **({"idempotency_key_hash": key_hash} if key_hash else {}),
            **LATEST_PIPELINE.as_dict(),
        },
    )
    session.add(job)
    document.status = "processing"
    await session.commit()
    await session.refresh(job)
    INGESTION_SUBMITTED.inc()
    return job, False
