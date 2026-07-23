#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import statistics
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Any


@dataclass
class Result:
    name: str
    ok: bool
    status: int
    latency_ms: float


def request_json(
    base_url: str,
    path: str,
    *,
    token: str | None = None,
    workspace_id: str | None = None,
    payload: dict[str, Any] | None = None,
) -> tuple[int, dict[str, Any]]:
    data = json.dumps(payload).encode() if payload is not None else None
    request = urllib.request.Request(
        f"{base_url}{path}",
        data=data,
        method="POST" if payload is not None else "GET",
        headers={"content-type": "application/json"},
    )
    if token:
        request.add_header("authorization", f"Bearer {token}")
    if workspace_id:
        request.add_header("x-workspace-id", workspace_id)
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return response.status, json.loads(response.read() or b"{}")
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read() or b"{}")


def register(base_url: str, index: int) -> tuple[str, str]:
    suffix = f"{int(time.time())}-{index}"
    status, body = request_json(
        base_url,
        "/auth/register",
        payload={
            "email": f"load-{suffix}@validation.localhost.com",
            "full_name": "Load Validation User",
            "password": "LoadValidationPass123!",
            "organization_name": f"Load Org {suffix}",
            "workspace_name": "General",
        },
    )
    if status not in {200, 201}:
        raise RuntimeError(f"registration failed: {status}")
    return body["access_token"], body["workspace_id"]


def timed(name: str, fn) -> Result:
    started = time.perf_counter()
    status = 0
    ok = False
    try:
        status, _ = fn()
        ok = 200 <= status < 300 or status in {403, 404, 409, 429, 503}
    except Exception:
        ok = False
    return Result(name, ok, status, (time.perf_counter() - started) * 1000)


def percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, round((pct / 100) * (len(ordered) - 1)))
    return ordered[index]


def main() -> None:
    parser = argparse.ArgumentParser(description="Small local EKIP agentic load probe")
    parser.add_argument("--base-url", default="http://localhost:8000/api/v1")
    parser.add_argument("--users", type=int, default=5)
    parser.add_argument("--requests-per-user", type=int, default=2)
    args = parser.parse_args()

    identities = [register(args.base_url, index) for index in range(args.users)]
    work: list[tuple[str, Any]] = []
    for token, workspace_id in identities:
        for _ in range(args.requests_per_user):
            work.extend(
                [
                    (
                        "search",
                        lambda token=token, workspace_id=workspace_id: request_json(
                            args.base_url,
                            "/search",
                            token=token,
                            workspace_id=workspace_id,
                            payload={"query": "What local evidence is available?"},
                        ),
                    ),
                    (
                        "agent_query",
                        lambda token=token, workspace_id=workspace_id: request_json(
                            args.base_url,
                            "/agent/query",
                            token=token,
                            workspace_id=workspace_id,
                            payload={
                                "query": "What local evidence is available?",
                                "allow_external_sources": False,
                            },
                        ),
                    ),
                    (
                        "research_list",
                        lambda token=token, workspace_id=workspace_id: request_json(
                            args.base_url,
                            "/agent/research",
                            token=token,
                            workspace_id=workspace_id,
                        ),
                    ),
                ]
            )

    results: list[Result] = []
    with ThreadPoolExecutor(max_workers=args.users) as pool:
        futures = [pool.submit(timed, name, fn) for name, fn in work]
        for future in as_completed(futures):
            results.append(future.result())

    latencies = [item.latency_ms for item in results]
    ok = sum(item.ok for item in results)
    summary = {
        "users": args.users,
        "requests": len(results),
        "success_rate": ok / max(1, len(results)),
        "error_rate": 1 - (ok / max(1, len(results))),
        "p50_ms": statistics.median(latencies) if latencies else 0.0,
        "p95_ms": percentile(latencies, 95),
        "p99_ms": percentile(latencies, 99),
        "throughput_rps": len(results) / max(0.001, sum(latencies) / 1000),
        "statuses": {
            str(status): sum(1 for item in results if item.status == status)
            for status in {item.status for item in results}
        },
    }
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
