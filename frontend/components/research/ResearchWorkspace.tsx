"use client";

import Link from "next/link";
import type { FormEvent } from "react";
import { useCallback, useEffect, useState } from "react";

import { api } from "@/lib/api";
import { frontendConfig } from "@/lib/config";
import { getWorkspaceId } from "@/lib/auth";
import { isTerminalStatus } from "@/lib/safe-url";
import type {
  DocumentItem,
  ResearchCreateResponse,
  ResearchFormat,
  ResearchJob,
} from "@/types";

import StatusBadge from "@/components/ui/StatusBadge";

const formats: Array<{ value: ResearchFormat; label: string }> = [
  { value: "markdown", label: "Markdown" },
  { value: "pdf", label: "PDF" },
  { value: "docx", label: "DOCX" },
];

export default function ResearchWorkspace() {
  const [question, setQuestion] = useState("");
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [documentIds, setDocumentIds] = useState<string[]>([]);
  const [requestedFormats, setRequestedFormats] = useState<ResearchFormat[]>(["markdown"]);
  const [allowExternal, setAllowExternal] = useState(false);
  const [depth, setDepth] = useState("standard");
  const [jobs, setJobs] = useState<ResearchJob[]>([]);
  const [filter, setFilter] = useState("all");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [accepted, setAccepted] = useState<ResearchCreateResponse | null>(null);
  const workspaceId = getWorkspaceId();

  const load = useCallback(async () => {
    try {
      const [jobRows, documentRows] = await Promise.all([
        api<ResearchJob[]>("/agent/research"),
        api<DocumentItem[]>("/documents"),
      ]);
      setJobs(jobRows);
      setDocuments(documentRows);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Failed to load research workspace");
    }
  }, []);

  useEffect(() => {
    if (frontendConfig.agenticResearchEnabled) void load();
  }, [load]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError("");
    setAccepted(null);
    try {
      const response = await api<ResearchCreateResponse>("/agent/research", {
        method: "POST",
        body: JSON.stringify({
          question,
          document_ids: documentIds.length ? documentIds : null,
          allow_external_sources: frontendConfig.externalSourcesEnabled && allowExternal,
          requested_formats: requestedFormats,
          max_depth_preset: depth,
        }),
      });
      setAccepted(response);
      setQuestion("");
      await load();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Research request failed");
    } finally {
      setLoading(false);
    }
  }

  if (!frontendConfig.agenticResearchEnabled) {
    return (
      <section className="result" data-testid="research-disabled">
        <h2>Research reports disabled</h2>
        <p className="muted">
          Asynchronous agentic reports are hidden by default. Backend authorization and feature
          flags remain authoritative if this page is enabled.
        </p>
      </section>
    );
  }

  const visibleJobs =
    filter === "all" ? jobs : jobs.filter((job) => (job.status ?? "").toLowerCase() === filter);

  return (
    <div className="agent-grid">
      <section className="workspace-panel">
        <form className="agent-form" onSubmit={submit} data-testid="research-form">
          <div>
            <h2>Create cited report</h2>
            <p className="muted">
              Workspace: <span className="wrap">{workspaceId ?? "not selected"}</span>
            </p>
          </div>
          <label htmlFor="research-question">Research question</label>
          <textarea
            id="research-question"
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            placeholder="Describe the report you need from authorized documents..."
            minLength={5}
            required
            data-testid="research-question"
          />
          <fieldset>
            <legend>Authorized document scope</legend>
            <p className="muted">Leave empty to use all authorized ready documents.</p>
            <div className="check-list">
              {documents.map((document) => (
                <label key={document.id}>
                  <input
                    type="checkbox"
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
          <label htmlFor="depth-preset">Report depth</label>
          <select id="depth-preset" value={depth} onChange={(event) => setDepth(event.target.value)}>
            <option value="standard">Standard</option>
            <option value="brief">Brief</option>
            <option value="deep">Deep</option>
          </select>
          <fieldset>
            <legend>Output formats</legend>
            <div className="check-list horizontal">
              {formats.map((format) => (
                <label key={format.value}>
                  <input
                    type="checkbox"
                    checked={requestedFormats.includes(format.value)}
                    onChange={(event) => {
                      setRequestedFormats((current) => {
                        const next = event.target.checked
                          ? [...current, format.value]
                          : current.filter((item) => item !== format.value);
                        return next.length ? next : ["markdown"];
                      });
                    }}
                  />
                  <span>{format.label}</span>
                </label>
              ))}
            </div>
          </fieldset>
          <div className="scope-summary" aria-live="polite">
            Internal documents only · {documentIds.length ? `${documentIds.length} selected` : "all authorized"}
          </div>
          {frontendConfig.externalSourcesEnabled ? (
            <label className="toggle-row">
              <input
                type="checkbox"
                checked={allowExternal}
                onChange={(event) => setAllowExternal(event.target.checked)}
                data-testid="research-external-toggle"
              />
              <span>
                Allow approved public providers for this report. External content is untrusted and
                verified before use.
              </span>
            </label>
          ) : null}
          {error ? <p className="error" role="alert">{error}</p> : null}
          {accepted ? (
            <p className="success" role="status">
              Report accepted. <Link href={`/agent/research/${accepted.job_id}`}>Open job</Link>
            </p>
          ) : null}
          <button disabled={loading || !workspaceId} data-testid="research-submit">
            {loading ? "Submitting..." : "Submit research job"}
          </button>
        </form>
      </section>
      <section className="workspace-panel">
        <div className="result-header">
          <h2>Recent research jobs</h2>
          <select aria-label="Research status filter" value={filter} onChange={(event) => setFilter(event.target.value)}>
            <option value="all">All</option>
            <option value="pending">Pending</option>
            <option value="running">Running</option>
            <option value="completed">Completed</option>
            <option value="failed">Failed</option>
            <option value="cancelled">Cancelled</option>
          </select>
        </div>
        <div className="cards">
          {visibleJobs.map((job) => (
            <article className="card compact" key={job.id}>
              <header>
                <strong>{job.question}</strong>
                <StatusBadge value={job.status} />
              </header>
              <p className="muted">
                {job.stage ?? "queued"} · {isTerminalStatus(job.status) ? "terminal" : "active"}
              </p>
              <Link href={`/agent/research/${job.id}`}>Open report job</Link>
            </article>
          ))}
          {!visibleJobs.length ? <div className="empty">No research jobs for this filter.</div> : null}
        </div>
      </section>
    </div>
  );
}
