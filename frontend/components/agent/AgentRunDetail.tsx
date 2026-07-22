"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { api } from "@/lib/api";
import { frontendConfig } from "@/lib/config";
import type { AgentRunDetail as AgentRunDetailType } from "@/types";

import ExecutionTimeline from "./ExecutionTimeline";

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

  return (
    <section className="result" data-testid="agent-run-detail">
      <div className="result-header">
        <h2>Processing stages</h2>
        <span className={`badge badge-${run.status.toLowerCase()}`}>{run.status}</span>
      </div>
      <p className="answer">{run.input_query}</p>
      {run.safe_plan_summary ? <p className="muted">{run.safe_plan_summary}</p> : null}
      {run.error_message ? <p className="error">{run.error_message}</p> : null}
      <ExecutionTimeline run={run} />
      <Link className="button secondary" href="/agent">
        Back to agent workspace
      </Link>
    </section>
  );
}
