# Document extraction and chunking v3

Phase 1 replaces flattened ingestion input with deterministic structural extraction. It does
not add an LLM, OCR engine, semantic model, reranker, orchestration framework, or cloud
infrastructure.

## Pipeline

The runtime flow is:

`upload validation → malware scan → quarantine object → parser → structural blocks → safe
normalization → extraction-quality assessment → chunking v3 quality gates → deterministic
embedding/index → source object → lifecycle state`

Every accepted chunk records `extraction_version`, `normalization_version`,
`chunking_version`, and `indexing_version`, plus the document/version IDs, safe source
filename, MIME type, source order, extraction quality, and available page, heading, section,
question, table, row, and line context. The latest versions are defined in
`app.ingestion.versions`.

Documents without all latest version markers are returned by the Documents API as
`reprocessing_recommended`; old chunks are never silently represented as current.

## Extraction behavior

- PDF uses layout-aware native text extraction when available, keeps page numbers, removes
  only repeated edge lines found on at least 60% of three or more pages, and emits a
  reading-order warning for suspiciously long lines. Empty/image pages contribute to the
  scanned-document likelihood.
- DOCX preserves paragraph/table order where the installed `python-docx` supports
  `iter_inner_content`, headings and levels, list/caption styles, and table boundaries.
- Markdown/TXT preserve headings, labelled sections such as `Topic: Functions`, questions,
  lists, paragraphs, fenced code, Unicode equations, and punctuation.
- HTML removes executable, embedded, navigation, and hidden content and reads only inert
  title/article/main/body structure. It never executes markup.
- CSV emits bounded 25-row table groups with the header, table identifier, and row range.
- Source code records language, safe source filename, symbols, and line ranges. Python uses
  its AST so imports, classes, and functions do not collapse into one chunk; malformed and
  other supported languages use bounded line groups.

Normalization is NFC Unicode normalization plus conservative whitespace cleanup. It does not
rewrite factual values, equations, numbering, or punctuation.

## Quality and lifecycle

Quality signals are stored as document metadata, never as log content or Prometheus labels:
character count, printable ratio, replacement characters, duplicate-line ratio, empty pages,
page coverage, suspicious token fragmentation, average line length, equation/symbol count,
table count, scanned likelihood, and reading-order warnings.

Typed extraction outcomes are `GOOD`, `ACCEPTABLE`, `LOW_QUALITY`, `REQUIRES_OCR`, and
`FAILED`. Document lifecycle states exposed by the API are `ready`, `ready_with_warnings`,
`reprocessing_recommended`, `requires_ocr`, and `extraction_failed`. A document cannot become
ready without a usable chunk. Failures expose a sanitized category rather than parser text or
storage details.

## Safe reprocessing and inspection

`POST /api/v1/documents/{document_id}/reprocess` requires document-management permission and
resolves the document inside the active workspace. It reuses the original logical document
and uploaded version/object. An existing pending, retrying, dispatch-failed, or running job is
returned idempotently instead of dispatching another task. Chunk replacement occurs in one
database transaction, so failure rolls back rather than leaving a partial index; completed
jobs retain pipeline history.

Callers may send `Idempotency-Key`. Only its SHA-256 digest is retained. Replays with the same
key return the same active or completed job; a different key requests a new explicit
reprocessing run without creating another logical document or uploaded version.

`GET /api/v1/documents/{document_id}/structure` is workspace-scoped and returns only safe
structure metadata and a bounded normalized excerpt. It never returns embeddings, vectors,
storage keys, database internals, or another tenant's chunks.

## OCR limitation

No OCR engine is included in this phase. A PDF with high scanned likelihood and insufficient
meaningful native text is `REQUIRES_OCR`, produces no chunks, and cannot produce a search
answer. Mixed native/scanned PDFs can be `LOW_QUALITY` or `ACCEPTABLE` based on coverage and
warnings, making the limitation visible instead of falsely claiming successful understanding.
