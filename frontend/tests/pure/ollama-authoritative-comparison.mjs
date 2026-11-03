import test from 'node:test';
import assert from 'node:assert/strict';
import { compareCreditView, matchesDisplayedUsd, parseCreditView, pairVisibleCreditViews, comparePairedCreditViews } from '../browser/m6/authoritative_credit_policy.mjs';

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
