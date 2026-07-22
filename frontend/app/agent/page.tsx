import AgentWorkspace from "@/components/agent/AgentWorkspace";

export default function AgentPage() {
  return (
    <>
      <div className="page-header">
        <div>
          <span className="eyebrow">CONTROLLED AGENT</span>
          <h1>Agent</h1>
          <p>Ask governed document questions with safe evidence, citations, and outcomes.</p>
        </div>
      </div>
      <AgentWorkspace />
    </>
  );
}
