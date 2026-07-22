import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import AgentWorkspace from "./AgentWorkspace";

vi.mock("@/lib/api", () => ({
  api: vi.fn(),
}));

vi.mock("@/lib/auth", () => ({
  getWorkspaceId: vi.fn(() => "workspace-1"),
}));

vi.mock("@/lib/config", () => ({
  frontendConfig: {
    agenticRagEnabled: true,
    agenticResearchEnabled: true,
    externalSourcesEnabled: false,
    pollIntervalMs: 2000,
  },
}));

import { api } from "@/lib/api";

const mockedApi = vi.mocked(api);

const agentResponse = {
  run_id: "run-1",
  status: "completed",
  current_state: "COMPLETED",
  answer: "Atlas launches in March with a controlled beta.",
  abstained: false,
  citations: [
    {
      citation_label: "C1",
      document_title: "Atlas Plan",
      chunk_id: "chunk-1",
      excerpt: "Launch beta in March.",
    },
  ],
  evidence: [],
  internal_evidence: [
    {
      chunk_id: "chunk-1",
      document_id: "doc-1",
      document_title: "Atlas Plan",
      content: "Launch beta in March.",
      score: 0.93,
      metadata: {},
    },
  ],
  external_evidence: [],
  external_sources_used: false,
  providers_used: [],
  external_access_allowed: false,
  external_access_performed: false,
  tools_used: ["internal_search", "answer_synthesizer"],
  safe_step_summaries: ["Searched authorized workspace documents."],
  safe_plan_summary: "Answer from internal evidence.",
  total_duration_ms: 128,
  fallback_used: false,
  retrieval_diagnosis: {
    status: "SUFFICIENT_EVIDENCE",
    retry_performed: false,
    evidence_count: 1,
  },
  outcome: "ANSWER_SUPPORTED",
  claims: [
    {
      claim_text: "Atlas launches in March.",
      verification_status: "supported",
      support_score: 0.91,
      citations: ["C1"],
    },
  ],
  conflicts: [],
  unsupported_claims_removed: [],
  confidence_category: "high",
  unified_evidence: [],
};

describe("AgentWorkspace", () => {
  beforeEach(() => {
    mockedApi.mockReset();
    localStorage.clear();
  });

  it("submits controlled internal-only agent queries and renders safe evidence", async () => {
    mockedApi
      .mockResolvedValueOnce([
        {
          id: "doc-1",
          workspace_id: "workspace-1",
          title: "Atlas Plan",
          status: "ready",
          created_by: "user-1",
          created_at: "2026-07-20T00:00:00Z",
          updated_at: "2026-07-20T00:00:00Z",
        },
      ])
      .mockResolvedValueOnce(agentResponse)
      .mockResolvedValueOnce({
        id: "run-1",
        workspace_id: "workspace-1",
        user_id: "user-1",
        status: "completed",
        current_state: "COMPLETED",
        input_query: "When does Atlas launch?",
        result_json: {},
        created_at: "2026-07-20T00:00:00Z",
        updated_at: "2026-07-20T00:00:00Z",
        steps: [],
        tool_calls: [],
      });

    render(<AgentWorkspace />);

    await screen.findByText("Atlas Plan");
    await userEvent.type(screen.getByTestId("agent-query"), "When does Atlas launch?");
    fireEvent.click(screen.getByTestId("agent-submit"));

    await waitFor(() => {
      expect(mockedApi).toHaveBeenCalledWith(
        "/agent/query",
        expect.objectContaining({
          method: "POST",
          body: JSON.stringify({
            query: "When does Atlas launch?",
            document_ids: null,
            allow_external_sources: false,
          }),
        }),
      );
    });

    const result = await screen.findByTestId("agent-result");
    expect(within(result).getByText("Atlas launches in March with a controlled beta.")).toBeInTheDocument();
    expect(within(result).getAllByText("Atlas Plan").length).toBeGreaterThan(0);
    expect(within(result).getByText("internal search")).toBeInTheDocument();
    expect(within(result).queryByText(/hidden reasoning/i)).not.toBeInTheDocument();
  });
});
