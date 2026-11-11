# M7 billing credential binding eligibility evidence

- Evidence ID: M7-REG-CRED-2026-11-11; recorder: delegated M02 implementer.
- Authority: approved T002 bounded extension under focused M7 execution plan 1.1.0,
  [implementation authority](m7-implementation-authority-2026-11-11.md).
- Requirements: FR-ACC-001, FR-BUDGET-001, NFR-DATA-001; acceptance contributions
  M7-A01 and AC-TEST-001/002. Full T002/M7 acceptance is not asserted.
- Contracts: unchanged CTR-REG-011 1.0.0 binding/lock shapes; consumes existing
  CTR-REG-014 1.0.0 billing metadata. No new contract or migration.
- Checkout: `m7-api-budgets`, base `6a8763068cc28c2856e7de45d76e06aa5c30858f`,
  working changes uncommitted at verification, 2026-11-11.

## Implemented boundary

The existing credential repository accepts Claude/Codex accounts only when their
persisted billing connection is pending or active. The new M02-local transaction
predicate checks the actual account/provider and billing metadata together.
Ollama's existing eligibility remains unchanged. Nonbilling Claude/Codex account
reads and prepare operations still reject without creating binding metadata.

Account archive now takes the existing credential lock for all three supported
provider account types, before the archive transaction. Lock acquisition does
not depend on an earlier billing lookup, avoiding a gap where enrollment could
begin between that lookup and archive. Inside the write transaction, billing
eligibility is checked again before retiring pending/active bindings, advancing
the generation fence and archiving the account atomically. Subscription-only
accounts still archive normally without binding rows. No additional lock scheme
or provider/default-profile access was introduced.

Archived account cleanup metadata remains readable, while another prepare is
rejected. The tests intentionally leave pending references at `cleanup_pending`:
no stored key, activation, deletion or cleanup-complete proof was manufactured.
Ollama access-target, monitoring-target and verification functions are unchanged.
Billing verification/monitoring authority remains later integration work.

## Red and Green

Before production edits, ran:

```text
/home/dev/Nextcloud/Code/AI/AgentMonitor/backend/.venv/bin/pytest -q backend/tests/integration/registry/test_billing_credential_binding.py
```

**Red: 4 failed, 4 passed in 29.45s**, exit 1. Both Claude/Codex tests created
accounts and billing metadata through production commands in real isolated
SQLite files, then failed on binding read with
`credential_binding_account_unavailable`. Both corresponding archive-lock tests
failed with `DID NOT RAISE ValueError`: archive ignored the held credential lock.
Ollama and nonbilling rejection regressions already passed. These were actual
behavioral failures, not absent imports or setup errors.

After the minimal repository/guard changes, the same command produced
**8 passed in 25.20s**, exit 0, no skips.

| Test ID | Real boundary verified |
|---|---|
| M7-REG-CRED-001 | Three providers: normal account creation, billing metadata where required, empty binding read, prepare/reopen, unchanged subscription/profile metadata, archive to cleanup pending, generation advancement, and post-archive prepare rejection |
| M7-REG-CRED-002 | Kernel account lock excludes archive through a separate descriptor; account remains unchanged while locked and archive succeeds after release |
| M7-REG-CRED-003 | Both subscription-only providers reject read/prepare, retain no binding rows, and can still archive |

Profiles inspected by these assertions are only empty registry metadata in the
new isolated database. No filesystem provider profile or owner account was read.

## Refactor and checks

Ruff import ordering was normalized in the two touched production files. Ruff
check and format check passed for those files and the new integration test.
`git diff --check` passed for the scoped changes.

Post-refactor adjacent regression command:

```text
/home/dev/Nextcloud/Code/AI/AgentMonitor/backend/.venv/bin/pytest -q backend/tests/integration/registry/test_billing_credential_binding.py backend/tests/integration/registry/test_billing_connections.py backend/tests/integration/registry/test_registry_persistence.py backend/tests/registry/test_credential_binding_policy.py backend/tests/registry/test_credential_lock_process.py backend/tests/persistence/sqlite/migrations/test_m02_credential_bindings.py
```

Result: **44 passed in 91.24s**, exit 0, no skips. This re-exercises new
eligibility/archive behavior together with billing metadata, existing registry
persistence, pure binding transitions, real process locks and the physical
credential-binding schema.

From `backend/`:

```text
MYPYPATH=src /home/dev/Nextcloud/Code/AI/AgentMonitor/backend/.venv/bin/mypy --strict --explicit-package-bases src/agentmonitor/adapters/persistence/registry/sqlite/credential_bindings.py src/agentmonitor/adapters/persistence/registry/sqlite/repository.py tests/integration/registry/test_billing_credential_binding.py
```

Result: `Success: no issues found in 3 source files`, exit 0.

## Integrity and remaining work

Changed files are the two M02 SQLite repositories above,
`backend/tests/integration/registry/test_billing_credential_binding.py`, and this
evidence record. No shared contract, prior migration, dependency or license
change. No service operation, actual owner account mutation, environment/profile
read, key value, provider call, mocked boundary, seeded credential/telemetry,
activation claim or cleanup-complete claim occurred. All account/billing/binding
rows were produced by normal application/repository commands against isolated
real SQLite.

Credential entry, physical storage, rotation, actual deletion, provider access,
verification, HTTP/browser credential status and canonical full M7 acceptance
are **Not Run** here. Owner-entered real credentials remain necessary for their
positive end-to-end evidence; this increment proves metadata eligibility and
archive fencing only. T002 and M7 remain in progress.
