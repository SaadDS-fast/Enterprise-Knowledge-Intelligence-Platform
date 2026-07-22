import type { AgentClaim } from "@/types";

export default function ClaimStatus({ claims }: { claims: AgentClaim[] }) {
  if (!claims.length) return <div className="empty">No claim verification details were returned.</div>;
  return (
    <div className="evidence-list">
      {claims.map((claim, index) => (
        <article className="evidence" key={`${claim.claim_text}-${index}`}>
          <header>
            <strong>{claim.verification_status.replaceAll("_", " ")}</strong>
            {typeof claim.support_score === "number" ? (
              <span>{Math.round(claim.support_score * 100)}%</span>
            ) : null}
          </header>
          <p>{claim.claim_text}</p>
        </article>
      ))}
    </div>
  );
}
