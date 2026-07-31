# Verified Ollama grounded generation

Ollama is an optional candidate synthesizer after scoped retrieval, sufficiency, conflict
analysis, and the canonical response-state decision. Only supported Search responses reach
generation. All other states remain deterministic. The controlled Agent, Evaluation, and
Research paths share the existing local provider gateway; the model never selects tools,
changes scope, retries retrieval, or decides response state.

The server creates bounded `E1..En` evidence packets from authorized retrieved objects.
Document text is explicitly marked as untrusted, instruction-like text is annotated, and
the prompt requests a strict JSON candidate containing an answer, claims, and evidence IDs.
Ollama's optional `thinking` field and every other unknown field are ignored and never
logged, stored, returned, or audited.

The candidate is untrusted. Pydantic rejects extra/schema-invalid fields, unknown evidence
IDs, unsupported claims, HTML/script output, prompt leakage, numeric/date/unit/equation
drift, and negation drift. Citations are rebuilt from the server's evidence objects.
Failure, timeout, malformed JSON, an absent model, or an open circuit returns the existing
deterministic extractive answer without changing canonical state.

The Ollama wire grammar is deliberately simpler than the application schema because
Ollama `0.32.1` rejects constrained grammar keywords. Strict validation remains
post-parse and server-side. Safe token counts and load duration are retained only in
ephemeral execution results; raw responses and reasoning fields are discarded.
