# M7 executable commands: initial implementation evidence

- Status: Intermediate; T003 is not complete and M7 is not complete.
- Scope: execution plan 1.1.0, T003; integration-owned engineering commands.
- Requirements: FR-BUDGET-001/004, AC-TEST-001/006, M7-A10.
- Authority: [owner implementation instruction](m7-implementation-authority-2026-11-11.md).
- Contracts: internal automation CLI/result only; no product/API/schema contract change.

## Change

`tools/automation/implementations/auto_m7.py` is one bounded lane runner. It
executes the explicitly selected current pure test files through the admitted
backend Python and existing `pytest_no_skip` policy. Missing files fail closed;
pytest failure, no collected tests, skip/xfail and timeout cannot become a pass.
The existing temporary tool environment exposes already installed development
tools and removes only links it created. No dependency is added.

The `pure` lane is expressly partial. The technical lane names its required
registry HTTP, persistence, collection, budget HTTP, compatibility and mutation
boundaries. Live, built-browser and deployment lanes name their required
boundaries. They remain Not Run until actual executable checks are connected.
The exit lane evaluates these four lanes in the same invocation. It neither
reads a manually supplied pass receipt nor uses ticket status as evidence.

The frozen `CheckResult` / `LaneResult` values carry scope, status and safe reason
codes. Their pure completion policy rejects empty/missing, duplicate, foreign,
failed or unexecuted evidence. A complete pure result cannot close technical or
exit scope. These values are not publication or owner acceptance records.

No deployed service, provider, account, profile or credential was read or changed.
There is no new migration, dependency, license impact or telemetry artifact.

## Red evidence

Before implementation:

```text
python3 tools/automation/run.py AUTO-M7-TEST
AUTO-M7-TEST: BLOCKED
- M7-T003 technical runner and approved contract tests
exit 3
```

The real-checkout test
`M7CanonicalExecutionTests.test_canonical_technical_command_reports_executed_and_missing_boundaries`
then failed with the expected assertion: `M7 CHECK pure:` was absent from the
canonical command output. That demonstrated a catalog placeholder where the
new behavior requires executed checks and explicit remaining boundaries.
No missing dependency, credential or simulated provider was used as Red.

## Verification

- `python3 -m unittest tools.automation.test_m7_commands.M7CompletionPolicyTests`:
  seven pure policy tests Passed. Constructed inputs remain entirely within
  the no-I/O completion policy; they are not live/provider evidence.
- Ruff format/check on the two Python files: Passed.
- Direct `python3 -m tools.automation.implementations.auto_m7 --lane exit`:
  Blocked, exit 3, with all unimplemented boundaries Not Run.
- Initial pure command: Blocked, exit 3, while the root-owned report-selection
  suite was not yet present. No partial subset was silently accepted instead.

After root wired the five canonical commands:

- `python3 -m unittest tools.automation.test_m7_commands`: Passed, eight tests,
  including the actual canonical technical command. Its output now evaluates
  named boundaries instead of stopping at a catalog placeholder. The initial
  test's extra prose-string assertion was removed because actual execution and
  missing-boundary outcomes are the behavior being verified.
- `python3 tools/automation/run.py AUTO-M7-TEST`: Blocked, exit 3, correctly
  reporting the still-missing report-selection suite and unimplemented technical
  boundaries. This is truthful command behavior, not a passing technical gate.
- `mypy --strict --follow-imports=silent tools/automation/implementations/auto_m7.py`:
  Passed.
- `AUTO-DOCS-CHECK`: Passed, 324 Markdown files at execution.

T003 remains open until the complete real checks required by the approved plan
are implemented and exercised.

## Integration handoff

Root owns `tools/automation/routines.toml`. Commands use
`python3 -m tools.automation.implementations.auto_m7 --lane <lane>`:
TEST → `technical`, LIVE → `live`, BROWSER → `browser`, DEPLOY → `deploy`,
EXIT → `exit`. Initially catalog statuses are `operational_limited`, describing
unimplemented boundaries explicitly. No dispatcher change is necessary.

As each approved ticket lands, connect its actual tests to the existing named
boundary and preserve red/green evidence. Do not equate file existence with a
passing check. Before final closure, replace every required Not Run result with
an actual real-boundary execution; conditional source limitations retain the
approved plan's separate status rules. Keep normal owner acceptance separate.
