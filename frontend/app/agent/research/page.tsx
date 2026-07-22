import ResearchWorkspace from "@/components/research/ResearchWorkspace";

export default function AgentResearchPage() {
  return (
    <>
      <div className="page-header">
        <div>
          <span className="eyebrow">ASYNC RESEARCH</span>
          <h1>Agent Research</h1>
          <p>Create cited reports through the controlled report-worker pipeline.</p>
        </div>
      </div>
      <ResearchWorkspace />
    </>
  );
}
