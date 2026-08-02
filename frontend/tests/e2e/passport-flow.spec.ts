import { expect, test } from "@playwright/test";

const passportId = "urn:uuid:00000000-0000-0000-0000-000000000042";

test("supported answer exposes an accessible authorized passport workflow", async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem("ekip_token", "synthetic-browser-token");
    localStorage.setItem("ekip_workspace", "00000000-0000-0000-0000-000000000001");
  });
  await page.route("**/api/v1/documents", (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: "[]" }),
  );
  await page.route("**/api/v1/search", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        answer: "The approved allowance is PKR 5,000 per day.",
        evidence: [],
        sufficient_evidence: true,
        abstained: false,
        outcome: "ANSWER_SUPPORTED",
        support_status: "SUPPORTED",
        confidence_category: "high",
        citations: [],
        conflicts: [],
        active_document_scope: [],
        generation_provider: "extractive",
        generation_model: "deterministic-extractive-v2",
        generation_used: false,
        generation_fallback_used: false,
        generation_duration_ms: 0,
        generation_verification: "not_applicable",
        structured_output_valid: false,
        claim_verification_passed: false,
        passport_reference: {
          passport_id: passportId,
          schema_version: "vap-1",
          metadata_available: true,
          export_available: true,
        },
      }),
    }),
  );
  await page.route(`**/api/v1/answer-passports/${encodeURIComponent(passportId)}`, (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        passport_id: passportId,
        schema_version: "vap-1",
        issued_at: "2026-08-02T12:00:00Z",
        expires_at: "2026-09-02T12:00:00Z",
        signer_key_id: "synthetic-public-key",
        issuer_id: "opaque-issuer",
        artifact_integrity: "VALID",
        status: "VERIFIED",
        freshness: "CURRENT",
        key_lifecycle_status: "ACTIVE",
        trust_bundle_version: 1,
        trust_bundle_checksum: "public-checksum",
        export_available: true,
      }),
    }),
  );
  await page.route(`**/api/v1/answer-passports/${encodeURIComponent(passportId)}/export`, (route) =>
    route.fulfill({
      status: 200,
      headers: {
        "Content-Type": "application/vnd.ekip.answer-passport+zip",
        "Content-Disposition": 'attachment; filename="../../unsafe-server-name.zip"',
      },
      body: Buffer.from("opaque-synthetic-zip"),
    }),
  );
  await page.route("**/api/v1/passport-trust-bundles/current", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        bundle: "public-lifecycle-data",
        verifier_bundle: '{"schema_version":"vap-trust-1","keys":[]}',
        signature: null,
        trust_mode: "unsigned-development",
        bundle_version: 1,
        bundle_checksum: "public-checksum",
        bootstrap_notice: "Independent trust required.",
      }),
    }),
  );

  await page.goto("/search");
  await page.getByTestId("search-query").fill("What is the approved allowance?");
  await page.getByTestId("search-submit").click();
  await expect(page.getByTestId("search-answer")).toHaveText(
    "The approved allowance is PKR 5,000 per day.",
  );
  await expect(page.getByTestId("passport-card")).toContainText("signed verification record");
  await page.getByRole("button", { name: "View assurance details" }).focus();
  await page.keyboard.press("Enter");
  await expect(page.getByText("Verified with current trust")).toBeVisible();
  await expect(page.getByText(/does not by itself establish initial trust/i)).toBeVisible();

  const passportDownload = page.waitForEvent("download");
  await page.getByRole("button", { name: "Download passport ZIP" }).click();
  expect((await passportDownload).suggestedFilename()).toBe(
    "answer-passport-00000000-0000-0000-0000-000000000042.zip",
  );

  const trustDownload = page.waitForEvent("download");
  await page.getByRole("button", { name: /download public verification trust bundle/i }).click();
  expect((await trustDownload).suggestedFilename()).toBe("answer-passport-trust-bundle.json");
  expect(await page.evaluate(() => Object.keys(localStorage).sort())).toEqual([
    "ekip_token",
    "ekip_workspace",
  ]);
  expect(await page.locator("body").innerText()).not.toMatch(/private key|detached signature|raw manifest/i);
});
