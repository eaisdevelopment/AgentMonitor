"use strict";

import { readFileSync } from "node:fs";
import { chromium } from "@playwright/test";

const origin = process.argv[2];
const accountId = process.argv[3];
const credential = readFileSync(0, "utf8");
let browser;
let stage = "input_validation";
let historyPaginationOutcome = "NOT RUN — the real first history page did not expose a continuation cursor";

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
    if (/^\/api\/v1\/(accounts|capacity\/history|process-metrics|processes|sessions|collection-runs)/.test(url.pathname)) {
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
  for (const field of [
    "Observation",
    "Collection run",
    "Observed",
    "Collected",
    "Stored",
    "Source",
    "Source class",
    "Adapter",
    "Mechanism version",
    "Provider version",
    "Freshness deadline",
    "Freshness policy",
    "Precision",
    "Confidence",
  ]) {
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
    const provenance = quotaRow.locator(".quota-provenance");
    const provenanceText = await provenance.innerText();
    requireTruth(!/Unavailable in API v1/u.test(provenanceText), "quota_provenance_missing_from_api");
    requireTruth(/claude\.usage\.ax-screen-reader\.v1/u.test(provenanceText), "quota_source_id_missing");
    requireTruth(/supported cli/iu.test(provenanceText), "quota_source_class_missing");
    requireTruth(/agentmonitor\.claude\s*·\s*1\.0\.2/u.test(provenanceText), "quota_adapter_version_missing");
    requireTruth(/Mechanism version\s*1/u.test(provenanceText), "quota_mechanism_version_missing");
    requireTruth(/Provider version\s*2\.1\.278/u.test(provenanceText), "quota_provider_version_missing");
    requireTruth(/claude-usage-five-minute-v1/u.test(provenanceText), "quota_freshness_policy_missing");
    requireTruth(/Precision\s*rounded/iu.test(provenanceText), "quota_precision_missing");
    requireTruth(/confirmed/iu.test(provenanceText), "quota_confidence_missing");
    quotaLineage.push({ collectionRunId, observationId });
  }

  stage = "capacity_history";
  await page.getByRole("heading", { name: "Capacity history", exact: true }).waitFor();
  const historyTable = page.getByRole("table", { name: "Capacity history exact values" });
  await historyTable.waitFor();
  const historyRows = historyTable.locator("tbody tr");
  requireTruth(await historyRows.count() > 0, "real_capacity_history_missing");
  const historyObservationIds = (await historyRows.locator(".history-observation-id").allTextContents()).map((value) => value.trim());
  const chart = page.getByRole("img", { name: "Capacity history trend" });
  await chart.waitFor();
  const chartObservationIds = (await chart.getAttribute("data-observation-ids"))?.split(" ").filter(Boolean) ?? [];
  requireTruth(JSON.stringify(chartObservationIds) === JSON.stringify(historyObservationIds), "history_chart_table_lineage_mismatch");
  requireTruth(historyObservationIds.every((value) => quotaLineage.some((lineage) => lineage.observationId === value)), "history_current_observation_lineage_mismatch");
  requireTruth((await historyRows.locator(".history-exact-value").allTextContents()).every((value) => value.trim().length > 0), "history_exact_value_missing");
  const historyPanel = page.locator(".history-panel");
  requireTruth(
    /Showing \d+ retained observations? from 1 bounded page\./u.test(await historyPanel.getByRole("status").innerText()),
    "history_page_state_missing",
  );
  const loadNextHistoryPage = historyPanel.getByRole("button", { name: "Load next history page", exact: true });
  if (await loadNextHistoryPage.count() === 1) {
    stage = "capacity_history_pagination";
    const nextHistoryResponse = page.waitForResponse((response) => {
      const url = new URL(response.url());
      return url.origin === origin && url.pathname === "/api/v1/capacity/history" &&
        url.searchParams.has("cursor") && response.request().method() === "GET";
    });
    await loadNextHistoryPage.click();
    const response = await nextHistoryResponse;
    requireTruth(response.status() === 200, "history_next_page_get_failed");
    const cursorUrl = new URL(response.url());
    requireTruth((cursorUrl.searchParams.get("cursor") ?? "").length > 0, "history_next_page_cursor_missing");
    await page.waitForFunction(
      (previousCount) => document.querySelectorAll('[aria-label="Capacity history exact values"] tbody tr').length > previousCount,
      historyObservationIds.length,
    );
    const pagedObservationIds = (await historyRows.locator(".history-observation-id").allTextContents()).map((value) => value.trim());
    requireTruth(pagedObservationIds.length <= historyObservationIds.length + 200, "history_next_page_exceeded_bound");
    requireTruth(new Set(pagedObservationIds).size === pagedObservationIds.length, "history_next_page_duplicate_observation");
    requireTruth(
      JSON.stringify(pagedObservationIds.slice(0, historyObservationIds.length)) === JSON.stringify(historyObservationIds),
      "history_first_page_not_preserved",
    );
    const pagedChartObservationIds = (await chart.getAttribute("data-observation-ids"))?.split(" ").filter(Boolean) ?? [];
    requireTruth(JSON.stringify(pagedChartObservationIds) === JSON.stringify(pagedObservationIds), "history_paged_chart_table_lineage_mismatch");
    requireTruth(/from 2 bounded pages\./u.test(await historyPanel.getByRole("status").innerText()), "history_loaded_page_count_missing");
    historyPaginationOutcome = "PASSED — real second cursor page retained exact chart/table lineage";
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
  await page.getByText("Reading runtime observations…", { exact: true }).waitFor({ state: "detached" });

  stage = "same_account_runtime";
  const sessionRows = page.locator(".session-row");
  requireTruth(await sessionRows.count() > 0, "real_same_account_session_missing");
  const sessionText = await sessionRows.first().innerText();
  requireTruth(/automatic matched/iu.test(sessionText), "session_not_automatically_correlated");
  requireTruth(/account correlated/iu.test(sessionText), "session_account_correlation_missing");
  await page.getByRole("heading", { name: "Session hierarchy", exact: true }).first().waitFor();
  const sessionTree = page.locator('[data-session-tree="true"]').first();
  requireTruth(await sessionTree.locator('[data-session-tree-node="true"]').count() > 0, "session_tree_node_missing");
  requireTruth(/included\s+\d+/iu.test(await sessionTree.innerText()), "session_tree_included_count_missing");
  requireTruth(/excluded\s+\d+/iu.test(await sessionTree.innerText()), "session_tree_excluded_count_missing");
  requireTruth(/unknown\s+\d+/iu.test(await sessionTree.innerText()), "session_tree_unknown_count_missing");
  await sessionRows.first().getByRole("button", { name: "Inspect provenance" }).click();
  await page.getByRole("heading", { name: "Observation provenance", exact: true }).waitFor();
  await page.getByText("Source", { exact: true }).first().waitFor();
  requireTruth(
    /claude\.otel\.metrics\.http-json\.v1/u.test(await page.locator(".session-detail").innerText()),
    "session_otel_provenance_missing",
  );
  for (const field of [
    "Observed",
    "Collected",
    "Freshness deadline",
    "Freshness policy",
    "Source class",
    "Adapter",
    "Mechanism version",
    "Parser version",
    "Provider protocol",
    "Provider version",
    "Precision",
    "Confidence",
    "Value kind",
    "Derivation method",
    "Input observations",
  ]) {
    await page.locator(".session-detail").getByText(field, { exact: true }).waitFor();
  }

  stage = "real_process_runtime";
  const processResponse = page.waitForResponse((response) => {
    const url = new URL(response.url());
    return url.origin === origin && url.pathname === "/api/v1/process-metrics" && response.request().method() === "GET";
  });
  await page.getByRole("button", { name: "Sessions", exact: true }).click();
  requireTruth((await processResponse).status() === 200, "process_observation_get_failed");
  await page.getByRole("heading", { name: "Sessions", exact: true }).waitFor();
  await page.getByText("Reading runtime observations…", { exact: true }).waitFor({ state: "detached" });
  const processTable = page.getByRole("region", { name: "Process observations table" });
  requireTruth(await processTable.count() === 1, "real_process_observation_missing");
  const processRows = processTable.locator("tbody tr");
  requireTruth(await processRows.count() > 0, "real_process_observation_missing");
  for (const heading of ["Parent PID", "Start marker", "CPU", "RSS memory", "Threads", "Kernel state", "Observed / freshness"]) {
    await processTable.getByRole("columnheader", { name: heading, exact: true }).waitFor();
  }
  for (let index = 0; index < await processRows.count(); index += 1) {
    const processRow = processRows.nth(index);
    const rowText = await processRow.innerText();
    requireTruth(/^claude\b/im.test(rowText), "process_provider_not_attributed");
    requireTruth(/\blinux\.proc\.process\.v1\b/i.test(rowText), "process_source_missing");
    requireTruth(/^\d+$/u.test((await processRow.locator(".process-parent-pid").innerText()).trim()), "process_parent_pid_missing");
    requireTruth(/\bticks\b/u.test(await processRow.locator(".process-cpu").innerText()), "process_cpu_ticks_missing");
    requireTruth(/\bpages\b/u.test(await processRow.locator(".process-memory").innerText()), "process_rss_memory_missing");
    requireTruth(/^\d+$/u.test((await processRow.locator(".process-threads").innerText()).trim()), "process_thread_count_missing");
    requireTruth(/^[A-Za-z]$/u.test((await processRow.locator(".process-kernel-state").innerText()).trim()), "process_kernel_state_missing");
    requireTruth(/ticks after boot/u.test(await processRow.locator(".process-start").innerText()), "process_safe_start_missing");
    const freshnessText = await processRow.locator(".process-freshness").innerText();
    const presenceText = (await processRow.locator(".process-presence").innerText()).trim();
    requireTruth(/Observed .* ago/u.test(freshnessText), "process_observation_age_missing");
    requireTruth(/Freshness (deadline|unavailable|unknown|unsupported|withheld|stale)/iu.test(freshnessText), "process_freshness_missing");
    requireTruth(/deadline passed/iu.test(freshnessText) ? presenceText === "unknown" : presenceText === "running", "process_presence_freshness_mismatch");
  }

  stage = "http_proof";
  const capacityPath = `/api/v1/accounts/${encodeURIComponent(accountId)}/capacity`;
  const quotaPath = `/api/v1/accounts/${encodeURIComponent(accountId)}/quotas`;
  requireTruth(safeGetResults.some((entry) => entry.pathname === capacityPath && entry.status === 200), "account_capacity_get_missing_or_failed");
  requireTruth(safeGetResults.some((entry) => entry.pathname === quotaPath && entry.status === 200), "account_quota_get_missing_or_failed");
  requireTruth(safeGetResults.some((entry) => entry.pathname === "/api/v1/capacity/history" && entry.status === 200), "capacity_history_get_missing_or_failed");
  requireTruth(safeGetResults.some((entry) => entry.pathname === "/api/v1/sessions" && entry.hasAccountFilter && entry.status === 200), "account_session_get_missing_or_failed");
  requireTruth(safeGetResults.some((entry) => /^\/api\/v1\/sessions\/[^/]+\/tree$/u.test(entry.pathname) && entry.status === 200), "session_tree_get_missing_or_failed");
  requireTruth(safeGetResults.some((entry) => entry.pathname === "/api/v1/process-metrics" && entry.status === 200), "process_observation_get_missing_or_failed");
  requireTruth(safeGetResults.some((entry) => entry.pathname === "/api/v1/collection-runs" && entry.status === 200), "collection_run_get_missing_or_failed");

  stage = "privacy";
  requireTruth(await page.getByText(/sample|demo|placeholder/i).count() === 0, "prohibited_telemetry_label");
  requireTruth(externalRequests.length === 0, "external_request");
  requireTruth(pageErrors.length === 0, "page_error");
  requireTruth(await page.evaluate(() => localStorage.length === 0 && sessionStorage.length === 0), "monitoring_data_in_browser_storage");
  requireTruth(!(await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 1)), "document_horizontal_overflow");

  stage = "responsive";
  for (const viewport of [{ width: 960, height: 540 }, { width: 390, height: 844 }]) {
    await page.setViewportSize(viewport);
    await page.goto(`${origin}/accounts/${encodeURIComponent(accountId)}`);
    await page.getByRole("heading", { name: "Quota windows", exact: true }).waitFor();
    await page.getByRole("heading", { name: "Capacity history", exact: true }).waitFor();
    await page.getByRole("heading", { name: "Running sessions", exact: true }).waitFor();
    requireTruth(!(await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 1)), `responsive_horizontal_overflow:${viewport.width}`);
  }

  await browser.close();
  console.log(`P02 POPULATED MONITORING: PASSED — real Claude quota history/chart, collection reconciliation, exact process runtime, and same-account session hierarchy/provenance; capacity pagination ${historyPaginationOutcome}`);
} catch (error) {
  if (browser) await browser.close();
  console.error(`P02 POPULATED MONITORING: FAILED — ${stage}: ${error instanceof Error ? error.message : "unknown"}`);
  process.exitCode = 1;
}
