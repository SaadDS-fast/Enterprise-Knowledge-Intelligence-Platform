from dataclasses import dataclass
from datetime import UTC, datetime


@dataclass(frozen=True, slots=True)
class WorkerHealth:
    status: str
    checked_at: datetime


def worker_health() -> WorkerHealth:
    return WorkerHealth(status="ok", checked_at=datetime.now(UTC))
