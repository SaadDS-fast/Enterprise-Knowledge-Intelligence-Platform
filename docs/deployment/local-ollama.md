# Local Ollama deployment

Install and provision Ollama separately from the application. No model is pulled at
startup and model caches are never stored in Git. Confirm `ollama --version`, then perform
an explicit operator-approved `ollama pull <alias>` and add that exact alias to
`OLLAMA_ALLOWED_MODELS`.

Host backend: use `http://127.0.0.1:11434`. Docker Desktop on macOS: use
`http://host.docker.internal:11434`. Linux Docker should add a host-gateway mapping and use
the same hostname, or a private Compose-only `ollama` service with no published port.

Enable only for a validation/runtime session:

```env
LOCAL_LLM_BACKEND=ollama
OLLAMA_ENABLED=true
LOCAL_LLM_MODEL=llama3.2:3b
OLLAMA_ALLOWED_MODELS=["llama3.2:3b"]
```

The endpoint must be uncredentialed HTTP on an allowlisted local/private host. Redirects,
public/link-local destinations, arbitrary aliases, and runtime pulls are rejected.

Validated runtime: Ollama `0.32.1`, `llama3:latest`, digest
`365c0bd3c000a25d28ddbf732fe1c6add414de7275464c4e4d1c3b5fcb5d8ad1`,
8.0B/Q4_0, context 8192, installed size about 4.7 GB and loaded model size about
5.0 GB. Docker Desktop connectivity through `host.docker.internal` passed without
publishing an Ollama container port.
