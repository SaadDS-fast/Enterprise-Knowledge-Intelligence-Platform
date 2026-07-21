from __future__ import annotations

import time
from dataclasses import dataclass

from app.agents.enums import AgentErrorCode
from app.agents.errors import AgentBudgetError


@dataclass(frozen=True, slots=True)
class AgentBudget:
    max_steps: int
    max_tool_calls: int
    max_retrieval_retries: int
    timeout_seconds: float
    started_at: float = 0.0

    @classmethod
    def from_settings(cls) -> AgentBudget:
        from app.core.config import settings

        return cls(
            max_steps=settings.agent_max_steps,
            max_tool_calls=settings.agent_max_tool_calls,
            max_retrieval_retries=settings.agent_max_retrieval_retries,
            timeout_seconds=settings.agent_timeout_seconds,
            started_at=time.monotonic(),
        )

    def ensure_steps(self, count: int) -> None:
        if count > self.max_steps:
            raise AgentBudgetError(
                AgentErrorCode.BUDGET_EXCEEDED,
                f"Agent plan exceeds maximum step budget of {self.max_steps}",
            )

    def ensure_tool_call(self, count: int) -> None:
        if count > self.max_tool_calls:
            raise AgentBudgetError(
                AgentErrorCode.BUDGET_EXCEEDED,
                f"Agent run exceeds maximum tool-call budget of {self.max_tool_calls}",
            )

    def ensure_retrieval_retry(self, count: int) -> None:
        if count > self.max_retrieval_retries:
            raise AgentBudgetError(
                AgentErrorCode.BUDGET_EXCEEDED,
                "Agent run exceeds maximum retrieval retry budget",
            )

    def ensure_time(self) -> None:
        if self.started_at and time.monotonic() - self.started_at > self.timeout_seconds:
            raise AgentBudgetError(AgentErrorCode.TIMEOUT, "Agent run exceeded total timeout")
