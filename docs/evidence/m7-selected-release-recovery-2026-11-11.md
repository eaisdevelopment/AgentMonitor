# M7 selected release and schema recovery increment

Status: intermediate T003/T014 implementation; not installed activation or M7
completion. Requirements FR-BUDGET-001/004; AC-OPS-003, AC-TEST-001/006;
M7-A10. Owner: root integration. Public product contracts and schema versions
are unchanged by this increment; the existing schema head remains `v1_0731`.

## Change and reason

The guarded cutover/update previously prepared a fixed M6 source checkout.
They now accept only an optional candidate/expected-revision pair for source
selection. Service, data root, credential file and executable remain fixed.
Selection checks an absolute canonical path, clean Git state and the exact
revision before entering the installed transition. Retention repeats the
expected-revision check before creating release files, then retains its existing
clone/build/seal/revalidation behavior. Candidate schema still must match the
controller. Omitted arguments preserve the legacy selection.

The preparation routine passes its expected revision through to retention.
The three operator wrappers separately admit their own selected clean checkout
and preserve its SHA through runtime re-execution; see the
[controller evidence](m7-selected-controller-admission-2026-11-11.md).
Deployment/recovery must execute from the retained clean controller, not rely
on an editable development directory remaining unchanged.

## Red and Green

New tests use actual Git clones and parent revisions from this checkout, the
existing real frontend toolchain, and private temporary storage. They never
invoke an accepted activation against the installed service.

```
PYTHONPATH=backend/src:. /home/dev/Nextcloud/Code/AI/AgentMonitor/backend/.venv/bin/python -m pytest -c backend/pyproject.toml tools/automation/tests/test_m7_selected_release.py -q --tb=short
```

Initial Red: three tests failed because `prepare_candidate_release()` rejected
the new `expected_revision` keyword. Two public-entry tests separately failed
because `cutover()` and `update_current_schema()` rejected `candidate`.
These failures exposed missing selected-source admission, not failed provider
access. After implementation, five tests passed. The additional actual clean,
dirty and incomplete-pair selection test plus existing preparation suite gave
**10 passed in 30.10 seconds**:

```
PYTHONPATH=backend/src:. /home/dev/Nextcloud/Code/AI/AgentMonitor/backend/.venv/bin/python -m pytest -c backend/pyproject.toml tools/automation/tests/test_m7_selected_release.py tools/automation/tests/test_m7_setup_activation.py -q --tb=short
```

The true sealed build in this run came from `716cf923ef1598e02edcf007279c7bf0812498e1`.
The controller's new selection code ran from the current worktree. This is not
evidence that uncommitted changes existed in that sealed candidate.

## Actual recovery tests

The old disposable-service test's predecessor table lacked the current schema.
It now admits `0731 → 0720`. The public entry-point guard now permits code/SHA
selection only, retaining its prohibition on arbitrary service/data targets.

Run the following with `AGENTMONITOR_TEST_CANDIDATE` set to the actual sealed
candidate produced above, and `PYTHONPATH=backend/src:.`:

```
/home/dev/Nextcloud/Code/AI/AgentMonitor/backend/.venv/bin/python -m pytest -c backend/pyproject.toml tools/automation/tests/test_m6_cutover.py -k 'public_cutover or recovery_command or (disposable and (normal or restore_restart or candidate_finalize or migration_crash or candidate_attempt_recovery or override_installed_restore))' -q --tb=short
```

Result: **14 passed, one failed, nine deselected** in 103.78 seconds. All thirteen
selected real disposable-systemd/SQLite cases and the public-scope guard passed.
The failure was the existing CLI assertion requiring the preserved unknown-target
message. The wrappers were corrected; their 21 focused cases plus that actual
CLI regression then passed (22 total). The costly service cases were not rerun
after a diagnostic-text-only correction. Unselected scenarios are not claimed
as passed. The owner-database-copy test was not selected.

The existing no-argument retention test
`test_m6_frontend_build.py::test_retained_candidate_survives_source_checkout_change`
also passed (8.81 seconds), exercising the legacy default and retained build
after its source changed. This provides compatibility evidence beyond the new
explicit-revision tests.

The exercised cases include normal migration, candidate finalization and
process-change rejection, restart-policy restoration, interrupted migration
before/after commit, post-start reconciliation and pre-start override recovery.
They use actual new empty SQLite files and disposable test services. They do
not stop the installed dashboard or interact with owner agents/profiles.

## Impact and remaining work

No dependency, license, secret custody, provider request or account configuration
change. No provider data or keys were used. Ruff passed with the backend config
for the changed retention, cutover, preparation and test files.

T003/T014 still must publish the scoped M7 setup-activation invocation, execute
from a clean retained controller and verify the installed command, authenticated
browser and existing collectors. The later financial schema transition also
needs its own admission/recovery evidence. These tests do not close T014, prove
populated billing persistence, or imply provider access or M7 acceptance.
