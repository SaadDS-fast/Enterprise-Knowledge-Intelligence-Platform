from __future__ import annotations

import asyncio
import ipaddress
import json
import logging
import re
import socket
import time
from dataclasses import dataclass
from urllib.parse import urlsplit

import httpx
from pydantic import ValidationError

from app.core.config import LocalLLMBackend, settings
from app.llm.answer_plan import build_answer_plan
from app.llm.base import GenerationRequest, GenerationResult, LLMProvider
from app.llm.grounded import (
    INJECTION_PATTERN,
    build_evidence_packet,
)
from app.llm.grounded_v2 import (
    GroundedCandidateV2,
    build_planned_prompt,
    candidate_schema_v2,
    normalize_candidate_payload,
    verify_and_render,
)
from app.observability.metrics import (
    GENERATION_DURATION,
    GENERATION_FALLBACKS,
    GENERATION_REQUESTS,
    GENERATION_SUCCESSES,
    GENERATION_TIMEOUTS,
    GENERATION_VERIFICATION_FAILURES,
)
from app.rag.embeddings import tokenize
from app.rag.evidence import assess_evidence_support, synthesize_direct_answer

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class _Circuit:
    failures: int = 0
    opened_at: float | None = None

    def available(self, now: float) -> bool:
        if self.opened_at is None:
            return True
        if now - self.opened_at >= settings.ollama_circuit_recovery_seconds:
            self.opened_at = None
            self.failures = 0
            return True
        return False

    def fail(self, now: float) -> None:
        self.failures += 1
        if self.failures >= settings.ollama_circuit_failure_threshold:
            self.opened_at = now

    def succeed(self) -> None:
        self.failures = 0
        self.opened_at = None


_circuit = _Circuit()


class LocalProvider(LLMProvider):
    async def generate(self, request: GenerationRequest) -> GenerationResult:
        fallback = self._extractive(request)
        if not settings.ollama_enabled or settings.local_llm_backend is not LocalLLMBackend.OLLAMA:
            return fallback
        now = time.monotonic()
        if not _circuit.available(now):
            return self._fallback(fallback, "circuit_open")
        GENERATION_REQUESTS.labels(provider="ollama").inc()
        started = time.perf_counter()
        try:
            result = await self._ollama(request)
        except TimeoutError:
            _circuit.fail(time.monotonic())
            GENERATION_TIMEOUTS.labels(provider="ollama").inc()
            return self._fallback(fallback, "generation_timeout", started)
        except (httpx.HTTPError, OSError, ValueError, ValidationError) as exc:
            _circuit.fail(time.monotonic())
            logger.warning(
                "Local generation unavailable; safe fallback used (%s)", type(exc).__name__
            )
            return self._fallback(fallback, "provider_unavailable", started)
        if not result.used:
            safe = self._fallback(fallback, result.verification, started)
            return GenerationResult(
                text=safe.text,
                provider=safe.provider,
                model=safe.model,
                fallback_used=True,
                duration_ms=result.duration_ms,
                verification=result.verification,
                structured_output_valid=result.structured_output_valid,
            )
        _circuit.succeed()
        GENERATION_DURATION.labels(provider="ollama", outcome="verified").observe(
            result.duration_ms / 1000
        )
        GENERATION_SUCCESSES.labels(provider="ollama").inc()
        return result

    async def _ollama(self, request: GenerationRequest) -> GenerationResult:
        await _validate_runtime_endpoint()
        packet = build_evidence_packet(request.evidence)
        if not packet:
            raise ValueError("empty_evidence_packet")
        plan = build_answer_plan(request.question, packet)
        if not plan.components:
            raise ValueError("empty_answer_plan")
        prompt = build_planned_prompt(request.question, packet, plan)
        timeout = httpx.Timeout(
            settings.ollama_generation_timeout_seconds,
            connect=settings.ollama_connect_timeout_seconds,
        )
        started = time.perf_counter()
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=False) as client:
            await self._ensure_model_installed(client)
            schema_valid = False
            for attempt in range(settings.ollama_max_retries + 1):
                try:
                    response = await client.post(
                        f"{settings.local_llm_base_url.rstrip('/')}/api/generate",
                        json={
                            "model": settings.local_llm_model,
                            "prompt": prompt
                            + (
                                "\n\nYour prior output was invalid. Return only schema-valid JSON."
                                if attempt
                                else ""
                            ),
                            "stream": False,
                            "format": candidate_schema_v2(),
                            "keep_alive": settings.ollama_keep_alive,
                            "options": {
                                "temperature": 0,
                                "num_predict": settings.llm_max_output_tokens,
                            },
                        },
                    )
                    response.raise_for_status()
                except httpx.TimeoutException as exc:
                    raise TimeoutError("ollama_timeout") from exc
                payload = response.json()
                # Ollama may expose model thinking separately. It is deliberately ignored.
                raw_text = payload.get("response", "")
                try:
                    raw = json.loads(raw_text)
                    candidate = GroundedCandidateV2.model_validate(
                        normalize_candidate_payload(raw, plan)
                    )
                    schema_valid = True
                    break
                except (json.JSONDecodeError, ValidationError, TypeError):
                    if attempt >= settings.ollama_max_retries:
                        return self._verification_failure(
                            "schema_validation_failed", started, schema_valid=False
                        )
            verification = verify_and_render(candidate, plan, packet)
            if not verification.passed:
                return self._verification_failure(
                    verification.category, started, schema_valid=schema_valid
                )
            return GenerationResult(
                text=verification.answer,
                provider="ollama",
                model=settings.local_llm_model,
                used=True,
                duration_ms=(time.perf_counter() - started) * 1000,
                verification=verification.category,
                structured_output_valid=True,
                claim_verification_passed=True,
                citations=tuple(verification.citations),
                input_tokens=payload.get("prompt_eval_count"),
                output_tokens=payload.get("eval_count"),
                load_duration_ms=(
                    float(payload["load_duration"]) / 1_000_000
                    if payload.get("load_duration") is not None
                    else None
                ),
            )

    async def _ensure_model_installed(self, client: httpx.AsyncClient) -> None:
        if settings.local_llm_model not in settings.ollama_allowed_models:
            raise ValueError("model_not_allowlisted")
        response = await client.get(f"{settings.local_llm_base_url.rstrip('/')}/api/tags")
        response.raise_for_status()
        installed = {item.get("name") for item in response.json().get("models", [])}
        if settings.local_llm_model not in installed:
            raise ValueError("model_not_installed")

    def _verification_failure(
        self, category: str, started: float, *, schema_valid: bool
    ) -> GenerationResult:
        GENERATION_VERIFICATION_FAILURES.labels(category=category).inc()
        return GenerationResult(
            text="",
            provider="ollama",
            model=settings.local_llm_model,
            duration_ms=(time.perf_counter() - started) * 1000,
            verification=category,
            structured_output_valid=schema_valid,
        )

    def _extractive(self, request: GenerationRequest) -> GenerationResult:
        assessment = assess_evidence_support(
            [item.score for item in request.evidence],
            request.question,
            [item.content for item in request.evidence],
        )
        direct_answer = synthesize_direct_answer(request.question, assessment)
        if direct_answer:
            if re.search(
                r"(?i)\b(amount|allowance|limit|monetary|effective|published|equation)\b",
                request.question,
            ):
                for item in request.evidence:
                    for sentence in re.split(r"(?<=[.!?])\s+|\n+", item.content):
                        if (
                            direct_answer.casefold() in sentence.casefold()
                            and not INJECTION_PATTERN.search(sentence)
                        ):
                            direct_answer = sentence.strip()
                            break
            return GenerationResult(direct_answer, "extractive", "deterministic-extractive-v2")
        query_tokens = set(tokenize(request.question))
        candidates: list[tuple[float, str, int]] = []
        for citation, item in enumerate(request.evidence, 1):
            for sentence in re.split(r"(?<=[.!?])\s+|\n+", item.content):
                sentence = sentence.strip()
                if len(sentence) < 20 or INJECTION_PATTERN.search(sentence):
                    continue
                overlap = len(query_tokens & set(tokenize(sentence))) / max(1, len(query_tokens))
                candidates.append((0.65 * item.score + 0.35 * overlap, sentence, citation))
        candidates.sort(reverse=True, key=lambda row: row[0])
        selected: list[str] = []
        seen: set[str] = set()
        for _, sentence, citation in candidates:
            if sentence.lower() in seen:
                continue
            seen.add(sentence.lower())
            selected.append(f"{sentence} [{citation}]")
            if len(selected) == 4:
                break
        text = " ".join(selected) or "The available evidence does not contain a direct answer."
        return GenerationResult(text, "extractive", "deterministic-extractive-v1")

    def _fallback(
        self, fallback: GenerationResult, category: str, started: float | None = None
    ) -> GenerationResult:
        GENERATION_FALLBACKS.labels(category=category).inc()
        return GenerationResult(
            text=fallback.text,
            provider="extractive",
            model=fallback.model,
            fallback_used=True,
            duration_ms=(time.perf_counter() - started) * 1000 if started else 0,
            verification=category,
        )


async def _validate_runtime_endpoint() -> None:
    parsed = urlsplit(settings.local_llm_base_url)
    host = parsed.hostname
    if not host:
        raise ValueError("missing_ollama_host")
    loop = asyncio.get_running_loop()
    records = await loop.run_in_executor(
        None, lambda: socket.getaddrinfo(host, parsed.port or 11434, type=socket.SOCK_STREAM)
    )
    addresses = {record[4][0] for record in records}
    if not addresses:
        raise ValueError("ollama_dns_empty")
    for raw in addresses:
        address = ipaddress.ip_address(raw)
        if address.is_link_local or not (address.is_private or address.is_loopback):
            raise ValueError("ollama_dns_not_private")
