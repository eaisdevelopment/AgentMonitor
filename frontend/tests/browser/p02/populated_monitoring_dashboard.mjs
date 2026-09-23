"use strict";

import { readFileSync } from "node:fs";
import { chromium } from "@playwright/test";

const origin = process.argv[2];
const accountId = process.argv[3];
const credential = readFileSync(0, "utf8");
let browser;
let stage = "input_validation";
let runtimeOutcome = "BLOCKED — no same-account session observation";

function requireTruth(condition, reason) {
  if (!condition) throw new Error(reason);
}

try {
  const originUrl = new URL(origin);
  requireTruth(originUrl.protocol === "http:" && originUrl.hostname === "127.0.0.1" && originUrl.port !== "" && originUrl.origin === origin, "invalid_loopback_origin");
  requireTruth(typeof accountId === "string" && accountId.length > 0 && accountId.length <= 256, "invalid_opaque_account_id");
  browser = await chromium.launch({ channel: "chrome", headless: true });
  const context = await browser.newContext({
    baseURL: origin,
    viewport: { width: 1920, height: 1080 },
    reducedMotion: "reduce",
  });
  const page = await context.newPage();
  const externalRequests = [];
  const pageErrors = [];
  const safeGetResults = [];
  page.on("request", (request) => {
    if (new URL(request.url()).origin !== origin) externalRequests.push(new URL(request.url()).hostname);
  });
  page.on("pageerror", (error) => pageErrors.push(error.name));
  page.on("response", (response) => {
    const request = response.request();
    const url = new URL(response.url());
    if (url.origin !== origin || request.method() !== "GET") return;
    if (/^\/api\/v1\/(accounts|sessions|collection-runs)/.test(url.pathname)) {
      safeGetResults.push({ pathname: url.pathname, hasAccountFilter: url.searchParams.has("account_id"), status: response.status() });
    }
  });

  stage = "login";
  await page.goto(`${origin}/login`);
  await page.getByRole("heading", { name: "Sign in" }).waitFor();
  await page.getByLabel("Administrator password").fill(credential);
  await page.getByRole("button", { name: "Sign in" }).click();
  await page.getByRole("heading", { name: "AgentMonitor" }).waitFor();

  stage = "account_page";
  const document = await page.goto(`${origin}/accounts/${encodeURIComponent(accountId)}`);
  requireTruth(document?.status() === 200, "account_shell_route_missing");
  await page.locator("h1#page-title").waitFor();
  await page.getByRole("heading", { name: "Quota windows", exact: true }).waitFor();
  await page.getByRole("heading", { name: "Running sessions", exact: true }).waitFor();
  requireTruth(await page.locator(".identity-panel dd").filter({ hasText: /^claude$/i }).count() === 1, "real_claude_account_not_rendered");

  stage = "quota";
  await page.getByRole("table", { name: "Provider-reported windows with exact values and freshness" }).waitFor();
  const quotaRows = page.locator('[aria-label="Quota windows table"] tbody tr');
  const quotaRowCount = await quotaRows.count();
  requireTruth(quotaRowCount > 0, "real_quota_window_missing");
  await page.locator(".quota-provenance").first().waitFor();
  for (const field of ["Observation", "Collection run", "Collected", "Stored", "Source/version"]) {
    await page.getByText(field, { exact: true }).first().waitFor();
  }
  requireTruth(await page.locator(".health-strip").count() > 0, "capacity_health_explanation_missing");
  const quotaLineage = [];
  for (let index = 0; index < quotaRowCount; index += 1) {
    const quotaRow = quotaRows.nth(index);
    const collectionRunId = (await quotaRow.locator(".quota-collection-run-id").textContent())?.trim();
    const observationId = (await quotaRow.locator(".quota-observation-id").textContent())?.trim();
    requireTruth(collectionRunId !== undefined && collectionRunId.length > 0, "quota_collection_run_id_missing");
    requireTruth(observationId !== undefined && observationId.length > 0, "quota_observation_id_missing");
    const sourceVersion = quotaRow.getByText("Unavailable in API v1", { exact: true });
    await sourceVersion.scrollIntoViewIfNeeded();
    requireTruth(await sourceVersion.isVisible(), "quota_source_version_state_not_visible");
    quotaLineage.push({ collectionRunId, observationId });
  }

  stage = "collection_run_reconciliation";
  const collectionResponse = page.waitForResponse((response) => {
    const url = new URL(response.url());
    return url.origin === origin && url.pathname === "/api/v1/collection-runs" && response.request().method() === "GET";
  });
  await page.getByRole("button", { name: "Collectors", exact: true }).click();
  requireTruth((await collectionResponse).status() === 200, "collection_run_get_failed");
  await page.getByRole("heading", { name: "Collection runs", exact: true }).waitFor();
  await page.getByText("Reading collection history…", { exact: true }).waitFor({ state: "detached" });
  const runCards = page.locator('[data-collection-run="true"]');
  const renderedRunIds = (await runCards.locator(".collection-run-id").allTextContents()).map((value) => value.trim());
  for (const lineage of quotaLineage) {
    const matchingRunIndex = renderedRunIds.indexOf(lineage.collectionRunId);
    requireTruth(matchingRunIndex >= 0, `quota_collection_run_not_rendered:${renderedRunIds.length}`);
    const matchingRun = runCards.nth(matchingRunIndex);
    await matchingRun.getByText(lineage.observationId, { exact: false }).waitFor();
    for (const field of ["Source", "Adapter version", "Provider version", "Requested", "Started", "Completed", "Observations"]) {
      await matchingRun.getByText(field, { exact: true }).waitFor();
    }
    requireTruth(!/(Unavailable|Not reported|None reported)/.test(await matchingRun.locator(".run-provenance").innerText()), "collection_run_provenance_incomplete");
  }

  stage = "return_to_account";
  await page.goto(`${origin}/accounts/${encodeURIComponent(accountId)}`);
  await page.getByRole("heading", { name: "Running sessions", exact: true }).waitFor();

  stage = "same_account_runtime";
  const sessionRows = page.locator(".session-row");
  if (await sessionRows.count() > 0) {
    await sessionRows.first().getByRole("button", { name: "Inspect provenance" }).click();
    await page.getByRole("heading", { name: "Observation provenance", exact: true }).waitFor();
    await page.getByText("Source", { exact: true }).first().waitFor();
    runtimeOutcome = "PASSED — real same-account session provenance";
  } else {
    await page.getByText(/No observed sessions|Session observation (unavailable|unsupported|unknown)/).waitFor();
  }

  stage = "http_proof";
  const capacityPath = `/api/v1/accounts/${encodeURIComponent(accountId)}/capacity`;
  const quotaPath = `/api/v1/accounts/${encodeURIComponent(accountId)}/quotas`;
  requireTruth(safeGetResults.some((entry) => entry.pathname === capacityPath && entry.status === 200), "account_capacity_get_missing_or_failed");
  requireTruth(safeGetResults.some((entry) => entry.pathname === quotaPath && entry.status === 200), "account_quota_get_missing_or_failed");
  requireTruth(safeGetResults.some((entry) => entry.pathname === "/api/v1/sessions" && entry.hasAccountFilter && entry.status === 200), "account_session_get_missing_or_failed");
  requireTruth(safeGetResults.some((entry) => entry.pathname === "/api/v1/collection-runs" && entry.status === 200), "collection_run_get_missing_or_failed");

  stage = "privacy";
  requireTruth(await page.getByText(/sample|demo|placeholder/i).count() === 0, "prohibited_telemetry_label");
  requireTruth(externalRequests.length === 0, "external_request");
  requireTruth(pageErrors.length === 0, "page_error");
  requireTruth(await page.evaluate(() => localStorage.length === 0 && sessionStorage.length === 0), "monitoring_data_in_browser_storage");
  requireTruth(!(await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 1)), "document_horizontal_overflow");

  await browser.close();
  console.log(`P02 POPULATED MONITORING: PASSED — real Claude account/quota/collection reconciliation; quota source/version BLOCKED — absent from API v1; runtime ${runtimeOutcome}`);
} catch (error) {
  if (browser) await browser.close();
  console.error(`P02 POPULATED MONITORING: FAILED — ${stage}: ${error instanceof Error ? error.message : "unknown"}`);
  process.exitCode = 1;
}
