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

  it("renders collapsible semantic retrieval diagnostics without vectors", async () => {
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

    await screen.findByText(/Hybrid lexical \+ semantic retrieval/);
    expect(screen.getByText(/Reranker applied/)).toBeInTheDocument();
    expect(screen.getByText(/Selected-document scope/)).toBeInTheDocument();
    expect(screen.getByText(/Retrieval recovery used/)).toBeInTheDocument();
    expect(screen.getByText("Technical retrieval diagnostics")).toBeInTheDocument();
    expect(document.body.textContent).not.toMatch(/embedding_values|raw_vector/);
  });

  it.each([
    ["SUFFICIENT_EVIDENCE", "Evidence found directly"],
    ["RETRIEVAL_FAILURE_RECOVERED", "Evidence found after an additional search"],
    [
      "RETRIEVAL_FAILURE_UNRESOLVED",
      "Relevant evidence may exist, but the search could not verify it",
    ],
    ["KNOWLEDGE_ABSENT", "Information does not appear to exist in the selected documents"],
    ["PARTIAL_EVIDENCE", "Only partial evidence found"],
    ["CONFLICTING_EVIDENCE", "Conflicting evidence found"],
    ["AMBIGUOUS_QUERY", "Question needs clarification"],
  ])("renders diagnosis state %s", async (status, label) => {
    mockedApi
      .mockResolvedValueOnce([])
      .mockResolvedValueOnce({
        answer: "I do not have enough evidence to answer that.",
        evidence: [],
        sufficient_evidence: false,
        abstained: true,
        request_id: "req-1",
        retrieval_diagnosis: {
          status,
          initial_evidence_sufficient: status === "SUFFICIENT_EVIDENCE",
          retry_performed: status !== "SUFFICIENT_EVIDENCE",
          retry_strategy: status === "SUFFICIENT_EVIDENCE" ? [] : ["query_reformulation"],
          initial_support_score: 0.1,
          final_support_score: 0.42,
          evidence_count: 0,
          reason_code: "TEST",
        },
        outcome: status === "CONFLICTING_EVIDENCE" ? "CONFLICTING_EVIDENCE" : "INSUFFICIENT_EVIDENCE",
        support_status: "ABSENT",
        confidence_category: "none",
        citations: [],
        conflicts: [],
        topic_items: [],
        active_document_scope: [],
      });

    render(<SearchBar />);

    await userEvent.type(
      screen.getByPlaceholderText("Ask a question grounded in your documents..."),
      "What happened?",
    );
    fireEvent.click(screen.getByRole("button", { name: "Search knowledge" }));

    await waitFor(() => expect(screen.getByText(label)).toBeInTheDocument());
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
});
