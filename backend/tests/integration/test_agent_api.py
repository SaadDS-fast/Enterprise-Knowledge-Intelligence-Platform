from uuid import UUID

import pytest
from sqlalchemy import select

from app.agents.errors import AgentCancelledError
from app.agents.orchestrator import AgentOrchestrator
from app.agents.schemas import AgentQueryRequest
from app.core.config import settings
from app.db.models import AgentRun, AgentStep, AuditEvent, Workspace
from app.db.session import AsyncSessionLocal
from app.tenancy.context import TenantContext


def test_agent_feature_flag_disabled(client, auth_headers, monkeypatch) -> None:
    monkeypatch.setattr(settings, "agentic_rag_enabled", False)
    response = client.post(
        "/api/v1/agent/query",
        headers=auth_headers,
        json={"query": "Who owns Project Atlas?"},
    )
    assert response.status_code == 403
    assert response.json()["code"] == "AGENT_FEATURE_DISABLED"


def test_agent_query_persists_safe_summaries_without_chain_of_thought(
    client, auth_headers, monkeypatch
) -> None:
    monkeypatch.setattr(settings, "agentic_rag_enabled", True)
    response = client.post(
        "/api/v1/agent/query",
        headers=auth_headers,
        json={"query": "Who owns Project Atlas?"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    run_id = UUID(body["run_id"])
    assert body["safe_plan_summary"] == (
        "Internal document search selected; Evidence verification selected"
    )
    detail = client.get(f"/api/v1/agent/runs/{run_id}", headers=auth_headers)
    assert detail.status_code == 200
    detail_body = detail.json()
    persisted_text = str(detail_body).lower()
    assert "chain-of-thought" not in persisted_text
    assert "private reasoning" not in persisted_text
    assert detail_body["workspace_id"] == auth_headers["X-Workspace-ID"]
    assert detail_body["steps"]
    assert detail_body["tool_calls"]


def test_agent_run_tenant_scope_preserved(client, auth_headers, monkeypatch) -> None:
    monkeypatch.setattr(settings, "agentic_rag_enabled", True)
    response = client.post(
        "/api/v1/agent/query",
        headers=auth_headers,
        json={"query": "What evidence exists?"},
    )
    assert response.status_code == 200
    run_id = response.json()["run_id"]
    other = client.post(
        "/api/v1/auth/register",
        json={
            "email": "agent-other@example.com",
            "full_name": "Other Agent",
            "password": "correct-horse-battery-staple",
            "organization_name": "Other Agent Org",
            "workspace_name": "General",
        },
    )
    if other.status_code == 409:
        other = client.post(
            "/api/v1/auth/login",
            json={"email": "agent-other@example.com", "password": "correct-horse-battery-staple"},
        )
    auth = other.json()
    other_headers = {
        "Authorization": f"Bearer {auth['access_token']}",
        "X-Workspace-ID": auth["workspace_id"],
    }
    forbidden = client.get(f"/api/v1/agent/runs/{run_id}", headers=other_headers)
    assert forbidden.status_code == 404


@pytest.mark.asyncio
async def test_agent_cancellation_is_persisted_safely(client, auth_headers) -> None:
    me = client.get("/api/v1/auth/me", headers=auth_headers)
    assert me.status_code == 200
    user_id = UUID(me.json()["id"])
    workspace_id = UUID(auth_headers["X-Workspace-ID"])
    async with AsyncSessionLocal() as session:
        workspace = await session.get(Workspace, workspace_id)
        assert workspace is not None
        tenant = TenantContext(
            user_id=user_id,
            workspace_id=workspace_id,
            organization_id=workspace.organization_id,
            role="owner",
        )
        with pytest.raises(AgentCancelledError):
            await AgentOrchestrator().run(
                session,
                tenant=tenant,
                payload=AgentQueryRequest(query="Cancel this run"),
                request_id="cancel-test",
                cancel_requested=True,
            )
        run = (
            await session.scalars(
                select(AgentRun).where(AgentRun.request_id == "cancel-test").limit(1)
            )
        ).one()
        assert run.status == "cancelled"
        assert run.current_state == "cancelled"
        assert run.error_code == "AGENT_CANCELLED"


@pytest.mark.asyncio
async def test_agent_safe_persistence_and_audit_event() -> None:
    async with AsyncSessionLocal() as session:
        run = (
            await session.scalars(
                select(AgentRun).where(AgentRun.safe_plan_summary.is_not(None)).limit(1)
            )
        ).first()
        assert run is not None
        assert "Internal document search selected" in (run.safe_plan_summary or "")
        steps = (await session.scalars(select(AgentStep).where(AgentStep.run_id == run.id))).all()
        assert steps
        assert all("thought" not in step.summary.lower() for step in steps)
        audit = (
            await session.scalars(
                select(AuditEvent).where(
                    AuditEvent.resource_type == "agent_run",
                    AuditEvent.resource_id == str(run.id),
                )
            )
        ).first()
        assert audit is not None


def test_existing_search_regression(client, auth_headers) -> None:
    response = client.post(
        "/api/v1/search",
        headers=auth_headers,
        json={"query": "Who owns Project Atlas?"},
    )
    assert response.status_code == 200
    body = response.json()
    assert "answer" in body
    assert "retrieval_diagnosis" in body
