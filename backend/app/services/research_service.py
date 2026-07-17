from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ResearchJob
from app.services.search_service import search_and_answer


async def create_research_job(
    session: AsyncSession, *, workspace_id: UUID, user_id: UUID, question: str
) -> ResearchJob:
    job = ResearchJob(
        workspace_id=workspace_id, user_id=user_id, question=question, status="running"
    )
    session.add(job)
    await session.commit()
    await session.refresh(job)
    try:
        result = await search_and_answer(session, workspace_id=workspace_id, query=question)
        sources = "\n".join(f"- {e.document_title} (score {e.score:.2f})" for e in result.evidence)
        evidence_status = "Sufficient" if result.sufficient_evidence else "Insufficient"
        job.report_markdown = (
            f"# Research Brief\n\n## Question\n{question}\n\n"
            f"## Findings\n{result.answer}\n\n"
            f"## Evidence Status\n{evidence_status}\n\n"
            f"## Sources\n{sources or '- None'}"
        )
        job.result_json = result.model_dump(mode="json")
        job.status = "completed"
    except Exception as exc:
        job.status = "failed"
        job.error_message = str(exc)[:2000]
    await session.commit()
    await session.refresh(job)
    return job
