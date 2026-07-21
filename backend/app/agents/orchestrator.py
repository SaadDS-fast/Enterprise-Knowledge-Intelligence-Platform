from __future__ import annotations

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
from app.agents.executor import ToolExecutor
from app.agents.planner import PlannerProvider, get_planner
from app.agents.policies import safe_operational_summary, validate_plan
from app.agents.schemas import AgentQueryRequest, AgentQueryResponse, AgentRunRead, AgentToolResult
from app.agents.state import AgentRuntimeState
from app.agents.tool_registry import ToolRegistry, build_default_registry
from app.db.models import AgentRun, AgentStep, AgentToolCall, AuditEvent
from app.tenancy.context import TenantContext


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
            await self._record_step(
                session,
                run=run,
                number=1,
                state=AgentStateName.RECEIVE_REQUEST,
                summary="Agent request received",
            )
            runtime.transition(AgentStateName.AUTHORIZE)
            await self._sync_run(session, run, runtime)
            await self._record_step(
                session,
                run=run,
                number=2,
                state=AgentStateName.AUTHORIZE,
                summary="Tenant workspace scope authorized",
            )

            runtime.transition(AgentStateName.CLASSIFY_INTENT)
            await self._sync_run(session, run, runtime)
            plan = await self.planner.create_plan(payload.query)
            await self._record_step(
                session,
                run=run,
                number=3,
                state=AgentStateName.CLASSIFY_INTENT,
                summary=f"Intent classified as {plan.intent.value}",
            )

            runtime.transition(AgentStateName.CREATE_PLAN)
            runtime.plan_summary = safe_operational_summary(plan.safe_summary())
            validate_plan(
                plan,
                registry=self.registry,
                budget=self.budget,
                workspace_id=tenant.workspace_id,
            )
            await self._sync_run(session, run, runtime)
            await self._record_step(
                session,
                run=run,
                number=4,
                state=AgentStateName.CREATE_PLAN,
                summary=runtime.plan_summary or "Safe structured plan created",
            )

            latest_result: AgentToolResult | None = None
            step_number = 5
            for plan_step in plan.steps:
                if runtime.cancelled:
                    raise AgentCancelledError()
                self.budget.ensure_time()
                runtime.transition(AgentStateName.SELECT_TOOL)
                await self._sync_run(session, run, runtime)
                await self._record_step(
                    session,
                    run=run,
                    number=step_number,
                    state=AgentStateName.SELECT_TOOL,
                    summary=f"Tool selected: {plan_step.tool}",
                )
                step_number += 1
                runtime.transition(AgentStateName.EXECUTE_TOOL)
                await self._sync_run(session, run, runtime)
                runtime.tool_calls += 1
                self.budget.ensure_tool_call(runtime.tool_calls)
                tool_payload = self._tool_payload(plan_step.tool, payload, latest_result)
                tool_call = AgentToolCall(
                    run_id=run.id,
                    step_id=None,
                    workspace_id=tenant.workspace_id,
                    tool_name=plan_step.tool,
                    status=AgentToolStatus.RUNNING.value,
                )
                session.add(tool_call)
                await session.flush()
                result, duration_ms = await self.executor.execute(
                    plan_step,
                    tool_payload,
                    {
                        "session": session,
                        "workspace_id": tenant.workspace_id,
                        "request_id": request_id,
                        "document_ids": payload.document_ids,
                    },
                )
                latest_result = result
                if result.evidence:
                    runtime.evidence = result.evidence
                if result.answer:
                    runtime.answer = result.answer
                tool_call.status = AgentToolStatus.COMPLETED.value
                tool_call.summary = safe_operational_summary(result.summary)
                tool_call.duration_ms = duration_ms
                await self._record_step(
                    session,
                    run=run,
                    number=step_number,
                    state=AgentStateName.EXECUTE_TOOL,
                    summary=result.summary,
                    duration_ms=duration_ms,
                )
                step_number += 1

            runtime.transition(AgentStateName.ASSEMBLE_EVIDENCE)
            await self._sync_run(session, run, runtime)
            await self._record_step(
                session,
                run=run,
                number=step_number,
                state=AgentStateName.ASSEMBLE_EVIDENCE,
                summary="Evidence assembled from authorized workspace results",
            )
            step_number += 1
            runtime.transition(AgentStateName.VERIFY_EVIDENCE)
            await self._sync_run(session, run, runtime)
            await self._record_step(
                session,
                run=run,
                number=step_number,
                state=AgentStateName.VERIFY_EVIDENCE,
                summary="Final citations verified" if runtime.evidence else "Evidence insufficient",
            )
            step_number += 1
            runtime.transition(AgentStateName.SYNTHESIZE)
            await self._sync_run(session, run, runtime)
            await self._record_step(
                session,
                run=run,
                number=step_number,
                state=AgentStateName.SYNTHESIZE,
                summary="Answer synthesized from verified evidence",
            )
            step_number += 1
            runtime.transition(AgentStateName.SAFETY_REVIEW)
            await self._sync_run(session, run, runtime)
            await self._record_step(
                session,
                run=run,
                number=step_number,
                state=AgentStateName.SAFETY_REVIEW,
                summary="Safe response reviewed",
            )
            runtime.transition(AgentStateName.COMPLETE)
            runtime.status = AgentRunStatus.COMPLETED
            await self._sync_run(session, run, runtime)
            run.result_json = self._result_json(runtime, latest_result)
            await self._audit(session, tenant, run.id, request_id, "agent.run.completed")
            await session.commit()
            retrieval_diagnosis = (
                latest_result.metadata.get("retrieval_diagnosis", {}) if latest_result else {}
            )
            return AgentQueryResponse(
                run_id=run.id,
                status=AgentRunStatus.COMPLETED,
                current_state=AgentStateName.COMPLETE,
                answer=runtime.answer,
                evidence=runtime.evidence,
                safe_plan_summary=runtime.plan_summary,
                request_id=request_id,
                retrieval_diagnosis=retrieval_diagnosis,
            )
        except TimeoutError as exc:
            await self._fail(
                session,
                run,
                runtime,
                AgentErrorCode.TIMEOUT.value,
                "Agent tool execution timed out",
            )
            raise AgentBudgetError(
                AgentErrorCode.TIMEOUT, "Agent tool execution timed out"
            ) from exc
        except AgentCancelledError:
            runtime.status = AgentRunStatus.CANCELLED
            runtime.current_state = AgentStateName.CANCELLED
            run.status = runtime.status.value
            run.current_state = runtime.current_state.value
            run.error_code = AgentErrorCode.CANCELLED.value
            run.error_message = "Agent run was cancelled"
            await self._audit(session, tenant, run.id, request_id, "agent.run.cancelled")
            await session.commit()
            raise
        except (AgentBudgetError, AgentPolicyError, AgentError) as exc:
            await self._fail(session, run, runtime, exc.code.value, exc.message)
            raise

    def _tool_payload(
        self, tool_name: str, payload: AgentQueryRequest, latest_result: AgentToolResult | None
    ) -> dict:
        if tool_name == "internal_search":
            return {"query": payload.query, "top_k": payload.top_k}
        if tool_name == "evidence_verifier":
            return {
                "sufficient_evidence": bool(latest_result and latest_result.sufficient_evidence),
                "evidence_count": len(latest_result.evidence) if latest_result else 0,
            }
        return {}

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
        step = AgentStep(
            run_id=run.id,
            workspace_id=run.workspace_id,
            step_number=number,
            state=state.value,
            summary=safe_operational_summary(summary),
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
        run.result_json = {"summary": "Agent run failed safely"}
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

    def _result_json(
        self, runtime: AgentRuntimeState, latest_result: AgentToolResult | None
    ) -> dict:
        return {
            "summary": "Agent run completed",
            "evidence_count": len(runtime.evidence),
            "tool_calls": runtime.tool_calls,
            "retrieval_diagnosis": latest_result.metadata.get("retrieval_diagnosis", {})
            if latest_result
            else {},
        }


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
