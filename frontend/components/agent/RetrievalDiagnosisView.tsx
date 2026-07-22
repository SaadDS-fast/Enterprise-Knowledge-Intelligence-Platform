import type { RetrievalDiagnosis } from "@/types";

const diagnosisLabels: Record<string, string> = {
  SUFFICIENT_EVIDENCE: "Evidence found directly",
  RETRIEVAL_FAILURE_RECOVERED: "Evidence found after retry",
  RETRIEVAL_FAILURE_UNRESOLVED: "Retrieval unresolved",
  KNOWLEDGE_ABSENT: "Knowledge absent",
  PARTIAL_EVIDENCE: "Partial evidence",
  CONFLICTING_EVIDENCE: "Conflicting evidence",
  AMBIGUOUS_QUERY: "Clarification required",
};

export default function RetrievalDiagnosisView({
  diagnosis,
}: {
  diagnosis?: Partial<RetrievalDiagnosis> | null;
}) {
  if (!diagnosis || !diagnosis.status) {
    return <div className="diagnosis">No retrieval diagnosis was returned.</div>;
  }
  const score =
    typeof diagnosis.final_support_score === "number"
      ? `${Math.round(diagnosis.final_support_score * 100)}% support`
      : "support unavailable";
  return (
    <div className="diagnosis" data-testid="agent-retrieval-diagnosis">
      <strong>{diagnosisLabels[diagnosis.status] ?? "Unknown retrieval state"}</strong>
      <span>
        {diagnosis.retry_performed ? "Retry attempted" : "Initial retrieval only"} · {score}
      </span>
      {diagnosis.reason_code ? <small>{diagnosis.reason_code}</small> : null}
    </div>
  );
}
