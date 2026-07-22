import asyncio
from uuid import UUID

from app.db.session import close_database
from app.ingestion.pipeline import process_ingestion_job
from app.jobs.queue import celery_app
from app.services.research_service import generate_research_report


async def _run_ingestion_task(job_id: UUID, request_id: str | None) -> dict:
    await close_database()
    try:
        return await process_ingestion_job(job_id, request_id=request_id)
    finally:
        await close_database()


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
    return asyncio.run(_run_ingestion_task(UUID(job_id), request_id))


async def _run_research_report_task(job_id: UUID, request_id: str | None) -> dict:
    await close_database()
    try:
        return await generate_research_report(job_id, request_id=request_id)
    finally:
        await close_database()


@celery_app.task(
    name="ekip.research_report",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    retry_kwargs={"max_retries": 3},
    soft_time_limit=300,
    time_limit=360,
)
def research_report(job_id: str, request_id: str | None = None) -> dict:
    return asyncio.run(_run_research_report_task(UUID(job_id), request_id))
