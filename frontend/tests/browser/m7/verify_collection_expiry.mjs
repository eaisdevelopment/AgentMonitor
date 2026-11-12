"use strict";

// Read an existing genuine expired run. Never enqueue collection or change setup.
const [expectedRevision, runId] = process.argv.slice(2);
const origin = "http://127.0.0.1:43110";
let page, status = "failed", reason = "invalid_probe_arguments", revision = null;
let mutations = 0;
const checks = { history_api: false, run_status: false, history_ui: false };
function stop(state, code) { status = state; reason = code; throw new Error("probe_stopped"); }
function requireEvidence(value, code) { if (!value) stop("failed", code); }
try {
  requireEvidence(/^[a-f0-9]{40}$/.test(expectedRevision ?? "") && /^usage-manual-run-[a-f0-9]{40}$/.test(runId ?? ""), "invalid_probe_arguments");
  const { chromium } = await import("/home/dev/.local/share/agentmonitor/worktrees/dashboard-product-promotion/frontend/node_modules/@playwright/test/index.mjs");
  const browser = await chromium.connectOverCDP("http://127.0.0.1:9225", { timeout: 5000 });
  const context = browser.contexts()[0];
  if (!context) stop("blocked", "browser_context_unavailable");
  page = await context.newPage();
  page.setDefaultTimeout(10000);
  page.on("request", request => { if (!["GET", "HEAD", "OPTIONS"].includes(request.method())) mutations += 1; });
  async function read(path) {
    const response = await page.request.get(origin + path, { headers: { Origin: origin }, timeout: 10000 });
    if (response.status() === 401) stop("blocked", "authentication_required");
    requireEvidence(response.ok(), "collection_read_failed");
    return response.json();
  }
  const versions = await read("/api/v1/operations/versions");
  revision = versions.source_revision?.value ?? null;
  requireEvidence(revision === expectedRevision, "installed_revision_mismatch");
  let selected, cursor;
  for (let index = 0; index < 20; index += 1) {
    const query = new URLSearchParams({ provider_key: "ollama", limit: "200" });
    if (cursor) query.set("cursor", cursor);
    const history = await read("/api/v1/collection-runs?" + query);
    requireEvidence(history.availability.state === "available", "history_unavailable");
    selected = history.items.find(run => run.run_id === runId);
    if (selected || !history.page.has_more) break;
    cursor = history.page.next_cursor;
    requireEvidence(typeof cursor === "string" && cursor.length > 0, "history_cursor_missing");
  }
  requireEvidence(selected, "selected_expired_run_not_found");
  requireEvidence(selected.state === "failed" && selected.error_code === "collection_queued_expired" && selected.started_at === null && selected.duration_ms === null && selected.observation_ids.length === 0, "expired_history_changed_meaning");
  checks.history_api = true;
  const run = await read(`/api/v1/accounts/${encodeURIComponent(selected.account_id)}/cloud-usage/${encodeURIComponent(selected.resource_id)}/runs/${encodeURIComponent(runId)}`);
  requireEvidence(run.state === "failed" && run.error_code === selected.error_code && run.started_at === null && run.report_id === null && run.completed_at === selected.completed_at, "expired_status_changed_meaning");
  checks.run_status = true;
  await page.goto(origin, { waitUntil: "domcontentloaded" });
  await page.getByRole("button", { name: "Collection / History", exact: true }).click();
  const panel = page.getByRole("region", { name: "Collection runs", exact: true });
  await panel.locator(".state-available").waitFor();
  requireEvidence(await panel.locator("[data-collection-run]").count() > 0, "history_rows_missing");
  requireEvidence(await panel.getByRole("alert").count() === 0, "history_error_visible");
  checks.history_ui = true;
  requireEvidence(mutations === 0, "unexpected_mutation");
  status = "passed"; reason = null;
} catch (error) {
  if (error?.message !== "probe_stopped") { status = "failed"; reason = "probe_execution_failed"; }
} finally {
  if (page) await page.close().catch(() => {});
}
process.stdout.write(JSON.stringify({
  status, reason, revision, checks, mutations, observed_at: new Date().toISOString(),
  scope: "existing_expired_run_and_collection_history_read_only",
}) + "\n", () => process.exit({ passed: 0, failed: 1, blocked: 3 }[status]));
