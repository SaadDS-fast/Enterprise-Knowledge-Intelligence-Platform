from uuid import uuid4

import pytest

from app.agents.enums import AgentRunStatus, AgentStateName
from app.agents.research import (
    ResearchCreateRequest,
    ResearchFormat,
    ResearchState,
    StructuredReport,
    can_transition,
    render_docx,
    render_markdown,
    render_pdf,
    research_object_key,
    scoped_idempotency_key,
    sign_download_token,
    validate_transition,
    verify_download_token,
)
from app.agents.schemas import AgentQueryResponse


def test_research_state_machine_allows_only_controlled_transitions() -> None:
    assert can_transition(ResearchState.PENDING, ResearchState.AUTHORIZING)
    assert can_transition(ResearchState.EXPORTING, ResearchState.COMPLETED)
    assert not can_transition(ResearchState.COMPLETED, ResearchState.EXPORTING)
    with pytest.raises(ValueError):
        validate_transition(ResearchState.PENDING.value, ResearchState.EXPORTING)


def test_scoped_idempotency_includes_tenant_workspace_user_and_payload() -> None:
    tenant_id = uuid4()
    workspace_id = uuid4()
    user_id = uuid4()
    payload = ResearchCreateRequest(
        question="Summarize Project Atlas ownership.",
        requested_formats=[ResearchFormat.MARKDOWN],
        idempotency_key="request-123",
    )
    first = scoped_idempotency_key(
        tenant_id=tenant_id,
        workspace_id=workspace_id,
        user_id=user_id,
        payload=payload,
    )
    second = scoped_idempotency_key(
        tenant_id=tenant_id,
        workspace_id=uuid4(),
        user_id=user_id,
        payload=payload,
    )
    assert first != second


def test_research_object_key_is_scoped_to_tenant_workspace_job_and_artifact() -> None:
    tenant_id = uuid4()
    workspace_id = uuid4()
    job_id = uuid4()
    artifact_id = uuid4()
    key = research_object_key(
        tenant_id=tenant_id,
        workspace_id=workspace_id,
        job_id=job_id,
        artifact_id=artifact_id,
        ext="md",
    )
    assert key == f"reports/{tenant_id}/{workspace_id}/{job_id}/{artifact_id}/report.md"


def test_report_renderers_create_markdown_pdf_and_docx() -> None:
    report = StructuredReport(
        title="Project Atlas",
        research_question="Who owns Project Atlas?",
        executive_summary="Project Atlas is owned by Operations Analytics.",
        scope_and_methodology="Authorized workspace retrieval only.",
        key_findings=["Operations Analytics owns Project Atlas."],
        detailed_analysis="The claim is supported by the uploaded source.",
        internal_evidence=[{"document_title": "atlas.txt"}],
        external_evidence=[],
        conflicting_evidence=[],
        information_gaps=[],
        limitations=["Internal corpus only."],
        conclusions=["Atlas ownership is supported."],
        citations=[{"citation_label": "S1", "document_title": "atlas.txt"}],
        generation_metadata={
            "pipeline_version": "research-v1",
            "outcome": "ANSWER_SUPPORTED",
            "confidence_category": "high",
        },
    )
    markdown = render_markdown(report)
    assert "## Citations" in markdown
    assert "atlas.txt" in markdown
    assert render_pdf(markdown).startswith(b"%PDF-1.4")
    assert render_docx(markdown).startswith(b"PK")


def test_download_token_signature_validates_and_rejects_tampering() -> None:
    job_id = uuid4()
    artifact_id = uuid4()
    expires, signature = sign_download_token(job_id, artifact_id, "markdown")
    assert verify_download_token(job_id, artifact_id, "markdown", expires, signature)
    assert not verify_download_token(job_id, artifact_id, "pdf", expires, signature)


def test_build_report_accepts_agent_response_without_hidden_reasoning() -> None:
    response = AgentQueryResponse(
        run_id=uuid4(),
        status=AgentRunStatus.COMPLETED,
        current_state=AgentStateName.COMPLETE,
        answer="Project Atlas is owned by Operations Analytics.",
        citations=[{"citation_label": "S1", "document_title": "atlas.txt"}],
        outcome="ANSWER_SUPPORTED",
        confidence_category="high",
        claims=[
            {
                "claim_text": "Project Atlas ownership is Operations Analytics.",
                "verification_status": "SUPPORTED",
            }
        ],
    )
    assert "Project Atlas" in render_markdown(response_to_report(response))


def response_to_report(response: AgentQueryResponse) -> StructuredReport:
    from app.agents.research import build_structured_report

    return build_structured_report(response, "Who owns Project Atlas?")
