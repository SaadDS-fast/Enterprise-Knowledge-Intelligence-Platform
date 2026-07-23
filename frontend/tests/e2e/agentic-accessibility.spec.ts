import { expect, test, type Page } from "@playwright/test";

test.skip(process.env.E2E_AGENTIC_ENABLED !== "true", "Agentic frontend routes disabled");

const viewports = [
  { name: "desktop", width: 1440, height: 900 },
  { name: "tablet", width: 820, height: 1180 },
  { name: "mobile", width: 390, height: 844 },
];

async function installAgentMocks(page: Page) {
  await page.addInitScript(() => {
    localStorage.setItem("ekip_token", "test-token");
    localStorage.setItem("ekip_workspace", "workspace-responsive");
  });
  await page.route("**/api/v1/documents", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify([
        {
          id: "doc-responsive",
          workspace_id: "workspace-responsive",
          title: "Very long responsive evidence document title that must wrap without overflow",
          status: "ready",
          created_by: "user-responsive",
          created_at: "2026-07-23T00:00:00Z",
          updated_at: "2026-07-23T00:00:00Z",
        },
      ]),
    });
  });
  await page.route("**/api/v1/agent/runs/responsive-run", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        id: "responsive-run",
        workspace_id: "workspace-responsive",
        user_id: "user-responsive",
        status: "completed",
        current_state: "COMPLETED",
        input_query: "Who owns the responsive validation project?",
        safe_plan_summary: "Validate authorized evidence and produce a safe answer.",
        result_json: {},
        created_at: "2026-07-23T00:00:00Z",
        updated_at: "2026-07-23T00:00:01Z",
        steps: [
          {
            id: "step-1",
            run_id: "responsive-run",
            step_number: 1,
            state: "INTERNAL_RETRIEVAL",
            summary:
              "Searched authorized internal evidence with a deliberately long summary that must wrap.",
            status: "completed",
            duration_ms: 42,
            created_at: "2026-07-23T00:00:00Z",
            updated_at: "2026-07-23T00:00:01Z",
          },
        ],
        tool_calls: [
          {
            id: "tool-1",
            run_id: "responsive-run",
            step_id: "step-1",
            tool_name: "internal_search",
            status: "success",
            summary: "Internal search completed.",
            duration_ms: 24,
            created_at: "2026-07-23T00:00:00Z",
            updated_at: "2026-07-23T00:00:01Z",
          },
        ],
      }),
    });
  });
  await page.route("**/api/v1/agent/research", async (route) => {
    if (new URL(route.request().url()).pathname !== "/api/v1/agent/research") {
      await route.fallback();
      return;
    }
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify([
        {
          id: "responsive-job",
          question: "Responsive cited report with a very long title that must wrap safely.",
          status: "completed",
          current_state: "COMPLETED",
          stage: "completed",
          progress_percent: 100,
          requested_formats: ["markdown", "pdf", "docx"],
          result_json: {},
          created_at: "2026-07-23T00:00:00Z",
          updated_at: "2026-07-23T00:00:01Z",
        },
      ]),
    });
  });
  await page.route("**/api/v1/agent/research/responsive-job", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        id: "responsive-job",
        question: "Responsive cited report with a very long title that must wrap safely.",
        status: "completed",
        current_state: "COMPLETED",
        stage: "completed",
        progress_percent: 100,
        source_count: 3,
        verified_citation_count: 3,
        requested_formats: ["markdown", "pdf", "docx"],
        result_json: { report: { executive_summary: "Responsive report completed safely." } },
        created_at: "2026-07-23T00:00:00Z",
        updated_at: "2026-07-23T00:00:01Z",
        completed_at: "2026-07-23T00:00:01Z",
        agent_run_id: "responsive-run",
      }),
    });
  });
  await page.route("**/api/v1/agent/research/responsive-job/artifacts", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify([
        {
          format: "markdown",
          filename: "responsive.md",
          mime_type: "text/markdown",
          checksum_sha256: "abc123",
          size_bytes: 2048,
          download_url: "/api/v1/agent/research/responsive-job/download/markdown",
        },
        {
          format: "pdf",
          filename: "responsive.pdf",
          mime_type: "application/pdf",
          checksum_sha256: "def456",
          size_bytes: 4096,
          download_url: "/api/v1/agent/research/responsive-job/download/pdf",
        },
        {
          format: "docx",
          filename: "responsive.docx",
          mime_type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
          checksum_sha256: "fed789",
          size_bytes: 4096,
          download_url: "/api/v1/agent/research/responsive-job/download/docx",
        },
      ]),
    });
  });
}

async function expectNoHorizontalOverflow(page: Page) {
  await expect
    .poll(async () =>
      page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1),
    )
    .toBeTruthy();
}

for (const viewport of viewports) {
  test(`agent routes remain usable and responsive at ${viewport.name}`, async ({ page }) => {
    await page.setViewportSize({ width: viewport.width, height: viewport.height });
    await installAgentMocks(page);

    await page.goto("/agent");
    await expect(page.getByTestId("agent-form")).toBeVisible();
    await expect(page.getByLabel("Question")).toBeVisible();
    await page.keyboard.press("Tab");
    await expect(page.locator(":focus")).toBeVisible();
    await expectNoHorizontalOverflow(page);

    await page.goto("/agent/runs/responsive-run");
    await expect(page.getByTestId("agent-run-detail")).toBeVisible();
    await expect(page.getByTestId("execution-timeline")).toBeVisible();
    await expect(page.getByText("completed").first()).toBeVisible();
    await expectNoHorizontalOverflow(page);

    await page.goto("/agent/research");
    await expect(page.getByTestId("research-form")).toBeVisible();
    await expect(page.getByLabel("Research question")).toBeVisible();
    await expect(page.getByLabel("Research status filter")).toBeVisible();
    await expectNoHorizontalOverflow(page);

    await page.goto("/agent/research/responsive-job");
    await expect(page.getByTestId("research-job-detail")).toBeVisible();
    await expect(page.getByLabel("Research progress")).toBeVisible();
    await expect(page.getByTestId("research-artifacts")).toContainText("MARKDOWN");
    await expect(page.getByTestId("research-artifacts")).toContainText("PDF");
    await expect(page.getByTestId("research-artifacts")).toContainText("DOCX");
    await expectNoHorizontalOverflow(page);
  });
}
