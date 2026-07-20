from __future__ import annotations

import os
import time

from celery import signals
from prometheus_client import start_http_server

from app.observability.metrics import (
    WORKER_ACTIVE_TASKS,
    WORKER_QUEUE_DELAY,
    WORKER_TASK_DURATION,
    WORKER_TASKS_COMPLETED,
    WORKER_TASKS_FAILED,
    WORKER_TASKS_RECEIVED,
    WORKER_TASKS_RETRIED,
)

_starts: dict[str, float] = {}
_server_started = False


def _role() -> str:
    return os.getenv("WORKER_ROLE", "worker")


@signals.worker_ready.connect
def start_worker_metrics_server(**_: object) -> None:
    global _server_started
    port = os.getenv("WORKER_METRICS_PORT")
    if not port or _server_started:
        return
    start_http_server(int(port))
    _server_started = True


@signals.task_prerun.connect
def record_task_start(task_id: str | None = None, task: object | None = None, **_: object) -> None:
    if not task_id:
        return
    now = time.time()
    _starts[task_id] = now
    role = _role()
    WORKER_TASKS_RECEIVED.labels(role).inc()
    WORKER_ACTIVE_TASKS.labels(role).inc()
    request = getattr(task, "request", None)
    headers = getattr(request, "headers", None) or {}
    published_at = headers.get("published_at")
    if isinstance(published_at, (int, float)):
        WORKER_QUEUE_DELAY.labels(role).observe(max(0.0, now - float(published_at)))


@signals.task_postrun.connect
def record_task_finish(
    task_id: str | None = None,
    state: str | None = None,
    **_: object,
) -> None:
    if not task_id:
        return
    role = _role()
    started = _starts.pop(task_id, None)
    if started is not None:
        WORKER_TASK_DURATION.labels(role).observe(max(0.0, time.time() - started))
    WORKER_ACTIVE_TASKS.labels(role).dec()
    if state == "SUCCESS":
        WORKER_TASKS_COMPLETED.labels(role).inc()
    elif state == "FAILURE":
        WORKER_TASKS_FAILED.labels(role).inc()


@signals.task_retry.connect
def record_task_retry(**_: object) -> None:
    WORKER_TASKS_RETRIED.labels(_role()).inc()
