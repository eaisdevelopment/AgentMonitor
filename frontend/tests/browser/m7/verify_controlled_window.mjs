"use strict";

// Own one NEW window only. Never close the shared browser/context or owner tabs.
import { createInterface } from "node:readline";
const revision = process.argv[2], phase = process.argv[3];
const origin = "http://127.0.0.1:43110";
let browser, session, page, targetId, windowId;
let stage = "input", status = "failed", reason = "controlled_window_invalid";
let unsafe = 0, windowClosed = false, observedAt = null;
let alertsReadContinuity = "not_run";
const input = createInterface({ input: process.stdin, crlfDelay: Infinity });
const lines = input[Symbol.asyncIterator]();
const requireEvidence = (condition, code) => { if (!condition) throw new Error(code); };
const instant = value => typeof value === "string" ? value.replace("+00:00", "Z").replace(/(?:\.(\d{1,6}))?Z$/, (_, digits) => `.${(digits ?? "").padEnd(6, "0")}Z`) : null;
const safeId = value => typeof value === "string" && /^[A-Za-z0-9._:-]{1,256}$/.test(value);
async function closeOwnedWindow() {
  if (!session || !targetId) return;
  const closed = await session.send("Target.closeTarget", { targetId });
  requireEvidence(closed.success === true, "controlled_target_close_failed");
  const targets = await session.send("Target.getTargets");
  requireEvidence(!targets.targetInfos.some(target => target.targetId === targetId), "controlled_target_remained");
  targetId = null;
  for (let attempt = 0; attempt < 20 && !windowClosed; attempt++) {
    try { await session.send("Browser.getWindowBounds", { windowId }); }
    catch {
      // A disconnected CDP transport is not evidence that the window vanished.
      await session.send("Target.getTargets");
      windowClosed = true;
    }
    if (!windowClosed) await new Promise(resolve => setTimeout(resolve, 100));
  }
  requireEvidence(windowClosed, "controlled_window_remained");
  observedAt = new Date().toISOString();
}
process.once("SIGTERM", () => {
  const timer = setTimeout(() => process.exit(1), 5000);
  closeOwnedWindow().catch(() => {}).finally(() => { clearTimeout(timer); process.exit(1); });
});
try {
  requireEvidence(/^[a-f0-9]{40}$/.test(revision ?? "") && ["close", "reopen"].includes(phase), "controlled_window_input_invalid");
  const value = JSON.parse((await lines.next()).value);
  requireEvidence(value && safeId(value.account_id) && safeId(value.resource_id), "controlled_window_input_invalid");
  for (const key of ["period_start", "period_end", "as_of"]) {
    requireEvidence(typeof value[key] === "string" && Number.isFinite(Date.parse(value[key])), "controlled_window_input_invalid");
    value[key] = value[key].replace("+00:00", "Z");
    requireEvidence(/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z$/.test(value[key]), "controlled_window_input_invalid");
  }
  requireEvidence(phase !== "reopen" || safeId(value.report_id), "controlled_window_input_invalid");
  const { chromium, expect } = await import("/home/dev/.local/share/agentmonitor/worktrees/dashboard-product-promotion/frontend/node_modules/@playwright/test/index.mjs");
  stage = "browser";
  browser = await chromium.connectOverCDP("http://127.0.0.1:9225", { timeout: 5000 });
  session = await browser.newBrowserCDPSession();
  const before = await session.send("Target.getTargets");
  const windows = new Set();
  for (const target of before.targetInfos.filter(target => target.type === "page")) {
    try { windows.add((await session.send("Browser.getWindowForTarget", { targetId: target.targetId })).windowId); }
    catch { /* An owner target may close independently; it is never controlled here. */ }
  }
  ({ targetId } = await session.send("Target.createTarget", { url: "about:blank", newWindow: true, background: true }));
  ({ windowId } = await session.send("Browser.getWindowForTarget", { targetId }));
  requireEvidence(!windows.has(windowId), "controlled_window_not_distinct");
  for (let attempt = 0; attempt < 50 && !page; attempt++) {
    for (const context of browser.contexts()) for (const candidate of context.pages()) {
      let attached;
      try {
        attached = await context.newCDPSession(candidate);
        const info = await attached.send("Target.getTargetInfo");
        if (info.targetInfo.targetId === targetId) page = candidate;
      } catch { /* Never adopt an unproven target. */ }
      finally { if (attached) await attached.detach().catch(() => {}); }
    }
    if (!page) await new Promise(resolve => setTimeout(resolve, 100));
  }
  requireEvidence(page !== undefined, "controlled_target_unavailable");
  page.setDefaultTimeout(10000);
  page.on("request", request => { if (!["GET", "HEAD", "OPTIONS"].includes(request.method())) unsafe++; });
  const query = new URLSearchParams({ budget_resource: value.resource_id, budget_start: value.period_start, budget_end: value.period_end, budget_as_of: value.as_of });
  if (phase === "reopen") query.set("budget_report", value.report_id);
  stage = "authentication";
  await page.goto(`${origin}/accounts/${encodeURIComponent(value.account_id)}?${query}`, { waitUntil: "domcontentloaded", timeout: 15000 });
  const read = async path => {
    const response = await page.request.get(`${origin}${path}`, { headers: { Origin: origin }, timeout: 10000, failOnStatusCode: false });
    if (response.status() === 401 || response.status() === 403) throw new Error("authentication_required");
    requireEvidence(response.ok(), "controlled_financial_read_failed");
    return response.json();
  };
  const versions = await read("/api/v1/operations/versions");
  requireEvidence(versions.source_revision?.availability === "available" && versions.source_revision.source === "build_manifest" && versions.source_revision.value === revision, "controlled_revision_mismatch");
  stage = "financial_view";
  const financial = page.getByRole("region", { name: "API usage & spend", exact: true });
  await expect(financial).toBeVisible();
  await expect(financial).toHaveAttribute("aria-busy", "false");
  const summary = await read(`/api/v1/accounts/${encodeURIComponent(value.account_id)}/budgets?${new URLSearchParams({ period_start: value.period_start, period_end: value.period_end, as_of: value.as_of })}`);
  requireEvidence(summary.account_id === value.account_id && summary.cloud_resources?.some(resource => resource.resource_id === value.resource_id), "controlled_financial_resource_missing");
  requireEvidence(instant(await financial.locator("[data-budget-window]").getAttribute("data-read-as-of")) === instant(value.as_of), "controlled_cutoff_mismatch");
  if (phase === "close") {
    await expect(financial.locator(`[data-cloud-reading="${value.resource_id}"]`)).toBeVisible();
  } else {
    stage = "new_report";
    const selected = financial.getByRole("region", { name: "Selected financial report", exact: true });
    await expect(selected).toBeVisible();
    const history = selected.locator("[data-budget-history]");
    await expect(history).toHaveAttribute("data-budget-history", value.report_id);
    await expect(history).toHaveAttribute("aria-busy", "false");
    const source = await read(`/api/v1/budgets/${encodeURIComponent(value.resource_id)}/history?${new URLSearchParams({ account_id: value.account_id, report_id: value.report_id, period_start: value.period_start, period_end: value.period_end, as_of: value.as_of, limit: "50" })}`);
    requireEvidence(source.report.report_id === value.report_id && source.report.account_id === value.account_id && source.report.resource_id === value.resource_id && source.availability.state === "available" && instant(source.as_of) === instant(value.as_of), "controlled_new_report_mismatch");
    const expected = source.items.map(row => `${row.kind}:${(row.cost ?? row.usage).bucket_key}`).sort();
    const rendered = await history.locator("[data-bucket-key]").evaluateAll(nodes => nodes.map(node => `${node.getAttribute("data-bucket-kind")}:${node.getAttribute("data-bucket-key")}`).sort());
    requireEvidence(JSON.stringify(rendered) === JSON.stringify(expected), "controlled_history_facts_mismatch");
    await expect(history.locator(':scope > [role="alert"]')).toHaveCount(0);
  }
  stage = "alerts_read_continuity";
  const alertView = async navigate => {
    const responseFor = path => page.waitForResponse(response => {
      const url = new URL(response.url());
      return response.request().method() === "GET" && url.origin === origin && url.pathname === path
        && !url.searchParams.has("scope_kind") && !url.searchParams.has("cursor");
    }, { timeout: 10000 });
    const [listResponse, countResponse] = await Promise.all([
      responseFor("/api/v1/alert-notifications"),
      responseFor("/api/v1/alert-notifications/counts"),
      navigate(),
    ]);
    if ([listResponse.status(), countResponse.status()].some(code => code === 401 || code === 403)) throw new Error("authentication_required");
    requireEvidence(listResponse.status() === 200 && countResponse.status() === 200, "controlled_alert_read_failed");
    const [list, counts] = await Promise.all([listResponse.json(), countResponse.json()]);
    requireEvidence(list.availability?.state === "available" && Array.isArray(list.items), "controlled_alert_list_unavailable");
    const panel = page.locator(".alerts-page");
    await expect(panel).toBeVisible();
    await expect(panel).toHaveAttribute("aria-busy", "false");
    await expect(panel.getByRole("alert")).toHaveCount(0);
    await expect(panel.locator(".alert-list > .alert-card")).toHaveCount(list.items.length);
    const summary = panel.locator('[aria-label="Alert counts"]');
    for (const [key, label] of [["active_critical", "critical"], ["active_warning", "warning"], ["visible_unread", "unread"], ["snoozed", "snoozed"]]) {
      requireEvidence(Number.isSafeInteger(counts[key]) && counts[key] >= 0, "controlled_alert_counts_invalid");
      await expect(summary.getByText(`${counts[key]} ${label}`, { exact: true })).toBeVisible();
    }
    if (list.items.length === 0) await expect(panel.getByText("No active alerts.", { exact: true })).toBeVisible();
  };
  await alertView(() => page.getByRole("button", { name: "Alerts", exact: true }).click());
  await alertView(() => page.reload({ waitUntil: "domcontentloaded", timeout: 15000 }));
  alertsReadContinuity = "passed";
  requireEvidence(unsafe === 0, "controlled_window_mutation_observed");
  stage = "close_owned_window";
  await closeOwnedWindow();
  status = "passed"; reason = null;
} catch (error) {
  const code = error instanceof Error ? error.message : "";
  reason = /^(?:controlled_[a-z_]+|authentication_required)$/.test(code) ? code : "controlled_window_unavailable";
  status = reason === "authentication_required" ? "blocked" : "failed";
} finally {
  if (targetId) await closeOwnedWindow().catch(() => { status = "failed"; reason = "controlled_window_cleanup_failed"; });
  input.close();
}
// Process exit disconnects this CDP client; never invoke Browser.close/context.close.
process.stdout.write(JSON.stringify({ record_type: "agentmonitor.m7_controlled_window.v1", status, reason_code: reason, stage, source_revision: revision, phase, window_closed: windowClosed, unsafe_requests: unsafe, observed_at: observedAt, alerts_read_continuity: alertsReadContinuity, alerts_scope: "available_list_counts_and_reload" }) + "\n", () => process.exit({ passed: 0, failed: 1, blocked: 3 }[status]));
