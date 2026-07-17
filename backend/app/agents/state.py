from dataclasses import dataclass, field

from app.models.domain import RetrievedEvidence


@dataclass(slots=True)
class AgentState:
    question: str
    plan: list[str] = field(default_factory=list)
    evidence: list[RetrievedEvidence] = field(default_factory=list)
    draft: str = ""
    safe: bool = True
    errors: list[str] = field(default_factory=list)
