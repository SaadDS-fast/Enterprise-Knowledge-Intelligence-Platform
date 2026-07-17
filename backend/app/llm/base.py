from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.models.domain import RetrievedEvidence


@dataclass(frozen=True, slots=True)
class GenerationRequest:
    question: str
    evidence: list[RetrievedEvidence]
    system_prompt: str = ""


@dataclass(frozen=True, slots=True)
class GenerationResult:
    text: str
    provider: str
    model: str


class LLMProvider(ABC):
    @abstractmethod
    async def generate(self, request: GenerationRequest) -> GenerationResult: ...
