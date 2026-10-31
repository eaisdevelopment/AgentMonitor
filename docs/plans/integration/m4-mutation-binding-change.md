# Change plan: refresh the reviewed runtime mutation binding

- Status: **Approved for this bounded foundation correction**.
- Plan version: `1.0.0`; reviewed 2026-09-29 by root integration.
- Owner: PLAN-FND automation; parent [foundation plan](../foundation/plan-v1.md).
- Authority: the active owner-authorized objective is fully implement M4 goals.
- Requirements: `NFR-TEST-001/002`, `NFR-COMP-001`; acceptance `AC-TEST-005`.
- Contracts: existing `CTR-RUN-004/005/007` and `CTR-CAP-003` V1.
- Target: V1-M4 local quality prerequisites, without changing M3 acceptance.

## Outcome and scope

The existing mutation gate executes against the current approved additive
runtime contract. Only its full-file supporting contract digest changes.
All exact equivalent-mutant hashes, selectors and fail-closed verdict rules
remain in force. Allowed files are the mutation runner, its real-checkout
regression in `tools/automation/test_run.py`, and this evidence/plan.
No provider, application, database, API, dependency or account changes.

## Review and contract impact

The pinned baseline is commit `6b1edfc`, contract SHA-256
`4b8cbead227bcf6b37ee75188fc04a42f086464e2d8c26589011f456371318f2`.
The current contract SHA-256 is
`0733bf799efeaa6d047e2dbf51e3ba79ca309feb39a69b2a17a18b1cf8826ecc`.
Root inspected the complete diff from that baseline: an additional
`QueryAvailabilityV1` import and appended owner-association/live-location
records. The existing correlation, stall and input validation declarations
are unchanged. All three mutated policy files are byte-unchanged from that
baseline. The seven previously reviewed equivalent mutants therefore retain
their supporting invariants; the real mutation run must still verify their
exact rendered hashes. Future drift continues to fail closed.

## Test-first evidence and completion

Existing regression provides Red before the runner changes:

```text
python3 -m unittest tools.automation.test_run.AutomationRoutineTests.test_mutation_equivalence_is_bound_to_contract_invariants
2026-09-29: exit 1, AssertionError: False is not true
```

Green requires the same test to accept this reviewed checkout and reject an
altered contract. The canonical verification is:

```bash
python3 tools/automation/run.py AUTO-MUTATION
```

Record actual counts, exact equivalents and all non-killed classes. A failed,
blocked or unavailable mutation run remains so; refreshing the digest alone
does not pass mutation acceptance or M4. Static/diff checks finish this scope.

The first canonical run exposed an additional runner defect: its baseline
pytest invocation relies on caller `PYTHONPATH`, so the clean caller fails
with `ModuleNotFoundError: No module named 'agentmonitor'`. Root approves
making the selected baseline command self-contained through an explicit
checkout source argument, preserving every test selector. The new real
subprocess regression `test_mutation_baseline_runs_without_caller_pythonpath`
first failed with the expected missing `baseline_policy_command` import.
Its Green must run the complete selected pure suite with a minimal environment
and no caller source path. This runner defect is not a policy mutation failure.

## Privacy, operations and rollback

The existing private copied workspace contains only selected checkout source
and pure tests, no owner data or provider profiles. No new dependencies,
licenses, persistence or migration impact. Rollback restores the previous
runner, which correctly blocks on the current contract. Stop if a supporting
invariant changed or an unreviewed/non-equivalent survivor appears; investigate
the actual policy/test rather than expanding the equivalent list blindly.
