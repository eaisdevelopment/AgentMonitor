# M7 current billing report query increment

Date: 2026-11-11. Owner: M05. Status: intermediate implementation and focused
verification; populated provider-report integration remains **Not Run**.
Authority: approved focused execution plan 1.1.0/M05 increment 0.3.0, resumed
root delegation for T005/T010 after the planning pause.

## Scope and contract

Supports FR-BUDGET-002/004, FR-ORG-003, AC-HIST-001, M7-A02/A07 and relevant
AC-TEST-001/005. Consumes root-published CTR-CAP-006 2.1.0:

```python
BudgetCurrentReportsPortV1.get_current_reports(
    BudgetCurrentQueryV1(
        account_id, resource_id, scope_generation, period, as_of, limit=200
    )
) -> QueryCollectionV1[BudgetReportSelectionV1]
```

Each selection has `current` and `latest_attempt` (not `last_attempt`). The
existing internal `BudgetReportSelection` import now aliases the published
immutable DTO; existing selection/aggregation consumers retain that name.
No shared contract, schema, migration, composition or API edit by this agent.

## Behavior

The SQLite query scans **all** matching revisions for exact account, resource,
scope epoch and requested period; both collected and stored timestamps must be
at or before `as_of`. It does not reuse a bounded history page. Window functions
rank metadata by collection time, storage time and report ID, exactly matching
the existing pure selector. Each compatible context independently retains the
latest attempt and latest whole complete report. A complete empty replacement
therefore removes superseded charges even after more than fifty partial polls.
No SQL arithmetic processes financial amounts.

Context includes the full subject/provider/target, scope ID, source/category,
cost basis, grouping and currency; epoch/period are fixed by query predicates.
Credential rotation does not split monetary history. Unknown currency and
unresolved scope stay explicit; no scope proof, currency, balance or zero spend
is inferred. Original coverage, source watermark and timestamps remain intact.

A single SQLite read transaction pins metadata and subsequent body loads.
Only IDs, context metadata and byte lengths are returned by the ranking query,
with at most `limit+1` contexts. Before loading report bodies, the repository
requires at most 200 contexts and 16 MiB of unique normalized report JSON.
The same report used as both current and latest attempt is counted/loaded once.
Bodies are checked against selected IDs/byte lengths/collection timestamps and
query account/resource/epoch/period/as-of, then the existing pure selector
rechecks compatible context and ordering.

Overflow returns **no subtotal** and explicit unavailable query coverage:

- `budget_current_reports_absent`: no matching reports;
- `budget_current_context_limit`: more compatible contexts than the limit;
- `budget_current_byte_limit`: selected unique report bodies exceed 16 MiB;
- `budget_current_query_unavailable`: storage, decoding or metadata mismatch;
- `budget_current_reports_read`: available query result.

The last reason means the requested contexts were read successfully; it does
not certify provider freshness, known currency or a financial total. All
availability timestamps use the supplied `as_of`, not a substituted current
clock. No pagination or partial-prefix subtotal is introduced.

## Red → Green and verification

- Before implementation: combined pure/real-empty run produced **2 failed,
  1 passed**. Pure Red showed the existing internal selection was not the
  published DTO; real migrated empty SQLite Red was `AttributeError` for
  missing `get_current_reports`.
- Bounded ID/byte selection recorded expected missing-helper `ImportError`
  before implementation. The policy deduplicates the exact 16 MiB boundary,
  refuses one additional report, caps references and rejects inconsistent sizes.
- Metadata/body guard recorded expected missing-capability assertion Red before
  implementation. Green covers account/resource/epoch/period/as-of, later
  storage, wrong report ID, byte-count mismatch and collection-time mismatch.
- Pure regressions cover 101 partial attempts following a complete empty
  correction, explicit unknown currency/scope, and collection/storage/report-ID
  tie ordering. Constructed values never cross SQLite or provider I/O.
- Real empty tests use production migration and the published port, prove no
  reports/receipts are invented, verify foreign keys, and distinguish a missing
  database from a successful empty read without creating storage.
- Default pytest discovery initially found a filename collision with the
  root-owned contract test. Renaming the owned pure file to
  `test_budget_current_selection.py` fixed it; no import-mode workaround.

Focused regression command from the worktree root:

```sh
/home/dev/Nextcloud/Code/AI/AgentMonitor/backend/.venv/bin/pytest -q \
  backend/tests/capacity/pure/test_budget_current_selection.py \
  backend/tests/capacity/pure/test_budget_report_selection.py \
  backend/tests/capacity/pure/test_budget_aggregation.py \
  backend/tests/capacity/pure/test_budget_codec.py \
  backend/tests/capacity/pure/test_budget_commit_policy.py \
  backend/tests/capacity/pure/test_budget_history_cursor.py \
  backend/tests/integration/capacity/test_budget_repository_empty.py \
  backend/tests/integration/capacity/test_budget_current_empty.py \
  backend/tests/contracts/test_budget_current_query.py
```

Result: **71 passed in 1.77s**, zero skips, including eight new pure and two new
empty-storage checks. Strict mypy passed for the three owned production and two
owned test files, including structural assignment to the published read port.
Scoped Ruff check and format passed from the worktree root using explicit
`--config backend/pyproject.toml`. Root owns canonical `auto_m7` registration.
This focused evidence is narrower than the full M7 completion gate.

## Consumer handoff and limits

P01/composition must supply the authorized account/resource and current scope
epoch, propagate unavailable coverage, and derive money only through compatible
M05 aggregation. Preserve `current`'s original time and coverage. A newer
unknown-currency report is another context; it cannot make prior monetary
evidence fresh. Failed collection attempts with no stored report require M04
status separately; `latest_attempt` means latest **persisted report** only.

Populated SQL selection with genuine corrections, cross-context/provider data,
concurrent append and populated as-of isolation remain **Not Run**, as does
HTTP/browser presentation. Pure policy plus actual empty SQL execution is not
claimed as that proof. The next real boundary needs genuine reports committed
through M04/M02 fences, followed by query/readback and API projection.

No dependency/license change, provider call, secret/profile access, owner-state
or configuration modification, migration, deployment or commit. No raw provider
payload or seeded financial telemetry. Query bodies contain only existing typed
normalized data. Scope is preserved for root integration review.

## Owned files

- `backend/src/agentmonitor/adapters/persistence/capacity/sqlite/budget_repository.py`
- `backend/src/agentmonitor/adapters/persistence/capacity/sqlite/budget_current_query.py`
- `backend/src/agentmonitor/modules/capacity/domain/budget_reports.py`
- `backend/tests/capacity/pure/test_budget_current_selection.py`
- `backend/tests/integration/capacity/test_budget_current_empty.py`
- `docs/evidence/m7-budget-current-query-2026-11-11.md`
