"use strict";

import assert from "node:assert/strict";
import { usesApiOnlyLayout, accountOrganizationName } from "../../src/features/accounts/providerPresentation.ts";

// Pure account presentation policy. No constructed telemetry enters I/O.
assert.equal(usesApiOnlyLayout({ initial_connection_purpose: "api", has_active_subscription_resource: false }), true);
assert.equal(usesApiOnlyLayout({ initial_connection_purpose: "api", has_active_subscription_resource: true }), false);
assert.equal(usesApiOnlyLayout({ initial_connection_purpose: "api", has_active_subscription_resource: null }), true);
assert.equal(usesApiOnlyLayout({ initial_connection_purpose: "api" }), true);
assert.equal(usesApiOnlyLayout({ initial_connection_purpose: null, has_active_subscription_resource: true }), false);
assert.equal(usesApiOnlyLayout({ initial_connection_purpose: null, has_active_subscription_resource: false }), false);
assert.equal(usesApiOnlyLayout(undefined), false);
assert.equal(accountOrganizationName(null, []), "Ungrouped");
assert.equal(accountOrganizationName("assigned", []), "Organization unavailable");
assert.equal(accountOrganizationName("assigned", [{ organization_id: "assigned", name: "Selected organization" }]), "Selected organization");
console.log("ACCOUNT RESOURCE LAYOUT PURE: PASSED");
