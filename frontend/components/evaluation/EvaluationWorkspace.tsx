"use client";
import type { FormEvent } from "react";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { EvaluationRun } from "@/types";

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
          </article>
        ))}
      </div>
    </div>
  );
}
