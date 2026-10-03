# M3 safe current-revision gate implementation

- Scope: `AC-M3-006`, `AC-M3-007`; one explicitly selected real Claude account.
- Owners: PLAN-INT integration gate and P02 browser verification. Consumed API
  contracts: M02 account V1, M03 observed identity V1, M04 collection run V1,
  M05 capacity/history V1, M06 runtime V1. No contract or production change.
- Status: implementation verification passed. The canonical clean-revision
  `AUTO-M3-EXIT` run and acceptance decision remain separate evidence.

## Automation behavior

`AUTO-M3-EXIT` now selects the safe current successor. It requires an explicit
existing account selector, the PID of the existing reviewed AgentMonitor
dashboard service, and a visible authenticated loopback Chrome context. It
rejects a dirty checkout, builds that revision, validates and gracefully
preflights the owner-confirmed identity through authenticated GETs, and only
then restarts the existing dashboard with a closed command shape. The Linux
process is held through a pidfd, and the replacement must emit its own closed
exact-origin ready event through a bounded in-memory pipe. A dedicated process
continuously discards later output without retaining it on disk. A failed first
launch is cleaned up and a second validated launch restores the dashboard
before the gate reports failure. The gate then waits for one new scheduled
quota run. It executes `AUTO-M3-TEST`,
`AUTO-QUALITY`, `AUTO-MUTATION`, `AUTO-DOCS-CHECK`, and `AUTO-GIT-PREFLIGHT`
after the browser witness. It creates a privacy-minimized receipt at the fixed
owner-only local path `.agentmonitor-local/m3-current-gate-receipt.json` only
when every required lane passes with no skip; an existing target is rejected.
The replacement service pidfd remains open and is checked immediately before
and after that exclusive receipt write.

The historical gate implementation remains in the repository as historical
evidence but is no longer selected by the automation catalog. The successor
does not directly invoke Claude, discover or enroll a provider profile, write
registry metadata, or control a running agent. Its only lifecycle action is
restarting the existing AgentMonitor dashboard from the clean assessed
revision; the installed scheduler performs the read-only provider collection.

## Red, Green, and refactor evidence

The receipt and canonical-selection tests first failed with:

```text
ModuleNotFoundError: No module named 'tools.automation.implementations.auto_m3_current_exit'
```

After the minimum implementation, the focused suite returned:

```text
PYTHONPATH=backend/src backend/.venv/bin/python -m pytest tools/automation/test_m3_current_exit.py -q --tb=short
3 passed
```

Changing the catalog exposed the previous implementation-path assertion in
the existing automation suite. Its focused run failed on the difference
between `auto_m3_exit.py` and `auto_m3_current_exit.py`; after aligning the
catalog contract with the approved successor, that focused test passed. A
bounded independent review then found that the first receipt writer could
overwrite an arbitrary absolute path and that a stale running service was not
bound to the assessed revision. The expanded tests failed on the missing
private-path and service-restart policies before those behaviors were added:

```text
PYTHONPATH=backend/src backend/.venv/bin/python -m pytest tools/automation/test_m3_current_exit.py -q --tb=short
# exit 2: PRE_BROWSER_ROUTINES import missing
```

The refactored focused checks returned:

```text
PYTHONPATH=backend/src backend/.venv/bin/python -m pytest tools/automation/test_m3_current_exit.py -q --tb=short
# exit 0: 5 passed
python3 -m unittest tools.automation.test_run.AutomationRoutineTests.test_m3_exit_gate_is_distinct_and_cataloged_fail_closed
# exit 0
backend/.venv/bin/ruff check tools/automation/implementations/auto_m3_current_exit.py tools/automation/test_m3_current_exit.py
# exit 0
backend/.venv/bin/ruff format --check tools/automation/implementations/auto_m3_current_exit.py tools/automation/test_m3_current_exit.py
# exit 0
node --check tools/ui/verify_m3_current.mjs
# exit 0
git diff --check
# exit 0
```

A final independent safety review found three remaining false-pass seams: the
readiness capture retained a filesystem name, the replacement pidfd was closed
before receipt creation, and the account registry tuple was compared only
within each browser phase. The new regression tests first failed during
collection with:

```text
ImportError: cannot import name 'start_service_output_drainer_v1'
```

The completed implementation reads only a bounded readiness prefix and then
hands the pipe to a continuous discard process, verifies the same real service
process around receipt creation, and compares a privacy-minimized digest of the
exact selected account metadata across preflight and post-restart witness
phases. The focused suite then returned:

```text
PYTHONPATH=backend/src backend/.venv/bin/python -m pytest tools/automation/test_m3_current_exit.py -q --tb=short
# exit 0: 8 passed
```

The follow-up review found that a drainer-spawn error did not require confirmed
service cleanup before restoration. The real-process cleanup test first failed
with `TypeError: _stop_spawned_service() got an unexpected keyword argument
'graceful_timeout'`. Cleanup now allows the dashboard's 30-second graceful
shutdown, escalates only the gate-owned replacement to `SIGKILL`, confirms its
exit, and forbids a restoration retry when cleanup cannot be proven. The final
focused result was `9 passed`.

## Real browser evidence

The verifier uses an authenticated shared Chrome context at the installed
loopback dashboard. It opens and closes only its own tab. All API requests are
GETs through V1; it performs no provider authentication, profile write,
database checkpoint, or account edit. The canonical wrapper owns the separate
revision-bound dashboard restart described above.

Before that restart, the same verifier's bounded preflight mode returned exit
0 for the selected managed account and proved owner-confirmed registry state,
the exact reported identity, unchanged registry metadata, and zero API
mutations. This prevents an invalid selector from starting scheduled provider
work before eligibility is known.

The first real selected protected-default run returned exit 1:

```text
M3 CURRENT BROWSER: FAILED — current_identity_and_capacity: registered_observed_identity_mismatch
```

The administrator name and currently reported Claude identity differ. This is
a real negative result and remains unresolved for that account. No address or
opaque account identifier is recorded here.

An exact-matching owner-selected managed account first exposed a bounded
history-query error: the 365-day first page held 200 older retained points and
did not contain the current quota observation. Restricting the witness query
to the recent hour made the current observation reachable through the real
API. Waiting for the built page's process read also resolved a transient
loading-state assertion. Before the fresh-run requirement was added, the
selected managed account passed the real browser/API/registry check. That
earlier pass is a development result, not the final `AC-M3-007` witness.

The final verifier snapshots the selected account's current verified run,
waits at most 420 seconds for a different installed-service run requested and
completed after the gate starts, and requires an actual succeeded M04 run with
observation IDs. It reconciles those IDs with M05 current quota windows and
recent history, the M03 identity receipt, and the built account page. It checks
the visible account name, monitoring state, percentage, freshness, source,
precision, confidence, runtime/session count, and linked path or explicit
unreported state. Desktop and 390px mobile views are checked. It compares the
M02 friendly name, organization, record version, and registry revision before
and after, rejects any browser API mutation, and binds a digest of that same
metadata tuple across the preflight and post-restart browser phases.

Focused negative checks after the fresh-run change:

```text
node --check tools/ui/verify_m3_current.mjs
# exit 0

AGENTMONITOR_M3_FRESH_TIMEOUT_SECONDS=1 node tools/ui/verify_m3_current.mjs
# protected default: exit 1, registered_observed_identity_mismatch
# selected managed account: exit 3, fresh_installed_collection_timeout
```

Both live invocations also supplied the required loopback CDP endpoint,
dashboard origin, and selected account ID through environment variables. The
one-second timeout is a focused negative check; it is not a substitute for the
default cadence run. No sensitive values are emitted by the verifier. A PASS
emits privacy-minimized JSON: account and run identifiers are hashed, while
bounded timestamps, availability, counts, and boolean integrity results remain
explicit for the canonical gate receipt.

The default-cadence real Chrome/installed-service run then returned exit 0:

```text
node tools/ui/verify_m3_current.mjs
M3 CURRENT BROWSER: PASSED — selected real account, verified identity and fresh quota lineage, built account/runtime view, unchanged registry
```

The command used the same three explicit environment selectors, without the
one-second override. Its safe JSON receipt recorded one new completed run after
the witness start, `identity_match=true`, `registry_unchanged=true`,
`runtime_state=available`, zero linked current processes, zero current session
records, and `mutations=0`. The UI correctly displayed the unlinked path and
session state. A historic runtime record does not imply a currently running
agent for this selected managed account.

The first clean-revision canonical run then exposed a real restart race. The
new dashboard emitted its exact ready event, but its observed-identity view was
still unavailable when the browser made its first request:

```text
M3 CURRENT BROWSER: FAILED — current_identity_and_capacity: selected_identity_not_verified
M3 CURRENT EXIT: BLOCKED — m3_current_browser_failed
```

The gate returned exit 3 and created no receipt. A read-only follow-up showed
the same view became verified after startup. The verifier now polls that view
inside the existing 420-second deadline and accepts only a collection run whose
request and completion times are both after the post-restart witness started;
it does not accept the persisted pre-restart identity as fresh evidence.

## Impact and outstanding evidence

- Security/privacy: GET-only authenticated V1 browser reads and a
  privacy-minimized receipt; no address, path, raw account ID, raw run ID, or
  observation ID appears in output. The service restart command is parsed from
  the existing owned process, validated against a closed allowlist, and never
  printed.
- Data/migration: no database or API migration. The only output is an
  owner-readable receipt in the fixed local AgentMonitor evidence directory.
- Migration/license: none.
- Live verification: fresh default-cadence browser pass for one selected
  managed account; the protected-default identity mismatch remains a genuine
  failure for that selector.
- Acceptance: the canonical M3 exit, owner interaction/countersignature, and
  historical Red-first disposition remain separate required evidence.

## Files in the implementation increment

- `tools/automation/implementations/auto_m3_current_exit.py`
- `tools/automation/test_m3_current_exit.py`
- `tools/ui/verify_m3_current.mjs`
- `tools/automation/routines.toml`
- `tools/automation/test_run.py`
- `tools/docs/check.py` and `tools/docs/test_check.py`
- `docs/engineering/completion-and-automation-gates.md`
- this evidence record

The documentation validator adds fail-closed support for a future M3 schema
`3.0.0` acceptance record. Its predecessor and receipt digest pins remain
unset until the real gate receipt exists and the owner decisions are recorded.
After review, the real receipt is copied to
`docs/evidence/m3-current-gate-receipt-2026-10-03.json`; the validator binds
that fixed path and its independent SHA rather than trusting a self-reported
digest.
