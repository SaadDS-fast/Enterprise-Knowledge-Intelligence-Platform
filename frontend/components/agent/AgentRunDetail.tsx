"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { api } from "@/lib/api";
import { frontendConfig } from "@/lib/config";
import type {
  AgentRunDetail as AgentRunDetailType,
  CanonicalResponseState,
} from "@/types";

import CitationList from "./CitationList";
import ClaimStatus from "./ClaimStatus";
import ExecutionTimeline from "./ExecutionTimeline";
import OutcomeBadge from "./OutcomeBadge";
import RetrievalDiagnosisView from "./RetrievalDiagnosisView";

export default function AgentRunDetail({ runId }: { runId: string }) {
  const [run, setRun] = useState<AgentRunDetailType | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    const controller = new AbortController();
    async function load() {
      try {
        setRun(await api<AgentRunDetailType>(`/agent/runs/${runId}`, { signal: controller.signal }));
      } catch (caught) {
        if (!controller.signal.aborted) {
          setError(caught instanceof Error ? caught.message : "Run not found");
        }
      }
    }
    if (frontendConfig.agenticRagEnabled) void load();
    return () => controller.abort();
  }, [runId]);

  if (!frontendConfig.agenticRagEnabled) {
    return <div className="result">Agent run details are disabled in this frontend build.</div>;
  }

  if (error) return <p className="error" role="alert">{error}</p>;
  if (!run) return <div className="empty">Loading run detail...</div>;
  const result = run.result_json;
  const responseState = result.response_state as CanonicalResponseState | undefined;
  const citations = Array.isArray(result.citations) ? result.citations : [];
  const claims = Array.isArray(result.claims) ? result.claims : [];
  const tools = Array.isArray(result.tools_used) ? result.tools_used : [];
  const summaries = String(run.safe_plan_summary ?? "")
    .split(";")
    .map((item) => item.trim())
    .filter(Boolean);

  return (
    <section className="result" data-testid="agent-run-detail">
      <div className="result-header">
        <h2>Result summary</h2>
        <span className={`badge badge-${run.status.toLowerCase()}`}>{run.status}</span>
      </div>
      <p className="answer">{run.input_query}</p>
      <div className="meta-row">
        <span>Workflow status: {run.status}</span>
        <OutcomeBadge value={responseState?.primary_state ?? String(result.outcome ?? "INSUFFICIENT_EVIDENCE")} />
        <span>Confidence: {responseState?.confidence.final.toLowerCase() ?? String(result.confidence_category ?? "none")}</span>
        <span>{String(result.total_duration_ms ?? 0)} ms</span>
      </div>
      <h3>Final answer</h3>
      <p className="answer">{String(result.answer ?? "No supported answer was produced.")}</p>
      {result.abstained ? <p className="muted">Abstained: yes</p> : <p className="muted">Abstained: no</p>}
      <h3>Citations</h3>
      <CitationList citations={citations} />
      <h3>Retrieval diagnosis</h3>
      <RetrievalDiagnosisView diagnosis={result.retrieval_diagnosis as Record<string, unknown>} />
      <h3>Claim verification</h3>
      <ClaimStatus claims={claims} />
      <h3>Tools used</h3>
      <div className="tool-list">
        {tools.map((tool) => (
          <span key={String(tool)}>{String(tool).replaceAll("_", " ")}</span>
        ))}
      </div>
      {summaries.length ? (
        <>
          <h3>Plan summary</h3>
          <div className="tool-list">
            {summaries.map((summary) => (
              <span key={summary}>{summary}</span>
            ))}
          </div>
        </>
      ) : null}
      {run.error_message ? <p className="error">{run.error_message}</p> : null}
      <h2>Processing stages</h2>
      <ExecutionTimeline run={run} />
      <Link className="button secondary" href="/agent">
        Back to agent workspace
      </Link>
    </section>
  );
}
