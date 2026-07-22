import { safeExternalHref } from "@/lib/safe-url";
import type { Evidence, ExternalSource } from "@/types";

export function InternalEvidenceCard({ item, index }: { item: Evidence; index: number }) {
  return (
    <article className="evidence" data-testid="internal-evidence-card">
      <header>
        <strong>
          [{index + 1}] {item.document_title}
        </strong>
        <span>{Math.round(item.score * 100)}%</span>
      </header>
      <p>{item.content}</p>
      <small className="wrap">Chunk {item.chunk_id}</small>
    </article>
  );
}

export function ExternalEvidenceCard({ item, index }: { item: ExternalSource; index: number }) {
  const href = safeExternalHref(item.canonical_url);
  return (
    <article className="evidence" data-testid="external-evidence-card">
      <header>
        <strong>
          [{index + 1}] {item.title}
        </strong>
        <span>{item.provider}</span>
      </header>
      <p>{item.excerpt}</p>
      {href ? (
        <a href={href} target="_blank" rel="noopener noreferrer">
          Open external source
        </a>
      ) : (
        <small>External link unavailable</small>
      )}
    </article>
  );
}
