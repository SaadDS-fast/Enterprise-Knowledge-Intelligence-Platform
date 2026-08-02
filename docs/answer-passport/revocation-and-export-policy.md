# Revocation and export policy

Artifact integrity, signature verification, issuance validity, lifecycle/revocation, passport
freshness, and trust availability are separate. Integrity failure denies output. Revocation
dominates freshness and is never described as signature corruption.

Precedence is corruption/cryptographic invalidity first, then revocation, then expiry/freshness,
then retirement. Trust unavailability is explicit and is not rewritten as signature corruption.

Editors may export valid, retired, stale, and expired artifacts for review. The manifest states the
condition. Revoked forensic/compliance export requires admin or owner and records `KEY_REVOKED`.
No condition triggers retrieval, re-answering, repair, or replacement.
