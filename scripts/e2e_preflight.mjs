import process from "node:process";

const frontendUrl = process.env.E2E_BASE_URL;
const backendApi = process.env.E2E_API_BASE_URL;
const expectedCommit = process.env.E2E_BUILD_COMMIT;
const expectedCompatibility = process.env.E2E_COMPATIBILITY_ID;
const agentic = process.env.E2E_AGENTIC_ENABLED === "true";

if (!frontendUrl || !backendApi || !expectedCommit || !expectedCompatibility) {
  throw new Error("E2E preflight configuration is incomplete");
}

async function json(url) {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`E2E preflight request failed: ${url} (${response.status})`);
  }
  return response.json();
}

const frontend = await json(`${frontendUrl}/api/runtime-identity`);
const backend = await json(`${backendApi}/health/runtime`);
const ready = await json(`${backendApi}/health/ready`);

function requireValue(actual, expected, label) {
  if (actual !== expected) {
    throw new Error(
      `E2E preflight mismatch for ${label}: expected ${expected}, received ${actual}`,
    );
  }
}

requireValue(frontend.application, "ekip-frontend", "frontend application");
requireValue(backend.application, "ekip-backend", "backend application");
requireValue(frontend.build_commit, expectedCommit, "frontend commit");
requireValue(backend.build_commit, expectedCommit, "backend commit");
requireValue(frontend.compatibility_id, expectedCompatibility, "frontend compatibility");
requireValue(backend.compatibility_id, expectedCompatibility, "backend compatibility");
requireValue(frontend.compatibility_id, backend.compatibility_id, "cross-runtime compatibility");
requireValue(frontend.api_base_url, backendApi, "frontend API target");
requireValue(frontend.features.agentic_rag, agentic, "frontend agentic RAG");
requireValue(frontend.features.agentic_research, agentic, "frontend research");
requireValue(backend.features.agentic_rag, agentic, "backend agentic RAG");
requireValue(backend.features.agentic_research, agentic, "backend research");
requireValue(frontend.features.external_sources, false, "frontend external sources");
requireValue(backend.features.external_apis, false, "backend external APIs");
requireValue(backend.features.semantic_embeddings, false, "semantic embeddings");
requireValue(backend.features.reranker, false, "reranker");
requireValue(ready.status, "ok", "backend readiness");

console.log(
  JSON.stringify({
    profile: agentic ? "agentic" : "default",
    commit: expectedCommit,
    compatibility: expectedCompatibility,
    frontend: frontendUrl,
    backend: backendApi,
  }),
);
