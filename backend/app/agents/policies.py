from __future__ import annotations

from uuid import UUID

from app.agents.budgets import AgentBudget
from app.agents.enums import AgentErrorCode
from app.agents.errors import AgentPolicyError
from app.agents.schemas import AgentPlan
from app.agents.tool_registry import ToolRegistry
from app.core.config import settings

FORBIDDEN_ARGUMENT_KEYS = {"shell", "command", "sql", "url", "urls", "endpoint"}


def validate_plan(
    plan: AgentPlan,
    *,
    registry: ToolRegistry,
    budget: AgentBudget,
    workspace_id: UUID,
    allow_external_sources: bool = False,
) -> None:
    budget.ensure_tool_call(len(plan.steps))
    for step in plan.steps:
        if FORBIDDEN_ARGUMENT_KEYS.intersection(step.arguments):
            raise AgentPolicyError(
                AgentErrorCode.INVALID_PLAN, "Planner output contains forbidden arguments"
            )
        if "workspace_id" in step.arguments and str(step.arguments["workspace_id"]) != str(
            workspace_id
        ):
            raise AgentPolicyError(
                AgentErrorCode.INVALID_PLAN, "Planner output attempted to change workspace scope"
            )
        tool = registry.get(step.tool)
        if not tool.enabled:
            raise AgentPolicyError(AgentErrorCode.TOOL_DISABLED, f"Tool is disabled: {step.tool}")
        if tool.network_required:
            flag_enabled = (
                bool(getattr(settings, tool.feature_flag))
                if tool.feature_flag is not None
                else False
            )
            if allow_external_sources and flag_enabled:
                continue
            raise AgentPolicyError(
                AgentErrorCode.INVALID_PLAN,
                f"Network tool is not allowed for this request: {step.tool}",
            )


def safe_operational_summary(value: str, *, max_length: int = 500) -> str:
    clean = " ".join(value.split())
    return clean[:max_length]
