from __future__ import annotations

import asyncio
from contextlib import suppress

from sqlalchemy import select

from app.core.config import JobExecutionMode, settings
from app.db.models import IngestionJob, ResearchJob
from app.db.session import AsyncSessionLocal
from app.jobs.service import dispatch_ingestion_safely
from app.jobs.status import JobStatus
from app.observability.metrics import AGENT_RESEARCH_RETRIES
from app.services.research_service import dispatch_research_safely


async def dispatch_pending_ingestion_jobs_once(limit: int = 25) -> int:
    if settings.job_execution_mode is not JobExecutionMode.CELERY:
        return 0
    async with AsyncSessionLocal() as session:
        jobs = (
            await session.scalars(
                select(IngestionJob)
                .where(
                    IngestionJob.status.in_([JobStatus.RETRY_PENDING, JobStatus.DISPATCH_FAILED])
                )
                .order_by(IngestionJob.created_at)
                .limit(limit)
            )
        ).all()
        dispatched = 0
        for job in jobs:
            request_id = (job.result_json or {}).get("request_id")
            task_id = await dispatch_ingestion_safely(session, job.id, request_id=request_id)
            if task_id:
                await session.refresh(job)
            if task_id and job.status in {
                JobStatus.RETRY_PENDING,
                JobStatus.DISPATCH_FAILED,
            }:
                job.status = JobStatus.PENDING
                job.stage = "queued"
                job.error_message = None
                await session.commit()
                dispatched += 1
        return dispatched


async def dispatch_pending_research_jobs_once(limit: int = 25) -> int:
    if settings.job_execution_mode is not JobExecutionMode.CELERY:
        return 0
    async with AsyncSessionLocal() as session:
        jobs = (
            await session.scalars(
                select(ResearchJob)
                .where(ResearchJob.status == "dispatch_failed")
                .order_by(ResearchJob.created_at)
                .limit(limit)
            )
        ).all()
        dispatched = 0
        for job in jobs:
            task_id = await dispatch_research_safely(session, job.id, request_id=job.request_id)
            if task_id:
                AGENT_RESEARCH_RETRIES.labels(reason="dispatch_failed").inc()
                dispatched += 1
        return dispatched


async def dispatch_pending_ingestion_jobs_loop(interval_seconds: float = 5.0) -> None:
    while True:
        with suppress(Exception):
            await dispatch_pending_ingestion_jobs_once()
        with suppress(Exception):
            await dispatch_pending_research_jobs_once()
        await asyncio.sleep(interval_seconds)
