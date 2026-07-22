from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from app.agents.schemas import ExternalSource


class ExternalProviderError(RuntimeError):
    def __init__(self, provider: str, reason: str) -> None:
        self.provider = provider
        self.reason = reason
        super().__init__(f"{provider}: {reason}")


@dataclass(frozen=True, slots=True)
class ProviderResponse:
    provider: str
    status: str
    results: list[ExternalSource] = field(default_factory=list)
    disabled: bool = False
    error: str | None = None


class ExternalProvider(ABC):
    name: str

    @abstractmethod
    async def search(self, query: str, *, max_results: int) -> ProviderResponse:
        raise NotImplementedError
