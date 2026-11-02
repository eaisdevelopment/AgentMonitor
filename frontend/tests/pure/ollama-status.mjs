"use strict";

import assert from "node:assert/strict";
import { ollamaStatusMessage } from "../../src/features/providers/ollamaStatus.ts";

assert.equal(ollamaStatusMessage("success", "source_available", "source_available"), null);
assert.equal(
  ollamaStatusMessage("provider_unavailable", "collection_in_progress", "collection_in_progress"),
  "Another Ollama reading is in progress. Try again shortly.",
);
assert.equal(
  ollamaStatusMessage("deadline_exceeded", "operation_deadline_exceeded", "operation_deadline_exceeded"),
  "The Ollama reading timed out.",
);
assert.equal(
  ollamaStatusMessage("provider_unavailable", "source_unavailable", "source_unavailable"),
  "The local Ollama service is unavailable.",
);
assert.equal(
  ollamaStatusMessage("partial", "source_available", "operation_deadline_exceeded"),
  "Some Ollama information is unavailable.",
);
console.log("OLLAMA STATUS PURE: PASSED");
