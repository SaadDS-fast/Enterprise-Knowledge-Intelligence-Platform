import type { AgentConflict } from "@/types";

export default function ConflictCard({ conflict }: { conflict: AgentConflict }) {
  return (
    <article className="evidence warning-card" data-testid="conflict-card">
      <header>
        <strong>{conflict.field ?? "Evidence conflict"}</strong>
        <span>Needs review</span>
      </header>
      <p>{conflict.summary ?? conflict.claim ?? "The available evidence contains conflicting claims."}</p>
      {conflict.values?.length ? <small>{conflict.values.join(" / ")}</small> : null}
    </article>
  );
}
