/** Read the already open official Usage credit card and one owner-selected account.
 * No provider requests/navigation, keys, requests table, billing or settings writes.
 */
import { chromium } from '@playwright/test';
import { createHash } from 'node:crypto';
import { compareCreditView, parseCreditView } from './authoritative_credit_policy.mjs';

const revision = process.argv[2];
const origin = 'http://127.0.0.1:43110';
const began = new Date();
const deadline = Date.now() + 60_000;
const empty = createHash('sha256').digest('hex');
const result = {
  record_type: 'agentmonitor.m6_authoritative_comparison.v1', schema_version: '1.0.0',
  pairing_provenance: 'owner_asserted_visible_principal',
  status: 'not_run', reason_code: 'official_usage_pairing_unproven', source_revision: revision,
  compared_targets: 0, current_balance_lineage_sha256: empty, comparison_sha256: empty,
  started_at: began.toISOString(), completed_at: began.toISOString(),
  provider_observed_at: null, source_observed_at: null,
};
let browser;
let disposable;
function fail(reason) { throw new Error(reason); }
function timeout() {
  const remaining = deadline - Date.now();
  if (remaining < 1) fail('official_usage_observation_timeout');
  return Math.min(5000, remaining);
}
function digest(value) { return createHash('sha256').update(JSON.stringify(value)).digest('hex'); }
function lineage(account, quotas) {
  const rows = quotas.items.map(item => [account.account_id, item.subject.resource_id,
    item.subject.provider_target_id, item.window_id, item.current_observation_id, item.collection_run_id].join('\0'));
  return createHash('sha256').update([...new Set(rows)].sort().map(row => row + '\n').join('')).digest('hex');
}
async function localJson(path) {
  const response = await disposable.request.get(origin + path, { headers: { Origin: origin }, timeout: timeout(), failOnStatusCode: false });
  if (response.status() !== 200) fail('official_usage_dashboard_unavailable');
  return response.json();
}
async function currentRevision() {
  const value = await localJson('/api/v1/operations/versions');
  if (value?.source_revision?.availability !== 'available' || value.source_revision.source !== 'build_manifest'
      || value.source_revision.value !== revision) fail('official_usage_revision_mismatch');
}
function providerUrl(page) {
  try { const url = new URL(page.url()); return url.origin === 'https://ollama.com' && url.pathname === '/settings'; }
  catch { return false; }
}
async function officialView(page) {
  if (!providerUrl(page)) fail('official_usage_pairing_unproven');
  const identity = page.locator('aside summary');
  if (await identity.count() !== 1 || !await identity.isVisible()) fail('official_usage_pairing_unproven');
  let principalText = await identity.innerText({ timeout: timeout() });
  // On narrow windows the selected identity is visible in the account menu,
  // not in the avatar-only summary. Open only this menu and restore its state.
  if (!principalText.includes('@')) {
    const details = identity.locator('xpath=..');
    const wasOpen = await details.evaluate(element => element.open === true);
    try {
      if (!wasOpen) await identity.click({ timeout: timeout() });
      const header = details.locator(':scope > div > div').first();
      if (!await header.isVisible()) fail('official_usage_pairing_unproven');
      principalText = await header.innerText({ timeout: timeout() });
    } finally {
      if (!wasOpen) await identity.click({ timeout: timeout() });
    }
  }
  if (principalText.length > 512) fail('official_usage_pairing_unproven');
  const emails = principalText.match(/[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/gi) ?? [];
  if (emails.length !== 1) fail('official_usage_pairing_unproven');
  const button = page.getByRole('button', { name: 'Usage credits breakdown', exact: true });
  await button.hover({ timeout: timeout() });
  const tooltip = button.locator('xpath=..').locator('[role="tooltip"]');
  if (await tooltip.count() !== 1) fail('official_usage_credit_view_unavailable');
  const monthly = tooltip.getByText('Monthly credits', { exact: true }).locator('xpath=..').locator('span').nth(1);
  const added = tooltip.getByText('Added credits', { exact: true }).locator('xpath=..').locator('span').nth(1);
  const refill = tooltip.locator(':scope > span').nth(1);
  const view = parseCreditView((await monthly.innerText({ timeout: timeout() })).trim(),
    (await refill.innerText({ timeout: timeout() })).trim(), (await added.innerText({ timeout: timeout() })).trim());
  if (view === null) fail('official_usage_credit_view_unavailable');
  return { principal: emails[0].toLowerCase(), view, observedAt: new Date().toISOString() };
}
async function accountSnapshot(accountId, principal) {
  const registry = await localJson('/api/v1/accounts?limit=200');
  if (!Array.isArray(registry?.items) || registry.page?.has_more !== false) fail('official_usage_pairing_unproven');
  const matches = registry.items.filter(account => account.provider_key === 'ollama'
    && account.lifecycle === 'active' && account.is_effective_monitoring_enabled === true
    && account.identity_state === 'owner_confirmed' && typeof account.friendly_name === 'string'
    && account.friendly_name.trim().toLowerCase() === principal);
  if (matches.length !== 1 || matches[0].account_id !== accountId) fail('official_usage_pairing_unproven');
  const connection = await localJson(`/api/v1/accounts/${encodeURIComponent(accountId)}/ollama-cloud-connection`);
  if (connection.state !== 'access_valid_owner_confirmed' || !['scheduled', 'reading'].includes(connection.monitoring_state)) fail('official_usage_connection_unavailable');
  const quotas = await localJson(`/api/v1/accounts/${encodeURIComponent(accountId)}/quotas/v2`);
  if (!Array.isArray(quotas?.items) || quotas.items.length !== 2 || quotas.page?.has_more !== false
      || new Set(quotas.items.map(item => item.window_key)).size !== 2) fail('official_usage_capacity_unavailable');
  for (const item of quotas.items) {
    if (item.subject?.account_id !== accountId || item.subject.provider_key !== 'ollama'
        || item.subject.provider_target_kind !== 'cloud_service' || item.semantic_role !== 'capacity'
        || item.freshness !== 'fresh' || item.provenance?.source_id !== 'ollama.cloud.balance.v1'
        || !Number.isFinite(Date.parse(item.observed_at)) || Date.parse(item.observed_at) > Date.now()
        || item.remaining?.availability !== 'available') fail('official_usage_capacity_unavailable');
  }
  if (new Set(quotas.items.map(item => item.subject.provider_target_id)).size !== 1
      || new Set(quotas.items.map(item => item.collection_run_id)).size !== 1
      || new Set(quotas.items.map(item => item.observed_at)).size !== 1) fail('official_usage_capacity_unavailable');
  return { account: matches[0], connection, quotas: { items: quotas.items, page: quotas.page } };
}
function nativeAmounts(quotas) {
  const included = quotas.items.find(item => item.window_key === 'ollama_included_credits');
  const purchased = quotas.items.find(item => item.window_key === 'ollama_purchased_credits');
  if (!included || !purchased || included.limit?.availability !== 'available'
      || purchased.limit?.availability !== 'unknown') return null;
  return { included: { remaining: included.remaining.value, limit: included.limit.value,
    resetAt: included.reset_at, resetPrecision: included.reset_precision },
  purchased: { remaining: purchased.remaining.value, limit: null, resetAt: purchased.reset_at ?? null } };
}
try {
  if (!/^[a-f0-9]{40}$/.test(revision ?? '')) fail('official_usage_revision_mismatch');
  browser = await chromium.connectOverCDP('http://127.0.0.1:9225', { timeout: timeout() });
  const pages = browser.contexts().flatMap(context => context.pages());
  const official = pages.filter(providerUrl);
  const selected = pages.filter(page => {
    try { const url = new URL(page.url()); return url.origin === origin && /^\/accounts\/[^/]+$/.test(url.pathname); }
    catch { return false; }
  });
  if (official.length !== 1 || selected.length !== 1) fail('official_usage_pairing_unproven');
  const accountId = decodeURIComponent(new URL(selected[0].url()).pathname.split('/').at(-1));
  disposable = await selected[0].context().newPage();
  disposable.setDefaultTimeout(5000);
  await disposable.goto(origin + '/', { waitUntil: 'domcontentloaded', timeout: timeout() });
  await currentRevision();
  for (let attempt = 0; attempt < 2; attempt += 1) {
    const providerBefore = await officialView(official[0]);
    const before = await accountSnapshot(accountId, providerBefore.principal);
    const amounts = nativeAmounts(before.quotas);
    if (amounts === null) fail('official_usage_capacity_unavailable');
    const decision = compareCreditView(providerBefore.view, amounts);
    const after = await accountSnapshot(accountId, providerBefore.principal);
    const providerAfter = await officialView(official[0]);
    await currentRevision();
    const stable = digest(before) === digest(after)
      && providerBefore.principal === providerAfter.principal
      && digest(providerBefore.view) === digest(providerAfter.view)
      && selected[0].url() === origin + '/accounts/' + encodeURIComponent(accountId);
    if (!stable) {
      if (attempt === 0) continue; // One read-only retry; never dispatch a provider check.
      fail('official_usage_lineage_changed');
    }
    result.provider_observed_at = providerAfter.observedAt;
    result.source_observed_at = before.quotas.items[0].observed_at;
    if (decision !== 'matched') {
      result.status = decision === 'mismatch' ? 'failed' : 'not_run';
      result.reason_code = decision === 'mismatch' ? 'official_usage_value_mismatch' : 'official_usage_capacity_unavailable';
      break;
    }
    result.status = 'passed'; result.reason_code = 'official_usage_compared'; result.compared_targets = 1;
    result.current_balance_lineage_sha256 = lineage(before.account, before.quotas);
    result.comparison_sha256 = digest({ revision, pairing: 'owner_asserted_visible_principal',
      account: before.account, connection: before.connection, provider: providerBefore.view,
      principal: providerBefore.principal, quotas: before.quotas,
      providerBefore: providerBefore.observedAt, providerAfter: providerAfter.observedAt });
    break;
  }
} catch (error) {
  const allowed = new Set(['official_usage_pairing_unproven', 'official_usage_observation_timeout',
    'official_usage_dashboard_unavailable', 'official_usage_revision_mismatch', 'official_usage_credit_view_unavailable',
    'official_usage_connection_unavailable', 'official_usage_capacity_unavailable', 'official_usage_lineage_changed']);
  result.status = 'not_run';
  result.reason_code = allowed.has(error?.message) ? error.message : 'official_usage_boundary_unavailable';
} finally {
  if (disposable !== undefined) await disposable.close().catch(() => {});
  if (browser !== undefined) await browser.close().catch(() => {});
  result.completed_at = new Date().toISOString();
}
console.log(JSON.stringify(result));
process.exitCode = result.status === 'passed' ? 0 : result.status === 'failed' ? 1 : 3;
