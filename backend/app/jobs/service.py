from uuid import UUID

from fastapi import BackgroundTasks

from app.core.config import JobExecutionMode, settings
from app.ingestion.pipeline import process_ingestion_job
from app.jobs.queue import celery_app


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
            headers={"request_id": request_id} if request_id else None,
        )
        return result.id
    if background_tasks is not None:
        background_tasks.add_task(process_ingestion_job, job_id, request_id=request_id)
    return None
