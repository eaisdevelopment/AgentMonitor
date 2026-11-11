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

## Registry metadata/API slice integration

The next T003 increment adds `registry_metadata` to technical execution and as
an explicit partial lane. It selects the actual account-intent, connection
metadata and enrollment-HTTP tests:

- `backend/tests/integration/registry/test_billing_account_intent.py`
- `backend/tests/integration/registry/test_billing_connections.py`
- `backend/tests/integration/api/test_billing_enrollment_http.py`

This is a subdivision of the existing T002 registry requirement, not an added
acceptance condition. The full `registry_http` check remains Not Run until the
credential/setup flow has its required evidence. A metadata slice pass cannot
close that check. No provider access, credential setup or identity proof is
claimed by account metadata saved in real isolated SQLite/HTTP tests.

Red: the existing canonical execution test failed because the real command had
no `M7 CHECK registry_metadata:` outcome. After wiring, the direct partial lane
reported Not Run and exit 3 while the connection test file had not landed. Missing
files are no longer described as an executed check; the lane overall is Blocked.
No missing test was silently omitted and no absent file was treated as Green.
The new pure scope-policy assertion confirms metadata success plus unexecuted
full registry flow cannot close the technical gate.

Initial quality: eight pure command-policy tests Passed; Ruff formatting/lint
and strict mypy Passed.

Once all three selected files existed, actual `--lane registry_metadata`
execution returned Failed (exit 1): eight tests passed and three failed in
11.45 seconds. The observed gaps were the missing billing metadata table,
missing billing metadata repository and enrollment status HTTP 503 rather than
200 while that implementation was in progress. Existing test files therefore
did not turn the slice green. These results are real migration/SQLite/HTTP
execution, with no provider request or deployed-service change. A fresh run is
required after the owning implementation lands.

The complete command-regression suite then passed: nine tests in 34.889 seconds,
including actual `AUTO-M7-TEST` execution and explicit preservation of remaining
Not Run boundaries. This command-regression pass does not override the registry
slice's failed implementation results above.

## Nonsecret billing binding lifecycle selection

After M02 metadata implementation landed, the unchanged three-file metadata lane
passed 25 tests in 49.35 seconds during the independent bounded review. That
supersedes the earlier implementation Red for this slice only.

The existing `registry_metadata` selection now also includes
`backend/tests/integration/registry/test_billing_credential_binding.py`. Its real
isolated registry checks cover opaque binding references, reservation/finalization
metadata and archive/lock behavior. No secret entry, credential activation,
provider access or full registry setup is claimed. The lane's explanatory text
now states this scope explicitly. Full `registry_http` remains Not Run; no new
command, acceptance condition or framework was introduced.

Actual execution of the expanded lane passed **33 tests in 89.13 seconds**,
exit 0. Its final result explicitly reads: registry metadata and nonsecret
binding lifecycle only; no secret entry, activation or provider access claim.
The temporary development-tool context exited and cleaned its owned links before
root's subsequent build. Ruff formatting/lint passed for the runner change;
no further test/build helper was started by this agent after the lane completed.
