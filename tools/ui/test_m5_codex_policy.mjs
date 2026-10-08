import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

import {
  bindIndependentCodexExecutableProofsV1,
  buildCodexWitnessV1,
  codexExecutableIdentityDigestV1,
  normalizeCodexQuotaWindowsV1,
  isExactCodexProvenanceV1,
  isExactServiceRevisionV1,
  isFreshCodexLineageV1,
  liveIdentityDigestV1,
  parseLinuxProcStatV1,
  publicRegistryDigestV1,
  selectRepresentativeCodexProcessesV1,
  validateOwnerOutcomesV1,
} from "./m5_codex_policy.mjs";
import { readAllRegistryItemsV1 } from "./m5_registry_pages.mjs";

const digest = value => value.repeat(64);
const serviceRevision = "a".repeat(40);
const ownerRoot = "/home/owner/.local/share/agentmonitor";
const outcomes = {
  schema: "agentmonitor.m5-owner-outcomes.v2",
  implementation_revision: "a".repeat(40),
  service_pid: 321,
  service_start_time_ticks: 654,
  owner_confirmed_at: "2026-10-07T10:00:00Z",
  owner_confirmation: true,
  outcomes: [
    { account_id: "account-one", alias: "Private one", disposition: "verified" },
    { account_id: "account-two", alias: "Private two", disposition: "verified" },
    { account_id: "account-three", alias: "Private three", disposition: "owner_unavailable", reason: "owner_login_unavailable" },
    { account_id: "account-four", alias: "Private four", disposition: "owner_unavailable", reason: "owner_login_unavailable" },
  ],
};

const provenance = {
  source_id: "codex.app-server.account-rate-limits-read.v2",
  adapter_id: "agentmonitor.codex",
  adapter_version: "1.0.2",
  parser_version: "1.0.1",
  provider_version: "0.160.0",
  decision_reference: "M5-CDX-0-160-0-002",
  is_experimental: true,
};
const remainingRatio = {
  availability: "available",
  value: { coefficient: "76", scale: 2, unit: "ratio" },
  precision: "exact",
  confidence: "confirmed",
  value_kind: "provider_reported",
  reason_code: null,
};

const records = ["account-one", "account-two"].map((accountId, index) => ({
  accountId,
  collectionRunId: `run-${index}`,
  currentHistoryMatched: true,
  freshAfterRestart: true,
  providerKey: "codex",
  lifecycle: "active",
  monitoringPreference: "enabled",
  effectiveMonitoringEnabled: true,
  identityState: "owner_confirmed",
  accountRecordVersion: 1,
  accountRegistryRevision: index + 1,
  liveIdentityDigest: digest(String(index + 1)),
  quotaWindows: [
    {
      windowKey: "codex:primary",
      semanticRole: "primary",
      remainingPercent: 18 + index,
      resetEpoch: 1_791_331_200,
      resetPrecision: "exact",
      currentObservationId: `observation-${index}-primary`,
    },
    {
      windowKey: "codex:secondary",
      semanticRole: "secondary",
      remainingPercent: 76 + index,
      resetEpoch: null,
      resetPrecision: "unknown",
      currentObservationId: `observation-${index}-secondary`,
    },
  ],
}));

const processes = Array.from({ length: 5 }, (_, index) => ({
  pid: 1000 + index,
  start_time_ticks: 2000 + index,
  platform_scope_id: `${index + 1}`.repeat(64),
  provider_key: "codex",
  provider_version: "0.160.0",
  state: "running",
  account_correlation: "unresolved",
  working_directory: `/home/owner/project-${index}`,
  observed_at: "2026-10-07T10:00:00Z",
  parent_pid: 500 + index,
  association_key: `${index + 5}`.repeat(64),
  account_association: null,
}));
const executableMetadata = {
  device: "66306",
  inode: "3598569",
  fileType: "32768",
  sizeBytes: "289101384",
  modifiedNs: "1790876010940495000",
  changedNs: "1790950975357341254",
};
const executableIdentity = codexExecutableIdentityDigestV1(executableMetadata);
const processProofs = processes.map(item => ({
  pid: item.pid,
  parentPid: item.parent_pid,
  startTimeTicks: item.start_time_ticks,
  workingDirectoryBefore: item.working_directory,
  workingDirectoryAfter: item.working_directory,
  executableIdentityBefore: executableIdentity,
  executableIdentityAfter: executableIdentity,
}));
const provenProcesses = bindIndependentCodexExecutableProofsV1(
  processes,
  processProofs,
  executableIdentity,
  { ownerRoot },
);

test("live entrypoint wires independent executable proofs into the witness", () => {
  const source = readFileSync(
    new URL("./verify_m5_codex.mjs", import.meta.url),
    "utf8",
  );
  const alertSource = readFileSync(
    new URL("./verify_m5_codex_alert_lifecycle.mjs", import.meta.url),
    "utf8",
  );
  const quotaSource = readFileSync(
    new URL("./verify_m5_codex_quota_reconciliation.mjs", import.meta.url),
    "utf8",
  );
  assert.match(source, /await readIndependentProcessProof\(process\)/);
  assert.match(source, /open\(`\$\{root\}\/exe`, "r"\)/);
  assert.match(source, /bindIndependentCodexExecutableProofsV1\([\s\S]*?\{ ownerRoot \},\n\s*\)/);
  assert.match(source, /buildCodexWitnessV1\(ownerDocument, records, representativeProcesses,/);
  assert.match(source, /processScanTruncated:[\s\S]*?ownerRoot,/);
  assert.match(source, /readAllRegistryItemsV1/);
  assert.match(source, /getByText\("Activity unknown", \{[\s\S]*?exact: true,/);
  assert.match(source, /process\.account_association === null[\s\S]*?"Account unknown"[\s\S]*?: "Owner confirmed"/);
  assert.match(source, /throw new VerificationError\("owner_outcomes_changed", true\)/);
  assert.doesNotMatch(source, /for \(let pageIndex = 0; pageIndex < 64;/);
  assert.match(alertSource, /readAllRegistryItemsV1/);
  assert.doesNotMatch(alertSource, /for \(let pageIndex = 0; pageIndex < 64;/);
  assert.match(quotaSource, /\.usage-allowance \.allowance-card\[data-window-key\]/);
  assert.doesNotMatch(quotaSource, /\.workspace-reading\[data-window-key\]/);
  assert.match(
    quotaSource,
    /const historyDetails = page\.locator\("details\.quota-history"\);[\s\S]*?await historyDetails\.locator\("summary"\)\.evaluate\(element => element\.click\(\)\);/,
  );
});

test("registry pagination requires every available page and a progressing cursor", async () => {
  const requested = [];
  const pages = [
    {
      availability: { state: "available" },
      items: [{ account_id: "account-one" }],
      page: { has_more: true, next_cursor: "cursor-one" },
    },
    {
      availability: { state: "available" },
      items: [{ account_id: "account-two" }],
      page: { has_more: false, next_cursor: null },
    },
  ];
  const items = await readAllRegistryItemsV1(async path => {
    requested.push(path);
    return pages.shift();
  }, "/api/v1/accounts");
  assert.deepEqual(items.map(item => item.account_id), ["account-one", "account-two"]);
  assert.deepEqual(requested, [
    "/api/v1/accounts?limit=200",
    "/api/v1/accounts?limit=200&cursor=cursor-one",
  ]);

  await assert.rejects(
    readAllRegistryItemsV1(async () => ({
      availability: { state: "unavailable" },
      items: [],
      page: { has_more: false, next_cursor: null },
    }), "/api/v1/accounts"),
    /registry_page_invalid/,
  );
});

test("owner outcomes accept exactly four unique verified or unavailable rows", () => {
  const expectedContext = {
    implementationRevision: "a".repeat(40),
    servicePid: 321,
    serviceStartTimeTicks: 654,
  };
  const selected = validateOwnerOutcomesV1(
    outcomes,
    new Date("2026-10-07T10:05:00Z"),
    expectedContext,
  );
  assert.equal(selected.length, 4);
  assert.equal(selected.filter(row => row.disposition === "verified").length, 2);
  for (const change of [
    { outcomes: outcomes.outcomes.slice(0, 3) },
    { outcomes: outcomes.outcomes.map((row, index) => index === 3 ? { ...row, account_id: "account-one" } : row) },
    { outcomes: outcomes.outcomes.map((row, index) => index === 3 ? { ...row, alias: " private ONE " } : row) },
    { outcomes: outcomes.outcomes.map((row, index) => index === 0 ? { ...row, disposition: "unresolved" } : row) },
    { outcomes: outcomes.outcomes.map((row, index) => index === 0 ? { ...row, identity_fingerprint: digest("f") } : row) },
    { implementation_revision: "b".repeat(39) },
    { owner_confirmation: false },
    { owner_confirmed_at: "2026-09-01T10:00:00Z" },
  ]) {
    assert.throws(
      () => validateOwnerOutcomesV1({ ...outcomes, ...change }, new Date("2026-10-07T10:05:00Z")),
      /owner_outcomes_invalid/,
    );
  }
  assert.throws(
    () => validateOwnerOutcomesV1(
      outcomes,
      new Date("2026-10-07T10:05:00Z"),
      { ...expectedContext, serviceStartTimeTicks: 655 },
    ),
    /owner_outcomes_invalid/,
  );
});

test("live identity uniqueness is derived from the authenticated API fields", () => {
  const identity = {
    state: "verified",
    provider_key: "codex",
    email: "Owner@Example.invalid",
    provider_organization: "Workspace One",
  };
  assert.equal(
    liveIdentityDigestV1(identity),
    liveIdentityDigestV1({ ...identity, email: "owner@example.invalid" }),
  );
  assert.notEqual(
    liveIdentityDigestV1(identity),
    liveIdentityDigestV1({ ...identity, email: "other@example.invalid" }),
  );
  assert.throws(
    () => liveIdentityDigestV1({ ...identity, state: "unresolved", email: null }),
    /codex_live_identity_invalid/,
  );
});

test("Codex provenance is exact and experimental", () => {
  assert.equal(isExactCodexProvenanceV1(provenance), true);
  for (const [key, value] of [["provider_version", "0.161.0"], ["adapter_version", "1.0.0"], ["is_experimental", false]]) {
    assert.equal(isExactCodexProvenanceV1({ ...provenance, [key]: value }), false);
  }
});

test("service inventory binds the running process to the clean revision", () => {
  const expected = "a".repeat(40);
  const inventory = {
    source_revision: {
      value: expected,
      availability: "available",
      source: "build_manifest",
    },
  };
  assert.equal(isExactServiceRevisionV1(inventory, expected), true);
  for (const changed of [
    { value: "b".repeat(40) },
    { availability: "unknown" },
    { availability: { state: "available" } },
    { source: "application_manifest" },
  ]) {
    assert.equal(isExactServiceRevisionV1({
      source_revision: { ...inventory.source_revision, ...changed },
    }, expected), false);
  }
  assert.equal(isExactServiceRevisionV1(inventory, "not-a-revision"), false);
});

test("fresh Codex lineage binds run windows and matching history", () => {
  const candidate = {
    accountId: "account-one",
    identity: { account_id: "account-one", collection_run_id: "run-new", state: "verified", provider_key: "codex", provider_version: "0.160.0", identity_source_id: "codex.app-server.account-read.v2", profile_protection: "managed" },
    run: { run_id: "run-new", account_id: "account-one", provider_key: "codex", capability_id: "subscription.quota", state: "succeeded", outcome_code: "succeeded", error_code: null, source_id: provenance.source_id, adapter_version: "1.0.2", provider_version: "0.160.0", requested_at: "2026-10-07T10:00:01Z", completed_at: "2026-10-07T10:00:02Z", observation_ids: ["observation-one"] },
    windows: [{ window_key: "codex:primary", subject: { account_id: "account-one", provider_key: "codex" }, freshness: "fresh", collection_run_id: "run-new", current_observation_id: "observation-one", remaining_ratio: remainingRatio, provenance }],
    history: { availability: { state: "available" }, items: [{ subject: { account_id: "account-one", provider_key: "codex" }, collection_run_id: "run-new", observation_id: "observation-one", window_key: "codex:primary", completeness: "complete", value: remainingRatio, provenance }] },
  };
  assert.equal(isFreshCodexLineageV1(candidate, "2026-10-07T10:00:00Z"), true);
  assert.equal(isFreshCodexLineageV1({ ...candidate, run: { ...candidate.run, provider_version: "0.161.0" } }, "2026-10-07T10:00:00Z"), false);
  assert.equal(isFreshCodexLineageV1({ ...candidate, identity: { ...candidate.identity, state: "unresolved" } }, "2026-10-07T10:00:00Z"), false);
  assert.equal(isFreshCodexLineageV1({ ...candidate, run: { ...candidate.run, provider_key: "claude" } }, "2026-10-07T10:00:00Z"), false);
  assert.equal(isFreshCodexLineageV1({ ...candidate, run: { ...candidate.run, capability_id: "identity.verification" } }, "2026-10-07T10:00:00Z"), false);
  assert.equal(isFreshCodexLineageV1({ ...candidate, windows: [{ ...candidate.windows[0], remaining_ratio: { ...remainingRatio, availability: "unknown", value: null } }] }, "2026-10-07T10:00:00Z"), false);
  assert.equal(isFreshCodexLineageV1({ ...candidate, history: { ...candidate.history, items: [{ ...candidate.history.items[0], value: { ...remainingRatio, value: { coefficient: "75", scale: 2, unit: "ratio" } } }] } }, "2026-10-07T10:00:00Z"), false);
  assert.equal(isFreshCodexLineageV1({ ...candidate, history: { ...candidate.history, items: [] } }, "2026-10-07T10:00:00Z"), false);
});

test("Codex quota windows require exact whole percentages and unique keys", () => {
  const window = {
    window_key: "codex:primary",
    semantic_role: "primary",
    allowance: { remaining_percentage: remainingRatio },
    remaining_ratio: remainingRatio,
    reset_at: "2026-10-07T12:00:00Z",
    reset_precision: "exact",
    current_observation_id: "observation-one",
  };
  assert.deepEqual(normalizeCodexQuotaWindowsV1([window]), [{
    windowKey: "codex:primary",
    semanticRole: "primary",
    remainingPercent: 76,
    resetEpoch: 1_791_374_400,
    resetPrecision: "exact",
    currentObservationId: "observation-one",
  }]);
  for (const invalid of [
    [{ ...window, allowance: { remaining_percentage: {
      ...remainingRatio,
      value: { coefficient: "185", scale: 3, unit: "ratio" },
    } } }],
    [window, { ...window }],
    [{ ...window, reset_at: null }],
    [{ ...window, semantic_role: "" }],
  ]) {
    assert.throws(
      () => normalizeCodexQuotaWindowsV1(invalid),
      /codex_quota_window_invalid/,
    );
  }
});

test("Linux proc stat parsing binds PID, parent PID, and start identity", () => {
  const stat = ["S", "42", ...Array(17).fill("0"), "9876"].join(" ");
  assert.deepEqual(parseLinuxProcStatV1(`123 (codex worker) ${stat}\n`, 123), {
    pid: 123,
    parentPid: 42,
    startTimeTicks: 9876,
  });
  assert.throws(
    () => parseLinuxProcStatV1(`124 (codex worker) ${stat}\n`, 123),
    /codex_proc_stat_invalid/,
  );
  assert.throws(
    () => parseLinuxProcStatV1(`123 (codex worker) ${stat}${" ".repeat(16_384)}`, 123),
    /codex_proc_stat_invalid/,
  );
});

test("Codex executable identity follows the Linux selector fingerprint", () => {
  assert.equal(
    executableIdentity,
    "ac2ef2126f3cf5f77d1b4ab430b576c5db14a77a78944682bc424db9cbd5fb19",
  );
  assert.equal(
    executableIdentity,
    codexExecutableIdentityDigestV1({ ...executableMetadata }),
  );
  for (const invalid of [
    { ...executableMetadata, fileType: "40960" },
    { ...executableMetadata, inode: "0" },
    { ...executableMetadata, sizeBytes: "0289101384" },
    { ...executableMetadata, extra: "not-closed" },
  ]) {
    assert.throws(
      () => codexExecutableIdentityDigestV1(invalid),
      /codex_executable_identity_invalid/,
    );
  }
});

test("every representative process is independently bound to the admitted executable", () => {
  assert.equal(provenProcesses.length, 5);
  assert.ok(provenProcesses.every(item =>
    item.independent_executable_identity === executableIdentity));
  for (const invalidProofs of [
    processProofs.slice(0, 4),
    processProofs.map((proof, index) => index === 0
      ? { ...proof, executableIdentityAfter: digest("e") } : proof),
    processProofs.map((proof, index) => index === 0
      ? { ...proof, startTimeTicks: proof.startTimeTicks + 1 } : proof),
    processProofs.map((proof, index) => index === 1
      ? { ...proof, pid: processProofs[0].pid } : proof),
    processProofs.map((proof, index) => index === 0
      ? { ...proof, workingDirectoryAfter: "/home/owner/other" } : proof),
  ]) {
    assert.throws(
      () => bindIndependentCodexExecutableProofsV1(
        processes,
        invalidProofs,
        executableIdentity,
        { ownerRoot },
      ),
      /independent_codex_process_proof_required/,
    );
  }
});

test("public registry digest covers all fields with canonical record ordering", () => {
  const registry = {
    accounts: [
      { account_id: "account-two", nested: { z: 2, a: 1 } },
      { account_id: "account-one", friendly_name: "One" },
    ],
    organizations: [{ organization_id: "org-one", name: "One" }],
    installations: [
      { provider_installation_id: "install-two", provider_key: "claude" },
      { provider_installation_id: "install-one", provider_key: "codex" },
    ],
  };
  const reordered = {
    installations: [...registry.installations].reverse(),
    organizations: registry.organizations,
    accounts: [
      { friendly_name: "One", account_id: "account-one" },
      { nested: { a: 1, z: 2 }, account_id: "account-two" },
    ],
  };
  assert.equal(publicRegistryDigestV1(registry), publicRegistryDigestV1(reordered));
  assert.notEqual(
    publicRegistryDigestV1(registry),
    publicRegistryDigestV1({
      ...registry,
      accounts: registry.accounts.map((item, index) => index === 0
        ? { ...item, extra_public_field: true } : item),
    }),
  );
});

test("representative Codex processes form a unique acyclic forest", () => {
  const scope = digest("f");
  const forest = processes.map((item, index) => ({
    ...item,
    platform_scope_id: scope,
    pid: 1000 + index,
    parent_pid: index === 0 ? 500 : 999 + index,
    start_time_ticks: 2000 + index,
  }));
  assert.equal(selectRepresentativeCodexProcessesV1(forest, { ownerRoot }).length, 5);
  for (const invalid of [
    forest.map((item, index) => index === 1
      ? { ...item, pid: forest[0].pid, start_time_ticks: forest[0].start_time_ticks }
      : item),
    forest.map((item, index) => index === 1
      ? { ...item, parent_pid: item.pid }
      : item),
    forest.map((item, index) => index === 1
      ? { ...item, start_time_ticks: forest[0].start_time_ticks - 1 }
      : item),
    forest.map((item, index) => index === 0
      ? { ...item, parent_pid: forest[1].pid, start_time_ticks: 2000 }
      : index === 1
        ? { ...item, parent_pid: forest[0].pid, start_time_ticks: 2000 }
        : item),
  ]) {
    assert.throws(
      () => selectRepresentativeCodexProcessesV1(invalid, { ownerRoot }),
      /representative_codex_processes_required/,
    );
  }
});

test("managed collection children and unknown locations cannot satisfy agent count", () => {
  assert.throws(
    () => selectRepresentativeCodexProcessesV1(processes),
    /representative_codex_processes_required/,
  );
  for (const excludedLocation of [
    null,
    ownerRoot,
    `${ownerRoot}/profiles/codex/account-one`,
    `${ownerRoot}/profiles/codex/account-one/../account-two`,
  ]) {
    const candidates = processes.map((item, index) => index === 4
      ? { ...item, working_directory: excludedLocation } : item);
    assert.throws(
      () => selectRepresentativeCodexProcessesV1(candidates, { ownerRoot }),
      /representative_codex_processes_required/,
    );
  }
});

test("witness selects five or six exact real Codex processes and emits digests only", () => {
  const selected = selectRepresentativeCodexProcessesV1([
    ...provenProcesses,
    { ...provenProcesses[0], pid: 2000, start_time_ticks: 3000, platform_scope_id: digest("6"), association_key: digest("a") },
    { ...provenProcesses[1], pid: 2001, start_time_ticks: 3001, platform_scope_id: digest("7"), association_key: digest("b") },
  ].reverse(), { ownerRoot });
  assert.equal(selected.length, 6);
  assert.deepEqual(selected.map(item => item.pid), [1000, 1001, 1002, 1003, 1004, 2000]);
  const result = buildCodexWitnessV1(outcomes, records, provenProcesses, {
    event: "m5_codex_witness",
    registryDigest: digest("a"),
    serviceRevision,
    providerHealth: "healthy",
    processScanTruncated: true,
    ownerRoot,
  });
  assert.equal(result.account_count, 4);
  assert.equal(result.verified_count, 2);
  assert.equal(result.owner_unavailable_count, 2);
  assert.equal(result.process_count, 5);
  assert.equal(result.process_scan_truncated, true);
  assert.equal(result.service_revision, serviceRevision);
  assert.match(result.process_set_digest, /^[0-9a-f]{64}$/);
  assert.match(result.quota_value_set_digest, /^[0-9a-f]{64}$/);
  assert.match(result.history_value_set_digest, /^[0-9a-f]{64}$/);
  assert.doesNotMatch(JSON.stringify(result), /Private|account-one|\/home\/owner/);
  const laterRuns = records.map((record, index) => ({
    ...record,
    collectionRunId: `later-run-${index}`,
  }));
  const laterResult = buildCodexWitnessV1(outcomes, laterRuns, provenProcesses, {
    event: "m5_codex_witness",
    registryDigest: digest("a"),
    serviceRevision,
    ownerRoot,
  });
  assert.notEqual(result.collection_run_set_digest, laterResult.collection_run_set_digest);
  assert.equal(result.quota_value_set_digest, laterResult.quota_value_set_digest);
  assert.equal(result.history_value_set_digest, laterResult.history_value_set_digest);
  const laterObservation = buildCodexWitnessV1(outcomes, [
    {
      ...records[0],
      quotaWindows: records[0].quotaWindows.map((window, index) => index === 0
        ? { ...window, currentObservationId: "observation-later" } : window),
    },
    records[1],
  ], provenProcesses, {
    event: "m5_codex_witness",
    registryDigest: digest("a"),
    serviceRevision,
    ownerRoot,
  });
  assert.notEqual(result.history_value_set_digest,
    laterObservation.history_value_set_digest);
  for (const invalidWindows of [
    [{ ...records[0].quotaWindows[0], remainingPercent: 18.5 }],
    [records[0].quotaWindows[0], { ...records[0].quotaWindows[0] }],
    [{ ...records[0].quotaWindows[0], resetPrecision: "approximate" }],
  ]) {
    assert.throws(
      () => buildCodexWitnessV1(outcomes, [
        { ...records[0], quotaWindows: invalidWindows },
        records[1],
      ], provenProcesses, {
        event: "m5_codex_witness", registryDigest: digest("a"), serviceRevision,
        ownerRoot,
      }),
      /codex_witness_invalid/,
    );
  }
  assert.throws(
    () => buildCodexWitnessV1(outcomes, [
      records[0],
      { ...records[1], liveIdentityDigest: records[0].liveIdentityDigest },
    ], provenProcesses, {
      event: "m5_codex_witness", registryDigest: digest("a"), serviceRevision,
      ownerRoot,
    }),
    /codex_witness_invalid/,
  );
  assert.throws(
    () => buildCodexWitnessV1(outcomes, records, provenProcesses.slice(0, 4), {
      event: "m5_codex_witness", registryDigest: digest("a"), serviceRevision,
      ownerRoot,
    }),
    /representative_codex_processes_required/,
  );
  assert.throws(
    () => buildCodexWitnessV1(outcomes, records, processes, {
      event: "m5_codex_witness", registryDigest: digest("a"), serviceRevision,
      ownerRoot,
    }),
    /codex_witness_invalid/,
  );
  assert.throws(
    () => buildCodexWitnessV1(outcomes, records, provenProcesses, {
      event: "m5_codex_witness", registryDigest: digest("a"),
      serviceRevision: "not-a-revision",
      ownerRoot,
    }),
    /codex_witness_invalid/,
  );
});
