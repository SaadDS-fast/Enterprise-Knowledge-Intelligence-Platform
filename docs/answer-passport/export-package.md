# Answer Passport export package

The uncompressed bounded ZIP has fixed entries: `passport.json`, `passport.sig`,
`export-manifest.json`, and optionally public-only `trust-bundle.json`. The export manifest lists
length and lowercase SHA-256, lifecycle/freshness status, export time, trust inclusion, and an
independent-trust-channel warning.

No evidence snapshot/text, document, answer, prompt, log, ACL, database ID, private key, or model is
included. A UUID-derived filename and `no-store`, `no-cache`, and `nosniff` headers prevent caller
filename/header reflection; caller paths, symlinks, and compression are absent.
