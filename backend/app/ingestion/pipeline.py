from __future__ import annotations

from pathlib import Path
from uuid import UUID

from sqlalchemy import delete

from app.db.models import Chunk, Document, DocumentVersion, IngestionJob
from app.db.session import AsyncSessionLocal
from app.ingestion.loaders import load_document
from app.ingestion.processors import build_metadata, deduplicate_chunks, find_pii, normalize_text
from app.integrations.storage import get_storage
from app.rag.chunking import chunk_text
from app.rag.embeddings import embed_text


async def process_ingestion_job(job_id: UUID) -> dict:
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
            job.status = "running"
            job.stage = "loading"
            document.status = "processing"
            await session.commit()
            data = await get_storage().get(version.storage_key)
            extension = Path(version.filename).suffix.lower()
            text = normalize_text(load_document(extension, data))
            if not text:
                raise ValueError("No readable text could be extracted")
            job.stage = "chunking"
            await session.commit()
            raw_chunks = deduplicate_chunks(chunk_text(text))
            if not raw_chunks:
                raise ValueError("No chunks were generated")
            job.stage = "embedding"
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
            approved_key = version.storage_key.replace("quarantine/", "approved/", 1)
            if approved_key != version.storage_key:
                await storage.put(approved_key, data, version.mime_type)
                await storage.delete(version.storage_key)
                version.storage_key = approved_key
            version.extracted_text = text
            version.metadata_json = build_metadata(
                version.filename, version.mime_type, version.size_bytes, text
            ) | {"pii_findings": pii_count}
            document.status = "ready"
            job.status = "completed"
            job.stage = "indexed"
            job.result_json = {
                "chunks": len(raw_chunks),
                "characters": len(text),
                "pii_findings": pii_count,
            }
            await session.commit()
            return job.result_json
        except Exception as exc:
            await session.rollback()
            job = await session.get(IngestionJob, job_id)
            document = await session.get(Document, version.document_id)
            if job:
                job.status = "failed"
                job.stage = "failed"
                job.error_message = str(exc)[:2000]
            if document:
                document.status = "failed"
            await session.commit()
            raise
