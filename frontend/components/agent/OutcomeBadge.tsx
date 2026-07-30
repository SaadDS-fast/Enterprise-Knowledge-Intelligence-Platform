const outcomeLabels: Record<string, string> = {
  SUPPORTED: "Answer supported",
  SUPPORTED_COMPOSITE: "Answer supported by multiple sources",
  RETRIEVAL_FAILURE: "Retrieval could not be completed",
  AMBIGUOUS_QUERY: "Query needs clarification",
  LOW_QUALITY_SOURCE: "Source quality is insufficient",
  PROCESSING_FAILED: "Response could not be completed",
  CANCELLED: "Request cancelled",
  ANSWER_SUPPORTED: "Answer supported",
  ANSWER_PARTIALLY_SUPPORTED: "Partially supported",
  CONFLICTING_EVIDENCE: "Sources contain conflicting information",
  INSUFFICIENT_EVIDENCE: "Insufficient evidence",
  KNOWLEDGE_ABSENT: "Information not found in selected documents",
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
