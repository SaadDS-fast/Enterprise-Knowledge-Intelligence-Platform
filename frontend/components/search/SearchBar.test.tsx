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
    mockedApi.mockResolvedValueOnce({
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
    });

    render(<SearchBar />);

    await userEvent.type(
      screen.getByPlaceholderText("Ask a question grounded in your documents..."),
      "When does Atlas launch?",
    );
    fireEvent.click(screen.getByRole("button", { name: "Search knowledge" }));

    expect(screen.getByRole("button", { name: "Searching..." })).toBeDisabled();
    await waitFor(() => expect(screen.getByText("Evidence verified")).toBeInTheDocument());
    expect(screen.getAllByText("Project Atlas launches in March 2025.")).toHaveLength(2);
  });

  it("renders API errors", async () => {
    mockedApi.mockRejectedValueOnce(new Error("Search failed with 500"));

    render(<SearchBar />);

    await userEvent.type(
      screen.getByPlaceholderText("Ask a question grounded in your documents..."),
      "What failed?",
    );
    fireEvent.click(screen.getByRole("button", { name: "Search knowledge" }));

    await waitFor(() => expect(screen.getByText("Search failed with 500")).toBeInTheDocument());
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
    mockedApi.mockResolvedValueOnce({
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
    });

    render(<SearchBar />);

    await userEvent.type(
      screen.getByPlaceholderText("Ask a question grounded in your documents..."),
      "What happened?",
    );
    fireEvent.click(screen.getByRole("button", { name: "Search knowledge" }));

    await waitFor(() => expect(screen.getByText(label)).toBeInTheDocument());
  });
});
