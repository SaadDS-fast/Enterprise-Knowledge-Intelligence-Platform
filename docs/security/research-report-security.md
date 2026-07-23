# Research Report Security

Research reports inherit agent authorization and add artifact-specific controls.

- Report creation requires authenticated workspace membership.
- Optional `document_ids` must belong to the caller's workspace.
- Idempotency is scoped by tenant, workspace, user, question, document scope, formats, and source policy.
- Active job limits are enforced per user, per workspace, and globally for queued jobs.
- Artifact listing and downloads recheck tenant, workspace, job, artifact, format, and signature.
- API artifact metadata does not expose object keys or raw signature values.
- Generated markdown/PDF/DOCX files are user artifacts and are not committed to the repository.
- Retrieved text remains untrusted evidence and cannot authorize tools, change budgets, enable
  external sources, alter tenant scope, or override policy.
