// Real response/DOM timing only: no interception, delays, fixtures or mutations.
const origin = process.argv[2] ?? "http://127.0.0.1:43110";
let page, stage = "origin", status = "failed", mutations = 0, firstCount = 0, finalCount = 0;
const check = condition => { if (!condition) throw new Error(); };
function cycle() {
  return { accounts: [], inventoryDone: false, quota: new Map(), identity: new Map(), monitoring: new Map(), error: false, firstReady: null, signal: null };
}
let current = cycle(), subscriptions = null;
function required(account, observed) {
  return observed.quota.has(account.account_id) && observed.identity.has(account.account_id) && (account.provider_key !== "ollama" || observed.monitoring.has(account.account_id));
}
function wake(observed) {
  if (observed.inventoryDone && observed.accounts.length > 6 && observed.accounts.slice(0, 6).every(account => required(account, observed))) observed.signal?.();
}
function startCycle() {
  current = cycle(); current.firstReady = new Promise(resolve => { current.signal = resolve; }); return current;
}
async function bounded(promise, timeout = 10000) {
  let timer;
  try { return await Promise.race([promise, new Promise((_, reject) => { timer = setTimeout(() => reject(new Error()), timeout); })]); }
  finally { clearTimeout(timer); }
}
try {
  check(/^http:\/\/127\.0\.0\.1:\d+$/.test(origin));
  let playwright;
  try { playwright = await import("@playwright/test"); }
  catch (error) {
    if (error?.code !== "ERR_MODULE_NOT_FOUND") throw error;
    playwright = await import("/home/dev/.local/share/agentmonitor/worktrees/dashboard-product-promotion/frontend/node_modules/@playwright/test/index.mjs");
  }
  const browser = await playwright.chromium.connectOverCDP("http://127.0.0.1:9225", { timeout: 5000 });
  const context = browser.contexts().find(item => item.pages().some(tab => tab.url().startsWith("http://127.0.0.1:43110/")));
  check(context !== undefined);
  page = await context.newPage(); page.setDefaultTimeout(10000);
  page.on("request", request => { if (!["GET", "HEAD", "OPTIONS"].includes(request.method())) mutations++; });
  page.on("response", async response => {
    const observed = current, url = new URL(response.url());
    try {
      if (url.pathname === "/api/v1/budgets" && response.ok()) {
        const body = await response.json();
        if (body.availability.state === "available") subscriptions = body.subscription_account_ids;
        return;
      }
      const match = /^\/api\/v1\/accounts\/([^/]+)\/(capacity\/v2|provider-identity|ollama-cloud-connection)$/.exec(url.pathname);
      const inventory = url.pathname === "/api/v1/accounts" && !url.searchParams.has("provider_key");
      if (!inventory && match === null) return;
      if (!response.ok()) { observed.error = true; observed.signal?.(); return; }
      const body = await response.json();
      if (observed !== current) return;
      if (inventory) {
        for (const account of body.items) if (account.lifecycle !== "archived" && !observed.accounts.some(item => item.account_id === account.account_id)) observed.accounts.push(account);
        observed.inventoryDone = body.page.has_more === false;
      } else {
        const source = match[2] === "capacity/v2" ? observed.quota : match[2] === "provider-identity" ? observed.identity : observed.monitoring;
        source.set(decodeURIComponent(match[1]), body);
      }
      wake(observed);
    } catch { observed.error = true; observed.signal?.(); }
  });
  const first = startCycle(), deadline = Date.now() + 10000;
  await page.goto(`${origin}/`, { waitUntil: "domcontentloaded", timeout: 10000 });
  stage = "first_real_batch";
  await bounded(first.firstReady, Math.max(1, deadline - Date.now()));
  check(!first.error && first.accounts.length > 6);
  await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
  stage = "genuine_progress_window";
  check(!first.accounts.every(account => required(account, first)));
  const panel = page.locator('section[aria-labelledby="overview-accounts-title"]');
  const table = panel.getByRole("table", { name: "Account quota overview", exact: true });
  stage = "completed_batch_waits_for_tail";
  check(await table.count() === 1 && await panel.getAttribute("aria-busy") === "true");
  const firstIds = first.accounts.slice(0, 6).map(account => account.account_id);
  const rendered = await table.locator("tbody tr[data-account-id]").evaluateAll(nodes => nodes.map(node => node.dataset.accountId));
  check(rendered.length > 0 && rendered.some(id => firstIds.includes(id)) && rendered.every(id => first.accounts.some(account => account.account_id === id && required(account, first))));
  firstCount = rendered.length;
  stage = "complete_inventory";
  await page.locator('section[aria-labelledby="overview-accounts-title"][aria-busy="false"]').waitFor();
  check(first.accounts.every(account => required(account, first)) && !first.error);
  // The actual financial projection supplies subscription membership, including
  // mixed-purpose accounts; API-only accounts are not invented quota rows.
  await bounded(new Promise(resolve => {
    const poll = () => subscriptions !== null ? resolve() : setTimeout(poll, 20);
    poll();
  }));
  function members() {
    return table.locator("tbody tr[data-account-id], [data-connection-account-id]").evaluateAll(nodes => nodes.map(node => node.dataset.connectionAccountId ?? node.dataset.accountId));
  }
  const actual = await members();
  const expected = first.accounts.filter(account => subscriptions.includes(account.account_id)).map(account => account.account_id).sort();
  check(actual.length === new Set(actual).size && JSON.stringify([...actual].sort()) === JSON.stringify(expected));
  finalCount = actual.length;
  const originalRows = await table.locator("tbody tr[data-account-id]").evaluateAll(nodes => nodes.map(node => node.dataset.accountId));
  stage = "refresh_retains_real_rows";
  const refresh = startCycle();
  await panel.getByRole("button", { name: "Refresh overview", exact: true }).click();
  check(JSON.stringify((await members()).sort()) === JSON.stringify(expected));
  await bounded(refresh.firstReady); check(!refresh.error);
  await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
  check(JSON.stringify((await members()).sort()) === JSON.stringify(expected));
  await page.locator('section[aria-labelledby="overview-accounts-title"][aria-busy="false"]').waitFor();
  check(refresh.accounts.every(account => required(account, refresh)) && !refresh.error);
  check(JSON.stringify((await members()).sort()) === JSON.stringify(expected));
  // On an unchanged source snapshot the existing sort and identity dedup must
  // produce the same final primary rows after progressive refresh.
  stage = "final_sort_and_dedup";
  check(JSON.stringify(await table.locator("tbody tr[data-account-id]").evaluateAll(nodes => nodes.map(node => node.dataset.accountId))) === JSON.stringify(originalRows));
  stage = "read_only"; check(mutations === 0);
  status = "passed";
  console.log(`M7 QUOTA PROGRESS BROWSER: PASSED first_rows=${firstCount} connections=${finalCount}`);
} catch {
  console.log(`M7 QUOTA PROGRESS BROWSER: FAILED — ${stage}`);
} finally {
  await page?.close().catch(() => { status = "failed"; });
}
process.stdout.write("", () => process.exit(status === "passed" ? 0 : 1));
