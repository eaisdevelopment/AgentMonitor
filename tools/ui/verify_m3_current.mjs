/** AC-M3-007: one selected real Claude account in the current built dashboard. */
import { chromium } from "../../frontend/node_modules/@playwright/test/index.mjs";
import { createHash } from "node:crypto";

const endpoint = process.env.AGENTMONITOR_TEST_DASHBOARD_CDP_ENDPOINT;
const origin = process.env.AGENTMONITOR_TEST_DASHBOARD_ORIGIN;
const accountId = process.env.AGENTMONITOR_M3_ACCOUNT_ID;
const preflightOnly = process.env.AGENTMONITOR_M3_PREFLIGHT_ONLY === "1";
const timeoutSeconds = Number(process.env.AGENTMONITOR_M3_FRESH_TIMEOUT_SECONDS ?? "420");
const requireResult = (condition, code) => { if (!condition) throw new Error(code); };
const digest = (value) => createHash("sha256").update(value).digest("hex");
class BlockedError extends Error {}
const safeId = (value) => typeof value === "string" && /^[A-Za-z0-9_-]{1,64}$/.test(value);
const percent = (field) => {
  const value = field?.value;
  if (!value || !["available", "stale"].includes(field.availability) || !["ratio", "percent"].includes(value.unit)) return null;
  const result = Number(value.coefficient) * 10 ** ((value.unit === "ratio" ? 2 : 0) - value.scale);
  return Number.isFinite(result) && result >= 0 && result <= 100 ? `${Number(result.toFixed(2))}%` : null;
};

let browser;
let page;
let stage = "prerequisites";
let before;
let after;
let mutations = 0;
let externalRequests = 0;
let pageErrors = 0;
let exitCode = 0;

try {
  requireResult(endpoint && origin && safeId(accountId), "explicit_selected_account_and_browser_required");
  requireResult(Number.isInteger(timeoutSeconds) && timeoutSeconds >= 1 && timeoutSeconds <= 600, "fresh_timeout_invalid");
  const cdpUrl = new URL(endpoint);
  const dashboardUrl = new URL(origin);
  requireResult(cdpUrl.protocol === "http:" && cdpUrl.hostname === "127.0.0.1" && dashboardUrl.protocol === "http:" && dashboardUrl.hostname === "127.0.0.1" && dashboardUrl.origin === origin, "loopback_browser_required");
  browser = await chromium.connectOverCDP(endpoint);
  const context = browser.contexts()[0];
  requireResult(context, "authenticated_chrome_context_required");
  page = await context.newPage();
  await page.setViewportSize({ width: 1920, height: 1080 });
  page.on("request", request => {
    const url = new URL(request.url());
    if (url.origin !== origin) externalRequests += 1;
    if (url.origin === origin && url.pathname.startsWith("/api/v1/") && !["GET", "HEAD"].includes(request.method())) mutations += 1;
  });
  page.on("pageerror", () => { pageErrors += 1; });
  await page.goto(origin);
  const read = async path => page.evaluate(async selectedPath => {
    const response = await fetch(selectedPath, { credentials: "same-origin" });
    if (!response.ok) throw new Error("authenticated_v1_get_failed");
    return response.json();
  }, path);

  stage = "selected_registry_account";
  const accounts = await read("/api/v1/accounts?limit=200");
  requireResult(accounts.availability.state === "available" && !accounts.page.has_more, "registry_selection_incomplete");
  const account = accounts.items.find(item => item.account_id === accountId);
  requireResult(account && account.provider_key === "claude" && account.lifecycle === "active" && account.is_effective_monitoring_enabled && account.identity_state === "owner_confirmed", "selected_claude_account_not_monitoring");
  before = { friendly_name: account.friendly_name, organization_id: account.organization_id, record_version: account.record_version, registry_revision: account.registry_revision };
  const selectedMetadataDigest = digest(`${accountId}\u0000${JSON.stringify(before)}`);

  stage = "current_identity_and_capacity";
  const id = encodeURIComponent(accountId);
  let identity = await read(`/api/v1/accounts/${id}/observed-identity`);
  requireResult(identity.state === "verified" && identity.account_id === accountId && identity.email && identity.collection_run_id && identity.source_id === "claude.auth.status.v1", "selected_identity_not_verified");
  requireResult(account.friendly_name === identity.email, "registered_observed_identity_mismatch");
  if (preflightOnly) {
    stage = "preflight_registry_unchanged";
    const finalAccounts = await read("/api/v1/accounts?limit=200");
    const finalAccount = finalAccounts.items.find(item => item.account_id === accountId);
    requireResult(finalAccount, "selected_account_disappeared");
    after = { friendly_name: finalAccount.friendly_name, organization_id: finalAccount.organization_id, record_version: finalAccount.record_version, registry_revision: finalAccount.registry_revision };
    requireResult(JSON.stringify(before) === JSON.stringify(after) && mutations === 0, "registry_metadata_changed_or_browser_mutation");
    requireResult(externalRequests === 0 && pageErrors === 0, "browser_external_or_script_error");
    console.log("M3 CURRENT PREFLIGHT: PASSED — selected owner-confirmed account and exact reported identity");
    console.log(JSON.stringify({ event: "m3_current_browser_preflight", selected_account_digest: digest(accountId), selected_account_metadata_digest: selectedMetadataDigest, identity_match: true, registry_unchanged: true, mutations: 0 }));
  } else {
  const previousRunId = identity.collection_run_id;
  const gateStartedAt = Date.now();
  const deadline = gateStartedAt + timeoutSeconds * 1000;
  let freshRun;
  stage = "fresh_installed_service_collection";
  while (Date.now() < deadline) {
    identity = await read(`/api/v1/accounts/${id}/observed-identity`);
    if (identity.state === "verified" && identity.account_id === accountId && identity.email === account.friendly_name && identity.collection_run_id && identity.collection_run_id !== previousRunId) {
      const runs = await read(`/api/v1/collection-runs?${new URLSearchParams({ provider_key: "claude", account_id: accountId, limit: "200" })}`);
      const candidate = runs.items.find(item => item.run_id === identity.collection_run_id);
      if (candidate && candidate.state === "succeeded" && candidate.account_id === accountId && candidate.source_id === "claude.usage.ax-screen-reader.v1" && candidate.requested_at && candidate.completed_at && Date.parse(candidate.requested_at) >= gateStartedAt && Date.parse(candidate.completed_at) >= gateStartedAt && candidate.observation_ids.length > 0) {
        freshRun = candidate;
        break;
      }
    }
    await new Promise(resolve => setTimeout(resolve, Math.min(5000, Math.max(0, deadline - Date.now()))));
  }
  if (!freshRun) throw new BlockedError("fresh_installed_collection_timeout");
  stage = "current_identity_and_capacity";
  const now = new Date();
  // A current-revision witness needs the recent poll snapshots. A year of
  // history can exceed one bounded page and hide the latest observation.
  const from = new Date(now.getTime() - 60 * 60 * 1000);
  const [capacity, quotas, history, sessions, locations] = await Promise.all([
    read(`/api/v1/accounts/${id}/capacity`),
    read(`/api/v1/accounts/${id}/quotas`),
    read(`/api/v1/capacity/history?${new URLSearchParams({ subject_id: accountId, metric: "remaining_ratio", series_kind: "poll_snapshot", from: from.toISOString(), before: now.toISOString(), limit: "200" })}`),
    read(`/api/v1/sessions?${new URLSearchParams({ provider_key: "claude", account_id: accountId, limit: "200" })}`),
    read("/api/v1/process-locations"),
  ]);
  requireResult(identity.state === "verified" && identity.account_id === accountId && identity.email === account.friendly_name && identity.collection_run_id === freshRun.run_id, "fresh_identity_changed");
  const windows = capacity.items.flatMap(item => item.windows);
  requireResult(capacity.account_id === accountId && capacity.availability.state === "available" && windows.length > 0 && quotas.account_id === accountId && quotas.availability.state === "available" && !quotas.page.has_more, "current_quota_unavailable");
  requireResult(windows.every(window => window.subject.account_id === accountId && window.freshness === "fresh" && window.collection_run_id === freshRun.run_id && window.current_observation_id && freshRun.observation_ids.includes(window.current_observation_id) && window.provenance?.source_id === "claude.usage.ax-screen-reader.v1" && window.provenance.freshness_deadline && window.provenance.precision !== "unknown" && window.provenance.confidence !== "unknown"), "current_quota_identity_lineage_invalid");
  requireResult(quotas.items.length === windows.length && quotas.items.every(window => windows.some(item => item.window_id === window.window_id && item.current_observation_id === window.current_observation_id && item.collection_run_id === window.collection_run_id)), "quota_views_disagree");
  requireResult(history.availability.state === "available" && history.items.some(point => point.subject.account_id === accountId && point.collection_run_id === identity.collection_run_id && windows.some(window => window.current_observation_id === point.observation_id)), "current_quota_history_lineage_missing");
  requireResult(["available", "partial"].includes(sessions.availability.state) && sessions.items.every(item => item.account_id === accountId) && locations.availability.state === "available", "runtime_account_scope_invalid");
  const linked = locations.items.filter(item => item.account_association?.account_id === accountId);
  const paths = [...new Set(linked.flatMap(item => item.working_directory === null ? [] : [item.working_directory]))];

  stage = "built_account_page";
  const response = await page.goto(`${origin}/accounts/${id}`);
  requireResult(response?.status() === 200, "account_route_unavailable");
  const activity = page.getByRole("table", { name: "Account activity", exact: true });
  await activity.waitFor({ timeout: 15_000 });
  const row = activity.locator("tbody tr");
  await row.locator(".workspace-account-name").getByText(identity.email, { exact: true }).waitFor({ timeout: 15_000 });
  await page.locator(".allowance-card").first().waitFor({ timeout: 15_000 });
  requireResult(await row.count() === 1 && (await page.locator("h1#page-title").innerText()).trim() === identity.email, "account_identity_not_rendered");
  requireResult(await page.locator(".connection-warning").count() === 0 && (await row.locator('[data-label="State"]').innerText()).includes("Monitoring on"), "account_identity_or_monitoring_warning");
  requireResult((await page.locator(".workspace-footnote").innerText()).includes(`${sessions.items.length}${sessions.page.has_more ? "+" : ""} linked session`), "session_summary_mismatch");
  const cards = page.locator(".allowance-card");
  requireResult(await cards.count() === quotas.items.length, "quota_card_count_mismatch");
  for (const window of quotas.items) {
    const card = cards.filter({ has: page.getByRole("heading", { name: window.safe_label ?? window.window_key, exact: true }) });
    requireResult(await card.count() === 1, "fresh_quota_card_missing");
    requireResult((await card.locator(".reading-freshness").textContent())?.trim() === "Up to date", "quota_card_not_fresh");
    const expected = percent(window.allowance?.remaining_percentage ?? window.remaining_ratio);
    if (expected !== null) requireResult((await card.locator(".allowance-value strong").innerText()).trim() === expected, "quota_percentage_not_rendered");
  }
  await page.locator("details.quota-technical > summary").click();
  const rows = page.locator('[aria-label="Quota windows table"] tbody tr');
  requireResult(await rows.count() === quotas.items.length, "quota_provenance_rows_missing");
  for (const window of quotas.items) {
    const matching = rows.filter({ has: page.locator(".quota-observation-id", { hasText: window.current_observation_id }) });
    requireResult(await matching.count() === 1 && (await matching.locator(".quota-collection-run-id").innerText()).trim() === identity.collection_run_id, "quota_provenance_lineage_not_rendered");
    const provenance = await matching.locator(".quota-provenance").innerText();
    requireResult(provenance.includes(window.provenance.source_id) && provenance.includes(window.provenance.precision) && provenance.includes(window.provenance.confidence) && provenance.includes(window.provenance.freshness_policy_id), "quota_provenance_not_rendered");
  }

  stage = "runtime_and_path_truth";
  await page.getByText("Reading running Claude processes…", { exact: true }).waitFor({ state: "detached" });
  const pathCell = row.locator('[data-label="Path"]');
  if (paths.length === 0) requireResult((await pathCell.innerText()).includes("Not reported"), "unlinked_path_not_reported");
  else for (const path of paths) await pathCell.locator("code").getByText(path, { exact: true }).waitFor({ timeout: 15_000 });
  const agents = page.getByRole("table", { name: "Agents using this account", exact: true });
  if (linked.length === 0) requireResult((await page.getByText("No agents linked to this account yet.").count()) === 1, "unlinked_agent_state_missing");
  else requireResult(await agents.locator("tbody tr").count() === linked.length, "linked_agent_count_mismatch");
  await page.locator('details[data-account-sessions] > summary').click();
  await page.getByRole("heading", { name: "Session records", exact: true }).waitFor();
  await page.getByText("Reading runtime observations…", { exact: true }).waitFor({ state: "detached" });
  const sessionRows = page.locator('details[data-account-sessions] .session-row');
  requireResult(await sessionRows.count() === sessions.items.length, "session_record_count_mismatch");
  if (sessions.items.length === 0) requireResult((await page.getByText("No observed sessions are available.").count()) === 1, "unresolved_session_state_missing");
  else for (let index = 0; index < sessions.items.length; index += 1) {
    const description = await sessionRows.nth(index).locator(".session-row-main").innerText();
    requireResult(description.includes(sessions.items[index].correlation_state.replaceAll("_", " ")) && description.includes("account correlated"), "session_correlation_not_rendered");
  }
  stage = "mobile_account_reading";
  await page.setViewportSize({ width: 390, height: 844 });
  requireResult(await activity.isVisible() && (await row.locator('[data-label="State"]').innerText()).includes("Monitoring on"), "mobile_account_state_hidden");
  requireResult(!(await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 1)), "mobile_horizontal_overflow");

  stage = "registry_unchanged";
  const finalAccounts = await read("/api/v1/accounts?limit=200");
  const finalAccount = finalAccounts.items.find(item => item.account_id === accountId);
  requireResult(finalAccount, "selected_account_disappeared");
  after = { friendly_name: finalAccount.friendly_name, organization_id: finalAccount.organization_id, record_version: finalAccount.record_version, registry_revision: finalAccount.registry_revision };
  requireResult(JSON.stringify(before) === JSON.stringify(after) && mutations === 0, "registry_metadata_changed_or_browser_mutation");
  requireResult(externalRequests === 0 && pageErrors === 0, "browser_external_or_script_error");
  console.log("M3 CURRENT BROWSER: PASSED — selected real account, verified identity and fresh quota lineage, built account/runtime view, unchanged registry");
  console.log(JSON.stringify({ event: "m3_current_browser_witness", selected_account_digest: digest(accountId), selected_account_metadata_digest: selectedMetadataDigest, collection_run_digest: digest(freshRun.run_id), observed_at: identity.verified_at, completed_at: freshRun.completed_at, identity_match: true, registry_unchanged: true, runtime_state: sessions.availability.state, linked_count: linked.length, session_count: sessions.items.length, mutations: 0 }));
  }
} catch (error) {
  const blocked = error instanceof BlockedError;
  const code = error instanceof Error && /^[a-z0-9_]+$/.test(error.message) ? error.message : "browser_verification_unavailable";
  console.error(`M3 CURRENT BROWSER: ${blocked ? "BLOCKED" : "FAILED"} — ${stage}: ${code}`);
  exitCode = blocked ? 3 : 1;
} finally {
  if (page) await page.close();
}
process.exit(exitCode);
