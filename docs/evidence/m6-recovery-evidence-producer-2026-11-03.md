# M6 exact recovery and sampled continuity producer — 2026-11-03

Status: candidate implementation; natural recovery positive scenario Not Run.
No M6 completion claim. Root integration retains rollout and canonical exit.

Requirements: FR-COL-003..008, M6-A07, AC-LIVE-007, AC-OPS-003.
Modules/contracts: M04 and integration; additive CTR-COL-012 1.0.0, existing
CTR-COL-008 1.1.0, CTR-REG-012 1.1.0 and versioned operations API unchanged.
Contract review: root integration steward accepted the
[impact assessment](../plans/integration/m6-recovery-evidence-contract-impact.md)
and its exact-source and bounded sampled-continuity semantics.

## Red / green evidence

- Before the contract/domain adapter existed, the pure and actual repository
  tests failed collection with the expected missing-module errors. After the
  implementation, the initial suite passed 19 tests using genuine retained
  M04 history for its sole SQLite boundary.
- `test_recovery_counts_without_actual_interval_are_not_evidence` initially
  failed because positive summary counts made M6-A07 `passed` without actual
  interval evidence. The new producer envelope is now required by the gate.
- `test_query_rejects_mixed_provider_scope_before_io` initially failed with
  `DID NOT RAISE`; the pure contract now rejects a mismatched provider scope.
- Independent review found that the durable `provider_unavailable` shape could
  also represent a local failure after an HTTP 200 response because CTR-COL-012
  carries no HTTP status. The pure regression
  `test_provider_unavailable_without_durable_http_status_is_not_natural`
  failed by returning that ambiguous run as natural. After the minimum policy
  correction, the complete pure recovery-policy file passed **24 tests in
  0.06 seconds**. The corrected policy excludes the ambiguous state;
  authoritative 401, 403 and 429 outcomes remain eligible.
- A second review regression proved that `failure -> committed success -> later
  failure` was still reported as recovered. It failed by returning the earlier
  success. The corrected pure policy requires the latest exact-scope terminal
  state to be the committed success, and the interval producer rebuilds the
  recovered set on every sample. The producer now also rechecks the exact
  service identity after all positive-supporting database reads and immediately
  before publication. The recovery/direct/gate pure suite passed **74 tests in
  0.43 seconds**.
- M6-A07 and the integrated Story now carry the machine-readable
  `sampled_dashboard_and_collection_continuity` limitation. One Claude and one
  Codex run cover the sampled interval for every recovered Ollama target; the
  target count is not presented as a distinct provider-account or agent count.
- The closed artifact parser initially failed collection because its module did
  not exist. Its tests now reject absent invocation identity, incorrect
  revisions, old/overlong intervals, incomplete sample/count evidence and
  positive counts attached to a Not Run result.
- Combined command: `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=backend/src
  backend/.venv/bin/python -B -m pytest
  tools/automation/test_m6_direct_evidence.py
  tools/automation/test_m6_recovery_evidence.py
  tools/automation/test_m6_exit.py
  backend/tests/collection_control/domain/test_recovery_evidence.py
  backend/tests/live/ollama/test_recovery_query.py -q`:
  **73 passed**. The checkout used the workstation's existing backend venv.
- Strict mypy with the project config, `MYPYPATH=backend/src` and
  `--explicit-package-bases` passed the three new backend production files.
- The canonical consumer invoked the actual producer through its fixed argv and
  tool environment, parsed the resulting real Not Run envelope, and retained
  its closed reason code. AUTO-PLAN-CHECK and AUTO-DOCS-CHECK passed; focused
  Ruff checks passed. No overall AUTO-M6-EXIT pass is claimed.

## Actual read-only observations

At 13:13:25 UTC the new browser probe passed against the running built dashboard
revision `9ac684ce062810d5bc1b1ed719e7460d6b37f395`. It created and closed only
its own browser page, inspected real navigation and the versioned revision
endpoint, and disconnected from the shared browser. No provider was called.

The real interval command returned exit 3 / `not_run` in approximately 35 ms:
`m6_recovery_current_natural_failure_absent`. It did not wait for a hypothetical
failure. This is not a passing M6-A07 result. Historical pre-dispatch fixes and
failures from other source fingerprints were not reclassified as natural
provider recovery. A separate actual read-only query found Codex history but no
Claude terminal quota run in the preceding hour; future positive continuity
requires both providers to have genuine successful quota runs in the observed
interval.

After the independent corrections, the same read-only command against running
revision `22d572c102f9684f38feaa1af4d99d7008c5d405` again returned exit 3 /
`not_run` with `m6_recovery_current_natural_failure_absent` in under one second.
It performed no provider request or write. The positive final-identity and
latest-success publication path remains **Not Run** until a qualifying natural
condition exists.

The maximum observation budget is 600 seconds, with a 660-second canonical
subprocess-group deadline. Only the owned evidence subprocesses may be stopped;
no shared browser or monitored agent process is targeted. Positive evidence
preserves the service invocation/revision, each actual dashboard sample time,
opaque failure/recovery and Claude/Codex run references, and exact-lineage digest.
It proves sampled availability, not continuous availability between samples.

## Security, migration and delivery limits

No provider call, profile, credential, application-state or live database write
was performed. No dependency, schema migration or API route was added. No
emails, organization names, balances, model responses or secret values enter
the artifact. The new SQLite port reads only M04-owned allowlisted tables with
a bounded deadline; automation uses existing public M02 query ports.

Production changes are in the M04 contract/domain/read adapter and the canonical
M6 gate/producer/browser probe. Tests, contract baseline/adoption, gate catalog,
scoped audit notes and this evidence accompany them. Integration must regenerate
combined planning controls after merging concurrent schema0718 work. A genuine
current-invocation exact-source failure followed by scheduled recovery and real
Claude/Codex/dashboard interval observations remains required for M6-A07.
