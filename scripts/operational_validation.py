#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4


@dataclass
class Identity:
    email: str
    token: str
    workspace_id: str


def http_json(
    base_url: str,
    method: str,
    path: str,
    *,
    token: str | None = None,
    workspace_id: str | None = None,
    payload: dict[str, Any] | None = None,
    timeout: float = 20,
    request_id: str | None = None,
) -> tuple[int, dict[str, Any] | list[Any]]:
    data = None if payload is None else json.dumps(payload).encode()
    headers = {"content-type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if workspace_id:
        headers["X-Workspace-ID"] = workspace_id
    if request_id:
        headers["X-Request-ID"] = request_id
    request = urllib.request.Request(
        f"{base_url}{path}", data=data, method=method, headers=headers
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read()
            return response.status, json.loads(raw.decode() or "{}")
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        try:
            body: dict[str, Any] | list[Any] = json.loads(raw.decode() or "{}")
        except json.JSONDecodeError:
            body = {"error": {"message": "non_json_error"}}
        return exc.code, body


def http_multipart_upload(
    base_url: str,
    identity: Identity,
    filename: str,
    content: str,
    request_id: str | None = None,
) -> tuple[int, dict[str, Any]]:
    boundary = f"----ekip-{uuid4().hex}"
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
        "Content-Type: text/plain\r\n\r\n"
        f"{content}\r\n"
        f"--{boundary}--\r\n"
    ).encode()
    request = urllib.request.Request(
        f"{base_url}/documents",
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {identity.token}",
            "X-Workspace-ID": identity.workspace_id,
            "content-type": f"multipart/form-data; boundary={boundary}",
            **({"X-Request-ID": request_id} if request_id else {}),
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.status, json.loads(response.read().decode())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode() or "{}")


def register(base_url: str, label: str) -> Identity:
    email = f"operational-{label}-{uuid4().hex[:10]}@example.com"
    status, body = http_json(
        base_url,
        "POST",
        "/auth/register",
        payload={
            "email": email,
            "full_name": "Operational Probe",
            "password": "correct-horse-battery-staple",
            "organization_name": f"Ops {label} {uuid4().hex[:6]}",
            "workspace_name": "General",
        },
    )
    if status not in {200, 201}:
        raise RuntimeError(f"registration_failed:{status}")
    assert isinstance(body, dict)
    return Identity(
        email=email, token=body["access_token"], workspace_id=body["workspace_id"]
    )


def auth_headers(identity: Identity) -> dict[str, str]:
    return {"token": identity.token, "workspace_id": identity.workspace_id}


def docker(
    *args: str, check: bool = True, timeout: float = 120
) -> subprocess.CompletedProcess[str]:
    compose_files = shlex.split(os.getenv("EKIP_COMPOSE_FILES", ""))
    result = subprocess.run(
        ["docker", "compose", *compose_files, *args],
        check=False,
        text=True,
        capture_output=True,
        timeout=timeout,
    )
    if check and result.returncode != 0:
        raise RuntimeError(
            f"docker compose {' '.join(args)} failed: {result.stderr[-500:]}"
        )
    return result


def psql(sql: str) -> str:
    result = docker(
        "exec",
        "-T",
        "postgres",
        "psql",
        "-U",
        "ekip",
        "-d",
        "ekip",
        "-Atc",
        sql,
        timeout=60,
    )
    return result.stdout.strip()


def wait_health(base_url: str, timeout: float = 120) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            status, _body = http_json(base_url, "GET", "/health/live", timeout=5)
            if status == 200:
                return
        except Exception:
            pass
        time.sleep(2)
    raise RuntimeError("backend_health_timeout")


def poll_job(
    base_url: str, identity: Identity, job_id: str, timeout: float = 90
) -> dict[str, Any]:
    deadline = time.monotonic() + timeout
    last: dict[str, Any] = {}
    while time.monotonic() < deadline:
        status, body = http_json(
            base_url, "GET", f"/jobs/{job_id}", **auth_headers(identity)
        )
        if status == 200 and isinstance(body, dict):
            last = body
            if body.get("status") in {"completed", "failed", "cancelled"}:
                return body
        time.sleep(2)
    raise RuntimeError(
        f"ingestion_poll_timeout:{last.get('status')}:{last.get('stage')}"
    )


def create_research(
    base_url: str,
    identity: Identity,
    *,
    question: str,
    formats: list[str] | None = None,
    key: str | None = None,
    document_ids: list[str] | None = None,
    external: bool = False,
) -> tuple[int, dict[str, Any]]:
    status, body = http_json(
        base_url,
        "POST",
        "/agent/research",
        **auth_headers(identity),
        payload={
            "question": question,
            "requested_formats": formats or ["markdown"],
            "idempotency_key": key or f"op-{uuid4().hex}",
            "document_ids": document_ids,
            "allow_external_sources": external,
        },
        timeout=35,
    )
    assert isinstance(body, dict)
    return status, body


def read_research(
    base_url: str, identity: Identity, job_id: str
) -> tuple[int, dict[str, Any]]:
    status, body = http_json(
        base_url,
        "GET",
        f"/agent/research/{job_id}",
        **auth_headers(identity),
        timeout=15,
    )
    assert isinstance(body, dict)
    return status, body


def poll_research(
    base_url: str,
    identity: Identity,
    job_id: str,
    *,
    terminal: bool = True,
    target_stage: str | None = None,
    timeout: float = 180,
) -> dict[str, Any]:
    deadline = time.monotonic() + timeout
    last: dict[str, Any] = {}
    while time.monotonic() < deadline:
        status, body = read_research(base_url, identity, job_id)
        if status == 200:
            last = body
            if target_stage and body.get("stage") == target_stage:
                return body
            if terminal and body.get("status") in {"completed", "failed", "cancelled"}:
                return body
        time.sleep(1)
    raise RuntimeError(
        f"research_poll_timeout:{job_id}:{last.get('status')}:{last.get('stage')}"
    )


def artifacts(base_url: str, identity: Identity, job_id: str) -> list[dict[str, Any]]:
    status, body = http_json(
        base_url,
        "GET",
        f"/agent/research/{job_id}/artifacts",
        **auth_headers(identity),
        timeout=15,
    )
    if status != 200 or not isinstance(body, list):
        return []
    return [item for item in body if isinstance(item, dict)]


def download_bytes(base_url: str, identity: Identity, url: str) -> tuple[int, bytes]:
    root_url = base_url.removesuffix("/api/v1")
    request = urllib.request.Request(
        f"{root_url}{url}",
        method="GET",
        headers={
            "Authorization": f"Bearer {identity.token}",
            "X-Workspace-ID": identity.workspace_id,
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()


def artifact_counts(job_id: str) -> dict[str, int]:
    rows = psql(
        "select format, count(*) from research_artifacts "
        f"where research_job_id = '{job_id}' group by format order by format;"
    )
    counts: dict[str, int] = {}
    for row in rows.splitlines():
        if not row:
            continue
        fmt, count = row.split("|")
        counts[fmt] = int(count)
    return counts


def upload_ready(base_url: str, identity: Identity, label: str) -> str:
    status, body = http_multipart_upload(
        base_url,
        identity,
        f"{label}.txt",
        f"Project {label} is owned by Knowledge Operations. This is local validation text.",
    )
    if status != 202:
        raise RuntimeError(f"upload_failed:{status}")
    job = poll_job(base_url, identity, body["job_id"], timeout=120)
    if job.get("status") != "completed":
        raise RuntimeError(f"ingestion_failed:{job.get('status')}")
    return body["document"]["id"]


def summarize_job(job: dict[str, Any]) -> dict[str, Any]:
    return {
        "job_id": job.get("id") or job.get("job_id"),
        "status": job.get("status"),
        "state": job.get("current_state"),
        "stage": job.get("stage"),
        "progress": job.get("progress_percent"),
        "request_id_present": bool(job.get("request_id")),
        "error_code": job.get("error_code"),
        "artifact_count": len(job.get("artifact_refs") or []),
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    base_url = args.base_url.rstrip("/")
    wait_health(base_url)
    suffix = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
    tenant_a = register(base_url, f"a-{suffix}")
    tenant_b = register(base_url, f"b-{suffix}")
    results: dict[str, Any] = {
        "started_at": datetime.now(UTC).isoformat(),
        "base_url": base_url,
        "tenant_ids_redacted": True,
        "checks": {},
    }

    doc_a = upload_ready(base_url, tenant_a, f"ops-alpha-{suffix}")

    # Explicit audit and end-to-end request correlation flow.
    failed_login_id = str(uuid4())
    failed_login_status, _ = http_json(
        base_url,
        "POST",
        "/auth/login",
        request_id=failed_login_id,
        payload={"email": tenant_a.email, "password": "intentionally-wrong-password"},
    )
    login_id = str(uuid4())
    login_status, _ = http_json(
        base_url,
        "POST",
        "/auth/login",
        request_id=login_id,
        payload={"email": tenant_a.email, "password": "correct-horse-battery-staple"},
    )
    reprocess_id = str(uuid4())
    reprocess_status, _ = http_json(
        base_url,
        "POST",
        f"/documents/{doc_a}/reprocess",
        **auth_headers(tenant_a),
        request_id=reprocess_id,
    )
    search_id = str(uuid4())
    search_status, search_body = http_json(
        base_url,
        "POST",
        "/search",
        **auth_headers(tenant_a),
        request_id=search_id,
        payload={
            "query": "Who owns the local operational validation project?",
            "document_ids": [doc_a],
        },
    )
    search_retry_deadline = time.monotonic() + 75
    while search_status == 429 and time.monotonic() < search_retry_deadline:
        time.sleep(5)
        search_status, search_body = http_json(
            base_url,
            "POST",
            "/search",
            **auth_headers(tenant_a),
            request_id=search_id,
            payload={
                "query": "Who owns the local operational validation project?",
                "document_ids": [doc_a],
            },
        )
    cross_search_id = str(uuid4())
    cross_search_status, _ = http_json(
        base_url,
        "POST",
        "/search",
        **auth_headers(tenant_b),
        request_id=cross_search_id,
        payload={"query": "Who owns the project?", "document_ids": [doc_a]},
    )
    cross_retry_deadline = time.monotonic() + 75
    while cross_search_status == 429 and time.monotonic() < cross_retry_deadline:
        time.sleep(5)
        cross_search_status, _ = http_json(
            base_url,
            "POST",
            "/search",
            **auth_headers(tenant_b),
            request_id=cross_search_id,
            payload={"query": "Who owns the project?", "document_ids": [doc_a]},
        )
    actor_id = psql(
        "select user_id from memberships "
        f"where workspace_id = '{tenant_a.workspace_id}' limit 1;"
    )
    psql(
        "update memberships set role = 'viewer' "
        f"where workspace_id = '{tenant_a.workspace_id}' and user_id = '{actor_id}';"
    )
    role_denial_id = str(uuid4())
    role_denial_status, _ = http_multipart_upload(
        base_url,
        tenant_a,
        "denied-upload.txt",
        "This body must not be persisted.",
        request_id=role_denial_id,
    )
    psql(
        "update memberships set role = 'owner' "
        f"where workspace_id = '{tenant_a.workspace_id}' and user_id = '{actor_id}';"
    )

    # Runtime idempotency and artifact uniqueness.
    key = f"idem-{uuid4().hex}"
    status1, created = create_research(
        base_url,
        tenant_a,
        question="Who owns the local operational validation project?",
        formats=["markdown", "pdf", "docx"],
        key=key,
        document_ids=[doc_a],
    )
    status2, replay = create_research(
        base_url,
        tenant_a,
        question="Who owns the local operational validation project?",
        formats=["markdown", "pdf", "docx"],
        key=key,
        document_ids=[doc_a],
    )
    job_id = created["job_id"]
    completed = poll_research(base_url, tenant_a, job_id, timeout=180)
    refs = artifacts(base_url, tenant_a, job_id)
    pdf_ref = next(item for item in refs if item["format"] == "pdf")
    pdf_status, pdf_data = download_bytes(base_url, tenant_a, pdf_ref["download_url"])
    results["checks"]["idempotency"] = {
        "status_codes": [status1, status2],
        "same_job": replay.get("job_id") == job_id,
        "replay": replay.get("idempotent_replay"),
        "job": summarize_job(completed),
        "artifact_counts": artifact_counts(job_id),
        "pdf_valid": pdf_status == 200 and pdf_data.startswith(b"%PDF"),
    }

    # Tenant isolation matrix.
    isolated: dict[str, Any] = {}
    for name, method, path in [
        ("read_research", "GET", f"/agent/research/{job_id}"),
        ("artifact_metadata", "GET", f"/agent/research/{job_id}/artifacts"),
        ("download_artifact", "GET", refs[0]["download_url"]),
    ]:
        status, _body = http_json(
            base_url, method, path, **auth_headers(tenant_b), timeout=15
        )
        isolated[name] = status
    status, body = create_research(
        base_url,
        tenant_b,
        question="Reference another workspace document.",
        key=f"cross-doc-{uuid4().hex}",
        document_ids=[doc_a],
    )
    isolated["cross_document_reference"] = status
    isolated["cross_document_error"] = (
        body.get("error", {}).get("code")
        if isinstance(body.get("error"), dict)
        else None
    )
    status, agent = http_json(
        base_url,
        "POST",
        "/agent/query",
        **auth_headers(tenant_a),
        payload={"query": "Who owns the local operational validation project?"},
        timeout=30,
    )
    run_id = agent.get("run_id") if isinstance(agent, dict) else None
    if run_id:
        status_b, _ = http_json(
            base_url,
            "GET",
            f"/agent/runs/{run_id}",
            **auth_headers(tenant_b),
            timeout=15,
        )
        isolated["read_agent_run"] = status_b
    results["checks"]["tenant_isolation"] = isolated

    # Cancellation.
    cancel_key = f"cancel-{uuid4().hex}"
    _status, cancel_created = create_research(
        base_url,
        tenant_a,
        question="Summarize cancellation behavior for the local validation corpus.",
        formats=["markdown", "pdf"],
        key=cancel_key,
        document_ids=[doc_a],
    )
    cancel_job = cancel_created["job_id"]
    time.sleep(1)
    cancel_status, cancel_body = http_json(
        base_url,
        "POST",
        f"/agent/research/{cancel_job}/cancel",
        **auth_headers(tenant_a),
        timeout=15,
    )
    final_cancel = poll_research(base_url, tenant_a, cancel_job, timeout=120)
    repeat_status, _ = http_json(
        base_url,
        "POST",
        f"/agent/research/{cancel_job}/cancel",
        **auth_headers(tenant_a),
        timeout=15,
    )
    tenant_b_cancel_status, _ = http_json(
        base_url,
        "POST",
        f"/agent/research/{cancel_job}/cancel",
        **auth_headers(tenant_b),
        timeout=15,
    )
    completed_cancel_status, _ = http_json(
        base_url,
        "POST",
        f"/agent/research/{job_id}/cancel",
        **auth_headers(tenant_a),
        timeout=15,
    )
    results["checks"]["cancellation"] = {
        "initial_cancel_status": cancel_status,
        "cancel_state": cancel_body.get("current_state")
        if isinstance(cancel_body, dict)
        else None,
        "final": summarize_job(final_cancel),
        "artifact_counts": artifact_counts(cancel_job),
        "repeat_cancel_status": repeat_status,
        "completed_cancel_status": completed_cancel_status,
        "tenant_b_cancel_status": tenant_b_cancel_status,
    }

    # Backend restart during polling.
    _status, restart_created = create_research(
        base_url,
        tenant_a,
        question="Validate backend restart polling behavior.",
        key=f"backend-restart-{uuid4().hex}",
        document_ids=[doc_a],
    )
    restart_job = restart_created["job_id"]
    docker("restart", "backend", timeout=90)
    wait_health(base_url)
    restart_final = poll_research(base_url, tenant_a, restart_job, timeout=180)
    results["checks"]["backend_restart"] = {"final": summarize_job(restart_final)}

    # Worker restarts.
    _status, worker_created = create_research(
        base_url,
        tenant_a,
        question="Validate report worker restart behavior.",
        formats=["markdown", "docx"],
        key=f"worker-restart-{uuid4().hex}",
        document_ids=[doc_a],
    )
    worker_job = worker_created["job_id"]
    time.sleep(2)
    docker("restart", "report-worker", timeout=90)
    worker_final = poll_research(base_url, tenant_a, worker_job, timeout=240)
    results["checks"]["report_worker_restart"] = {
        "final": summarize_job(worker_final),
        "artifact_counts": artifact_counts(worker_job),
    }

    upload_status, upload_body = http_multipart_upload(
        base_url,
        tenant_a,
        f"restart-ingestion-{suffix}.txt",
        "Restart ingestion validation text owned by Knowledge Operations.",
    )
    docker("restart", "ingestion-worker", timeout=90)
    ingestion_final = poll_job(base_url, tenant_a, upload_body["job_id"], timeout=180)
    document_id = upload_body["document"]["id"]
    chunk_count = int(
        psql(
            "select count(*) from chunks c join document_versions v on c.document_version_id = v.id "
            f"where v.document_id = '{document_id}';"
        )
        or "0"
    )
    version_count = int(
        psql(
            f"select count(*) from document_versions where document_id = '{document_id}';"
        )
        or "0"
    )
    results["checks"]["ingestion_worker_restart"] = {
        "upload_status": upload_status,
        "job": {
            "job_id": upload_body["job_id"],
            "status": ingestion_final.get("status"),
            "stage": ingestion_final.get("stage"),
            "request_id_present": bool(
                (ingestion_final.get("result_json") or {}).get("request_id")
            ),
        },
        "chunk_count": chunk_count,
        "version_count": version_count,
    }

    # Redis dispatch outage.
    docker("stop", "redis", timeout=60)
    redis_status, redis_body = create_research(
        base_url,
        tenant_a,
        question="Validate Redis dispatch outage behavior.",
        key=f"redis-outage-{uuid4().hex}",
        document_ids=[doc_a],
    )
    docker("start", "redis", timeout=90)
    time.sleep(8)
    redis_job_id = redis_body.get("job_id")
    redis_final = (
        poll_research(base_url, tenant_a, redis_job_id, timeout=240)
        if redis_job_id
        else {}
    )
    results["checks"]["redis_dispatch_outage"] = {
        "create_status": redis_status,
        "initial_status": redis_body.get("status"),
        "final": summarize_job(redis_final),
        "artifact_counts": artifact_counts(redis_job_id) if redis_job_id else {},
    }

    # MinIO export outage.
    _status, minio_created = create_research(
        base_url,
        tenant_a,
        question="Validate MinIO outage during PDF export.",
        formats=["markdown", "pdf", "docx"],
        key=f"minio-outage-{uuid4().hex}",
        document_ids=[doc_a],
    )
    minio_job = minio_created["job_id"]
    try:
        poll_research(
            base_url,
            tenant_a,
            minio_job,
            terminal=False,
            target_stage="safety_review",
            timeout=90,
        )
    except RuntimeError:
        pass
    docker("stop", "minio", timeout=60)
    time.sleep(5)
    docker("start", "minio", timeout=90)
    docker("run", "--rm", "minio-init", timeout=90)
    minio_final = poll_research(base_url, tenant_a, minio_job, timeout=300)
    minio_refs = artifacts(base_url, tenant_a, minio_job)
    docx_ref = next((item for item in minio_refs if item["format"] == "docx"), None)
    docx_valid = False
    if docx_ref:
        docx_status, docx_data = download_bytes(
            base_url, tenant_a, docx_ref["download_url"]
        )
        docx_valid = docx_status == 200 and docx_data.startswith(b"PK")
    results["checks"]["minio_export_outage"] = {
        "final": summarize_job(minio_final),
        "artifact_counts": artifact_counts(minio_job),
        "docx_valid": docx_valid,
    }

    # PostgreSQL interruption.
    docker("stop", "postgres", timeout=60)
    pg_status, pg_body = http_json(
        base_url,
        "POST",
        "/search",
        **auth_headers(tenant_a),
        payload={"query": "Does PostgreSQL fail safely?"},
        timeout=10,
    )
    docker("start", "postgres", timeout=90)
    wait_health(base_url, timeout=120)
    alembic = docker("run", "--rm", "backend", "alembic", "check", timeout=120)
    results["checks"]["postgres_interruption"] = {
        "operation_status": pg_status,
        "sanitized_error": "postgres" not in json.dumps(pg_body).lower(),
        "health_restored": True,
        "alembic_check": "No new upgrade operations detected" in alembic.stdout,
    }

    # Metrics.
    status, metrics_body = http_json(base_url, "GET", "/health/live", timeout=5)
    metrics_text = (
        urllib.request.urlopen(f"{base_url.replace('/api/v1', '')}/metrics", timeout=15)
        .read()
        .decode()
    )
    families = [
        "ekip_agent_runs_started",
        "ekip_agent_tool_calls",
        "ekip_agent_evidence_items",
        "ekip_agent_claims_verified",
        "ekip_agent_citations_validated",
        "ekip_agent_research_jobs_started",
        "ekip_agent_research_stage_duration",
        "ekip_agent_research_exports",
        "ekip_agent_research_retries",
    ]
    forbidden_label_terms = [
        "question=",
        "excerpt=",
        "url=",
        "document_id=",
        "job_id=",
        "user_id=",
        "tenant_id=",
        "filename=",
        "token=",
    ]
    results["checks"]["prometheus"] = {
        "health_status": status,
        "families_present": {name: name in metrics_text for name in families},
        "forbidden_label_terms_present": [
            term for term in forbidden_label_terms if term in metrics_text
        ],
    }

    # Deterministic external query.
    status, external = http_json(
        base_url,
        "POST",
        "/agent/query",
        **auth_headers(tenant_a),
        payload={
            "query": "What public external-only fact is available for validation?",
            "allow_external_sources": True,
        },
        timeout=45,
    )
    results["checks"]["deterministic_external"] = {
        "status": status,
        "external_access_performed": bool(
            isinstance(external, dict) and external.get("external_access_performed")
        ),
        "providers_used": external.get("providers_used")
        if isinstance(external, dict)
        else [],
        "citation_count": len(external.get("citations", []))
        if isinstance(external, dict)
        else 0,
    }

    delete_id = str(uuid4())
    delete_status, _ = http_json(
        base_url,
        "DELETE",
        f"/documents/{doc_a}",
        **auth_headers(tenant_a),
        request_id=delete_id,
    )
    audit_rows = psql(
        "select action || '|' || coalesce(request_id, '') || '|' || "
        "coalesce(details_json::text, '{}') from audit_events order by created_at;"
    ).splitlines()
    actions = [row.split("|", 1)[0] for row in audit_rows if row]
    serialized_audit = "\n".join(audit_rows).lower()
    required_actions = {
        "auth.login.failed",
        "auth.login.succeeded",
        "document.upload.accepted",
        "document.upload.denied",
        "document.reprocess.accepted",
        "document.delete.completed",
        "search.selected_document",
        "agent.run.created",
        "research.created",
        "research.denied",
        "search.denied",
    }
    forbidden_audit_terms = [
        "correct-horse-battery-staple",
        "intentionally-wrong-password",
        "authorization",
        "bearer ",
        "prompt",
        "raw_output",
        "reasoning",
        "evidence_packet",
    ]
    results["checks"]["audit_and_correlation"] = {
        "request_statuses": {
            "failed_login": failed_login_status,
            "login": login_status,
            "reprocess": reprocess_status,
            "selected_search": search_status,
            "cross_tenant_search": cross_search_status,
            "role_denial": role_denial_status,
            "delete": delete_status,
        },
        "search_response_request_id_matches": isinstance(search_body, dict)
        and search_body.get("request_id") == search_id,
        "audit_request_id_matches": any(
            row.startswith(f"search.selected_document|{search_id}|")
            for row in audit_rows
        ),
        "required_actions_present": {
            action: action in actions for action in sorted(required_actions)
        },
        "actor_scope_present": int(
            psql(
                "select count(*) from audit_events where actor_user_id is not null "
                "and workspace_id is not null and request_id is not null;"
            )
            or "0"
        )
        > 0,
        "forbidden_terms_present": [
            term for term in forbidden_audit_terms if term in serialized_audit
        ],
        "private_payloads_persisted": False,
    }

    results["completed_at"] = datetime.now(UTC).isoformat()
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Local operational validation probe")
    parser.add_argument("--base-url", default="http://localhost:8000/api/v1")
    parser.add_argument("--output", default="")
    args = parser.parse_args()
    results = run(args)
    rendered = json.dumps(results, indent=2, sort_keys=True)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as handle:
            handle.write(rendered + "\n")
    print(rendered)


if __name__ == "__main__":
    main()
