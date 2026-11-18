// Actual authenticated reads only; never controls processes or changes accounts.
const origin = process.argv[2] ?? "http://127.0.0.1:43110";
const expectedRevision = process.argv[3];
let page, stage = "origin", status = "failed", trees = 0, mutations = 0, rowsVerified = 0;
const check = condition => { if (!condition) throw new Error(); };
const path = value => new URL(value).pathname;
const isTree = value => /^\/api\/v1\/sessions\/[^/]+\/tree$/.test(path(value));
const words = value => value.replaceAll("_", " ");
try {
  check(/^http:\/\/127\.0\.0\.1:\d+$/.test(origin));
  check(expectedRevision === undefined || /^[a-f0-9]{40}$/.test(expectedRevision));
  let playwright;
  try { playwright = await import("@playwright/test"); }
  catch (error) {
    if (error?.code !== "ERR_MODULE_NOT_FOUND") throw error;
    playwright = await import("/home/dev/.local/share/agentmonitor/worktrees/dashboard-product-promotion/frontend/node_modules/@playwright/test/index.mjs");
  }
  stage = "authenticated_context";
  const browser = await playwright.chromium.connectOverCDP("http://127.0.0.1:9225", { timeout: 5000 });
  const context = browser.contexts().find(value => value.pages().some(tab => tab.url().startsWith("http://127.0.0.1:43110/")));
  check(context !== undefined);
  page = await context.newPage(); page.setDefaultTimeout(10000);
  let unsolicited;
  let treeSignal = new Promise(resolve => { unsolicited = resolve; });
  page.on("request", request => {
    if (isTree(request.url())) { trees++; unsolicited(); }
    if (!["GET", "HEAD", "OPTIONS"].includes(request.method())) mutations++;
  });
  if (expectedRevision !== undefined) {
    stage = "installed_revision";
    const version = await page.request.get(`${origin}/api/v1/operations/versions`, { headers: { Origin: origin } });
    check(version.ok() && (await version.json()).source_revision?.value === expectedRevision);
  }
  async function openList(address, accountId, reload = false) {
    const before = trees;
    treeSignal = new Promise(resolve => { unsolicited = resolve; });
    const response = page.waitForResponse(value => path(value.url()) === "/api/v1/sessions" && new URL(value.url()).searchParams.get("account_id") === (accountId ?? null));
    if (reload) await page.reload({ waitUntil: "domcontentloaded" });
    else await page.goto(address, { waitUntil: "domcontentloaded" });
    stage = "actual_session_list";
    const result = await response;
    check(result.ok());
    const sessions = await result.json();
    check(sessions.items.length > 0 && ["available", "partial"].includes(sessions.availability.state));
    const summary = page.locator('[aria-label="Runtime observations shown"]');
    stage = "unsolicited_tree_requests";
    await Promise.race([treeSignal, summary.waitFor({ state: "attached" })]);
    check(trees === before);
    await summary.waitFor({ state: "attached" });
    await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
    check(trees === before);
    stage = "session_summary_preserved";
    const panel = summary.locator("..");
    check(await panel.locator(".session-row").count() === sessions.items.length);
    check((await summary.textContent()).includes(`${sessions.items.length}sessions shown`));
    rowsVerified += sessions.items.length;
    return { sessions, panel };
  }
  const overview = await openList(`${origin}/`);
  stage = "process_summary_preserved";
  check(await overview.panel.getByRole("region", { name: "Process observations table", exact: true }).count() === 1);
  check(await overview.panel.locator("tr[data-process-id]").count() > 0);
  check((await overview.panel.locator('[aria-label="Runtime observations shown"]').textContent()).includes("processes shown"));

  async function expand(sessions, panel) {
    const record = sessions.items[0], row = panel.locator(".session-row").first();
    const button = row.getByRole("button", { name: "Show hierarchy", exact: true });
    stage = "explicit_hierarchy_control";
    await button.waitFor(); check(await button.getAttribute("aria-expanded") === "false");
    const before = trees;
    const response = page.waitForResponse(value => path(value.url()) === `/api/v1/sessions/${encodeURIComponent(record.session_id)}/tree`);
    await button.focus(); await button.press("Enter");
    stage = "explicit_hierarchy_response";
    const result = await response; check(result.ok());
    const expected = await result.json();
    check(expected.root_session_id === record.session_id && trees === before + 1);
    const tree = row.locator('[data-session-tree="true"]'); await tree.waitFor();
    const heading = tree.getByRole("heading", { name: "Session hierarchy", exact: true });
    await heading.waitFor();
    stage = "exact_hierarchy";
    check((await tree.textContent()).includes(`Included ${expected.included_count} · Excluded ${expected.excluded_count} · Unknown ${expected.unknown_count}`));
    const byId = new Map(expected.nodes.map(node => [node.session.session_id, node]));
    const reachable = [];
    function visit(id, ancestors = new Set()) {
      const node = byId.get(id); if (!node || ancestors.has(id)) return;
      reachable.push(id); const seen = new Set([...ancestors, id]);
      for (const child of node.child_session_ids) visit(child, seen);
    }
    visit(expected.root_session_id);
    check(reachable.length > 0);
    const rendered = await tree.locator('[data-session-tree-node="true"]').evaluateAll(nodes => nodes.map(node => node.dataset.sessionId));
    check(JSON.stringify(rendered) === JSON.stringify(reachable));
    for (const reason of expected.reason_codes) if (expected.partial) check((await tree.textContent()).includes(words(reason)));
    stage = "cached_hierarchy_reopen";
    const hide = row.getByRole("button", { name: "Hide hierarchy", exact: true });
    check(await hide.getAttribute("aria-expanded") === "true");
    await hide.click(); check(!await heading.isVisible());
    await row.getByRole("button", { name: "Show hierarchy", exact: true }).click(); await heading.waitFor();
    await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
    check(trees === before + 1);
    check(await panel.locator(".session-row").count() === sessions.items.length);
  }
  await expand(overview.sessions, overview.panel);
  const refreshed = await openList(`${origin}/`, undefined, true);
  check(await refreshed.panel.locator('[data-session-tree="true"]').count() === 0);
  await expand(refreshed.sessions, refreshed.panel);
  const sessionsPage = await openList(`${origin}/sessions`);
  await expand(sessionsPage.sessions, sessionsPage.panel);
  const linked = sessionsPage.sessions.items.find(item => item.account_id !== null);
  if (linked !== undefined) await openList(`${origin}/accounts/${encodeURIComponent(linked.account_id)}`, linked.account_id);
  stage = "read_only"; check(mutations === 0 && trees === 3);
  status = "passed";
  console.log(`M7 SESSION HIERARCHY BROWSER: PASSED explicit_reads=${trees} rows_checked=${rowsVerified} account_entry=${linked !== undefined}`);
} catch {
  console.log(`M7 SESSION HIERARCHY BROWSER: FAILED — ${stage}`);
} finally {
  await page?.close().catch(() => { status = "failed"; });
}
process.stdout.write("", () => process.exit(status === "passed" ? 0 : 1));
