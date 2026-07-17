from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AgentBudget:
    max_steps: int = 5
    max_retrieval_calls: int = 2
    max_output_tokens: int = 1500
