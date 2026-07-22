import LegacyResearchWorkspace from "@/components/research/LegacyResearchWorkspace";

export default function Research() {
  return (
    <>
      <div className="page-header">
        <div>
          <span className="eyebrow">CONTROLLED WORKFLOW</span>
          <h1>Research</h1>
          <p>Create a cited brief from workspace evidence.</p>
        </div>
      </div>
      <LegacyResearchWorkspace />
    </>
  );
}
