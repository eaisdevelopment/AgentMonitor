# M7 selected-controller admission — partial operational evidence

Date: 2026-11-11. Scope: existing T003/T014 setup deployment, supporting
M7-A01/M7-A07/M7-A10 and AC-TEST-001/AC-TEST-006. Owner: integration/operations.
This is a wrapper increment, not installed activation, recovery acceptance or
M7 completion. No published module contract changes.

## Changed behavior

The cutover, current-schema update and current-update recovery wrappers accept
one optional `--expected-revision=<40 lowercase hexadecimal SHA>` argument.
That explicitly selects the wrapper's own checkout, not an arbitrary service,
data root, executable or environment. Its actual Git state and exact revision
are checked before runtime admission, across runtime re-execution, and again
immediately before calling the operation. Existing runtime/executable hashes,
inherited revision fence and installed-target checks remain in place.

No-argument calls retain the fixed legacy source selection. Unknown flags,
additional flags and malformed or mismatching revisions remain blocked. The
existing checkout checker retains its limited untracked tooling-symlink
exception; downstream candidate sealing performs its own clean-source checks.

Selected cutover/update calls pass `candidate=_ROOT` and
`expected_revision=revision` to the root-owned engine. Recovery still takes no
engine target arguments: the actual releases come from its private journal.
The flag is preserved in runtime `execve` arguments.

## Red/Green

Test file: `tools/automation/tests/test_m7_selected_controller.py`.
It creates real isolated Git clones, installs only the actual current wrapper
source into each clone, commits that source with local command configuration,
and invokes real Git admission. It does not replace runtime collaborators.
Rejected CLI cases run actual subprocesses; accepted cases call only admission,
never the operation entry point.

Command:

```sh
/home/dev/Nextcloud/Code/AI/AgentMonitor/backend/.venv/bin/python -m pytest tools/automation/tests/test_m7_selected_controller.py -q --tb=short
```

- Initial missing helper discovery: 12 failed / 9 passed; not treated as the
  behavioral Red.
- After extracting the original admission policy without changing its allowed
  selections: **9 failed / 12 passed**. Exact-revision admission was refused
  with `operator_arguments_invalid`; mismatch/dirty cases did not reach their
  expected checks. This is the behavioral Red.
- After adding the scoped admission: **21 passed** (9.67 seconds).
- Ruff check: passed for the three wrappers and focused test file. Formatting
  applied only to those owned files.

## Operational boundary and recovery

No installed service, provider, account, credential, process or database was
changed or read by this work. Real installed activation, accepted runtime
re-execution and journal recovery remain Not Run here. No secret/environment
file was opened. No dependency, license or schema change.

The deployment owner must retain the exact clean controller checkout and record
its SHA and recovery invocation before stopping the service. The SHA option
checks identity; it does not make a writable development directory immutable.
A retained sealed controller is preferred. Reuse the same controller/catalog
for recovery; an older M6 controller may misclassify the M7 migration journal.
Post-start rollback restrictions remain unchanged.

Root owns the engine changes, canonical command wiring and real activation/
recovery acceptance. This increment does not claim either schema transition
or public deployment passed.

## Files

- `tools/automation/implementations/auto_m6_cutover.py`
- `tools/automation/implementations/auto_m6_current_update.py`
- `tools/automation/implementations/auto_m6_recover_current_update.py`
- `tools/automation/tests/test_m7_selected_controller.py`
- This evidence record.

## Follow-up: preserve actionable CLI rejection

The existing real CLI regression caught an overly generic message after this
increment: `--target example` correctly returned 3 but omitted its established
`no target arguments are accepted` explanation. Reproduced behavioral Red:
**1 failed** in `test_recovery_command_is_cataloged_and_rejects_target_arguments`.
An initial invocation without `PYTHONPATH` failed test collection; it is not Red.

The three wrappers now map only known admission reasons to fixed public text:
unknown/extra/malformed arguments, legacy wrong checkout, and expected-revision
mismatch. Other failures keep the generic safe message; exception text is not
printed. Dedicated rejected-CLI assertions now require the established text.

```sh
PYTHONPATH=backend/src:. /home/dev/Nextcloud/Code/AI/AgentMonitor/backend/.venv/bin/python -m pytest tools/automation/tests/test_m7_selected_controller.py tools/automation/tests/test_m6_cutover.py::test_recovery_command_is_cataloged_and_rejects_target_arguments -q --tb=short
```

Green: **22 passed** (8.34 seconds); Ruff passed. Previously passing real recovery
cases were not repeated. No accepted installed-service action was run.
