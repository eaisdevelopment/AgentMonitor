import assert from "node:assert/strict";
import { restorePoolIntent, poolReason, organizationLabel, compatiblePoolChoices } from "../../src/features/accounts/financialPoolPresentation.ts";

// Constructed values exercise pure presentation/validation only; no I/O fixtures.
const context = { accountId: "account-a", resourceId: "resource-a", selector: "billing" };
const intent = { ...context, kind: "assign", revision: 7, idempotencyKey: "a".repeat(32), action: "create", poolId: null, organizationId: "group-a" };
assert.deepEqual(restorePoolIntent(JSON.stringify(intent), context), intent);
assert.equal(restorePoolIntent(JSON.stringify(intent), { ...context, accountId: "account-b" }), null);
assert.equal(restorePoolIntent(JSON.stringify({ ...intent, revision: 0 }), context), null);
assert.equal(restorePoolIntent(JSON.stringify({ ...intent, action: "join" }), context), null);
assert.equal(restorePoolIntent(JSON.stringify({ ...intent, action: "unlink", organizationId: "group-a" }), context), null);
assert.equal(restorePoolIntent(JSON.stringify({ ...intent, api_key: "not-an-accepted-field" }), context), null);
assert.equal(restorePoolIntent("{", context), null);
assert.equal(organizationLabel(null, []), "Ungrouped");
assert.equal(organizationLabel("group-a", []), "Organization unavailable");
const group = { organization_id: "group-a", name: "Owner group", lifecycle: "active" };
assert.equal(organizationLabel("group-a", [group]), "Owner group");
const choices = [
  { pool_id: "first", provider_key: "ollama", selector: "self" },
  { pool_id: "second", provider_key: "ollama", selector: "team" },
  { pool_id: "third", provider_key: "claude", selector: "billing" },
];
assert.deepEqual(compatiblePoolChoices(choices, "ollama", "self"), [choices[0]]);
assert.match(poolReason("financial_pool_binding_unavailable"), /credential/i);
assert.match(poolReason("financial_pool_incompatible"), /scope/i);
assert.doesNotMatch(poolReason("unrecognized_diagnostic"), /unrecognized_diagnostic/);
console.log("financial-pool-presentation: passed");
