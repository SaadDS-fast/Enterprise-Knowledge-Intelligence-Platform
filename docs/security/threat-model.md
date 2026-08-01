# Enterprise threat model

Protected assets are tenant documents, objects, chunks, citations, identities, credentials,
audit records, and model inputs. Trust boundaries exist at browser/API, upload/parser,
API/database, queue/worker, object storage, retrieval, and optional local-model calls.

Primary threats are IDOR and cross-tenant inference, malicious files, prompt injection,
SSRF/DNS rebinding, unsafe redirects, model/evidence forgery, secret leakage, retry storms,
and stale data after reprocess. Controls are explicit workspace filtering, role checks,
MIME/magic/size validation, bounded extraction, outbound allowlists with IP revalidation,
server-owned evidence IDs/citations/state, strict candidate verification, idempotency,
timeouts/circuit breaking, CSP/security headers, and sanitized observability.

Cloud infrastructure and cloud inference are outside this release candidate's validated
scope.

Audit records cover authentication success/failure, document lifecycle, Search and selected
scope, Agent/Research creation or denial, cross-tenant/role denial, and deletion. Records use
safe action/outcome categories plus actor, workspace, timestamp, and request ID. Document
bodies, queries, prompts, evidence packets, model output, credentials, and reasoning are
explicitly excluded.
