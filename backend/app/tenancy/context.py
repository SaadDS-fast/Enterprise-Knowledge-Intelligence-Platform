from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class TenantContext:
    user_id: UUID
    workspace_id: UUID
    organization_id: UUID
    role: str
