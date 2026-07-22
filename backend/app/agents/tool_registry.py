from __future__ import annotations

import inspect
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel

from app.agents.enums import AgentErrorCode
from app.agents.errors import AgentPolicyError
from app.agents.schemas import AgentToolResult
from app.llm.base import GenerationRequest
from app.llm.gateway import get_llm_gateway
from app.models.domain import RetrievedEvidence
from app.models.schemas import EvidenceItem
from app.rag.abstention import abstention_message
from app.rag.citations import append_citations
from app.rag.evidence import evidence_is_sufficient, key_terms
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
    timeout_seconds: float
    max_result_size: int
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
    sufficient_evidence: bool
    diagnosis: dict[str, Any] = {}


class SafetyReviewerInput(BaseModel):
    query: str
    answer: str | None = None
    evidence: list[EvidenceItem] = []


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
        metadata={"evidence_count": len(data.evidence), "term_coverage": round(coverage, 4)},
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
    diagnosis_status = data.diagnosis.get("status")
    should_abstain = (not data.sufficient_evidence) or diagnosis_status in {
        DiagnosisStatus.AMBIGUOUS_QUERY.value,
        DiagnosisStatus.CONFLICTING_EVIDENCE.value,
        DiagnosisStatus.KNOWLEDGE_ABSENT.value,
        DiagnosisStatus.PARTIAL_EVIDENCE.value,
        DiagnosisStatus.RETRIEVAL_FAILURE_UNRESOLVED.value,
    }
    retrieved = [_to_retrieved(item) for item in data.evidence]
    if should_abstain:
        answer = abstention_message(data.query)
        abstained = True
    else:
        result = await get_llm_gateway().answer(
            GenerationRequest(question=data.query, evidence=retrieved)
        )
        answer = append_citations(result.text, retrieved)
        abstained = False
    return AgentToolResult(
        tool="answer_synthesizer",
        status="success",
        summary="Answer synthesized with citations" if not abstained else "Agent abstained safely",
        evidence=data.evidence,
        answer=answer,
        sufficient_evidence=data.sufficient_evidence,
        citations=_citations(data.evidence),
        abstained=abstained,
        metadata={"retrieval_diagnosis": data.diagnosis},
    )


def _safety_reviewer_handler(payload: BaseModel, context: dict[str, Any]) -> AgentToolResult:
    data = SafetyReviewerInput.model_validate(payload)
    query_scan = scan_prompt(data.query)
    evidence_scan = scan_prompt(" ".join(item.content for item in data.evidence[:5]))
    answer_scan = scan_prompt(data.answer or "")
    safe = query_scan.safe and evidence_scan.safe and answer_scan.safe
    return AgentToolResult(
        tool="safety_reviewer",
        status="success" if safe else "failed",
        summary="Safe response reviewed" if safe else "Unsafe prompt injection signal detected",
        answer=data.answer if safe else abstention_message(data.query),
        evidence=data.evidence,
        abstained=not safe,
        citations=_citations(data.evidence) if safe else [],
        metadata={
            "safe": safe,
            "query_matches": query_scan.matches,
            "evidence_matches": evidence_scan.matches,
            "answer_matches": answer_scan.matches,
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


def build_default_registry() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(
        ToolDefinition(
            name="document_metadata",
            description="Read safe metadata for authorized workspace documents.",
            input_schema=DocumentMetadataInput,
            output_schema=AgentToolResult,
            required_permission="workspace:read",
            timeout_seconds=5.0,
            max_result_size=10_000,
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
            timeout_seconds=5.0,
            max_result_size=10_000,
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
            timeout_seconds=20.0,
            max_result_size=50_000,
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
            timeout_seconds=5.0,
            max_result_size=10_000,
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
            timeout_seconds=5.0,
            max_result_size=10_000,
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
            timeout_seconds=20.0,
            max_result_size=20_000,
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
            timeout_seconds=5.0,
            max_result_size=10_000,
            network_required=False,
            enabled=True,
            handler=_safety_reviewer_handler,
        )
    )
    registry.register(
        ToolDefinition(
            name="external_web_search",
            description="Future external web search placeholder.",
            input_schema=PlaceholderInput,
            output_schema=AgentToolResult,
            required_permission="external:network",
            timeout_seconds=10.0,
            max_result_size=0,
            network_required=True,
            enabled=False,
            handler=_disabled_placeholder_handler,
        )
    )
    return registry
