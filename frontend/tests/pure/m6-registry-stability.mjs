import test from 'node:test';
import assert from 'node:assert/strict';
import { registryContentDigest } from '../browser/m6/registry_stability_policy.mjs';

// Constructed values are used only for this pure comparison policy, never I/O.
const records = () => [[{
  account_id: 'account-a', provider_key: 'ollama', friendly_name: 'Cloud account',
  organization_id: 'organization-a', lifecycle: 'active', monitoring_preference: 'enabled',
  is_effective_monitoring_enabled: true, effective_monitoring_reason: 'enabled',
  identity_state: 'owner_confirmed', record_version: 4, registry_revision: 30,
  created_at: '2026-11-01T12:00:00Z', updated_at: '2026-11-02T12:00:00Z', archived_at: null,
}], [{
  organization_id: 'organization-a', name: 'Organization A', description: null,
  display_order: 0, lifecycle: 'active', active_account_count: 1, archived_account_count: 0,
  record_version: 2, registry_revision: 30,
}]];

test('unrelated global registry revision does not mean account configuration changed', () => {
  const before=records();
  const after=records();
  for (const rows of after) for (const row of rows) row.registry_revision=31;
  assert.equal(registryContentDigest(before), registryContentDigest(after));
  assert.equal(before[0][0].registry_revision,30);
});

test('every account or organization content change remains detectable', () => {
  const original=records();
  for (const [group, changes] of [[0, {
    friendly_name:'Changed', organization_id:null, lifecycle:'pending', monitoring_preference:'disabled',
    is_effective_monitoring_enabled:false, effective_monitoring_reason:'disabled', identity_state:'conflict',
    record_version:5, updated_at:'2026-11-04T12:00:00Z', future_contract_field:'new',
  }], [1, {name:'Changed', description:'New', display_order:1, lifecycle:'archived', record_version:3,
    active_account_count:2, archived_account_count:1}]]) {
    for (const [key,value] of Object.entries(changes)) {
      const changed=records();changed[group][0][key]=value;
      assert.notEqual(registryContentDigest(original),registryContentDigest(changed),key);
    }
  }
});

test('addition removal and restored edits with a new record version remain detectable', () => {
  for (const group of [0,1]) {
    const removed=records();removed[group]=[];
    const added=records();added[group].push({...added[group][0]});
    const restored=records();restored[group][0].record_version+=2;
    for(const changed of [removed,added,restored]) {
      assert.notEqual(registryContentDigest(records()),registryContentDigest(changed));
    }
  }
});
