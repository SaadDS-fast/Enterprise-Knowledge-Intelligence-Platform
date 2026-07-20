from uuid import UUID

import pytest
from sqlalchemy import select

from app.core.config import JobExecutionMode
from app.db.models import Chunk, IngestionJob
from app.db.session import AsyncSessionLocal
from app.ingestion.pipeline import process_ingestion_job
from app.jobs import service
from app.jobs.status import JobStatus


@pytest.mark.asyncio
async def test_completed_ingestion_retry_preserves_request_id_and_chunks(client, auth_headers):
    upload = client.post(
        "/api/v1/documents",
        headers=auth_headers,
        files={"file": ("retry.txt", b"Retry validation document text.", "text/plain")},
    )
    assert upload.status_code == 202, upload.text
    job_id = UUID(upload.json()["job_id"])

    async with AsyncSessionLocal() as session:
        job = await session.get(IngestionJob, job_id)
        assert job is not None
        original_result = dict(job.result_json)
        assert original_result["request_id"]
        before = (
            await session.scalars(
                select(Chunk).where(Chunk.document_version_id == job.document_version_id)
            )
        ).all()

    result = await process_ingestion_job(job_id, request_id=None)

    async with AsyncSessionLocal() as session:
        job = await session.get(IngestionJob, job_id)
        after = (
            await session.scalars(
                select(Chunk).where(Chunk.document_version_id == job.document_version_id)
            )
        ).all()

    assert result["request_id"] == original_result["request_id"]
    assert job.result_json["request_id"] == original_result["request_id"]
    assert len(after) == len(before) == 1
    assert job.status == JobStatus.COMPLETED


@pytest.mark.asyncio
async def test_dispatch_failure_marks_retry_pending_without_losing_request_id(
    client, auth_headers, monkeypatch
):
    upload = client.post(
        "/api/v1/documents",
        headers=auth_headers,
        files={"file": ("dispatch.txt", b"Dispatch recovery text.", "text/plain")},
    )
    assert upload.status_code == 202, upload.text
    job_id = UUID(upload.json()["job_id"])

    def fail_dispatch(*args, **kwargs):
        raise ConnectionError("redis unavailable")

    monkeypatch.setattr(service.settings, "job_execution_mode", JobExecutionMode.CELERY)
    monkeypatch.setattr(service, "dispatch_ingestion", fail_dispatch)

    async with AsyncSessionLocal() as session:
        job = await session.get(IngestionJob, job_id)
        job.status = JobStatus.PENDING
        job.result_json = {"request_id": "req-preserved"}
        await session.commit()

        task_id = await service.dispatch_ingestion_safely(session, job_id, request_id=None)
        await session.refresh(job)

    assert task_id is None
    assert job.status == JobStatus.RETRY_PENDING
    assert job.result_json["request_id"] == "req-preserved"
    assert job.error_message == "Task dispatch failed; retry pending"
