from __future__ import annotations

import inspect
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel

from app.agents.enums import AgentErrorCode
from app.agents.errors import AgentPolicyError
from app.agents.schemas import AgentToolResult

ToolHandler = Callable[[BaseModel, dict[str, Any]], Awaitable[AgentToolResult] | AgentToolResult]


@dataclass(frozen=True, slots=True)
class ToolDefinition:
    name: str
    description: str
    input_schema: type[BaseModel]
    output_schema: type[BaseModel]
    required_permission: str
    timeout_seconds: float
    max_result_size: int
    network_required: bool
    enabled: bool
    handler: ToolHandler


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, ToolDefinition] = {}

    def register(self, tool: ToolDefinition) -> None:
        if tool.name in self._tools:
            raise ValueError(f"Tool already registered: {tool.name}")
        self._tools[tool.name] = tool

    def get(self, name: str) -> ToolDefinition:
        if name not in self._tools:
            raise AgentPolicyError(AgentErrorCode.UNKNOWN_TOOL, f"Unknown tool: {name}")
        return self._tools[name]

    @property
    def names(self) -> tuple[str, ...]:
        return tuple(sorted(self._tools))

    async def execute(
        self, name: str, payload: dict[str, Any], context: dict[str, Any]
    ) -> AgentToolResult:
        tool = self.get(name)
        if not tool.enabled:
            raise AgentPolicyError(AgentErrorCode.TOOL_DISABLED, f"Tool is disabled: {name}")
        parsed = tool.input_schema.model_validate(payload)
        result = tool.handler(parsed, context)
        if inspect.isawaitable(result):
            result = await result
        return tool.output_schema.model_validate(result)


class InternalSearchInput(BaseModel):
    query: str
    top_k: int | None = None


class EvidenceVerifierInput(BaseModel):
    sufficient_evidence: bool
    evidence_count: int


class PlaceholderInput(BaseModel):
    reason: str | None = None


async def _internal_search_handler(payload: BaseModel, context: dict[str, Any]) -> AgentToolResult:
    from app.services.search_service import search_and_answer

    data = InternalSearchInput.model_validate(payload)
    response = await search_and_answer(
        context["session"],
        workspace_id=context["workspace_id"],
        query=data.query,
        top_k=data.top_k,
        document_ids=context.get("document_ids"),
        request_id=context.get("request_id"),
    )
    return AgentToolResult(
        summary="Internal document search completed",
        evidence=response.evidence,
        answer=response.answer,
        sufficient_evidence=response.sufficient_evidence,
        metadata={
            "abstained": response.abstained,
            "retrieval_diagnosis": response.retrieval_diagnosis,
        },
    )


def _evidence_verifier_handler(payload: BaseModel, context: dict[str, Any]) -> AgentToolResult:
    data = EvidenceVerifierInput.model_validate(payload)
    summary = (
        "Final citations verified"
        if data.sufficient_evidence and data.evidence_count > 0
        else "Evidence insufficient; retrieval retry requested"
    )
    return AgentToolResult(
        summary=summary,
        sufficient_evidence=data.sufficient_evidence and data.evidence_count > 0,
    )


def _disabled_placeholder_handler(payload: BaseModel, context: dict[str, Any]) -> AgentToolResult:
    raise AgentPolicyError(
        AgentErrorCode.TOOL_DISABLED, "Placeholder tools are disabled in this phase"
    )


def build_default_registry() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(
        ToolDefinition(
            name="internal_search",
            description="Search authorized internal workspace documents.",
            input_schema=InternalSearchInput,
            output_schema=AgentToolResult,
            required_permission="workspace:read",
            timeout_seconds=20.0,
            max_result_size=50_000,
            network_required=False,
            enabled=True,
            handler=_internal_search_handler,
        )
    )
    registry.register(
        ToolDefinition(
            name="evidence_verifier",
            description="Check whether retrieved evidence can support an answer.",
            input_schema=EvidenceVerifierInput,
            output_schema=AgentToolResult,
            required_permission="workspace:read",
            timeout_seconds=5.0,
            max_result_size=10_000,
            network_required=False,
            enabled=True,
            handler=_evidence_verifier_handler,
        )
    )
    registry.register(
        ToolDefinition(
            name="external_web_search",
            description="Future external web search placeholder.",
            input_schema=PlaceholderInput,
            output_schema=AgentToolResult,
            required_permission="external:network",
            timeout_seconds=10.0,
            max_result_size=0,
            network_required=True,
            enabled=False,
            handler=_disabled_placeholder_handler,
        )
    )
    return registry
