import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import DocumentExplorer from "./DocumentExplorer";

vi.mock("@/lib/api", () => ({
  api: vi.fn(),
}));

import { api } from "@/lib/api";

const mockedApi = vi.mocked(api);

describe("DocumentExplorer", () => {
  beforeEach(() => {
    mockedApi.mockReset();
  });

  it("loads and renders documents", async () => {
    mockedApi.mockResolvedValueOnce([
      {
        id: "doc-1",
        workspace_id: "workspace-1",
        title: "Atlas Brief",
        status: "ready",
        description: "Launch plan",
        created_by: "user-1",
        created_at: "2026-07-20T00:00:00Z",
        updated_at: "2026-07-20T00:00:00Z",
      },
    ]);

    render(<DocumentExplorer />);

    expect(await screen.findByText("Atlas Brief")).toBeInTheDocument();
    expect(screen.getByText("ready")).toBeInTheDocument();
  });

  it("uploads a selected file and shows loading state", async () => {
    mockedApi
      .mockResolvedValueOnce([])
      .mockResolvedValueOnce({})
      .mockResolvedValueOnce([])
      .mockResolvedValueOnce([]);

    render(<DocumentExplorer />);

    const fileInput = screen.getByLabelText("Document file");
    await userEvent.upload(fileInput, new File(["hello"], "notes.txt", { type: "text/plain" }));
    const form = screen.getByRole("button", { name: "Upload" }).closest("form");
    expect(form).not.toBeNull();
    fireEvent.submit(form as HTMLFormElement);

    await waitFor(() => expect(mockedApi).toHaveBeenCalledWith("/documents", expect.any(Object)));
  });

  it("renders upload errors", async () => {
    mockedApi.mockResolvedValueOnce([]).mockRejectedValueOnce(new Error("Unsupported MIME type"));

    render(<DocumentExplorer />);

    const fileInput = screen.getByLabelText("Document file");
    await userEvent.upload(fileInput, new File(["%PDF"], "notes.txt", { type: "application/pdf" }));
    const form = screen.getByRole("button", { name: "Upload" }).closest("form");
    expect(form).not.toBeNull();
    fireEvent.submit(form as HTMLFormElement);

    expect(await screen.findByText("Unsupported MIME type")).toBeInTheDocument();
  });
});
