import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import ResearchWorkspace from "./ResearchWorkspace";

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

describe("ResearchWorkspace", () => {
  beforeEach(() => {
    mockedApi.mockReset();
  });

  it("creates async report jobs with internal-only scope and safe format selection", async () => {
    mockedApi
      .mockResolvedValueOnce([])
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
      .mockResolvedValueOnce({
        job_id: "job-1",
        status: "pending",
        current_state: "PENDING",
        idempotent_replay: false,
      })
      .mockResolvedValueOnce([
        {
          id: "job-1",
          question: "Summarize Atlas launch risks.",
          status: "pending",
          current_state: "PENDING",
          result_json: {},
          created_at: "2026-07-20T00:00:00Z",
          updated_at: "2026-07-20T00:00:00Z",
        },
      ])
      .mockResolvedValueOnce([]);

    render(<ResearchWorkspace />);

    await screen.findByText("Atlas Plan");
    await userEvent.type(screen.getByTestId("research-question"), "Summarize Atlas launch risks.");
    fireEvent.click(screen.getByLabelText("PDF"));
    fireEvent.click(screen.getByTestId("research-submit"));

    await waitFor(() => {
      expect(mockedApi).toHaveBeenCalledWith(
        "/agent/research",
        expect.objectContaining({
          method: "POST",
          body: JSON.stringify({
            question: "Summarize Atlas launch risks.",
            document_ids: null,
            allow_external_sources: false,
            requested_formats: ["markdown", "pdf"],
            max_depth_preset: "standard",
          }),
        }),
      );
    });
    expect(await screen.findByText(/Report accepted/)).toBeInTheDocument();
    expect(screen.queryByTestId("research-external-toggle")).not.toBeInTheDocument();
  });
});
