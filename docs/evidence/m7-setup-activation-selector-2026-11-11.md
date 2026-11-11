# M7 initial setup activation selector — partial implementation evidence

Date: 2026-11-11. Existing T003/T014 scoped setup increment; supporting
M7-A01/M7-A07/M7-A10, AC-TEST-001/AC-TEST-006. Owner: integration/operations.
No new command ID, dependency, schema or public module contract. This does not
close T014, full deploy, exit or M7.

## Scope and invocation

The existing `auto_m7` runner accepts `--lane deploy --check setup_activation`
with an explicit expected revision. It admits only its own actual clean sealed
checkout under the existing fixed retained-release directory. No target unit,
data-root, environment or arbitrary checkout selector is accepted.

Operator invocation, from that retained controller's working directory:

```sh
PYTHONPATH=backend/src:. /home/dev/.local/share/agentmonitor/releases/m6-runtime-2fedf0809fc9/bin/python -B -m tools.automation.implementations.auto_m7 --lane deploy --check setup_activation --expected-revision=COMMITTED_40_CHARACTER_SHA
```

`COMMITTED_40_CHARACTER_SHA` must be replaced with the exact recorded clean
controller commit after this work is committed and retained. This evidence does
not pretend the current uncommitted source has an executable release SHA. Root
records the actual retained directory, SHA and recovery commands before use.
The flag must not be derived afresh from a mutable checkout during recovery.

This selector is only the initial `0720 → 0731` setup activation. It refuses
other installed-source/catalog combinations; later full dashboard activation
still requires its separately planned migration admission. A repeat invocation
following successful activation is not a general resume/recovery command.

## Operational ordering

1. Verify exact Git revision, canonical path, fixed retained-release location,
   seal/build and initial schema selection before any installed action.
2. Invoke existing pinned cutover wrapper with the expected revision. Existing
   fixed service/runtime checks, locks, migration backup and journal remain
   authoritative; no alternate upgrader or recovery engine is introduced.
3. Wait up to 20 seconds for existing readiness helper to verify exact installed
   cwd/revision, process identity, schema, owned loopback listener and login page.
4. Invoke existing finalizer immediately and recheck runtime. Restore the prior
   restart policy before optional help/LAN probes can fail.
5. Run the installed billing credential operator with `--help` only, verify its
   account/resource/data-root options, check the approved LAN login page, then
   recheck installed runtime. Login availability is not authenticated workflow
   proof or remote-client firewall evidence.

Child commands use the fixed private Python runtime and a minimal code-owned
process environment. No credentials are read or forwarded. Command output is
never printed; only exact allowlisted wrapper messages become fixed diagnostic
codes. Unknown or additional output remains a generic closed failure. Cutover
and finalizer have bounded subprocess deadlines; an interrupted/failed operation
requires journal-aware review, never automatic rollback after candidate start.

Individual completed operational checks are reported separately. Even when all
succeed, the selector returns intermediate exit 3 with `authenticated_setup`,
`collector_continuity` and `backup_recovery` **Not Run** in this invocation.
Those proofs must come from their real separate checks. Full deploy/exit required
checks were not weakened or replaced by this partial result.

## Tests and Red/Green

New file: `tools/automation/tests/test_m7_setup_selector.py`.
Pure tests cover selection and incomplete-evidence policy. Real tests use actual
Git clones and rejected subprocess invocations; there are no mocked collaborators,
provider payloads or accepted installed activations.

- Initial helper discovery: 5 failed / 4 passed (missing functions; not treated as
  behavioral Red).
- Actual CLI behavioral Red: valid scoped arguments failed with exit 2,
  `unrecognized arguments: --check setup_activation --expected-revision=...`;
  test expected admission to controller preflight and closed exit 3.
- Closed-reason pure Red: expected cutover journal-review code, received generic
  `m7_setup_command_failed` (1 failed).
- Green combined selection, existing completion-policy and aggregation coverage:
  **36 passed, 2 subtests passed** (2.92 seconds, final rerun).
- Ruff and diff whitespace checks passed.

Command:

```sh
PYTHONPATH=backend/src:. /home/dev/Nextcloud/Code/AI/AgentMonitor/backend/.venv/bin/python -m pytest -c backend/pyproject.toml tools/automation/tests/test_m7_setup_selector.py tools/automation/test_m7_commands.py::M7CompletionPolicyTests backend/tests/capacity/pure/test_budget_aggregation.py -q --tb=short
```

The real CLI rejection test runs current actual runner source committed into an
isolated clean clone outside fixed releases, ensuring it cannot reach accepted
activation even after future repository commits. Pure aggregation tests were
also added to existing `PURE_TARGETS`; their implementation belongs to M05.
No temporary toolchain helper was invoked.

## Remaining verification and impact

Accepted initial rollout, runtime re-execution, actual installed help/LAN,
authenticated setup and continuity are **Not Run by this subtask**. Root performs
and records those against the final sealed revision. Previous recovery evidence
is not fabricated as execution by this selector. No installed state, provider,
user profile, account, credential, environment file or database was changed by
these tests. No license, dependency or migration change.

Changed files:

- `tools/automation/implementations/auto_m7.py`
- `tools/automation/tests/test_m7_setup_selector.py`
- This evidence record.
