# Release Security Checklist

- [ ] Secrets and private data are absent from the repository and build output.
- [ ] Tenant isolation tests pass.
- [ ] Authorization failures are covered by tests.
- [ ] Upload validation and quarantine controls pass.
- [ ] Dependency and container scans have no unresolved critical findings.
- [ ] Database migrations were reviewed and can be rolled back.
- [ ] Audit logging covers new privileged actions.
- [ ] Logs and traces redact credentials, tokens, and document contents.
- [ ] External requests use explicit allowlists, timeouts, and size limits.
- [ ] LLM tools use least privilege and structured arguments.
- [ ] Backups and recovery procedures were tested for production releases.
