export function safeExternalHref(value: string | null | undefined): string | null {
  if (!value) return null;
  try {
    const parsed = new URL(value);
    return parsed.protocol === "https:" || parsed.protocol === "http:" ? parsed.toString() : null;
  } catch {
    return null;
  }
}

export function isTerminalStatus(value: string | null | undefined): boolean {
  return ["completed", "failed", "cancelled"].includes((value ?? "").toLowerCase());
}

export function isCancellableResearchState(value: string | null | undefined): boolean {
  return [
    "PENDING",
    "AUTHORIZING",
    "PLANNING",
    "RETRIEVING",
    "RETRIEVAL_RETRY",
    "AGGREGATING_EVIDENCE",
    "VERIFYING_EVIDENCE",
    "WRITING",
    "VERIFYING_CITATIONS",
    "SAFETY_REVIEW",
    "EXPORTING",
  ].includes(value ?? "");
}
