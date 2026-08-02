# Passport persistence model

`answer_passports` stores exact manifest bytes, detached signature, protocol ID, opaque organization
and workspace IDs, issuer/key/schema/profile identifiers, three SHA-256 checksums, signed scope and
answer digests, issuance/expiry, safe correlation ID, idempotency key, creator ID, creation time, and
immutable version 1. Constraints enforce profile, sizes, hashes, uniqueness, times, and foreign keys.
PostgreSQL INSERT additionally verifies that `workspaces.organization_id` matches the supplied
organization; direct UPDATE and DELETE are rejected by a separately named immutable-row trigger.

It excludes answer/evidence text, prompts, reasoning, candidates/scores, ACL lists, tokens,
credentials, embeddings, provider secrets, and private signing material. Key revocation never edits
history. Retention or erasure needs a future explicitly authorized lifecycle design.
