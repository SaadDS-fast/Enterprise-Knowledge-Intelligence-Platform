import { expect, test, type APIRequestContext, type Page } from "@playwright/test";

test.skip(process.env.E2E_ENTERPRISE_ENABLED !== "true", "Enterprise profile disabled");

const apiBase = process.env.E2E_API_BASE_URL ?? "http://localhost:8000/api/v1";
const password = "EnterpriseBrowserPass123!";

async function register(page: Page, label: string) {
  const run = `${Date.now().toString(36)}-${label}`;
  await page.goto("/login");
  await page.getByTestId("auth-mode-toggle").click();
  await page.getByTestId("full-name-input").fill(`Synthetic ${label}`);
  await page.getByTestId("organization-input").fill(`Aurora Meridian ${run}`);
  await page.getByTestId("email-input").fill(`${run}@validation.localhost.com`);
  await page.getByTestId("password-input").fill(password);
  await page.getByTestId("auth-submit").click();
  await expect(page).toHaveURL(/\/dashboard$/);
}

async function headers(page: Page) {
  return page.evaluate(() => ({
    Authorization: `Bearer ${localStorage.getItem("ekip_token") ?? ""}`,
    "X-Workspace-ID": localStorage.getItem("ekip_workspace") ?? "",
  }));
}

async function documents(request: APIRequestContext, page: Page) {
  const response = await request.get(`${apiBase}/documents`, { headers: await headers(page) });
  expect(response.ok()).toBeTruthy();
  return response.json() as Promise<Array<{ id: string; title: string; status: string }>>;
}

test("enterprise browser workflows remain scoped, accessible, and responsive", async ({
  page,
  request,
}) => {
  const consoleErrors: string[] = [];
  page.on("console", (message) => {
    if (message.type() === "error") consoleErrors.push(message.text());
  });
  await register(page, "Tenant-A");
  await page.getByTestId("nav-documents").click();
  await page.getByTestId("document-file-input").setInputFiles({
    name: "enterprise-browser-policy.md",
    mimeType: "text/markdown",
    buffer: Buffer.from(
      "# Travel Policy\nPolicy Owner: Rowan Pike\nEffective Date: 4 February 2026\nEmployees must not approve their own travel claims.",
    ),
  });
  await page.getByTestId("document-upload-submit").click();
  let documentId = "";
  await expect
    .poll(async () => {
      const match = (await documents(request, page)).find(
        (item) => item.title === "enterprise-browser-policy",
      );
      documentId = match?.id ?? "";
      return match?.status;
    })
    .toBe("ready");

  await page.getByTestId("nav-search").click();
  await page.getByTestId("search-query").fill("Who owns the policy and when is it effective?");
  await page.getByTestId("search-submit").click();
  await expect(page.getByTestId("search-answer")).toContainText("Rowan Pike");
  await expect(page.getByTestId("search-answer")).toContainText("4 February 2026");
  await expect(page.getByTestId("search-citations")).toBeVisible();
  await expect(page.locator("body")).not.toContainText(/chain_of_thought|prompt_text|\/app\//i);

  for (const viewport of [
    { width: 1440, height: 900 },
    { width: 820, height: 1180 },
    { width: 390, height: 844 },
  ]) {
    await page.setViewportSize(viewport);
    await expect(page.getByTestId("search-answer")).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(
      true,
    );
  }

  await page.getByTestId("logout-button").click();
  await register(page, "Tenant-B");
  expect(await documents(request, page)).toHaveLength(0);
  const crossTenant = await request.post(`${apiBase}/search`, {
    headers: await headers(page),
    data: { query: "Who owns the policy?", document_ids: [documentId] },
  });
  expect([403, 404]).toContain(crossTenant.status());
  expect(consoleErrors).toEqual([]);
});
