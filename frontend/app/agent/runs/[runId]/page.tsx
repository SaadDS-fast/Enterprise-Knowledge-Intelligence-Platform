import AgentRunDetail from "@/components/agent/AgentRunDetail";

export default async function AgentRunPage({ params }: { params: Promise<{ runId: string }> }) {
  const { runId } = await params;
  return (
    <>
      <div className="page-header">
        <div>
          <span className="eyebrow">OPERATIONAL ACTIVITY</span>
          <h1>Run detail</h1>
          <p>Safe processing stages without hidden reasoning or prompt internals.</p>
        </div>
      </div>
      <AgentRunDetail runId={runId} />
    </>
  );
}
