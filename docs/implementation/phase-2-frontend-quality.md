# Phase 2 Frontend Quality Baseline

Implemented on 2026-07-20.

## Changes

- Replaced the frontend no-op lint script with real ESLint flat configuration.
- Added Vitest, React Testing Library, `user-event`, `jest-dom`, and jsdom.
- Added component tests for:
  - login form submission, registration-mode switching, and authentication errors
  - protected-route rendering through `PermissionGuard`
  - document list rendering, upload submission, and upload error state
  - search loading/error handling and evidence rendering
  - citation/evidence empty state and scored citation display
- Added an accessible label for the document upload file input.

## Validation

Commands run from `frontend/`:

```bash
rm -rf node_modules .next
npm ci
npm run lint
npm run typecheck
npm run test
npm run build
npm audit --omit=dev
```

Results:

- `npm ci`: passed, 249 packages installed from lockfile.
- `npm run lint`: passed with 0 errors and 1 warning for the standard Next.js `metadata` export in `app/layout.tsx`.
- `npm run typecheck`: passed.
- `npm run test`: passed, 5 files and 12 tests.
- `npm run build`: passed.
- `npm audit --omit=dev`: passed, 0 vulnerabilities.

## Remaining Frontend Gaps

- Browser automation is still not implemented.
- The frontend still needs broader enterprise workflow coverage: document details, versions, admin views, streaming, report export, evaluation comparisons, and audit-log views.
