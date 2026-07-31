# Ollama generation security

The outbound endpoint validator rejects HTTPS/public URLs, credentials, paths, queries,
fragments, link-local addresses, and non-allowlisted hostnames. DNS answers are checked
again immediately before a request and all answers must be private or loopback. HTTP
redirects are disabled.

The model receives only bounded authorized evidence and safe document identifiers. It
receives no secrets, storage paths, vectors, tenant names, database objects, tools, or
network capability. Instruction-like document text is treated as data. Structured output
has no reasoning field. Raw prompts, raw responses, private answer text, and evidence spans
are excluded from logs and metrics.

Post-generation verification is fail-closed. The application preserves authorization,
selected-document scope, conflict decisions, canonical primary state, final confidence,
and server-side citation authority.

Live prompt-injection resistance, tenant isolation, selected-document isolation,
unknown-ID rejection, reasoning exclusion, endpoint/model allowlists, and deterministic
fallback passed. The benchmark stores aggregate metrics only and contains no raw
candidates, prompts, document content, credentials, tenant identifiers, or model paths.

V2 further removes model authority over required components and critical wording.
Only request-scoped component, fact, and evidence mappings survive normalization;
server-controlled rendering and citations are authoritative. Unknown IDs fail closed
in the verifier, prompt-injection sentences are excluded from planning, no tools or
retrieval are exposed to Ollama, redirects remain disabled, DNS/private-endpoint and
model allowlists remain enforced, and raw candidates remain ephemeral. The sealed v2
holdout passed prompt injection, selected-document isolation, tenant isolation,
knowledge absence, retrieval failure, conflict handling, and safe fallback at 1.0000.
