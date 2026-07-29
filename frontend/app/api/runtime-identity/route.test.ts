import { describe, expect, it } from "vitest";

import { GET } from "./route";

describe("runtime identity", () => {
  it("contains only safe public build and feature information", async () => {
    const response = GET();
    const payload = await response.json();

    expect(payload.application).toBe("ekip-frontend");
    expect(payload.compatibility_id).toBeTruthy();
    expect(Object.keys(payload.features).sort()).toEqual([
      "agentic_rag",
      "agentic_research",
      "external_sources",
    ]);
    expect(JSON.stringify(payload).toLowerCase()).not.toMatch(
      /secret|credential|database|model.cache|filesystem/,
    );
  });
});
