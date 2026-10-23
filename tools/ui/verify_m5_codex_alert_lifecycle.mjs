/** Read-only browser proof for one genuine recovered Codex capacity alert. */
import { createHash } from "node:crypto";
import { chromium } from "../../frontend/node_modules/@playwright/test/index.mjs";

import {
  isExactServiceRevisionV1,
  publicRegistryDigestV1,
} from "./m5_codex_policy.mjs";
import {
  readAllAlertHistoryV1,
  readAllRegistryItemsV1,
} from "./m5_registry_pages.mjs";

const endpoint = process.env.AGENTMONITOR_TEST_DASHBOARD_CDP_ENDPOINT;
const origin = process.env.AGENTMONITOR_TEST_DASHBOARD_ORIGIN;
const revision = process.env.AGENTMONITOR_M5_IMPLEMENTATION_REVISION;
const servicePid = Number(process.env.AGENTMONITOR_M5_SERVICE_PID);
const serviceStart = Number(process.env.AGENTMONITOR_M5_SERVICE_START_TIME_TICKS);
const accountId = process.env.AGENTMONITOR_TEST_CODEX_ACCOUNT_ID;
const alertId = process.env.AGENTMONITOR_TEST_M5_ALERT_ID;
let browser;
let page;
let stage = "prerequisites";

const requireResult = (condition, reason) => {
  if (!condition) throw new Error(reason);
};
const canonicalJson = value => {
  if (Array.isArray(value)) return `[${value.map(canonicalJson).join(",")}]`;
  if (value !== null && typeof value === "object") {
    return `{${Object.keys(value).sort().map(key =>
      `${JSON.stringify(key)}:${canonicalJson(value[key])}`).join(",")}}`;
  }
  return JSON.stringify(value);
};
const sha256 = value => createHash("sha256")
  .update(canonicalJson(value))
  .digest("hex");
const historyMaterial = items => items.map(item => [
  item.event_id,
  item.alert_id,
  item.aggregate_sequence,
  item.transition,
  new Date(item.occurred_at).toISOString(),
  item.previous_lifecycle,
  item.current_lifecycle,
  item.previous_severity,
  item.current_severity,
  item.reason_code,
  item.source_event_id,
]);
try {
  requireResult(endpoint && origin && revision && accountId && alertId,
    "explicit_alert_witness_selection_required");
  requireResult(new URL(endpoint).hostname === "127.0.0.1"
    && new URL(origin).hostname === "127.0.0.1"
    && new URL(origin).protocol === "http:"
    && /^[0-9a-f]{40}$/.test(revision)
    && Number.isInteger(servicePid) && servicePid > 0
    && Number.isInteger(serviceStart) && serviceStart > 0
    && /^[A-Za-z0-9_-]{1,128}$/.test(accountId)
    && /^[A-Za-z0-9_-]{1,128}$/.test(alertId),
  "alert_witness_selection_invalid");

  browser = await chromium.connectOverCDP(endpoint);
  const context = browser.contexts()[0];
  requireResult(context, "shared_owner_browser_required");
  page = await context.newPage();
  let mutations = 0;
  page.on("request", request => {
    const url = new URL(request.url());
    if (url.origin === origin && !["GET", "HEAD"].includes(request.method())) {
      mutations += 1;
    }
  });
  await page.goto(origin);
  requireResult(await page.evaluate(() => location.origin) === origin,
    "shared_authenticated_dashboard_required");
  const read = async path => page.evaluate(async selected => {
    const response = await fetch(selected, { credentials: "same-origin" });
    if (!response.ok) throw new Error("authenticated_versioned_read_required");
    return response.json();
  }, path);
  const registry = async () => {
    const [accounts, organizations, installations] = await Promise.all([
      readAllRegistryItemsV1(read, "/api/v1/accounts"),
      readAllRegistryItemsV1(read, "/api/v1/organizations"),
      readAllRegistryItemsV1(read, "/api/v1/provider-installations"),
    ]);
    const records = {
      accounts,
      organizations,
      installations,
    };
    return { accounts, digest: publicRegistryDigestV1(records) };
  };

  stage = "persisted_lifecycle";
  const before = await registry();
  const notifications = await read("/api/v1/alert-notifications?limit=200");
  const targetIndex = notifications.items.findIndex(item =>
    item.alert.alert_id === alertId);
  requireResult(targetIndex >= 0 && !notifications.page.has_more,
    "selected_alert_not_in_notification_page");
  const target = notifications.items[targetIndex].alert;
  requireResult(target.account_id === accountId && target.provider_key === "codex"
    && target.condition_type === "capacity_remaining"
    && target.lifecycle === "recovered" && target.recovered_at !== null
    && Number.isInteger(target.record_version) && target.record_version > 0,
  "selected_codex_alert_not_recovered");
  const history = await readAllAlertHistoryV1(read, alertId);
  requireResult(history.availability.state === "available"
    && history.items.some(item => ["opened", "reopened"].includes(item.transition))
    && history.items.some(item => item.transition === "repeated")
    && history.items.some(item => ["acknowledged", "snoozed"].includes(item.transition))
    && history.items.some(item => item.transition === "recovered"),
  "selected_codex_alert_history_incomplete");

  stage = "built_alert_console";
  await page.goto(origin);
  await page.getByRole("button", { name: "Alerts", exact: true }).click();
  await page.getByRole("heading", { name: "Alerts", exact: true })
    .waitFor({ timeout: 15_000 });
  const cards = page.locator(".alert-card");
  await cards.first().waitFor({ timeout: 15_000 });
  while (await cards.count() <= targetIndex) {
    const more = page.getByRole("button", { name: "Load more alerts", exact: true });
    requireResult(await more.count() === 1, "selected_alert_not_rendered");
    await more.click();
    await page.waitForTimeout(100);
  }
  const account = before.accounts.find(item => item.account_id === accountId);
  requireResult(account?.provider_key === "codex", "selected_codex_account_missing");
  const card = cards.nth(targetIndex);
  requireResult((await card.textContent()).includes(account.friendly_name)
    && (await card.textContent()).includes("recovered"),
  "selected_alert_not_rendered");
  await card.getByText("Details and history", { exact: true }).click();
  const renderedHistory = card.locator("ol li");
  await renderedHistory.first().waitFor({ timeout: 15_000 });
  let historyClicks = 0;
  while (await renderedHistory.count() < history.items.length) {
    requireResult(historyClicks < 199, "selected_alert_history_not_rendered");
    const moreHistory = card.getByRole("button", {
      name: "Load more history",
      exact: true,
    });
    requireResult(await moreHistory.count() === 1,
      "selected_alert_history_not_rendered");
    const previousCount = await renderedHistory.count();
    const [response] = await Promise.all([
      page.waitForResponse(candidate => {
        const url = new URL(candidate.url());
        return url.origin === origin
          && url.pathname === `/api/v1/alerts/${encodeURIComponent(alertId)}/history`
          && candidate.request().method() === "GET";
      }),
      moreHistory.click(),
    ]);
    requireResult(response.ok(), "selected_alert_history_not_rendered");
    await page.waitForFunction(
      ({ selectedAlertId, count }) => {
        const cardElement = [...document.querySelectorAll(".alert-card")]
          .find(candidate => candidate.querySelector(
            `li[data-alert-id="${CSS.escape(selectedAlertId)}"]`,
          ));
        return cardElement !== undefined
          && cardElement.querySelectorAll("ol li").length > count;
      },
      { selectedAlertId: alertId, count: previousCount },
      { timeout: 15_000 },
    );
    historyClicks += 1;
  }
  requireResult(await renderedHistory.count() === history.items.length,
    "selected_alert_history_not_rendered");
  requireResult(await card.getByRole("button", {
    name: "Load more history",
    exact: true,
  }).count() === 0, "selected_alert_history_not_rendered");
  const renderedItems = await renderedHistory.evaluateAll(elements => elements.map(element => ({
    event_id: element.dataset.eventId,
    alert_id: element.dataset.alertId,
    aggregate_sequence: Number(element.dataset.aggregateSequence),
    transition: element.dataset.transition,
    occurred_at: element.dataset.occurredAt,
    previous_lifecycle: element.dataset.previousLifecycle || null,
    current_lifecycle: element.dataset.currentLifecycle,
    previous_severity: element.dataset.previousSeverity || null,
    current_severity: element.dataset.currentSeverity,
    reason_code: element.dataset.reasonCode,
    source_event_id: element.dataset.sourceEventId || null,
  })));
  requireResult(renderedItems.every((item, index) =>
    item.event_id === history.items[index].event_id
      && item.alert_id === alertId
      && item.aggregate_sequence === history.items[index].aggregate_sequence),
  "selected_alert_history_not_rendered");
  const expectedHistoryDigest = sha256(historyMaterial(history.items));
  requireResult(sha256(historyMaterial(renderedItems)) === expectedHistoryDigest,
    "selected_alert_history_not_rendered");

  stage = "service_revision";
  const [liveness, versions] = await Promise.all([
    read("/api/v1/operations/liveness"),
    read("/api/v1/operations/versions"),
  ]);
  requireResult(isExactServiceRevisionV1(versions, revision),
    "alert_service_revision_mismatch");
  stage = "service_freshness";
  const serviceCheckedAt = new Date(liveness.checked_at);
  const recoveredAt = new Date(target.recovered_at);
  const presentedAt = new Date();
  requireResult(liveness.state === "healthy"
    && Number.isFinite(serviceCheckedAt.getTime())
    && Number.isFinite(recoveredAt.getTime())
    && serviceCheckedAt >= recoveredAt
    && serviceCheckedAt <= presentedAt
    && presentedAt.getTime() - serviceCheckedAt.getTime() <= 120_000
    && versions.availability?.state === "available",
  "alert_service_freshness_invalid");

  stage = "registry_recheck";
  const after = await registry();
  requireResult(before.digest === after.digest && mutations === 0,
    "alert_browser_proof_mutated_state");
  console.log(JSON.stringify({
    schema: "agentmonitor.m5-alert-browser-proof.v2",
    implementation_revision: revision,
    service_source_revision: versions.source_revision.value,
    service_pid: servicePid,
    service_start_time_ticks: serviceStart,
    account_id: accountId,
    alert_id: alertId,
    presented_at: presentedAt.toISOString(),
    browser_presented: true,
    alert_record_version: target.record_version,
    history_digest: expectedHistoryDigest,
    service_checked_at: serviceCheckedAt.toISOString(),
    service_versions_digest: sha256(versions),
    registry_digest_scope: "all-public-registry-fields-v1",
    registry_digest_before: before.digest,
    registry_digest_after: after.digest,
    mutations,
  }));
} catch (error) {
  const reason = error instanceof Error && /^[a-z0-9_]+$/.test(error.message)
    ? error.message : "codex_alert_browser_unavailable";
  console.error(`M5 CODEX ALERT: BLOCKED — ${stage}: ${reason}`);
  process.exitCode = 3;
} finally {
  let cleanupFailed = false;
  if (page) {
    try {
      await page.close();
    } catch {
      cleanupFailed = true;
    }
  }
  if (browser) {
    try {
      await browser.close();
    } catch {
      cleanupFailed = true;
    }
  }
  if (cleanupFailed) {
    console.error(
      "M5 CODEX ALERT: BLOCKED — cleanup: codex_alert_browser_cleanup_failed",
    );
    process.exitCode = 3;
  }
}
