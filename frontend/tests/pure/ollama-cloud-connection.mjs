"use strict";

import assert from "node:assert/strict";
import { ollamaCloudConnectionCopy } from "../../src/features/accounts/ollamaCloudConnection.ts";

assert.equal(ollamaCloudConnectionCopy("not_configured").title, "Ollama cloud not connected");
assert.equal(ollamaCloudConnectionCopy("pending").title, "Waiting for a connection check");
const accessible = ollamaCloudConnectionCopy("access_valid_identity_unresolved");
assert.equal(accessible.title, "Ollama cloud access confirmed");
assert.match(accessible.description, /account name.*you provided/i);
assert.equal(ollamaCloudConnectionCopy("unauthorized").title, "Ollama rejected the connection");
assert.equal(ollamaCloudConnectionCopy("rate_limited").title, "Ollama temporarily limited requests");
assert.equal(ollamaCloudConnectionCopy("unknown_new_state").title, "Connection status unavailable");
console.log("OLLAMA CLOUD CONNECTION COPY: PASSED");

import { ollamaCloudConnectionAction } from "../../src/features/accounts/ollamaCloudConnection.ts";
assert.equal(ollamaCloudConnectionAction("not_configured", true), "Check connection");
assert.equal(ollamaCloudConnectionAction("access_valid_identity_unresolved", true), null);
assert.equal(ollamaCloudConnectionAction("pending", true), null);
assert.equal(ollamaCloudConnectionAction("unknown_new_state", true), null);
assert.equal(ollamaCloudConnectionAction("not_configured", false), null);
