"use strict";

// Read existing observations and the built financial section. Never collect,
// configure, authenticate, inspect other tabs, or emit account/financial data.
const origin = "http://127.0.0.1:43110";
let page;
let status = "blocked";
let reason = "browser_unavailable";
let mutations = 0;
let componentCount = 0;
let accountCount = 0;
let sourceRevision = null;
const checks = { authentication: "not_run", real_source: "not_run", funds_api: "not_run", financial_dom: "not_run", reload: "not_run", read_only: "not_run" };
function stop(outcome, code) { status = outcome; reason = code; throw new Error("probe_stopped"); }
function requireEvidence(condition, code) { if (!condition) stop("failed", code); }
function exactMoney(value) {
  const coefficient = BigInt(value.coefficient);
  const digits = (coefficient < 0n ? -coefficient : coefficient).toString().padStart(value.scale + 1, "0");
  return `${coefficient < 0n ? "-" : ""}${value.scale === 0 ? digits : `${digits.slice(0, -value.scale)}.${digits.slice(-value.scale)}`} ${value.currency}`;
}
try {
  let playwright;
  try { playwright = await import("@playwright/test"); }
  catch (error) {
    if (error?.code !== "ERR_MODULE_NOT_FOUND") throw error;
    playwright = await import("/home/dev/.local/share/agentmonitor/worktrees/dashboard-product-promotion/frontend/node_modules/@playwright/test/index.mjs");
  }
  const browser = await playwright.chromium.connectOverCDP("http://127.0.0.1:9225", { timeout: 5000 });
  const context = browser.contexts()[0];
  if (context === undefined) stop("blocked", "browser_context_unavailable");
  page = await context.newPage();
  page.setDefaultTimeout(7000);
  page.on("request", request => { if (!["GET", "HEAD", "OPTIONS"].includes(request.method())) mutations += 1; });
  await page.goto(origin, { waitUntil: "domcontentloaded", timeout: 10000 });
  const signIn = page.getByRole("heading", { name: "Sign in", exact: true });
  await signIn.or(page.getByRole("button", { name: "Accounts", exact: true })).first().waitFor();
  if (await signIn.isVisible()) stop("blocked", "authentication_required");
  checks.authentication = "passed";
  async function read(path) {
    const response = await page.request.get(`${origin}${path}`, { headers: { Origin: origin }, timeout: 7000 });
    if (response.status() === 401) stop("blocked", "authentication_required");
    if (response.status() !== 200) stop("blocked", "existing_api_unavailable");
    return response.json();
  }
  async function readAll(path, identity, kind) {
    const items = [];
    const identities = new Set();
    const cursors = new Set();
    let cursor;
    for (let index = 0; index < 20; index += 1) {
      const query = new URLSearchParams({ limit: "200", ...(cursor === undefined ? {} : { cursor }) });
      const result = await read(`${path}?${query}`);
      requireEvidence(Array.isArray(result.items) && typeof result.page?.has_more === "boolean", `${kind}_page_invalid`);
      for (const item of result.items) {
        const key = identity(item);
        if (identities.has(key)) stop("blocked", `${kind}_changed_during_pagination`);
        identities.add(key);
        items.push(item);
      }
      if (!result.page.has_more) {
        requireEvidence(result.page.next_cursor === null, `${kind}_terminal_cursor_invalid`);
        return items;
      }
      cursor = result.page.next_cursor;
      if (typeof cursor !== "string" || cursor.length === 0 || cursors.has(cursor)) stop("blocked", `${kind}_cursor_unavailable`);
      cursors.add(cursor);
    }
    stop("blocked", `${kind}_pagination_bound_exceeded`);
  }
  const windowIdentity = item => JSON.stringify([item.subject?.resource_id, item.window_id]);
  const componentIdentity = item => JSON.stringify([item.subject?.resource_id, item.component_id]);
  const quotaPath = account => `/api/v1/accounts/${encodeURIComponent(account.account_id)}/quotas/v2`;
  const eligibleSource = (item, accountId) => item.subject?.account_id === accountId
    && item.subject.provider_key === "ollama" && item.subject.provider_target_kind === "cloud_service"
    && item.provenance?.source_id === "ollama.cloud.balance.v1"
    && ["ollama_included_credits", "ollama_purchased_credits"].includes(item.window_key)
    && [item.remaining, item.limit].every(field => field?.value == null || field.value.unit === "usd");
  const sourceSnapshot = items => JSON.stringify(items.map(item => [windowIdentity(item), item.current_observation_id]).sort((left, right) => left[0].localeCompare(right[0])));
  const versions = await read("/api/v1/operations/versions");
  if (/^[a-f0-9]{40}$/.test(versions?.source_revision?.value ?? "")) sourceRevision = versions.source_revision.value;
  const sources = [];
  const inventory = await readAll("/api/v1/accounts", item => item.account_id, "inventory");
  for (const candidate of inventory) {
    if (candidate.provider_key !== "ollama" || candidate.lifecycle === "archived") continue;
    const quotas = await readAll(quotaPath(candidate), windowIdentity, "quota");
    if (quotas.some(item => eligibleSource(item, candidate.account_id) && item.remaining?.value?.unit === "usd")) sources.push(candidate);
  }
  if (sources.length === 0) stop("blocked", "genuine_ollama_funds_unavailable");
  checks.real_source = "passed";
  async function inspect(account, reload) {
    const path = `/api/v1/accounts/${encodeURIComponent(account.account_id)}/api-capacity`;
    // Quota HTTP accepts only limit/cursor, not as_of. Bracket the financial
    // read with complete snapshots and require immutable source identities to
    // stay unchanged. A replacement makes this comparison Blocked, not passed.
    const before = (await readAll(quotaPath(account), windowIdentity, "quota")).filter(item => eligibleSource(item, account.account_id));
    const responsePromise = page.waitForResponse(response => new URL(response.url()).pathname === path && response.request().method() === "GET");
    if (reload) await page.reload({ waitUntil: "domcontentloaded" });
    else await page.goto(`${origin}/accounts/${encodeURIComponent(account.account_id)}`, { waitUntil: "domcontentloaded" });
    const response = await responsePromise;
    if (response.status() === 401) stop("blocked", "authentication_required");
    requireEvidence(response.status() === 200, "financial_api_failed");
    const financial = await response.json();
    const after = (await readAll(quotaPath(account), windowIdentity, "quota")).filter(item => eligibleSource(item, account.account_id));
    if (sourceSnapshot(before) !== sourceSnapshot(after)) stop("blocked", "source_changed_during_probe");
    const asOf = Date.parse(financial.as_of);
    requireEvidence(financial.account_id === account.account_id && Number.isFinite(asOf), "financial_snapshot_invalid");
    const originals = before.filter(item => [item.collected_at, item.stored_at, ...(item.observed_at === null ? [] : [item.observed_at])].every(time => Date.parse(time) <= asOf));
    if (originals.length === 0) stop("blocked", "genuine_funds_at_snapshot_unavailable");
    requireEvidence(Array.isArray(financial.funds?.components) && financial.funds.components.length > 0, "budget_funds_projection_missing");
    requireEvidence(financial.funds.account_id === account.account_id && Date.parse(financial.funds.as_of) === asOf, "funds_snapshot_mismatch");
    const expectedIdentities = originals.map(windowIdentity).sort();
    const actualIdentities = financial.funds.components.map(componentIdentity).sort();
    requireEvidence(new Set(actualIdentities).size === actualIdentities.length && JSON.stringify(expectedIdentities) === JSON.stringify(actualIdentities), "funds_source_component_set_mismatch");
    const panel = page.getByRole("region", { name: "API usage & spend", exact: true });
    await panel.waitFor();
    await panel.getByRole("button", { name: "Refresh view", exact: true }).waitFor();
    const funds = panel.getByRole("region", { name: "Available funds and limits", exact: true });
    await funds.waitFor();
    const labels = { balance: "Balance", included_credits: "Included credits", purchased_credits: "Purchased credits", soft_limit: "Soft budget", hard_limit: "Hard limit" };
    requireEvidence(await funds.locator("[data-fund-component]").count() === financial.funds.components.length, "fund_dom_component_set_mismatch");
    for (const component of financial.funds.components) {
      const original = originals.find(item => windowIdentity(item) === componentIdentity(component));
      requireEvidence(original !== undefined && original.current_observation_id === component.observation_id, "funds_observation_mismatch");
      requireEvidence(component.subject.account_id === account.account_id && component.subject.provider_target_id === original.subject.provider_target_id, "funds_resource_mismatch");
      requireEvidence(original.provenance?.source_id === component.provenance.source_id, "funds_source_mismatch");
      requireEvidence(component.kind === (original.window_key === "ollama_included_credits" ? "included_credits" : "purchased_credits"), "fund_kind_mismatch");
      for (const field of ["remaining", "limit"]) {
        const actual = component[field];
        const expected = original[field];
        requireEvidence(actual.availability === expected.availability && (expected.value === null ? actual.value === null : actual.value?.coefficient === expected.value.coefficient && actual.value?.scale === expected.value.scale && actual.value?.currency === "USD"), "funds_exact_amount_mismatch");
      }
      const selector = await page.evaluate(({ resource, componentId }) => `[data-fund-resource="${CSS.escape(resource)}"][data-fund-component="${CSS.escape(componentId)}"]`, { resource: component.subject.resource_id, componentId: component.component_id });
      const row = funds.locator(selector);
      requireEvidence(await row.count() === 1, "fund_component_not_independently_rendered");
      requireEvidence(await row.getByRole("heading", { name: labels[component.kind], exact: true }).count() === 1, "fund_component_label_mismatch");
      if (component.remaining.value !== null) requireEvidence(await row.getByTitle(exactMoney(component.remaining.value), { exact: true }).count() > 0, "fund_exact_amount_not_rendered");
      requireEvidence(await row.locator("time").first().getAttribute("datetime") === (component.observed_at ?? component.collected_at), "fund_own_timestamp_missing");
      requireEvidence(await row.getByRole("meter").count() === 0, "invented_fund_percentage");
      if (component.scope_evidence === "unresolved") requireEvidence((await row.textContent()).includes("Scope unresolved"), "unresolved_fund_scope_hidden");
      if (component.is_constraining === false) requireEvidence((await row.textContent()).includes("does not determine account availability"), "non_constraining_fund_not_explained");
    }
    checks.funds_api = "passed";
    requireEvidence(!(await panel.textContent()).includes("Remaining funds not reported"), "actual_funds_reported_missing");
    if (!reload) componentCount += financial.funds.components.length;
    checks.financial_dom = "passed";
  }
  status = "failed";
  reason = "financial_dom_unavailable";
  for (const account of sources) {
    await inspect(account, false);
    await inspect(account, true);
    accountCount += 1;
  }
  checks.reload = "passed";
  requireEvidence(mutations === 0, "unexpected_mutation_request");
  status = "passed";
  reason = "real_funds_api_dom_verified";
} catch (error) {
  if (error?.message !== "probe_stopped" && checks.authentication === "passed") { status = "failed"; reason = "financial_probe_boundary_failed"; }
} finally {
  if (page !== undefined) await page.close().catch(() => { status = "failed"; reason = "probe_page_cleanup_failed"; });
  checks.read_only = page === undefined ? "not_run" : mutations === 0 ? "passed" : "failed";
  if (mutations !== 0) { status = "failed"; reason = "unexpected_mutation_request"; }
}
// Process exit disconnects CDP; never close the shared browser/context.
process.stdout.write(JSON.stringify({ record_type: "agentmonitor.m7_funds_probe.v1", status, reason_code: reason, source_revision: sourceRevision, checks, accounts_verified: accountCount, components_verified: componentCount, unsafe_requests: mutations, observed_at: new Date().toISOString() }) + "\n", () => process.exit(status === "passed" ? 0 : status === "failed" ? 1 : 3));
