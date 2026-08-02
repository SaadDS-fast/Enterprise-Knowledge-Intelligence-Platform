# Passport frontend export flow

Export begins with one explicit user action. The authenticated server endpoint performs tenant,
role, integrity, lifecycle, and forensic-policy checks before sending bytes. The client requires
`application/vnd.ekip.answer-passport+zip`, rejects declared or actual responses above 6 MiB,
ignores `Content-Disposition`, and derives `answer-passport-<uuid>.zip` from the validated protocol
ID. It creates one object URL, clicks once, and revokes the URL immediately.

The ZIP is never unpacked, rendered, logged, sent to analytics, or persisted in Web Storage,
IndexedDB, a service worker, or application state beyond the transient Blob. Authorization and
integrity failures produce bounded neutral messages and are not retried automatically.

The separate trust action downloads only the public Phase 1 verifier projection as
`answer-passport-trust-bundle.json`; no issuer parameter or key selection is accepted.
