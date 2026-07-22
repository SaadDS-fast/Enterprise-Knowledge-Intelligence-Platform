# Agent Query API

`POST /api/v1/agent/query` executes the controlled internal-document agent. It preserves the
existing `/api/v1/search` endpoint and reuses the validated retrieval, reranking, evidence
sufficiency, retrieval diagnosis, citations, retry, abstention, and safety review services.

The frontend sends:

```json
{
  "query": "What does the Atlas plan say?",
  "document_ids": ["doc-id"],
  "allow_external_sources": false
}
```

The response is structured for safe display:

```json
{
  "run_id": "agent-run-id",
  "status": "completed",
  "answer": "Supported answer text.",
  "abstained": false,
  "citations": [],
  "internal_evidence": [],
  "external_evidence": [],
  "retrieval_diagnosis": {},
  "tools_used": ["internal_search", "answer_synthesizer"],
  "safe_step_summaries": [],
  "total_duration_ms": 123,
  "fallback_used": false
}
```

Clients must not infer authorization from frontend state. The API validates tenant, workspace,
document scope, feature flags, and optional external-source permission on every request.
