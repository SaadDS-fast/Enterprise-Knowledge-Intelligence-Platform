from uuid import uuid4

from app.core.config import JobExecutionMode
from app.jobs import service


class DummyCeleryResult:
    id = "task-1"


class DummyCelery:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def send_task(self, *args, **kwargs) -> DummyCeleryResult:
        self.calls.append({"args": args, "kwargs": kwargs})
        return DummyCeleryResult()


class DummyBackgroundTasks:
    def __init__(self) -> None:
        self.calls: list[tuple] = []

    def add_task(self, *args, **kwargs) -> None:
        self.calls.append((args, kwargs))


def test_dispatch_ingestion_uses_deterministic_celery_task_id(monkeypatch):
    job_id = uuid4()
    celery = DummyCelery()
    monkeypatch.setattr(service.settings, "job_execution_mode", JobExecutionMode.CELERY)
    monkeypatch.setattr(service, "celery_app", celery)

    task_id = service.dispatch_ingestion(job_id, request_id="req-1")

    assert task_id == "task-1"
    assert celery.calls == [
        {
            "args": ("ekip.ingest",),
            "kwargs": {
                "args": [str(job_id)],
                "kwargs": {"request_id": "req-1"},
                "queue": "ingestion",
                "task_id": str(job_id),
                "headers": {"request_id": "req-1"},
            },
        }
    ]


def test_dispatch_ingestion_inline_adds_background_task(monkeypatch):
    job_id = uuid4()
    background_tasks = DummyBackgroundTasks()
    monkeypatch.setattr(service.settings, "job_execution_mode", JobExecutionMode.INLINE)

    task_id = service.dispatch_ingestion(job_id, background_tasks, request_id="req-2")

    assert task_id is None
    assert len(background_tasks.calls) == 1
    args, kwargs = background_tasks.calls[0]
    assert args[1] == job_id
    assert kwargs == {"request_id": "req-2"}
