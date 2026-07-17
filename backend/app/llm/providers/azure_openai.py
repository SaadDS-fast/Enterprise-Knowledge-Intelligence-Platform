import httpx

from app.core.config import settings
from app.llm.base import GenerationRequest, GenerationResult, LLMProvider
from app.llm.prompts.answer import build_answer_prompt


class AzureOpenAIProvider(LLMProvider):
    async def generate(self, request: GenerationRequest) -> GenerationResult:
        endpoint = (
            settings.azure_openai_endpoint.rstrip("/") if settings.azure_openai_endpoint else ""
        )
        url = (
            f"{endpoint}/openai/deployments/{settings.azure_openai_deployment}"
            "/chat/completions?api-version=2024-10-21"
        )
        key = (
            settings.azure_openai_api_key.get_secret_value()
            if settings.azure_openai_api_key
            else ""
        )
        async with httpx.AsyncClient(timeout=settings.llm_request_timeout_seconds) as client:
            response = await client.post(
                url,
                headers={"api-key": key},
                json={
                    "messages": [
                        {
                            "role": "user",
                            "content": build_answer_prompt(
                                request.question, [e.content for e in request.evidence]
                            ),
                        }
                    ],
                    "max_tokens": settings.llm_max_output_tokens,
                },
            )
            response.raise_for_status()
            payload = response.json()
        return GenerationResult(
            payload["choices"][0]["message"]["content"].strip(),
            "azure-openai",
            settings.azure_openai_deployment or "",
        )
