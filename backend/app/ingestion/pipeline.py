from __future__ import annotations

from pathlib import Path
from uuid import UUID

from sqlalchemy import delete

from app.db.models import Chunk, Document, DocumentVersion, IngestionJob
from app.db.session import AsyncSessionLocal
from app.ingestion.loaders import load_document
from app.ingestion.processors import build_metadata, deduplicate_chunks, find_pii, normalize_text
from app.integrations.storage import get_storage
from app.integrations.storage.keys import document_object_key
from app.jobs.status import IngestionStage, JobStatus
from app.observability.metrics import INGESTION_COMPLETED, INGESTION_FAILED
from app.rag.chunking import chunk_text
from app.rag.embeddings import embed_text


async def process_ingestion_job(job_id: UUID, request_id: str | None = None) -> dict:
    async with AsyncSessionLocal() as session:
        job = await session.get(IngestionJob, job_id)
        if not job:
            raise ValueError(f"Ingestion job {job_id} not found")
        version = await session.get(DocumentVersion, job.document_version_id)
        if not version:
            raise ValueError("Document version not found")
        document = await session.get(Document, version.document_id)
        if not document:
            raise ValueError("Document not found")
        try:
            job.status = JobStatus.RUNNING
            job.stage = IngestionStage.PARSING
            job.result_json = {"request_id": request_id} if request_id else {}
            document.status = "processing"
            await session.commit()
            data = await get_storage().get(version.storage_key)
            extension = Path(version.filename).suffix.lower()
            text = normalize_text(load_document(extension, data))
            if not text:
                raise ValueError("No readable text could be extracted")
            job.stage = IngestionStage.CHUNKING
            await session.commit()
            raw_chunks = deduplicate_chunks(chunk_text(text))
            if not raw_chunks:
                raise ValueError("No chunks were generated")
            job.stage = IngestionStage.EMBEDDING
            await session.commit()
            await session.execute(delete(Chunk).where(Chunk.document_version_id == version.id))
            pii_count = len(find_pii(text))
            session.add_all(
                [
                    Chunk(
                        document_version_id=version.id,
                        workspace_id=document.workspace_id,
                        ordinal=index,
                        content=content,
                        token_count=len(content.split()),
                        metadata_json={"filename": version.filename, "ordinal": index},
                        embedding=embed_text(content),
                    )
                    for index, content in enumerate(raw_chunks)
                ]
            )
            storage = get_storage()
            approved_key = document_object_key(
                group="source",
                workspace_id=document.workspace_id,
                document_id=document.id,
                version_id=version.id,
                filename=version.filename,
                unique=False,
            )
            if approved_key != version.storage_key:
                job.stage = IngestionStage.INDEXING
                await session.commit()
                await storage.put(approved_key, data, version.mime_type)
                await storage.delete(version.storage_key)
                version.storage_key = approved_key
            version.extracted_text = text
            version.metadata_json = build_metadata(
                version.filename, version.mime_type, version.size_bytes, text
            ) | {"pii_findings": pii_count}
            document.status = "ready"
            job.status = JobStatus.COMPLETED
            job.stage = IngestionStage.COMPLETED
            job.result_json = {
                "request_id": request_id,
                "chunks": len(raw_chunks),
                "characters": len(text),
                "pii_findings": pii_count,
            }
            await session.commit()
            INGESTION_COMPLETED.inc()
            return job.result_json
        except Exception as exc:
            await session.rollback()
            job = await session.get(IngestionJob, job_id)
            document = await session.get(Document, version.document_id)
            if job:
                job.status = JobStatus.FAILED
                job.stage = IngestionStage.FAILED
                job.error_message = str(exc)[:2000]
                job.result_json = {
                    **(job.result_json or {}),
                    "request_id": request_id,
                    "error_type": type(exc).__name__,
                }
            if document:
                document.status = "failed"
            await session.commit()
            INGESTION_FAILED.inc()
            raise
