# Ollama Local Profile

Ollama is optional and not required for default operation. Do not download large models
automatically.

When an operator already has an allowlisted local model, validate:

- exact model name and quantization when visible;
- structured planner JSON validity;
- claim-verification output validity;
- grounded answer synthesis;
- research report synthesis;
- timeout behavior;
- deterministic fallback after Ollama failure;
- absence of hidden reasoning in API/UI responses.

If Ollama is unavailable, mark the release result as `not runtime-tested` rather than failing the
local-first release.
