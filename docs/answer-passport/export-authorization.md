# Passport export authorization

Existing authentication and workspace membership roles are authoritative. Metadata requires valid
membership. Export requires editor, admin, or owner; revoked forensic export requires admin or
owner. Client organization, scope, role, signer, and issuer values are never accepted.

Every lookup is server-scoped. Cross-tenant, cross-workspace, and nonexistent IDs return the same
not-found response. Disabled export and unavailable trust use safe service-unavailable errors.
