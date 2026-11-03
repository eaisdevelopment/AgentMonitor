/** Pure decimal/calendar comparison. No browser, network, clock or file access. */
const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
const fullMonths = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
const amountPattern = /^\$(?:0|[1-9]\d{0,17}|[1-9]\d{0,2}(?:,\d{3})+)(?:\.\d{2})?$/;

function displayedMoney(value) {
  if (typeof value !== 'string' || value.length > 32 || !amountPattern.test(value)) return null;
  const plain = value.slice(1).replaceAll(',', '');
  const parts = plain.split('.');
  return { coefficient: BigInt(parts.join('')), scale: parts.length === 2 ? 2 : 0 };
}

export function matchesDisplayedUsd(displayed, amount) {
  const expected = displayedMoney(displayed);
  if (expected === null || amount?.unit !== 'usd'
      || typeof amount.coefficient !== 'string' || !/^(?:0|[1-9]\d{0,31})$/.test(amount.coefficient)
      || !Number.isInteger(amount.scale) || Math.abs(amount.scale) > 18) return false;
  const source = BigInt(amount.coefficient);
  if (amount.scale <= expected.scale) {
    return source * (10n ** BigInt(expected.scale - amount.scale)) === expected.coefficient;
  }
  const divisor = 10n ** BigInt(amount.scale - expected.scale);
  // An integer display is treated conservatively as exact. Two decimal places
  // use decimal half-up rounding; no binary floating point enters the amount.
  if (expected.scale === 0) return source === expected.coefficient * divisor;
  return (source + divisor / 2n) / divisor === expected.coefficient;
}

function calendarDate(value) {
  if (typeof value !== 'string') return null;
  const match = /^([A-Za-z]{3,9}) (\d{1,2}), (\d{4})$/.exec(value);
  if (match === null) return null;
  const month = Math.max(months.indexOf(match[1]), fullMonths.indexOf(match[1])) + 1;
  if (month < 1) return null;
  const day = Number(match[2]);
  const iso = `${match[3]}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
  const timestamp = Date.parse(`${iso}T00:00:00Z`);
  return Number.isFinite(timestamp) && new Date(timestamp).toISOString().slice(0, 10) === iso ? iso : null;
}

export function parseCreditView(monthly, refill, added) {
  if (displayedMoney(monthly) === null || displayedMoney(added) === null
      || typeof refill !== 'string' || refill.length > 250) return null;
  const match = /^Refills to (\$[\d,.]+) on ([A-Za-z]{3,9} \d{1,2}, \d{4})\. Unused monthly credits that are part of the subscription do not carry over\.$/.exec(refill.trim());
  if (match === null || displayedMoney(match[1]) === null || calendarDate(match[2]) === null) return null;
  return { monthly, allowance: match[1], added, refillDate: match[2] };
}

export function compareCreditView(view, source) {
  const date = calendarDate(view?.refillDate);
  if (date === null || !source?.included?.remaining || !source?.included?.limit
      || !source?.purchased?.remaining || source.purchased.limit !== null
      || source.purchased.resetAt !== null || source.included.resetPrecision !== 'exact'
      || typeof source.included.resetAt !== 'string'
      || !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$/.test(source.included.resetAt)
      || !Number.isFinite(Date.parse(source.included.resetAt))) return 'unavailable';
  return matchesDisplayedUsd(view.monthly, source.included.remaining)
    && matchesDisplayedUsd(view.allowance, source.included.limit)
    && matchesDisplayedUsd(view.added, source.purchased.remaining)
    && source.included.resetAt.slice(0, 10) === date ? 'matched' : 'mismatch';
}

/** Pair visible, consistent official principals to unique owner-confirmed labels.
 * Distinct principals are comparison subjects, never proof of distinct pools.
 */
export function pairVisibleCreditViews(views, accounts) {
  if (!Array.isArray(views) || views.length < 1 || views.length > 100
      || !Array.isArray(accounts) || accounts.length > 200) return null;
  const groups = new Map();
  for (let index = 0; index < views.length; index += 1) {
    const item = views[index];
    if (typeof item?.principal !== 'string'
        || !/^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$/i.test(item.principal)) return null;
    const principal = item.principal.toLowerCase();
    const group = groups.get(principal);
    if (group !== undefined) {
      if (JSON.stringify(views[group.viewIndices[0]].view) !== JSON.stringify(item.view)) return null;
      group.viewIndices.push(index);
      continue;
    }
    const matches = accounts.filter(account => account.provider_key === 'ollama'
      && account.lifecycle === 'active' && account.is_effective_monitoring_enabled === true
      && account.identity_state === 'owner_confirmed' && typeof account.friendly_name === 'string'
      && account.friendly_name.trim().toLowerCase() === principal);
    if (matches.length !== 1 || typeof matches[0].account_id !== 'string' || matches[0].account_id.length < 1) return null;
    groups.set(principal, { principal, accountId: matches[0].account_id, viewIndices: [index] });
  }
  const result = [...groups.values()];
  return new Set(result.map(item => item.accountId)).size === result.length ? result : null;
}

export function comparePairedCreditViews(views, pairs, sources) {
  const unavailable = { decision: 'unavailable', comparedTargets: 0 };
  if (!Array.isArray(pairs) || pairs.length < 1 || !Array.isArray(sources)
      || new Set(pairs.map(pair => pair.accountId)).size !== pairs.length) return unavailable;
  const decisions = [];
  for (const pair of pairs) {
    const matches = sources.filter(source => source.accountId === pair.accountId);
    const observed = views[pair.viewIndices[0]];
    if (matches.length !== 1 || observed?.principal.toLowerCase() !== pair.principal) return unavailable;
    decisions.push(compareCreditView(observed.view, matches[0].amounts));
  }
  if (decisions.includes('mismatch')) return { decision: 'mismatch', comparedTargets: 0 };
  return decisions.every(decision => decision === 'matched')
    ? { decision: 'matched', comparedTargets: pairs.length } : unavailable;
}
