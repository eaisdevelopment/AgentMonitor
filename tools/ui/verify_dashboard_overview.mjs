/** Verify the actual owner overview against its versioned account readings. */
import { chromium } from "../../frontend/node_modules/@playwright/test/index.mjs";

const endpoint = process.env.AGENTMONITOR_TEST_DASHBOARD_CDP_ENDPOINT;
const origin = process.env.AGENTMONITOR_TEST_DASHBOARD_ORIGIN;
let stage = "prerequisites";
function requireResult(condition, reason) { if (!condition) throw new Error(reason); }
function percentage(field) {
  if (!field || !["available", "stale"].includes(field.availability) || field.value === null || !["ratio", "percent"].includes(field.value.unit)) return null;
  const value = Number(field.value.coefficient) * 10 ** ((field.value.unit === "ratio" ? 2 : 0) - field.value.scale);
  return Number.isFinite(value) && value >= 0 && value <= 100 ? `${Number(value.toFixed(2))}%` : null;
}

try {
  requireResult(endpoint && origin && new URL(endpoint).hostname === "127.0.0.1" && new URL(origin).hostname === "127.0.0.1", "explicit_loopback_dashboard_required");
  const browser = await chromium.connectOverCDP(endpoint);
  const page = browser.contexts()[0]?.pages()[0];
  requireResult(page && await page.evaluate(() => location.origin) === origin, "shared_dashboard_required");
  const snapshot = await page.evaluate(async () => {
    const read = async path => { const r = await fetch(path); if (!r.ok) throw new Error("versioned_read_unavailable"); return r.json(); };
    const accounts = await read("/api/v1/accounts?limit=200");
    const organizations = await read("/api/v1/organizations?limit=200");
    const rows = [];
    for (const account of accounts.items.filter(item => item.lifecycle !== "archived")) {
      const capacity = await read(`/api/v1/accounts/${account.account_id}/capacity`);
      rows.push({ account, capacity });
    }
    return { rows, organizations };
  });
  requireResult(snapshot.rows.length > 0 && snapshot.rows.some(row => row.capacity.items.some(item => item.windows.length > 0)), "real_account_quota_required");
  let mutations = 0;
  page.on("request", request => { if (new URL(request.url()).origin === origin && request.url().includes("/api/v1/") && !["GET", "HEAD"].includes(request.method())) mutations += 1; });
  await page.goto(origin);
  stage = "account_quota_overview";
  const table = page.getByRole("table", { name: "Account quota overview", exact: true });
  await table.waitFor({ timeout: 10_000 });
  for (const label of ["Account", "Organization", "State", "Quota left", "Updated"]) requireResult(await table.getByRole("columnheader", { name: label, exact: true }).count() === 1, "overview_column_missing");
  for (const { account, capacity } of snapshot.rows) {
    const row = table.locator(`tbody tr[data-account-id="${account.account_id}"]`);
    await row.waitFor();
    const accountLink = row.getByRole("button", { name: /^Open account / });
    requireResult(await accountLink.count() === 1, "account_detail_action_missing");
    requireResult(await accountLink.evaluate(node => node.getAttribute("aria-label")?.includes(node.textContent.trim())), "account_action_visible_label_missing_from_accessible_name");
    const organization = snapshot.organizations.items.find(item => item.organization_id === account.organization_id);
    requireResult(await row.getByText(account.organization_id === null ? "Ungrouped" : organization?.name ?? "Unavailable", { exact: true }).count() > 0, "account_organization_missing");
    const windows = capacity.items.flatMap(item => item.windows);
    if (account.lifecycle === "pending") requireResult(await row.getByText("Not connected", { exact: true }).count() === 1, "pending_state_missing");
    else if (account.is_effective_monitoring_enabled && windows.length > 0) {
      if (windows.every(window => window.freshness === "fresh")) requireResult(await row.getByText("Current", { exact: true }).count() === 1, "fresh_quota_state_missing");
      else if (windows.some(window => window.freshness === "stale")) requireResult(await row.getByText("Stale", { exact: true }).count() === 1, "stale_quota_state_missing");
    }
    for (const window of capacity.items.flatMap(item => item.windows)) {
      const expected = percentage(window.allowance?.remaining_percentage ?? window.remaining_ratio);
      const reading = row.locator(`[data-window-id="${window.window_id}"]`);
      await reading.waitFor();
      requireResult(await reading.getByText(window.safe_label ?? window.window_key, { exact: true }).count() === 1, "quota_window_label_missing");
      if (expected !== null) {
        requireResult(await reading.getByText(expected, { exact: true }).count() === 1, "account_percentage_mismatch");
        requireResult(await reading.getByRole("meter").count() === 1, "account_quota_bar_missing");
      }
    }
    requireResult(await row.locator("time").count() > 0 || capacity.items.every(item => item.windows.length === 0), "account_update_time_missing");
  }
  stage = "compact_responsive";
  const prior = page.viewportSize() ?? await page.evaluate(() => ({ width: innerWidth, height: innerHeight }));
  try {
    for (const viewport of [{ width: 1920, height: 1080 }, { width: 1280, height: 800 }, { width: 390, height: 844 }]) {
      await page.setViewportSize(viewport);
      await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
      const heading = await page.locator(".overview-heading").boundingBox();
      requireResult(heading && heading.height <= 80, "overview_intro_too_tall");
      requireResult(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), "overview_horizontal_overflow");
      if (viewport.width >= 1280) {
        const box = await table.boundingBox();
        requireResult(box && box.y < 300, "account_quota_not_prioritized");
        if (viewport.width === 1920 && snapshot.rows.length <= 6 && snapshot.rows.reduce((count, row) => count + row.capacity.items.reduce((total, item) => total + item.windows.length, 0), 0) <= 12) requireResult(box.y + box.height < viewport.height, "account_quota_below_first_screen");
      }
    }
  } finally { await page.setViewportSize(prior); }
  stage = "read_only_navigation";
  const first = table.getByRole("button", { name: /^Open account / }).first();
  await first.focus();
  requireResult(await first.evaluate(node => document.activeElement === node), "account_action_not_keyboard_accessible");
  await first.click();
  await page.getByRole("region", { name: "Account activity", exact: true }).waitFor();
  requireResult(mutations === 0, "overview_started_mutation");
  await page.goto(origin);
  await page.getByRole("table", { name: "Account quota overview", exact: true }).waitFor();
  console.log(`DASHBOARD OVERVIEW: PASSED — ${snapshot.rows.length} real account rows, exact per-window percentages/bars, compact desktop/narrow layout, read-only navigation`);
  process.exit(0);
} catch (error) {
  const reason = error instanceof Error && /^[a-z_]+$/.test(error.message) ? error.message : "browser_verification_unavailable";
  console.log(`DASHBOARD OVERVIEW: BLOCKED — ${stage}: ${reason}`);
  process.exit(3);
}
