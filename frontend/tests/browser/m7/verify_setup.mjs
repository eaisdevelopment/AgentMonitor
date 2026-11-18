"use strict";
import { currentSetupProof, sameSetupAuthority, setupInstant } from "./setup_evidence.mjs";

// Installed setup surface only. Never submit configuration or inspect credentials.
const origin = "http://127.0.0.1:43110";
const expectedRevision = /^[a-f0-9]{40}$/.test(process.argv[2] ?? "") ? process.argv[2] : null;
const requireConnectedBilling = process.argv.includes("--require-connected-billing");
const checks = { authentication: "not_run", revision: "not_run", overview: "not_run", setup_form: "not_run", account_layout: "not_run", scope_contract: "not_run", continuity: "not_run", read_only: "not_run" };
if (requireConnectedBilling) Object.assign(checks, { credential_stored: "not_run", connection_verified: "not_run", monitoring_enabled: "not_run", retained_report: "not_run" });
let page;
let status = "blocked";
let reasonCode = "browser_unavailable";
let actualRevision = null;
let requestsObserved = 0;
let unsafeRequests = 0;
let stage = "tooling";
let setupStep = null;
let errorKind = null;
const failedRequests = [];
let setupDiagnostic = null;
function pathFamily(url) {
  const path = new URL(url).pathname;
  return ({ "/api/v1/accounts": "accounts", "/api/v1/organizations": "organizations", "/api/v1/iam/initialization": "iam_initialization", "/api/v1/session": "iam_session" })[path] ?? "other";
}

function stop(nextStatus, reason) {
  status = nextStatus;
  reasonCode = reason;
  if (reason === "authentication_required") checks.authentication = "blocked";
  throw new Error("probe_stopped");
}

function requireEvidence(condition, reason) {
  if (!condition) stop("failed", reason);
  if (unsafeRequests !== 0) stop("failed", "unexpected_mutation_request");
}

async function noOverflow() {
  requireEvidence(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1), "horizontal_overflow");
}

async function verifyConnectedBilling() {
  const read = async (path, absent = false) => {
    requestsObserved++;
    const response = await page.request.get(`${origin}${path}`, { headers: { Origin: origin }, timeout: 10000, failOnStatusCode: false });
    if (response.status() === 401) stop("blocked", "authentication_required");
    if (response.status() === 403) stop("blocked", "owner_setup_permission_required");
    if (absent && [400, 404].includes(response.status())) return null;
    requireEvidence(response.status() === 200, "owner_setup_read_unavailable");
    return response.json();
  };
  const accounts = [];
  let cursor = null;
  const cursors = new Set();
  for (let index = 0; index < 100; index++) {
    const query = new URLSearchParams({ limit: "200", ...(cursor === null ? {} : { cursor }) });
    const result = await read(`/api/v1/accounts?${query}`);
    requireEvidence(Array.isArray(result.items) && result.page, "owner_setup_inventory_invalid");
    accounts.push(...result.items);
    cursor = result.page.next_cursor;
    if (cursor === null) break;
    requireEvidence(typeof cursor === "string" && !cursors.has(cursor) && index < 99, "owner_setup_inventory_incomplete");
    cursors.add(cursor);
  }
  let selected = null;
  for (const account of accounts) {
    if (!["claude", "codex"].includes(account.provider_key) || !["pending", "active"].includes(account.lifecycle)) continue;
    stage = "credential_stored";
    const path = `/api/v1/accounts/${encodeURIComponent(account.account_id)}/billing-connections`;
    const status = await read(path);
    requireEvidence(status.account_id === account.account_id, "owner_setup_account_mismatch");
    if (status.credential_status?.state !== "stored") continue;
    checks.credential_stored = "passed";
    for (const connection of status.connections) {
      stage = "connection_verified";
      const monitoringPath = `${path}/${encodeURIComponent(connection.resource_id)}/monitoring`;
      const monitoring = await read(monitoringPath);
      if (monitoring.verified_run_id === null) continue;
      const run = await read(`/api/v1/collection-runs/${encodeURIComponent(monitoring.verified_run_id)}/budget/v2`);
      if (!currentSetupProof(status, connection, monitoring, run)) continue;
      checks.connection_verified = "passed";
      checks.monitoring_enabled = "passed";
      stage = "retained_report";
      const context = run.report_context;
      const end = new Date(run.requested_at);
      requireEvidence(Number.isFinite(end.getTime()), "owner_setup_run_time_invalid");
      end.setUTCHours(0, 0, 0, 0);
      // Legacy Check records omit report_context; inspect only the two admitted
      // completed windows at the actual request time, never invent report facts.
      const periods = context ? [{ start: context.interval_start, end: context.interval_end }] : [7, 30].map(days => ({ start: new Date(end.getTime() - days * 86400000).toISOString(), end: end.toISOString() }));
      const asOf = new Date().toISOString();
      for (const period of periods) {
        const query = { account_id: account.account_id, report_id: run.report_id, period_start: period.start, period_end: period.end, as_of: asOf, limit: "50" };
        const history = await read(`/api/v1/budgets/${encodeURIComponent(connection.resource_id)}/history?${new URLSearchParams(query)}`, context === null);
        if (history === null) continue;
        const report = history.report;
        requireEvidence(history.availability?.state === "available" && report.report_id === run.report_id && report.account_id === account.account_id && report.resource_id === connection.resource_id
          && report.provider_key === status.provider_key && report.scope_generation === connection.scope_generation && report.scope_id === connection.scope_id && report.scope_evidence === connection.scope_evidence
          && setupInstant(report.requested_period.start) === setupInstant(period.start) && setupInstant(report.requested_period.end) === setupInstant(period.end)
          && report.completeness === "complete" && setupInstant(history.as_of) === setupInstant(asOf), "owner_setup_report_mismatch");
        selected = { path, monitoringPath, status, connection, monitoring, run, history, query };
        break;
      }
      if (selected) break;
    }
    if (selected) break;
  }
  if (selected === null) stop("blocked", "owner_setup_current_evidence_unavailable");
  const { path, monitoringPath, status, connection, run, history, query } = selected;
  const search = new URLSearchParams({ budget_resource: connection.resource_id, budget_report: run.report_id, budget_start: query.period_start.replace("+00:00", "Z"), budget_end: query.period_end.replace("+00:00", "Z"), budget_as_of: query.as_of });
  const url = `${origin}/accounts/${encodeURIComponent(status.account_id)}?${search}`;
  const checkView = async () => {
    const financial = page.getByRole("region", { name: "API usage & spend", exact: true });
    await financial.waitFor({ state: "visible" });
    await page.waitForFunction(() => document.querySelector('[aria-label="Selected financial report"] [data-budget-history][aria-busy="false"]') !== null);
    const retained = financial.getByRole("region", { name: "Selected financial report", exact: true }).locator("[data-budget-history]");
    requireEvidence(await retained.getAttribute("data-budget-history") === run.report_id, "owner_setup_rendered_report_mismatch");
    requireEvidence(await retained.locator(':scope > [role="alert"]').count() === 0
      && setupInstant(await financial.locator("[data-budget-window]").getAttribute("data-read-as-of")) === setupInstant(query.as_of), "owner_setup_rendered_context_mismatch");
    const expected = history.items.map(row => `${row.kind}:${(row.cost ?? row.usage).bucket_key}`).sort();
    const actual = await retained.locator("[data-bucket-key]").evaluateAll(rows => rows.map(row => `${row.getAttribute("data-bucket-kind")}:${row.getAttribute("data-bucket-key")}`).sort());
    requireEvidence(JSON.stringify(actual) === JSON.stringify(expected), "owner_setup_rendered_facts_mismatch");
    const disclosure = page.locator("details[data-billing-connection]");
    if (await disclosure.count() && !await disclosure.evaluate(node => node.open)) await disclosure.locator(":scope > summary").click();
    const setup = page.getByRole("region", { name: "API billing setup", exact: true });
    await setup.getByText("Credential stored", { exact: true }).waitFor();
    await setup.getByText("API monitoring is on.", { exact: true }).waitFor();
    await setup.getByText("Access is confirmed for the current credential and billing scope.", { exact: true }).waitFor();
  };
  await page.goto(url, { waitUntil: "domcontentloaded", timeout: 10000 });
  await checkView();
  await page.reload({ waitUntil: "domcontentloaded", timeout: 10000 });
  await checkView();
  const fresh = await read(path), monitoring = await read(monitoringPath);
  requireEvidence(sameSetupAuthority(status, fresh, connection.resource_id), "owner_setup_authority_changed");
  requireEvidence(typeof monitoring.verified_run_id === "string", "owner_setup_verification_unavailable");
  const currentRun = monitoring.verified_run_id === run.run_id ? run
    : await read(`/api/v1/collection-runs/${encodeURIComponent(monitoring.verified_run_id)}/budget/v2`);
  requireEvidence(currentSetupProof(fresh, connection, monitoring, currentRun), "owner_setup_authority_changed");
  checks.retained_report = "passed";
}

try {
  if (expectedRevision === null) stop("failed", "invalid_revision_argument");
  let playwright;
  try {
    playwright = await import("@playwright/test");
  } catch (error) {
    if (error?.code !== "ERR_MODULE_NOT_FOUND") throw error;
    // Reuse the admitted development dependency tree without creating tool links.
    playwright = await import("/home/dev/.local/share/agentmonitor/worktrees/dashboard-product-promotion/frontend/node_modules/@playwright/test/index.mjs");
  }
  stage = "browser";
  const browser = await playwright.chromium.connectOverCDP("http://127.0.0.1:9225", { timeout: 5000 });
  const context = browser.contexts()[0];
  if (context === undefined) stop("blocked", "browser_context_unavailable");
  // Only this new page is controlled or closed. Existing tabs are never inspected.
  page = await context.newPage();
  page.setDefaultTimeout(7000);
  page.on("request", (request) => {
    requestsObserved += 1;
    if (!["GET", "HEAD", "OPTIONS"].includes(request.method())) unsafeRequests += 1;
  });
  page.on("requestfailed", request => {
    const error = request.failure()?.errorText;
    if (typeof error === "string" && /^net::ERR_[A-Z_]+$/.test(error)) failedRequests.push({ family: pathFamily(request.url()), error });
  });
  await page.setViewportSize({ width: 1366, height: 768 });
  stage = "authentication";
  const navigation = await page.goto(origin, { waitUntil: "domcontentloaded", timeout: 10000 });
  if (navigation?.status() !== 200) stop("blocked", "dashboard_unavailable");
  const signIn = page.getByRole("heading", { name: "Sign in", exact: true });
  const accounts = page.getByRole("button", { name: "Accounts", exact: true });
  await signIn.or(accounts).first().waitFor({ state: "visible" });
  if (await signIn.isVisible()) {
    checks.authentication = "blocked";
    stop("blocked", "authentication_required");
  }
  requireEvidence(await accounts.isVisible(), "authenticated_navigation_missing");
  checks.authentication = "passed";

  stage = "revision";
  requestsObserved += 1;
  const versions = await page.request.get(`${origin}/api/v1/operations/versions`, {
    headers: { Origin: origin }, timeout: 5000, failOnStatusCode: false,
  });
  if (versions.status() === 401) stop("blocked", "authentication_required");
  if (versions.status() !== 200) stop("blocked", "revision_unavailable");
  const version = (await versions.json())?.source_revision;
  if (version?.availability !== "available" || version.source !== "build_manifest") stop("blocked", "revision_unavailable");
  actualRevision = /^[a-f0-9]{40}$/.test(version.value ?? "") ? version.value : null;
  requireEvidence(actualRevision === expectedRevision, "revision_mismatch");
  checks.revision = "passed";

  stage = "overview";
  await page.getByRole("heading", { name: "AgentMonitor", exact: true }).waitFor();
  await noOverflow();
  checks.overview = "passed";

  stage = "setup_form";
  setupStep = "accounts_navigation";
  requireEvidence(await accounts.getAttribute("type") === "button", "accounts_navigation_not_safe");
  await accounts.click();
  setupStep = "add_api_control";
  const addApi = page.getByRole("button", { name: "Add API billing account", exact: true });
  await addApi.waitFor();
  requireEvidence(await addApi.getAttribute("type") === "button", "setup_mode_not_safe");
  await addApi.click();
  setupStep = "add_api_heading";
  await page.getByRole("heading", { name: "Add API billing account", exact: true }).waitFor();
  setupStep = "provider_choices";
  const provider = page.getByLabel("Provider", { exact: true });
  const providerKeys = await provider.locator("option").evaluateAll((options) => options.map((option) => option.value));
  requireEvidence(JSON.stringify(providerKeys) === JSON.stringify(["", "claude", "codex", "ollama"]), "provider_choices_mismatch");
  const create = page.getByRole("button", { name: "Create API billing account", exact: true });
  setupStep = "create_control";
  await create.waitFor();
  requireEvidence(await create.isDisabled(), "blank_creation_not_disabled");
  await noOverflow();
  checks.setup_form = "passed";

  stage = "account_layout";
  requestsObserved += 1;
  const inventory = await page.request.get(`${origin}/api/v1/accounts?limit=200`, {
    headers: { Origin: origin }, timeout: 10000, failOnStatusCode: false,
  });
  requireEvidence(inventory.status() === 200, "account_inventory_unavailable");
  const accountPage = await inventory.json();
  requireEvidence(accountPage.items.length > 0 && accountPage.items.every(item => typeof item.has_active_subscription_resource === "boolean"), "account_resource_classification_missing");
  const subscription = accountPage.items.find(item => item.has_active_subscription_resource && ["claude", "codex"].includes(item.provider_key));
  requireEvidence(subscription !== undefined, "genuine_subscription_account_required");
  await page.goto(`${origin}/accounts/${encodeURIComponent(subscription.account_id)}`);
  await page.getByRole("heading", { name: "Account activity", exact: true }).waitFor();
  await page.locator("details[data-billing-connection] summary").waitFor();
  requireEvidence(await page.locator("details.account-settings summary").textContent().then(text => text.includes("monitoring")), "subscription_settings_missing");
  await noOverflow();
  checks.account_layout = "passed";

  stage = "scope_contract";
  requestsObserved += 1;
  const contractResponse = await page.request.get(`${origin}/openapi.json`, {
    headers: { Origin: origin }, timeout: 10000, failOnStatusCode: false,
  });
  requireEvidence(contractResponse.status() === 200, "installed_openapi_unavailable");
  const contract = await contractResponse.json();
  const scopeOperation = contract.paths?.["/api/v1/accounts/{account_id}/billing-connections/{resource_id}/scope"]?.put;
  requireEvidence(scopeOperation?.operationId === "registry_change_billing_scope_v1", "billing_scope_contract_missing");
  const scopeInput = contract.components?.schemas?.ChangeBillingScopeInputV1;
  requireEvidence(scopeInput?.additionalProperties === false && ["scope_id", "expected_account_version", "expected_scope_generation"].every(field => scopeInput.required?.includes(field)), "billing_scope_contract_invalid");
  const reconnectOperation = contract.paths?.["/api/v1/accounts/{account_id}/billing-connections/{resource_id}/reconnect"]?.post;
  requireEvidence(reconnectOperation?.operationId === "registry_reconnect_billing_connection_v1", "billing_reconnect_contract_missing");
  const reconnectInput = contract.components?.schemas?.ReconnectBillingConnectionInputV1;
  requireEvidence(reconnectInput?.additionalProperties === false && ["expected_account_version", "expected_scope_generation"].every(field => reconnectInput.required?.includes(field)), "billing_reconnect_contract_invalid");
  const maintenanceInput = contract.components?.schemas?.BillingLocalMaintenanceV1;
  requireEvidence(contract.components?.schemas?.AccountBillingConnectionsV1?.properties?.local_maintenance !== undefined
    && maintenanceInput?.additionalProperties === false
    && ["host_label", "disconnect_command", "cleanup_command"].every(field => maintenanceInput.required?.includes(field)), "billing_maintenance_contract_missing");
  checks.scope_contract = "passed";

  stage = "continuity";
  const overview = page.getByRole("button", { name: "Overview", exact: true });
  requireEvidence(await overview.getAttribute("type") === "button", "overview_navigation_not_safe");
  await overview.click();
  await page.getByRole("heading", { name: "AgentMonitor", exact: true }).waitFor();
  await page.getByRole("region", { name: "Discover the Essential AI product family", exact: true }).waitFor();
  const support = page.locator(".header-support-link");
  requireEvidence(await support.isVisible() && await support.getAttribute("href") === "https://buy.stripe.com/dRm4gBfGo59L4enf167EQ00", "support_link_missing");
  const company = page.locator(".dashboard-company-footer").getByRole("link", { name: "Essential AI Solutions Ltd", exact: true });
  requireEvidence(await company.isVisible() && await company.getAttribute("href") === "https://essentialai.uk/", "company_footer_missing");
  await noOverflow();
  checks.continuity = "passed";
  if (requireConnectedBilling) await verifyConnectedBilling();
  requireEvidence(unsafeRequests === 0, "unexpected_mutation_request");
  status = "passed";
  reasonCode = requireConnectedBilling ? "installed_owner_setup_verified" : "installed_setup_surface_verified";
} catch (error) {
  errorKind = error?.name === "TimeoutError" ? "timeout" : "assertion_or_error";
  if (error?.message !== "probe_stopped") {
    const authRequired = page !== undefined && await page.getByRole("heading", { name: "Sign in", exact: true }).isVisible().catch(() => false);
    status = authRequired || ["tooling", "browser", "authentication", "revision"].includes(stage) ? "blocked" : "failed";
    if (authRequired) checks.authentication = "blocked";
    reasonCode = authRequired ? "authentication_required" : {
      tooling: "browser_tooling_unavailable", browser: "browser_unavailable",
      authentication: "dashboard_unavailable", revision: "revision_unavailable",
      overview: "overview_unavailable", setup_form: "setup_form_unavailable",
      continuity: "continuity_unavailable", account_layout: "account_layout_unavailable",
      scope_contract: "scope_contract_unavailable",
      credential_stored: "owner_setup_read_unavailable", connection_verified: "owner_setup_read_unavailable",
      retained_report: "owner_setup_report_unavailable",
    }[stage];
  }
  if (checks[stage] === "not_run") checks[stage] = status;
} finally {
  if (page !== undefined && status !== "passed") setupDiagnostic = await page.evaluate(() => ({
    local_service_unavailable: [...document.querySelectorAll("h1")].some(node => node.textContent === "Local service unavailable"),
    connecting: document.querySelector("main.auth-stage[role=status]") !== null,
    account_loading: [...document.querySelectorAll("p[role=status]")].some(node => node.textContent === "Reading monitored accounts…"),
    account_error: [...document.querySelectorAll("p[role=alert]")].some(node => ["Accounts could not be loaded from the local service.", "The local account registry is unavailable."].includes(node.textContent)),
  })).catch(() => null);
  if (page !== undefined) {
    try { await page.close(); }
    catch { status = "failed"; reasonCode = "probe_page_cleanup_failed"; }
  }
  if (unsafeRequests !== 0) { status = "failed"; reasonCode = "unexpected_mutation_request"; }
  checks.read_only = page === undefined ? "not_run" : unsafeRequests === 0 ? "passed" : "failed";
}

const result = {
  record_type: "agentmonitor.m7_installed_setup_probe.v1", status, reason_code: reasonCode,
  expected_revision: expectedRevision, source_revision: actualRevision, checks,
  requests_observed: requestsObserved, unsafe_requests: unsafeRequests,
  setup_step: setupStep, setup_diagnostic: setupDiagnostic, error_kind: errorKind, failed_requests: failedRequests.slice(0, 40),
  ...(requireConnectedBilling ? { evidence_scope: "current_verified_billing_state", resources_verified: checks.retained_report === "passed" ? 1 : 0, physical_rotation_removal: "not_verified", check_click_provenance: "not_verified" } : {}),
  observed_at: new Date().toISOString(),
};
// Exiting disconnects CDP without Browser.close or context.close on the shared browser.
process.stdout.write(JSON.stringify(result) + "\n", () => process.exit(status === "passed" ? 0 : status === "failed" ? 1 : 3));
