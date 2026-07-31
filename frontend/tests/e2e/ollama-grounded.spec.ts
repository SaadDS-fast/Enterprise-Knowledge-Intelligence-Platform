import { expect, test } from "@playwright/test";

const apiBase = process.env.E2E_API_BASE_URL ?? "http://127.0.0.1:8001/api/v1";

test.skip(
  process.env.E2E_OLLAMA_ENABLED !== "true",
  "Operator-provisioned live Ollama acceptance is not enabled",
);

test("live Ollama preserves critical facts in a disposable selected-document scope", async ({
  page,
  request,
}) => {
  const run = Date.now().toString(36);
  const registration = await request.post(`${apiBase}/auth/register`, {
    data: {
      email: `ollama-grounded-${run}@validation.localhost.com`,
      full_name: "Grounded Generation Browser Validation",
      password: "Temporary-Grounded-Validation-Password-42",
      organization_name: `ollama-grounded-${run}`,
      workspace_name: "Grounded Browser Validation",
    },
  });
  expect(registration.ok()).toBeTruthy();
  const auth = await registration.json();
  const headers = {
    Authorization: `Bearer ${auth.access_token}`,
    "X-Workspace-ID": auth.workspace_id,
  };
  const cases: Array<[string, string, RegExp, RegExp]> = [
    [
      "Topic: Quadratic Equations\nDefinition:\nA quadratic equation has the form ax² + bx + c = 0, where a is not zero.",
      "What is a quadratic equation?",
      /ax² \+ bx \+ c = 0/,
      /a is not zero/,
    ],
    [
      "Definition: A quadratic equation has the form ax² + bx + c = 0, where a is not zero.",
      "What is the quadratic equation definition?",
      /ax² \+ bx \+ c = 0/,
      /a is not zero/,
    ],
    [
      "Employees must not exceed the approved travel limit.",
      "What is prohibited?",
      /must not exceed/,
      /approved travel limit/,
    ],
    [
      "Employees must not exceed the approved travel limit.",
      "What obligation applies to employees?",
      /must not exceed/,
      /approved travel limit/,
    ],
    [
      "Policy Owner:\nThe policy owner is Ayesha Khan.\nEffective Date:\nThe policy is effective from 1 February 2026.",
      "Who owns the policy and when does it become effective?",
      /Ayesha Khan/,
      /1 February 2026/,
    ],
    [
      "Published Date:\nThe policy was published on 8 January 2026.\nEffective Date:\nThe policy is effective from 1 February 2026.",
      "What is the effective date?",
      /1 February 2026/,
      /effective/i,
    ],
    [
      "Policy Owner:\nThe policy owner is Ayesha Khan.\nEffective Date:\nThe policy is effective from 1 February 2026.",
      "Who owns the policy and when does it become effective?",
      /Ayesha Khan/,
      /1 February 2026/,
    ],
  ];

  await page.goto("/");
  await page.evaluate(
    ({ token, workspace }) => {
      localStorage.setItem("ekip_token", token);
      localStorage.setItem("ekip_workspace", workspace);
    },
    { token: auth.access_token, workspace: auth.workspace_id },
  );
  await page.goto("/search");
  const consoleErrors: string[] = [];
  page.on("console", (message) => {
    if (message.type() === "error") consoleErrors.push(message.text());
  });

  for (const [index, [content, query, expected, required]] of cases.entries()) {
    const upload = await request.post(`${apiBase}/documents`, {
      headers,
      multipart: {
        file: {
          name: `grounded-${index}-${run}.txt`,
          mimeType: "text/plain",
          buffer: Buffer.from(content),
        },
      },
    });
    expect(upload.ok()).toBeTruthy();
    const uploaded = await upload.json();
    await expect
      .poll(
        async () => {
          const job = await request.get(`${apiBase}/jobs/${uploaded.job_id}`, { headers });
          return (await job.json()).status;
        },
        { timeout: 30_000 },
      )
      .toBe("completed");

    await page.reload();
    await page.getByTestId("search-document-scope").selectOption(uploaded.document.id);
    await page.getByTestId("search-query").fill(query);
    await page.getByTestId("search-submit").click();
    await expect(page.getByTestId("search-answer")).toContainText(expected);
    await expect(page.getByTestId("search-answer")).toContainText(required);
    await expect(page.getByTestId("search-citations")).toContainText(`grounded-${index}-${run}`);
    await expect(page.getByTestId("search-citations")).toContainText(required);
    await expect(page.getByTestId("search-verdict")).not.toContainText(
      /insufficient|failed|conflict/i,
    );
    await expect(page.getByTestId("search-claim-support")).toContainText(/Citations:/);
    expect(await page.getByTestId("search-result").textContent()).not.toMatch(
      /answer_segments|fact_ids|required_component_id|\/Users\/|system prompt/i,
    );
    await request.delete(`${apiBase}/documents/${uploaded.document.id}`, { headers });
  }

  const tenantB = await request.post(`${apiBase}/auth/register`, {
    data: {
      email: `ollama-grounded-tenant-b-${run}@validation.localhost.com`,
      full_name: "Grounded Tenant B",
      password: "Temporary-Grounded-Validation-Password-42",
      organization_name: `ollama-grounded-tenant-b-${run}`,
      workspace_name: "Isolated Browser Validation",
    },
  });
  expect(tenantB.ok()).toBeTruthy();
  const authB = await tenantB.json();
  const tenantBSearch = await request.post(`${apiBase}/search`, {
    headers: {
      Authorization: `Bearer ${authB.access_token}`,
      "X-Workspace-ID": authB.workspace_id,
    },
    data: { query: "Who owns the policy?" },
  });
  expect(tenantBSearch.ok()).toBeTruthy();
  expect((await tenantBSearch.json()).evidence).toHaveLength(0);

  await page.route("**/api/v1/search", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        answer: "The available evidence does not contain a direct answer.",
        evidence: [],
        sufficient_evidence: false,
        abstained: true,
        outcome: "INSUFFICIENT_EVIDENCE",
        support_status: "ABSENT",
        confidence_category: "none",
        citations: [],
        conflicts: [],
        active_document_scope: [],
        generation_provider: "extractive",
        generation_fallback_used: true,
        generation_verification: "schema_validation_failed",
      }),
    });
  });
  await page.getByTestId("search-query").fill("Validate malformed candidate fallback");
  await page.getByTestId("search-submit").click();
  await expect(page.getByTestId("generation-status")).toContainText("safe fallback used");
  await expect(page.getByTestId("search-result")).not.toContainText(/answer_segments|fact_ids/);

  for (const viewport of [
    { width: 1440, height: 900 },
    { width: 820, height: 1180 },
    { width: 390, height: 844 },
  ]) {
    await page.setViewportSize(viewport);
    await expect
      .poll(() =>
        page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1),
      )
      .toBeTruthy();
  }
  expect(consoleErrors).toEqual([]);
});
