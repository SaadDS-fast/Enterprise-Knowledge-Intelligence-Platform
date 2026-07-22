import { expect, test, type APIRequestContext, type Page } from "@playwright/test";

const apiBase = process.env.E2E_API_BASE_URL ?? "http://localhost:8000/api/v1";
const password = "RuntimeAgentE2EPass123!";

test.skip(process.env.E2E_AGENTIC_ENABLED !== "true", "Agentic frontend runtime flag disabled");

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

    await page.getByTestId("nav-agent").click();
    await expect(page).toHaveURL(/\/agent$/);
    await expect(page.getByTestId("agent-form")).toBeVisible();

    await page.getByTestId("nav-documents").click();
    await page.getByTestId("document-file-input").setInputFiles({
      name: "agentic-frontier-e2e.txt",
      mimeType: "text/plain",
      buffer: Buffer.from(
        [
          "Project Frontier launches in April 2026.",
          "The owner is the Knowledge Operations team.",
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
    await page.getByTestId("agent-query").fill("When does Project Frontier launch and who owns it?");
    await page.getByTestId("agent-submit").click();
    await expect(page.getByTestId("agent-result")).toContainText(/Frontier|April|Knowledge/i);
    await expect(page.getByTestId("agent-result")).toContainText("Retrieval diagnosis");

    await page.getByTestId("nav-agent-research").click();
    await page.getByTestId("research-question").fill("Write a short cited Frontier launch brief.");
    await page.getByTestId("research-submit").click();
    await expect(page.getByRole("status")).toContainText("Report accepted");

    await page.getByTestId("nav-search").click();
    await expect(page).toHaveURL(/\/search$/);
    await expect(page.getByTestId("search-submit")).toBeVisible();
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
