# Passport frontend integration

The finalized Search lifecycle returns an optional minimal persisted reference. The browser does
not infer validity from that reference: opening the inline panel performs an authenticated,
workspace-scoped metadata GET and presents the backend status.

The panel separates artifact integrity, freshness, signing-key lifecycle, trust availability, and
export policy. Unknown status values use a neutral blocking state. Export visibility is a UX hint;
direct endpoint authorization remains mandatory and client-side bypass is denied by the backend.

ZIP and trust downloads reuse the authenticated transport. The ZIP is an opaque bounded binary
with an exact media type and UUID-derived local filename. The browser never unpacks, previews,
executes, caches, or stores it. Object URLs exist only for one user-initiated click and are revoked
in `finally`. Agent and Research remain unchanged and receive no synthetic passport state.
