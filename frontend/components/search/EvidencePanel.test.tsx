import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import EvidencePanel from "./EvidencePanel";

describe("EvidencePanel", () => {
  it("renders an empty state", () => {
    render(<EvidencePanel items={[]} />);

    expect(screen.getByText("No evidence was retrieved.")).toBeInTheDocument();
  });

  it("renders citations with score and excerpt", () => {
    render(
      <EvidencePanel
        items={[
          {
            chunk_id: "chunk-1",
            document_id: "doc-1",
            document_title: "Atlas Brief",
            content: "Project Atlas launches in March 2025.",
            score: 0.87,
            metadata: { page: 2 },
          },
        ]}
      />,
    );

    expect(screen.getByText("[1] Atlas Brief")).toBeInTheDocument();
    expect(screen.getByText("87%")).toBeInTheDocument();
    expect(screen.getByText("Project Atlas launches in March 2025.")).toBeInTheDocument();
  });
});
