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
