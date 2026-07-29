from __future__ import annotations

from asyncio import sleep
from pathlib import Path
from uuid import UUID

from sqlalchemy import delete

from app.core.config import settings
from app.db.models import Chunk, Document, DocumentVersion, IngestionJob
from app.db.session import AsyncSessionLocal
from app.ingestion.chunking_v3 import chunk_document
from app.ingestion.extractor import extract_document
from app.ingestion.processors import build_metadata, find_pii, normalize_text
from app.ingestion.quality import ExtractionQuality, assess_extraction
from app.ingestion.versions import LATEST_PIPELINE
from app.integrations.storage import get_storage
from app.integrations.storage.keys import document_object_key
from app.jobs.status import IngestionStage, JobStatus
from app.observability.metrics import INGESTION_COMPLETED, INGESTION_FAILED
from app.rag.semantic_provider import embed_with_fallback


async def process_ingestion_job(job_id: UUID, request_id: str | None = None) -> dict:
    async with AsyncSessionLocal() as session:
        job = await session.get(IngestionJob, job_id)
        if not job:
            raise ValueError(f"Ingestion job {job_id} not found")
        if job.status == JobStatus.COMPLETED:
            return job.result_json or {}
        version = await session.get(DocumentVersion, job.document_version_id)
        if not version:
            raise ValueError("Document version not found")
        document = await session.get(Document, version.document_id)
        if not document:
            raise ValueError("Document not found")
        existing_result = job.result_json or {}
        effective_request_id = request_id or existing_result.get("request_id")
        try:
            job.status = JobStatus.RUNNING
            job.stage = IngestionStage.PARSING
            job.result_json = (
                {**existing_result, "request_id": effective_request_id}
                if effective_request_id
                else existing_result
            )
            document.status = "processing"
            await session.commit()
            await _stage_delay()
            data = await get_storage().get(version.storage_key)
            extension = Path(version.filename).suffix.lower()
            extracted = extract_document(extension, data, filename=version.filename)
            for block in extracted.blocks:
                block.text = normalize_text(block.text)
            text = extracted.text
            quality = assess_extraction(extracted)
            pipeline_versions = LATEST_PIPELINE.as_dict()
            if quality.status == ExtractionQuality.REQUIRES_OCR:
                version.extracted_text = None
                version.metadata_json = (
                    build_metadata(version.filename, version.mime_type, version.size_bytes, "")
                    | pipeline_versions
                    | {
                        "extraction_quality": quality.as_dict(),
                        "page_count": extracted.page_count,
                        "chunk_count": 0,
                    }
                )
                document.status = "requires_ocr"
                job.status = JobStatus.COMPLETED
                job.stage = IngestionStage.COMPLETED
                job.result_json = {
                    **existing_result,
                    "request_id": effective_request_id,
                    "chunks": 0,
                    "status": "REQUIRES_OCR",
                    **pipeline_versions,
                }
                await session.commit()
                INGESTION_COMPLETED.inc()
                return job.result_json
            if quality.status == ExtractionQuality.FAILED:
                raise ValueError("extraction_empty")
            job.stage = IngestionStage.CHUNKING
            await session.commit()
            await _stage_delay()
            structured_chunks = chunk_document(extracted)
            if not structured_chunks:
                raise ValueError("no_usable_chunks")
            job.stage = IngestionStage.EMBEDDING
            await session.commit()
            await _stage_delay()
            embedding_inputs = [
                _semantic_chunk_text(
                    title=document.title,
                    content=structured.content,
                    metadata=structured.metadata,
                )
                for structured in structured_chunks
            ]
            embeddings, embedding_provider, embedding_fallback = await embed_with_fallback(
                embedding_inputs
            )
            embedding_metadata = embedding_provider.identity.metadata(
                indexing_version=pipeline_versions["indexing_version"]
            )
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
                        metadata_json={
                            "document_id": str(document.id),
                            "source_filename": version.filename,
                            "filename": version.filename,
                            "mime_type": version.mime_type,
                            "ordinal": index,
                            "document_version_id": str(version.id),
                            **structured.metadata,
                            **pipeline_versions,
                            "extraction_quality": quality.status.value,
                            "chunking_strategy": "structure-aware-v3",
                            **embedding_metadata,
                            "embedding_fallback_used": embedding_fallback,
                        },
                        embedding=embedding,
                    )
                    for index, (structured, embedding) in enumerate(
                        zip(structured_chunks, embeddings, strict=True)
                    )
                    for content in [structured.content]
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
                await _stage_delay()
                await storage.put(approved_key, data, version.mime_type)
                await storage.delete(version.storage_key)
                version.storage_key = approved_key
            version.extracted_text = text
            version.metadata_json = (
                build_metadata(version.filename, version.mime_type, version.size_bytes, text)
                | pipeline_versions
                | {
                    "pii_findings": pii_count,
                    "extraction_quality": quality.as_dict(),
                    "page_count": extracted.page_count,
                    "chunk_count": len(structured_chunks),
                    **embedding_metadata,
                    "embedding_fallback_used": embedding_fallback,
                }
            )
            document.status = (
                "ready_with_warnings"
                if quality.status in {ExtractionQuality.ACCEPTABLE, ExtractionQuality.LOW_QUALITY}
                else "ready"
            )
            job.status = JobStatus.COMPLETED
            job.stage = IngestionStage.COMPLETED
            job.result_json = {
                **existing_result,
                "request_id": effective_request_id,
                "chunks": len(structured_chunks),
                "characters": len(text),
                "pii_findings": pii_count,
                "status": document.status.upper(),
                "extraction_quality": quality.status.value,
                "chunking_strategy": "structure-aware-v3",
                **embedding_metadata,
                "embedding_fallback_used": embedding_fallback,
                **pipeline_versions,
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
                category = _safe_error_category(exc)
                job.error_message = category
                job.result_json = {
                    **(job.result_json or {}),
                    **({"request_id": effective_request_id} if effective_request_id else {}),
                    "error_category": category,
                }
            if document:
                document.status = "extraction_failed"
            version = await session.get(DocumentVersion, job.document_version_id) if job else None
            if version:
                version.metadata_json = {
                    **(version.metadata_json or {}),
                    **LATEST_PIPELINE.as_dict(),
                    "error_category": category,
                }
            await session.commit()
            INGESTION_FAILED.inc()
            raise


async def _stage_delay() -> None:
    if settings.ingestion_stage_delay_seconds:
        await sleep(settings.ingestion_stage_delay_seconds)


def _safe_error_category(exc: Exception) -> str:
    value = str(exc)
    if value in {"extraction_empty", "no_usable_chunks"}:
        return value.upper()
    if isinstance(exc, (ValueError, UnicodeError)):
        return "MALFORMED_OR_UNSUPPORTED_CONTENT"
    return "INTERNAL_PROCESSING_ERROR"


def _semantic_chunk_text(*, title: str, content: str, metadata: dict) -> str:
    """Build safe retrieval context from the chunk and structural labels only."""
    labels = [
        title[:255],
        str(metadata.get("heading") or "")[:500],
        str(metadata.get("section") or "")[:500],
        content,
    ]
    return "\n".join(value for value in labels if value)
