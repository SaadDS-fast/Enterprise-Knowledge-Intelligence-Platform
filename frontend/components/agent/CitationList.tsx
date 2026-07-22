import { safeExternalHref } from "@/lib/safe-url";
import type { AgentCitation } from "@/types";

function label(citation: AgentCitation, index: number): string {
  return citation.citation_label ?? citation.external_source_label ?? `S${index + 1}`;
}

export default function CitationList({ citations }: { citations: AgentCitation[] }) {
  if (!citations.length) return <div className="empty">No citations were returned.</div>;
  return (
    <div className="citation-list" data-testid="agent-citations">
      {citations.map((citation, index) => {
        const href = safeExternalHref(citation.canonical_url);
        const isExternal = Boolean(citation.provider || href);
        return (
          <details className="citation" key={`${label(citation, index)}-${index}`}>
            <summary>
              <strong>[{label(citation, index)}]</strong>
              <span>{isExternal ? citation.provider ?? "External source" : citation.document_title ?? "Internal document"}</span>
            </summary>
            <dl>
              {citation.document_title ? (
                <>
                  <dt>Document</dt>
                  <dd>{citation.document_title}</dd>
                </>
              ) : null}
              {citation.document_version_id ? (
                <>
                  <dt>Version</dt>
                  <dd className="wrap">{citation.document_version_id}</dd>
                </>
              ) : null}
              {citation.section || citation.page ? (
                <>
                  <dt>Location</dt>
                  <dd>{citation.section ?? `Page ${citation.page}`}</dd>
                </>
              ) : null}
              {citation.chunk_id ? (
                <>
                  <dt>Chunk</dt>
                  <dd className="wrap">{citation.chunk_id}</dd>
                </>
              ) : null}
              {citation.title ? (
                <>
                  <dt>Title</dt>
                  <dd>{citation.title}</dd>
                </>
              ) : null}
              {href ? (
                <>
                  <dt>Link</dt>
                  <dd>
                    <a href={href} target="_blank" rel="noopener noreferrer">
                      Open external source
                    </a>
                  </dd>
                </>
              ) : null}
              {citation.retrieval_timestamp ? (
                <>
                  <dt>Retrieved</dt>
                  <dd>{new Date(citation.retrieval_timestamp).toLocaleString()}</dd>
                </>
              ) : null}
              {citation.excerpt ? (
                <>
                  <dt>Excerpt</dt>
                  <dd>
                    <p>{citation.excerpt}</p>
                  </dd>
                </>
              ) : null}
            </dl>
          </details>
        );
      })}
    </div>
  );
}
