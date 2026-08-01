"use client";

import type { FormEvent } from "react";
import { useEffect, useMemo, useState } from "react";

import { api } from "@/lib/api";
import type { DocumentItem, SearchResult } from "@/types";

import EvidencePanel from "./EvidencePanel";

const outcomeCopy: Record<string, string> = {
  ANSWER_SUPPORTED: "Answer supported",
  ANSWER_PARTIALLY_SUPPORTED: "Partially supported",
  CLARIFICATION_REQUIRED: "Clarification required",
  SUPPORTED: "Answer supported",
  SUPPORTED_COMPOSITE: "Answer supported by multiple sources",
  CONFLICTING_EVIDENCE: "Sources contain conflicting information",
  KNOWLEDGE_ABSENT: "Information not found in selected documents",
  RETRIEVAL_FAILURE: "Retrieval could not be completed",
  AMBIGUOUS_QUERY: "Query needs clarification",
  LOW_QUALITY_SOURCE: "Source quality is insufficient",
  INSUFFICIENT_EVIDENCE: "Insufficient evidence",
  PROCESSING_FAILED: "Response could not be completed",
  CANCELLED: "Request cancelled",
};

export default function SearchBar() {
  const [query, setQuery] = useState("");
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [selectedDocumentId, setSelectedDocumentId] = useState("");
  const [result, setResult] = useState<SearchResult | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    let mounted = true;
    api<DocumentItem[]>("/documents")
      .then((items) => {
        if (mounted) setDocuments(items.filter((item) => item.status === "ready"));
      })
      .catch(() => {
        if (mounted) setDocuments([]);
      });
    return () => {
      mounted = false;
    };
  }, []);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError("");
    try {
      setResult(
        await api<SearchResult>("/search", {
          method: "POST",
          body: JSON.stringify({
            query,
            document_ids: selectedDocumentId ? [selectedDocumentId] : null,
          }),
        }),
      );
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Search failed");
    } finally {
      setLoading(false);
    }
  }

  const outcome =
    result?.response_state?.primary_state ??
    result?.outcome ??
    (result?.abstained ? "INSUFFICIENT_EVIDENCE" : "SUPPORTED");
  const activeScope = useMemo(
    () =>
      result?.active_document_scope?.length
        ? result.active_document_scope.map((item) => item.title).join(", ")
        : selectedDocumentId
          ? documents.find((item) => item.id === selectedDocumentId)?.title
          : "All ready workspace documents",
    [documents, result, selectedDocumentId],
  );

  return (
    <div>
      <form className="search-form" onSubmit={submit} data-testid="search-form">
        <label className="sr-only" htmlFor="search-query">
          Search query
        </label>
        <textarea
          id="search-query"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Ask a question grounded in your documents..."
          minLength={2}
          required
          data-testid="search-query"
        />
        <label htmlFor="search-document-scope">Search scope</label>
        <select
          id="search-document-scope"
          value={selectedDocumentId}
          onChange={(event) => setSelectedDocumentId(event.target.value)}
          data-testid="search-document-scope"
        >
          <option value="">All ready workspace documents</option>
          {documents.map((document) => (
            <option value={document.id} key={document.id}>
              {document.title}
            </option>
          ))}
        </select>
        <p className="muted" data-testid="search-active-scope">
          Active scope: {activeScope}
        </p>
        <button disabled={loading} data-testid="search-submit">
          {loading ? "Searching..." : "Search knowledge"}
        </button>
      </form>
      {error ? (
        <p className="error" data-testid="search-error">
          {error}
        </p>
      ) : null}
      {result ? (
        <section className="result" data-testid="search-result">
          <div className="result-header">
            <h2>Answer</h2>
            <span className={result.abstained ? "warning" : "success"} data-testid="search-verdict">
              {outcomeCopy[outcome] ?? outcome}
            </span>
          </div>
          <div className="diagnosis" aria-label="Answer outcome" data-testid="search-outcome">
            <strong>{outcomeCopy[outcome] ?? outcome}</strong>
            <span>
              Evidence:{" "}
              {(
                result.response_state?.evidence_decision ??
                result.support_status ??
                (result.sufficient_evidence ? "SUPPORTED" : "ABSENT")
              )
                .toLowerCase()
                .replaceAll("_", " ")}{" "}
              · Confidence:{" "}
              {(
                result.response_state?.confidence.final ??
                result.confidence_category ??
                "none"
              )
                .toLowerCase()
                .replaceAll("_", " ")}
            </span>
          </div>
          <p className="muted" data-testid="search-result-scope">
            Result scope: {activeScope}
          </p>
          <div className="diagnosis" aria-label="Answer generation" data-testid="generation-status">
            <strong>
              {result.generation_used
                ? "Grounded answer generated locally"
                : result.generation_fallback_used
                  ? "Local generator unavailable — safe fallback used"
                  : "Deterministic grounded answer used"}
            </strong>
            <span>
                {result.claim_verification_passed
                ? "Generated claims verified against cited evidence"
                : result.generation_used
                  ? "Generated answer could not be verified"
                  : "Server-authorized citations retained"}
            </span>
            <details>
              <summary>Technical generation details</summary>
              <small>
                Provider: {result.generation_provider ?? "extractive"} · Verification:{" "}
                {(result.generation_verification ?? "not_applicable").replaceAll("_", " ")} ·
                Duration: {Math.round(result.generation_duration_ms ?? 0)} ms
              </small>
            </details>
          </div>
          <pre className="answer" data-testid="search-answer">
            {result.answer}
          </pre>
          {result.topic_items?.length ? (
            <>
              <h2>Topics</h2>
              <div className="evidence-list" data-testid="search-topic-list">
                {result.topic_items.map((topic, index) => (
                  <article className="evidence" key={`${topic.label}-${index}`}>
                    <header>
                      <strong>
                        {index + 1}. {topic.label}
                      </strong>
                      <span>{topic.confidence}</span>
                    </header>
                    <small>
                      {topic.support_status} · {topic.document_title}
                    </small>
                  </article>
                ))}
              </div>
            </>
          ) : null}
          {result.answer_value ? (
            <p className="muted" data-testid="search-answer-value">
              Extracted value: {result.answer_value}
            </p>
          ) : null}
          {result.abstention_reason ? (
            <p className="muted" data-testid="search-abstention-reason">
              Reason: {result.abstention_reason}
            </p>
          ) : null}
          {result.conflicts?.length ? (
            <>
              <h2>Conflicts</h2>
              <div className="evidence-list" data-testid="search-conflicts">
                {result.conflicts.map((conflict, index) => (
                  <article className="evidence" key={`${conflict.summary ?? "conflict"}-${index}`}>
                    <strong>{conflict.summary ?? "Conflict detected"}</strong>
                    <p>{conflict.values?.join(" / ")}</p>
                  </article>
                ))}
              </div>
            </>
          ) : null}
          {result.response_state?.conflict.sides.length ? (
            <>
              <h2>Conflict sides</h2>
              <div className="evidence-list" data-testid="search-conflict-sides">
                {result.response_state.conflict.sides.map((side) => (
                  <article className="evidence warning-card" key={side.claim_id}>
                    <strong>{side.text}</strong>
                    <small>Citations: {side.citation_ids.join(", ")}</small>
                  </article>
                ))}
              </div>
            </>
          ) : null}
          {result.response_state?.claims.length ? (
            <>
              <h2>Claim support</h2>
              <div className="evidence-list" data-testid="search-claim-support">
                {result.response_state.claims.map((claim) => (
                  <article className="evidence" key={claim.claim_id}>
                    <strong>{claim.text}</strong>
                    <small>Citations: {claim.citation_ids.join(", ")}</small>
                  </article>
                ))}
              </div>
            </>
          ) : null}
          <h2>Citations</h2>
          <div className="citation-list" data-testid="search-citations">
            {result.citations?.length ? (
              result.citations.map((citation, index) => (
                <article className="citation" key={`${citation.chunk_id}-${index}`}>
                  <strong>
                    [{index + 1}] {citation.document_title}
                  </strong>
                  {citation.topic ? <small>Topic: {citation.topic}</small> : null}
                  <p>{citation.excerpt}</p>
                </article>
              ))
            ) : (
              <div className="empty">No validated citations for this result.</div>
            )}
          </div>
          <h2>Evidence</h2>
          <EvidencePanel items={result.evidence} />
        </section>
      ) : null}
    </div>
  );
}
