# M3 runtime commit-recovery correction

Status: Passed for the scoped M04/M06 crash-recovery correction on 2026-09-23.

## Scope

- Requirements/scenarios: `FR-COL-005`, `FR-COL-008`, `AC-OPS-005`,
  `M04-DB-019`, `M04-DB-026`.
- Contracts: no public contract or schema version changed. The internal M04
  repository port gained a bounded query for durable `committing` runs.
- Safety: recovery atomically reclaims only an expired lease whose owner
  heartbeat is stale, assigns a recovery scheduler and strictly newer fence,
  then queries the real M06 commit-status port and finalizes through normal
  fenced M04 transitions. It does not invoke procfs or a provider.

## Red / Green

Red command:

```text
PYTHONPATH=backend/src backend/.venv/bin/python -m pytest backend/tests/integration/collection_control/test_linux_runtime_recovery.py -q --tb=short
```

Expected Red: import failed because
`recover_pending_linux_runtime_commits` did not exist.

The independent concurrency review produced a second meaningful Red: an
unexpired active run was finalized and expired recovery retained fencing token
`1`. Both assertions failed before atomic reclaim was implemented.

Green result: `6 passed`. The real file-backed SQLite tests prove that an
absent M06 receipt closes the run as `collection_commit_interrupted`, releases
the lease, preserves conservative dispatched-budget accounting, leaves active
and recently heartbeating owners untouched, atomically gives exactly one of two
concurrent claimants a fresh bounded lease and newer fence, rejects the old
fence, drains only a bounded batch, and runs before any new runtime admission.

M04 integration result: `18 passed, 2 skipped`; the skips are the two explicit
owner live opt-ins and remain Not Run. Ruff check/format, strict mypy, and the
module-boundary check passed.

## Impact

- Migration/dependency/license/API/UI impact: none.
- Privacy/security: no provider content, process content, credentials, or owner
  database was read or changed by this verification.
- Live provider and owner-database verification: Not Run; neither is required
  to prove database-only recovery and the root integration run owns the later
  live collection check.
