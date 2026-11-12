"use strict";

// Installed setup surface only. Never submit configuration or inspect credentials.
const origin = "http://127.0.0.1:43110";
const expectedRevision = /^[a-f0-9]{40}$/.test(process.argv[2] ?? "") ? process.argv[2] : null;
const checks = { authentication: "not_run", revision: "not_run", overview: "not_run", setup_form: "not_run", account_layout: "not_run", scope_contract: "not_run", continuity: "not_run", read_only: "not_run" };
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

function stop(nextStatus, reason) {
  status = nextStatus;
  reasonCode = reason;
  throw new Error("probe_stopped");
}

function requireEvidence(condition, reason) {
  if (!condition) stop("failed", reason);
  if (unsafeRequests !== 0) stop("failed", "unexpected_mutation_request");
}

async function noOverflow() {
  requireEvidence(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1), "horizontal_overflow");
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
    if (typeof error === "string" && /^net::ERR_[A-Z_]+$/.test(error)) failedRequests.push(error);
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
  requireEvidence(unsafeRequests === 0, "unexpected_mutation_request");
  status = "passed";
  reasonCode = "installed_setup_surface_verified";
} catch (error) {
  errorKind = error?.name === "TimeoutError" ? "timeout" : "assertion_or_error";
  if (error?.message !== "probe_stopped") {
    const authRequired = page !== undefined && await page.getByRole("heading", { name: "Sign in", exact: true }).isVisible().catch(() => false);
    status = authRequired || ["tooling", "browser", "authentication", "revision"].includes(stage) ? "blocked" : "failed";
    reasonCode = authRequired ? "authentication_required" : {
      tooling: "browser_tooling_unavailable", browser: "browser_unavailable",
      authentication: "dashboard_unavailable", revision: "revision_unavailable",
      overview: "overview_unavailable", setup_form: "setup_form_unavailable",
      continuity: "continuity_unavailable", account_layout: "account_layout_unavailable",
      scope_contract: "scope_contract_unavailable",
    }[stage];
  }
  if (checks[stage] === "not_run") checks[stage] = status;
} finally {
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
  setup_step: setupStep, error_kind: errorKind, failed_requests: [...new Set(failedRequests)],
  observed_at: new Date().toISOString(),
};
// Exiting disconnects CDP without Browser.close or context.close on the shared browser.
process.stdout.write(JSON.stringify(result) + "\n", () => process.exit(status === "passed" ? 0 : status === "failed" ? 1 : 3));
