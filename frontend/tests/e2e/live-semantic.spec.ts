import { expect, test } from "@playwright/test";

const apiBase = process.env.E2E_API_BASE_URL ?? "http://127.0.0.1:8001/api/v1";

test.skip(
  process.env.E2E_LIVE_SEMANTIC_ENABLED !== "true",
  "Operator-provisioned live semantic models are not enabled",
);

test("live semantic retrieval and reranker diagnostics remain safe and scoped", async ({
  page,
  request,
}) => {
  const run = Date.now().toString(36);
  const registration = await request.post(`${apiBase}/auth/register`, {
    data: {
      email: `phase2-live-validation-browser-${run}@validation.localhost.com`,
      full_name: "Phase 2 Browser Validation",
      password: "Temporary-Phase2-Validation-Password-42",
      organization_name: `phase2-live-validation-browser-${run}`,
      workspace_name: "Live Browser Validation",
    },
  });
  expect(registration.ok()).toBeTruthy();
  const auth = await registration.json();
  const headers = {
    Authorization: `Bearer ${auth.access_token}`,
    "X-Workspace-ID": auth.workspace_id,
  };
  const upload = await request.post(`${apiBase}/documents`, {
    headers,
    multipart: {
      file: {
        name: "travel-policy.txt",
        mimeType: "text/plain",
        buffer: Buffer.from("Domestic Meal Allowance: PKR 5,000 per day."),
      },
    },
  });
  expect(upload.ok()).toBeTruthy();
  const uploaded = await upload.json();
  for (let attempt = 0; attempt < 120; attempt += 1) {
    const job = await request.get(`${apiBase}/jobs/${uploaded.job_id}`, { headers });
    const detail = await job.json();
    if (detail.status === "completed") break;
    await new Promise((resolve) => setTimeout(resolve, 250));
  }

  const consoleErrors: string[] = [];
  page.on("console", (message) => {
    if (message.type() === "error") consoleErrors.push(message.text());
  });
  await page.goto("/");
  await page.evaluate(
    ({ token, workspace }) => {
      localStorage.setItem("ekip_token", token);
      localStorage.setItem("ekip_workspace", workspace);
    },
    { token: auth.access_token, workspace: auth.workspace_id },
  );
  await page.goto("/search");
  await page.getByTestId("search-document-scope").selectOption(uploaded.document.id);
  await page
    .getByTestId("search-query")
    .fill("How much may an employee spend on food each day during official travel?");
  await page.getByTestId("search-submit").click();

  await expect(page.getByText(/Hybrid lexical \+ semantic retrieval/)).toBeVisible();
  await expect(page.getByText(/Reranker applied/)).toBeVisible();
  await expect(page.getByText(/Selected-document scope/)).toBeVisible();
  await expect(page.getByTestId("search-result-scope")).toContainText("travel-policy");
  await expect(page.getByTestId("search-result")).toContainText(/PKR 5,000|5,000 per day/);
  await expect
    .poll(() =>
      page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1),
    )
    .toBeTruthy();
  expect(await page.getByTestId("search-result").textContent()).not.toMatch(
    /raw_vector|embedding_values|\/Users\/|\.cache\/ekip-models/,
  );
  expect(consoleErrors).toEqual([]);

  await page.route("**/api/v1/search", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        answer: "I could not find sufficient evidence.",
        evidence: [],
        sufficient_evidence: false,
        abstained: true,
        retrieval_diagnosis: {
          status: "RETRIEVAL_FAILURE_UNRESOLVED",
          retry_performed: true,
          retry_strategy: ["top_k_expansion"],
          initial_support_score: 0,
          final_support_score: 0,
          evidence_count: 0,
          reason_code: "PROVIDER_UNAVAILABLE",
          semantic_used: false,
          reranker_used: false,
          fallback_used: true,
          selected_document_scope: true,
          retrieval_recovery_used: true,
          candidate_count: 1,
          final_evidence_count: 0,
          retrieval_duration_ms: 1,
        },
        outcome: "INSUFFICIENT_EVIDENCE",
        support_status: "ABSENT",
        confidence_category: "none",
        active_document_scope: [
          { document_id: uploaded.document.id, title: "travel-policy" },
        ],
      }),
    });
  });
  await page.getByTestId("search-submit").click();
  await expect(
    page.getByText(/Semantic model unavailable — lexical fallback used/),
  ).toBeVisible();

  await request.delete(`${apiBase}/documents/${uploaded.document.id}`, { headers });
});
