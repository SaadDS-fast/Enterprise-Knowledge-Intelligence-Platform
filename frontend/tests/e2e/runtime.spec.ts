import { expect, test, type APIRequestContext, type Page } from "@playwright/test";

const apiBase = process.env.E2E_API_BASE_URL ?? "http://localhost:8000/api/v1";
const password = "RuntimeE2EPass123!";

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

test("runtime registration, ingestion, search, isolation, and logout", async ({ page, request }) => {
  const run = Date.now().toString(36);
  const emailA = `e2e-a-${run}@validation.localhost.com`;
  const emailB = `e2e-b-${run}@validation.localhost.com`;
  const title = `E2E Project Atlas ${run}`;
  const createdDocumentIds: string[] = [];

  await page.goto("/login");
  await page.getByTestId("auth-mode-toggle").click();
  await page.getByTestId("full-name-input").fill("E2E Tenant A");
  await page.getByTestId("organization-input").fill(`E2E Org A ${run}`);
  await page.getByTestId("email-input").fill(emailA);
  await page.getByTestId("password-input").fill(password);
  await page.getByTestId("auth-submit").click();
  await expect(page).toHaveURL(/\/dashboard$/);
  await expect(page.getByTestId("app-main")).toContainText(/workspace overview/i);

  await page.getByTestId("logout-button").click();
  await expect(page).toHaveURL(/\/login$/);
  await page.getByTestId("email-input").fill(emailA);
  await page.getByTestId("password-input").fill(password);
  await page.getByTestId("auth-submit").click();
  await expect(page).toHaveURL(/\/dashboard$/);

  await page.getByTestId("nav-documents").click();
  await expect(page).toHaveURL(/\/documents$/);
  await page.getByTestId("document-file-input").setInputFiles({
    name: "project-atlas-e2e.txt",
    mimeType: "text/plain",
    buffer: Buffer.from(
      [
        "Project Atlas was launched in March 2025.",
        "The project is owned by the Operations Analytics team.",
        "The approved budget is 250,000 PKR.",
        "The project is currently in the implementation stage.",
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
      const doc = docs.find((item) => item.title === "project-atlas-e2e" || item.title === title);
      if (doc && !createdDocumentIds.includes(doc.id)) createdDocumentIds.push(doc.id);
      return doc?.status ?? "missing";
    }, { timeout: 30_000 })
    .toBe("ready");

  await page.reload();
  await expect(page.getByTestId("document-row").filter({ hasText: "project-atlas-e2e" })).toContainText("ready");

  await page.getByTestId("nav-search").click();
  await page.getByTestId("search-query").fill("When was Project Atlas launched and who owns it?");
  await page.getByTestId("search-submit").click();
  await expect(page.getByTestId("search-verdict")).toHaveText("Evidence verified");
  await expect(page.getByTestId("search-answer")).toContainText("March 2025");
  await expect(page.getByTestId("evidence-list")).toContainText("Operations Analytics");
  await expect(page.getByTestId("retrieval-diagnosis")).toContainText("Initial retrieval only");

  await page.getByTestId("search-query").fill("What is the capital of Virellia?");
  await page.getByTestId("search-submit").click();
  await expect(page.getByTestId("search-verdict")).toHaveText("Insufficient evidence");
  await expect(page.getByTestId("retrieval-diagnosis")).toContainText(
    "Information does not appear to exist",
  );

  await page.getByTestId("logout-button").click();
  await page.getByTestId("auth-mode-toggle").click();
  await page.getByTestId("full-name-input").fill("E2E Tenant B");
  await page.getByTestId("organization-input").fill(`E2E Org B ${run}`);
  await page.getByTestId("email-input").fill(emailB);
  await page.getByTestId("password-input").fill(password);
  await page.getByTestId("auth-submit").click();
  await expect(page).toHaveURL(/\/dashboard$/);

  const tenantBDocs = await apiFetch<Array<{ id: string }>>(request, page, "/documents");
  expect(tenantBDocs).toHaveLength(0);
  await page.getByTestId("nav-search").click();
  await page.getByTestId("search-query").fill("Project Atlas budget");
  await page.getByTestId("search-submit").click();
  await expect(page.getByTestId("search-verdict")).toHaveText("Insufficient evidence");
  await expect(page.getByTestId("empty-evidence")).toBeVisible();

  await page.getByTestId("logout-button").click();
  await expect(page).toHaveURL(/\/login$/);

  const loginA = await request.post(`${apiBase}/auth/login`, {
    data: { email: emailA, password },
  });
  const auth = await loginA.json();
  for (const documentId of createdDocumentIds) {
    await request.delete(`${apiBase}/documents/${documentId}`, {
      headers: {
        Authorization: `Bearer ${auth.access_token}`,
        "X-Workspace-ID": auth.workspace_id,
      },
    });
  }
});
