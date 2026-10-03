/** ST-FLEET-002/003: owner-selected real fleet through authenticated V1 and built UI. */
import { readFile, stat } from "node:fs/promises";
import { chromium } from "../../frontend/node_modules/@playwright/test/index.mjs";
import {
  buildFleetWitnessV1,
  isFreshCollectionLineageV1,
} from "./m4_fleet_policy.mjs";

const endpoint = process.env.AGENTMONITOR_TEST_DASHBOARD_CDP_ENDPOINT;
const origin = process.env.AGENTMONITOR_TEST_DASHBOARD_ORIGIN;
const outcomesPath = process.env.AGENTMONITOR_TEST_M4_OWNER_OUTCOMES;
const preflightOnly = process.env.AGENTMONITOR_M4_PREFLIGHT_ONLY === "1";
const serviceStartedAt = process.env.AGENTMONITOR_M4_SERVICE_STARTED_AT;
let stage = "prerequisites";
let page;
let exitCode = 0;
const requireResult = (condition, reason) => { if (!condition) throw new Error(reason); };
const opaque = value => typeof value === "string" && /^[A-Za-z0-9_-]{1,64}$/.test(value);

try {
  requireResult(endpoint && origin && outcomesPath, "explicit_owner_fleet_selection_required");
  requireResult(preflightOnly || (typeof serviceStartedAt === "string" && /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$/.test(serviceStartedAt)), "service_restart_time_required");
  requireResult(new URL(endpoint).hostname === "127.0.0.1" && new URL(origin).hostname === "127.0.0.1" && new URL(origin).protocol === "http:", "loopback_dashboard_required");
  requireResult(outcomesPath.startsWith("/"), "private_owner_outcomes_path_required");
  const file = await stat(outcomesPath);
  requireResult(file.isFile() && (file.mode & 0o077) === 0 && file.size > 2 && file.size <= 8192, "private_owner_outcomes_file_required");
  const manifest = JSON.parse(await readFile(outcomesPath, "utf8"));
  requireResult(manifest && Object.keys(manifest).sort().join(",") === "outcomes,schema" && manifest.schema === "agentmonitor.m4-owner-outcomes.v1" && Array.isArray(manifest.outcomes) && manifest.outcomes.length === 6, "six_owner_outcomes_required");
  requireResult(manifest.outcomes.every(row => row && Object.keys(row).sort().join(",") === "account_id,disposition,organization_id" && opaque(row.account_id) && opaque(row.organization_id) && ["verified", "owner_unavailable"].includes(row.disposition)), "owner_outcomes_schema_invalid");
  requireResult(new Set(manifest.outcomes.map(row => row.account_id)).size === 6 && new Set(manifest.outcomes.map(row => row.organization_id)).size === 2, "owner_outcomes_membership_invalid");
  requireResult(manifest.outcomes.every(row => row.disposition === "verified"), "owner_unavailable_blocks_full_fleet");
  const browser = await chromium.connectOverCDP(endpoint);
  const context = browser.contexts()[0];
  requireResult(context, "shared_owner_browser_required");
  page = await context.newPage();
  let mutations = 0;
  page.on("request", request => {
    if (new URL(request.url()).origin === origin && request.url().includes("/api/v1/") && !["GET", "HEAD"].includes(request.method())) mutations += 1;
  });
  await page.goto(origin);
  const read = async path => page.evaluate(async selectedPath => {
    const response = await fetch(selectedPath, { credentials: "same-origin" });
    if (!response.ok) throw new Error("authenticated_versioned_read_required");
    return response.json();
  }, path);
  stage = "authenticated_fleet_lineage";
  const [accounts, organizations, locations] = await Promise.all([
    read("/api/v1/accounts?limit=200"),
    read("/api/v1/organizations?limit=200"),
    read("/api/v1/process-locations"),
  ]);
  requireResult(!accounts.page.has_more && !organizations.page.has_more, "bounded_registry_page_incomplete");
  const selectRegistryRecords = (accountPage, organizationPage) => {
    requireResult(!accountPage.page.has_more && !organizationPage.page.has_more, "bounded_registry_page_incomplete");
    const accountById = new Map(accountPage.items.map(item => [item.account_id, item]));
    const organizationById = new Map(organizationPage.items.filter(item => item.lifecycle === "active").map(item => [item.organization_id, item]));
    return manifest.outcomes.map(outcome => {
      const account = accountById.get(outcome.account_id);
      const organization = organizationById.get(outcome.organization_id);
      requireResult(account?.provider_key === "claude" && account.organization_id === outcome.organization_id && organization, "fleet_membership_mismatch");
      requireResult(account.lifecycle === "active" && account.is_effective_monitoring_enabled && ["matched", "owner_confirmed"].includes(account.identity_state), "fleet_account_not_monitoring");
      return { outcome, account, organization };
    });
  };
  let selectedAccounts = selectRegistryRecords(accounts, organizations);
  const inspectAccount = async ({ outcome, account, organization }) => {
    const before = new Date();
    const from = new Date(before.getTime() - 60 * 60 * 1000);
    const id = encodeURIComponent(outcome.account_id);
    const [identity, capacity, history, sessions, runs] = await Promise.all([
      read(`/api/v1/accounts/${id}/observed-identity`),
      read(`/api/v1/accounts/${id}/capacity`),
      read(`/api/v1/capacity/history?${new URLSearchParams({ subject_id: outcome.account_id, metric: "remaining_ratio", series_kind: "poll_snapshot", from: from.toISOString(), before: before.toISOString(), limit: "200" })}`),
      read(`/api/v1/sessions?${new URLSearchParams({ provider_key: "claude", account_id: outcome.account_id, limit: "200" })}`),
      read(`/api/v1/collection-runs?${new URLSearchParams({ provider_key: "claude", account_id: outcome.account_id, limit: "200" })}`),
    ]);
    requireResult(["available", "partial"].includes(sessions.availability.state) && sessions.items.every(item => item.account_id === outcome.account_id), "fleet_session_scope_mismatch");
    const identityReady = identity.state === "verified"
      && identity.account_id === outcome.account_id
      && typeof identity.email === "string" && identity.email.length > 0
      && typeof identity.collection_run_id === "string" && identity.collection_run_id.length > 0;
    if (!identityReady) {
      requireResult(!preflightOnly, "fleet_identity_not_current");
      return {
        outcome, account, organization, identity, windows: [], sessions,
        pending: true, currentLineage: false, validHistory: false,
        currentHistoryMatched: false, freshAfterRestart: false,
      };
    }
    const windows = capacity.items.flatMap(item => item.windows);
    const currentLineage = capacity.availability.state === "available" && windows.length > 0 && windows.every(window => window.subject?.account_id === outcome.account_id && window.freshness === "fresh" && window.collection_run_id === identity.collection_run_id && window.current_observation_id && window.provenance?.source_id === "claude.usage.ax-screen-reader.v1");
    const validHistory = history.availability.state === "available" && history.items.length > 0 && history.items.every(point => point.subject.account_id === outcome.account_id && point.collection_run_id && point.provenance?.source_id);
    const currentHistoryMatched = validHistory && history.items.some(point => point.collection_run_id === identity.collection_run_id && windows.some(window => window.current_observation_id === point.observation_id));
    const run = runs.items.find(item => item.run_id === identity.collection_run_id);
    const freshAfterRestart = !preflightOnly && isFreshCollectionLineageV1({
      accountId: outcome.account_id, identity, run, windows, history,
    }, serviceStartedAt);
    return {
      outcome, account, organization, identity, windows, sessions,
      pending: false, currentLineage, validHistory, currentHistoryMatched,
      freshAfterRestart,
    };
  };
  const witnessRecords = items => items.map(item => ({
    accountId: item.account.account_id,
    organizationId: item.account.organization_id,
    administratorName: item.account.friendly_name,
    observedEmail: item.identity.email,
    providerOrganization: item.identity.provider_organization,
    collectionRunId: item.identity.collection_run_id,
    currentHistoryMatched: item.currentHistoryMatched,
    freshAfterRestart: item.freshAfterRestart,
    providerKey: item.account.provider_key,
    lifecycle: item.account.lifecycle,
    monitoringPreference: item.account.monitoring_preference,
    effectiveMonitoringEnabled: item.account.is_effective_monitoring_enabled,
    effectiveMonitoringReason: item.account.effective_monitoring_reason,
    identityState: item.account.identity_state,
    accountRecordVersion: item.account.record_version,
    accountRegistryRevision: item.account.registry_revision,
    organizationRecordVersion: item.organization.record_version,
    organizationRegistryRevision: item.organization.registry_revision,
  }));
  let selected;
  const freshnessDeadline = Date.now() + (preflightOnly ? 360_000 : 420_000);
  while (true) {
    selected = await Promise.all(selectedAccounts.map(inspectAccount));
    const allIdentitiesReady = selected.every(item => !item.pending);
    if (allIdentitiesReady) {
      buildFleetWitnessV1(witnessRecords(selected), {
        event: "m4_fleet_preflight",
      });
    }
    const ready = allIdentitiesReady && selected.every(item => item.currentLineage && item.validHistory && item.currentHistoryMatched
      && (preflightOnly || item.freshAfterRestart));
    if (ready) break;
    requireResult(Date.now() < freshnessDeadline, preflightOnly ? "fleet_quota_identity_lineage_mismatch" : "fresh_post_restart_fleet_collection_required");
    await new Promise(resolve => setTimeout(resolve, 10_000));
  }
  const [finalAccounts, finalOrganizations] = await Promise.all([
    read("/api/v1/accounts?limit=200"),
    read("/api/v1/organizations?limit=200"),
  ]);
  selectedAccounts = selectRegistryRecords(finalAccounts, finalOrganizations);
  const finalRegistryByAccount = new Map(selectedAccounts.map(item => [item.outcome.account_id, item]));
  selected = selected.map(item => {
    const current = finalRegistryByAccount.get(item.outcome.account_id);
    requireResult(current, "fleet_membership_mismatch");
    return { ...item, account: current.account, organization: current.organization };
  });
  const observedSessions = selected.reduce((total, item) => total + item.sessions.items.length, 0);
  requireResult(observedSessions > 0, "real_claude_sessions_required");
  const witness = buildFleetWitnessV1(witnessRecords(selected), {
    event: preflightOnly ? "m4_fleet_preflight" : "m4_fleet_witness",
  });
  if (!preflightOnly) {
    stage = "built_fleet_overview";
    await page.goto(origin);
    const overview = page.getByRole("table", { name: "Account quota overview", exact: true });
    await overview.waitFor({ timeout: 15_000 });
    const filters = page.getByRole("group", { name: "Organizations", exact: true });
    requireResult(await filters.count() === 1 && await filters.getByRole("button", { name: "All organizations", exact: true }).getAttribute("aria-pressed") === "true", "fleet_organization_controls_missing");
    for (const item of selected) {
      const primary = overview.locator(`tbody tr[data-account-id="${item.account.account_id}"]`);
      const additional = overview.getByRole("button", { name: `Review ${item.account.friendly_name} connection`, exact: true });
      requireResult(await primary.count() === 1 || await additional.count() === 1, "fleet_connection_hidden");
    }
    stage = "built_account_activity";
    for (const item of selected) {
      await page.goto(`${origin}/accounts/${encodeURIComponent(item.account.account_id)}`);
      const activity = page.getByRole("table", { name: "Account activity", exact: true });
      await activity.waitFor({ timeout: 15_000 });
      const row = activity.locator("tbody tr");
      await row.locator(".workspace-account-name").getByText(item.identity.email, { exact: true }).waitFor({ timeout: 15_000 });
      await row.locator(".workspace-reading").first().waitFor({ timeout: 15_000 });
      requireResult(await row.count() === 1, "fleet_account_identity_not_displayed");
      requireResult((await row.locator('[data-label="State"]').textContent()).includes("Monitoring on"), "fleet_account_monitoring_state_missing");
      requireResult(await row.locator(".workspace-reading").count() > 0, "fleet_account_quota_missing");
      const linked = locations.availability.state === "available" ? locations.items.filter(process => process.account_association?.account_id === item.account.account_id && process.working_directory !== null) : [];
      const pathCell = row.locator('[data-label="Path"]');
      if (linked.length === 0) requireResult((await pathCell.textContent()).includes("Not reported"), "unlinked_path_not_explicit");
      else for (const process of linked) await pathCell.getByText(process.working_directory, { exact: true }).waitFor({ timeout: 15_000 });
    }
    stage = "built_runtime_view";
    await page.goto(`${origin}/sessions`);
    await page.locator(".session-row").first().waitFor({ timeout: 15_000 });
    requireResult(await page.getByRole("heading", { name: "Sessions", exact: true }).count() === 1, "fleet_runtime_view_missing");
  }
  requireResult(mutations === 0, "fleet_read_verification_mutated_owner_state");
  console.log(JSON.stringify({ ...witness, mutations }));
  console.log(`M4 FLEET: PASSED — six distinct administrator-matched real Claude identities, two organizations, verified ${preflightOnly ? "current" : "fresh post-restart"} quota lineage, retained history, runtime scope${preflightOnly ? "" : ", authenticated API and built account activity"}`);
} catch (error) {
  const reason = error instanceof Error && /^[a-z0-9_]+$/.test(error.message) ? error.message : "fleet_verification_unavailable";
  console.error(`M4 FLEET: BLOCKED — ${stage}: ${reason}`);
  exitCode = 3;
} finally {
  if (page) await page.close();
}
process.exit(exitCode);
