from __future__ import annotations

from uuid import UUID

from app.agents.budgets import AgentBudget
from app.agents.enums import AgentErrorCode
from app.agents.errors import AgentPolicyError
from app.agents.schemas import AgentPlan
from app.agents.tool_registry import ToolRegistry

FORBIDDEN_ARGUMENT_KEYS = {"shell", "command", "sql", "url", "urls", "endpoint"}


def validate_plan(
    plan: AgentPlan,
    *,
    registry: ToolRegistry,
    budget: AgentBudget,
    workspace_id: UUID,
) -> None:
    budget.ensure_steps(len(plan.steps))
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
            raise AgentPolicyError(
                AgentErrorCode.INVALID_PLAN,
                f"Network tool is not allowed in this phase: {step.tool}",
            )


def safe_operational_summary(value: str, *, max_length: int = 500) -> str:
    clean = " ".join(value.split())
    return clean[:max_length]
