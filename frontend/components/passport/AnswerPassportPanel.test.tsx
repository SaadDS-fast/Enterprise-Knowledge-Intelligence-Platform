import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import AnswerPassportPanel from "./AnswerPassportPanel";
import {
  getCurrentTrustBundle,
  getPassportExport,
  getPassportMetadata,
  presentPassportStatus,
} from "@/lib/passport";

vi.mock("@/lib/passport", async () => {
  const actual = await vi.importActual("@/lib/passport");
  return {
    ...actual,
    getPassportMetadata: vi.fn(),
    getPassportExport: vi.fn(),
    getCurrentTrustBundle: vi.fn(),
    downloadTransient: vi.fn(),
  };
});

const reference = {
  passport_id: "urn:uuid:00000000-0000-0000-0000-000000000042",
  schema_version: "vap-1" as const,
  metadata_available: true,
  export_available: true,
};

const metadata = {
  passport_id: reference.passport_id,
  schema_version: "vap-1",
  issued_at: "2026-08-02T12:00:00Z",
  expires_at: "2026-09-02T12:00:00Z",
  signer_key_id: "phase-four-public-signing-key-identifier",
  issuer_id: "opaque-issuer",
  artifact_integrity: "VALID",
  status: "VERIFIED",
  freshness: "CURRENT",
  key_lifecycle_status: "ACTIVE",
  trust_bundle_version: 3,
  trust_bundle_checksum: "checksum",
  export_available: true,
};

describe("AnswerPassportPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(getPassportMetadata).mockResolvedValue(metadata);
  });

  it("loads separate backend-computed assurance concepts on user request", async () => {
    render(<AnswerPassportPanel reference={reference} />);
    expect(screen.getByText(/signed verification record is available/i)).toBeInTheDocument();
    expect(getPassportMetadata).not.toHaveBeenCalled();

    fireEvent.click(screen.getByRole("button", { name: /view assurance details/i }));
    expect(await screen.findByText("Artifact integrity")).toBeInTheDocument();
    expect(screen.getByText("Verified with current trust")).toBeInTheDocument();
    expect(screen.getByText("Signing-key lifecycle")).toBeInTheDocument();
    expect(document.body.textContent).not.toMatch(/detached signature|raw manifest|private key/i);
  });

  it.each([
    ["EXPIRED", "Expired — review required"],
    ["STALE", "Stale — review required"],
    ["KEY_RETIRED", "Signing key retired"],
    ["KEY_REVOKED", "Signing key revoked"],
    ["TRUST_UNAVAILABLE", "Current trust unavailable"],
  ])("preserves the %s backend status", (status, label) => {
    expect(presentPassportStatus(status).label).toBe(label);
  });

  it("fails closed for unknown and invalid statuses", () => {
    expect(presentPassportStatus("FUTURE_UNKNOWN").blocking).toBe(true);
    expect(presentPassportStatus("ARTIFACT_INVALID").blocking).toBe(true);
  });

  it("renders role-aware export behavior without treating it as authorization", async () => {
    vi.mocked(getPassportMetadata).mockResolvedValue({ ...metadata, export_available: false });
    render(<AnswerPassportPanel reference={{ ...reference, export_available: false }} />);
    fireEvent.click(screen.getByRole("button", { name: /view assurance details/i }));
    expect(await screen.findByText(/current role cannot export/i)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /passport zip/i })).not.toBeInTheDocument();
  });

  it.each([
    [false, false],
    [true, true],
  ])("renders revoked forensic export only when backend allows it", async (allowed, visible) => {
    vi.mocked(getPassportMetadata).mockResolvedValue({
      ...metadata,
      status: "KEY_REVOKED",
      key_lifecycle_status: "REVOKED",
      export_available: allowed,
    });
    render(<AnswerPassportPanel reference={{ ...reference, export_available: allowed }} />);
    fireEvent.click(screen.getByRole("button", { name: /view assurance details/i }));
    await screen.findByText("Signing key revoked");
    expect(Boolean(screen.queryByRole("button", { name: /forensic export/i }))).toBe(visible);
    expect(screen.queryByText(/verified with current trust/i)).not.toBeInTheDocument();
  });

  it("downloads one opaque ZIP and exposes accurate offline guidance", async () => {
    vi.mocked(getPassportExport).mockResolvedValue(new Blob(["opaque"]));
    render(<AnswerPassportPanel reference={reference} />);
    fireEvent.click(screen.getByRole("button", { name: /view assurance details/i }));
    fireEvent.click(await screen.findByRole("button", { name: /download passport zip/i }));
    await waitFor(() => expect(getPassportExport).toHaveBeenCalledTimes(1));
    expect(screen.getByText(/Exit 0 means VERIFIED/i)).toBeInTheDocument();
    expect(screen.getByText(/Exit 2 means review required/i)).toBeInTheDocument();
    expect(screen.getByText(/does not re-answer/i)).toBeInTheDocument();
  });

  it("downloads only the public verifier bundle with the bootstrap warning", async () => {
    vi.mocked(getCurrentTrustBundle).mockResolvedValue({
      bundle: "lifecycle-public-data",
      verifier_bundle: "public-verifier-data",
      signature: null,
      trust_mode: "unsigned-development",
      bundle_version: 3,
      bundle_checksum: "checksum",
      bootstrap_notice: "notice",
    });
    render(<AnswerPassportPanel reference={reference} />);
    fireEvent.click(screen.getByRole("button", { name: /view assurance details/i }));
    fireEvent.click(
      await screen.findByRole("button", { name: /download public verification trust bundle/i }),
    );
    await waitFor(() => expect(getCurrentTrustBundle).toHaveBeenCalledTimes(1));
    expect(screen.getByText(/does not by itself establish initial trust/i)).toBeInTheDocument();
  });

  it("shows a neutral unavailable state without raw backend errors", async () => {
    vi.mocked(getPassportMetadata).mockRejectedValue(new Error("SQL secret stack trace"));
    render(<AnswerPassportPanel reference={reference} />);
    fireEvent.click(screen.getByRole("button", { name: /view assurance details/i }));
    expect(await screen.findByText("The passport service is unavailable.")).toBeInTheDocument();
    expect(document.body.textContent).not.toContain("SQL secret stack trace");
  });
});
