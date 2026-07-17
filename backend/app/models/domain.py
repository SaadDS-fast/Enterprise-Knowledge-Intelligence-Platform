from dataclasses import dataclass, field
from uuid import UUID


@dataclass(slots=True)
class RetrievedEvidence:
    chunk_id: UUID
    document_id: UUID
    document_title: str
    content: str
    score: float
    metadata: dict = field(default_factory=dict)
