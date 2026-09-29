/** ST-ALERT-002: compare genuine derived alerts with the built alert console. */
import { chromium } from "../../frontend/node_modules/@playwright/test/index.mjs";

const endpoint = process.env.AGENTMONITOR_TEST_DASHBOARD_CDP_ENDPOINT;
const origin = process.env.AGENTMONITOR_TEST_DASHBOARD_ORIGIN;
let stage = "prerequisites";

class VerificationError extends Error {
  constructor(code, blocked = false) {
    super(code);
    this.blocked = blocked;
  }
}
const verify = (condition, code) => {
  if (!condition) throw new VerificationError(code);
};
const requireLive = (condition, code) => {
  if (!condition) throw new VerificationError(code, true);
};

try {
  requireLive(
    endpoint && origin && new URL(endpoint).hostname === "127.0.0.1"
      && new URL(origin).hostname === "127.0.0.1"
      && new URL(origin).protocol === "http:",
    "explicit_loopback_dashboard_required",
  );
  const browser = await chromium.connectOverCDP(endpoint);
  const page = browser.contexts()[0]?.pages()[0];
  requireLive(
    page && await page.evaluate(() => location.origin) === origin,
    "shared_authenticated_dashboard_required",
  );
  let mutations = 0;
  page.on("request", (request) => {
    const url = new URL(request.url());
    if (url.origin === origin && url.pathname.startsWith("/api/v1/")
        && !["GET", "HEAD"].includes(request.method())) mutations += 1;
  });

  stage = "actual_alert_api";
  const snapshot = await page.evaluate(async () => {
    const read = async (path) => {
      const response = await fetch(path);
      if (!response.ok) throw new Error("authenticated_alert_read_required");
      return response.json();
    };
    const notifications = await read("/api/v1/alert-notifications?limit=200");
    const counts = await read("/api/v1/alert-notifications/counts");
    const rules = await read("/api/v1/alert-rules?limit=200");
    const accounts = await read("/api/v1/accounts?limit=200");
    const histories = [];
    for (const item of notifications.items) {
      histories.push(await read(`/api/v1/alerts/${item.alert.alert_id}/history?limit=200`));
    }
    return { notifications, counts, rules, accounts, histories };
  });
  requireLive(snapshot.notifications.items.length > 0, "genuine_derived_alert_required");
  const accountIds = new Set(snapshot.accounts.items.map((item) => item.account_id));
  verify(snapshot.notifications.items.every(({ alert }) =>
    alert.account_id !== null && accountIds.has(alert.account_id)
      && typeof alert.source_event_id === "string" && alert.source_event_id.length >= 16
      && typeof alert.source_recorded_at === "string"
      && ["open", "recovered", "closed_by_configuration"].includes(alert.lifecycle)),
  "alert_source_lineage_incomplete");
  verify(snapshot.histories.every((history) => history.items.length > 0), "alert_history_missing");
  verify(snapshot.counts.visible_unread <= snapshot.notifications.items.length
    && snapshot.counts.total_unread >= snapshot.counts.visible_unread,
  "notification_count_mismatch");
  verify(snapshot.rules.availability.state === "available" && !snapshot.rules.page.has_more,
    "alert_rule_catalog_unavailable");
  verify(snapshot.notifications.items.some(({ alert }) =>
    alert.condition_type === "capacity_remaining"
      && Number.isInteger(alert.warning_remaining_basis_points)
      && Number.isInteger(alert.critical_remaining_basis_points)
      && alert.decision_reason_code === "quota_remaining"
      && ["warning", "critical"].includes(alert.severity)),
  "capacity_rule_resolution_missing");

  stage = "built_alert_console";
  await page.goto(origin);
  await page.getByRole("button", { name: "Alerts", exact: true }).click();
  await page.getByRole("heading", { name: "Alerts", exact: true }).waitFor({ timeout: 15_000 });
  const cards = page.locator(".alert-card");
  await cards.first().waitFor({ timeout: 15_000 });
  verify(await cards.count() === snapshot.notifications.items.length, "alert_card_count_mismatch");
  const first = cards.first();
  await first.getByText("Details and history", { exact: true }).click();
  await first.getByRole("heading", { name: "History", exact: true }).waitFor();
  await first.locator("ol li").first().waitFor({ timeout: 10_000 });
  verify(await first.getByRole("button", { name: "Open account", exact: true }).count() === 1,
    "alert_account_drilldown_missing");
  verify(await page.getByLabel("Alert counts", { exact: true }).count() === 1,
    "alert_counts_missing");

  stage = "built_rule_console";
  await page.locator(".alerts-page")
    .getByRole("button", { name: "Alert rules", exact: true }).click();
  await page.getByRole("heading", { name: "Alert rules", exact: true }).waitFor();
  await page.getByRole("button", { name: "Create rule", exact: true })
    .waitFor({ timeout: 15_000 });

  stage = "responsive_read_only";
  const priorViewport = await page.evaluate(() => ({ width: innerWidth, height: innerHeight }));
  for (const [width, height] of [[1280, 900], [390, 844]]) {
    await page.setViewportSize({ width, height });
    await page.evaluate(() => new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve))));
    verify(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1),
      "alert_console_overflow");
  }
  await page.setViewportSize(priorViewport);
  verify(mutations === 0, "alert_live_verifier_mutated_owner_state");
  console.log(JSON.stringify({
    status: "Passed", boundary: "genuine derived alerts and built browser",
    alerts: snapshot.notifications.items.length, histories: snapshot.histories.length,
  }));
  process.exit(0);
} catch (error) {
  const code = error instanceof VerificationError ? error.message : "alert_browser_verification_unavailable";
  const blocked = error instanceof VerificationError && error.blocked;
  console.error(`M4 ALERTS: ${blocked ? "BLOCKED" : "FAILED"} — ${stage}: ${code}`);
  process.exit(blocked ? 3 : 1);
}
