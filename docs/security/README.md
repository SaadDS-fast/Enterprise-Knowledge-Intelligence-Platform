# Security architecture

Security controls include Argon2 password hashing, signed JWTs, tenant-scoped database queries,
role checks, upload size/MIME/signature validation, path sanitization, prompt-injection scanning,
SSRF blocking, structured error responses, security headers, request IDs, audit-event models,
and dependency/container scanning workflows. Production still requires TLS, enterprise identity,
external malware scanning, centralized secrets, persistent distributed rate limiting, and review.
