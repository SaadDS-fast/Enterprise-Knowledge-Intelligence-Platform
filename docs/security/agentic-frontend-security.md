# Agentic Frontend Security

The frontend is a presentation layer for controlled agent outputs. It does not relax backend
authorization, expose hidden reasoning, persist signed URLs, or add web search.

Security controls:

- Agent and research navigation are hidden unless frontend feature flags are enabled.
- Backend feature flags, tenant membership, workspace membership, and document scope remain
  authoritative.
- Uploaded document text, evidence snippets, and report content are rendered as React text, not
  injected HTML.
- External citation links are allowed only for parsed `http` and `https` URLs and use
  `noopener noreferrer`.
- Tool timelines show safe summaries, tool names, statuses, error codes, and durations only.
- Browser localStorage stores only authentication data managed by the existing auth flow and a
  bounded list of recent agent run IDs.
- Downloads use authenticated requests and refresh expired signed URLs instead of storing them.

Telemetry and metrics must not use queries, document text, users, tenants, or filenames as label
values. The existing Prometheus metric guidance for agent runs and tool calls still applies.
