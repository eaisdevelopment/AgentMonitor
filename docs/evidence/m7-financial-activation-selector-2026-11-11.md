# M7 selected financial-schema activation

Status: partial T014 implementation under approved focused plan 1.1.0.
Requirements FR-BUDGET-001, AC-OPS-003/006, M7-A09/A10. This increment prepares
and admits the existing operational transition; it does not establish an
installed migration, genuine financial report or complete M7 deployment.

## Fixed transition and reuse

The existing preparation command now accepts `--phase financial`. Its default
setup behavior remains unchanged. Financial preparation requires catalog head
`v1_0733`, builds and seals the exact selected clean checkout, checks the real
credential-operator and billing-worker command interfaces, and rehearses actual
`v1_0731 -> v1_0733` migrations on a newly created empty private SQLite database.
It creates and verifies the existing SQLite backup before migration and verifies
that backup again afterwards. The backup remains `v1_0731`. The existing
migration/cutover policies must admit that exact source; a rejected policy stays
an explicit preparation blocker. No installed database is opened or copied.

`auto_m7 --lane deploy --check financial_activation --expected-revision=<40SHA>`
uses the same sealed-controller check, fixed service/data/runtime, selected
revision cutover, runtime revision/readiness inspection and finalize wrapper as
the setup selector. Its installed precondition is exactly `v1_0731`, candidate
head exactly `v1_0733`. The initial setup selector remains `v1_0720 -> v1_0731`.
There is no arbitrary service, data root, command or account selector.

Restart policy is finalized immediately after exact installed revision and
loopback readiness pass, before optional operator/worker/LAN probes. The actual
runtime is rechecked after finalization and at the end. Existing pinned
controller and journal-based recovery behavior remain unchanged; no new recovery
engine is introduced. An unretained clean development clone cannot activate.

Successful operational checks still produce an intermediate non-success result:
authenticated first report, collector continuity and installed backup/recovery
proof remain separate `Not Run` checks. Neither the selector nor its preparation
artifact can close the full deploy or exit lane.

## Commands

Inactive preparation (absolute paths, fresh workspace and exact committed SHA):

```text
PYTHONPATH=backend/src:. /home/dev/Nextcloud/Code/AI/AgentMonitor/backend/.venv/bin/python -m tools.automation.implementations.m7_setup_activation --phase financial --candidate <absolute-clean-checkout> --expected-revision <40SHA> --workspace <absolute-new-private-workspace> --tool-modules /home/dev/.local/share/agentmonitor/worktrees/dashboard-product-promotion/frontend/node_modules --python-executable /home/dev/Nextcloud/Code/AI/AgentMonitor/backend/.venv/bin/python
```

Later installed operation, **not executed by this increment**: run from that
exact clean revision retained and sealed under the existing fixed releases root,
using the trusted pinned runtime. An arbitrary preparation-workspace release is
not accepted as the installed controller:

```text
PYTHONPATH=backend/src:. /home/dev/.local/share/agentmonitor/releases/m6-runtime-2fedf0809fc9/bin/python -m tools.automation.implementations.auto_m7 --lane deploy --check financial_activation --expected-revision=<40SHA>
```

## Red, Green and limitations

Red: **3 failed in 3.51s**. The existing selector rejected the financial slice;
the actual rehearsal ignored its financial phase and created source `v1_0720`;
an unknown phase was accepted and created a workspace. These were behavioral
assertion failures, not missing dependencies or provider-access failures.

Initial Green with existing selector regression: **14 passed in 4.60s**.
The expanded real candidate/build/storage/legacy regression selection passed:
**21 passed in 35.57s**.

```text
PYTHONPATH=backend/src:. /home/dev/Nextcloud/Code/AI/AgentMonitor/backend/.venv/bin/python -m pytest -q tools/automation/tests/test_m7_financial_activation.py tools/automation/tests/test_m7_setup_selector.py tools/automation/tests/test_m7_setup_activation.py
```

The real retained candidate test uses an isolated Git clone of integration
checkpoint `32b16fc` plus the actual two current operator files committed in
that clone, without mocks or replacement implementations. It verifies the real
frontend build and release seal, credential/worker `--help`, backup/current
schemas, database integrity, empty accounts/reports/runs, private modes, clean
source revision and removal of temporary node-module links. No provider data is
created. Separate tests execute the financial selector from a real clean but
unretained clone and verify refusal before any installed action.

Scoped Ruff, format checks, strict mypy for the two implementation files and
new tests, and whitespace checks passed. Direct backend imports replace two
accidental `m6_cutover` re-exports in the selector for explicit typing; behavior
is unchanged.

**Not Run:** accepted installed financial activation, actual installed restore,
authenticated first financial report/browser projection, continuous scheduled
collection and existing-provider continuity. The prepared clone is isolated test
evidence, not a released project revision or provider success. The full canonical
M7 deploy/exit gates remain open.

## Impact and files

- `tools/automation/implementations/auto_m7.py`
- `tools/automation/implementations/m7_setup_activation.py`
- `tools/automation/tests/test_m7_financial_activation.py`
- This evidence document.

No product/shared contract, schema, dependency, license, generated file, account,
key, default profile, installed service or running agent was changed. The granted
build window was released after all candidate test processes exited; no tool
helper or temporary link remains held. Root owns review, commit, final retained
release and separately authorized installed execution.
