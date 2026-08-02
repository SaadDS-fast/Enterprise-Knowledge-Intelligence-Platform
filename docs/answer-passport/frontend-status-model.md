# Passport frontend status model

Frontend wording preserves backend semantics:

| Backend status | Presentation | Export implication |
|---|---|---|
| `VERIFIED` | Verified with current trust | Backend policy applies |
| `TRUST_UNAVAILABLE` | Current trust unavailable | Never described as corruption |
| `EXPIRED`, `STALE`, `REVIEW_REQUIRED` | Review required | Editor+ when backend permits |
| `KEY_RETIRED` | Signing key retired | Not described as revoked |
| `KEY_REVOKED` | Signing key revoked | Admin/owner forensic policy |
| `ARTIFACT_INVALID` | Blocking integrity error | No download |
| unknown or missing | Verification unavailable | Fail closed |

Color is supplementary; every state has text. The UI never combines these values into a universal
truth or correctness claim and never performs browser cryptographic verification.

Integrity has precedence over revocation, which has precedence over expiry or staleness. A refresh
removes the previous presentation until the backend returns the current compound status.
