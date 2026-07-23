from uuid import UUID

from app.agents.research import ResearchState
from app.core.config import settings
from app.db.models import ResearchJob, Workspace
from app.db.session import AsyncSessionLocal


def _upload_ready_document(client, headers, filename: str, content: str) -> str:
    response = client.post(
        "/api/v1/documents",
        headers=headers,
        files={"file": (filename, content.encode(), "text/plain")},
    )
    assert response.status_code == 202
    document_id = response.json()["document"]["id"]
    job_id = response.json()["job_id"]
    job = client.get(f"/api/v1/jobs/{job_id}", headers=headers)
    assert job.status_code == 200
    assert job.json()["status"] == "completed"
    return document_id


def _register_user(client, email: str, organization: str, workspace: str) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "full_name": "Research User",
            "password": "correct-horse-battery-staple",
            "organization_name": organization,
            "workspace_name": workspace,
        },
    )
    if response.status_code == 409:
        response = client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": "correct-horse-battery-staple"},
        )
    assert response.status_code in {200, 201}
    auth = response.json()
    return {
        "Authorization": f"Bearer {auth['access_token']}",
        "X-Workspace-ID": auth["workspace_id"],
    }


def test_research_feature_flag_disabled(client, auth_headers, monkeypatch) -> None:
    monkeypatch.setattr(settings, "agent_research_enabled", False)
    response = client.post(
        "/api/v1/agent/research",
        headers=auth_headers,
        json={"question": "Summarize Project Atlas ownership."},
    )
    assert response.status_code == 403
    assert response.json()["code"] == "AGENT_RESEARCH_FEATURE_DISABLED"


def test_research_report_lifecycle_exports_and_signed_downloads(
    client, auth_headers, monkeypatch
) -> None:
    monkeypatch.setattr(settings, "agent_research_enabled", True)
    document_id = _upload_ready_document(
        client,
        auth_headers,
        "research-atlas.txt",
        "Project Atlas is owned by Operations Analytics.",
    )
    response = client.post(
        "/api/v1/agent/research",
        headers=auth_headers,
        json={
            "question": "Who owns Project Atlas?",
            "document_ids": [document_id],
            "requested_formats": ["markdown", "pdf", "docx"],
            "idempotency_key": "atlas-report-1",
        },
    )
    assert response.status_code == 202
    job_id = response.json()["job_id"]

    replay = client.post(
        "/api/v1/agent/research",
        headers=auth_headers,
        json={
            "question": "Who owns Project Atlas?",
            "document_ids": [document_id],
            "requested_formats": ["markdown", "pdf", "docx"],
            "idempotency_key": "atlas-report-1",
        },
    )
    assert replay.status_code == 202
    assert replay.json()["job_id"] == job_id
    assert replay.json()["idempotent_replay"] is True

    detail = client.get(f"/api/v1/agent/research/{job_id}", headers=auth_headers)
    assert detail.status_code == 200
    body = detail.json()
    assert body["status"] == "completed"
    assert body["current_state"] == ResearchState.COMPLETED.value
    assert body["source_count"] >= 1
    assert body["verified_citation_count"] >= 1
    assert body["artifact_refs"]
    assert "Operations Analytics" in body["result_json"]["report"]["executive_summary"]

    artifacts = client.get(f"/api/v1/agent/research/{job_id}/artifacts", headers=auth_headers)
    assert artifacts.status_code == 200
    refs = artifacts.json()
    assert {item["format"] for item in refs} == {"markdown", "pdf", "docx"}
    assert all("object_key" not in item for item in refs)
    assert all("signed_url_signature" not in item for item in refs)
    assert all(item["checksum_sha256"] for item in refs)
    for item in refs:
        download = client.get(item["download_url"], headers=auth_headers)
        assert download.status_code == 200
        if item["format"] == "markdown":
            assert b"Operations Analytics" in download.content
        if item["format"] == "pdf":
            assert download.content.startswith(b"%PDF")
        if item["format"] == "docx":
            assert download.content.startswith(b"PK")

    tampered = client.get(
        refs[0]["download_url"].replace("signature=", "signature=tampered"),
        headers=auth_headers,
    )
    assert tampered.status_code == 403


def test_research_report_knowledge_absence_and_conflict(client, auth_headers, monkeypatch) -> None:
    monkeypatch.setattr(settings, "agent_research_enabled", True)
    isolated_headers = _register_user(
        client,
        "research-absence@example.com",
        "Research Absence Org",
        "Absence Workspace",
    )
    absent = client.post(
        "/api/v1/agent/research",
        headers=isolated_headers,
        json={"question": "What is the capital of Virellia?"},
    )
    assert absent.status_code == 202
    absent_detail = client.get(
        f"/api/v1/agent/research/{absent.json()['job_id']}", headers=isolated_headers
    )
    assert absent_detail.status_code == 200
    absent_report = absent_detail.json()["result_json"]["report"]
    assert absent_report["generation_metadata"]["outcome"] in {
        "KNOWLEDGE_ABSENT",
        "INSUFFICIENT_EVIDENCE",
    }
    assert absent_report["information_gaps"]

    _upload_ready_document(
        client,
        auth_headers,
        "research-conflict.txt",
        "Project Chronos launched in March 2025. Project Chronos launched in April 2026.",
    )
    conflict = client.post(
        "/api/v1/agent/research",
        headers=auth_headers,
        json={"question": "When did Project Chronos launch?"},
    )
    assert conflict.status_code == 202
    conflict_detail = client.get(
        f"/api/v1/agent/research/{conflict.json()['job_id']}", headers=auth_headers
    )
    assert conflict_detail.status_code == 200
    report = conflict_detail.json()["result_json"]["report"]
    assert report["generation_metadata"]["outcome"] == "CONFLICTING_EVIDENCE"
    assert report["conflicting_evidence"]


def test_research_cancel_and_tenant_scope(client, auth_headers, monkeypatch) -> None:
    monkeypatch.setattr(settings, "agent_research_enabled", True)
    other_headers = _register_user(
        client,
        "research-other@example.com",
        "Other Research Org",
        "Research Workspace",
    )
    response = client.post(
        "/api/v1/agent/research",
        headers=auth_headers,
        json={
            "question": "Summarize the available Project Nimbus documentation.",
            "idempotency_key": "cancel-this-job",
        },
    )
    assert response.status_code == 202
    job_id = response.json()["job_id"]
    assert client.get(f"/api/v1/agent/research/{job_id}", headers=other_headers).status_code == 404

    created = _create_pending_research_job(client, auth_headers)
    cancel = client.post(
        f"/api/v1/agent/research/{created}/cancel",
        headers=auth_headers,
    )
    assert cancel.status_code == 200
    assert cancel.json()["current_state"] == ResearchState.CANCEL_REQUESTED.value


def test_research_rejects_cross_workspace_document_scope(client, auth_headers, monkeypatch) -> None:
    monkeypatch.setattr(settings, "agent_research_enabled", True)
    document_id = _upload_ready_document(
        client,
        auth_headers,
        "research-scope.txt",
        "Project Scope belongs only in this workspace.",
    )
    other_headers = _register_user(
        client,
        "research-workspace-other@example.com",
        "Workspace Isolation Org",
        "Other Workspace",
    )
    response = client.post(
        "/api/v1/agent/research",
        headers=other_headers,
        json={
            "question": "Summarize Project Scope.",
            "document_ids": [document_id],
        },
    )
    assert response.status_code == 403


def test_research_concurrency_limit_returns_typed_error(client, auth_headers, monkeypatch) -> None:
    monkeypatch.setattr(settings, "agent_research_enabled", True)
    monkeypatch.setattr(settings, "agent_research_max_concurrent_per_user", 1)
    _create_pending_research_job(client, auth_headers)

    response = client.post(
        "/api/v1/agent/research",
        headers=auth_headers,
        json={"question": "Start one more research job beyond the user limit."},
    )

    assert response.status_code == 429
    assert response.json()["error"]["code"] == "CONCURRENCY_LIMIT_REACHED"


def test_request_body_size_limit_returns_typed_error(client, monkeypatch) -> None:
    monkeypatch.setattr(settings, "max_request_body_bytes", 10)

    response = client.post(
        "/api/v1/search",
        content=b"x" * 32,
        headers={"content-type": "application/json"},
    )

    assert response.status_code == 413
    assert response.json()["error"]["code"] == "REQUEST_TOO_LARGE"


def test_existing_search_endpoint_unchanged(client, auth_headers) -> None:
    _upload_ready_document(
        client,
        auth_headers,
        "research-search-regression.txt",
        "The search regression token is blue-harbor.",
    )
    response = client.post(
        "/api/v1/search",
        headers=auth_headers,
        json={"query": "What is the search regression token?"},
    )
    assert response.status_code == 200
    assert "blue-harbor" in response.json()["answer"].lower()


def _create_pending_research_job(client, auth_headers) -> str:
    import asyncio

    user = client.get("/api/v1/auth/me", headers=auth_headers).json()
    workspace_id = UUID(auth_headers["X-Workspace-ID"])

    async def create() -> str:
        async with AsyncSessionLocal() as session:
            workspace = await session.get(Workspace, workspace_id)
            assert workspace is not None
            job = ResearchJob(
                tenant_id=workspace.organization_id,
                workspace_id=workspace_id,
                user_id=UUID(user["id"]),
                question="Pending cancellable research job.",
                status="pending",
                current_state=ResearchState.PENDING.value,
                stage="queued",
                requested_formats=["markdown"],
                result_json={},
            )
            session.add(job)
            await session.commit()
            return str(job.id)

    return asyncio.run(create())
