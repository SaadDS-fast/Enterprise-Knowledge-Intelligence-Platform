import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import CitationList from "./CitationList";

describe("CitationList", () => {
  it("renders external citation links with safe link attributes", () => {
    render(
      <CitationList
        citations={[
          {
            external_source_label: "E1",
            title: "Public advisory",
            provider: "approved-provider",
            canonical_url: "https://example.test/advisory",
            excerpt: "The advisory confirms the date.",
          },
        ]}
      />,
    );

    const link = screen.getByRole("link", { name: "Open external source" });
    expect(link).toHaveAttribute("href", "https://example.test/advisory");
    expect(link).toHaveAttribute("target", "_blank");
    expect(link).toHaveAttribute("rel", "noopener noreferrer");
  });

  it("does not create links for unsafe citation URLs", () => {
    render(
      <CitationList
        citations={[
          {
            external_source_label: "E1",
            title: "Unsafe advisory",
            provider: "approved-provider",
            canonical_url: "javascript:alert(1)",
            excerpt: "<script>alert('x')</script>",
          },
        ]}
      />,
    );

    expect(screen.queryByRole("link", { name: "Open external source" })).not.toBeInTheDocument();
    expect(screen.getByText("<script>alert('x')</script>")).toBeInTheDocument();
  });
});
