import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import SearchBar from "./SearchBar";

vi.mock("@/lib/api", () => ({
  api: vi.fn(),
}));

import { api } from "@/lib/api";

const mockedApi = vi.mocked(api);

describe("SearchBar", () => {
  beforeEach(() => {
    mockedApi.mockReset();
  });

  it("renders loading state and grounded evidence", async () => {
    mockedApi
      .mockResolvedValueOnce([])
      .mockResolvedValueOnce({
        answer: "Project Atlas launches in March 2025.",
        evidence: [
          {
            chunk_id: "chunk-1",
            document_id: "doc-1",
            document_title: "Atlas Brief",
            content: "Project Atlas launches in March 2025.",
            score: 0.91,
            metadata: {},
          },
        ],
        sufficient_evidence: true,
        abstained: false,
        request_id: "req-1",
        outcome: "ANSWER_SUPPORTED",
        support_status: "SUPPORTED",
        confidence_category: "high",
        citations: [
          {
            chunk_id: "chunk-1",
            document_title: "Atlas Brief",
            excerpt: "Project Atlas launches in March 2025.",
          },
        ],
        conflicts: [],
        topic_items: [],
        active_document_scope: [],
      });

    render(<SearchBar />);

    await userEvent.type(
      screen.getByPlaceholderText("Ask a question grounded in your documents..."),
      "When does Atlas launch?",
    );
    fireEvent.click(screen.getByRole("button", { name: "Search knowledge" }));

    expect(screen.getByRole("button", { name: "Searching..." })).toBeDisabled();
    await waitFor(() => expect(screen.getAllByText("Answer supported")[0]).toBeInTheDocument());
    expect(screen.getAllByText("Project Atlas launches in March 2025.")).toHaveLength(3);
  });

  it("renders API errors", async () => {
    mockedApi.mockResolvedValueOnce([]).mockRejectedValueOnce(new Error("Search failed with 500"));

    render(<SearchBar />);

    await userEvent.type(
      screen.getByPlaceholderText("Ask a question grounded in your documents..."),
      "What failed?",
    );
    fireEvent.click(screen.getByRole("button", { name: "Search knowledge" }));

    await waitFor(() => expect(screen.getByText("Search failed with 500")).toBeInTheDocument());
  });

  it("does not expose internal retrieval classifications or scores", async () => {
    mockedApi.mockResolvedValueOnce([]).mockResolvedValueOnce({
      answer: "PKR 5,000 per day.",
      evidence: [],
      sufficient_evidence: true,
      abstained: false,
      retrieval_diagnosis: {
        status: "RETRIEVAL_FAILURE_RECOVERED",
        initial_evidence_sufficient: false,
        retry_performed: true,
        retry_strategy: ["top_k_expansion"],
        initial_support_score: 0.2,
        final_support_score: 0.9,
        evidence_count: 1,
        reason_code: "RETRY_FOUND_SUPPORTING_EVIDENCE",
        semantic_used: true,
        reranker_used: true,
        selected_document_scope: true,
        retrieval_recovery_used: true,
        candidate_count: 4,
        final_evidence_count: 1,
        retrieval_duration_ms: 12.4,
      },
      outcome: "ANSWER_SUPPORTED",
      support_status: "SUPPORTED",
      confidence_category: "high",
      active_document_scope: [],
    });
    render(<SearchBar />);
    await userEvent.type(screen.getByTestId("search-query"), "What is the meal allowance?");
    fireEvent.click(screen.getByTestId("search-submit"));

    await screen.findByText("PKR 5,000 per day.");
    expect(document.body.textContent).not.toMatch(
      /RETRIEVAL_FAILURE|support score|retry|recovery|embedding_values|raw_vector/i,
    );
  });

  it("sends selected document scope and renders topic items", async () => {
    mockedApi
      .mockResolvedValueOnce([
        {
          id: "doc-1",
          workspace_id: "workspace-1",
          title: "AS_Practice_questions",
          status: "ready",
          description: null,
          created_by: "user-1",
          created_at: "2026-07-25T00:00:00Z",
          updated_at: "2026-07-25T00:00:00Z",
        },
      ])
      .mockResolvedValueOnce({
        answer: "The practice questions cover:\n1. Functions - supported by AS_Practice_questions.",
        evidence: [],
        sufficient_evidence: true,
        abstained: false,
        outcome: "ANSWER_SUPPORTED",
        support_status: "SUPPORTED",
        confidence_category: "high",
        citations: [
          {
            chunk_id: "chunk-1",
            document_title: "AS_Practice_questions",
            excerpt: "Section: Functions\nQuestion 1: Determine whether...",
            topic: "Functions",
          },
        ],
        conflicts: [],
        topic_items: [
          {
            label: "Functions",
            confidence: "high",
            support_status: "SUPPORTED",
            chunk_id: "chunk-1",
            document_id: "doc-1",
            document_title: "AS_Practice_questions",
            excerpt: "Section: Functions\nQuestion 1: Determine whether...",
            section: "Functions",
          },
        ],
        active_document_scope: [{ document_id: "doc-1", title: "AS_Practice_questions" }],
      });

    render(<SearchBar />);

    await waitFor(() => expect(screen.getByText("AS_Practice_questions")).toBeInTheDocument());
    await userEvent.selectOptions(screen.getByTestId("search-document-scope"), "doc-1");
    await userEvent.type(
      screen.getByPlaceholderText("Ask a question grounded in your documents..."),
      "What topics are covered by the practice questions?",
    );
    fireEvent.click(screen.getByRole("button", { name: "Search knowledge" }));

    await waitFor(() => expect(screen.getByTestId("search-topic-list")).toHaveTextContent("Functions"));
    expect(mockedApi).toHaveBeenLastCalledWith("/search", {
      method: "POST",
      body: JSON.stringify({
        query: "What topics are covered by the practice questions?",
        document_ids: ["doc-1"],
      }),
    });
    expect(screen.getByTestId("search-result-scope")).toHaveTextContent("AS_Practice_questions");
  });

  it.each([
    [
      true,
      false,
      "verified",
      "Grounded answer generated locally",
      "Generated claims verified against cited evidence",
    ],
    [
      false,
      true,
      "generation_timeout",
      "Local generator unavailable — safe fallback used",
      "Server-authorized citations retained",
    ],
  ])(
    "renders safe generation metadata without raw provider output",
    async (used, fallback, verification, label, verificationLabel) => {
      mockedApi.mockResolvedValueOnce([]).mockResolvedValueOnce({
        answer: "The verified allowance is PKR 5,000.",
        evidence: [],
        sufficient_evidence: true,
        abstained: false,
        outcome: "ANSWER_SUPPORTED",
        support_status: "SUPPORTED",
        confidence_category: "high",
        citations: [],
        conflicts: [],
        topic_items: [],
        active_document_scope: [],
        generation_provider: used ? "ollama" : "extractive",
        generation_model: used ? "approved-local-alias" : "deterministic-extractive-v2",
        generation_used: used,
        generation_fallback_used: fallback,
        generation_duration_ms: 12,
        generation_verification: verification,
        structured_output_valid: used,
        claim_verification_passed: used,
      });
      render(<SearchBar />);
      await userEvent.type(screen.getByTestId("search-query"), "What is the allowance?");
      fireEvent.click(screen.getByTestId("search-submit"));

      expect(await screen.findByText(label)).toBeInTheDocument();
      expect(screen.getByText(verificationLabel)).toBeInTheDocument();
      expect(document.body.textContent).not.toMatch(/candidate_answer|reasoning|system prompt/i);
    },
  );

  it.each([
    [
      "equation",
      "A quadratic equation has the form ax² + bx + c = 0, where a is not zero.",
      "Quadratic Equations",
    ],
    [
      "negation",
      "Employees must not exceed the approved travel limit.",
      "Travel Policy",
    ],
    [
      "owner/date",
      "The policy owner is Ayesha Khan. The policy is effective from 1 February 2026.",
      "Policy Details",
    ],
  ])("renders supported %s answers with visible claim citations", async (_, answer, title) => {
    mockedApi.mockResolvedValueOnce([]).mockResolvedValueOnce({
      answer,
      evidence: [],
      sufficient_evidence: true,
      abstained: false,
      outcome: "ANSWER_SUPPORTED",
      support_status: "SUPPORTED",
      confidence_category: "high",
      citations: [
        {
          chunk_id: "chunk-closure",
          document_id: "doc-closure",
          document_title: title,
          excerpt: answer,
        },
      ],
      conflicts: [],
      topic_items: [],
      active_document_scope: [],
      response_state: {
        primary_state: title === "Policy Details" ? "SUPPORTED_COMPOSITE" : "SUPPORTED",
        answer,
        claims: [
          { claim_id: "claim-1", text: answer, citation_ids: ["chunk-closure"] },
          ...(title === "Policy Details"
            ? [{ claim_id: "claim-2", text: "1 February 2026", citation_ids: ["chunk-closure"] }]
            : []),
        ],
        citation_ids: ["chunk-closure"],
        citation_document_ids: { "chunk-closure": "doc-closure" },
        evidence_decision: "SUFFICIENT",
        conflict: { category: "NO_CONFLICT", unresolved: false, material: false, sides: [] },
        confidence: {
          retrieval: "HIGH",
          evidence_support: "HIGH",
          conflict: "NOT_APPLICABLE",
          final: "HIGH",
        },
        retrieval: {
          mode: "lexical",
          semantic_applied: false,
          reranker_applied: false,
          lexical_fallback_used: false,
          recovery_attempted: false,
          recovery_succeeded: false,
          failure_category: null,
        },
        scope: { selected_document_scope: false, authorized_document_ids: [] },
        diagnostics: {},
        user_message: answer,
      },
    });

    render(<SearchBar />);
    await userEvent.type(screen.getByTestId("search-query"), "Show supported answer");
    fireEvent.click(screen.getByTestId("search-submit"));

    expect(await screen.findByTestId("search-answer")).toHaveTextContent(answer);
    expect(screen.getByTestId("search-citations")).toHaveTextContent(title);
    expect(screen.getByTestId("search-citations")).toHaveTextContent(answer);
    expect(screen.getByTestId("search-claim-support")).toHaveTextContent("chunk-closure");
    expect(screen.getByTestId("search-verdict")).not.toHaveTextContent(/insufficient|failed/i);
    expect(document.body.textContent).not.toMatch(/answer_segments|fact_ids|\/Users\//i);
  });

  it("shows the passport indicator only when the server returns a persisted reference", async () => {
    mockedApi.mockResolvedValueOnce([]).mockResolvedValueOnce({
      answer: "A supported unchanged answer.",
      evidence: [],
      sufficient_evidence: true,
      abstained: false,
      outcome: "ANSWER_SUPPORTED",
      support_status: "SUPPORTED",
      confidence_category: "high",
      citations: [],
      conflicts: [],
      active_document_scope: [],
      passport_reference: {
        passport_id: "urn:uuid:00000000-0000-0000-0000-000000000042",
        schema_version: "vap-1",
        metadata_available: true,
        export_available: true,
      },
    });
    render(<SearchBar />);
    await userEvent.type(screen.getByTestId("search-query"), "Show supported answer");
    fireEvent.click(screen.getByTestId("search-submit"));
    expect(await screen.findByTestId("passport-card")).toHaveTextContent("Answer Passport");
    expect(screen.getByTestId("search-answer")).toHaveTextContent("A supported unchanged answer.");
  });

  it.each(["CONFLICTING_EVIDENCE", "PROCESSING_FAILED", "INSUFFICIENT_EVIDENCE"])(
    "does not imply passport availability for %s",
    async (outcome) => {
      mockedApi.mockResolvedValueOnce([]).mockResolvedValueOnce({
        answer: "Neutral terminal response.",
        evidence: [],
        sufficient_evidence: false,
        abstained: true,
        outcome,
        support_status: outcome === "CONFLICTING_EVIDENCE" ? "CONFLICT" : "ABSENT",
        confidence_category: "none",
        citations: [],
        conflicts: [],
        active_document_scope: [],
        passport_reference: null,
      });
      render(<SearchBar />);
      await userEvent.type(screen.getByTestId("search-query"), "Show terminal response");
      fireEvent.click(screen.getByTestId("search-submit"));
      await screen.findByText("Neutral terminal response.");
      expect(screen.queryByTestId("passport-card")).not.toBeInTheDocument();
    },
  );
});
