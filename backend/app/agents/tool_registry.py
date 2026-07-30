from __future__ import annotations

import inspect
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel

from app.agents.enums import AgentErrorCode
from app.agents.errors import AgentPolicyError
from app.agents.evidence import (
    UnifiedEvidence,
    deterministic_synthesize,
    normalize_external_sources,
    normalize_internal_evidence,
)
from app.agents.providers import build_web_search_provider
from app.agents.providers.arxiv import ArxivProvider
from app.agents.providers.base import ExternalProviderError, ProviderResponse
from app.agents.providers.wikipedia import WikipediaProvider
from app.agents.schemas import AgentToolResult, ExternalSource
from app.core.config import settings
from app.llm.base import GenerationRequest
from app.llm.gateway import get_llm_gateway
from app.models.domain import RetrievedEvidence
from app.models.schemas import EvidenceItem
from app.observability.metrics import (
    AGENT_EXTERNAL_SOURCES_USED,
    AGENT_EXTERNAL_TIMEOUTS,
    AGENT_EXTERNAL_TOOL_CALLS,
    AGENT_EXTERNAL_TOOL_DURATION,
    AGENT_EXTERNAL_TOOL_FAILURES,
    AGENT_SYNTHESIS_FALLBACKS,
)
from app.rag.abstention import abstention_message
from app.rag.citations import append_citations
from app.rag.evidence import assess_evidence_support, evidence_is_sufficient, key_terms
from app.rag.evidence_diagnosis import (
    DiagnosisStatus,
    diagnose_evidence,
    reformulate_query,
)
from app.rag.hybrid_retriever import retrieve
from app.rag.query_rewrite import rewrite_query
from app.repositories.documents import list_documents
from app.security.prompt_security import scan_prompt

ToolHandler = Callable[[BaseModel, dict[str, Any]], Awaitable[AgentToolResult] | AgentToolResult]


@dataclass(frozen=True, slots=True)
class ToolDefinition:
    name: str
    description: str
    input_schema: type[BaseModel]
    output_schema: type[BaseModel]
    required_permission: str
    feature_flag: str | None
    timeout_seconds: float
    max_result_count: int
    max_result_size: int
    max_response_size: int
    network_required: bool
    enabled: bool
    handler: ToolHandler


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, ToolDefinition] = {}

    def register(self, tool: ToolDefinition) -> None:
        if tool.name in self._tools:
            raise ValueError(f"Tool already registered: {tool.name}")
        self._tools[tool.name] = tool

    def get(self, name: str) -> ToolDefinition:
        if name not in self._tools:
            raise AgentPolicyError(AgentErrorCode.UNKNOWN_TOOL, f"Unknown tool: {name}")
        return self._tools[name]

    @property
    def names(self) -> tuple[str, ...]:
        return tuple(sorted(self._tools))

    async def execute(
        self, name: str, payload: dict[str, Any], context: dict[str, Any]
    ) -> AgentToolResult:
        tool = self.get(name)
        if not tool.enabled:
            raise AgentPolicyError(AgentErrorCode.TOOL_DISABLED, f"Tool is disabled: {name}")
        parsed = tool.input_schema.model_validate(payload)
        result = tool.handler(parsed, context)
        if inspect.isawaitable(result):
            result = await result
        return tool.output_schema.model_validate(result)


class InternalSearchInput(BaseModel):
    query: str
    top_k: int | None = None


class DocumentMetadataInput(BaseModel):
    include_counts: bool = True


class QueryReformulationInput(BaseModel):
    query: str
    retry: bool = False


class EvidenceVerifierInput(BaseModel):
    query: str
    evidence: list[EvidenceItem]


class RetrievalDiagnosisInput(BaseModel):
    query: str
    initial_evidence: list[EvidenceItem]
    final_evidence: list[EvidenceItem]
    initial_evidence_sufficient: bool
    final_evidence_sufficient: bool
    retry_performed: bool = False
    retry_strategy: list[str] = []


class AnswerSynthesizerInput(BaseModel):
    query: str
    evidence: list[EvidenceItem]
    external_sources: list[ExternalSource] = []
    unified_evidence: list[dict[str, Any]] = []
    sufficient_evidence: bool
    diagnosis: dict[str, Any] = {}


class SafetyReviewerInput(BaseModel):
    query: str
    answer: str | None = None
    evidence: list[EvidenceItem] = []
    external_sources: list[ExternalSource] = []
    unified_evidence: list[dict[str, Any]] = []
    citations: list[dict[str, Any]] = []


class ExternalSearchInput(BaseModel):
    query: str
    max_results: int | None = None


class PlaceholderInput(BaseModel):
    reason: str | None = None


async def _internal_search_handler(payload: BaseModel, context: dict[str, Any]) -> AgentToolResult:
    data = InternalSearchInput.model_validate(payload)
    evidence = await retrieve(
        context["session"],
        workspace_id=context["workspace_id"],
        query=data.query,
        top_k=data.top_k,
        document_ids=context.get("document_ids"),
    )
    sufficient = evidence_is_sufficient(
        [item.score for item in evidence], data.query, [item.content for item in evidence]
    )
    return AgentToolResult(
        tool="internal_search",
        status="success",
        summary="Internal document search completed",
        evidence=[_to_evidence_item(item) for item in evidence],
        sufficient_evidence=sufficient,
        query=data.query,
        metadata={
            "tenant_scope_preserved": True,
            "workspace_scope_preserved": True,
            "evidence_count": len(evidence),
            **(
                {
                    key: evidence[0].metadata.get(key)
                    for key in (
                        "retrieval_mode",
                        "semantic_used",
                        "reranker_used",
                        "fallback_used",
                        "candidate_count",
                        "retrieval_duration_ms",
                        "embedding_version",
                        "reranker_version",
                    )
                }
                if evidence
                else {}
            ),
        },
    )


async def _document_metadata_handler(
    payload: BaseModel, context: dict[str, Any]
) -> AgentToolResult:
    data = DocumentMetadataInput.model_validate(payload)
    documents = await list_documents(context["session"], context["workspace_id"])
    ready_count = sum(1 for document in documents if document.status == "ready")
    return AgentToolResult(
        tool="document_metadata",
        status="success",
        summary="Workspace document metadata inspected",
        metadata={
            "document_count": len(documents) if data.include_counts else None,
            "ready_document_count": ready_count if data.include_counts else None,
            "tenant_scope_preserved": True,
            "workspace_scope_preserved": True,
        },
    )


def _query_reformulation_handler(payload: BaseModel, context: dict[str, Any]) -> AgentToolResult:
    data = QueryReformulationInput.model_validate(payload)
    normalized = rewrite_query(data.query)
    query = reformulate_query(normalized) if data.retry else normalized
    summary = "Query reformulated for retrieval retry" if data.retry else "Query normalized"
    return AgentToolResult(
        tool="query_reformulation",
        status="success",
        summary=summary,
        query=query,
        metadata={"retry": data.retry, "original_query_changed": query != data.query},
    )


def _evidence_verifier_handler(payload: BaseModel, context: dict[str, Any]) -> AgentToolResult:
    data = EvidenceVerifierInput.model_validate(payload)
    terms = key_terms(data.query)
    evidence_terms = key_terms(" ".join(item.content for item in data.evidence[:3]))
    coverage = len(terms & evidence_terms) / max(1, len(terms))
    sufficient = evidence_is_sufficient(
        [item.score for item in data.evidence], data.query, [item.content for item in data.evidence]
    )
    assessment = assess_evidence_support(
        [item.score for item in data.evidence], data.query, [item.content for item in data.evidence]
    )
    if " and " in data.query.lower() and coverage <= 0.6:
        sufficient = False
    summary = (
        "Final citations verified"
        if sufficient and data.evidence
        else "Evidence insufficient; retrieval retry requested"
    )
    return AgentToolResult(
        tool="evidence_verifier",
        status="success",
        summary=summary,
        evidence=data.evidence,
        sufficient_evidence=sufficient,
        metadata={
            "evidence_count": len(data.evidence),
            "term_coverage": round(coverage, 4),
            "support_assessment": assessment.as_dict(),
        },
    )


def _retrieval_diagnosis_handler(payload: BaseModel, context: dict[str, Any]) -> AgentToolResult:
    data = RetrievalDiagnosisInput.model_validate(payload)
    diagnosis = diagnose_evidence(
        query=data.query,
        initial_evidence=[_to_retrieved(item) for item in data.initial_evidence],
        final_evidence=[_to_retrieved(item) for item in data.final_evidence],
        initial_evidence_sufficient=data.initial_evidence_sufficient,
        final_evidence_sufficient=data.final_evidence_sufficient,
        retry_performed=data.retry_performed,
        retry_strategy=data.retry_strategy,
    )
    return AgentToolResult(
        tool="retrieval_diagnosis",
        status="success",
        summary=f"Retrieval diagnosis: {diagnosis.status.value}",
        evidence=data.final_evidence,
        sufficient_evidence=data.final_evidence_sufficient,
        metadata={"retrieval_diagnosis": diagnosis.as_dict()},
    )


async def _answer_synthesizer_handler(
    payload: BaseModel, context: dict[str, Any]
) -> AgentToolResult:
    data = AnswerSynthesizerInput.model_validate(payload)
    if data.unified_evidence:
        try:
            unified = [UnifiedEvidence.model_validate(item) for item in data.unified_evidence]
            synthesis = deterministic_synthesize(data.query, unified, data.diagnosis)
            return AgentToolResult(
                tool="answer_synthesizer",
                status="success",
                summary=(
                    "Grounded answer synthesized with validated citations"
                    if not synthesis.abstained
                    else "Agent abstained safely after claim verification"
                ),
                evidence=data.evidence,
                external_sources=data.external_sources,
                unified_evidence=[item.model_dump(mode="json") for item in unified],
                answer=synthesis.answer,
                sufficient_evidence=not synthesis.abstained,
                citations=synthesis.citations,
                abstained=synthesis.abstained,
                claims=[item.model_dump(mode="json") for item in synthesis.claims],
                conflicts=[item.model_dump(mode="json") for item in synthesis.conflicts],
                unsupported_claims_removed=synthesis.unsupported_claims_removed,
                outcome=synthesis.outcome.value,
                confidence_category=synthesis.confidence_category.value,
                metadata={
                    "retrieval_diagnosis": data.diagnosis,
                    "synthesizer": "deterministic_extractive",
                    "citation_validation": "validated",
                },
            )
        except Exception:
            AGENT_SYNTHESIS_FALLBACKS.labels(outcome="validation_failure").inc()
    diagnosis_status = data.diagnosis.get("status")
    has_external = bool(data.external_sources)
    terminal_internal_diagnosis = diagnosis_status in {
        DiagnosisStatus.AMBIGUOUS_QUERY.value,
        DiagnosisStatus.CONFLICTING_EVIDENCE.value,
        DiagnosisStatus.KNOWLEDGE_ABSENT.value,
        DiagnosisStatus.PARTIAL_EVIDENCE.value,
        DiagnosisStatus.RETRIEVAL_FAILURE_UNRESOLVED.value,
    }
    should_abstain = ((not data.sufficient_evidence) or terminal_internal_diagnosis) and not (
        has_external and diagnosis_status != DiagnosisStatus.CONFLICTING_EVIDENCE.value
    )
    retrieved = [_to_retrieved(item) for item in data.evidence]
    generation_metadata: dict[str, Any] = {
        "generation_provider": "extractive",
        "generation_used": False,
        "generation_fallback_used": False,
        "generation_verification": "not_applicable",
    }
    generated_citations: list[dict[str, Any]] = []
    if should_abstain:
        answer = abstention_message(data.query)
        abstained = True
    elif has_external and not retrieved:
        first = data.external_sources[0]
        answer = (
            "External source evidence is available from "
            f"{first.provider}: {first.title}. {first.excerpt[:500]} [E1]"
        )
        abstained = False
    else:
        result = await get_llm_gateway().answer(
            GenerationRequest(question=data.query, evidence=retrieved)
        )
        answer = append_citations(result.text, retrieved)
        generated_citations = list(result.citations)
        generation_metadata = {
            "generation_provider": result.provider,
            "generation_model": result.model,
            "generation_used": result.used,
            "generation_fallback_used": result.fallback_used,
            "generation_duration_ms": result.duration_ms,
            "generation_verification": result.verification,
            "structured_output_valid": result.structured_output_valid,
            "claim_verification_passed": result.claim_verification_passed,
        }
        abstained = False
    return AgentToolResult(
        tool="answer_synthesizer",
        status="success",
        summary="Answer synthesized with citations" if not abstained else "Agent abstained safely",
        evidence=data.evidence,
        external_sources=data.external_sources,
        answer=answer,
        sufficient_evidence=data.sufficient_evidence,
        citations=(generated_citations or _citations(data.evidence))
        + _external_citations(data.external_sources),
        abstained=abstained,
        metadata={"retrieval_diagnosis": data.diagnosis, **generation_metadata},
    )


def _safety_reviewer_handler(payload: BaseModel, context: dict[str, Any]) -> AgentToolResult:
    data = SafetyReviewerInput.model_validate(payload)
    cited_labels = {
        str(citation.get("citation_label") or citation.get("external_source_label") or "")
        for citation in data.citations
    }
    cited_unified = [
        item
        for item in data.unified_evidence
        if not cited_labels or str(item.get("citation_label")) in cited_labels
    ]
    query_scan = scan_prompt(data.query)
    evidence_scan = scan_prompt(
        "" if data.unified_evidence else " ".join(item.content for item in data.evidence[:5])
    )
    external_scan = scan_prompt(
        ""
        if data.unified_evidence
        else " ".join(item.excerpt for item in data.external_sources[:5])
    )
    unified_scan = scan_prompt(" ".join(str(item.get("excerpt", "")) for item in cited_unified[:5]))
    answer_scan = scan_prompt(data.answer or "")
    safe = (
        query_scan.safe
        and evidence_scan.safe
        and external_scan.safe
        and unified_scan.safe
        and answer_scan.safe
    )
    return AgentToolResult(
        tool="safety_reviewer",
        status="success" if safe else "failed",
        summary="Safe response reviewed" if safe else "Unsafe prompt injection signal detected",
        answer=data.answer if safe else abstention_message(data.query),
        evidence=data.evidence,
        external_sources=data.external_sources,
        unified_evidence=data.unified_evidence,
        abstained=not safe,
        citations=(
            data.citations
            if safe and data.citations
            else (
                _citations(data.evidence) + _external_citations(data.external_sources)
                if safe
                else []
            )
        ),
        outcome=None if safe else "SAFETY_BLOCKED",
        confidence_category=None if safe else "none",
        metadata={
            "safe": safe,
            "query_matches": query_scan.matches,
            "evidence_matches": evidence_scan.matches,
            "external_matches": external_scan.matches,
            "unified_evidence_matches": unified_scan.matches,
            "answer_matches": answer_scan.matches,
        },
    )


async def _web_search_handler(payload: BaseModel, context: dict[str, Any]) -> AgentToolResult:
    if not context.get("allow_external_sources") or not settings.agent_web_search_enabled:
        return _external_disabled_result("web_search", "web_search")
    data = ExternalSearchInput.model_validate(payload)
    provider = build_web_search_provider()
    return await _execute_external_provider(
        tool="web_search",
        provider=provider,
        query=data.query,
        max_results=data.max_results or settings.web_search_max_results,
    )


async def _wikipedia_lookup_handler(payload: BaseModel, context: dict[str, Any]) -> AgentToolResult:
    if not context.get("allow_external_sources") or not settings.agent_external_apis_enabled:
        return _external_disabled_result("wikipedia_lookup", "wikipedia")
    data = ExternalSearchInput.model_validate(payload)
    provider = WikipediaProvider(
        timeout_seconds=settings.web_search_timeout_seconds,
        max_response_bytes=settings.web_search_max_response_bytes,
    )
    return await _execute_external_provider(
        tool="wikipedia_lookup",
        provider=provider,
        query=data.query,
        max_results=data.max_results or settings.web_search_max_results,
    )


async def _arxiv_search_handler(payload: BaseModel, context: dict[str, Any]) -> AgentToolResult:
    if not context.get("allow_external_sources") or not settings.agent_external_apis_enabled:
        return _external_disabled_result("arxiv_search", "arxiv")
    data = ExternalSearchInput.model_validate(payload)
    provider = ArxivProvider(
        timeout_seconds=settings.web_search_timeout_seconds,
        max_response_bytes=settings.web_search_max_response_bytes,
    )
    return await _execute_external_provider(
        tool="arxiv_search",
        provider=provider,
        query=data.query,
        max_results=data.max_results or settings.web_search_max_results,
    )


async def _execute_external_provider(
    *, tool: str, provider: Any, query: str, max_results: int
) -> AgentToolResult:
    started = time.perf_counter()
    outcome = "success"
    provider_name = getattr(provider, "name", "unknown")
    try:
        response: ProviderResponse = await provider.search(query, max_results=max_results)
        provider_name = response.provider
        outcome = response.status
        AGENT_EXTERNAL_TOOL_CALLS.labels(
            provider=response.provider, tool=tool, outcome=outcome
        ).inc()
        if response.results:
            AGENT_EXTERNAL_SOURCES_USED.labels(provider=response.provider, tool=tool).inc(
                len(response.results)
            )
        return AgentToolResult(
            tool=tool,
            status=response.status,
            summary=(
                "External provider is disabled"
                if response.disabled
                else "External source search completed"
            ),
            external_sources=response.results,
            metadata={
                "provider": response.provider,
                "disabled": response.disabled,
                "external_access_performed": bool(response.results),
                "untrusted_source_boundary": True,
                "error": response.error,
            },
        )
    except TimeoutError:
        outcome = "timeout"
        AGENT_EXTERNAL_TIMEOUTS.labels(provider=provider_name, tool=tool).inc()
        AGENT_EXTERNAL_TOOL_FAILURES.labels(
            provider=provider_name, tool=tool, outcome=outcome
        ).inc()
        return AgentToolResult(
            tool=tool,
            status="timeout",
            summary="External provider timed out",
            metadata={"provider": provider_name, "error": "timeout"},
        )
    except ExternalProviderError as exc:
        provider_name = exc.provider
        outcome = exc.reason
        AGENT_EXTERNAL_TOOL_FAILURES.labels(
            provider=provider_name, tool=tool, outcome=outcome
        ).inc()
        return AgentToolResult(
            tool=tool,
            status="failed",
            summary="External provider failed safely",
            metadata={"provider": provider_name, "error": exc.reason},
        )
    finally:
        AGENT_EXTERNAL_TOOL_DURATION.labels(
            provider=provider_name, tool=tool, outcome=outcome
        ).observe(time.perf_counter() - started)


def _external_disabled_result(tool: str, provider: str) -> AgentToolResult:
    AGENT_EXTERNAL_TOOL_CALLS.labels(provider=provider, tool=tool, outcome="disabled").inc()
    return AgentToolResult(
        tool=tool,
        status="disabled",
        summary="External tool disabled; no network access attempted",
        metadata={
            "provider": provider,
            "disabled": True,
            "external_access_performed": False,
            "untrusted_source_boundary": True,
        },
    )


def _disabled_placeholder_handler(payload: BaseModel, context: dict[str, Any]) -> AgentToolResult:
    raise AgentPolicyError(
        AgentErrorCode.TOOL_DISABLED, "Placeholder tools are disabled in this phase"
    )


def _to_evidence_item(item: RetrievedEvidence) -> EvidenceItem:
    return EvidenceItem(
        chunk_id=item.chunk_id,
        document_id=item.document_id,
        document_title=item.document_title,
        content=item.content,
        score=item.score,
        metadata=item.metadata,
    )


def _to_retrieved(item: EvidenceItem) -> RetrievedEvidence:
    return RetrievedEvidence(
        chunk_id=item.chunk_id,
        document_id=item.document_id,
        document_title=item.document_title,
        content=item.content,
        score=item.score,
        metadata=item.metadata,
    )


def _citations(evidence: list[EvidenceItem]) -> list[dict[str, Any]]:
    return [
        {
            "index": index,
            "chunk_id": str(item.chunk_id),
            "document_id": str(item.document_id),
            "document_title": item.document_title,
        }
        for index, item in enumerate(evidence, 1)
    ]


def _external_citations(sources: list[ExternalSource]) -> list[dict[str, Any]]:
    return [
        {
            "index": index,
            "source": "external",
            "external_source_label": f"E{index}",
            "provider": item.provider,
            "title": item.title,
            "canonical_url": item.canonical_url,
            "retrieval_date": item.retrieval_timestamp.date().isoformat(),
            "excerpt": item.excerpt,
        }
        for index, item in enumerate(sources, 1)
    ]


def normalize_tool_evidence(
    internal: list[EvidenceItem],
    external: list[ExternalSource],
    *,
    tenant_id: Any,
    workspace_id: Any,
) -> list[UnifiedEvidence]:
    return normalize_internal_evidence(
        internal,
        tenant_id=tenant_id,
        workspace_id=workspace_id,
    ) + normalize_external_sources(external)


def build_default_registry() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(
        ToolDefinition(
            name="document_metadata",
            description="Read safe metadata for authorized workspace documents.",
            input_schema=DocumentMetadataInput,
            output_schema=AgentToolResult,
            required_permission="workspace:read",
            feature_flag=None,
            timeout_seconds=5.0,
            max_result_count=1,
            max_result_size=10_000,
            max_response_size=10_000,
            network_required=False,
            enabled=True,
            handler=_document_metadata_handler,
        )
    )
    registry.register(
        ToolDefinition(
            name="query_reformulation",
            description="Normalize or reformulate a query for internal retrieval.",
            input_schema=QueryReformulationInput,
            output_schema=AgentToolResult,
            required_permission="workspace:read",
            feature_flag=None,
            timeout_seconds=5.0,
            max_result_count=1,
            max_result_size=10_000,
            max_response_size=10_000,
            network_required=False,
            enabled=True,
            handler=_query_reformulation_handler,
        )
    )
    registry.register(
        ToolDefinition(
            name="internal_search",
            description="Search authorized internal workspace documents.",
            input_schema=InternalSearchInput,
            output_schema=AgentToolResult,
            required_permission="workspace:read",
            feature_flag=None,
            timeout_seconds=20.0,
            max_result_count=50,
            max_result_size=50_000,
            max_response_size=50_000,
            network_required=False,
            enabled=True,
            handler=_internal_search_handler,
        )
    )
    registry.register(
        ToolDefinition(
            name="evidence_verifier",
            description="Check whether retrieved evidence can support an answer.",
            input_schema=EvidenceVerifierInput,
            output_schema=AgentToolResult,
            required_permission="workspace:read",
            feature_flag=None,
            timeout_seconds=5.0,
            max_result_count=50,
            max_result_size=10_000,
            max_response_size=10_000,
            network_required=False,
            enabled=True,
            handler=_evidence_verifier_handler,
        )
    )
    registry.register(
        ToolDefinition(
            name="retrieval_diagnosis",
            description="Classify retrieval result state without exposing hidden reasoning.",
            input_schema=RetrievalDiagnosisInput,
            output_schema=AgentToolResult,
            required_permission="workspace:read",
            feature_flag=None,
            timeout_seconds=5.0,
            max_result_count=1,
            max_result_size=10_000,
            max_response_size=10_000,
            network_required=False,
            enabled=True,
            handler=_retrieval_diagnosis_handler,
        )
    )
    registry.register(
        ToolDefinition(
            name="answer_synthesizer",
            description="Synthesize an answer from verified internal evidence.",
            input_schema=AnswerSynthesizerInput,
            output_schema=AgentToolResult,
            required_permission="workspace:read",
            feature_flag=None,
            timeout_seconds=20.0,
            max_result_count=50,
            max_result_size=20_000,
            max_response_size=20_000,
            network_required=False,
            enabled=True,
            handler=_answer_synthesizer_handler,
        )
    )
    registry.register(
        ToolDefinition(
            name="safety_reviewer",
            description="Review query, evidence, and final answer for prompt-injection signals.",
            input_schema=SafetyReviewerInput,
            output_schema=AgentToolResult,
            required_permission="workspace:read",
            feature_flag=None,
            timeout_seconds=5.0,
            max_result_count=50,
            max_result_size=10_000,
            max_response_size=10_000,
            network_required=False,
            enabled=True,
            handler=_safety_reviewer_handler,
        )
    )
    registry.register(
        ToolDefinition(
            name="web_search",
            description="Search an approved web-search provider when explicitly enabled.",
            input_schema=ExternalSearchInput,
            output_schema=AgentToolResult,
            required_permission="external:search",
            feature_flag="agent_web_search_enabled",
            timeout_seconds=settings.web_search_timeout_seconds,
            max_result_count=settings.web_search_max_results,
            max_result_size=50_000,
            max_response_size=settings.web_search_max_response_bytes,
            network_required=True,
            enabled=True,
            handler=_web_search_handler,
        )
    )
    registry.register(
        ToolDefinition(
            name="wikipedia_lookup",
            description="Look up approved Wikipedia public API excerpts.",
            input_schema=ExternalSearchInput,
            output_schema=AgentToolResult,
            required_permission="external:api",
            feature_flag="agent_external_apis_enabled",
            timeout_seconds=settings.web_search_timeout_seconds,
            max_result_count=settings.web_search_max_results,
            max_result_size=50_000,
            max_response_size=settings.web_search_max_response_bytes,
            network_required=True,
            enabled=True,
            handler=_wikipedia_lookup_handler,
        )
    )
    registry.register(
        ToolDefinition(
            name="arxiv_search",
            description="Search approved arXiv public API metadata and abstracts.",
            input_schema=ExternalSearchInput,
            output_schema=AgentToolResult,
            required_permission="external:api",
            feature_flag="agent_external_apis_enabled",
            timeout_seconds=settings.web_search_timeout_seconds,
            max_result_count=settings.web_search_max_results,
            max_result_size=50_000,
            max_response_size=settings.web_search_max_response_bytes,
            network_required=True,
            enabled=True,
            handler=_arxiv_search_handler,
        )
    )
    registry.register(
        ToolDefinition(
            name="external_web_search",
            description="Future external web search placeholder.",
            input_schema=PlaceholderInput,
            output_schema=AgentToolResult,
            required_permission="external:network",
            feature_flag="agent_web_search_enabled",
            timeout_seconds=10.0,
            max_result_count=0,
            max_result_size=0,
            max_response_size=0,
            network_required=True,
            enabled=False,
            handler=_disabled_placeholder_handler,
        )
    )
    return registry
