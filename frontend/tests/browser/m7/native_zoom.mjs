// Native Chrome page zoom in an owned disposable profile. No CDP emulation,
// owner session, screenshots, source replay or product mutations.
import { mkdtemp, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";

const origin = process.argv[2];
let context, profile, stage = "input", passed = false, mutations = 0, focusChecks = 0;
const check = value => { if (!value) throw new Error(); };
const exact = value => {
  const number = BigInt(value.coefficient), digits = (number < 0n ? -number : number).toString().padStart(value.scale + 1, "0");
  return `${number < 0n ? "-" : ""}${value.scale === 0 ? digits : `${digits.slice(0, -value.scale)}.${digits.slice(-value.scale)}`} ${value.currency ?? value.unit}`;
};
async function cleanup() {
  if (context) { const owned = context; context = undefined; await owned.close(); }
  if (profile) { const owned = profile; profile = undefined; await rm(owned, { recursive: true, force: true }); }
}
process.once("SIGTERM", () => { cleanup().finally(() => process.exit(1)); });
try {
  check(/^http:\/\/127\.0\.0\.1:\d+$/.test(origin ?? ""));
  let input = "";
  for await (const part of process.stdin) input += part;
  const packet = JSON.parse(input); input = "";
  // Overview accepts canonical UTC URLs at JavaScript millisecond precision.
  for (const key of ["period_start", "period_end", "as_of"]) packet[key] = new Date(packet[key]).toISOString();
  let playwright;
  try { playwright = await import("@playwright/test"); }
  catch (error) {
    if (error?.code !== "ERR_MODULE_NOT_FOUND") throw error;
    playwright = await import("/home/dev/.local/share/agentmonitor/worktrees/dashboard-product-promotion/frontend/node_modules/@playwright/test/index.mjs");
  }
  stage = "owned_browser";
  profile = await mkdtemp(join(tmpdir(), "agentmonitor-native-zoom-"));
  context = await playwright.chromium.launchPersistentContext(profile, {
    channel: "chrome", headless: true, viewport: null,
    args: ["--window-size=1366,900", "--no-first-run", "--disable-default-apps"],
  });
  const page = await context.newPage(); page.setDefaultTimeout(10000);
  stage = "isolated_iam_login";
  await page.goto(`${origin}/login`, { waitUntil: "domcontentloaded" });
  await page.getByLabel("Administrator password").fill(packet.credential);
  packet.credential = "";
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await page.getByRole("region", { name: "Overview filters", exact: true }).waitFor();
  page.on("request", request => { if (!["GET", "HEAD", "OPTIONS"].includes(request.method())) mutations++; });
  async function read(path) {
    const response = await page.request.get(origin + path, { headers: { Origin: origin }, timeout: 15000 });
    check(response.ok()); return response.json();
  }
  const metrics = () => page.evaluate(() => ({ dpr: devicePixelRatio, width: innerWidth, height: innerHeight,
    outerWidth, outerHeight, visualScale: visualViewport.scale }));
  const before = await metrics();
  const settings = await context.newPage();
  await settings.goto("chrome://settings/appearance");
  const zoom = settings.locator("#zoomLevel");
  stage = "native_zoom_settings";
  await zoom.waitFor();
  stage = "native_zoom_default"; check(await zoom.inputValue() === "1");
  stage = "native_zoom_selection";
  await zoom.selectOption("2"); check(await zoom.inputValue() === "2");
  // Compare foreground geometry on both sides of the native settings change.
  await page.bringToFront();
  stage = "native_zoom_dpr";
  await playwright.expect.poll(async () => (await metrics()).dpr).toBe(before.dpr * 2);
  const after = await metrics();
  stage = "native_zoom_outer_geometry";
  check(after.outerWidth === before.outerWidth && after.outerHeight === before.outerHeight);
  stage = "native_zoom_css_geometry";
  check(Math.abs(after.width * 2 - before.width) <= 1 && Math.abs(after.height * 2 - before.height) <= 1);
  stage = "native_zoom_visual_scale";
  check(after.visualScale === 1 && before.visualScale === 1);
  await page.bringToFront();
  async function focused(target) {
    const focus = await target.evaluate(element => {
      const style = getComputedStyle(element), rect = element.getBoundingClientRect();
      const left = Math.max(0, rect.left), right = Math.min(innerWidth, rect.right);
      const top = Math.max(0, rect.top), bottom = Math.min(innerHeight, rect.bottom);
      const hit = document.elementFromPoint((left + right) / 2, (top + bottom) / 2);
      return {
        active: document.activeElement === element,
        visible: element.matches(":focus-visible"),
        outline: style.outlineStyle !== "none" && parseFloat(style.outlineWidth) >= 1
          && style.outlineColor !== "transparent" && !/rgba\([^)]*,\s*0\)$/.test(style.outlineColor),
        onscreen: right > left && bottom > top,
        unobscured: hit === element || element.contains(hit),
      };
    });
    for (const [name, value] of Object.entries(focus)) {
      if (!value) { stage += `_${name}`; throw new Error(); }
    }
    focusChecks++;
  }
  async function tabTo(target) {
    await target.waitFor({ state: "visible" });
    stage += "_tab";
    for (let index = 0; index < 300; index++) {
      if (await target.evaluate(element => document.activeElement === element)) { await focused(target); return; }
      await page.keyboard.press("Tab");
    }
    throw new Error();
  }
  async function noPageOverflow() {
    const overflow = await page.evaluate(() => {
      if (document.documentElement.scrollWidth <= innerWidth + 1) return null;
      const nodes = [...document.querySelectorAll("main *")].filter(element => {
        const rect = element.getBoundingClientRect();
        return rect.width > 0 && rect.right > innerWidth + 1;
      }).slice(-5);
      return [document.documentElement.scrollWidth, innerWidth,
        ...nodes.flatMap(element => {
          const rect = element.getBoundingClientRect();
          return [element.tagName.toLowerCase(), Math.round(rect.left), Math.round(rect.width)];
        })].join("_");
    });
    if (overflow !== null) { stage += `_geometry_${overflow}`; throw new Error(); }
    check((await metrics()).dpr === after.dpr);
  }
  const query = new URLSearchParams({ period_start: packet.period_start, period_end: packet.period_end,
    as_of: packet.as_of, provider_key: "ollama", limit: "200" });
  stage = "genuine_overview";
  let chosen, selected, snapshot;
  const cursors = new Set();
  for (let index = 0; index < 100; index++) {
    const result = await read(`/api/v1/budgets?${query}`);
    chosen = result.items.find(row => row.contexts.some(item => item.spend !== null && item.currency !== null && item.completeness === "complete"));
    if (chosen) { selected = chosen.contexts.find(item => item.spend !== null && item.currency !== null && item.completeness === "complete"); snapshot = result; break; }
    if (!result.page.has_more) break;
    check(typeof result.page.next_cursor === "string" && !cursors.has(result.page.next_cursor));
    cursors.add(result.page.next_cursor); query.set("cursor", result.page.next_cursor);
  }
  check(chosen !== undefined && selected !== undefined);
  query.delete("limit"); query.delete("cursor"); query.set("resource_type", "api");
  await page.goto(`${origin}/?${query}`, { waitUntil: "domcontentloaded" });
  const financial = page.getByRole("region", { name: "API usage & spend", exact: true });
  await page.locator('.financial-overview[aria-busy="false"] [data-financial-row]').first().waitFor();
  stage = "overview_period_preserved";
  for (const key of ["period_start", "period_end", "as_of"]) check(new URL(page.url()).searchParams.get(key) === packet[key]);
  await noPageOverflow();
  await page.locator(".skip-link").focus();
  stage = "overview_zoom_keyboard";
  const provider = page.getByRole("combobox", { name: "Provider", exact: true });
  await tabTo(provider);
  const rowSelector = await page.evaluate(value => `[data-financial-row="${CSS.escape(value)}"]`, chosen.row_id);
  const row = financial.locator(rowSelector);
  for (let index = 0; await row.count() === 0 && index < 100; index++) {
    const more = financial.getByRole("button", { name: "Load more financial rows", exact: true });
    const count = await financial.locator("[data-financial-row]").count();
    await tabTo(more); await page.keyboard.press("Enter");
    await playwright.expect.poll(() => financial.locator("[data-financial-row]").count()).toBeGreaterThan(count);
  }
  const reportSelector = await page.evaluate(value => `[data-overview-report="${CSS.escape(value)}"]`, selected.report_id);
  const link = row.locator(reportSelector).getByRole("button", { name: "View report", exact: true });
  stage = "overview_zoom_report_keyboard";
  await tabTo(link);
  stage = "overview_zoom_report_activation";
  await page.keyboard.press("Enter");
  const account = selected.report_account_id ?? chosen.account.account_id;
  const resource = selected.report_resource_id ?? chosen.resource_id;
  await page.waitForURL(url => url.pathname === `/accounts/${encodeURIComponent(account)}` && url.searchParams.get("budget_report") === selected.report_id);
  stage = "detail_zoom_history";
  const section = page.getByRole("region", { name: "Selected financial report", exact: true });
  await section.locator('[data-budget-history][aria-busy="false"]').waitFor();
  stage = "detail_zoom_source";
  const sourceQuery = new URLSearchParams({ account_id: account, report_id: selected.report_id,
    period_start: snapshot.period.start, period_end: snapshot.period.end, as_of: snapshot.as_of });
  const source = await read(`/api/v1/budgets/${encodeURIComponent(resource)}?${sourceQuery}`);
  check(source.report.report_id === selected.report_id && source.report.account_id === account && source.report.resource_id === resource);
  const facts = new Map([
    ...source.report.cost_buckets.map(item => [`cost:${item.bucket_key}`, exact(item.amount)]),
    ...source.report.usage_buckets.map(item => [`usage:${item.bucket_key}`, exact(item.quantity)]),
  ]);
  stage = "detail_zoom_facts";
  const rows = await section.locator("tr[data-bucket-key]").evaluateAll(nodes => nodes.map(node => ({
    key: `${node.dataset.bucketKind}:${node.dataset.bucketKey}`, amount: node.querySelectorAll("td")[1]?.textContent,
  })));
  check(rows.length > 0 && rows.every(row => facts.has(row.key) && row.amount === facts.get(row.key)));
  stage = "detail_zoom_overflow";
  await noPageOverflow();
  stage = "history_zoom_keyboard";
  const history = section.getByRole("region", { name: "Exact cost history", exact: true });
  await tabTo(history);
  const scroll = await history.evaluate(node => ({ left: node.scrollLeft, width: node.clientWidth, content: node.scrollWidth }));
  if (scroll.content > scroll.width + 1) {
    await page.keyboard.press("ArrowRight");
    await playwright.expect.poll(() => history.evaluate(node => node.scrollLeft)).toBeGreaterThan(scroll.left);
  }
  stage = "zoom_reload";
  await page.reload({ waitUntil: "domcontentloaded" });
  await section.locator('[data-budget-history][aria-busy="false"]').waitFor();
  await noPageOverflow(); check(new URL(page.url()).searchParams.get("budget_report") === selected.report_id);
  check(mutations === 0 && focusChecks >= 3);
  passed = true;
} catch {
  // Only closed stages are emitted; never a URL, report, password or DOM dump.
} finally {
  await cleanup().catch(() => { passed = false; stage = "owned_browser_cleanup"; });
}
console.log(passed ? `M7 NATIVE ZOOM BROWSER: PASSED native_zoom=200 focus_checks=${focusChecks} mutations=0`
  : `M7 NATIVE ZOOM BROWSER: FAILED — ${stage}`);
process.exitCode = passed ? 0 : 1;
