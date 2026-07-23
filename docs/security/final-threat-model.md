# Final Threat Model

Primary threats reviewed for v0.2.0 release preparation:

- authentication bypass;
- IDOR on documents, agent runs, research jobs, and artifacts;
- cross-tenant or cross-workspace retrieval leakage;
- prompt and tool injection through uploaded or external text;
- SSRF, redirect SSRF, cloud metadata access, and unsafe schemes;
- oversized request bodies and uploads;
- malicious MIME types and unsafe filenames;
- stale or leaked signed artifact URLs;
- hidden reasoning exposure;
- metric, log, trace, or audit label cardinality leaks;
- retry duplication and artifact duplication after outages;
- default feature flags accidentally enabling agent/research/external access.

Mitigations are implemented through scoped dependencies, validated document scope, typed tools,
allowlisted providers, outbound request validation, safe error payloads, low-cardinality
observability, bounded retries, idempotency keys, and disabled-by-default feature flags.

Remaining limitations are documented in `KNOWN_LIMITATIONS.md`; this threat model is not a
third-party penetration test or WCAG certification.
