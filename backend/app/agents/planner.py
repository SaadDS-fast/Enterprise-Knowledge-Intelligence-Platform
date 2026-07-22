from __future__ import annotations

from abc import ABC, abstractmethod

from app.agents.enums import AgentIntent
from app.agents.schemas import AgentPlan, PlannerStep


class PlannerProvider(ABC):
    @abstractmethod
    async def create_plan(self, query: str) -> AgentPlan:
        raise NotImplementedError


class DeterministicPlanner(PlannerProvider):
    async def create_plan(self, query: str) -> AgentPlan:
        normalized = query.strip()
        intent = AgentIntent.DOCUMENT_QUESTION if normalized else AgentIntent.UNSUPPORTED
        return AgentPlan(
            intent=intent,
            steps=[
                PlannerStep(
                    tool="document_metadata",
                    purpose="Document metadata scoped to workspace selected",
                    required=True,
                    arguments={},
                ),
                PlannerStep(
                    tool="query_reformulation",
                    purpose="Query normalization selected",
                    required=True,
                    arguments={},
                ),
                PlannerStep(
                    tool="internal_search",
                    purpose="Internal document search selected",
                    required=True,
                    arguments={},
                ),
                PlannerStep(
                    tool="evidence_verifier",
                    purpose="Evidence verification selected",
                    required=True,
                    arguments={},
                ),
                PlannerStep(
                    tool="retrieval_diagnosis",
                    purpose="Retrieval diagnosis selected",
                    required=True,
                    arguments={},
                ),
                PlannerStep(
                    tool="answer_synthesizer",
                    purpose="Answer synthesis selected",
                    required=True,
                    arguments={},
                ),
                PlannerStep(
                    tool="safety_reviewer",
                    purpose="Safety review selected",
                    required=True,
                    arguments={},
                ),
            ],
        )


def get_planner() -> PlannerProvider:
    from app.core.config import AgentPlannerProvider, settings

    if settings.agent_planner_provider is AgentPlannerProvider.DETERMINISTIC:
        return DeterministicPlanner()
    return DeterministicPlanner()


def build_plan(question: str) -> list[str]:
    return [
        "Normalize the question",
        "Retrieve workspace evidence",
        "Verify evidence sufficiency",
        "Draft a cited answer",
        "Run safety review",
    ]
