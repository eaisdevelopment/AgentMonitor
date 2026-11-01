"use strict";

import assert from "node:assert/strict";
import { ollamaReadingFreshness } from "../../src/features/providers/ollamaFreshness.ts";

const now = Date.parse("2026-11-01T12:00:00Z");
assert.equal(ollamaReadingFreshness("2026-11-01T11:59:30Z", now), "current");
assert.equal(ollamaReadingFreshness("2026-11-01T11:58:30Z", now), "current");
assert.equal(ollamaReadingFreshness("2026-11-01T11:58:29Z", now), "stale");
assert.equal(ollamaReadingFreshness(null, now), "unknown");
assert.equal(ollamaReadingFreshness("invalid", now), "unknown");
assert.equal(ollamaReadingFreshness("2026-11-01T12:00:00Z", Number.NaN), "unknown");
assert.equal(ollamaReadingFreshness("2026-11-01T12:00:06Z", now), "unknown");
console.log("OLLAMA FRESHNESS PURE: PASSED");
