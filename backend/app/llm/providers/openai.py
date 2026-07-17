import httpx

from app.core.config import settings
from app.llm.base import GenerationRequest, GenerationResult, LLMProvider
from app.llm.prompts.answer import SYSTEM_PROMPT, build_answer_prompt


class OpenAIProvider(LLMProvider):
    async def generate(self, request: GenerationRequest) -> GenerationResult:
        key = settings.openai_api_key.get_secret_value() if settings.openai_api_key else ""
        async with httpx.AsyncClient(timeout=settings.llm_request_timeout_seconds) as client:
            response = await client.post(
                "https://api.openai.com/v1/responses",
                headers={"Authorization": f"Bearer {key}"},
                json={
                    "model": settings.openai_model,
                    "instructions": SYSTEM_PROMPT,
                    "input": build_answer_prompt(
                        request.question, [e.content for e in request.evidence]
                    ),
                    "max_output_tokens": settings.llm_max_output_tokens,
                },
            )
            response.raise_for_status()
            payload = response.json()
        text = payload.get("output_text") or ""
        return GenerationResult(text.strip(), "openai", settings.openai_model)
