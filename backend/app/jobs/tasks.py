import asyncio
from uuid import UUID

from app.ingestion.pipeline import process_ingestion_job
from app.jobs.queue import celery_app


@celery_app.task(
    name="ekip.ingest",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def ingest(job_id: str) -> dict:
    return asyncio.run(process_ingestion_job(UUID(job_id)))
