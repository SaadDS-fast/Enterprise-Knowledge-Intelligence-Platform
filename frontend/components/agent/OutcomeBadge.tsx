const outcomeLabels: Record<string, string> = {
  ANSWER_SUPPORTED: "Answer supported",
  ANSWER_PARTIALLY_SUPPORTED: "Partially supported",
  CONFLICTING_EVIDENCE: "Conflicting evidence",
  INSUFFICIENT_EVIDENCE: "Insufficient evidence",
  KNOWLEDGE_ABSENT: "Knowledge absent",
  CLARIFICATION_REQUIRED: "Clarification required",
  SAFETY_BLOCKED: "Safety blocked",
  FAILED: "Failed",
};

function outcomeLabel(value: string | null | undefined): string {
  return outcomeLabels[value ?? ""] ?? "Unknown outcome";
}

export default function OutcomeBadge({ value }: { value: string | null | undefined }) {
  const normalized = (value ?? "unknown").toLowerCase().replaceAll("_", "-");
  return <span className={`badge outcome outcome-${normalized}`}>{outcomeLabel(value)}</span>;
}
