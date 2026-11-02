"use strict";

import assert from "node:assert/strict";
import { exactUsd, isLowQuota } from "../../src/features/command/quotaPresentation.ts";

// Pure presentation inputs; these are not provider responses or I/O fixtures.
const quantity = (coefficient, scale, unit = "usd") => ({ coefficient, scale, unit });
assert.equal(exactUsd(quantity("125", 1)), "$12.50");
assert.equal(exactUsd(quantity("123456789012345678901", 3)), "$123456789012345678.901");
assert.equal(exactUsd(quantity("0", 0)), "$0.00");
assert.equal(exactUsd(quantity("12", 0, "tokens")), null);
assert.equal(exactUsd(quantity("-1", 0)), null);
assert.equal(isLowQuota(3, false), false);
assert.equal(isLowQuota(3, true), true);
assert.equal(isLowQuota(3, null), true);
assert.equal(isLowQuota(21, true), false);
