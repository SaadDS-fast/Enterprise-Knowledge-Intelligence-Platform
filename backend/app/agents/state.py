from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

from app.agents.enums import AgentRunStatus, AgentStateName
from app.agents.schemas import ExternalSource
from app.models.schemas import EvidenceItem

ALLOWED_TRANSITIONS: dict[AgentStateName, frozenset[AgentStateName]] = {
    AgentStateName.RECEIVE_REQUEST: frozenset({AgentStateName.AUTHORIZE}),
    AgentStateName.AUTHORIZE: frozenset(
        {AgentStateName.CLASSIFY_INTENT, AgentStateName.FAILED, AgentStateName.CANCELLED}
    ),
    AgentStateName.CLASSIFY_INTENT: frozenset({AgentStateName.CREATE_PLAN, AgentStateName.FAILED}),
    AgentStateName.CREATE_PLAN: frozenset({AgentStateName.SELECT_TOOL, AgentStateName.FAILED}),
    AgentStateName.SELECT_TOOL: frozenset(
        {AgentStateName.EXECUTE_TOOL, AgentStateName.ASSEMBLE_EVIDENCE}
    ),
    AgentStateName.EXECUTE_TOOL: frozenset(
        {
            AgentStateName.SELECT_TOOL,
            AgentStateName.ASSEMBLE_EVIDENCE,
            AgentStateName.VERIFY_EVIDENCE,
            AgentStateName.REPLAN,
            AgentStateName.SYNTHESIZE,
            AgentStateName.SAFETY_REVIEW,
            AgentStateName.FAILED,
            AgentStateName.CANCELLED,
        }
    ),
    AgentStateName.ASSEMBLE_EVIDENCE: frozenset({AgentStateName.VERIFY_EVIDENCE}),
    AgentStateName.VERIFY_EVIDENCE: frozenset(
        {
            AgentStateName.SELECT_TOOL,
            AgentStateName.SYNTHESIZE,
            AgentStateName.REPLAN,
            AgentStateName.FAILED,
        }
    ),
    AgentStateName.REPLAN: frozenset(
        {AgentStateName.SELECT_TOOL, AgentStateName.SYNTHESIZE, AgentStateName.FAILED}
    ),
    AgentStateName.SYNTHESIZE: frozenset(
        {AgentStateName.SELECT_TOOL, AgentStateName.SAFETY_REVIEW}
    ),
    AgentStateName.SAFETY_REVIEW: frozenset({AgentStateName.COMPLETE, AgentStateName.FAILED}),
    AgentStateName.COMPLETE: frozenset(),
    AgentStateName.FAILED: frozenset(),
    AgentStateName.CANCELLED: frozenset(),
}


def can_transition(current: AgentStateName, target: AgentStateName) -> bool:
    return target in ALLOWED_TRANSITIONS[current]


@dataclass(slots=True)
class AgentRuntimeState:
    query: str
    workspace_id: UUID
    user_id: UUID
    request_id: str | None = None
    status: AgentRunStatus = AgentRunStatus.PENDING
    current_state: AgentStateName = AgentStateName.RECEIVE_REQUEST
    plan_summary: str | None = None
    evidence: list[EvidenceItem] = field(default_factory=list)
    internal_evidence: list[EvidenceItem] = field(default_factory=list)
    external_evidence: list[ExternalSource] = field(default_factory=list)
    answer: str | None = None
    abstained: bool = False
    citations: list[dict] = field(default_factory=list)
    retrieval_diagnosis: dict = field(default_factory=dict)
    providers_used: list[str] = field(default_factory=list)
    external_sources_used: bool = False
    external_access_allowed: bool = False
    external_access_performed: bool = False
    tools_used: list[str] = field(default_factory=list)
    safe_step_summaries: list[str] = field(default_factory=list)
    fallback_used: bool = False
    total_duration_ms: int | None = None
    tool_calls: int = 0
    retrieval_retries: int = 0
    cancelled: bool = False
    errors: list[str] = field(default_factory=list)

    def transition(self, target: AgentStateName) -> None:
        if not can_transition(self.current_state, target):
            raise ValueError(f"Invalid agent transition: {self.current_state} -> {target}")
        self.current_state = target
