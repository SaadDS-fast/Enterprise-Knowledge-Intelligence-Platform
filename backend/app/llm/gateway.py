from functools import lru_cache

from app.llm.base import GenerationRequest, GenerationResult, LLMProvider
from app.llm.routing import build_provider


class LLMGateway:
    def __init__(self, provider: LLMProvider | None = None) -> None:
        self.provider = provider or build_provider()

    async def answer(self, request: GenerationRequest) -> GenerationResult:
        return await self.provider.generate(request)


@lru_cache(maxsize=1)
def get_llm_gateway() -> LLMGateway:
    return LLMGateway()
