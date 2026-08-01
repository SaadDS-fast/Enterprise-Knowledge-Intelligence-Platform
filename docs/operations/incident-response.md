# Incident response

Classify unauthorized access, isolation failure, SSRF bypass, arbitrary file access,
unsupported supported claims, corruption, or unrecoverable migration failure as critical.
Contain affected services, preserve sanitized audit evidence, rotate exposed credentials,
and restore from a verified backup. Do not copy private payloads into tickets or chat.

For availability incidents, confirm safe canonical state and fallback before recovery.
Validate tenant, citation, and object authorization after service restoration. Record root
cause, affected window, remediation, and prevention without retaining raw prompts or
provider output.

Immediate actions:

1. Disable `AGENTIC_RAG_ENABLED`, `AGENT_RESEARCH_ENABLED`, generation, and external-provider
   flags when their boundary may be involved.
2. Preserve sanitized logs, metrics, request IDs, run IDs, and job IDs without copying
   document contents or signed URLs.
3. Check tenant/workspace scope on affected documents, runs, jobs, citations, and artifacts.
4. Confirm whether retries created duplicate artifacts or invalid state transitions.
5. Rotate secrets if token or credential exposure is suspected.
6. Document root cause and remediation before re-enabling optional features.
