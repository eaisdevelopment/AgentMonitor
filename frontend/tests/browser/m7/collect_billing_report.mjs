// One real dashboard-authorized collection. No key entry, account configuration,
// provider URL override, request replay, or mutation after an uncertain POST.
const [expectedRevision, provider, account, resource, category, grouping, range] = process.argv.slice(2);
if (!/^[a-f0-9]{40}$/.test(expectedRevision ?? "") ||
    !["anthropic", "openai"].includes(provider) ||
    ![account, resource].every(value => /^[A-Za-z0-9_.:-]{1,128}$/.test(value ?? "")) ||
    !/^(cost|usage_[a-z_]+)$/.test(category ?? "") ||
    !["", "project", "api_key_id", "model", "token_category", "workspace"].includes(grouping) ||
    !["7d", "30d"].includes(range)) throw new Error("collection_arguments_invalid");
const origin = "http://127.0.0.1:43110";
const expectedGrouping = grouping ? [grouping] : [];
let browser, posts = 0, stage = "browser", receipt = null;
const check = (condition, failure) => { if (!condition) { stage = failure; throw new Error(); } };
const delay = ms => new Promise(resolve => setTimeout(resolve, ms));
try {
  let playwright;
  try { playwright = await import("@playwright/test"); }
  catch (error) {
    if (error?.code !== "ERR_MODULE_NOT_FOUND") throw error;
    playwright = await import("/home/dev/.local/share/agentmonitor/worktrees/dashboard-product-promotion/frontend/node_modules/@playwright/test/index.mjs");
  }
  browser = await playwright.chromium.connectOverCDP("http://127.0.0.1:9225");
  const context = browser.contexts()[0];
  async function read(path) {
    const response = await context.request.get(origin + path, { headers: { Origin: origin }, timeout: 10000 });
    check(response.status() === 200, "authenticated_read_unavailable");
    return response.json();
  }
  async function verifyRevision() {
    const version = await read("/api/v1/operations/versions");
    check(version.source_revision?.value === expectedRevision, "installed_revision_mismatch");
  }
  await verifyRevision();
  const registry = await read(`/api/v1/accounts/${account}/billing-connections`);
  const providerKey = provider === "openai" ? "codex" : "claude";
  check(registry.account_id === account && registry.provider_key === providerKey &&
    registry.connections.some(item => item.resource_id === resource && item.provider_key === providerKey),
  "billing_resource_mismatch");
  const end = new Date(); end.setUTCHours(0, 0, 0, 0);
  const start = new Date(+end - (range === "30d" ? 30 : 7) * 86400000);
  const query = new URLSearchParams({ range_key: range, interval_start: start.toISOString(),
    interval_end: end.toISOString(), source_category: category, ...(grouping ? { grouping } : {}) });
  const eligibilityPath = `/api/v1/accounts/${account}/billing-connections/${resource}/collection-eligibility/v2?${query}`;
  function sameContext(value) {
    return value?.source_category === category && value.range_key === range &&
      Date.parse(value.interval_start) === +start && Date.parse(value.interval_end) === +end &&
      JSON.stringify(value.grouping) === JSON.stringify(expectedGrouping);
  }
  let eligibility = await read(eligibilityPath);
  check(sameContext(eligibility.report_context), "context_mismatch");
  if (!eligibility.can_collect) {
    check(eligibility.reason_code === "billing_check_rate_limited" && eligibility.next_allowed_at, "not_collectable");
    console.log(JSON.stringify({ provider, status: "waiting", reason: eligibility.reason_code,
      next_allowed_at: eligibility.next_allowed_at }));
  }
  const stop = Date.now() + 1200000;
  while (!eligibility.can_collect && Date.now() < stop) {
    check(eligibility.reason_code === "billing_check_rate_limited", "eligibility_changed");
    const next = Date.parse(eligibility.next_allowed_at);
    check(Number.isFinite(next), "cooldown_invalid");
    await delay(Math.min(30000, Math.max(1000, next - Date.now() + 100)));
    eligibility = await read(eligibilityPath);
  }
  check(eligibility.can_collect && sameContext(eligibility.report_context), "cooldown_not_finished");
  await verifyRevision();
  const page = context.pages().find(item => {
    try { return new URL(item.url()).origin === origin; } catch { return false; }
  });
  check(page, "existing_dashboard_tab_required");
  stage = "collection_submission";
  // Count the attempted POST before waiting: a lost response never permits a retry.
  posts = 1;
  const accepted = await page.evaluate(async ({ account, resource, eligibility }) => {
    const cookie = document.cookie.split(";").map(value => value.trim()).find(value => value.startsWith("agentmonitor_csrf="));
    if (!cookie) return { status: 0 };
    const id = Array.from(crypto.getRandomValues(new Uint8Array(16)), byte => byte.toString(16).padStart(2, "0")).join("");
    const response = await fetch(`/api/v1/accounts/${account}/billing-connections/${resource}/collections/v2`, {
      method: "POST", credentials: "same-origin",
      headers: { "Content-Type": "application/json", "X-CSRF-Token": decodeURIComponent(cookie.slice("agentmonitor_csrf=".length)),
        "If-Match": `"${account}.${eligibility.account_record_version}"`, "Idempotency-Key": id },
      body: JSON.stringify({ expected_connection_version: eligibility.connection_record_version, report_context: eligibility.report_context }),
    });
    return response.status === 202 ? { status: 202, run: await response.json() } : { status: response.status };
  }, { account, resource, eligibility });
  check(accepted.status === 202, "collection_not_accepted");
  let run = accepted.run;
  check(typeof run.run_id === "string", "run_missing");
  const runId = run.run_id;
  const until = Date.now() + 130000;
  while (["requested", "queued", "running", "committing"].includes(run.state) && Date.now() < until) {
    await delay(2000);
    run = await read(`/api/v1/collection-runs/${encodeURIComponent(runId)}/budget/v2`);
  }
  receipt = { provider, state: run.state, error_code: run.error_code, report_id: run.report_id,
    run_id: run.run_id, source_category: run.report_context?.source_category, grouping: run.report_context?.grouping, posts };
  check(run.run_id === runId && run.account_id === account && run.resource_id === resource &&
    run.state === "succeeded" && run.report_id && sameContext(run.report_context), "collection_not_successful");
  await verifyRevision();
  console.log(JSON.stringify({ status: "passed", revision: expectedRevision,
    boundary: "authenticated_api_collection_no_navigation", ...receipt }));
} catch {
  console.log(JSON.stringify({ provider, status: "failed", stage, posts, receipt }));
  process.exitCode = 1;
} finally {
  await browser?.close();
}
