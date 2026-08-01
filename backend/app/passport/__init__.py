"""Pure cryptographic core for Verifiable Answer Passports.

This package intentionally has no dependencies on retrieval, generation, persistence, APIs, or
network clients. Phase 1 accepts prebuilt passport manifests; production issuance is out of scope.
"""

from app.passport.canonical import canonicalize
from app.passport.hashing import content_digest
from app.passport.jws import sign_detached, verify_detached
from app.passport.verifier import VerificationResult, verify_passport

__all__ = [
    "VerificationResult",
    "canonicalize",
    "content_digest",
    "sign_detached",
    "verify_detached",
    "verify_passport",
]
