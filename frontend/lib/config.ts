export const frontendConfig = {
  agenticRagEnabled: process.env.NEXT_PUBLIC_AGENTIC_RAG_ENABLED === "true",
  agenticResearchEnabled: process.env.NEXT_PUBLIC_AGENTIC_RESEARCH_ENABLED === "true",
  externalSourcesEnabled: process.env.NEXT_PUBLIC_AGENT_EXTERNAL_SOURCES_ENABLED === "true",
  pollIntervalMs: Number(process.env.NEXT_PUBLIC_AGENT_POLL_INTERVAL_MS ?? "2000"),
};

export function boundedPollInterval(): number {
  if (!Number.isFinite(frontendConfig.pollIntervalMs)) return 2000;
  return Math.min(Math.max(frontendConfig.pollIntervalMs, 1000), 10000);
}
