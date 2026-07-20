import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import Login from "./page";

const push = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push }),
}));

vi.mock("@/lib/api", () => ({
  api: vi.fn(),
}));

vi.mock("@/lib/auth", () => ({
  saveSession: vi.fn(),
}));

import { api } from "@/lib/api";
import { saveSession } from "@/lib/auth";

const mockedApi = vi.mocked(api);
const mockedSaveSession = vi.mocked(saveSession);

describe("Login page", () => {
  beforeEach(() => {
    mockedApi.mockReset();
    mockedSaveSession.mockReset();
    push.mockReset();
  });

  it("submits login and stores the returned session", async () => {
    mockedApi.mockResolvedValueOnce({
      access_token: "token-1",
      token_type: "bearer",
      expires_in: 1800,
      workspace_id: "workspace-1",
      user: {
        id: "user-1",
        email: "ada@example.com",
        full_name: "Ada Lovelace",
        is_active: true,
        is_superuser: false,
        created_at: "2026-07-20T00:00:00Z",
      },
    });

    render(<Login />);

    await userEvent.type(screen.getByPlaceholderText("Email"), "ada@example.com");
    await userEvent.type(screen.getByPlaceholderText("Password (12+ characters)"), "long-password");
    fireEvent.click(screen.getByRole("button", { name: "Sign in" }));

    await waitFor(() => expect(mockedSaveSession).toHaveBeenCalledWith("token-1", "workspace-1"));
    expect(push).toHaveBeenCalledWith("/dashboard");
  });

  it("switches to registration mode", async () => {
    render(<Login />);

    await userEvent.click(screen.getByRole("button", { name: "Need an account? Register" }));

    expect(screen.getByPlaceholderText("Full name")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("Organization name")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Create account" })).toBeInTheDocument();
  });

  it("renders authentication errors", async () => {
    mockedApi.mockRejectedValueOnce(new Error("Invalid credentials"));

    render(<Login />);

    await userEvent.type(screen.getByPlaceholderText("Email"), "ada@example.com");
    await userEvent.type(screen.getByPlaceholderText("Password (12+ characters)"), "wrong-password");
    fireEvent.click(screen.getByRole("button", { name: "Sign in" }));

    expect(await screen.findByText("Invalid credentials")).toBeInTheDocument();
  });
});
