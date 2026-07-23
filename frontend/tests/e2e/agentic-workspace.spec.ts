import { expect, test, type APIRequestContext, type Page } from "@playwright/test";

const apiBase = process.env.E2E_API_BASE_URL ?? "http://localhost:8000/api/v1";
const password = "RuntimeAgentE2EPass123!";

test.skip(process.env.E2E_AGENTIC_ENABLED !== "true", "Agentic frontend runtime flag disabled");
test.setTimeout(120_000);

async function apiHeaders(page: Page) {
  return page.evaluate(() => ({
    Authorization: `Bearer ${localStorage.getItem("ekip_token") ?? ""}`,
    "X-Workspace-ID": localStorage.getItem("ekip_workspace") ?? "",
  }));
}

async function apiFetch<T>(
  request: APIRequestContext,
  page: Page,
  path: string,
  options: { method?: string; data?: unknown } = {},
): Promise<T> {
  const response = await request.fetch(`${apiBase}${path}`, {
    method: options.method ?? "GET",
    data: options.data,
    headers: await apiHeaders(page),
  });
  expect(response.ok()).toBeTruthy();
  return (await response.json()) as T;
}

test("agent query and async research workspace run through the real stack", async ({
  page,
  request,
}) => {
  const run = Date.now().toString(36);
  const email = `agent-e2e-${run}@validation.localhost.com`;
  const emailB = `agent-e2e-b-${run}@validation.localhost.com`;
  const createdDocumentIds: string[] = [];

  try {
    await page.goto("/login");
    await page.getByTestId("auth-mode-toggle").click();
    await page.getByTestId("full-name-input").fill("Agentic E2E User");
    await page.getByTestId("organization-input").fill(`Agentic Org ${run}`);
    await page.getByTestId("email-input").fill(email);
    await page.getByTestId("password-input").fill(password);
    await page.getByTestId("auth-submit").click();
    await expect(page).toHaveURL(/\/dashboard$/);

    if (!(await page.getByTestId("nav-agent").isVisible().catch(() => false))) {
      await expect(page.getByTestId("nav-agent")).toHaveCount(0);
      await expect(page.getByTestId("nav-agent-research")).toHaveCount(0);
      await page.goto("/agent");
      await expect(page.getByTestId("agent-disabled")).toBeVisible();
      await page.goto("/agent/research");
      await expect(page.getByTestId("research-disabled")).toBeVisible();
      return;
    }

    await page.getByTestId("nav-agent").click();
    await expect(page).toHaveURL(/\/agent$/);
    await expect(page.getByTestId("agent-form")).toBeVisible();
    await expect(page.getByLabel("Question")).toBeVisible();

    await page.getByTestId("nav-documents").click();
    await page.getByTestId("document-file-input").setInputFiles({
      name: "agentic-frontier-e2e.txt",
      mimeType: "text/plain",
      buffer: Buffer.from(
        [
          "Project Frontier is owned by the Knowledge Operations team.",
          "The evidence policy requires citations for every factual answer.",
        ].join("\n"),
      ),
    });
    await page.getByTestId("document-upload-submit").click();

    await expect
      .poll(async () => {
        const docs = await apiFetch<Array<{ id: string; title: string; status: string }>>(
          request,
          page,
          "/documents",
        );
        const doc = docs.find((item) => item.title === "agentic-frontier-e2e");
        if (doc && !createdDocumentIds.includes(doc.id)) createdDocumentIds.push(doc.id);
        return doc?.status ?? "missing";
      }, { timeout: 30_000 })
      .toBe("ready");

    await page.getByTestId("nav-agent").click();
    await page.getByTestId("agent-query").fill("Who owns Project Frontier?");
    await page.getByTestId("agent-submit").click();
    const agentResult = page.getByTestId("agent-result");
    await expect(agentResult).toContainText(/Frontier|Knowledge Operations/i);
    await expect(agentResult).toContainText("Answer supported");
    await expect(agentResult.getByTestId("internal-evidence-card").first()).toBeVisible();
    await expect(agentResult.getByTestId("agent-citations")).toBeVisible();
    await expect(agentResult).toContainText("Retrieval diagnosis");
    await expect(agentResult).not.toContainText(/chain.of.thought|hidden reasoning|system prompt/i);
    const agentRunUrl = await agentResult.getByRole("link", { name: "Execution timeline" }).getAttribute("href") ?? "";
    expect(agentRunUrl).toContain("/agent/runs/");

    if (await page.getByTestId("agent-external-toggle").isVisible().catch(() => false)) {
      await page.getByTestId("agent-query").fill("What public external-only fact is available?");
      await page.getByTestId("agent-external-toggle").check();
      await page.getByTestId("agent-submit").click();
      await expect(agentResult.getByTestId("external-evidence-card").first()).toBeVisible();
      const externalLink = agentResult.getByRole("link", { name: "Open external source" }).first();
      await expect(externalLink).toHaveAttribute("href", /^https:\/\/example\.invalid\//);
      await expect(externalLink).toHaveAttribute("target", "_blank");
      await expect(externalLink).toHaveAttribute("rel", "noopener noreferrer");
    }

    await agentResult.getByRole("link", { name: "Execution timeline" }).click();
    await expect(page.getByTestId("agent-run-detail")).toBeVisible();
    await expect(page.getByTestId("execution-timeline")).toBeVisible();
    await expect(page.getByTestId("agent-run-detail")).not.toContainText(
      /chain.of.thought|hidden reasoning|system prompt/i,
    );

    await page.getByTestId("nav-agent-research").click();
    await page.getByTestId("research-question").fill("Write a short cited Frontier launch brief.");
    await page.getByLabel("PDF").check();
    await page.getByLabel("DOCX").check();
    await page.getByTestId("research-submit").click();
    const accepted = page.getByRole("status");
    await expect(accepted).toContainText("Report accepted");
    const researchJobUrl = await accepted.getByRole("link", { name: "Open job" }).getAttribute("href") ?? "";
    expect(researchJobUrl).toContain("/agent/research/");
    await accepted.getByRole("link", { name: "Open job" }).click();
    await expect(page.getByTestId("research-job-detail")).toBeVisible();
    await expect
      .poll(async () => page.getByTestId("research-job-detail").textContent(), { timeout: 60_000 })
      .toMatch(/completed/i);
    await expect(page.getByTestId("research-artifacts")).toContainText("MARKDOWN");
    await expect(page.getByTestId("research-artifacts")).toContainText("PDF");
    await expect(page.getByTestId("research-artifacts")).toContainText("DOCX");
    await page.getByRole("button", { name: "Download markdown report" }).click();
    await expect(page.getByTestId("research-job-detail")).not.toContainText(/Download failed/i);

    await page.getByTestId("nav-agent-research").click();
    await page.getByTestId("research-question").fill("Create a cancellable Frontier follow-up.");
    await page.getByTestId("research-submit").click();
    const cancelLink = page.getByRole("status").getByRole("link", { name: "Open job" });
    await expect(cancelLink).toBeVisible();
    await cancelLink.click();
    if (await page.getByTestId("research-cancel").isVisible().catch(() => false)) {
      page.once("dialog", async (dialog) => {
        expect(dialog.message()).toContain("Request cancellation");
        await dialog.accept();
      });
      await page.getByTestId("research-cancel").click();
      await expect(page.getByTestId("research-job-detail")).toContainText(/cancel/i);
    }

    await page.getByTestId("nav-search").click();
    await expect(page).toHaveURL(/\/search$/);
    await expect(page.getByTestId("search-submit")).toBeVisible();

    await page.getByTestId("logout-button").click();
    await page.getByTestId("auth-mode-toggle").click();
    await page.getByTestId("full-name-input").fill("Agentic E2E Tenant B");
    await page.getByTestId("organization-input").fill(`Agentic Org B ${run}`);
    await page.getByTestId("email-input").fill(emailB);
    await page.getByTestId("password-input").fill(password);
    await page.getByTestId("auth-submit").click();
    await expect(page).toHaveURL(/\/dashboard$/);
    await page.goto(agentRunUrl);
    await expect(page.getByText("Agent run not found")).toBeVisible();
    await page.goto(researchJobUrl);
    await expect(page.getByText("Research job not found")).toBeVisible();
  } finally {
    const login = await request.post(`${apiBase}/auth/login`, { data: { email, password } });
    if (login.ok()) {
      const auth = await login.json();
      for (const documentId of createdDocumentIds) {
        await request.delete(`${apiBase}/documents/${documentId}`, {
          headers: {
            Authorization: `Bearer ${auth.access_token}`,
            "X-Workspace-ID": auth.workspace_id,
          },
        });
      }
    }
  }
});
