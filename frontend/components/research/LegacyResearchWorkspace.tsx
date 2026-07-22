"use client";

import type { FormEvent } from "react";
import { useCallback, useEffect, useState } from "react";

import { api } from "@/lib/api";
import type { ResearchJob } from "@/types";

import StatusBadge from "@/components/ui/StatusBadge";

export default function LegacyResearchWorkspace() {
  const [question, setQuestion] = useState("");
  const [jobs, setJobs] = useState<ResearchJob[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    try {
      setJobs(await api<ResearchJob[]>("/research"));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Failed to load research jobs");
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError("");
    try {
      await api("/research", { method: "POST", body: JSON.stringify({ question }) });
      setQuestion("");
      await load();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Research request failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <form className="evaluation-form" onSubmit={submit}>
        <label htmlFor="legacy-research-question">Research question</label>
        <textarea
          id="legacy-research-question"
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          placeholder="Create a cited brief from workspace evidence..."
          required
        />
        {error ? (
          <p className="error" role="alert">
            {error}
          </p>
        ) : null}
        <button disabled={loading}>{loading ? "Creating..." : "Create brief"}</button>
      </form>
      <div className="cards">
        {jobs.map((job) => (
          <article className="card" key={job.id}>
            <header>
              <strong>{job.question}</strong>
              <StatusBadge value={job.status} />
            </header>
            {job.report_markdown ? <p className="report">{job.report_markdown}</p> : null}
          </article>
        ))}
        {!jobs.length ? <div className="empty">No research jobs yet.</div> : null}
      </div>
    </>
  );
}
