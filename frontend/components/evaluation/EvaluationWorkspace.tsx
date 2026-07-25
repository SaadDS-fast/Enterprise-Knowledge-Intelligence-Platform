"use client";
import type { FormEvent } from "react";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { EvaluationRun } from "@/types";

type EvaluationCaseResult = {
  question?: string;
  expected_answer?: string;
  actual_answer?: string;
  actual_value?: string | null;
  passed?: boolean;
  normalized_answer_match?: boolean;
  token_f1?: number;
  evidence_support?: string;
  citation_validity?: boolean;
  abstained?: boolean;
  conflict_status?: string;
};

export default function EvaluationWorkspace() {
  const [runs, setRuns] = useState<EvaluationRun[]>([]);
  const [name, setName] = useState("");
  const [pipeline, setPipeline] = useState("standard_search");
  const [question, setQuestion] = useState("");
  const [expectedAnswer, setExpectedAnswer] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function load() {
    try {
      setRuns(await api<EvaluationRun[]>("/evaluation"));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Failed to load evaluations");
    }
  }

  useEffect(() => {
    void load();
  }, []);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError("");
    try {
      await api("/evaluation", {
        method: "POST",
        body: JSON.stringify({
          name,
          pipeline,
          cases: [{ question, expected_answer: expectedAnswer }],
        }),
      });
      setName("");
      setPipeline("standard_search");
      setQuestion("");
      setExpectedAnswer("");
      await load();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Evaluation failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <form className="evaluation-form" onSubmit={submit} data-testid="evaluation-form">
        <p className="muted">
          Evaluation runs the question against the selected deterministic pipeline and compares the
          grounded answer with the expected answer.
        </p>
        <label>
          Evaluation name
          <input
            name="name"
            value={name}
            onChange={(event) => setName(event.target.value)}
            required
            data-testid="evaluation-name"
          />
        </label>
        <label>
          Pipeline
          <select
            name="pipeline"
            value={pipeline}
            onChange={(event) => setPipeline(event.target.value)}
            data-testid="evaluation-pipeline"
          >
            <option value="standard_search">Standard Search</option>
            <option value="controlled_agent">Controlled Agent</option>
          </select>
        </label>
        <label>
          Question
          <textarea
            name="question"
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            required
            data-testid="evaluation-question"
          />
        </label>
        <label>
          Expected answer
          <textarea
            name="answer"
            value={expectedAnswer}
            onChange={(event) => setExpectedAnswer(event.target.value)}
            required
            data-testid="evaluation-answer"
          />
        </label>
        <button disabled={loading} data-testid="evaluation-submit">
          {loading ? "Running evaluation..." : "Run evaluation"}
        </button>
      </form>
      {error ? <p className="error" role="alert">{error}</p> : null}
      <div className="cards">
        {runs.map((run) => (
          <article className="card" key={run.id} data-testid="evaluation-run">
            <h3>{run.name}</h3>
            <p>
              Status: <strong>{run.status}</strong>
            </p>
            <p>Pipeline: {String(run.config_json.pipeline ?? "standard_search")}</p>
            <dl>
              {Object.entries(run.metrics_json).map(([key, value]) => (
                <div key={key}>
                  <dt>{key.replaceAll("_", " ")}</dt>
                  <dd>{typeof value === "number" ? value.toFixed(3) : String(value)}</dd>
                </div>
              ))}
            </dl>
            {caseResults(run).map((item, index) => (
              <section className="diagnosis" key={`${item.question ?? "case"}-${index}`}>
                <strong>{item.passed ? "PASS" : "FAIL"}</strong>
                <span>Question: {item.question ?? "not recorded"}</span>
                <span>Expected answer: {item.expected_answer ?? "not recorded"}</span>
                <span>Actual answer: {item.actual_answer ?? "not recorded"}</span>
                {item.actual_value ? <span>Actual value: {item.actual_value}</span> : null}
                <span>
                  Normalized answer match: {item.normalized_answer_match ? "yes" : "no"}
                </span>
                <span>Token F1: {formatMetric(item.token_f1)}</span>
                <span>Evidence support: {item.evidence_support ?? "unknown"}</span>
                <span>Citation validity: {item.citation_validity ? "valid" : "invalid"}</span>
                <span>Abstained: {item.abstained ? "yes" : "no"}</span>
                <span>Outcome: {item.conflict_status ?? "unknown"}</span>
              </section>
            ))}
          </article>
        ))}
      </div>
    </div>
  );
}

function caseResults(run: EvaluationRun): EvaluationCaseResult[] {
  const value = run.config_json.case_results;
  return Array.isArray(value) ? (value as EvaluationCaseResult[]) : [];
}

function formatMetric(value: number | undefined): string {
  return typeof value === "number" ? value.toFixed(3) : "not recorded";
}
