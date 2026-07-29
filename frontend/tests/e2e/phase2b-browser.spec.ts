import { expect, test } from "@playwright/test";

test.skip(process.env.E2E_PHASE2B_ENABLED !== "true", "Phase 2B isolated acceptance disabled");

const cases = [
  ["paraphrased travel allowance", "Daily travel meals are PKR 6,850.", "Employee Travel Policy"],
  ["correct approval role", "The procurement manager grants procurement approval.", "Procurement Controls"],
  ["annual revenue absence", "I could not find annual revenue in the selected documents.", ""],
  ["revenue versus budget", "Annual revenue is PKR 38,750,000.", "Atlas Annual Report"],
  ["function versus equation", "A function maps every input to exactly one output.", "Mathematics Glossary"],
  ["displacement versus deformation", "Elastic deformation is reversible extension.", "Materials Handbook"],
  ["current versus superseded", "The current records policy is effective 12 August 2026.", "Records Policy 2026"],
  ["table numerical lookup", "Medical allowance is PKR 92,000.", "Benefits Table"],
  ["two-document comparison", "Revenue is PKR 38,750,000; budget is PKR 38,250,000.", "Atlas Annual Report"],
  ["selected-document scope", "An equation asserts two expressions are equal.", "Mathematics Glossary"],
  ["tenant isolation", "No authorized evidence exists in this workspace.", ""],
  ["ambiguous query", "Please clarify which policy you mean.", ""],
  ["reranker fallback", "Travel allowance is PKR 6,850 per day.", "Employee Travel Policy"],
  ["embedding fallback", "The procurement manager grants approval.", "Procurement Controls"],
  ["multi-claim single-source", "Travel allowance is PKR 6,850 and the travel manager approves trips.", "Employee Travel Policy"],
  ["true value conflict", "Authorized sources contain conflicting information.", "Travel Policy"],
  ["low-quality source", "The available source quality is insufficient for a reliable answer.", ""],
  ["retrieval failure", "Reliable retrieval could not be completed. This does not mean the information is absent.", ""],
] as const;

test("18 retrieval and response states render consistently in clean Chromium", async ({ page }) => {
  const consoleErrors: string[] = [];
  page.on("console", (message) => {
    if (message.type() === "error") consoleErrors.push(message.text());
  });
  await page.route("**/api/v1/documents", (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: "[]" }),
  );
  let current = 0;
  await page.route("**/api/v1/search", async (route) => {
    const [query, answer, source] = cases[current];
    const conflict = query.includes("true value conflict");
    const lowQuality = query.includes("low-quality");
    const retrievalFailure = query.includes("retrieval failure");
    const abstained = !source || conflict;
    const fallback = query.includes("fallback");
    const primaryState = conflict
      ? "CONFLICTING_EVIDENCE"
      : lowQuality
        ? "LOW_QUALITY_SOURCE"
        : retrievalFailure
          ? "RETRIEVAL_FAILURE"
          : query.includes("ambiguous")
            ? "AMBIGUOUS_QUERY"
            : abstained
              ? "KNOWLEDGE_ABSENT"
              : query.includes("two-document comparison")
                ? "SUPPORTED_COMPOSITE"
                : "SUPPORTED";
    const citationIds = source ? (conflict ? ["C1", "C2"] : ["C1"]) : [];
    const citations = source
      ? citationIds.map((citationId, index) => ({
          citation_label: citationId,
          chunk_id: `chunk-${current}-${index}`,
          document_id: `doc-${current}-${index}`,
          document_title: conflict ? `Travel Policy ${index ? "B" : "A"}` : source,
          excerpt: conflict
            ? `Meal allowance is PKR ${index ? "6,000" : "5,000"} per day.`
            : answer,
        }))
      : [];
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        answer,
        evidence: source
          ? [{
              chunk_id: `chunk-${current}`,
              document_id: `doc-${current}`,
              document_title: source,
              content: answer,
              score: 0.98,
              metadata: {},
            }]
          : [],
        citations,
        sufficient_evidence: !abstained,
        abstained,
        outcome: abstained
          ? query.includes("ambiguous") ? "CLARIFICATION_REQUIRED" : "KNOWLEDGE_ABSENT"
          : "ANSWER_SUPPORTED",
        support_status: abstained ? "ABSENT" : "SUPPORTED",
        confidence_category: abstained ? "none" : "high",
        retrieval_diagnosis: {
          status: query.includes("ambiguous")
            ? "AMBIGUOUS_QUERY"
            : abstained ? "KNOWLEDGE_ABSENT" : "SUFFICIENT_EVIDENCE",
          initial_evidence_sufficient: !abstained,
          retry_performed: false,
          retry_strategy: [],
          initial_support_score: abstained ? 0 : 0.98,
          final_support_score: abstained ? 0 : 0.98,
          evidence_count: source ? 1 : 0,
          reason_code: abstained ? "NO_AUTHORIZED_SUPPORT" : "SUPPORTED",
          semantic_used: !fallback,
          reranker_used: !fallback,
          fallback_used: fallback,
          selected_document_scope: query.includes("selected-document"),
          candidate_count: source ? 3 : 0,
          final_evidence_count: source ? 1 : 0,
          retrieval_duration_ms: 12,
        },
        active_document_scope: source
          ? [{ document_id: `doc-${current}`, title: source }]
          : [],
        response_state: {
          primary_state: primaryState,
          answer: abstained ? null : answer,
          claims: abstained
            ? []
            : citationIds.map((citationId, index) => ({
                claim_id: `claim-${index + 1}`,
                text: answer,
                citation_ids: [citationId],
              })),
          citation_ids: citationIds,
          citation_document_ids: Object.fromEntries(
            citationIds.map((citationId, index) => [citationId, `doc-${current}-${index}`]),
          ),
          evidence_decision: conflict
            ? "CONFLICTING"
            : primaryState === "KNOWLEDGE_ABSENT"
              ? "ABSENT"
              : retrievalFailure
                ? "UNAVAILABLE"
                : lowQuality
                  ? "PARTIAL"
                  : "SUFFICIENT",
          conflict: {
            category: conflict ? "VALUE_CONFLICT" : "NO_CONFLICT",
            unresolved: conflict,
            material: conflict,
            sides: conflict
              ? [
                  { claim_id: "a", text: "PKR 5,000 per day", citation_ids: ["C1"], applicability: "applicable" },
                  { claim_id: "b", text: "PKR 6,000 per day", citation_ids: ["C2"], applicability: "applicable" },
                ]
              : [],
          },
          confidence: {
            retrieval: abstained ? "NOT_APPLICABLE" : "HIGH",
            evidence_support: abstained ? "NOT_APPLICABLE" : "HIGH",
            conflict: conflict ? "HIGH" : "NOT_APPLICABLE",
            final: abstained ? (conflict ? "LOW" : "NOT_APPLICABLE") : "HIGH",
          },
          retrieval: {
            mode: fallback ? "lexical_fallback" : "hybrid",
            semantic_applied: !fallback,
            reranker_applied: !fallback,
            lexical_fallback_used: fallback,
            recovery_attempted: false,
            recovery_succeeded: false,
            failure_category: retrievalFailure ? "retrieval_unavailable" : null,
          },
          scope: { selected_document_scope: false, authorized_document_ids: [] },
          diagnostics: {},
          user_message: answer,
        },
      }),
    });
  });
  await page.goto("/");
  await page.evaluate(() => {
    localStorage.setItem("ekip_token", "isolated-phase2b-token");
    localStorage.setItem("ekip_workspace", "isolated-phase2b-workspace");
  });
  await page.goto("/search");

  for (current = 0; current < cases.length; current += 1) {
    const [query, answer, source] = cases[current];
    await page.getByTestId("search-query").fill(query);
    await page.getByTestId("search-submit").click();
    await expect(page.getByTestId("search-answer")).toHaveText(answer);
    if (source) {
      await expect(page.getByTestId("search-citations")).toContainText(source);
      if (!query.includes("true value conflict")) {
        await expect(page.getByTestId("search-citations")).toContainText(answer);
      }
    } else {
      await expect(page.getByTestId("search-citations")).toContainText("No validated citations");
    }
  }
  await expect(page.getByTestId("search-outcome").locator("strong")).toHaveCount(1);
  for (const viewport of [
    { width: 1440, height: 900 },
    { width: 820, height: 1180 },
    { width: 390, height: 844 },
  ]) {
    await page.setViewportSize(viewport);
    await expect
      .poll(() => page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1))
      .toBeTruthy();
  }
  await expect
    .poll(() => page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1))
    .toBeTruthy();
  expect(await page.getByTestId("search-result").textContent()).not.toMatch(
    /raw_vector|embedding_values|\/Users\/|\.cache\/|model path/i,
  );
  expect(consoleErrors).toEqual([]);
});
