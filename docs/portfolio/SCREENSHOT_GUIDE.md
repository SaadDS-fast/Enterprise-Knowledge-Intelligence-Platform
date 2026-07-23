# Screenshot Guide

Store screenshots under `docs/portfolio/screenshots/` when they are captured. Do not commit private document text, real tenant names, credentials, signed URLs, or tokens.

## Required Screenshots

| # | Screenshot | Suggested Path | What To Show |
| ---: | --- | --- | --- |
| 1 | Landing/login | `docs/portfolio/screenshots/01-login.png` | Login or registration screen at `http://localhost:3000/login` |
| 2 | Document upload | `docs/portfolio/screenshots/02-document-upload.png` | `/documents` with an upload in progress or completed ingestion status |
| 3 | Search result | `docs/portfolio/screenshots/03-search-result.png` | `/search` showing a grounded answer and retrieval diagnosis |
| 4 | Agent workspace | `docs/portfolio/screenshots/04-agent-workspace.png` | `/agent` with controlled agent query input and response |
| 5 | Citations/evidence | `docs/portfolio/screenshots/05-evidence-citations.png` | Evidence and citation panel for an agent or search response |
| 6 | Run timeline | `docs/portfolio/screenshots/06-run-timeline.png` | `/agent/runs/{run_id}` showing safe step summaries and tool statuses |
| 7 | Research job | `docs/portfolio/screenshots/07-research-job.png` | `/agent/research/{job_id}` showing progress or completed report |
| 8 | Report artifacts | `docs/portfolio/screenshots/08-report-artifacts.png` | Research artifact list with markdown/PDF/DOCX availability |
| 9 | Grafana dashboard | `docs/portfolio/screenshots/09-grafana-dashboard.png` | Grafana `EKIP Agentic Runtime` dashboard at `http://localhost:3001` |
| 10 | Architecture diagram | `docs/portfolio/screenshots/10-architecture.png` | README Mermaid high-level architecture rendered in GitHub or a Mermaid viewer |

## Capture Checklist

- Use only throwaway local users and documents.
- Keep browser zoom consistent, ideally 100%.
- Prefer a desktop viewport around 1440x900.
- Crop browser chrome only if it does not remove useful context.
- Redact any email address, token, signed URL, tenant name, or document text that should not be public.
- Do not include `.env`, terminal history with secrets, Docker volume paths, or local filesystem usernames if sharing publicly.

## Demo Data Suggestions

Use a small synthetic document that includes:

- one clear factual answer;
- one fact with a date or owner;
- one intentionally missing question topic;
- optionally one conflicting statement for the conflict demo.

Avoid real company documents or private personal information.
