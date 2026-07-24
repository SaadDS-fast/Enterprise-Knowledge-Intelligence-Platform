from __future__ import annotations

import logging
import re

import httpx

from app.core.config import LocalLLMBackend, settings
from app.llm.base import GenerationRequest, GenerationResult, LLMProvider
from app.llm.prompts.answer import build_answer_prompt
from app.rag.embeddings import tokenize
from app.rag.evidence import assess_evidence_support, synthesize_direct_answer

logger = logging.getLogger(__name__)


class LocalProvider(LLMProvider):
    async def generate(self, request: GenerationRequest) -> GenerationResult:
        if settings.local_llm_backend is LocalLLMBackend.OLLAMA:
            try:
                return await self._ollama(request)
            except (httpx.HTTPError, TimeoutError) as exc:
                logger.warning("Ollama unavailable; using extractive fallback: %s", exc)
        return self._extractive(request)

    async def _ollama(self, request: GenerationRequest) -> GenerationResult:
        prompt = build_answer_prompt(request.question, [item.content for item in request.evidence])
        async with httpx.AsyncClient(timeout=settings.llm_request_timeout_seconds) as client:
            response = await client.post(
                f"{settings.local_llm_base_url.rstrip('/')}/api/generate",
                json={
                    "model": settings.local_llm_model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"num_predict": settings.llm_max_output_tokens},
                },
            )
            response.raise_for_status()
            text = response.json().get("response", "").strip()
        if not text:
            raise ValueError("Local model returned an empty response")
        return GenerationResult(text, "local-ollama", settings.local_llm_model)

    def _extractive(self, request: GenerationRequest) -> GenerationResult:
        assessment = assess_evidence_support(
            [item.score for item in request.evidence],
            request.question,
            [item.content for item in request.evidence],
        )
        direct_answer = synthesize_direct_answer(request.question, assessment)
        if direct_answer:
            return GenerationResult(
                direct_answer, "local-extractive", "deterministic-extractive-v2"
            )
        query_tokens = set(tokenize(request.question))
        candidates: list[tuple[float, str, int]] = []
        for citation, item in enumerate(request.evidence, 1):
            for sentence in re.split(r"(?<=[.!?])\s+|\n+", item.content):
                sentence = sentence.strip()
                if len(sentence) < 20:
                    continue
                overlap = len(query_tokens & set(tokenize(sentence))) / max(1, len(query_tokens))
                candidates.append((0.65 * item.score + 0.35 * overlap, sentence, citation))
        candidates.sort(reverse=True, key=lambda row: row[0])
        selected: list[str] = []
        seen: set[str] = set()
        for _, sentence, citation in candidates:
            key = sentence.lower()
            if key in seen:
                continue
            seen.add(key)
            selected.append(f"{sentence} [{citation}]")
            if len(selected) == 4:
                break
        text = (
            " ".join(selected)
            if selected
            else "The available evidence does not contain a direct answer."
        )
        return GenerationResult(text, "local-extractive", "deterministic-extractive-v1")
