# Demo Script

Use this for a 3-5 minute walkthrough. Keep the demo local and avoid claiming hosted deployment or CI unless those are added later.

## Preparation

Start the local Docker stack:

```bash
docker compose --profile observability up -d --build
```

For agent/research UI demos, enable the corresponding backend and frontend flags through `.env` or an explicit Compose environment before rebuilding. Keep external providers disabled unless you are intentionally demonstrating SearXNG.

Open:

- Frontend: `http://localhost:3000`
- API docs: `http://localhost:8000/docs`
- Grafana: `http://localhost:3001`

## 3-5 Minute Sequence

### 1. Login And Workspace

Show the login or registration flow. Explain that users operate inside an organization and workspace, and that every document, search, agent run, and research artifact is scoped.

Suggested narration:

"This is a local-first multi-tenant document intelligence platform. The important thing is not just answering questions; it is answering from the right workspace and refusing unsafe evidence."

### 2. Upload A Document

Go to `/documents` and upload a small text, PDF, or DOCX file. Show the ingestion status completing.

Mention:

- MIME validation;
- background-compatible ingestion;
- chunking and retrieval indexing;
- PostgreSQL/Redis/MinIO/Celery in Docker mode.

### 3. Standard Search

Go to `/search` and ask a question answered by the uploaded document.

Point out:

- answer text;
- citations/evidence;
- retrieval diagnosis;
- the stable non-agentic endpoint: `POST /api/v1/search`.

### 4. Controlled Agent Query

Go to `/agent` with agentic flags enabled and ask a document-specific question.

Explain:

- deterministic planning;
- typed internal tools;
- scoped internal retrieval;
- evidence verification;
- citation validation;
- safe final response without hidden reasoning.

### 5. Evidence And Citations

Open the evidence/citation section. Show that the answer is tied to document evidence rather than unsupported model text.

Suggested narration:

"The agent cannot just invent a citation label. Citations are checked against retained evidence before the answer is returned."

### 6. Conflict Or Knowledge Absence

Ask a question the uploaded document cannot answer, or use a document fixture that contains a conflict.

Show:

- abstention or conflict response;
- `retrieval_diagnosis`;
- distinction between knowledge absence and retrieval failure.

### 7. Research Report

Go to `/agent/research`. Submit a concise research-report question against the uploaded document.

Show:

- asynchronous job creation;
- polling;
- stages/progress;
- cancellation availability for cancellable states.

### 8. PDF/DOCX Download

Open the completed research job and show artifact metadata. Download PDF or DOCX.

Mention:

- scoped object keys;
- short-lived signed download parameters;
- markdown/PDF/DOCX export;
- idempotency and duplicate-artifact protection.

### 9. Observability Dashboard

Open Grafana at `http://localhost:3001` and show the `EKIP Agentic Runtime` dashboard.

Mention:

- Prometheus backend and worker targets;
- agent and research metrics;
- low-cardinality labels;
- OpenTelemetry collector support.

## Closing Line

"The project is designed to show the difference between a chatbot over documents and a controlled, auditable document-intelligence runtime that can be evaluated safely."
