# M7 billing connection metadata evidence

- Evidence ID: M7-REG-BILL-2026-11-11.
- Date/recorder: 2026-11-11, delegated M02 persistence implementer.
- Scope: T002 metadata get/create slice, approved focused execution plan 1.1.0;
  [implementation authority](m7-implementation-authority-2026-11-11.md).
- Requirements: FR-ACC-001, FR-BUDGET-001, NFR-DATA-001; acceptance contribution
  M7-A01, AC-V1-004, AC-TEST-001/002. This is not acceptance of those full criteria.
- Contract: consumes additive CTR-REG-014 1.0.0; preserves CTR-REG-005 resource
  lifecycle and existing registry account/receipt/event contracts.
- Checkout: `m7-api-budgets`, base `6a8763068cc28c2856e7de45d76e06aa5c30858f`
  with this increment uncommitted during verification.

## Behavior and boundaries

`SqliteBillingConnectionRepositoryV1` implements the billing metadata port.
An eligible pending or active Claude/Codex account may receive one connection.
Creation uses `BEGIN IMMEDIATE` to persist the resource, billing metadata,
registry revision, sanitized change/outbox event and existing-format command
receipt atomically. The account row, subscription identity and monitoring state
remain unchanged. Reads use one SQLite snapshot. Replay reads persisted status;
a changed scope/account/version with the same principal and command key conflicts.
Distinct commands cannot add a second connection, including concurrent requests.

The resource is `api_organization`, lifecycle `active` meaning it exists in the
registry. Its billing connection remains `pending`, monitoring disabled. There
are no linked profiles, provider fingerprints or verification timestamps. A
supplied scope is owner-asserted; absent scope is unresolved. Neither is provider
identity evidence. Resource events carry opaque IDs and revisions, never scope.
Missing accounts return `None`. Archived/disabled accounts and unsupported
providers are ineligible. Ollama returns `existing_cloud_connection_required`;
this slice creates no Ollama resource or key and does not implement cloud reuse.

The pure eligibility decision lives in
`backend/src/agentmonitor/modules/registry/domain/billing_connection.py`, moved
there after review to keep policy out of the SQLite adapter. It contains no
provider access behavior or I/O.

## Red, Green and refactor

Before adding the migration or repository, ran from the worktree:

```text
/home/dev/Nextcloud/Code/AI/AgentMonitor/backend/.venv/bin/pytest -q backend/tests/integration/registry/test_billing_connections.py
```

First real SQLite Red: **1 failed**, with
`AssertionError: billing metadata table is missing`; the complete admitted
migration chain at v1_0730 created no `reg_billing_connection` columns.
The subsequent new-capability Red was **2 failed**: the same schema failure and
`AssertionError: billing metadata repository is missing` from an owned-module
availability assertion. No empty implementation shell or deliberately broken
production implementation was introduced. The availability assertion establishes
the missing seam; it does not claim an individual pre-existing arithmetic or
transaction behavior regressed. Transaction assertions were written before the
repository implementation, then run against the real admitted database.

The initial implemented suite found **4 failed, 12 passed**: the new resource
incorrectly used `pending`, which CTR-REG-005 does not accept. The existing
`list_account_resources` failed with `registry_repository_unavailable`.
Corrected resource lifecycle to `active`, retained pending/disabled billing,
and asserted absent provider identity/verification/profile links. Focused Green:
**16 passed in 21.57s**, exit 0.

After extracting pure policy and replacing the historical availability probe
with ordinary static imports, ran:

```text
/home/dev/Nextcloud/Code/AI/AgentMonitor/backend/.venv/bin/pytest -q backend/tests/integration/registry/test_billing_connections.py backend/tests/integration/registry/test_billing_account_intent.py backend/tests/integration/registry/test_registry_persistence.py
```

Result: **27 passed in 28.27s**, exit 0, no skips. This covers fresh physical
schema, legacy intent/account behavior and registry persistence alongside:

| Scenario | Boundary and evidence |
|---|---|
| M7-REG-BILL-001 | Real migrated file contains billing metadata table |
| M7-REG-BILL-003 | Claude/Codex normal account CRUD; null/asserted scope; create/reopen/replay; subscription preservation; real resource compatibility; sanitized event; FK/integrity checks |
| M7-REG-BILL-004 | Missing account, stale account version, changed-scope retry and duplicate connection reject without durable count/revision changes |
| M7-REG-BILL-005 | Actual archived account and Ollama account reject without writes |
| M7-REG-BILL-006 | Two threads with separate real SQLite connections serialize duplicate and distinct commands into one connection/revision/event/receipt |
| M7-REG-BILL-007 | Real SQLite enforces resource/account binding, scope consistency, monitoring and positive version/generation constraints |
| Pure eligibility | Six no-I/O constructed policy cases, including active/disabled/unsupported states, without invented persisted provider identity |

Ruff check and format check pass for adapter, domain policy, migration and test
files. From `backend/`, strict typing passes for adapter, domain and test:

```text
MYPYPATH=src /home/dev/Nextcloud/Code/AI/AgentMonitor/backend/.venv/bin/mypy --strict --explicit-package-bases src/agentmonitor/adapters/persistence/registry/sqlite/billing_connections.py src/agentmonitor/modules/registry/domain/billing_connection.py tests/integration/registry/test_billing_connections.py
```

Result: `Success: no issues found in 3 source files`. An initial typing invocation
without `--explicit-package-bases` failed module discovery; it was setup failure,
not behavioral Red. All final commands above exited 0.

## Migration, privacy and handoff

New migration `v1_0731_m02_billing_connections.py`, parent `v1_0730`, adds only
`reg_billing_connection`, with unique account and composite account/resource FK,
positive generation/version/revision and scope/lifecycle/monitoring checks.
Its finalized SHA256 is
`03cee77d6b3beca1d545227b72dca0cb7c027e7c3dca8d2c5e48f0c3bfde83ee`.
No earlier migration changed. Root owns catalog/schema admission and updated the
closed registry table inventory; the passing tests used that admitted chain.
Production migration/backup/restore/deployment are **Not Run** in this slice.
Existing-database backup remains required by migration metadata; downgrade is
unsupported and recovery uses verified restore or a forward fix.

Owned files: the migration, SQLite `billing_connections.py`, domain
`billing_connection.py` (additional path authorized during review), integration
`test_billing_connections.py`, and this evidence record. Shared contracts,
composition, HTTP handlers, migration admission and inventory changes are root
work and not attributed to this subagent.

No dependency or license change. No credentials, arbitrary environment/profile
reads, provider calls, telemetry, service operations or real owner account
mutations occurred. Tests use production account commands in isolated real
SQLite files; the pure policy inputs have no I/O. No mock, fake, stub, emulator,
recorded provider response, seeded telemetry or test-only production branch was
used. Events and receipts retain only allowed technical fields; raw scope stays
in owner metadata and is represented by a digest in request fingerprints.

HTTP/browser/provider/live credential verification, disconnect/rotation,
Ollama reuse, operational migration/restore and the canonical full M7 gate remain
outside this evidence and **Not Run by this implementer**. Root independently
owns integration verification. T002 and M7 remain in progress; these results
establish only the bounded metadata persistence slice.
