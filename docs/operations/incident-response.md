# Incident Response

Immediate actions:

1. Disable `AGENTIC_RAG_ENABLED`, `AGENT_RESEARCH_ENABLED`, and external-provider flags.
2. Preserve logs, metrics, request IDs, run IDs, and job IDs without copying document contents or
   signed URLs.
3. Check tenant/workspace scope on affected documents, runs, jobs, and artifacts.
4. Confirm whether retries created duplicate artifacts or corrupt state transitions.
5. Rotate secrets if token or credential exposure is suspected.
6. Document root cause and remediation before re-enabling agentic features.
