/** Verify the mixed-provider Overview filter against the real owner registry. */
import { chromium } from "../../frontend/node_modules/@playwright/test/index.mjs";

const endpoint = process.env.AGENTMONITOR_TEST_DASHBOARD_CDP_ENDPOINT;
const origin = process.env.AGENTMONITOR_TEST_DASHBOARD_ORIGIN;
let stage = "prerequisites";
class VerificationError extends Error {
  constructor(message, blocked = false) { super(message); this.blocked = blocked; }
}
function requireResult(condition, reason) {
  if (!condition) throw new VerificationError(reason);
}
function requireLive(condition, reason) {
  if (!condition) throw new VerificationError(reason, true);
}

try {
  requireLive(endpoint && origin
    && new URL(endpoint).hostname === "127.0.0.1"
    && new URL(origin).hostname === "127.0.0.1",
  "explicit_loopback_dashboard_required");
  let browser;
  try { browser = await chromium.connectOverCDP(endpoint); }
  catch { throw new VerificationError("shared_dashboard_required", true); }
  const page = browser.contexts().flatMap(context => context.pages())
    .find(candidate => new URL(candidate.url()).origin === origin);
  requireLive(page, "shared_dashboard_required");
  let responses;
  try {
    responses = await page.evaluate(async () => {
      const read = async path => {
        const response = await fetch(path);
        return { status: response.status, body: response.ok ? await response.json() : null };
      };
      return {
        accounts: await read("/api/v1/accounts?limit=200"),
        organizations: await read("/api/v1/organizations?limit=200"),
      };
    });
  } catch {
    throw new VerificationError("authenticated_versioned_read_required", true);
  }
  requireLive(![401, 403].includes(responses.accounts.status)
    && ![401, 403].includes(responses.organizations.status),
  "authenticated_versioned_read_required");
  requireResult(responses.accounts.status === 200 && responses.organizations.status === 200,
    "versioned_read_unavailable");
  const snapshot = {
    accounts: responses.accounts.body.items
      .filter(account => account.lifecycle !== "archived"),
    organizations: responses.organizations.body.items,
  };
  const providers = [...new Set(snapshot.accounts.map(account => account.provider_key))]
    .sort((left, right) => left.localeCompare(right));
  requireLive(providers.includes("claude") && providers.includes("codex"),
    "real_claude_and_codex_accounts_required");
  const accountsById = new Map(snapshot.accounts.map(account => [account.account_id, account]));
  let mutations = 0;
  page.on("request", request => {
    const url = new URL(request.url());
    if (url.origin === origin && url.pathname.startsWith("/api/v1/")
        && !["GET", "HEAD"].includes(request.method())) mutations += 1;
  });

  await page.goto(origin);
  const table = page.getByRole("table", { name: "Account quota overview", exact: true });
  await table.waitFor({ timeout: 15_000 });
  stage = "provider_filter";
  const providerFilter = page.getByRole("combobox", { name: "Provider", exact: true });
  requireResult(await providerFilter.count() === 1, "provider_filter_missing");
  requireResult(await providerFilter.inputValue() === "all", "all_providers_not_default");
  const optionValues = await providerFilter.locator("option").evaluateAll(options =>
    options.map(option => ({ value: option.value, label: option.textContent?.trim() })));
  requireResult(optionValues.some(option => option.value === "all" && option.label === "All providers")
    && optionValues.some(option => option.value === "claude" && option.label === "Claude")
    && optionValues.some(option => option.value === "codex" && option.label === "Codex"),
  "provider_options_missing");

  const visibleIds = () => table.locator("tbody tr").evaluateAll(rows =>
    rows.map(row => row.dataset.accountId).filter(Boolean).sort());
  const assertProvider = async providerKey => {
    const ids = await visibleIds();
    requireResult(ids.length > 0, `${providerKey}_rows_missing`);
    requireResult(ids.every(id => accountsById.get(id)?.provider_key === providerKey),
      `${providerKey}_filter_mismatch`);
    const expectedConnections = snapshot.accounts
      .filter(account => account.provider_key === providerKey).length;
    const countText = await page.locator(".fleet-overview-controls > span").textContent();
    requireResult(countText?.includes(`${ids.length} account row`)
      && countText.includes(`${expectedConnections} of ${snapshot.accounts.length} connections listed`),
    "provider_filtered_count_mismatch");
    return ids;
  };

  const allIds = await visibleIds();
  requireResult(allIds.length > 0, "overview_rows_missing");
  await providerFilter.focus();
  requireResult(await providerFilter.evaluate(node => document.activeElement === node),
    "provider_filter_not_keyboard_accessible");
  await page.keyboard.press("Home");
  await page.keyboard.press("ArrowDown");
  requireResult(await providerFilter.inputValue() === providers[0],
    "provider_filter_keyboard_selection_failed");
  await assertProvider(providers[0]);

  await providerFilter.selectOption("claude");
  const claudeIds = await assertProvider("claude");
  await providerFilter.selectOption("codex");
  const codexIds = await assertProvider("codex");
  requireResult(claudeIds.every(id => !codexIds.includes(id)), "provider_rows_overlap");
  await providerFilter.selectOption("all");
  requireResult(JSON.stringify(await visibleIds()) === JSON.stringify(allIds),
    "all_providers_reset_failed");

  stage = "provider_organization_composition";
  const organization = snapshot.organizations.find(item => {
    const members = snapshot.accounts.filter(account => account.organization_id === item.organization_id);
    return members.some(account => account.provider_key === "claude")
      && members.some(account => account.provider_key === "codex");
  });
  requireLive(organization, "mixed_provider_organization_required");
  const organizationFilters = page.getByRole("group", { name: "Organizations", exact: true });
  const organizationButton = organizationFilters.getByRole("button", { name: organization.name, exact: true });
  await organizationButton.click();
  await providerFilter.selectOption("claude");
  const organizationClaudeIds = await visibleIds();
  const expectedOrganizationClaudeIds = allIds
    .filter(id => {
      const account = accountsById.get(id);
      return account?.provider_key === "claude"
        && account.organization_id === organization.organization_id;
    })
    .sort();
  requireResult(expectedOrganizationClaudeIds.length > 0
    && JSON.stringify(organizationClaudeIds) === JSON.stringify(expectedOrganizationClaudeIds),
  "provider_organization_filter_mismatch");
  await organizationFilters.getByRole("button", { name: "All organizations", exact: true }).click();

  stage = "provider_filter_refresh";
  await providerFilter.selectOption("codex");
  const refreshResponse = page.waitForResponse(response => {
    const url = new URL(response.url());
    return url.origin === origin && url.pathname === "/api/v1/accounts"
      && response.request().method() === "GET";
  });
  await page.getByRole("button", { name: "Refresh overview", exact: true }).click();
  requireResult((await refreshResponse).status() === 200, "provider_refresh_unavailable");
  await page.waitForFunction(() => document.querySelector(".fleet-overview")?.getAttribute("aria-busy") === "false");
  requireResult(await providerFilter.inputValue() === "codex", "provider_selection_lost_after_refresh");
  await assertProvider("codex");
  stage = "provider_filter_periodic_refresh";
  const periodicResponse = await page.waitForResponse(response => {
    const url = new URL(response.url());
    return url.origin === origin && url.pathname === "/api/v1/accounts"
      && response.request().method() === "GET";
  }, { timeout: 40_000 });
  requireResult(periodicResponse.status() === 200, "provider_periodic_refresh_unavailable");
  await page.waitForFunction(() => document.querySelector(".fleet-overview")?.getAttribute("aria-busy") === "false");
  requireResult(await providerFilter.inputValue() === "codex",
    "provider_selection_lost_after_periodic_refresh");
  await assertProvider("codex");
  stage = "provider_filter_responsive";
  const priorViewport = page.viewportSize() ?? { width: 1280, height: 800 };
  try {
    for (const viewport of [
      { width: 1920, height: 1080 },
      { width: 1280, height: 800 },
      { width: 390, height: 844 },
    ]) {
      await page.setViewportSize(viewport);
      await page.evaluate(() => new Promise(resolve =>
        requestAnimationFrame(() => requestAnimationFrame(resolve))));
      requireResult(await providerFilter.isVisible(), "provider_filter_hidden");
      requireResult(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1),
        "provider_filter_horizontal_overflow");
    }
  } finally {
    await page.setViewportSize(priorViewport);
  }
  requireResult(mutations === 0, "provider_filter_started_mutation");
  console.log(`DASHBOARD PROVIDER FILTER: PASSED — ${claudeIds.length} Claude rows, ${codexIds.length} Codex rows, all-provider reset, organization composition, keyboard access, manual/periodic refresh retention, desktop/mobile reflow, zero mutations`);
  process.exit(0);
} catch (error) {
  const reason = error instanceof Error && /^[a-z0-9_]+$/.test(error.message)
    ? error.message : "browser_verification_failed";
  const blocked = error instanceof VerificationError && error.blocked;
  console.log(`DASHBOARD PROVIDER FILTER: ${blocked ? "BLOCKED" : "FAILED"} — ${stage}: ${reason}`);
  process.exit(blocked ? 3 : 1);
}
