from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class JobMessage:
    job_id: UUID
    task_type: str
    workspace_id: UUID
