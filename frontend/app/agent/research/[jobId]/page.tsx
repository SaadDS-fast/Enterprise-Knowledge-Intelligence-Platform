import ResearchJobDetail from "@/components/research/ResearchJobDetail";

export default async function AgentResearchJobPage({ params }: { params: Promise<{ jobId: string }> }) {
  const { jobId } = await params;
  return (
    <>
      <div className="page-header">
        <div>
          <span className="eyebrow">REPORT LIFECYCLE</span>
          <h1>Research job</h1>
          <p>Track safe status, evidence counts, citation checks, and generated artifacts.</p>
        </div>
      </div>
      <ResearchJobDetail jobId={jobId} />
    </>
  );
}
