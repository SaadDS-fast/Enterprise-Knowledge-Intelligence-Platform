from uuid import UUID

from fastapi import BackgroundTasks

from app.core.config import JobExecutionMode, settings
from app.ingestion.pipeline import process_ingestion_job
from app.jobs.queue import celery_app


def dispatch_ingestion(job_id: UUID, background_tasks: BackgroundTasks | None = None) -> None:
    if settings.job_execution_mode is JobExecutionMode.CELERY:
        celery_app.send_task("ekip.ingest", args=[str(job_id)], queue="ingestion")
    elif background_tasks is not None:
        background_tasks.add_task(process_ingestion_job, job_id)
