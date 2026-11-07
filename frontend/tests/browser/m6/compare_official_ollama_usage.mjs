/** Read the already open official Usage credit card and uniquely owner-paired accounts across existing browser contexts.
 * No provider requests/navigation, keys, requests table, billing or settings writes.
 */
import { chromium } from '@playwright/test';
import { createHash } from 'node:crypto';
import { parseCreditView, parsePercentageView, pairVisibleCreditViews, comparePairedCreditViews } from './authoritative_credit_policy.mjs';

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
function lineage(snapshots) {
  const rows = snapshots.flatMap(({ account, quotas }) => quotas.items.map(item => [account.account_id, item.subject.resource_id,
    item.subject.provider_target_id, item.window_id, item.current_observation_id, item.collection_run_id].join('\0')));
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
  if (await button.count() === 0) {
    // Read only balance labels and provider-authored reset metadata. Never read
    // the neighboring model/request history, payment controls or page body.
    const heading = page.getByRole('heading', { name: /^Usage credits/ });
    if (await heading.count() !== 1) fail('official_usage_credit_view_unavailable');
    const balance = heading.locator('xpath=..').locator(':scope > span');
    const cloud = page.getByRole('heading', { name: 'Cloud usage', exact: true }).locator('xpath=../..');
    async function usage(label) {
      const row = cloud.locator(':scope > div').filter({ has: page.getByText(label, { exact: true }) });
      const used = row.getByText(/^\s*\d+(?:\.\d+)?% used\s*$/);
      const reset = row.locator('[data-time]').filter({ hasText: /Resets in/ });
      if (await row.count() !== 1 || await used.count() !== 1 || await reset.count() !== 1
          || !await used.isVisible() || !await reset.isVisible()) fail('official_usage_credit_view_unavailable');
      return { used: (await used.innerText({ timeout: timeout() })).trim(),
        reset: await reset.getAttribute('data-time', { timeout: timeout() }) };
    }
    if (await balance.count() !== 1 || !await balance.isVisible()) fail('official_usage_credit_view_unavailable');
    const session = await usage('Session usage');
    const weekly = await usage('Weekly usage');
    const view = parsePercentageView(session.used, weekly.used,
      (await balance.innerText({ timeout: timeout() })).trim(), session.reset, weekly.reset);
    if (view === null) fail('official_usage_credit_view_unavailable');
    return { principal: emails[0].toLowerCase(), view, observedAt: new Date().toISOString() };
  }
  if (await button.count() !== 1) fail('official_usage_credit_view_unavailable');
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
async function registryAccounts() {
  const registry = await localJson('/api/v1/accounts?limit=200');
  if (!Array.isArray(registry?.items) || registry.items.length > 200 || registry.page?.has_more !== false) fail('official_usage_pairing_unproven');
  return registry.items;
}
async function accountSnapshot(accountId, principal) {
  const matches = (await registryAccounts()).filter(account => account.provider_key === 'ollama'
    && account.lifecycle === 'active' && account.is_effective_monitoring_enabled === true
    && account.identity_state === 'owner_confirmed' && typeof account.friendly_name === 'string'
    && account.friendly_name.trim().toLowerCase() === principal);
  if (matches.length !== 1 || matches[0].account_id !== accountId) fail('official_usage_pairing_unproven');
  const connection = await localJson(`/api/v1/accounts/${encodeURIComponent(accountId)}/ollama-cloud-connection`);
  if (connection.state !== 'access_valid_owner_confirmed' || !['scheduled', 'reading'].includes(connection.monitoring_state)) fail('official_usage_connection_unavailable');
  const quotas = await localJson(`/api/v1/accounts/${encodeURIComponent(accountId)}/quotas/v2`);
  if (!Array.isArray(quotas?.items) || ![2, 3].includes(quotas.items.length) || quotas.page?.has_more !== false
      || new Set(quotas.items.map(item => item.window_key)).size !== quotas.items.length) fail('official_usage_capacity_unavailable');
  for (const item of quotas.items) {
    if (item.subject?.account_id !== accountId || item.subject.provider_key !== 'ollama'
        || item.subject.provider_target_kind !== 'cloud_service' || item.semantic_role !== 'capacity'
        || item.freshness !== 'fresh' || item.provenance?.source_id !== 'ollama.cloud.balance.v1'
        || !Number.isFinite(Date.parse(item.observed_at)) || Date.parse(item.observed_at) > Date.now()) fail('official_usage_capacity_unavailable');
  }
  if (new Set(quotas.items.map(item => item.subject.provider_target_id)).size !== 1
      || new Set(quotas.items.map(item => item.collection_run_id)).size !== 1
      || new Set(quotas.items.map(item => item.observed_at)).size !== 1) fail('official_usage_capacity_unavailable');
  return { account: matches[0], connection, quotas: { items: quotas.items, page: quotas.page } };
}
function nativeAmounts(quotas) {
  const included = quotas.items.find(item => item.window_key === 'ollama_included_credits');
  const purchased = quotas.items.find(item => item.window_key === 'ollama_purchased_credits');
  if (!purchased || purchased.remaining?.availability !== 'available'
      || purchased.limit?.availability !== 'unknown') return null;
  if (quotas.items.length === 3) {
    const session = quotas.items.find(item => item.window_key === 'ollama_session');
    const weekly = quotas.items.find(item => item.window_key === 'ollama_weekly');
    if (included || !session || !weekly || session.remaining_ratio?.availability !== 'available'
        || weekly.remaining_ratio?.availability !== 'available') return null;
    return { kind: 'percentage',
      session: { remainingRatio: session.remaining_ratio.value, resetAt: session.reset_at, resetPrecision: session.reset_precision },
      weekly: { remainingRatio: weekly.remaining_ratio.value, resetAt: weekly.reset_at, resetPrecision: weekly.reset_precision },
      purchased: { remaining: purchased.remaining.value, limit: null, resetAt: purchased.reset_at ?? null } };
  }
  if (!included || included.remaining?.availability !== 'available' || included.limit?.availability !== 'available') return null;
  return { included: { remaining: included.remaining.value, limit: included.limit.value,
    resetAt: included.reset_at, resetPrecision: included.reset_precision },
  purchased: { remaining: purchased.remaining.value, limit: null, resetAt: purchased.reset_at ?? null } };
}
try {
  if (!/^[a-f0-9]{40}$/.test(revision ?? '')) fail('official_usage_revision_mismatch');
  browser = await chromium.connectOverCDP('http://127.0.0.1:9225', { timeout: timeout() });
  const pages = browser.contexts().flatMap(context => context.pages());
  const official = pages.filter(providerUrl);
  const dashboard = pages.find(page => {
    try { return new URL(page.url()).origin === origin; }
    catch { return false; }
  });
  if (official.length < 1 || official.length > 100 || dashboard === undefined) fail('official_usage_pairing_unproven');
  disposable = await dashboard.context().newPage();
  disposable.setDefaultTimeout(5000);
  await disposable.goto(origin + '/', { waitUntil: 'domcontentloaded', timeout: timeout() });
  await currentRevision();
  for (let attempt = 0; attempt < 2; attempt += 1) {
    const providerBefore = [];
    for (const page of official) providerBefore.push(await officialView(page));
    const pairs = pairVisibleCreditViews(providerBefore, await registryAccounts());
    if (pairs === null) fail('official_usage_pairing_unproven');
    const before = [];
    const sources = [];
    for (const pair of pairs) {
      const snapshot = await accountSnapshot(pair.accountId, pair.principal);
      const amounts = nativeAmounts(snapshot.quotas);
      if (amounts === null) fail('official_usage_capacity_unavailable');
      before.push(snapshot);
      sources.push({ accountId: pair.accountId, amounts });
    }
    const comparison = comparePairedCreditViews(providerBefore, pairs, sources);
    const after = [];
    for (const pair of pairs) after.push(await accountSnapshot(pair.accountId, pair.principal));
    const providerAfter = [];
    for (const page of official) providerAfter.push(await officialView(page));
    const afterPairs = pairVisibleCreditViews(providerAfter, await registryAccounts());
    await currentRevision();
    const stable = digest(before) === digest(after) && digest(pairs) === digest(afterPairs)
      && digest(providerBefore.map(({ principal, view }) => ({ principal, view })))
        === digest(providerAfter.map(({ principal, view }) => ({ principal, view })));
    if (!stable) {
      if (attempt === 0) continue; // One read-only retry; never dispatch a provider check.
      fail('official_usage_lineage_changed');
    }
    result.provider_observed_at = providerAfter.at(-1).observedAt;
    result.source_observed_at = before.map(item => item.quotas.items[0].observed_at)
      .sort((left, right) => Date.parse(left) - Date.parse(right))[0];
    if (comparison.decision !== 'matched') {
      const mismatch = comparison.decision === 'mismatch';
      result.status = mismatch ? 'failed' : 'not_run';
      result.reason_code = mismatch ? 'official_usage_value_mismatch' : 'official_usage_capacity_unavailable';
      break;
    }
    result.status = 'passed'; result.reason_code = 'official_usage_compared'; result.compared_targets = comparison.comparedTargets;
    result.current_balance_lineage_sha256 = lineage(before);
    result.comparison_sha256 = digest({ revision, pairing: 'owner_asserted_visible_principal',
      snapshots: before, providerBefore, providerAfter, pairs });
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
