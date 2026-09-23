# M3 owner-confirmed Claude persistence vertical evidence

- Evidence ID: `M3-OWNER-CONFIRMED-CLAUDE-VERTICAL-2026-09-23`
- Scope: `ST-REG-001`, `ST-OBS-001`, owner-assisted A01 → M02 → M04 → M05
- Requirements: `FR-ACC-005/006`, `FR-COL-004..008`, `FR-QUOTA-001..006`
- Contracts: `CTR-PROV-004/005`, `CTR-REG-002..006`, `CTR-COL-002/004/006`, `CTR-CAP-001/003/004` V1
- Environment: real Claude Code `2.1.278`, Linux x86_64, protected default profile, real migrated file SQLite
- Result: **Passed** for the narrow owner-assisted production persistence flow;
  independent identity discovery and exact opt-in pytest acceptance remain open

## Implemented production path

`ClaudeAdapterV1` now publishes the structural `AccountDiscoveryPortV1` call.
It invokes the admitted real `/usage` source, discards the subscription values
for discovery, and emits one opaque `owner_confirmation_required` candidate.
It neither reads nor claims a provider identity. M02 then uses its published
reconcile, explicit-owner-confirmation, and graph-enrollment ports. The confirmed
M02 account ID—not the pre-confirmation candidate reference—is supplied to the
durably admitted M04 run and the M05 capacity subject.

`agentmonitor.composition.claude_live_monitoring` is the production composition
entry point for a caller-supplied migrated `DatabaseRefV1`. It enforces the
reviewed 300-second interval between the discovery read and quota collection,
admits M04 before the quota provider call, captures completion time after I/O,
and commits through the single M05 sink. Its CLI accepts only an absolute,
owner-approved data root and emits safe internal IDs/counts, never provider
values or identity.

The five former skip-only declarations are executable live assertions covering
the owner-confirmation-required candidate, stale confirmation rejection,
enrollment replay, confirmed-account M04 lineage, and M05 run/observation/
health lineage. They do not contain a constructed discovery outcome, seeded
telemetry, provider recording, response fixture, or direct table insertion.

They are excluded from ordinary `AUTO-TEST` provider I/O by a fail-closed
session fixture. With no opt-in, all five report `NOT RUN`/Skipped before a
database or adapter is opened. The only accepted live selection is the exact
test-only setting `AGENTMONITOR_RUN_CLAUDE_OWNER_VERTICAL=1`; any other supplied
value fails before provider I/O. This prevents a normal regression run from
silently making two provider calls or waiting through the 300-second interval.

## Red and partial Green evidence

The first behavioral Red proved that A01 lacked the required production port:

```text
backend/.venv/bin/python -m pytest \
  backend/tests/integration/registry/test_claude_reconciliation.py -q --tb=short
# 1 failed, 2 skipped in 0.10s
# assert isinstance(adapter, AccountDiscoveryPortV1)
# assert False
```

After implementing the real port, that structural check passed (`1 passed,
2 skipped in 0.09s`). This was only a structural increment and was not reported
as `M02-LIVE-005` completion.

The first complete live command reached the real source and failed before M02:

```text
PYTHONPATH=backend/src backend/.venv/bin/python -m pytest \
  backend/tests/integration/registry/test_claude_reconciliation.py \
  backend/tests/integration/collection_control/test_claude_quota_run.py \
  backend/tests/integration/capacity/test_claude_quota_commit.py \
  -q --tb=short -s
# 5 errors in 30.41s
# safe source code: usage_deadline_incomplete_render
```

After waiting more than the reviewed 300-second interval and adding only safe,
closed parser-reason classification, one authorized retry was executed:

```text
# same combined command
# 5 errors in 30.50s
# safe source code: usage_deadline_window_conflicting_duplicate
```

The retry confirmed a real redraw-history conflict and stopped before registry
reconciliation. No account, collection run, quota observation, projection, or
populated browser state was fabricated. The five executable tests are therefore
**Failed/Blocked at that checkpoint**, not Passed or skipped-as-pass.

After the redraw policy was corrected to select the latest complete label block
while retaining fail-closed conflict checks inside that current block, the
adapter/parser provenance advanced to `1.0.2`. Two additional production
pre-provider defects were found and fixed without issuing the quota call: the
M04 admission now records the truthful `owner_local_operator` authorization and
the manifest fingerprint uses the canonical SHA-256 composition binding.

The final persistent production command then completed against the owner-local
database after its real discovery and enforced 300-second interval:

```text
# exit 0
claude_live_collection_completed
account_id=pmcGwOGaJKUj7UHf5KDuF546_7H7MCPd
collection_run_id=claude-quota-run-9f36f543a366488b8c7d06ce11790df7
quota_window_count=2
```

These are safe AgentMonitor opaque IDs and a count, not provider identity or
quota values. The confirmed M02 account, admitted/finalized M04 run, M05 receipt,
two current quota windows, provenance, and health projection were committed.
The authenticated application then started on loopback `127.0.0.1:43110` over
that same persistent database. No provider response, identity, credential,
prompt, response, source content, or raw quota value was retained in evidence.

## Non-live verification

```text
PYTHONPATH=backend/src backend/.venv/bin/python -m pytest \
  backend/tests/integration/collection_control/test_claude_composition.py -q
# 2 passed in 0.55s

MYPYPATH=backend/src backend/.venv/bin/mypy \
  --config-file backend/pyproject.toml --explicit-package-bases \
  backend/src/agentmonitor/composition/claude_live_monitoring.py \
  backend/src/agentmonitor/adapters/providers/claude/adapter.py \
  backend/src/agentmonitor/modules/provider_system/application/gateway.py \
  backend/src/agentmonitor/modules/registry/application/owner_enrollment.py \
  backend/src/agentmonitor/modules/collection_control/application/runner.py \
  backend/src/agentmonitor/modules/collection_control/application/executor.py
# Success: no issues found in 6 source files

PYTHONPATH=backend/src backend/.venv/bin/python -m pytest \
  backend/tests/foundation/test_contract_boundaries.py -q
# 180 passed in 4.56s

python3 tooling/foundation/check_boundaries.py .
# boundaries: PASS (0 violations)
```

Scoped Ruff lint passed and Ruff format reported the 11 changed source/test
files formatted. No dependency, license, migration, database-schema, or API
shape/compatibility change was introduced. The OpenAPI and generated client
source-hash artifacts were regenerated after the published adapter version
changed.

The default and invalid-selection checks completed without provider I/O:

```text
PYTHONPATH=backend/src backend/.venv/bin/python -m pytest \
  backend/tests/integration/registry/test_claude_reconciliation.py \
  backend/tests/integration/collection_control/test_claude_quota_run.py \
  backend/tests/integration/capacity/test_claude_quota_commit.py \
  -q --tb=short -rs
# 5 skipped in 0.02s; each reason begins `NOT RUN`

AGENTMONITOR_RUN_CLAUDE_OWNER_VERTICAL=yes \
  PYTHONPATH=backend/src backend/.venv/bin/python -m pytest \
  backend/tests/integration/registry/test_claude_reconciliation.py -q --tb=short
# 3 errors in 0.04s; claude_owner_vertical_opt_in_invalid
```

## Authenticated populated browser

The production frontend was rebuilt and served by the authenticated loopback
application over the same persistent database. The dashboard password was read
from the protected local `.env` and piped only to the verifier's standard input;
it was not placed in argv, logs, evidence, or output.

The first real-browser Red exposed a zero-width quota-provenance value at the
required 1920×1080 viewport. Giving that provenance column a bounded minimum
width made the source/version limitation visible inside the horizontal table
region. A second Red exposed an asynchronous navigation race in the verifier;
the verifier now waits for the real `GET /api/v1/collection-runs` response and
the loading state to leave before reconciling IDs.

```text
# Red 1
P02 POPULATED MONITORING: FAILED — quota: quota_source_version_state_not_visible

# Red 2
P02 POPULATED MONITORING: FAILED — collection_run_reconciliation:
# quota_collection_run_not_rendered:0

# Green, real installed Chrome and production build
P02 POPULATED MONITORING: PASSED — real Claude account/quota/collection
# reconciliation; quota source/version BLOCKED — absent from API v1;
# runtime BLOCKED — no same-account session observation
```

The browser proved authenticated rendering of the owner-confirmed Claude
account, all two rendered real quota windows, each exact M05 observation ID,
the matching succeeded M04 collection run, provenance timestamps and versions,
account-filtered runtime query, no external request, no monitoring data in browser
storage, no demo/placeholder label, and no document-level horizontal overflow.

The executed command supplied the credential only through standard input:

```text
printf '%s' "$dashboard_password" | node \
  frontend/tests/browser/p02/populated_monitoring_dashboard.mjs \
  http://127.0.0.1:43110 pmcGwOGaJKUj7UHf5KDuF546_7H7MCPd
```

The two Red outputs and final Green output are retained above, but their exact
wall-clock timestamps were not captured. The callable completion-time correction
also lacks a historical pre-fix Red. These are explicit TDD evidence deviations;
this record does not claim `AC-TEST-001` for those changes. Red-first evidence is
required for later changes.

## Blocked / Not Run

- Independent provider-derived account identity discovery remains Blocked; the
  current lane is explicitly owner-assisted and the manifest declares quota,
  not an independent account-identity source.
- The five-test opt-in pytest batch has not rerun after the final production
  success and remains Not Run on `1.0.2`; the CLI success does not retroactively
  turn its two earlier Red executions into passing tests.
- Same-account runtime correlation remains separately Blocked by Task 5.
- The populated verifier passed when invoked directly, but it is not selected by
  a cataloged M3 live-browser routine. M3 completion automation therefore remains
  absent; the M2-scoped `AUTO-TEST` result must not substitute for it.
- `AUTO-TEST` passed its declared M2 scope: 101 automation tests, 778 backend
  passes, five explicit M3 provider Not Run skips, generated-contract/build
  verification, and all M1/M2 real-Chrome scenarios including the real
  1,800-second idle expiry. Its emitted T5/T6/T7 rows remain Not Run and the
  separate exact M0 G1 gate remains Failed outside that M2 gate.
- `AUTO-QUALITY`, `AUTO-BUILD`, and `AUTO-DOCS-CHECK` passed after the persistent
  run: zero static/boundary/type errors, 22 compatible OpenAPI operations, the
  current generated client, a 33-module production build, and 231 Markdown files.

## Security, privacy, migration, license, and documentation impact

The source remains read-only against the protected default profile. Only the
owner-approved opaque tuple, safe internal IDs, versions, digests, timestamps,
states, and bounded codes are representable in this workflow. No identity,
credential, prompt, response, raw provider value, profile path, arbitrary
environment value, or source content was read into evidence or persisted.
There is no process control, authentication mutation, dependency addition,
schema change, or migration. This evidence documents a passed narrow quota
persistence/browser result while preserving the stated runtime and M0 control
blockers; it does not claim M3 completion.
