import time
from uuid import UUID

from fastapi import BackgroundTasks
from kombu.exceptions import OperationalError as KombuOperationalError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import JobExecutionMode, settings
from app.db.models import IngestionJob
from app.ingestion.pipeline import process_ingestion_job
from app.jobs.queue import celery_app
from app.jobs.status import JobStatus


def dispatch_ingestion(
    job_id: UUID,
    background_tasks: BackgroundTasks | None = None,
    *,
    request_id: str | None = None,
) -> str | None:
    if settings.job_execution_mode is JobExecutionMode.CELERY:
        result = celery_app.send_task(
            "ekip.ingest",
            args=[str(job_id)],
            kwargs={"request_id": request_id},
            queue="ingestion",
            task_id=str(job_id),
            headers={"request_id": request_id, "published_at": time.time()}
            if request_id
            else {"published_at": time.time()},
        )
        return result.id
    if background_tasks is not None:
        background_tasks.add_task(process_ingestion_job, job_id, request_id=request_id)
    return None


async def dispatch_ingestion_safely(
    session: AsyncSession,
    job_id: UUID,
    background_tasks: BackgroundTasks | None = None,
    *,
    request_id: str | None = None,
) -> str | None:
    job = await session.get(IngestionJob, job_id)
    if not job:
        raise ValueError(f"Ingestion job {job_id} not found")
    try:
        task_id = dispatch_ingestion(job_id, background_tasks, request_id=request_id)
    except (KombuOperationalError, OSError, ConnectionError) as exc:
        job.status = JobStatus.RETRY_PENDING
        job.stage = "queued"
        job.error_message = "Task dispatch failed; retry pending"
        job.result_json = {
            **(job.result_json or {}),
            **({"request_id": request_id} if request_id else {}),
            "dispatch_error_type": type(exc).__name__,
        }
        await session.commit()
        return None
    job.error_message = None
    job.result_json = {
        **(job.result_json or {}),
        **({"request_id": request_id} if request_id else {}),
        "task_id": task_id,
    }
    await session.commit()
    return task_id
