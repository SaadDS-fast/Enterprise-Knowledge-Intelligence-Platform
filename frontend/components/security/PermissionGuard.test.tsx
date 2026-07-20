import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import PermissionGuard from "./PermissionGuard";

vi.mock("@/lib/auth", () => ({
  isAuthenticated: vi.fn(),
}));

import { isAuthenticated } from "@/lib/auth";

const mockedIsAuthenticated = vi.mocked(isAuthenticated);

describe("PermissionGuard", () => {
  it("renders protected content for authenticated users", () => {
    mockedIsAuthenticated.mockReturnValue(true);

    render(
      <PermissionGuard fallback={<p>Denied</p>}>
        <p>Protected workspace</p>
      </PermissionGuard>,
    );

    expect(screen.getByText("Protected workspace")).toBeInTheDocument();
    expect(screen.queryByText("Denied")).not.toBeInTheDocument();
  });

  it("renders fallback for unauthenticated users", () => {
    mockedIsAuthenticated.mockReturnValue(false);

    render(
      <PermissionGuard fallback={<p>Denied</p>}>
        <p>Protected workspace</p>
      </PermissionGuard>,
    );

    expect(screen.getByText("Denied")).toBeInTheDocument();
    expect(screen.queryByText("Protected workspace")).not.toBeInTheDocument();
  });
});
