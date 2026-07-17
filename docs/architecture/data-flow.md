# Data Flow

## Upload path

1. Authenticate the user and resolve organization/workspace context.
2. Validate filename, extension, MIME type, size, and authorization.
3. Store the file under a generated object key in quarantine.
4. Create an idempotent ingestion job and return HTTP 202.
5. A worker scans, parses, normalizes, chunks, embeds, and indexes the document version.
6. The worker publishes status and audit events.

## Query path

1. Authenticate and resolve tenant scope.
2. Normalize and validate the query.
3. Run BM25 and vector retrieval with mandatory tenant and permission filters.
4. Fuse and rerank results.
5. Verify evidence sufficiency.
6. Generate a cited answer, retry retrieval, ask for clarification, or abstain.
7. Redact output where required and write an audit event.
