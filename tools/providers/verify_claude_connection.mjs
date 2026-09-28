/** Check the real authenticated dashboard through its versioned HTTP API. */
import { chromium } from "../../frontend/node_modules/@playwright/test/index.mjs";

const endpoint = process.env.AGENTMONITOR_TEST_DASHBOARD_CDP_ENDPOINT;
const accountId = process.env.AGENTMONITOR_TEST_MANAGED_ACCOUNT_ID;
const origin = process.env.AGENTMONITOR_TEST_DASHBOARD_ORIGIN;
if (!endpoint || !accountId || !origin) {
  console.log("CLAUDE DASHBOARD: BLOCKED — explicit shared dashboard and account required");
  process.exit(3);
}

function requireResult(condition, message) {
  if (!condition) throw new Error(message);
}

try {
  requireResult(new URL(endpoint).hostname === "127.0.0.1" && new URL(origin).hostname === "127.0.0.1", "loopback dashboard required");
  const browser = await chromium.connectOverCDP(endpoint);
  const page = browser.contexts()[0]?.pages()[0];
  requireResult(page && await page.evaluate(() => window.location.origin) === origin, "shared dashboard page required");
  const response = await page.evaluate(async (id) => {
    const paths = [`/api/v1/accounts/${id}`, `/api/v1/accounts/${id}/observed-identity`, `/api/v1/accounts/${id}/capacity`, `/api/v1/accounts/${id}/connection`];
    const results = [];
    for (const path of paths) {
      const value = await fetch(path);
      if (!value.ok) return { available: false };
      results.push(await value.json());
    }
    return { available: true, account: results[0], identity: results[1], capacity: results[2], connection: results[3] };
  }, accountId);
  requireResult(response.available, "authenticated versioned account reads unavailable");
  const { account, identity, capacity, connection } = response;
  requireResult(["managed", "protected_default", "unknown"].includes(identity.profile_protection), "profile provenance missing");
  requireResult(account.lifecycle === "active" && account.is_effective_monitoring_enabled, "account is not enrolled for monitoring");
  requireResult(identity.state === "verified" && identity.email && identity.profile_protection === "managed", "no verified managed quota identity yet");
  const windows = (capacity.items ?? []).flatMap(item => item.windows);
  requireResult(windows.length >= 2 && windows.every(window => window.collection_run_id === identity.collection_run_id && window.freshness === "fresh"), "fresh per-account quota lineage missing");
  await page.goto(`${origin}/accounts/${encodeURIComponent(accountId)}`);
  await page.getByRole("heading", { level: 1, name: identity.email, exact: true }).waitFor({ timeout: 12_000 });
  const activity = page.getByRole("region", { name: "Account activity", exact: true });
  requireResult(await activity.getByRole("columnheader", { name: "Account", exact: true }).count() === 1, "account table missing");
  requireResult(await activity.getByRole("columnheader", { name: "Left", exact: true }).count() === 1, "remaining quota column missing");
  if (connection.state === "connected" && connection.flow_id !== null) {
    const panel = page.getByRole("region", { name: "Claude connection", exact: true });
    await panel.getByText("Claude connected", { exact: true }).waitFor();
    const priorViewport = page.viewportSize() ?? await page.evaluate(() => ({ width: window.innerWidth, height: window.innerHeight }));
    try {
      for (const viewport of [{ width: 1920, height: 1080 }, { width: 1280, height: 800 }, { width: 390, height: 844 }]) {
        await page.setViewportSize(viewport);
        await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
        const box = await panel.boundingBox();
        console.log(`CLAUDE CONNECTED LAYOUT: width=${viewport.width} height=${box?.height ?? "unavailable"}`);
        requireResult(box && box.height <= (viewport.width < 600 ? 112 : 72), "connected status occupies too much space");
        requireResult(box.x >= 0 && box.x + box.width <= viewport.width + 1, "connected status overflows viewport");
      }
      const button = panel.getByRole("button", { name: "Check status for Claude connection", exact: true });
      await button.focus();
      requireResult(await button.evaluate(node => document.activeElement === node), "connected status action is not keyboard accessible");
      const buttonBox = await button.boundingBox();
      requireResult(buttonBox && buttonBox.height >= 24 && buttonBox.width >= 24, "connected status action target is too small");
      let signInMutations = 0;
      const observe = request => {
        const url = new URL(request.url());
        if (url.origin === origin && url.pathname.endsWith("/connection") && request.method() !== "GET") signInMutations += 1;
      };
      page.on("request", observe);
      try {
        await Promise.all([
          page.waitForResponse(value => new URL(value.url()).pathname === `/api/v1/accounts/${accountId}/connection` && value.request().method() === "GET" && value.status() === 200),
          button.click(),
        ]);
        await panel.getByText("Claude connected", { exact: true }).waitFor();
        requireResult(signInMutations === 0, "connected status refresh started authentication");
      } finally {
        page.off("request", observe);
      }
      console.log("CLAUDE CONNECTED STATUS: PASSED — compact desktop/narrow layout and accessible read-only refresh");
    } finally {
      await page.setViewportSize(priorViewport);
    }
  }
  console.log("CLAUDE DASHBOARD: PASSED — identified managed account and fresh quota through V1 API and real browser");
  process.exit(0);
} catch (error) {
  const known = new Set(["loopback dashboard required", "shared dashboard page required", "authenticated versioned account reads unavailable", "profile provenance missing", "account is not enrolled for monitoring", "no verified managed quota identity yet", "fresh per-account quota lineage missing", "account table missing", "remaining quota column missing", "connected status occupies too much space", "connected status overflows viewport", "connected status action is not keyboard accessible", "connected status action target is too small", "connected status refresh started authentication"]);
  const message = error instanceof Error && known.has(error.message) ? error.message : "dashboard verification unavailable";
  console.log(`CLAUDE DASHBOARD: BLOCKED — ${message}`);
  process.exit(3);
}
