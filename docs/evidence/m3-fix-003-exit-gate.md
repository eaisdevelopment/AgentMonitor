# M3-FIX-003 — fresh same-account M3 exit gate

- Audit finding: `M3-003`
- Requirements: M3 Task 6 completion rule; `AC-TEST-003/004/006`
- Modules/contracts: integration automation consuming published M02/M04/M05/M06
  V1 contracts; no contract version changed
- Status: local policy Green; the canonical gate fails closed before provider I/O
  while the refreshed M0 handoff remains blocked.

## Red

The catalog tests were added before the routine existed:

```text
python3 -m unittest \
  tools.automation.test_run.AutomationRoutineTests.test_m3_exit_gate_is_distinct_and_cataloged_fail_closed \
  tools.automation.test_run.AutomationRoutineTests.test_real_catalog_defines_every_mandatory_routine -v

FAILED: AUTO-M3-EXIT was absent (KeyError and missing mandatory routine).
```

A real subprocess-boundary regression then proved that the first implementation
discarded the owner's normal terminal environment:

```text
python3 -m unittest \
  tools.automation.test_run.AutomationRoutineTests.test_m3_exit_child_commands_preserve_the_owner_terminal_environment -v

ERROR: M3ExitErrorV1: m3_exit_required_gate_failed
```

The audit then required the exit gate to reject a stale registry claim after
runtime collection. Its test was written before the gate hook and failed for
the expected missing production function:

```text
python3 -m unittest \
  tools.automation.test_run.AutomationRoutineTests.test_m3_exit_runs_the_real_identity_evidence_check_after_runtime -v

ImportError: cannot import name 'identity_evidence_check' from 'auto_m3_exit'
```

## Green

The exit routine now:

1. validates the current digest-bound M0 live handoff before provider I/O;
2. collects a fresh owner-account quota observation;
3. opens an owner-terminal Claude OTLP session and requires a fresh committed
   runtime observation;
4. reruns the real read-only M02/M06 identity-evidence test against that owner
   database and rejects a stale or detached fingerprint claim;
5. rejects stale timestamps, non-UTC evidence, empty/deduplicated lineage,
   failed runtime state, wrong source, or account mismatch;
6. validates the authenticated production browser against that exact account;
7. runs the mutation, test, quality, build, documentation, and Git-preflight
   gates.

Child commands inherit the normal owner terminal environment without reading,
printing, recording, or filtering arbitrary values in AgentMonitor. Only the
fixed AgentMonitor data-root/account selectors are injected into the isolated
browser child.

```text
python3 -m unittest \
  tools.automation.test_run.AutomationRoutineTests.test_m3_exit_child_commands_preserve_the_owner_terminal_environment \
  tools.automation.test_run.AutomationRoutineTests.test_m3_exit_runs_the_real_identity_evidence_check_after_runtime \
  tools.automation.test_run.AutomationRoutineTests.test_m3_exit_lineage_rejects_non_utc_gate_time -v

OK (3 tests)
```

The canonical live command is:

```text
python3 tools/automation/run.py AUTO-M3-EXIT
```

Until that command returns zero with fresh owner-countersigned evidence, the M3
live exit remains Not Run/Blocked. `AUTO-M3-LIVE` remains a separate read-only
browser/replay diagnostic and cannot satisfy the exit gate.

Current fail-closed result:

```text
python3 tools/automation/run.py AUTO-M3-EXIT
M3 EXIT: FAILED — m3_exit_m0_handoff_not_authorized
exit 1
```

## Impact

- Security/privacy: no new secret transport, logs, or retained provider values.
- Provider/process state: only the approved owner-terminal read-only launch;
  no running process is killed, restarted, interrupted, routed, or switched.
- Migration/API/UI/license: none.
- Automation: adds the fail-closed `AUTO-M3-EXIT` routine.
