/** Verify the actual owner overview against its versioned account readings. */
import { chromium } from "../../frontend/node_modules/@playwright/test/index.mjs";

const endpoint = process.env.AGENTMONITOR_TEST_DASHBOARD_CDP_ENDPOINT;
const origin = process.env.AGENTMONITOR_TEST_DASHBOARD_ORIGIN;
let stage = "prerequisites";
function requireResult(condition, reason) { if (!condition) throw new Error(reason); }
function percentageValue(field) {
  if (!field || !["available", "stale"].includes(field.availability) || field.value === null || !["ratio", "percent"].includes(field.value.unit)) return null;
  const value = Number(field.value.coefficient) * 10 ** ((field.value.unit === "ratio" ? 2 : 0) - field.value.scale);
  return Number.isFinite(value) && value >= 0 && value <= 100 ? value : null;
}
function percentage(field) {
  const value = percentageValue(field);
  return value === null ? null : `${Number(value.toFixed(2))}%`;
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
      const identity = await read(`/api/v1/accounts/${account.account_id}/observed-identity`);
      rows.push({ account, capacity, identity });
    }
    return { rows, organizations };
  });
  requireResult(snapshot.rows.length > 0 && snapshot.rows.some(row => row.capacity.items.some(item => item.windows.length > 0)), "real_account_quota_required");
  // Keep every registry connection; quota presentation is one row per fresh
  // observed provider identity within its dashboard/provider organizations.
  const connections = new Map();
  for (const row of snapshot.rows) {
    const { account, capacity, identity } = row;
    const windows = capacity.items.flatMap(item => item.windows);
    const eligible = ["matched", "owner_confirmed"].includes(account.identity_state) && capacity.availability.state === "available" && identity.state === "verified" && identity.account_id === account.account_id && identity.email !== null && identity.provider_organization !== null && windows.length > 0 && windows.every(window => window.freshness === "fresh" && window.collection_run_id === identity.collection_run_id);
    const key = eligible ? JSON.stringify([account.provider_key, account.organization_id, identity.email, identity.provider_organization]) : JSON.stringify([account.account_id]);
    connections.set(key, [...(connections.get(key) ?? []), row]);
  }
  const presentationRows = [...connections.values()].map(group => group.sort((left, right) => Number(right.account.friendly_name === right.identity.email) - Number(left.account.friendly_name === left.identity.email) || left.account.account_id.localeCompare(right.account.account_id))[0]);
  let mutations = 0;
  let collectionHistoryGets = 0;
  page.on("request", request => {
    const url = new URL(request.url());
    if (url.origin !== origin || !url.pathname.startsWith("/api/v1/")) return;
    if (url.pathname === "/api/v1/collection-runs" && request.method() === "GET") collectionHistoryGets += 1;
    if (!["GET", "HEAD"].includes(request.method())) mutations += 1;
  });
  await page.goto(origin);
  stage = "account_quota_overview";
  const collectionHistory = page.getByRole("button", { name: "Collection / History", exact: true });
  await collectionHistory.waitFor({ timeout: 10_000 });
  requireResult(await collectionHistory.count() === 1, "collection_history_navigation_missing");
  requireResult(await page.getByRole("heading", { name: "Collection runs", exact: true }).count() === 0, "collection_history_still_on_overview");
  const table = page.getByRole("table", { name: "Account quota overview", exact: true });
  await table.waitFor({ timeout: 10_000 });
  requireResult(collectionHistoryGets === 0, "overview_loaded_collection_history");
  const collectionResponse = page.waitForResponse(response => {
    const url = new URL(response.url());
    return url.origin === origin && url.pathname === "/api/v1/collection-runs" && response.request().method() === "GET";
  });
  await collectionHistory.click();
  await page.getByRole("heading", { name: "Collection runs", exact: true }).waitFor();
  requireResult((await collectionResponse).status() === 200, "collection_history_get_unavailable");
  requireResult(new URL(page.url()).pathname === "/collectors" && await page.title() === "Collection / History · AgentMonitor" && collectionHistoryGets > 0, "collection_history_route_missing");
  const historyGetsAfterNavigation = collectionHistoryGets;
  await page.goto(origin);
  await table.waitFor({ timeout: 10_000 });
  requireResult(collectionHistoryGets === historyGetsAfterNavigation, "overview_loaded_collection_history");
  for (const label of ["Account", "Organization", "State", "Quota left", "Updated"]) requireResult(await table.getByRole("columnheader", { name: label, exact: true }).count() === 1, "overview_column_missing");
  stage = "interactive_sorting";
  const sortHeaders = Object.fromEntries(["Organization", "State", "Quota left"].map(label => [label, table.getByRole("columnheader", { name: label, exact: true })]));
  for (const label of Object.keys(sortHeaders)) requireResult(await sortHeaders[label].getByRole("button", { name: label, exact: true }).count() === 1, "overview_sort_control_missing");
  const organizationLabel = row => row.account.organization_id === null ? "Ungrouped" : snapshot.organizations.items.find(item => item.organization_id === row.account.organization_id)?.name ?? "Unavailable";
  const stateLabel = row => {
    const { account, capacity } = row;
    const windows = capacity.items.flatMap(item => item.windows);
    if (["wrong_account", "conflict", "invalidated"].includes(account.identity_state)) return "Check identity";
    if (account.lifecycle === "pending") return "Not connected";
    if (account.lifecycle === "disabled") return "Disabled";
    if (!account.is_effective_monitoring_enabled) return "Monitoring off";
    if (capacity.availability.state === "unavailable") return "Unavailable";
    if (capacity.availability.state === "unsupported") return "Unsupported";
    if (capacity.availability.state === "unknown") return "Unknown";
    if (windows.length === 0) return "No quota yet";
    if (windows.some(window => window.freshness === "conflicted")) return "Conflicting readings";
    if (windows.some(window => window.freshness === "stale")) return "Stale";
    if (windows.some(window => window.freshness !== "fresh")) return "Unknown freshness";
    if (capacity.availability.state === "partial") return "Partial readings";
    return "Current";
  };
  const minimum = row => {
    const values = row.capacity.items.flatMap(item => item.windows).map(window => percentageValue(window.allowance?.remaining_percentage ?? window.remaining_ratio)).filter(value => value !== null);
    return values.length > 0 ? Math.min(...values) : Infinity;
  };
  const tie = (left, right) => left.account.friendly_name.localeCompare(right.account.friendly_name) || left.account.account_id.localeCompare(right.account.account_id);
  const expectedOrder = (key, direction, rows = presentationRows) => [...rows].sort((left, right) => {
    let primary = 0;
    if (key === "quota") {
      const leftValue = minimum(left);
      const rightValue = minimum(right);
      const leftAvailable = Number.isFinite(leftValue);
      const rightAvailable = Number.isFinite(rightValue);
      if (leftAvailable !== rightAvailable) return leftAvailable ? -1 : 1;
      if (leftAvailable) primary = leftValue - rightValue;
    } else {
      const leftValue = key === "organization" ? organizationLabel(left) : stateLabel(left);
      const rightValue = key === "organization" ? organizationLabel(right) : stateLabel(right);
      primary = leftValue.localeCompare(rightValue);
    }
    return (primary === 0 ? 0 : direction === "ascending" ? primary : -primary) || tie(left, right);
  }).map(row => row.account.account_id);
  const orderedIds = () => table.locator("tbody tr").evaluateAll(rows => rows.map(row => row.dataset.accountId));
  const assertSort = async (label, key, direction, rows = presentationRows, headersVisible = true) => {
    if (headersVisible) {
      requireResult(await sortHeaders[label].getAttribute("aria-sort") === direction, "overview_sort_direction_missing");
      for (const other of Object.keys(sortHeaders).filter(value => value !== label)) requireResult(await sortHeaders[other].getAttribute("aria-sort") === null, "overview_multiple_active_sorts");
    }
    requireResult(JSON.stringify(await orderedIds()) === JSON.stringify(expectedOrder(key, direction, rows)), "overview_sort_order_mismatch");
  };
  await assertSort("Quota left", "quota", "ascending");
  await sortHeaders.Organization.getByRole("button", { name: "Organization", exact: true }).click();
  await assertSort("Organization", "organization", "ascending");
  await sortHeaders.Organization.getByRole("button", { name: "Organization", exact: true }).click();
  await assertSort("Organization", "organization", "descending");
  const stateSort = sortHeaders.State.getByRole("button", { name: "State", exact: true });
  await stateSort.focus();
  requireResult(await stateSort.evaluate(node => document.activeElement === node), "overview_sort_not_keyboard_accessible");
  await page.keyboard.press("Enter");
  await assertSort("State", "state", "ascending");
  await page.keyboard.press("Space");
  await assertSort("State", "state", "descending");
  const quotaSort = sortHeaders["Quota left"].getByRole("button", { name: "Quota left", exact: true });
  await quotaSort.click();
  await assertSort("Quota left", "quota", "ascending");
  await quotaSort.click();
  await assertSort("Quota left", "quota", "descending");
  await quotaSort.click();
  await assertSort("Quota left", "quota", "ascending");
  await sortHeaders.Organization.getByRole("button", { name: "Organization", exact: true }).click();
  await sortHeaders.Organization.getByRole("button", { name: "Organization", exact: true }).click();
  await assertSort("Organization", "organization", "descending");
  stage = "organization_filter";
  const filters = page.getByRole("group", { name: "Organizations", exact: true });
  requireResult(await filters.count() === 1, "organization_filter_missing");
  const all = filters.getByRole("button", { name: "All organizations", exact: true });
  requireResult(await all.getAttribute("aria-pressed") === "true", "all_organizations_not_default");
  const expectedIds = rows => presentationRows.filter(primary => rows.some(row => row.account.account_id === primary.account.account_id)).map(row => row.account.account_id).sort();
  const visibleIds = async () => table.locator("tbody tr").evaluateAll(rows => rows.map(row => row.dataset.accountId).sort());
  const sameIds = (actual, expected) => JSON.stringify(actual) === JSON.stringify(expected);
  const groups = snapshot.organizations.items.filter(organization => snapshot.rows.some(row => row.account.organization_id === organization.organization_id));
  requireResult(groups.length >= 2, "two_real_organizations_required");
  const firstGroup = filters.getByRole("button", { name: groups[0].name, exact: true });
  const secondGroup = filters.getByRole("button", { name: groups[1].name, exact: true });
  await firstGroup.focus();
  requireResult(await firstGroup.evaluate(node => document.activeElement === node), "organization_filter_not_keyboard_accessible");
  await page.keyboard.press("Space");
  requireResult(await firstGroup.getAttribute("aria-pressed") === "true" && await all.getAttribute("aria-pressed") === "false", "single_organization_selection_not_exposed");
  requireResult(sameIds(await visibleIds(), expectedIds(snapshot.rows.filter(row => row.account.organization_id === groups[0].organization_id))), "single_organization_rows_mismatch");
  const firstGroupRows = presentationRows.filter(row => row.account.organization_id === groups[0].organization_id);
  await assertSort("Organization", "organization", "descending", firstGroupRows);
  await page.getByRole("button", { name: "Refresh overview", exact: true }).click();
  await page.getByRole("button", { name: "Refresh overview", exact: true }).waitFor();
  requireResult(await firstGroup.getAttribute("aria-pressed") === "true", "organization_selection_lost_after_refresh");
  requireResult(sameIds(await visibleIds(), expectedIds(snapshot.rows.filter(row => row.account.organization_id === groups[0].organization_id))), "filtered_refresh_rows_mismatch");
  await assertSort("Organization", "organization", "descending", firstGroupRows);
  stage = "organization_periodic_refresh";
  const periodicRead = await page.waitForResponse(response => new URL(response.url()).pathname === "/api/v1/accounts" && response.request().method() === "GET", { timeout: 40_000 });
  requireResult(periodicRead.status() === 200, "periodic_account_read_unavailable");
  await page.getByRole("button", { name: "Refresh overview", exact: true }).waitFor();
  requireResult(await firstGroup.getAttribute("aria-pressed") === "true" && sameIds(await visibleIds(), expectedIds(snapshot.rows.filter(row => row.account.organization_id === groups[0].organization_id))), "organization_selection_lost_after_periodic_refresh");
  await assertSort("Organization", "organization", "descending", firstGroupRows);
  stage = "organization_filter";
  await secondGroup.click();
  requireResult(await firstGroup.getAttribute("aria-pressed") === "true" && await secondGroup.getAttribute("aria-pressed") === "true", "multiple_organization_selection_not_exposed");
  requireResult(sameIds(await visibleIds(), expectedIds(snapshot.rows.filter(row => [groups[0].organization_id, groups[1].organization_id].includes(row.account.organization_id)))), "multiple_organization_rows_mismatch");
  await firstGroup.click();
  await secondGroup.click();
  requireResult(await table.count() === 0 && await page.getByText("No organizations selected. Choose an organization or All organizations.", { exact: true }).count() === 1, "empty_organization_selection_not_explicit");
  await all.click();
  requireResult(await all.getAttribute("aria-pressed") === "true" && sameIds(await visibleIds(), expectedIds(snapshot.rows)), "all_organizations_reset_failed");
  await assertSort("Organization", "organization", "descending");
  await quotaSort.click();
  await assertSort("Quota left", "quota", "ascending");
  stage = "lowest_quota_first";
  const actualOrder = await table.locator("tbody tr").evaluateAll(rows => rows.map(row => row.dataset.accountId));
  const orderedMinimums = actualOrder.map(id => minimum(snapshot.rows.find(row => row.account.account_id === id)));
  requireResult(orderedMinimums.every((value, index) => index === 0 || value >= orderedMinimums[index - 1]), "accounts_not_sorted_by_lowest_remaining_quota");
  requireResult(await table.getByRole("columnheader", { name: "Quota left", exact: true }).getAttribute("aria-sort") === "ascending", "quota_sort_not_accessible");
  stage = "per_window_quota";
  let lowWindows = 0;
  let normalWindows = 0;
  for (const { account, capacity } of presentationRows) {
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
        const meter = reading.getByRole("meter");
        requireResult(await meter.count() === 1, "account_quota_bar_missing");
        const value = percentageValue(window.allowance?.remaining_percentage ?? window.remaining_ratio);
        const color = await meter.locator("span").evaluate(node => getComputedStyle(node).backgroundColor.match(/\d+/g)?.slice(0, 3).map(Number));
        if (value <= 20) {
          lowWindows += 1;
          requireResult(color && color[0] > color[1] * 1.5 && color[0] > color[2] * 1.5, "low_quota_bar_not_red");
          requireResult(await reading.getByText("Low", { exact: true }).count() === 1 && /low/i.test(await meter.getAttribute("aria-valuetext") ?? ""), "low_quota_text_missing");
        } else {
          normalWindows += 1;
          requireResult(color && color[2] > color[0], "normal_quota_bar_changed_to_warning");
          requireResult(await reading.getByText("Low", { exact: true }).count() === 0, "normal_quota_marked_low");
        }
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
      const mobileSort = page.getByLabel("Sort accounts", { exact: true });
      if (viewport.width < 600) {
        requireResult(await mobileSort.isVisible(), "mobile_sort_control_missing");
        await mobileSort.selectOption("organization:descending");
        requireResult(await mobileSort.inputValue() === "organization:descending", "mobile_sort_direction_missing");
        await assertSort("Organization", "organization", "descending", presentationRows, false);
        await mobileSort.selectOption("quota:ascending");
        requireResult(await mobileSort.inputValue() === "quota:ascending", "mobile_sort_direction_missing");
        await assertSort("Quota left", "quota", "ascending", presentationRows, false);
      } else requireResult(await mobileSort.isHidden(), "mobile_sort_control_visible_on_desktop");
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
  console.log(`DASHBOARD OVERVIEW: PASSED — ${presentationRows.length} real account rows from ${snapshot.rows.length} registry connections, single/multiple/reset/empty organization filters, retained manual/periodic refresh selection, lowest quota first, ${lowWindows} low red / ${normalWindows} normal bars, compact desktop/narrow layout, read-only navigation`);
  if (lowWindows === 0) console.log("LOW-QUOTA LIVE COLOR: NOT RUN — no actual reading at or below 20 percent");
  process.exit(0);
} catch (error) {
  const reason = error instanceof Error && /^[a-z_]+$/.test(error.message) ? error.message : "browser_verification_unavailable";
  console.log(`DASHBOARD OVERVIEW: BLOCKED — ${stage}: ${reason}`);
  process.exit(3);
}
