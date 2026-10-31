"use strict";

import assert from "node:assert/strict";

import {
  providerConnectionCopy,
  providerDisplayName,
} from "../../src/features/accounts/providerPresentation.ts";

assert.equal(providerDisplayName("claude"), "Claude");
assert.equal(providerDisplayName("codex"), "Codex");
assert.equal(providerDisplayName("other_provider"), "other provider");

const codex = providerConnectionCopy("codex");
assert.equal(codex.connected, "Codex connected");
assert.match(codex.idle, /Codex's official sign-in/);
assert.match(codex.wrongAccount, /Codex reported a different identity/);
assert.match(codex.wrongAccount, /quarantined/);
assert.match(codex.wrongAccount, /create a new account record/);
assert.match(codex.emailHelp, /Codex's official page/);

const claude = providerConnectionCopy("claude");
assert.equal(claude.connected, "Claude connected");
assert.match(claude.idle, /Claude's official sign-in/);

console.log("PROVIDER ACCOUNT PRESENTATION PURE: PASSED");
