import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import ResearchJobDetail from "./ResearchJobDetail";

vi.mock("@/lib/api", () => {
  class APIError extends Error {
    constructor(
      public status: number,
      message: string,
    ) {
      super(message);
    }
  }
  return {
    APIError,
    api: vi.fn(),
    apiBlob: vi.fn(),
  };
});

vi.mock("@/lib/config", () => ({
  boundedPollInterval: vi.fn(() => 2000),
  frontendConfig: {
    agenticRagEnabled: true,
    agenticResearchEnabled: true,
    externalSourcesEnabled: false,
    pollIntervalMs: 2000,
  },
}));

import { api, APIError, apiBlob } from "@/lib/api";

const mockedApi = vi.mocked(api);
const mockedApiBlob = vi.mocked(apiBlob);

describe("ResearchJobDetail", () => {
  beforeEach(() => {
    mockedApi.mockReset();
    mockedApiBlob.mockReset();
    vi.spyOn(URL, "createObjectURL").mockReturnValue("blob:download");
    vi.spyOn(URL, "revokeObjectURL").mockImplementation(() => undefined);
    vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => undefined);
  });

  it("refreshes artifacts when a signed download URL expires", async () => {
    let artifactRefreshCount = 0;
    mockedApi.mockImplementation(async (path) => {
      if (path === "/agent/research/job-1") {
        return {
          id: "job-1",
          question: "Write the Atlas report.",
          status: "completed",
          current_state: "COMPLETED",
          progress_percent: 100,
          requested_formats: ["markdown"],
          source_count: 2,
          verified_citation_count: 2,
          result_json: { report: { executive_summary: "Atlas is ready for beta." } },
          created_at: "2026-07-20T00:00:00Z",
          updated_at: "2026-07-20T00:00:00Z",
          completed_at: "2026-07-20T00:01:00Z",
        };
      }
      if (path === "/agent/research/job-1/artifacts") {
        artifactRefreshCount += 1;
        return [
          {
            format: "markdown",
            filename: "atlas.md",
            mime_type: "text/markdown",
            checksum_sha256: "abc123",
            size_bytes: 2048,
            download_url: `/api/v1/agent/research/job-1/artifacts/md?sig=${
              artifactRefreshCount === 1 ? "old" : "fresh"
            }`,
          },
        ];
      }
      throw new Error(`Unexpected API path ${path}`);
    });
    mockedApiBlob
      .mockRejectedValueOnce(new APIError(403, "Expired signed URL"))
      .mockResolvedValueOnce(new Blob(["# Atlas"], { type: "text/markdown" }));

    render(<ResearchJobDetail jobId="job-1" />);

    const button = await screen.findByRole("button", { name: "Download markdown report" });
    fireEvent.click(button);

    await waitFor(() => {
      expect(mockedApiBlob).toHaveBeenLastCalledWith(
        "/api/v1/agent/research/job-1/artifacts/md?sig=fresh",
      );
    });
    expect(URL.createObjectURL).toHaveBeenCalled();
  });
});
