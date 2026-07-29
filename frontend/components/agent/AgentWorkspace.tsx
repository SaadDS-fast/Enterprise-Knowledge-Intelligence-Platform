"use client";

import Link from "next/link";
import type { FormEvent } from "react";
import { useCallback, useEffect, useState } from "react";

import { api } from "@/lib/api";
import { frontendConfig } from "@/lib/config";
import { getWorkspaceId } from "@/lib/auth";
import type { AgentQueryResponse, AgentRunDetail, DocumentItem } from "@/types";

import CitationList from "./CitationList";
import ClaimStatus from "./ClaimStatus";
import ConfidenceIndicator from "./ConfidenceIndicator";
import ConflictCard from "./ConflictCard";
import { ExternalEvidenceCard, InternalEvidenceCard } from "./EvidenceCard";
import OutcomeBadge from "./OutcomeBadge";
import RetrievalDiagnosisView from "./RetrievalDiagnosisView";

const recentRunsKey = "ekip_recent_agent_runs";

function saveRecentRun(runId: string): void {
  const current = readRecentRunIds();
  localStorage.setItem(
    recentRunsKey,
    JSON.stringify([runId, ...current.filter((item) => item !== runId)].slice(0, 8)),
  );
}

function readRecentRunIds(): string[] {
  if (typeof window === "undefined") return [];
  try {
    const parsed = JSON.parse(localStorage.getItem(recentRunsKey) ?? "[]");
    return Array.isArray(parsed) ? parsed.filter((item): item is string => typeof item === "string") : [];
  } catch {
    return [];
  }
}

export default function AgentWorkspace() {
  const [query, setQuery] = useState("");
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [documentIds, setDocumentIds] = useState<string[]>([]);
  const [allowExternal, setAllowExternal] = useState(false);
  const [result, setResult] = useState<AgentQueryResponse | null>(null);
  const [recentRuns, setRecentRuns] = useState<AgentRunDetail[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const workspaceId = getWorkspaceId();

  const loadRecentRuns = useCallback(async () => {
    const runIds = readRecentRunIds();
    const loaded: AgentRunDetail[] = [];
    for (const runId of runIds) {
      try {
        loaded.push(await api<AgentRunDetail>(`/agent/runs/${runId}`));
      } catch {
        // Missing or unauthorized old local run links are ignored.
      }
    }
    setRecentRuns(loaded);
  }, []);

  useEffect(() => {
    async function loadDocuments() {
      try {
        setDocuments(await api<DocumentItem[]>("/documents"));
      } catch (caught) {
        setError(caught instanceof Error ? caught.message : "Failed to load documents");
      }
    }
    if (frontendConfig.agenticRagEnabled) void loadDocuments();
    void loadRecentRuns();
  }, [loadRecentRuns]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError("");
    setResult(null);
    try {
      const response = await api<AgentQueryResponse>("/agent/query", {
        method: "POST",
        body: JSON.stringify({
          query,
          document_ids: documentIds.length ? documentIds : null,
          allow_external_sources: frontendConfig.externalSourcesEnabled && allowExternal,
        }),
      });
      setResult(response);
      saveRecentRun(response.run_id);
      await loadRecentRuns();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Agent request failed");
    } finally {
      setLoading(false);
    }
  }

  if (!frontendConfig.agenticRagEnabled) {
    return (
      <section className="result" data-testid="agent-disabled">
        <h2>Agent workspace disabled</h2>
        <p className="muted">
          Controlled agent querying is hidden by default. Backend authorization and feature flags
          remain authoritative if this page is enabled.
        </p>
      </section>
    );
  }

  return (
    <div className="agent-grid">
      <section className="workspace-panel">
        <form className="agent-form" onSubmit={submit} data-testid="agent-form">
          <div>
            <h2>Ask controlled agent</h2>
            <p className="muted">
              Workspace: <span className="wrap">{workspaceId ?? "not selected"}</span>
            </p>
          </div>
          <label htmlFor="agent-question">Question</label>
          <textarea
            id="agent-question"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Ask a question grounded in authorized workspace documents..."
            minLength={2}
            required
            data-testid="agent-query"
          />
          <fieldset>
            <legend>Authorized document scope</legend>
            <p className="muted">Leave empty to use all authorized ready documents.</p>
            <div className="check-list">
              {documents.map((document) => (
                <label key={document.id}>
                  <input
                    type="checkbox"
                    value={document.id}
                    checked={documentIds.includes(document.id)}
                    onChange={(event) => {
                      setDocumentIds((current) =>
                        event.target.checked
                          ? [...current, document.id]
                          : current.filter((item) => item !== document.id),
                      );
                    }}
                  />
                  <span>{document.title}</span>
                </label>
              ))}
            </div>
          </fieldset>
          <div className="scope-summary" aria-live="polite">
            Internal documents only
            {documentIds.length ? ` · ${documentIds.length} selected` : " · all authorized"}
          </div>
          {frontendConfig.externalSourcesEnabled ? (
            <label className="toggle-row">
              <input
                type="checkbox"
                checked={allowExternal}
                onChange={(event) => setAllowExternal(event.target.checked)}
                data-testid="agent-external-toggle"
              />
              <span>
                Allow approved public providers for this request. External content is untrusted and
                verified before use.
              </span>
            </label>
          ) : null}
          {error ? <p className="error" role="alert">{error}</p> : null}
          <button disabled={loading || !workspaceId} data-testid="agent-submit">
            {loading ? "Running..." : "Run controlled query"}
          </button>
        </form>
      </section>
      <aside className="workspace-panel">
        <h2>Recent safe runs</h2>
        <div className="cards">
          {recentRuns.map((run) => (
            <article className="card compact" key={run.id}>
              <header>
                <strong>{run.input_query}</strong>
                <span className={`badge badge-${run.status.toLowerCase()}`}>{run.status}</span>
              </header>
              <Link href={`/agent/runs/${run.id}`}>Open run detail</Link>
            </article>
          ))}
          {!recentRuns.length ? <div className="empty">No recent local run links.</div> : null}
        </div>
      </aside>
      {result ? (
        <section className="result agent-result" data-testid="agent-result">
          <div className="result-header">
            <h2>Agent result</h2>
            <OutcomeBadge value={result.response_state?.primary_state ?? result.outcome} />
          </div>
          <div className="meta-row">
            <ConfidenceIndicator
              value={
                result.response_state?.confidence.final.toLowerCase() ??
                result.confidence_category
              }
            />
            <span>{result.total_duration_ms ?? 0} ms</span>
            <span>{result.fallback_used ? "Fallback used" : "No fallback"}</span>
            <Link href={`/agent/runs/${result.run_id}`}>Execution timeline</Link>
          </div>
          <h3>Answer</h3>
          <p className="answer">{result.answer ?? "No supported answer was produced."}</p>
          <h3>Retrieval diagnosis</h3>
          <RetrievalDiagnosisView diagnosis={result.retrieval_diagnosis} />
          <h3>Citations</h3>
          <CitationList citations={result.citations} />
          <h3>Internal evidence</h3>
          <div className="evidence-list">
            {result.internal_evidence.map((item, index) => (
              <InternalEvidenceCard item={item} index={index} key={item.chunk_id} />
            ))}
            {!result.internal_evidence.length ? <div className="empty">No internal evidence.</div> : null}
          </div>
          <h3>External evidence</h3>
          <div className="evidence-list">
            {result.external_evidence.map((item, index) => (
              <ExternalEvidenceCard item={item} index={index} key={item.source_id} />
            ))}
            {!result.external_evidence.length ? <div className="empty">No external evidence.</div> : null}
          </div>
          <h3>Conflicts</h3>
          <div className="evidence-list">
            {result.conflicts.map((conflict, index) => (
              <ConflictCard conflict={conflict} key={`${conflict.summary ?? "conflict"}-${index}`} />
            ))}
            {!result.conflicts.length ? <div className="empty">No conflicts detected.</div> : null}
          </div>
          {result.response_state?.conflict.sides.length ? (
            <div className="evidence-list" data-testid="agent-conflict-sides">
              {result.response_state.conflict.sides.map((side) => (
                <article className="evidence warning-card" key={side.claim_id}>
                  <strong>{side.text}</strong>
                  <small>Citations: {side.citation_ids.join(", ")}</small>
                </article>
              ))}
            </div>
          ) : null}
          <h3>Claim verification</h3>
          <ClaimStatus claims={result.claims} />
          <h3>Tools used</h3>
          <div className="tool-list">
            {result.tools_used.map((tool) => (
              <span key={tool}>{tool.replaceAll("_", " ")}</span>
            ))}
          </div>
        </section>
      ) : null}
    </div>
  );
}
