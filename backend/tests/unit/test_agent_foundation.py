import asyncio
import time
from uuid import uuid4

import pytest
from pydantic import BaseModel

from app.agents.budgets import AgentBudget
from app.agents.enums import AgentErrorCode, AgentIntent, AgentStateName
from app.agents.errors import AgentBudgetError, AgentPolicyError
from app.agents.executor import ToolExecutor
from app.agents.planner import DeterministicPlanner
from app.agents.policies import validate_plan
from app.agents.schemas import AgentPlan, AgentToolResult, PlannerStep
from app.agents.state import AgentRuntimeState, can_transition
from app.agents.tool_registry import ToolDefinition, ToolRegistry, build_default_registry


def test_valid_state_transitions() -> None:
    state = AgentRuntimeState(query="What is Project Atlas?", workspace_id=uuid4(), user_id=uuid4())
    state.transition(AgentStateName.AUTHORIZE)
    state.transition(AgentStateName.CLASSIFY_INTENT)
    assert state.current_state is AgentStateName.CLASSIFY_INTENT
    assert can_transition(AgentStateName.SAFETY_REVIEW, AgentStateName.COMPLETE)


def test_invalid_state_transition_is_rejected() -> None:
    state = AgentRuntimeState(query="What is Project Atlas?", workspace_id=uuid4(), user_id=uuid4())
    with pytest.raises(ValueError, match="Invalid agent transition"):
        state.transition(AgentStateName.COMPLETE)


@pytest.mark.asyncio
async def test_deterministic_plan_generation() -> None:
    plan = await DeterministicPlanner().create_plan("Who owns Project Atlas?")
    assert plan.intent is AgentIntent.DOCUMENT_QUESTION
    assert [step.tool for step in plan.steps] == ["internal_search", "evidence_verifier"]
    assert (
        plan.safe_summary() == "Internal document search selected; Evidence verification selected"
    )


def test_unknown_tool_rejection() -> None:
    plan = AgentPlan(
        intent=AgentIntent.DOCUMENT_QUESTION,
        steps=[PlannerStep(tool="direct_sql", purpose="Try direct SQL", required=True)],
    )
    with pytest.raises(AgentPolicyError) as exc:
        validate_plan(
            plan,
            registry=build_default_registry(),
            budget=AgentBudget(6, 8, 2, 90, 1.0),
            workspace_id=uuid4(),
        )
    assert exc.value.code is AgentErrorCode.UNKNOWN_TOOL


def test_budget_enforcement_rejects_too_many_steps() -> None:
    plan = AgentPlan(
        intent=AgentIntent.DOCUMENT_QUESTION,
        steps=[
            PlannerStep(tool="internal_search", purpose=f"Search pass {idx}", required=True)
            for idx in range(3)
        ],
    )
    with pytest.raises(AgentBudgetError):
        validate_plan(
            plan,
            registry=build_default_registry(),
            budget=AgentBudget(2, 8, 2, 90, 1.0),
            workspace_id=uuid4(),
        )


def test_workspace_scope_change_is_rejected() -> None:
    workspace_id = uuid4()
    plan = AgentPlan(
        intent=AgentIntent.DOCUMENT_QUESTION,
        steps=[
            PlannerStep(
                tool="internal_search",
                purpose="Find authorized evidence",
                required=True,
                arguments={"workspace_id": str(uuid4())},
            )
        ],
    )
    with pytest.raises(AgentPolicyError, match="workspace scope"):
        validate_plan(
            plan,
            registry=build_default_registry(),
            budget=AgentBudget(6, 8, 2, 90, 1.0),
            workspace_id=workspace_id,
        )


class SlowInput(BaseModel):
    value: str = "slow"


async def slow_handler(payload: BaseModel, context: dict) -> AgentToolResult:
    await asyncio.sleep(0.05)
    return AgentToolResult(summary="Slow completed")


@pytest.mark.asyncio
async def test_tool_timeout_handling() -> None:
    registry = ToolRegistry()
    registry.register(
        ToolDefinition(
            name="slow_tool",
            description="Slow test tool",
            input_schema=SlowInput,
            output_schema=AgentToolResult,
            required_permission="workspace:read",
            timeout_seconds=0.001,
            max_result_size=100,
            network_required=False,
            enabled=True,
            handler=slow_handler,
        )
    )
    executor = ToolExecutor(registry, AgentBudget(6, 8, 2, 90, time.monotonic()))
    with pytest.raises(TimeoutError):
        await executor.execute(
            PlannerStep(tool="slow_tool", purpose="Timeout", required=True),
            {},
            {},
        )
