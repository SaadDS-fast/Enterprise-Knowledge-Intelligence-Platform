from __future__ import annotations

import asyncio
import time
from typing import Any

from app.agents.budgets import AgentBudget
from app.agents.schemas import AgentToolResult, PlannerStep
from app.agents.tool_registry import ToolRegistry


class ToolExecutor:
    def __init__(self, registry: ToolRegistry, budget: AgentBudget) -> None:
        self.registry = registry
        self.budget = budget

    async def execute(
        self, step: PlannerStep, payload: dict[str, Any], context: dict[str, Any]
    ) -> tuple[AgentToolResult, int]:
        started = time.perf_counter()
        self.budget.ensure_time()
        tool = self.registry.get(step.tool)
        result = await asyncio.wait_for(
            self.registry.execute(step.tool, payload, context),
            timeout=tool.timeout_seconds,
        )
        self.budget.ensure_time()
        return result, int((time.perf_counter() - started) * 1000)
