from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.agents.enums import AgentIntent, AgentRunStatus, AgentStateName
from app.models.schemas import EvidenceItem


class AgentQueryRequest(BaseModel):
    query: str = Field(min_length=2, max_length=4000)
    top_k: int | None = Field(default=None, ge=1, le=50)
    document_ids: list[UUID] | None = None
    allow_external_sources: bool = False


class ExternalSource(BaseModel):
    source_id: str = Field(min_length=1, max_length=160)
    provider: str = Field(min_length=1, max_length=80)
    title: str = Field(min_length=1, max_length=500)
    canonical_url: str = Field(min_length=1, max_length=2000)
    excerpt: str = Field(default="", max_length=2000)
    source_type: str = Field(default="web", max_length=80)
    retrieval_timestamp: datetime
    trust_category: str = Field(default="untrusted_external", max_length=80)
    rank: int = Field(ge=1, le=100)
    publication_date: str | None = Field(default=None, max_length=80)
    authors: list[str] = Field(default_factory=list, max_length=20)


class PlannerStep(BaseModel):
    tool: str = Field(min_length=1, max_length=80)
    purpose: str = Field(min_length=3, max_length=200)
    required: bool = True
    arguments: dict[str, Any] = Field(default_factory=dict)

    @field_validator("arguments")
    @classmethod
    def reject_dangerous_arguments(cls, value: dict[str, Any]) -> dict[str, Any]:
        forbidden = {"shell", "command", "sql", "url", "urls", "endpoint"}
        if forbidden.intersection(value):
            raise ValueError("Planner step contains a forbidden argument")
        return value


class AgentPlan(BaseModel):
    intent: AgentIntent
    steps: list[PlannerStep] = Field(min_length=1)

    def safe_summary(self) -> str:
        return "; ".join(step.purpose for step in self.steps)


class AgentToolResult(BaseModel):
    tool: str = Field(default="unknown", min_length=1, max_length=80)
    status: str = Field(default="success", max_length=40)
    summary: str = Field(max_length=500)
    evidence: list[EvidenceItem] = Field(default_factory=list)
    external_sources: list[ExternalSource] = Field(default_factory=list)
    answer: str | None = Field(default=None, max_length=8000)
    sufficient_evidence: bool | None = None
    query: str | None = Field(default=None, max_length=4000)
    citations: list[dict[str, Any]] = Field(default_factory=list)
    abstained: bool = False
    unified_evidence: list[dict[str, Any]] = Field(default_factory=list)
    claims: list[dict[str, Any]] = Field(default_factory=list)
    conflicts: list[dict[str, Any]] = Field(default_factory=list)
    unsupported_claims_removed: list[str] = Field(default_factory=list)
    outcome: str | None = Field(default=None, max_length=80)
    confidence_category: str | None = Field(default=None, max_length=40)
    metadata: dict[str, Any] = Field(default_factory=dict)


class AgentStepRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    run_id: UUID
    step_number: int
    state: str
    summary: str
    status: str
    error_code: str | None
    duration_ms: int | None
    created_at: datetime
    updated_at: datetime


class AgentToolCallRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    run_id: UUID
    step_id: UUID | None
    tool_name: str
    status: str
    summary: str | None
    error_code: str | None
    duration_ms: int | None
    created_at: datetime
    updated_at: datetime


class AgentRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workspace_id: UUID
    user_id: UUID
    request_id: str | None
    status: AgentRunStatus
    current_state: AgentStateName
    input_query: str
    safe_plan_summary: str | None
    result_json: dict[str, Any]
    error_code: str | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime
    steps: list[AgentStepRead] = Field(default_factory=list)
    tool_calls: list[AgentToolCallRead] = Field(default_factory=list)


class AgentQueryResponse(BaseModel):
    run_id: UUID
    status: AgentRunStatus
    current_state: AgentStateName
    answer: str | None = None
    abstained: bool = False
    citations: list[dict[str, Any]] = Field(default_factory=list)
    evidence: list[EvidenceItem] = Field(default_factory=list)
    internal_evidence: list[EvidenceItem] = Field(default_factory=list)
    external_evidence: list[ExternalSource] = Field(default_factory=list)
    external_sources_used: bool = False
    providers_used: list[str] = Field(default_factory=list)
    external_access_allowed: bool = False
    external_access_performed: bool = False
    tools_used: list[str] = Field(default_factory=list)
    safe_step_summaries: list[str] = Field(default_factory=list)
    safe_plan_summary: str | None = None
    total_duration_ms: int | None = None
    fallback_used: bool = False
    request_id: str | None = None
    retrieval_diagnosis: dict[str, Any] = Field(default_factory=dict)
    outcome: str = "INSUFFICIENT_EVIDENCE"
    claims: list[dict[str, Any]] = Field(default_factory=list)
    conflicts: list[dict[str, Any]] = Field(default_factory=list)
    unsupported_claims_removed: list[str] = Field(default_factory=list)
    confidence_category: str = "none"
    unified_evidence: list[dict[str, Any]] = Field(default_factory=list)
    evidence_ranking: dict[str, Any] = Field(default_factory=dict)
    evidence_deduplication: list[dict[str, Any]] = Field(default_factory=list)
    context_budget: dict[str, Any] = Field(default_factory=dict)


class AgentFeatureDisabledResponse(BaseModel):
    enabled: bool = False
    message: str = "Agentic RAG is disabled. Set AGENTIC_RAG_ENABLED=true to enable it."
    code: str = "AGENT_FEATURE_DISABLED"
