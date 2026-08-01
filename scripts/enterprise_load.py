#!/usr/bin/env python3
"""Dependency-free bounded API/search load and soak probe for local release acceptance."""

from __future__ import annotations

import argparse
import json
import math
import statistics
import time
import urllib.error
import urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Any
from uuid import uuid4


@dataclass(frozen=True)
class Result:
    operation: str
    status: int
    latency_ms: float


def request(
    base_url: str,
    path: str,
    *,
    token: str | None = None,
    workspace_id: str | None = None,
    payload: dict[str, Any] | None = None,
) -> tuple[int, dict[str, Any]]:
    assert base_url.startswith(("http://127.0.0.1:", "http://localhost:"))
    headers = {"content-type": "application/json"}
    if token:
        headers["authorization"] = f"Bearer {token}"
    if workspace_id:
        headers["x-workspace-id"] = workspace_id
    call = urllib.request.Request(  # noqa: S310 -- local base URL asserted above
        f"{base_url}{path}",
        method="POST" if payload is not None else "GET",
        headers=headers,
        data=None if payload is None else json.dumps(payload).encode(),
    )
    try:
        with urllib.request.urlopen(call, timeout=30) as response:  # noqa: S310
            return response.status, json.loads(response.read() or b"{}")
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read() or b"{}")


def register(base_url: str) -> tuple[str, str]:
    suffix = uuid4().hex
    status, body = request(
        base_url,
        "/auth/register",
        payload={
            "email": f"enterprise-load-{suffix}@validation.localhost.com",
            "full_name": "Synthetic Load User",
            "password": "EnterpriseLoadPass123!",
            "organization_name": f"Aurora Load {suffix[:8]}",
            "workspace_name": "Load Validation",
        },
    )
    assert status in {200, 201}
    return body["access_token"], body["workspace_id"]


def timed(operation: str, function: Any) -> Result:
    started = time.perf_counter()
    try:
        status, _ = function()
    except Exception:
        status = 0
    return Result(operation, status, (time.perf_counter() - started) * 1000)


def percentile(values: list[float], value: int) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    return round(ordered[min(len(ordered) - 1, math.ceil(value / 100 * len(ordered)) - 1)], 2)


def summarize(results: list[Result], elapsed: float) -> dict[str, Any]:
    latencies = [result.latency_ms for result in results]
    successes = sum(200 <= result.status < 300 for result in results)
    rate_limited = sum(result.status == 429 for result in results)
    unexpected_errors = sum(
        not (200 <= result.status < 300 or result.status == 429) for result in results
    )
    return {
        "requests": len(results),
        "successes": successes,
        "success_rate": round(successes / max(1, len(results)), 6),
        "rate_limited": rate_limited,
        "unexpected_error_rate": round(unexpected_errors / max(1, len(results)), 6),
        "throughput_rps": round(len(results) / max(0.001, elapsed), 2),
        "average_ms": round(statistics.fmean(latencies), 2),
        "p50_ms": percentile(latencies, 50),
        "p90_ms": percentile(latencies, 90),
        "p95_ms": percentile(latencies, 95),
        "p99_ms": percentile(latencies, 99),
        "statuses": dict(Counter(str(result.status) for result in results)),
    }


def bounded_load(base_url: str, duration: int, health_clients: int, search_clients: int):
    token, workspace_id = register(base_url)
    deadline = time.monotonic() + duration
    results: list[Result] = []
    started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=health_clients + search_clients) as pool:
        while time.monotonic() < deadline:
            futures = []
            for _ in range(health_clients):
                futures.append(
                    pool.submit(timed, "health", lambda: request(base_url, "/health/ready"))
                )
            for index in range(search_clients):
                query = "What information is absent?" if index % 2 else "What policy is current?"
                futures.append(
                    pool.submit(
                        timed,
                        "search",
                        lambda query=query: request(
                            base_url,
                            "/search",
                            token=token,
                            workspace_id=workspace_id,
                            payload={"query": query},
                        ),
                    )
                )
            results.extend(future.result() for future in as_completed(futures))
            time.sleep(0.1)
    elapsed = time.perf_counter() - started
    by_operation = {
        operation: summarize([item for item in results if item.operation == operation], elapsed)
        for operation in {item.operation for item in results}
    }
    return {
        "duration_seconds": round(elapsed, 2),
        "overall": summarize(results, elapsed),
        **by_operation,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000/api/v1")
    parser.add_argument("--duration-seconds", type=int, default=120)
    parser.add_argument("--health-clients", type=int, default=20)
    parser.add_argument("--search-clients", type=int, default=10)
    args = parser.parse_args()
    print(
        json.dumps(
            bounded_load(
                args.base_url,
                max(1, args.duration_seconds),
                max(1, args.health_clients),
                max(1, args.search_clients),
            ),
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
