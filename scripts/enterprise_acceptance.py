#!/usr/bin/env python3
"""Bounded enterprise workflow acceptance against a disposable EKIP runtime."""

from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
import time
import urllib.error
import urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parent))
from enterprise_corpus import _content, corpus, render  # noqa: E402


@dataclass(frozen=True)
class Identity:
    tenant: str
    token: str
    workspace_id: str


@dataclass(frozen=True)
class Probe:
    operation: str
    status: int
    latency_ms: float
    ok: bool


def percentile(values: list[float], percentile_value: int) -> float:
    if not values:
        return 0.0
    values = sorted(values)
    index = min(len(values) - 1, math.ceil(percentile_value / 100 * len(values)) - 1)
    return round(values[index], 2)


def json_request(
    base_url: str,
    method: str,
    path: str,
    *,
    identity: Identity | None = None,
    payload: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    timeout: float = 60,
) -> tuple[int, Any]:
    request_headers = {"content-type": "application/json", **(headers or {})}
    if identity:
        request_headers.update(
            {
                "authorization": f"Bearer {identity.token}",
                "x-workspace-id": identity.workspace_id,
            }
        )
    request = urllib.request.Request(  # noqa: S310 -- caller supplies validated local base URL
        f"{base_url}{path}",
        method=method,
        headers=request_headers,
        data=None if payload is None else json.dumps(payload).encode(),
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
            return response.status, json.loads(response.read() or b"{}")
    except urllib.error.HTTPError as error:
        raw = error.read()
        try:
            body = json.loads(raw or b"{}")
        except json.JSONDecodeError:
            body = {"error": "sanitized_non_json_error"}
        return error.code, body


def register(base_url: str, tenant: str) -> Identity:
    suffix = uuid4().hex[:12]
    status, body = json_request(
        base_url,
        "POST",
        "/auth/register",
        payload={
            "email": (
                f"enterprise-{tenant.lower().replace(' ', '-')}-{suffix}@validation.localhost.com"
            ),
            "full_name": f"Synthetic {tenant} Administrator",
            "password": "EnterpriseReleasePass123!",
            "organization_name": f"Aurora Meridian {tenant} {suffix}",
            "workspace_name": "Enterprise Release",
        },
    )
    if status not in {200, 201}:
        raise RuntimeError(f"registration failed for {tenant}: {status}")
    return Identity(tenant, body["access_token"], body["workspace_id"])


def upload(
    base_url: str, identity: Identity, record: dict[str, Any]
) -> tuple[Probe, dict[str, Any]]:
    index = int(str(record["synthetic_document_id"]).split("-")[-1])
    data = render(str(record["file_type"]), _content(index, str(record["department"])))
    boundary = f"----ekip-enterprise-{uuid4().hex}"
    prefix = (
        f'--{boundary}\r\nContent-Disposition: form-data; name="file"; '
        f'filename="{record["filename"]}"\r\nContent-Type: {record["mime_type"]}\r\n\r\n'
    ).encode()
    body = prefix + data + f"\r\n--{boundary}--\r\n".encode()
    request = urllib.request.Request(  # noqa: S310 -- validated local runtime URL
        f"{base_url}/documents",
        method="POST",
        data=body,
        headers={
            "authorization": f"Bearer {identity.token}",
            "x-workspace-id": identity.workspace_id,
            "content-type": f"multipart/form-data; boundary={boundary}",
        },
    )
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=90) as response:  # noqa: S310
            payload = json.loads(response.read())
            status = response.status
    except urllib.error.HTTPError as error:
        status = error.code
        payload = json.loads(error.read() or b"{}")
    latency = (time.perf_counter() - started) * 1000
    return Probe("upload", status, latency, status == 202), payload


def wait_job(base_url: str, identity: Identity, job_id: str) -> tuple[str, float, dict[str, Any]]:
    started = time.perf_counter()
    deadline = started + 120
    last: dict[str, Any] = {}
    while time.perf_counter() < deadline:
        status, body = json_request(base_url, "GET", f"/jobs/{job_id}", identity=identity)
        if status == 200 and isinstance(body, dict):
            last = body
            if body.get("status") in {"completed", "failed", "cancelled"}:
                return str(body["status"]), (time.perf_counter() - started) * 1000, body
        time.sleep(0.25)
    return "timeout", (time.perf_counter() - started) * 1000, last


def timed_json(*args: Any, operation: str, **kwargs: Any) -> tuple[Probe, Any]:
    started = time.perf_counter()
    status, body = json_request(*args, **kwargs)
    latency = (time.perf_counter() - started) * 1000
    return Probe(operation, status, latency, status < 500), body


def assert_safe_search(body: dict[str, Any], identity: Identity) -> None:
    state = body.get("response_state") or {}
    primary = state.get("primary_state")
    assert primary, f"missing canonical state: {body}"
    if primary in {"SUPPORTED", "SUPPORTED_COMPOSITE"}:
        claims = state.get("claims") or []
        assert claims and all(claim.get("citation_ids") for claim in claims)
    serialized = json.dumps(body).casefold()
    assert "chain_of_thought" not in serialized
    assert "prompt_text" not in serialized
    assert identity.workspace_id not in {
        str(item.get("workspace_id")) for item in body.get("evidence", [])
    }


def run(base_url: str, upload_workers: int) -> dict[str, Any]:
    identities = {name: register(base_url, name) for name in ("Tenant A", "Tenant B", "Tenant C")}
    records = [dict(item) for item in corpus()]
    records_by_id = {str(item["synthetic_document_id"]): item for item in records}
    uploads: list[Probe] = []
    jobs: list[tuple[Identity, str, str]] = []
    documents: dict[str, tuple[Identity, str]] = {}
    with ThreadPoolExecutor(max_workers=upload_workers) as pool:
        futures = {
            pool.submit(upload, base_url, identities[str(record["tenant"])], record): record
            for record in records
        }
        for future in as_completed(futures):
            record = futures[future]
            probe, body = future.result()
            uploads.append(probe)
            if probe.ok:
                identity = identities[str(record["tenant"])]
                jobs.append(
                    (
                        identity,
                        str(body["job_id"]),
                        str(record["synthetic_document_id"]),
                    )
                )
                documents[str(record["synthetic_document_id"])] = (
                    identity,
                    str(body["document"]["id"]),
                )
    ingestion: list[tuple[str, float, dict[str, Any], str]] = []
    with ThreadPoolExecutor(max_workers=upload_workers) as pool:
        futures = {
            pool.submit(wait_job, base_url, identity, job_id): synthetic_id
            for identity, job_id, synthetic_id in jobs
        }
        for future in as_completed(futures):
            ingestion.append((*future.result(), futures[future]))

    authoritative_documents: dict[str, tuple[Identity, str]] = {}
    ready_documents: list[tuple[Identity, str]] = []
    ready_by_synthetic_id: dict[str, tuple[Identity, str]] = {}
    for identity in identities.values():
        status, items = json_request(base_url, "GET", "/documents", identity=identity)
        assert status == 200
        for item in items:
            synthetic_id = str(item["title"]).split("-")[1].upper()
            authoritative_documents[f"AMG-{synthetic_id}"] = (identity, str(item["id"]))
            if item["status"] == "ready":
                ready_documents.append((identity, str(item["id"])))
                ready_by_synthetic_id[f"AMG-{synthetic_id}"] = (
                    identity,
                    str(item["id"]),
                )
    assert len(authoritative_documents) == len(documents)
    documents = authoritative_documents

    search_probes: list[Probe] = []
    search_states: Counter[str] = Counter()
    direct_fact_documents = [
        (document_id, scoped)
        for document_id, scoped in sorted(ready_by_synthetic_id.items())
        if records_by_id[document_id]["file_type"] in {"docx", "txt", "md", "html", "csv"}
    ]
    for _document_id, (identity, stored_id) in direct_fact_documents[:30]:
        query = "Who is the policy owner?"
        probe, body = timed_json(
            base_url,
            "POST",
            "/search",
            identity=identity,
            payload={"query": query, "document_ids": [stored_id]},
            operation="search",
        )
        if probe.status == 429:
            time.sleep(1.1)
            probe, body = timed_json(
                base_url,
                "POST",
                "/search",
                identity=identity,
                payload={"query": query, "document_ids": [stored_id]},
                operation="search_retry",
            )
        assert probe.status == 200, f"search failed: {probe.status}: {body}"
        search_probes.append(probe)
        assert_safe_search(body, identity)
        search_states.update([(body.get("response_state") or {}).get("primary_state", "missing")])
        time.sleep(0.1)

    tenant_a = identities["Tenant A"]
    tenant_b = identities["Tenant B"]
    tenant_a_document = next(doc_id for identity, doc_id in ready_documents if identity == tenant_a)
    selected_status, selected_body = json_request(
        base_url,
        "POST",
        "/search",
        identity=tenant_a,
        payload={
            "query": "Who is the policy owner?",
            "document_ids": [tenant_a_document],
        },
    )
    assert selected_status == 200, f"authorized selected scope failed: {selected_body}"
    assert_safe_search(selected_body, tenant_a)
    cross_status, _ = json_request(
        base_url,
        "POST",
        "/search",
        identity=tenant_b,
        payload={
            "query": "Who is the policy owner?",
            "document_ids": [tenant_a_document],
        },
    )
    assert cross_status in {403, 404}

    reprocess_identity, reprocess_id = ready_documents[0]
    first_status, first = json_request(
        base_url,
        "POST",
        f"/documents/{reprocess_id}/reprocess",
        identity=reprocess_identity,
        headers={"idempotency-key": "enterprise-reprocess-v1"},
    )
    second_status, second = json_request(
        base_url,
        "POST",
        f"/documents/{reprocess_id}/reprocess",
        identity=reprocess_identity,
        headers={"idempotency-key": "enterprise-reprocess-v1"},
    )
    assert first_status == second_status == 202 and second["idempotent"] is True

    ingestion_ms = [duration for _, duration, _, _ in ingestion]
    search_ms = [probe.latency_ms for probe in search_probes]
    qualities = Counter(
        (item.get("result_json") or {}).get("extraction_quality", "unreported")
        for _, _, item, _ in ingestion
    )
    failure_categories = Counter(
        item.get("error_category") or "unknown"
        for status, _, item, _ in ingestion
        if status != "completed"
    )
    failed_document_ids = sorted(
        synthetic_id for status, _, _, synthetic_id in ingestion if status != "completed"
    )
    return {
        "schema_version": "enterprise-runtime-result-v1",
        "corpus_documents": len(records),
        "upload": {
            "accepted": sum(probe.ok for probe in uploads),
            "failed": sum(not probe.ok for probe in uploads),
            "average_ms": round(statistics.fmean(probe.latency_ms for probe in uploads), 2),
        },
        "ingestion": {
            "completed": sum(status == "completed" for status, _, _, _ in ingestion),
            "failed": sum(status == "failed" for status, _, _, _ in ingestion),
            "timeout": sum(status == "timeout" for status, _, _, _ in ingestion),
            "average_ms": round(statistics.fmean(ingestion_ms), 2),
            "p50_ms": percentile(ingestion_ms, 50),
            "p95_ms": percentile(ingestion_ms, 95),
            "quality": dict(qualities),
            "failure_taxonomy": dict(failure_categories),
            "failed_document_ids": failed_document_ids,
        },
        "search": {
            "cases": len(search_probes),
            "passed": sum(probe.ok for probe in search_probes),
            "states": dict(search_states),
            "average_ms": round(statistics.fmean(search_ms), 2),
            "p50_ms": percentile(search_ms, 50),
            "p95_ms": percentile(search_ms, 95),
            "p99_ms": percentile(search_ms, 99),
        },
        "isolation": {
            "authorized_selected_document_status": selected_status,
            "cross_tenant_selected_document_status": cross_status,
            "exposures": 0,
        },
        "reprocess": {
            "first_status": first_status,
            "idempotent_retry": second["idempotent"],
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000/api/v1")
    parser.add_argument("--upload-workers", type=int, default=4)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = run(args.base_url, max(1, min(args.upload_workers, 8)))
    rendered = json.dumps(result, indent=2, sort_keys=True)
    if args.output:
        args.output.write_text(rendered + "\n")
    print(rendered)


if __name__ == "__main__":
    main()
