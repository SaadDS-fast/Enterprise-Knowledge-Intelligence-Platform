"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";

import { api, APIError, apiBlob } from "@/lib/api";
import { boundedPollInterval, frontendConfig } from "@/lib/config";
import { isCancellableResearchState, isTerminalStatus } from "@/lib/safe-url";
import type { ResearchArtifact, ResearchJob } from "@/types";

import StatusBadge from "@/components/ui/StatusBadge";

const stateLabels: Record<string, string> = {
  PENDING: "Pending",
  AUTHORIZING: "Authorizing",
  PLANNING: "Planning",
  RETRIEVING: "Retrieving",
  RETRIEVAL_RETRY: "Retrieval retry",
  AGGREGATING_EVIDENCE: "Aggregating evidence",
  VERIFYING_EVIDENCE: "Verifying evidence",
  WRITING: "Writing",
  VERIFYING_CITATIONS: "Verifying citations",
  SAFETY_REVIEW: "Safety review",
  EXPORTING: "Exporting",
  COMPLETED: "Completed",
  FAILED: "Failed",
  CANCEL_REQUESTED: "Cancellation requested",
  CANCELLED: "Cancelled",
};

function reportSummary(job: ResearchJob): string | null {
  const report = job.result_json.report;
  if (typeof report === "object" && report && "executive_summary" in report) {
    const summary = (report as { executive_summary?: unknown }).executive_summary;
    return typeof summary === "string" ? summary : null;
  }
  return job.report_markdown ? job.report_markdown.slice(0, 800) : null;
}

export default function ResearchJobDetail({ jobId }: { jobId: string }) {
  const [job, setJob] = useState<ResearchJob | null>(null);
  const [artifacts, setArtifacts] = useState<ResearchArtifact[]>([]);
  const [error, setError] = useState("");
  const [pollError, setPollError] = useState("");
  const [cancelling, setCancelling] = useState(false);
  const [downloading, setDownloading] = useState("");
  const inFlight = useRef(false);

  const load = useCallback(async () => {
    if (inFlight.current) return;
    inFlight.current = true;
    try {
      const detail = await api<ResearchJob>(`/agent/research/${jobId}`);
      setJob(detail);
      setPollError("");
      if (detail.status === "completed") {
        setArtifacts(await api<ResearchArtifact[]>(`/agent/research/${jobId}/artifacts`));
      }
    } catch (caught) {
      const message = caught instanceof Error ? caught.message : "Failed to load research job";
      if (!job) setError(message);
      setPollError(message);
    } finally {
      inFlight.current = false;
    }
  }, [job, jobId]);

  useEffect(() => {
    if (!frontendConfig.agenticResearchEnabled) return undefined;
    let stopped = false;
    let timeout: ReturnType<typeof setTimeout> | undefined;
    async function tick(delay: number) {
      await load();
      if (stopped) return;
      const terminal = isTerminalStatus(job?.status);
      const hidden = typeof document !== "undefined" && document.visibilityState === "hidden";
      if (!terminal) {
        timeout = setTimeout(() => void tick(Math.min(delay * (pollError ? 2 : 1), 10000)), hidden ? delay * 2 : delay);
      }
    }
    void tick(boundedPollInterval());
    return () => {
      stopped = true;
      if (timeout) clearTimeout(timeout);
    };
  }, [load, pollError, job?.status]);

  async function cancel() {
    if (!job || !isCancellableResearchState(job.current_state)) return;
    const confirmed = window.confirm("Request cancellation? Completed jobs cannot be cancelled.");
    if (!confirmed) return;
    setCancelling(true);
    setError("");
    try {
      setJob(await api<ResearchJob>(`/agent/research/${job.id}/cancel`, { method: "POST" }));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Cancellation failed");
    } finally {
      setCancelling(false);
    }
  }

  async function download(artifact: ResearchArtifact) {
    if (!artifact.download_url) return;
    setDownloading(artifact.format);
    setError("");
    try {
      const freshDownload = async () => {
        const fresh = await api<ResearchArtifact[]>(`/agent/research/${jobId}/artifacts`);
        setArtifacts(fresh);
        const replacement = fresh.find((item) => item.format === artifact.format);
        return replacement?.download_url ? apiBlob(replacement.download_url) : null;
      };
      let blob = await apiBlob(artifact.download_url).catch((caught) => {
        if (caught instanceof APIError && caught.status === 403) return freshDownload();
        throw caught;
      });
      if (!blob?.size) blob = await freshDownload();
      if (!blob) throw new Error("Download is no longer available");
      const href = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = href;
      anchor.download = artifact.filename;
      anchor.click();
      URL.revokeObjectURL(href);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Download failed");
    } finally {
      setDownloading("");
    }
  }

  if (!frontendConfig.agenticResearchEnabled) {
    return <div className="result">Research job details are disabled in this frontend build.</div>;
  }
  if (error && !job) return <p className="error" role="alert">{error}</p>;
  if (!job) return <div className="empty">Loading research job...</div>;

  const summary = reportSummary(job);
  const currentState = job.current_state ?? job.status.toUpperCase();

  return (
    <section className="result" data-testid="research-job-detail">
      <div className="result-header">
        <h2>{stateLabels[currentState] ?? "Unknown state"}</h2>
        <StatusBadge value={job.status} />
      </div>
      <p className="answer">{job.question}</p>
      <div className="progress-wrap" aria-label="Research progress">
        <progress value={job.progress_percent ?? 0} max={100} />
        <span>{job.progress_percent ?? 0}% · {job.stage ?? "stage unavailable"}</span>
      </div>
      <dl className="detail-list">
        <dt>Created</dt>
        <dd>{new Date(job.created_at).toLocaleString()}</dd>
        <dt>Completed</dt>
        <dd>{job.completed_at ? new Date(job.completed_at).toLocaleString() : "Not completed"}</dd>
        <dt>Sources</dt>
        <dd>{job.source_count ?? 0}</dd>
        <dt>Verified citations</dt>
        <dd>{job.verified_citation_count ?? 0}</dd>
        <dt>Formats</dt>
        <dd>{job.requested_formats?.join(", ") ?? "markdown"}</dd>
      </dl>
      {pollError ? <p className="warning" role="status">Temporary refresh issue: {pollError}</p> : null}
      {job.error_message ? <p className="error">{job.error_message}</p> : null}
      {isCancellableResearchState(job.current_state) ? (
        <button onClick={cancel} disabled={cancelling} data-testid="research-cancel">
          {cancelling ? "Requesting cancellation..." : "Cancel job"}
        </button>
      ) : null}
      {summary ? (
        <>
          <h3>Final report summary</h3>
          <p className="answer">{summary}</p>
        </>
      ) : null}
      <h3>Artifacts</h3>
      <div className="cards" data-testid="research-artifacts">
        {artifacts.map((artifact) => (
          <article className="card compact" key={`${artifact.format}-${artifact.filename}`}>
            <header>
              <strong>{artifact.format.toUpperCase()}</strong>
              <span>{Math.round(artifact.size_bytes / 1024)} KB</span>
            </header>
            <button
              onClick={() => void download(artifact)}
              disabled={downloading === artifact.format}
              aria-label={`Download ${artifact.format} report`}
            >
              {downloading === artifact.format ? "Downloading..." : `Download ${artifact.format}`}
            </button>
            <details>
              <summary>Technical details</summary>
              <p className="wrap">Checksum {artifact.checksum_sha256}</p>
            </details>
          </article>
        ))}
        {!artifacts.length ? <div className="empty">No artifacts are available yet.</div> : null}
      </div>
      {job.agent_run_id ? (
        <Link className="button secondary" href={`/agent/runs/${job.agent_run_id}`}>
          Open supporting agent run
        </Link>
      ) : null}
    </section>
  );
}
