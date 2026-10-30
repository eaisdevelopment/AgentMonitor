/** Compare owner-submitted historical screenshots to retained versioned API data. */
import { chromium } from '../../frontend/node_modules/@playwright/test/index.mjs';
import { readAllCapacityHistoryV1 } from './m5_registry_pages.mjs';
import { isExactCodexProvenanceV1 } from './m5_codex_policy.mjs';

const requireFact = (ok) => { if (!ok) throw new Error('historical_quota_evidence_invalid'); };
let payload = '';
for await (const chunk of process.stdin) payload += chunk;
const facts = JSON.parse(payload);
const browser = await chromium.connectOverCDP(process.env.AGENTMONITOR_TEST_DASHBOARD_CDP_ENDPOINT);
const context = browser.contexts()[0];
requireFact(context && Array.isArray(facts) && facts.length === 2);
const page = await context.newPage();
try {
  let mutations = 0;
  page.on('request', request => { if (['POST', 'PUT', 'PATCH', 'DELETE'].includes(request.method())) mutations++; });
  await page.goto(process.env.AGENTMONITOR_TEST_DASHBOARD_ORIGIN);
  const read = path => page.evaluate(async path => {
    const response = await fetch(path, { credentials: 'same-origin' });
    if (!response.ok) throw new Error('versioned_api_unavailable');
    return response.json();
  }, path);
  const records = [];
  for (const fact of facts) {
    const at = Date.parse(fact.file_mtime);
    requireFact(Number.isFinite(at));
    const id = encodeURIComponent(fact.account_id);
    const query = new URLSearchParams({subject_id: fact.account_id, metric: 'remaining_ratio',
      series_kind: 'poll_snapshot', from: new Date(at - 300000).toISOString(), before: new Date(at).toISOString()});
    const [identity, history] = await Promise.all([
      read(`/api/v1/accounts/${id}/provider-identity`),
      readAllCapacityHistoryV1(read, `/api/v1/capacity/history?${query}`),
    ]);
    requireFact(identity.state === 'verified' && identity.account_id === fact.account_id
      && typeof identity.email === 'string'
      && identity.email.normalize('NFKC').toLowerCase() === fact.email.normalize('NFKC').toLowerCase()
      && history.availability.state === 'available' && history.items.length > 0);
    const eligible = history.items.filter(p => p.subject?.account_id === fact.account_id
      && p.subject?.provider_key === 'codex' && p.metric === 'remaining_ratio'
      && p.series_kind === 'poll_snapshot' && isExactCodexProvenanceV1(p.provenance)
      && ['complete', 'partial'].includes(p.completeness)
      && Date.parse(p.observed_at) <= at && Date.parse(p.observed_at) >= at - 300000);
    requireFact(eligible.length > 0);
    const latest = Math.max(...eligible.map(p => Date.parse(p.observed_at)));
    const points = eligible.filter(p => Date.parse(p.observed_at) === latest);
    requireFact(points.length === fact.windows.length && new Set(points.map(p => p.collection_run_id)).size === 1
      && new Set(points.map(p => p.window_key)).size === points.length);
    const windows = points.map(p => {
      const v = p.value?.value;
      requireFact(p.value?.availability === 'available' && ['ratio', 'percent'].includes(v?.unit)
        && /^(0|[1-9][0-9]*)$/.test(v.coefficient) && Number.isInteger(v.scale) && v.scale >= 0 && v.scale <= 18);
      const n = BigInt(v.coefficient) * (v.unit === 'ratio' ? 100n : 1n), d = 10n ** BigInt(v.scale);
      requireFact(n % d === 0n && n / d <= 100n);
      return {window_key: p.window_key, semantic_role: p.semantic_role, remaining_percent: Number(n / d),
        reset_at: p.reset_at, reset_precision: p.reset_precision};
    });
    records.push({account_id: fact.account_id, collection_run_id: points[0].collection_run_id,
      collected_at: points[0].observed_at, windows});
  }
  requireFact(mutations === 0);
  console.log(JSON.stringify(records));
} finally { await page.close(); await browser.close(); }
