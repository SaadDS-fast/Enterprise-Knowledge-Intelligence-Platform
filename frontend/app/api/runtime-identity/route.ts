import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

export function GET() {
  return NextResponse.json({
    application: "ekip-frontend",
    version: "1.0.0",
    build_commit: process.env.NEXT_PUBLIC_BUILD_COMMIT ?? "development",
    environment: process.env.NODE_ENV ?? "development",
    compatibility_id: process.env.NEXT_PUBLIC_RUNTIME_COMPATIBILITY_ID ?? "ekip-v1",
    api_base_url: process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1",
    features: {
      agentic_rag: process.env.NEXT_PUBLIC_AGENTIC_RAG_ENABLED === "true",
      agentic_research: process.env.NEXT_PUBLIC_AGENTIC_RESEARCH_ENABLED === "true",
      external_sources: process.env.NEXT_PUBLIC_AGENT_EXTERNAL_SOURCES_ENABLED === "true",
    },
  });
}
