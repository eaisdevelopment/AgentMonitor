/** AC-LIVE-005: authenticated API, retained history, and built DOM quota facts. */

import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { chromium } from "../../frontend/node_modules/@playwright/test/index.mjs";

import {
  canonicalCodexHistoryMaterialV1,
  codexAdmissionV1,
  isExactServiceRevisionV1,
  isFreshCodexLineageV1,
  liveIdentityDigestV1,
} from "./m5_codex_policy.mjs";
import { readAllRegistryItemsV1 } from "./m5_registry_pages.mjs";

const endpoint = process.env.AGENTMONITOR_TEST_DASHBOARD_CDP_ENDPOINT;
const origin = process.env.AGENTMONITOR_TEST_DASHBOARD_ORIGIN;
const outcomesPath = process.env.AGENTMONITOR_TEST_M5_OWNER_OUTCOMES;
const revision = process.env.AGENTMONITOR_M5_IMPLEMENTATION_REVISION;
const servicePid = Number(process.env.AGENTMONITOR_M5_SERVICE_PID);
const serviceTicks = Number(process.env.AGENTMONITOR_M5_SERVICE_START_TIME_TICKS);

class VerificationError extends Error {}
const requireResult = (condition, reason) => {
  if (!condition) throw new VerificationError(reason);
};
const sha256 = value => createHash("sha256")
  .update(JSON.stringify(value)).digest("hex");
const exactPercent = field => {
  const value = field?.value;
  requireResult(field?.availability === "available"
    && value !== null && ["ratio", "percent"].includes(value?.unit)
    && typeof value?.coefficient === "string"
    && /^(?:0|[1-9][0-9]*)$/.test(value.coefficient)
    && Number.isInteger(value.scale) && value.scale >= 0 && value.scale <= 18,
  "codex_quota_value_invalid");
  const numerator = BigInt(value.coefficient)
    * (value.unit === "ratio" ? 100n : 1n);
  const denominator = 10n ** BigInt(value.scale);
  requireResult(numerator % denominator === 0n,
    "whole_percent_codex_quota_required");
  const percent = Number(numerator / denominator);
  requireResult(Number.isInteger(percent) && percent >= 0 && percent <= 100,
    "codex_quota_value_invalid");
  return percent;
};
const exactMetricText = field => {
  const value = field?.value;
  requireResult(field?.availability === "available" && value !== null,
    "codex_quota_value_invalid");
  if (value.scale === 0) return `${value.coefficient} ${value.unit}`;
  return value.scale > 0
    ? `${value.coefficient} × 10^-${value.scale} ${value.unit}`
    : `${value.coefficient} × 10^${Math.abs(value.scale)} ${value.unit}`;
};
const resetEpoch = value => value === null ? null : Math.floor(Date.parse(value) / 1000);
const apiValueMaterial = records => records.flatMap(record => record.windows.map(window => [
  record.account_id,
  window.window_key,
  window.semantic_role,
  window.remaining_percent,
  resetEpoch(window.reset_at),
  window.reset_precision,
])).sort();
const renderedValueMaterial = rows => rows.map(row => [
  row.account_id,
  row.window_key,
  row.semantic_role,
  row.remaining_percent,
  resetEpoch(row.reset_at),
  row.reset_precision,
]).sort();
const registryMaterial = async (read, accounts, organizations, installations) => {
  const codex = accounts.filter(item => item.provider_key === "codex");
  const details = await Promise.all(codex.map(async account => {
    const [connection, identity] = await Promise.all([
      read(`/api/v1/accounts/${encodeURIComponent(account.account_id)}/connection`),
      read(`/api/v1/accounts/${encodeURIComponent(account.account_id)}/provider-identity`),
    ]);
    return [
      account.account_id, account.provider_key, account.friendly_name,
      account.organization_id, account.lifecycle, account.monitoring_preference,
      account.is_effective_monitoring_enabled, account.identity_state,
      account.record_version, account.registry_revision,
      connection.state, connection.reason_code, connection.can_connect,
      connection.can_cancel, connection.attempt_id, connection.record_version,
      identity.state, identity.provider_key, identity.provider_version,
      identity.identity_source_id, identity.profile_protection,
      identity.collection_run_id,
      identity.email === null ? null : sha256(identity.email.normalize("NFKC").toLowerCase()),
      identity.provider_organization === null ? null
        : sha256(identity.provider_organization.normalize("NFKC")),
    ];
  }));
  return [
    ...organizations.map(item => [
      "organization", item.organization_id, item.name, item.description,
      item.display_order, item.lifecycle, item.record_version, item.registry_revision,
    ]),
    ...accounts.map(item => [
      "account", item.account_id, item.provider_key, item.friendly_name,
      item.organization_id, item.lifecycle, item.monitoring_preference,
      item.is_effective_monitoring_enabled, item.identity_state,
      item.record_version, item.registry_revision,
    ]),
    ...installations.map(item => [
      "installation", item.provider_installation_id, item.provider_key,
      item.platform_key, item.version?.state, item.version?.masked_value,
      item.presence_state, item.record_version, item.registry_revision,
    ]),
    ...details.map(item => ["codex-detail", ...item]),
  ].sort((left, right) => JSON.stringify(left).localeCompare(JSON.stringify(right)));
};

let page;
let exitCode = 0;
let stage = "selection";
try {
  requireResult(typeof endpoint === "string" && typeof origin === "string"
    && new URL(endpoint).hostname === "127.0.0.1"
    && new URL(origin).hostname === "127.0.0.1"
    && typeof outcomesPath === "string" && outcomesPath.endsWith("/m5-owner-outcomes.json")
    && typeof revision === "string" && /^[0-9a-f]{40}$/.test(revision)
    && Number.isSafeInteger(servicePid) && servicePid > 1
    && Number.isSafeInteger(serviceTicks) && serviceTicks > 0,
  "m5_quota_browser_selection_invalid");
  const ownerDocument = JSON.parse(readFileSync(outcomesPath, "utf8"));
  requireResult(Array.isArray(ownerDocument?.outcomes)
    && ownerDocument.outcomes.length === 4,
  "m5_quota_owner_outcomes_invalid");
  const verified = ownerDocument.outcomes.filter(row => row?.disposition === "verified");
  requireResult(verified.length > 0
    && new Set(verified.map(row => row.account_id)).size === verified.length,
  "m5_quota_verified_accounts_required");

  const browser = await chromium.connectOverCDP(endpoint);
  const context = browser.contexts()[0];
  requireResult(context, "shared_authenticated_dashboard_required");
  page = await context.newPage();
  let mutations = 0;
  page.on("request", request => {
    if (["POST", "PUT", "PATCH", "DELETE"].includes(request.method())) mutations += 1;
  });
  stage = "authenticated_api";
  await page.goto(origin);
  requireResult(new URL(page.url()).origin === origin,
    "shared_authenticated_dashboard_required");
  const read = path => page.evaluate(async pathValue => {
    const response = await fetch(pathValue, { credentials: "same-origin" });
    if (!response.ok) throw new Error("authenticated_versioned_read_required");
    return response.json();
  }, path);
  const [baseRegistry, versions] = await Promise.all([
    Promise.all([
      readAllRegistryItemsV1(read, "/api/v1/accounts"),
      readAllRegistryItemsV1(read, "/api/v1/organizations"),
      readAllRegistryItemsV1(read, "/api/v1/provider-installations?provider_key=codex"),
    ]),
    read("/api/v1/operations/versions"),
  ]);
  requireResult(isExactServiceRevisionV1(versions, revision),
    "m5_quota_service_revision_mismatch");
  const registryBefore = sha256(await registryMaterial(read, ...baseRegistry));
  const accounts = new Map(baseRegistry[0].map(item => [item.account_id, item]));

  stage = "current_codex_lineage";
  const now = new Date();
  const from = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);
  const records = [];
  const identityKeys = [];
  for (const outcome of verified) {
    const account = accounts.get(outcome.account_id);
    requireResult(account?.provider_key === "codex" && account.lifecycle === "active"
      && account.is_effective_monitoring_enabled,
    "m5_quota_account_not_current");
    const id = encodeURIComponent(outcome.account_id);
    const [identity, capacity, history, runs] = await Promise.all([
      read(`/api/v1/accounts/${id}/provider-identity`),
      read(`/api/v1/accounts/${id}/capacity`),
      read(`/api/v1/capacity/history?${new URLSearchParams({
        subject_id: outcome.account_id, metric: "remaining_ratio",
        series_kind: "poll_snapshot", from: from.toISOString(),
        before: now.toISOString(), limit: "200",
      })}`),
      read(`/api/v1/collection-runs?${new URLSearchParams({
        provider_key: "codex", account_id: outcome.account_id, limit: "200",
      })}`),
    ]);
    const windows = capacity.items.flatMap(item => item.windows);
    const run = runs.items.find(item => item.run_id === identity.collection_run_id);
    requireResult(isFreshCodexLineageV1({
      accountId: outcome.account_id, identity, run, windows, history,
    }, "1970-01-01T00:00:00Z"), "m5_quota_current_lineage_required");
    requireResult(typeof identity.email === "string" && identity.email.length > 0,
      "m5_quota_verified_identity_required");
    identityKeys.push(liveIdentityDigestV1(identity));
    const normalizedWindows = windows.map(window => {
      const quotaField = window.allowance?.remaining_percentage ?? window.remaining_ratio;
      requireResult(typeof window.semantic_role === "string"
        && window.semantic_role.length > 0
        && ["exact", "rounded", "range", "estimated", "unknown"]
          .includes(window.reset_precision)
        && (window.reset_at === null) === (window.reset_precision === "unknown")
        && (window.reset_at === null || Number.isFinite(Date.parse(window.reset_at))),
      "m5_quota_window_contract_invalid");
      return {
        window_key: window.window_key,
        semantic_role: window.semantic_role,
        remaining_percent: exactPercent(quotaField),
        history_value_text: exactMetricText(window.remaining_ratio),
        reset_at: window.reset_at,
        reset_precision: window.reset_precision,
        current_observation_id: window.current_observation_id,
      };
    });
    records.push({
      account_id: outcome.account_id,
      alias: outcome.alias,
      collection_run_id: run.run_id,
      collected_at: run.completed_at,
      windows: normalizedWindows,
    });
  }
  requireResult(new Set(identityKeys).size === verified.length,
    "m5_quota_distinct_identities_required");

  stage = "built_quota_and_history";
  const rendered = [];
  const historyRendered = [];
  for (const record of records) {
    await page.goto(`${origin}/accounts/${encodeURIComponent(record.account_id)}`);
    await page.getByRole("table", { name: "Account activity", exact: true })
      .waitFor({ timeout: 15_000 });
    const allowanceRows = page.locator(
      ".usage-allowance .allowance-card[data-window-key]",
    );
    await allowanceRows.first().waitFor({ timeout: 15_000 });
    const rows = await allowanceRows.evaluateAll(items =>
      items.map(item => ({
        window_key: item.getAttribute("data-window-key"),
        semantic_role: item.getAttribute("data-semantic-role"),
        remaining_text: item.querySelector("strong")?.textContent?.trim() ?? "",
        reset_at: item.querySelector(".quota-reset time")?.getAttribute("datetime") ?? null,
        reset_precision: item.querySelector(".quota-reset")
          ?.getAttribute("data-reset-precision") ?? null,
      })));
    requireResult(rows.length === record.windows.length,
      "m5_quota_rendered_window_count_mismatch");
    for (const window of record.windows) {
      const matches = rows.filter(row => row.window_key === window.window_key);
      requireResult(matches.length === 1
        && matches[0].semantic_role === window.semantic_role
        && matches[0].remaining_text === `${window.remaining_percent}%`
        && matches[0].reset_at === window.reset_at
        && matches[0].reset_precision === window.reset_precision,
      "m5_quota_rendered_value_mismatch");
      rendered.push({ account_id: record.account_id, ...matches[0],
        remaining_percent: window.remaining_percent });
    }
    const historyDetails = page.locator("details.quota-history");
    await historyDetails.locator("summary").evaluate(element => element.click());
    const chart = page.getByRole("img", { name: "Capacity history trend", exact: true });
    await chart.waitFor({ timeout: 15_000 });
    const chartIds = new Set(((await chart.getAttribute("data-observation-ids")) ?? "")
      .split(" ").filter(Boolean));
    for (const window of record.windows) {
      requireResult(chartIds.has(window.current_observation_id),
        "m5_quota_current_history_point_not_charted");
      const row = page.locator('table[aria-label="Capacity history exact values"] tbody tr')
        .filter({ hasText: window.current_observation_id });
      const resetTime = row.locator(".quota-reset time");
      requireResult(await row.count() === 1
        && await row.getAttribute("data-window-key") === window.window_key
        && await row.getAttribute("data-semantic-role") === window.semantic_role
        && await row.locator(".history-exact-value")
          .getByText(window.history_value_text, { exact: false }).count() === 1
        && await row.locator(".quota-reset").getAttribute("data-reset-precision")
          === window.reset_precision
        && (await resetTime.count() === 0 ? null : await resetTime.getAttribute("datetime"))
          === window.reset_at,
      "m5_quota_current_history_value_not_rendered");
      historyRendered.push([
        record.account_id, window.window_key, window.semantic_role,
        window.remaining_percent, resetEpoch(window.reset_at), window.reset_precision,
        window.current_observation_id,
      ]);
    }
  }

  stage = "unchanged_registry";
  const finalRegistry = await Promise.all([
    readAllRegistryItemsV1(read, "/api/v1/accounts"),
    readAllRegistryItemsV1(read, "/api/v1/organizations"),
    readAllRegistryItemsV1(read, "/api/v1/provider-installations?provider_key=codex"),
  ]);
  const registryAfter = sha256(await registryMaterial(read, ...finalRegistry));
  requireResult(registryAfter === registryBefore && mutations === 0,
    "m5_quota_browser_mutated_registry");
  const privateRecords = records.map(record => ({
    account_id: record.account_id,
    alias: record.alias,
    collection_run_id: record.collection_run_id,
    collected_at: record.collected_at,
    windows: record.windows.map(({ history_value_text: _ignoredText, ...window }) =>
      window),
  }));
  const proof = {
    schema: "agentmonitor.m5-quota-browser-proof.v1",
    implementation_revision: revision,
    service_source_revision: revision,
    service_pid: servicePid,
    service_start_time_ticks: serviceTicks,
    captured_at: new Date().toISOString(),
    account_count: records.length,
    window_count: records.reduce((total, record) => total + record.windows.length, 0),
    provider_version: codexAdmissionV1.provider_version,
    source_id: codexAdmissionV1.rate_limits_source_id,
    identity_set_digest: sha256([...identityKeys].sort()),
    collection_run_set_digest: sha256(records.map(record => [
      record.account_id, record.collection_run_id,
    ]).sort()),
    quota_value_set_digest: sha256(apiValueMaterial(records)),
    rendered_value_set_digest: sha256(renderedValueMaterial(rendered)),
    history_value_set_digest: sha256(
      canonicalCodexHistoryMaterialV1(historyRendered),
    ),
    registry_digest_before: registryBefore,
    registry_digest_after: registryAfter,
    mutations,
    records: privateRecords,
  };
  console.log(JSON.stringify(proof));
  console.log(`M5 CODEX QUOTA BROWSER: PASSED — ${proof.account_count} account(s), ${proof.window_count} window(s), exact API/history/DOM values`);
} catch (error) {
  const reason = error instanceof VerificationError
    && /^[a-z0-9_]+$/.test(error.message)
    ? error.message : "m5_quota_browser_unavailable";
  console.error(`M5 CODEX QUOTA BROWSER: BLOCKED — ${stage}: ${reason}`);
  exitCode = 3;
} finally {
  if (page) await page.close();
}
process.exit(exitCode);
