"use strict";

import assert from "node:assert/strict";
import { exactMoneyText, displayMoney, completedPeriod } from "../../src/features/accounts/budgetPresentation.ts";

// Pure values only; these amounts never enter a browser, provider or database.
const money = (coefficient, scale, currency = "USD") => ({ coefficient, scale, currency });
assert.equal(exactMoneyText(money("9007199254740993123456789", 9)), "9007199254740993.123456789 USD");
assert.equal(displayMoney(money("9007199254740993123456789", 9)), "9007199254740993.12 USD");
assert.equal(displayMoney(money("0", 0)), "0.00 USD");
assert.equal(displayMoney(money("4", 3)), "<0.01 USD");
assert.equal(displayMoney(money("-4", 3)), "-<0.01 USD");
assert.equal(displayMoney(money("1005", 3)), "1.00 USD");
assert.equal(displayMoney(money("1015", 3)), "1.02 USD");
assert.equal(displayMoney(money("-1015", 3)), "-1.02 USD");
assert.equal(displayMoney(money("12345", 3, "GBP")), "12.345 GBP");
assert.deepEqual(completedPeriod(7, new Date("2026-03-29T23:45:00Z")), {
  period_start: "2026-03-22T00:00:00.000Z", period_end: "2026-03-29T00:00:00.000Z", as_of: "2026-03-29T23:45:00.000Z",
});
assert.deepEqual(completedPeriod(30, new Date("2026-11-11T02:30:00Z")), {
  period_start: "2026-10-12T00:00:00.000Z", period_end: "2026-11-11T00:00:00.000Z", as_of: "2026-11-11T02:30:00.000Z",
});
console.log("BUDGET ACCOUNT PRESENTATION PURE: PASSED");
