from __future__ import annotations

from pathlib import Path
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Document, DocumentVersion, IngestionJob
from app.integrations.storage import get_storage
from app.security.file_validation import validate_file
from app.security.malware_scan import scan_bytes
from app.utils.hashing import hash_bytes


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
    storage_key = f"quarantine/{workspace_id}/{document.id}/{uuid4()}-{validated.filename}"
    await get_storage().put(storage_key, data, validated.mime_type)
    version = DocumentVersion(
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
    return document, version, job


async def delete_document_and_objects(session: AsyncSession, document: Document) -> None:
    await session.refresh(document, attribute_names=["versions"])
    storage = get_storage()
    for version in document.versions:
        if await storage.exists(version.storage_key):
            await storage.delete(version.storage_key)
    await session.delete(document)
    await session.commit()
