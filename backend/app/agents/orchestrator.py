from __future__ import annotations

import time
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.budgets import AgentBudget
from app.agents.enums import (
    AgentErrorCode,
    AgentRunStatus,
    AgentStateName,
    AgentToolStatus,
)
from app.agents.errors import AgentBudgetError, AgentCancelledError, AgentError, AgentPolicyError
from app.agents.evidence import (
    AnswerOutcome,
    aggregate_evidence,
    map_diagnosis_to_outcome,
    normalize_external_sources,
    normalize_internal_evidence,
)
from app.agents.executor import ToolExecutor
from app.agents.planner import PlannerProvider, get_planner
from app.agents.policies import safe_operational_summary, validate_plan
from app.agents.schemas import (
    AgentQueryRequest,
    AgentQueryResponse,
    AgentRunRead,
    AgentToolResult,
    PlannerStep,
)
from app.agents.state import AgentRuntimeState
from app.agents.tool_registry import ToolRegistry, build_default_registry
from app.core.config import settings
from app.db.models import AgentRun, AgentStep, AgentToolCall, AuditEvent
from app.observability.metrics import (
    AGENT_DURATION,
    AGENT_FALLBACKS,
    AGENT_REPLANS,
    AGENT_RUNS_COMPLETED,
    AGENT_RUNS_FAILED,
    AGENT_RUNS_STARTED,
)
from app.rag.evidence_diagnosis import DiagnosisStatus, reformulate_query
from app.rag.response_state import legacy_fields, response_state_from_legacy
from app.services.search_service import search_and_answer
from app.tenancy.context import TenantContext

TERMINAL_DIAGNOSES = {
    DiagnosisStatus.KNOWLEDGE_ABSENT.value,
    DiagnosisStatus.AMBIGUOUS_QUERY.value,
    DiagnosisStatus.CONFLICTING_EVIDENCE.value,
    DiagnosisStatus.PARTIAL_EVIDENCE.value,
    DiagnosisStatus.RETRIEVAL_FAILURE_UNRESOLVED.value,
}


class AgentOrchestrator:
    def __init__(
        self,
        *,
        registry: ToolRegistry | None = None,
        planner: PlannerProvider | None = None,
        budget: AgentBudget | None = None,
    ) -> None:
        self.registry = registry or build_default_registry()
        self.planner = planner or get_planner()
        self.budget = budget or AgentBudget.from_settings()
        self.executor = ToolExecutor(self.registry, self.budget)

    async def run(
        self,
        session: AsyncSession,
        *,
        tenant: TenantContext,
        payload: AgentQueryRequest,
        request_id: str | None = None,
        cancel_requested: bool = False,
    ) -> AgentQueryResponse:
        started = time.perf_counter()
        AGENT_RUNS_STARTED.inc()
        runtime = AgentRuntimeState(
            query=payload.query,
            workspace_id=tenant.workspace_id,
            user_id=tenant.user_id,
            request_id=request_id,
            cancelled=cancel_requested,
        )
        run = AgentRun(
            tenant_id=tenant.organization_id,
            workspace_id=tenant.workspace_id,
            user_id=tenant.user_id,
            request_id=request_id,
            status=AgentRunStatus.RUNNING.value,
            current_state=runtime.current_state.value,
            input_query=payload.query,
            result_json={},
        )
        session.add(run)
        await session.flush()
        await self._audit(session, tenant, run.id, request_id, "agent.run.created")

        try:
            if runtime.cancelled:
                raise AgentCancelledError()
            await self._record_state(
                session, run, runtime, AgentStateName.RECEIVE_REQUEST, "Agent request received"
            )
            await self._record_state(
                session,
                run,
                runtime,
                AgentStateName.AUTHORIZE,
                "Tenant workspace scope authorized",
            )
            await self._record_state(
                session,
                run,
                runtime,
                AgentStateName.CLASSIFY_INTENT,
                "Intent classified as document_question",
            )

            plan = await self.planner.create_plan(payload.query)
            runtime.plan_summary = safe_operational_summary(plan.safe_summary())
            validate_plan(
                plan,
                registry=self.registry,
                budget=self.budget,
                workspace_id=tenant.workspace_id,
                allow_external_sources=payload.allow_external_sources,
            )
            await self._record_state(
                session,
                run,
                runtime,
                AgentStateName.CREATE_PLAN,
                runtime.plan_summary or "Safe structured plan created",
            )

            await self._execute_tool(
                session,
                run,
                runtime,
                tenant,
                "document_metadata",
                {"include_counts": True},
                payload,
            )
            reformulation = await self._execute_tool(
                session,
                run,
                runtime,
                tenant,
                "query_reformulation",
                {"query": payload.query, "retry": False},
                payload,
            )
            active_query = reformulation.query or payload.query
            initial_search = await self._execute_tool(
                session,
                run,
                runtime,
                tenant,
                "internal_search",
                {"query": active_query, "top_k": payload.top_k},
                payload,
            )
            initial_evidence = initial_search.evidence
            verifier = await self._execute_tool(
                session,
                run,
                runtime,
                tenant,
                "evidence_verifier",
                {"query": payload.query, "evidence": initial_evidence},
                payload,
            )
            final_evidence = verifier.evidence
            final_sufficient = bool(verifier.sufficient_evidence)
            initial_sufficient = final_sufficient
            retry_performed = False
            retry_strategy: list[str] = []

            retry_candidate = reformulate_query(active_query)
            should_retry = (not final_sufficient) or retry_candidate != active_query
            if should_retry and self.budget.max_retrieval_retries > 0:
                runtime.retrieval_retries += 1
                self.budget.ensure_retrieval_retry(runtime.retrieval_retries)
                AGENT_REPLANS.inc()
                await self._record_state(
                    session,
                    run,
                    runtime,
                    AgentStateName.REPLAN,
                    "Evidence insufficient; retrieval retry requested",
                )
                retry_performed = True
                retry_strategy = ["query_reformulation", "top_k_expansion"]
                retry_query = await self._execute_tool(
                    session,
                    run,
                    runtime,
                    tenant,
                    "query_reformulation",
                    {"query": active_query, "retry": True},
                    payload,
                )
                retry_search = await self._execute_tool(
                    session,
                    run,
                    runtime,
                    tenant,
                    "internal_search",
                    {
                        "query": retry_query.query or active_query,
                        "top_k": min(max(payload.top_k or 0, 12), 50),
                    },
                    payload,
                )
                merged_by_chunk = {item.chunk_id: item for item in final_evidence}
                for item in retry_search.evidence:
                    current = merged_by_chunk.get(item.chunk_id)
                    if current is None or item.score > current.score:
                        merged_by_chunk[item.chunk_id] = item
                final_evidence = sorted(
                    merged_by_chunk.values(), key=lambda item: item.score, reverse=True
                )
                verifier = await self._execute_tool(
                    session,
                    run,
                    runtime,
                    tenant,
                    "evidence_verifier",
                    {"query": payload.query, "evidence": final_evidence},
                    payload,
                )
                final_evidence = verifier.evidence
                final_sufficient = bool(verifier.sufficient_evidence)

            await self._record_state(
                session,
                run,
                runtime,
                AgentStateName.ASSEMBLE_EVIDENCE,
                "Evidence assembled from authorized workspace results",
            )
            await self._record_state(
                session,
                run,
                runtime,
                AgentStateName.VERIFY_EVIDENCE,
                "Final citations verified" if final_sufficient else "Evidence insufficient",
            )
            diagnosis = await self._execute_tool(
                session,
                run,
                runtime,
                tenant,
                "retrieval_diagnosis",
                {
                    "query": payload.query,
                    "initial_evidence": initial_evidence,
                    "final_evidence": final_evidence,
                    "initial_evidence_sufficient": initial_sufficient,
                    "final_evidence_sufficient": final_sufficient,
                    "retry_performed": retry_performed,
                    "retry_strategy": retry_strategy,
                },
                payload,
            )
            runtime.retrieval_diagnosis = diagnosis.metadata.get("retrieval_diagnosis", {})
            runtime.internal_evidence = final_evidence
            runtime.external_access_allowed = payload.allow_external_sources and (
                settings.agent_web_search_enabled or settings.agent_external_apis_enabled
            )
            external_sources = []
            external_status_allows_answer = runtime.retrieval_diagnosis.get("status") not in {
                DiagnosisStatus.AMBIGUOUS_QUERY.value,
                DiagnosisStatus.CONFLICTING_EVIDENCE.value,
            }
            if (
                payload.allow_external_sources
                and not final_sufficient
                and external_status_allows_answer
            ):
                external_result = await self._execute_tool(
                    session,
                    run,
                    runtime,
                    tenant,
                    self._select_external_tool(payload.query),
                    {
                        "query": payload.query,
                        "max_results": settings.web_search_max_results,
                    },
                    payload,
                )
                external_sources = external_result.external_sources
                runtime.external_evidence = external_sources
                runtime.external_sources_used = bool(external_sources)
                runtime.external_access_performed = bool(
                    external_result.metadata.get("external_access_performed")
                )
                provider = external_result.metadata.get("provider")
                if provider and provider not in runtime.providers_used:
                    runtime.providers_used.append(str(provider))
            unified_internal = normalize_internal_evidence(
                final_evidence,
                tenant_id=tenant.organization_id,
                workspace_id=tenant.workspace_id,
            )
            unified_external = normalize_external_sources(external_sources)
            aggregation = aggregate_evidence(
                payload.query,
                [*unified_internal, *unified_external],
            )
            runtime.unified_evidence = [
                item.model_dump(mode="json") for item in aggregation.evidence
            ]
            runtime.evidence_ranking = aggregation.ranking
            runtime.evidence_deduplication = [
                item.model_dump(mode="json") for item in aggregation.deduplication
            ]
            runtime.context_budget = aggregation.context_budget
            synthesized = await self._execute_tool(
                session,
                run,
                runtime,
                tenant,
                "answer_synthesizer",
                {
                    "query": payload.query,
                    "evidence": final_evidence,
                    "external_sources": external_sources,
                    "unified_evidence": runtime.unified_evidence,
                    "sufficient_evidence": final_sufficient or bool(external_sources),
                    "diagnosis": runtime.retrieval_diagnosis,
                },
                payload,
            )
            await self._record_state(
                session, run, runtime, AgentStateName.SYNTHESIZE, synthesized.summary
            )
            reviewed = await self._execute_tool(
                session,
                run,
                runtime,
                tenant,
                "safety_reviewer",
                {
                    "query": payload.query,
                    "answer": synthesized.answer,
                    "evidence": final_evidence,
                    "external_sources": external_sources,
                    "unified_evidence": runtime.unified_evidence,
                    "citations": synthesized.citations,
                },
                payload,
            )
            await self._record_state(
                session,
                run,
                runtime,
                AgentStateName.SAFETY_REVIEW,
                reviewed.summary,
            )
            runtime.answer = reviewed.answer
            runtime.abstained = reviewed.abstained or synthesized.abstained
            runtime.evidence = final_evidence
            runtime.internal_evidence = final_evidence
            runtime.external_evidence = external_sources
            runtime.citations = [] if reviewed.abstained else reviewed.citations
            runtime.claims = synthesized.claims if not reviewed.abstained else []
            runtime.conflicts = synthesized.conflicts
            runtime.unsupported_claims_removed = synthesized.unsupported_claims_removed
            runtime.confidence_category = (
                reviewed.confidence_category
                or synthesized.confidence_category
                or runtime.confidence_category
            )
            runtime.outcome = (
                reviewed.outcome
                or synthesized.outcome
                or map_diagnosis_to_outcome(
                    runtime.retrieval_diagnosis,
                    safety_blocked=False,
                    has_conflict=bool(runtime.conflicts),
                ).value
            )
            if (
                runtime.retrieval_diagnosis.get("status") in TERMINAL_DIAGNOSES
                and not external_sources
            ):
                diagnosis_status = runtime.retrieval_diagnosis.get("status")
                has_supported_claim = any(
                    claim.get("verification_status") == "SUPPORTED" for claim in runtime.claims
                )
                should_preserve_supported_partial = (
                    diagnosis_status == DiagnosisStatus.PARTIAL_EVIDENCE.value
                    and has_supported_claim
                )
                should_preserve_supported_conflict = (
                    diagnosis_status == DiagnosisStatus.CONFLICTING_EVIDENCE.value
                    and has_supported_claim
                    and not runtime.conflicts
                )
                should_preserve_supported = (
                    should_preserve_supported_partial or should_preserve_supported_conflict
                )
                runtime.abstained = not should_preserve_supported
                if (
                    diagnosis_status != DiagnosisStatus.CONFLICTING_EVIDENCE.value
                    and not should_preserve_supported
                ):
                    runtime.outcome = map_diagnosis_to_outcome(
                        runtime.retrieval_diagnosis,
                        safety_blocked=False,
                        has_conflict=False,
                    ).value
                elif (
                    runtime.outcome == AnswerOutcome.ANSWER_SUPPORTED.value
                    and not should_preserve_supported
                ):
                    runtime.outcome = map_diagnosis_to_outcome(
                        runtime.retrieval_diagnosis,
                        safety_blocked=False,
                        has_conflict=bool(runtime.conflicts),
                    ).value
            runtime.total_duration_ms = int((time.perf_counter() - started) * 1000)
            runtime.status = AgentRunStatus.COMPLETED
            runtime.transition(AgentStateName.COMPLETE)
            await self._sync_run(session, run, runtime)
            run.result_json = self._result_json(runtime)
            await self._audit(session, tenant, run.id, request_id, "agent.run.completed")
            await session.commit()
            AGENT_RUNS_COMPLETED.inc()
            AGENT_DURATION.observe(runtime.total_duration_ms / 1000)
            return self._response(run.id, runtime)
        except AgentCancelledError:
            runtime.status = AgentRunStatus.CANCELLED
            runtime.current_state = AgentStateName.CANCELLED
            runtime.total_duration_ms = int((time.perf_counter() - started) * 1000)
            run.status = runtime.status.value
            run.current_state = runtime.current_state.value
            run.error_code = AgentErrorCode.CANCELLED.value
            run.error_message = "Agent run was cancelled"
            run.result_json = self._result_json(runtime)
            await self._audit(session, tenant, run.id, request_id, "agent.run.cancelled")
            await session.commit()
            AGENT_RUNS_FAILED.inc()
            raise
        except TimeoutError as exc:
            return await self._fallback_or_fail(
                session,
                run,
                runtime,
                tenant,
                payload,
                request_id,
                started,
                AgentErrorCode.TIMEOUT.value,
                "Agent tool execution timed out",
                exc,
            )
        except (AgentBudgetError, AgentPolicyError, AgentError) as exc:
            return await self._fallback_or_fail(
                session,
                run,
                runtime,
                tenant,
                payload,
                request_id,
                started,
                exc.code.value,
                exc.message,
                exc,
            )
        except Exception as exc:
            return await self._fallback_or_fail(
                session,
                run,
                runtime,
                tenant,
                payload,
                request_id,
                started,
                AgentErrorCode.INVALID_PLAN.value,
                "Agent tool execution failed safely",
                exc,
            )

    async def _execute_tool(
        self,
        session: AsyncSession,
        run: AgentRun,
        runtime: AgentRuntimeState,
        tenant: TenantContext,
        tool_name: str,
        payload: dict,
        request: AgentQueryRequest,
    ) -> AgentToolResult:
        if runtime.cancelled:
            raise AgentCancelledError()
        self.budget.ensure_time()
        runtime.transition(AgentStateName.SELECT_TOOL)
        await self._sync_run(session, run, runtime)
        await self._record_step(
            session,
            run=run,
            number=len(runtime.safe_step_summaries) + 1,
            state=AgentStateName.SELECT_TOOL,
            summary=f"Tool selected: {tool_name}",
        )
        runtime.safe_step_summaries.append(f"Tool selected: {tool_name}")
        runtime.transition(AgentStateName.EXECUTE_TOOL)
        await self._sync_run(session, run, runtime)
        runtime.tool_calls += 1
        self.budget.ensure_tool_call(runtime.tool_calls)
        tool_call = AgentToolCall(
            run_id=run.id,
            step_id=None,
            workspace_id=tenant.workspace_id,
            tool_name=tool_name,
            status=AgentToolStatus.RUNNING.value,
        )
        session.add(tool_call)
        await session.flush()
        result, duration_ms = await self.executor.execute(
            PlannerStep(tool=tool_name, purpose=f"Execute {tool_name}", required=True),
            payload,
            {
                "session": session,
                "workspace_id": tenant.workspace_id,
                "request_id": runtime.request_id,
                "document_ids": request.document_ids,
                "allow_external_sources": request.allow_external_sources,
            },
        )
        runtime.tools_used.append(tool_name)
        tool_call.status = AgentToolStatus.COMPLETED.value
        tool_call.summary = safe_operational_summary(result.summary)
        tool_call.duration_ms = duration_ms
        await self._record_step(
            session,
            run=run,
            number=len(runtime.safe_step_summaries) + 1,
            state=AgentStateName.EXECUTE_TOOL,
            summary=result.summary,
            duration_ms=duration_ms,
        )
        runtime.safe_step_summaries.append(safe_operational_summary(result.summary))
        return result

    async def _fallback_or_fail(
        self,
        session: AsyncSession,
        run: AgentRun,
        runtime: AgentRuntimeState,
        tenant: TenantContext,
        payload: AgentQueryRequest,
        request_id: str | None,
        started: float,
        code: str,
        message: str,
        exc: Exception,
    ) -> AgentQueryResponse:
        try:
            fallback = await search_and_answer(
                session,
                workspace_id=tenant.workspace_id,
                query=payload.query,
                top_k=payload.top_k,
                document_ids=payload.document_ids,
                request_id=request_id,
            )
            runtime.fallback_used = True
            runtime.answer = fallback.answer
            runtime.abstained = fallback.abstained
            runtime.evidence = fallback.evidence
            runtime.internal_evidence = fallback.evidence
            runtime.retrieval_diagnosis = fallback.retrieval_diagnosis
            runtime.outcome = map_diagnosis_to_outcome(
                runtime.retrieval_diagnosis,
                safety_blocked=False,
            ).value
            runtime.citations = [
                {
                    "index": index,
                    "chunk_id": str(item.chunk_id),
                    "document_id": str(item.document_id),
                    "document_title": item.document_title,
                }
                for index, item in enumerate(fallback.evidence, 1)
            ]
            runtime.total_duration_ms = int((time.perf_counter() - started) * 1000)
            runtime.status = AgentRunStatus.COMPLETED
            runtime.current_state = AgentStateName.COMPLETE
            run.status = runtime.status.value
            run.current_state = runtime.current_state.value
            run.error_code = code
            run.error_message = f"Fallback used: {message}"
            run.result_json = self._result_json(runtime)
            await self._audit(session, tenant, run.id, request_id, "agent.run.fallback")
            await session.commit()
            AGENT_FALLBACKS.inc()
            AGENT_RUNS_COMPLETED.inc()
            return self._response(run.id, runtime)
        except Exception:
            await self._fail(session, run, runtime, code, message)
            AGENT_RUNS_FAILED.inc()
            raise exc from None

    async def _record_state(
        self,
        session: AsyncSession,
        run: AgentRun,
        runtime: AgentRuntimeState,
        state: AgentStateName,
        summary: str,
    ) -> None:
        if runtime.current_state is not state:
            runtime.transition(state)
        await self._sync_run(session, run, runtime)
        await self._record_step(
            session,
            run=run,
            number=len(runtime.safe_step_summaries) + 1,
            state=state,
            summary=summary,
        )
        runtime.safe_step_summaries.append(safe_operational_summary(summary))

    async def _record_step(
        self,
        session: AsyncSession,
        *,
        run: AgentRun,
        number: int,
        state: AgentStateName,
        summary: str,
        duration_ms: int | None = None,
        status: AgentToolStatus = AgentToolStatus.COMPLETED,
        error_code: str | None = None,
    ) -> AgentStep:
        safe_summary = safe_operational_summary(summary)
        step = AgentStep(
            run_id=run.id,
            workspace_id=run.workspace_id,
            step_number=number,
            state=state.value,
            summary=safe_summary,
            status=status.value,
            duration_ms=duration_ms,
            error_code=error_code,
        )
        session.add(step)
        await session.flush()
        return step

    async def _sync_run(
        self, session: AsyncSession, run: AgentRun, runtime: AgentRuntimeState
    ) -> None:
        run.status = runtime.status.value
        run.current_state = runtime.current_state.value
        run.safe_plan_summary = runtime.plan_summary
        await session.flush()

    async def _fail(
        self,
        session: AsyncSession,
        run: AgentRun,
        runtime: AgentRuntimeState,
        code: str,
        message: str,
    ) -> None:
        runtime.status = AgentRunStatus.FAILED
        runtime.current_state = AgentStateName.FAILED
        run.status = runtime.status.value
        run.current_state = runtime.current_state.value
        run.error_code = code
        run.error_message = message
        run.result_json = {"summary": "Agent run failed safely", "fallback_used": False}
        await session.commit()

    async def _audit(
        self,
        session: AsyncSession,
        tenant: TenantContext,
        run_id: UUID,
        request_id: str | None,
        action: str,
    ) -> None:
        session.add(
            AuditEvent(
                workspace_id=tenant.workspace_id,
                actor_user_id=tenant.user_id,
                action=action,
                resource_type="agent_run",
                resource_id=str(run_id),
                request_id=request_id,
                ip_hash=None,
                details_json={"summary": action.replace(".", " ")},
            )
        )
        await session.flush()

    def _result_json(self, runtime: AgentRuntimeState) -> dict:
        response_state = response_state_from_legacy(
            answer=runtime.answer,
            outcome=runtime.outcome,
            citations=runtime.citations,
            claims=runtime.claims,
            conflicts=runtime.conflicts,
            confidence_category=runtime.confidence_category,
            retrieval_diagnosis=runtime.retrieval_diagnosis,
            fallback_used=runtime.fallback_used,
            status=runtime.status.value,
        )
        compatible = legacy_fields(response_state)
        return {
            "summary": (
                "Agent run completed"
                if runtime.status == AgentRunStatus.COMPLETED
                else "Agent run failed safely"
            ),
            "answer": compatible["answer"],
            "abstained": compatible["abstained"],
            "citations": runtime.citations,
            "evidence_count": len(runtime.evidence),
            "internal_evidence_count": len(runtime.internal_evidence),
            "external_evidence_count": len(runtime.external_evidence),
            "tools_used": runtime.tools_used,
            "safe_step_summaries": runtime.safe_step_summaries,
            "tool_calls": runtime.tool_calls,
            "fallback_used": runtime.fallback_used,
            "total_duration_ms": runtime.total_duration_ms,
            "retrieval_diagnosis": runtime.retrieval_diagnosis,
            "external_sources_used": runtime.external_sources_used,
            "providers_used": runtime.providers_used,
            "external_access_allowed": runtime.external_access_allowed,
            "external_access_performed": runtime.external_access_performed,
            "outcome": compatible["outcome"],
            "claims": runtime.claims,
            "conflicts": runtime.conflicts,
            "unsupported_claims_removed": runtime.unsupported_claims_removed,
            "confidence_category": compatible["confidence_category"],
            "response_state": response_state.model_dump(mode="json"),
            "unified_evidence": runtime.unified_evidence,
            "evidence_ranking": runtime.evidence_ranking,
            "evidence_deduplication": runtime.evidence_deduplication,
            "context_budget": runtime.context_budget,
        }

    def _response(self, run_id: UUID, runtime: AgentRuntimeState) -> AgentQueryResponse:
        return AgentQueryResponse(
            run_id=run_id,
            status=runtime.status,
            current_state=runtime.current_state,
            answer=runtime.answer,
            abstained=runtime.abstained,
            citations=runtime.citations,
            evidence=runtime.evidence,
            internal_evidence=runtime.internal_evidence,
            external_evidence=runtime.external_evidence,
            external_sources_used=runtime.external_sources_used,
            providers_used=runtime.providers_used,
            external_access_allowed=runtime.external_access_allowed,
            external_access_performed=runtime.external_access_performed,
            tools_used=runtime.tools_used,
            safe_step_summaries=runtime.safe_step_summaries,
            safe_plan_summary=runtime.plan_summary,
            total_duration_ms=runtime.total_duration_ms,
            fallback_used=runtime.fallback_used,
            request_id=runtime.request_id,
            retrieval_diagnosis=runtime.retrieval_diagnosis,
            outcome=runtime.outcome,
            claims=runtime.claims,
            conflicts=runtime.conflicts,
            unsupported_claims_removed=runtime.unsupported_claims_removed,
            confidence_category=runtime.confidence_category,
            unified_evidence=runtime.unified_evidence,
            evidence_ranking=runtime.evidence_ranking,
            evidence_deduplication=runtime.evidence_deduplication,
            context_budget=runtime.context_budget,
        )

    def _select_external_tool(self, query: str) -> str:
        normalized = query.lower()
        if settings.agent_external_apis_enabled and "wikipedia" in normalized:
            return "wikipedia_lookup"
        if settings.agent_external_apis_enabled and (
            "arxiv" in normalized or "paper" in normalized or "research" in normalized
        ):
            return "arxiv_search"
        return "web_search"


async def read_agent_run(
    session: AsyncSession, *, workspace_id: UUID, run_id: UUID
) -> AgentRunRead | None:
    run = await session.get(AgentRun, run_id)
    if not run or run.workspace_id != workspace_id:
        return None
    steps = (
        await session.scalars(
            select(AgentStep).where(AgentStep.run_id == run_id).order_by(AgentStep.step_number)
        )
    ).all()
    tool_calls = (
        await session.scalars(
            select(AgentToolCall)
            .where(AgentToolCall.run_id == run_id)
            .order_by(AgentToolCall.created_at)
        )
    ).all()
    return AgentRunRead.model_validate(
        {
            **run.__dict__,
            "steps": list(steps),
            "tool_calls": list(tool_calls),
        }
    )
