// Real keyboard navigation over unchanged genuine data. No mouse shortcuts,
// network interception, owner credentials, screenshots, or browser zoom emulation.
const origin = process.argv[2];
let page, browser, stage = "origin", passed = false, mutations = 0, focusChecks = 0;
const check = condition => { if (!condition) throw new Error(); };
const instant = value => value.replace(/(?:\.(\d{1,6}))?Z$/, (_, fraction) => `.${(fraction ?? "").padEnd(6, "0")}Z`);
const exact = value => {
  const number = BigInt(value.coefficient), digits = (number < 0n ? -number : number).toString().padStart(value.scale + 1, "0");
  return `${number < 0n ? "-" : ""}${value.scale === 0 ? digits : `${digits.slice(0, -value.scale)}.${digits.slice(-value.scale)}`} ${value.currency}`;
};
try {
  check(/^http:\/\/127\.0\.0\.1:\d+$/.test(origin ?? ""));
  let input = "";
  for await (const part of process.stdin) input += part;
  const packet = JSON.parse(input); input = "";
  for (const key of ["period_start", "period_end", "as_of"]) packet[key] = new Date(packet[key]).toISOString();
  let playwright;
  try { playwright = await import("@playwright/test"); }
  catch (error) {
    if (error?.code !== "ERR_MODULE_NOT_FOUND") throw error;
    playwright = await import("/home/dev/.local/share/agentmonitor/worktrees/dashboard-product-promotion/frontend/node_modules/@playwright/test/index.mjs");
  }
  stage = "browser";
  browser = await playwright.chromium.launch({ channel: "chrome", headless: true });
  const context = await browser.newContext();
  page = await context.newPage(); page.setDefaultTimeout(10000);
  await page.setViewportSize({ width: 1366, height: 768 });
  async function read(path) {
    const response = await page.request.get(origin + path, { headers: { Origin: origin }, timeout: 10000 });
    if (response.status() === 401) { stage = "authentication_required"; throw new Error(); }
    check(response.ok()); return response.json();
  }
  async function visibleFocus(target) {
    const focus = await target.evaluate(element => {
      const style = getComputedStyle(element), rect = element.getBoundingClientRect();
      const hit = document.elementFromPoint(rect.left + rect.width / 2, rect.top + rect.height / 2);
      return {
        active: document.activeElement === element,
        visible: element.matches(":focus-visible"),
        outline: style.outlineStyle !== "none" && parseFloat(style.outlineWidth) >= 1
          && style.outlineColor !== "transparent" && !/rgba\([^)]*,\s*0\)$/.test(style.outlineColor),
        size: rect.width > 0 && rect.height > 0,
        onscreen: rect.left >= 0 && rect.top >= 0 && rect.right <= innerWidth + 1 && rect.bottom <= innerHeight + 1,
        unobscured: hit === element || element.contains(hit),
      };
    });
    for (const [name, value] of Object.entries(focus)) {
      if (!value) {
        stage += `_${name}`;
        if (name === "onscreen") {
          const geometry = await target.evaluate(element => {
            const rect = element.getBoundingClientRect();
            return [rect.left, rect.top, rect.right, rect.bottom, innerWidth, innerHeight,
              document.documentElement.scrollWidth].map(Math.round);
          });
          stage += `_geometry_${geometry.join("_")}`;
        }
        throw new Error();
      }
    }
    focusChecks++;
  }
  async function tabTo(target) {
    await target.waitFor({ state: "visible" });
    for (let index = 0; index < 300; index++) {
      if (await target.evaluate(element => document.activeElement === element)) { await visibleFocus(target); return; }
      await page.keyboard.press("Tab");
    }
    throw new Error();
  }
  async function attribute(name, value) {
    return page.evaluate(({ name, value }) => `[${name}="${CSS.escape(value)}"]`, { name, value });
  }
  stage = "authentication";
  await page.goto(`${origin}/login`, { waitUntil: "domcontentloaded" });
  await page.getByLabel("Administrator password").fill(packet.credential);
  packet.credential = "";
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await page.getByRole("region", { name: "Overview filters", exact: true }).waitFor();
  page.on("request", request => { if (!["GET", "HEAD", "OPTIONS"].includes(request.method())) mutations++; });
  const period = new URLSearchParams({ period_start: packet.period_start, period_end: packet.period_end, as_of: packet.as_of });
  await page.goto(`${origin}/?${period}`, { waitUntil: "domcontentloaded" });
  await page.locator('.financial-overview[aria-busy="false"] [data-financial-row]').first().waitFor();
  stage = "overview_period_preserved";
  for (const key of ["period_start", "period_end", "as_of"]) check(new URL(page.url()).searchParams.get(key) === packet[key]);
  // One starting point only; every tested control is reached by actual Tab.
  await page.locator(".skip-link").focus();
  stage = "organization_keyboard_focus";
  const all = page.getByRole("button", { name: "All organizations", exact: true });
  await tabTo(all); await page.keyboard.press("Enter"); check(await all.getAttribute("aria-pressed") === "true");
  stage = "provider_keyboard_focus";
  const provider = page.getByRole("combobox", { name: "Provider", exact: true });
  await tabTo(provider); await page.keyboard.press("Home"); check(await provider.inputValue() === "all");
  stage = "resources_keyboard_activation";
  const resources = page.getByRole("combobox", { name: "Resources", exact: true });
  await tabTo(resources); await page.keyboard.press("End"); await page.keyboard.press("Enter");
  await page.waitForURL(url => url.searchParams.get("resource_type") === "api");
  check(await resources.inputValue() === "api");
  check(!await page.getByRole("table", { name: "Account quota overview", exact: true }).isVisible());
  const financial = page.getByRole("region", { name: "API usage & spend", exact: true });
  check(await financial.isVisible());
  stage = "genuine_monetary_selection";
  const query = new URLSearchParams();
  for (const key of ["period_start", "period_end", "as_of"]) {
    const value = new URL(page.url()).searchParams.get(key); check(value !== null); query.set(key, value);
  }
  query.set("limit", "200");
  let chosen, selected, snapshot, revision;
  const cursors = new Set();
  for (let index = 0; index < 100; index++) {
    const result = await read(`/api/v1/budgets?${query}`);
    check(["available", "partial"].includes(result.availability.state));
    revision ??= result.registry_revision; check(revision === result.registry_revision);
    chosen = result.items.find(row => row.contexts.some(item => item.spend !== null && item.currency !== null && item.completeness === "complete"));
    if (chosen) { selected = chosen.contexts.find(item => item.spend !== null && item.currency !== null && item.completeness === "complete"); snapshot = result; break; }
    if (!result.page.has_more) break;
    check(typeof result.page.next_cursor === "string" && !cursors.has(result.page.next_cursor));
    cursors.add(result.page.next_cursor); query.set("cursor", result.page.next_cursor);
  }
  check(chosen !== undefined && selected !== undefined);
  const row = financial.locator(await attribute("data-financial-row", chosen.row_id));
  for (let index = 0; await row.count() === 0 && index < 100; index++) {
    stage = "pagination_keyboard";
    const more = financial.getByRole("button", { name: "Load more financial rows", exact: true });
    await tabTo(more); await page.keyboard.press("Enter");
    await page.locator('.financial-overview[aria-busy="false"]').waitFor();
  }
  stage = "account_link_keyboard";
  const entry = row.locator('th[scope="row"] > button').first();
  await tabTo(entry); await page.keyboard.press("Enter");
  const first = chosen.contexts[0];
  await page.waitForURL(url => url.pathname === `/accounts/${encodeURIComponent(first.report_account_id ?? chosen.account.account_id)}`);
  check(new URL(page.url()).searchParams.get("budget_report") === first.report_id);
  await page.waitForFunction(() => document.activeElement?.id === "budget-account-title");
  stage = "back_navigation";
  await page.goBack({ waitUntil: "domcontentloaded" });
  await row.waitFor();
  check(new URL(page.url()).searchParams.get("resource_type") === "api");
  await page.locator(".skip-link").focus();
  stage = "report_link_keyboard";
  const reportLink = row.locator(await attribute("data-overview-report", selected.report_id)).getByRole("button", { name: "View report", exact: true });
  await tabTo(reportLink); await page.keyboard.press("Enter");
  const accountId = selected.report_account_id ?? chosen.account.account_id;
  const resourceId = selected.report_resource_id ?? chosen.resource_id;
  await page.waitForURL(url => url.pathname === `/accounts/${encodeURIComponent(accountId)}`);
  const address = new URL(page.url());
  check(address.searchParams.get("budget_report") === selected.report_id && address.searchParams.get("budget_resource") === resourceId);
  check(instant(address.searchParams.get("budget_as_of")) === instant(snapshot.as_of));
  const forecastQuery = new URLSearchParams({ account_id: accountId, report_id: selected.report_id, period_start: snapshot.period.start, period_end: snapshot.period.end, as_of: snapshot.as_of });
  const expected = await read(`/api/v1/budgets/${encodeURIComponent(resourceId)}/forecast?${forecastQuery}`);
  stage = "genuine_rate_required";
  check(expected.rate !== null && expected.report.report_id === selected.report_id);
  const section = page.getByRole("region", { name: "Selected financial report", exact: true });
  const rate = section.getByRole("region", { name: "Observed spending rate", exact: true });
  await section.locator('[data-budget-rate][aria-busy="false"]').waitFor();
  const details = rate.locator("details"), summary = details.locator("summary");
  stage = "calculation_keyboard_focus";
  await tabTo(summary); check(await details.getAttribute("open") === null);
  stage = "calculation_keyboard_open";
  await page.keyboard.press("Enter"); await details.locator("dl").waitFor({ state: "visible" });
  const text = await details.textContent();
  check(text.includes(exact(expected.rate.cost)) && text.includes(`${expected.rate.covered_seconds} seconds`));
  check(text.includes(expected.method_id) && text.includes(expected.method_version));
  check(expected.rate.input_report_ids.every(value => text.includes(value)) && expected.rate.input_bucket_keys.every(value => text.includes(value)));
  await visibleFocus(summary);
  stage = "calculation_keyboard_close";
  await page.keyboard.press("Space"); check(await details.getAttribute("open") === null);
  stage = "calculation_narrow_keyboard";
  await page.setViewportSize({ width: 768, height: 1024 });
  await page.keyboard.press("Tab"); await page.keyboard.press("Shift+Tab"); await visibleFocus(summary);
  await page.keyboard.press("Enter"); await details.locator("dl").waitFor({ state: "visible" });
  check(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1));
  stage = "read_only"; check(mutations === 0);
  passed = true;
  console.log(`M7 ACCESSIBILITY BROWSER: PASSED focus_checks=${focusChecks} native_zoom=not_run`);
} catch {
  console.log(`M7 ACCESSIBILITY BROWSER: FAILED — ${stage}`);
} finally {
  if (page) await page.close().catch(() => { passed = false; });
  if (browser) await browser.close().catch(() => { passed = false; });
}
process.stdout.write("", () => process.exit(passed ? 0 : 1));
