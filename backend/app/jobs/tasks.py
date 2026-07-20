import asyncio
from uuid import UUID

from app.ingestion.pipeline import process_ingestion_job
from app.jobs.queue import celery_app


@celery_app.task(
    name="ekip.ingest",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    retry_kwargs={"max_retries": 3},
    soft_time_limit=300,
    time_limit=360,
)
def ingest(job_id: str, request_id: str | None = None) -> dict:
    return asyncio.run(process_ingestion_job(UUID(job_id), request_id=request_id))
