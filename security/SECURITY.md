# Security Policy

## Reporting

Report vulnerabilities privately. Do not open a public issue containing exploit details, credentials, private documents, or personal data.

## Baseline controls

- Least-privilege authorization and deny-by-default policies.
- Organization and workspace isolation in database and vector queries.
- File type, MIME, size, archive, malware, and path validation.
- Quarantine before indexing.
- Argon2 password hashing when local credentials are used.
- Short-lived access tokens and secure refresh-token handling.
- Secure, HTTP-only, SameSite cookies for browser sessions.
- Outbound request allowlists and SSRF protection.
- Prompt-injection defenses and tool allowlists.
- Audit events for sensitive actions.
- Redaction of secrets and personal data from logs.
- Dependency, secret, container, and infrastructure scanning.
- Encrypted transport, storage, and backups in production.
