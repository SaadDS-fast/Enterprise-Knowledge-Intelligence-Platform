import { api, apiBinary, apiBoundedJson, APIError } from "@/lib/api";

export const PASSPORT_MEDIA_TYPE = "application/vnd.ekip.answer-passport+zip";
export const MAX_PASSPORT_DOWNLOAD_BYTES = 6 * 1024 * 1024;

export type PassportMetadata = {
  passport_id: string;
  schema_version: string;
  issued_at: string;
  expires_at: string | null;
  signer_key_id: string;
  issuer_id: string;
  artifact_integrity: string;
  status: string;
  freshness: string;
  key_lifecycle_status: string;
  trust_bundle_version: number | null;
  trust_bundle_checksum: string | null;
  export_available: boolean;
};

export type TrustBundleResponse = {
  bundle: string;
  verifier_bundle: string;
  signature: string | null;
  trust_mode: string;
  bundle_version: number | null;
  bundle_checksum: string | null;
  bootstrap_notice: string;
};

export type PassportPresentation = {
  label: string;
  tone: "positive" | "review" | "blocked" | "neutral";
  blocking: boolean;
};

const statusPresentation: Record<string, PassportPresentation> = {
  VERIFIED: { label: "Verified with current trust", tone: "positive", blocking: false },
  VERIFIED_WITHOUT_CURRENT_TRUST: {
    label: "Verified without current trust",
    tone: "review",
    blocking: false,
  },
  REVIEW_REQUIRED: { label: "Review required", tone: "review", blocking: false },
  EXPIRED: { label: "Expired — review required", tone: "review", blocking: false },
  STALE: { label: "Stale — review required", tone: "review", blocking: false },
  KEY_RETIRED: { label: "Signing key retired", tone: "review", blocking: false },
  KEY_REVOKED: { label: "Signing key revoked", tone: "blocked", blocking: false },
  TRUST_UNAVAILABLE: { label: "Current trust unavailable", tone: "neutral", blocking: false },
  ARTIFACT_INVALID: { label: "Artifact integrity invalid", tone: "blocked", blocking: true },
};

export function presentPassportStatus(status: string): PassportPresentation {
  return (
    statusPresentation[status] ?? {
      label: "Verification status unavailable",
      tone: "neutral",
      blocking: true,
    }
  );
}

export function abbreviateIdentifier(value: string): string {
  return value.length <= 22 ? value : `${value.slice(0, 10)}…${value.slice(-8)}`;
}

export function safePassportFilename(passportId: string): string {
  const value = passportId.replace(/^urn:uuid:/, "").toLowerCase();
  if (!/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/.test(value)) {
    throw new APIError(400, "The passport identifier is invalid.");
  }
  return `answer-passport-${value}.zip`;
}

export function safePassportMessage(error: unknown): string {
  if (!(error instanceof APIError)) return "The passport service is unavailable.";
  if (error.status === 401) return "Please sign in to view this verification record.";
  if (error.status === 403) return "You do not have permission for this passport action.";
  if (error.status === 404) return "This verification record is unavailable.";
  if (error.status === 413) return "The download exceeds the safety limit.";
  if (error.message === "The download format is invalid.") return error.message;
  return "The passport service is unavailable.";
}

export function getPassportMetadata(
  passportId: string,
  signal?: AbortSignal,
): Promise<PassportMetadata> {
  return api<PassportMetadata>(`/answer-passports/${encodeURIComponent(passportId)}`, { signal });
}

export function getPassportExport(passportId: string, signal?: AbortSignal): Promise<Blob> {
  return apiBinary(
    `/answer-passports/${encodeURIComponent(passportId)}/export`,
    PASSPORT_MEDIA_TYPE,
    MAX_PASSPORT_DOWNLOAD_BYTES,
    signal,
  );
}

export function getCurrentTrustBundle(signal?: AbortSignal): Promise<TrustBundleResponse> {
  return apiBoundedJson<TrustBundleResponse>(
    "/passport-trust-bundles/current",
    5 * 1024 * 1024,
    signal,
  );
}

export function downloadTransient(blob: Blob, filename: string): () => void {
  const objectUrl = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = objectUrl;
  anchor.download = filename;
  anchor.rel = "noopener";
  anchor.hidden = true;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();

  // Chromium must consume the click before the object URL is revoked.
  let revoked = false;
  const cleanup = () => {
    if (revoked) return;
    revoked = true;
    URL.revokeObjectURL(objectUrl);
  };
  window.setTimeout(cleanup, 0);
  return cleanup;
}
