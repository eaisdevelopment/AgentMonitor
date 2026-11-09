import test from 'node:test';
import assert from 'node:assert/strict';
import * as policy from '../browser/m6/authoritative_credit_policy.mjs';
import { compareCreditView, matchesDisplayedUsd, parseCreditView, pairVisibleCreditViews, comparePairedCreditViews, parsePercentageView, comparePercentageView } from '../browser/m6/authoritative_credit_policy.mjs';

// Constructed values remain entirely inside these pure decimal/date decisions.
const money = (coefficient, scale = 2) => ({ coefficient, scale, unit: 'usd' });
const view = { monthly: '$42.38', allowance: '$80', added: '$2.50', refillDate: 'Dec 10, 2026' };
const source = {
  included: { remaining: money('423812', 4), limit: money('80', 0), resetAt: '2026-12-10T00:00:00Z', resetPrecision: 'exact' },
  purchased: { remaining: money('250'), limit: null, resetAt: null },
};

test('native USD comparison preserves decimals and separate credit buckets', () => {
  assert.equal(compareCreditView(view, source), 'matched');
  assert.equal(matchesDisplayedUsd('$42.38', money('423812', 4)), true);
  assert.equal(matchesDisplayedUsd('$42.38', money('423850', 4)), false);
});

test('integer provider display cannot hide a fractional amount', () => {
  assert.equal(matchesDisplayedUsd('$0', money('0', 0)), true);
  assert.equal(matchesDisplayedUsd('$0', money('4', 1)), false);
});

test('negative values, other units, unsupported precision and floats fail closed', () => {
  for (const value of [money('-1'), { ...money('100'), unit: 'percent' }, money(123.4), money('1', 99)]) {
    assert.equal(matchesDisplayedUsd('$1', value), false);
  }
});

test('refill date is compared at the provider calendar-date precision', () => {
  assert.equal(compareCreditView(view, { ...source, included: { ...source.included, resetAt: '2026-12-11T00:00:00Z' } }), 'mismatch');
  assert.equal(compareCreditView(view, { ...source, included: { ...source.included, resetAt: null } }), 'unavailable');
});

test('swapped buckets and synthesized purchased allowance do not match', () => {
  assert.equal(compareCreditView({ ...view, monthly: '$2.50' }, source), 'mismatch');
  assert.equal(compareCreditView(view, { ...source, purchased: { ...source.purchased, limit: money('80', 0) } }), 'unavailable');
});

test('credit label parser accepts only the precise supported refill text', () => {
  assert.deepEqual(parseCreditView('$42.38', 'Refills to $80 on Dec 10, 2026. Unused monthly credits that are part of the subscription do not carry over.', '$2.50'), view);
  assert.equal(parseCreditView('$42.38', 'Available next month', '$2.50'), null);
});

test('official full month names retain the same calendar precision', () => {
  assert.equal(compareCreditView({ ...view, refillDate: 'December 10, 2026' }, source), 'matched');
  assert.equal(parseCreditView('$42.38', 'Refills to $80 on December 10, 2026. Unused monthly credits that are part of the subscription do not carry over.', '$2.50')?.refillDate, 'December 10, 2026');
});


const account = (accountId, label) => ({ account_id: accountId, friendly_name: label,
  provider_key: 'ollama', lifecycle: 'active', is_effective_monitoring_enabled: true,
  identity_state: 'owner_confirmed' });
const visible = (principal, creditView = view) => ({ principal, view: creditView });

test('two visible principals pair to two distinct owner-confirmed records', () => {
  assert.deepEqual(pairVisibleCreditViews(
    [visible('one@example.invalid'), visible('two@example.invalid')],
    [account('one', 'one@example.invalid'), account('two', 'two@example.invalid')],
  ), [
    { principal: 'one@example.invalid', accountId: 'one', viewIndices: [0] },
    { principal: 'two@example.invalid', accountId: 'two', viewIndices: [1] },
  ]);
});

test('duplicate tabs with identical principal and credit display count once', () => {
  assert.deepEqual(pairVisibleCreditViews(
    [visible('one@example.invalid'), visible('one@example.invalid')],
    [account('one', 'one@example.invalid')],
  ), [{ principal: 'one@example.invalid', accountId: 'one', viewIndices: [0, 1] }]);
});

test('ambiguous duplicate display or Registry identity is unproven', () => {
  assert.equal(pairVisibleCreditViews(
    [visible('one@example.invalid'), visible('one@example.invalid', { ...view, added: '$9' })],
    [account('one', 'one@example.invalid')],
  ), null);
  assert.equal(pairVisibleCreditViews([visible('one@example.invalid')],
    [account('one', 'one@example.invalid'), account('two', 'one@example.invalid')]), null);
});

test('unmapped or not owner-confirmed principals are unproven', () => {
  assert.equal(pairVisibleCreditViews([visible('one@example.invalid')], []), null);
  assert.equal(pairVisibleCreditViews([visible('one@example.invalid')],
    [{ ...account('one', 'one@example.invalid'), identity_state: 'unknown' }]), null);
});

test('only visible paired accounts count; absent other scopes are not fabricated', () => {
  assert.equal(pairVisibleCreditViews([visible('one@example.invalid')],
    [account('one', 'one@example.invalid'), account('two', 'two@example.invalid')]).length, 1);
});


test('all exact paired sources aggregate once and swapped accounts fail', () => {
  const otherView = { ...view, monthly: '$18.25' };
  const otherSource = { ...source, included: { ...source.included, remaining: money('1825') } };
  const views = [visible('one@example.invalid'), visible('two@example.invalid', otherView)];
  const pairs = pairVisibleCreditViews(views, [account('one', 'one@example.invalid'), account('two', 'two@example.invalid')]);
  assert.deepEqual(comparePairedCreditViews(views, pairs, [
    { accountId: 'two', amounts: otherSource }, { accountId: 'one', amounts: source },
  ]), { decision: 'matched', comparedTargets: 2 });
  assert.deepEqual(comparePairedCreditViews(views, pairs, [
    { accountId: 'one', amounts: otherSource }, { accountId: 'two', amounts: source },
  ]), { decision: 'mismatch', comparedTargets: 0 });
  assert.deepEqual(comparePairedCreditViews(views, pairs, [{ accountId: 'one', amounts: source }]),
    { decision: 'unavailable', comparedTargets: 0 });
});

const ratio = (coefficient, scale = 4) => ({ coefficient, scale, unit: 'ratio' });
const percentageView = { kind: 'percentage', sessionUsed: '100% used', weeklyUsed: '27.9% used',
  purchased: '$0', sessionReset: '2026-11-05T17:00:00Z', weeklyReset: '2026-11-09T00:00:00Z' };
const percentageSource = { kind: 'percentage',
  session: { remainingRatio: ratio('0'), resetAt: percentageView.sessionReset, resetPrecision: 'exact' },
  weekly: { remainingRatio: ratio('7213'), resetAt: percentageView.weeklyReset, resetPrecision: 'exact' },
  purchased: { remaining: money('0', 0), limit: null, resetAt: null } };

test('dashboard balances compare without claiming unavailable resets matched', () => {
  const balanceView = policy.parsePercentageBalanceView('100% used', '27.9% used', '$0');
  assert.deepEqual(balanceView, { kind: 'percentage_balances', sessionUsed: '100% used',
    weeklyUsed: '27.9% used', purchased: '$0', resetComparison: 'unavailable' });
  assert.equal(policy.comparePercentageBalanceView(balanceView, percentageSource), 'matched');
  assert.equal(policy.comparePercentageBalanceView({ ...balanceView, weeklyUsed: '72.1% used' }, percentageSource), 'mismatch');
  assert.equal(policy.comparePercentageBalanceView({ ...balanceView, purchased: '$1' }, percentageSource), 'mismatch');
  assert.equal(policy.comparePercentageBalanceView({ ...balanceView, resetComparison: 'matched' }, percentageSource), 'unavailable');
  assert.equal(policy.comparePercentageBalanceView({ ...balanceView, sessionReset: percentageView.sessionReset }, percentageSource), 'unavailable');
});

test('dashboard balance comparison still rejects invalid source fields and missing amounts', () => {
  const balanceView = policy.parsePercentageBalanceView('100% used', '27.9% used', '$0');
  for (const invalid of [null, { ...percentageSource, session: null },
    { ...percentageSource, weekly: { ...percentageSource.weekly, remainingRatio: ratio('10001') } },
    { ...percentageSource, purchased: { ...percentageSource.purchased, remaining: null } }]) {
    assert.equal(policy.comparePercentageBalanceView(balanceView, invalid), 'unavailable');
  }
  assert.equal(policy.parsePercentageBalanceView('101% used', '27.9% used', '$0'), null);
  assert.equal(policy.parsePercentageBalanceView('100% used', '27.9% used', null), null);
});

test('mixed plan pairing keeps balance-only reset limitation explicit in the view', () => {
  const balanceView = policy.parsePercentageBalanceView('100% used', '27.9% used', '$0');
  const views = [visible('one@example.invalid'), visible('two@example.invalid', balanceView)];
  const pairs = pairVisibleCreditViews(views, [account('one', 'one@example.invalid'), account('two', 'two@example.invalid')]);
  assert.deepEqual(comparePairedCreditViews(views, pairs, [
    { accountId: 'one', amounts: source }, { accountId: 'two', amounts: percentageSource },
  ]), { decision: 'matched', comparedTargets: 2 });
});

test('paired comparison supports simultaneous USD and percentage plans without changing units', () => {
  const views = [visible('one@example.invalid'), visible('two@example.invalid', percentageView)];
  const pairs = pairVisibleCreditViews(views, [account('one', 'one@example.invalid'), account('two', 'two@example.invalid')]);
  assert.deepEqual(comparePairedCreditViews(views, pairs, [
    { accountId: 'one', amounts: source }, { accountId: 'two', amounts: percentageSource },
  ]), { decision: 'matched', comparedTargets: 2 });
});

test('percentage parser retains the official used labels and exact reset metadata', () => {
  assert.deepEqual(parsePercentageView('100% used', '27.9% used', '$0', percentageView.sessionReset, percentageView.weeklyReset), percentageView);
  for (const value of ['100.1% used', '-1% used', '027.9% used', '27.9% left', '27.9%', ' 27.9% used', 27.9, null]) {
    assert.equal(parsePercentageView(value, '27.9% used', '$0', percentageView.sessionReset, percentageView.weeklyReset), null);
  }
  for (const reset of [null, 'tomorrow', '2026-02-30T00:00:00Z', '2026-11-05T17:00:00', '2026-11-05T17:00:00+01:00']) {
    assert.equal(parsePercentageView('100% used', '27.9% used', '$0', reset, percentageView.weeklyReset), null);
  }
  assert.equal(parsePercentageView('100% used', '27.9% used', '0', percentageView.sessionReset, percentageView.weeklyReset), null);
});

test('remaining ratios are complemented to used percentages with decimal half-up rounding', () => {
  assert.equal(comparePercentageView(percentageView, percentageSource), 'matched');
  assert.equal(comparePercentageView({ ...percentageView, weeklyUsed: '72.1% used' }, percentageSource), 'mismatch');
  const withWeekly = remainingRatio => ({ ...percentageSource, weekly: { ...percentageSource.weekly, remainingRatio } });
  assert.equal(comparePercentageView(percentageView, withWeekly(ratio('7215'))), 'matched');
  assert.equal(comparePercentageView(percentageView, withWeekly(ratio('721500000000000001', 18))), 'mismatch');
  assert.equal(comparePercentageView({ ...percentageView, weeklyUsed: '28% used' }, withWeekly(ratio('725'))), 'mismatch');
  assert.equal(comparePercentageView({ ...percentageView, weeklyUsed: '28% used' }, withWeekly(ratio('725', 3))), 'matched');
  assert.equal(comparePercentageView({ ...percentageView, sessionUsed: '0% used' }, {
    ...percentageSource, session: { ...percentageSource.session, remainingRatio: ratio('1', 0) },
  }), 'matched');
});

test('invalid, missing, mixed or out-of-range percentage inputs remain unavailable', () => {
  for (const remainingRatio of [null, ratio('-1'), ratio('10001'), ratio('01'), ratio(7213), ratio('1', -1), ratio('1', 19),
    { ...ratio('7213'), unit: 'percent' }, { ...ratio('7213'), used: '27.87' }]) {
    assert.equal(comparePercentageView(percentageView, { ...percentageSource,
      weekly: { ...percentageSource.weekly, remainingRatio } }), 'unavailable');
  }
  for (const invalid of [null, { ...percentageSource, kind: 'other' }, { ...percentageSource, included: source.included },
    { ...percentageSource, session: null }, { ...percentageSource, purchased: { ...percentageSource.purchased, limit: money('1') } },
    { ...percentageSource, purchased: { ...percentageSource.purchased, remaining: money('-1') } },
    { ...percentageSource, purchased: { ...percentageSource.purchased, resetAt: percentageView.sessionReset } }]) {
    assert.equal(comparePercentageView(percentageView, invalid), 'unavailable');
  }
  assert.equal(comparePercentageView({ ...percentageView, monthly: '$0' }, percentageSource), 'unavailable');
  assert.equal(comparePercentageView({ ...percentageView, weeklyUsed: undefined }, percentageSource), 'unavailable');
});

test('percentage reset checks preserve exact instants and never substitute calendar dates', () => {
  assert.equal(comparePercentageView(percentageView, { ...percentageSource,
    session: { ...percentageSource.session, resetAt: '2026-11-05T17:00:00.000000000+00:00' } }), 'matched');
  for (const resetAt of ['2026-11-05T18:00:00Z', '2026-11-05T17:00:00.000001Z']) {
    assert.equal(comparePercentageView(percentageView, { ...percentageSource,
      session: { ...percentageSource.session, resetAt } }), 'mismatch');
  }
  for (const resetPrecision of ['rounded', 'unknown', null]) {
    assert.equal(comparePercentageView(percentageView, { ...percentageSource,
      session: { ...percentageSource.session, resetPrecision } }), 'unavailable');
  }
  assert.equal(comparePercentageView(percentageView, { ...percentageSource,
    weekly: { ...percentageSource.weekly, resetAt: '2026-02-30T00:00:00Z' } }), 'unavailable');
});

test('percentage purchased credits use the existing exact USD rules', () => {
  assert.equal(comparePercentageView(percentageView, { ...percentageSource,
    purchased: { ...percentageSource.purchased, remaining: money('4', 1) } }), 'mismatch');
  assert.equal(comparePercentageView({ ...percentageView, purchased: '$2.50' }, { ...percentageSource,
    purchased: { ...percentageSource.purchased, remaining: money('2504', 3) } }), 'matched');
});

test('paired comparison rejects mixed source kinds and legacy shapes with percentage fields', () => {
  const views = [visible('one@example.invalid')];
  const pairs = pairVisibleCreditViews(views, [account('one', 'one@example.invalid')]);
  for (const amounts of [percentageSource, { ...source, kind: 'percentage' }, { ...source, session: percentageSource.session }]) {
    assert.deepEqual(comparePairedCreditViews(views, pairs, [{ accountId: 'one', amounts }]),
      { decision: 'unavailable', comparedTargets: 0 });
  }
});
