# M7 budget receipt and storage foundation

Status: intermediate T004/T005/T007 work, under approved focused plan 1.1.0 and
M05 increment 0.3.0. Requirements FR-BUDGET-002/004, FR-COL-004/008;
AC-TEST-001/003, M7-A02/A06/A09. Root owns shared contracts/migration.
Successful real report commits, financial UI and M7 acceptance remain open.

## Contracts and storage

CTR-COL-006 2.0.0 adds BudgetCollectionReceiptV1, BudgetCollectionCommitStatusV1
and BudgetCollectionCommitPortV1 beside unchanged quota types. Receipts require
an actual report ID but permit zero facts. Missing identity, malformed digests,
invalid generations, duplicate facts and inconsistent commit status are rejected.
CTR-CAP-004 2.1.0 adds BudgetCollectionInputV1; CTR-CAP-006 2.0.0 adds bounded
BudgetReportHistoryQueryV1. BudgetReportRepositoryV1 publishes commit/status,
account-bound get and bounded history. These interfaces grant no provider access;
M02's real transaction fence and M04's admission/reconciliation remain necessary.

Additive v1_0732 follows setup v1_0731. Two new tables store immutable report
coverage/context and signed cost measures, reusing existing receipt, provenance,
budget observation and usage structures. Signed coefficients preserve 78 digits
and 18-scale precision; negative values require adjustment kind. Empty coverage needs no
invented facts. SQLite's non-reused report sequence pins history pagination.
Normalized typed report JSON is bounded to 16 MiB, full safe typed provenance to
64 KiB; neither is a raw provider response archive. Catalog/schema digests pin
the actual artifacts; all old migration bytes and schema branches remain intact.

This schema is not installed. The service remains 7e252b8/schema0731; the second
rollout still requires its planned migration/recovery verification. No new
dependency, license, credential custody or breaking wire change/ADR.

## Verification

- Receipt capability discovery initially failed 9 tests. With basic records
  present, 9 behavioral tests still failed DID NOT RAISE ValueError for invalid
  acknowledgement/identity states. Validation made them pass. Three out-of-bound
  history limits likewise failed before validation. Contract/report regression:
  **23 passed**.
- Fresh real SQLite initially lacked both required tables (expected failure).
  New fresh schema, actual 0731-to-0732 upgrade and existing capacity schema checks:
  **6 passed**, no seeded accounts or financial observations.
- One test initially inspected after a WAL reader and correctly received locked.
  Quiescent inspection now precedes that reader; no lock/policy was weakened.
- Existing runner initially rejected persistence_schema with exit2. Its new
  scoped selection executes the 6 tests and passes with empty-schema-only scope:

```sh
PYTHONPATH=backend/src:. /home/dev/Nextcloud/Code/AI/AgentMonitor/backend/.venv/bin/python -m tools.automation.implementations.auto_m7 --lane persistence_schema
```

- Broader migration/runtime/contract regression: 60 passed, one failed on stale
  M6 inventory expectations (39 revisions/head0720). Its explicit inventory now
  includes the three actual M7 migrations (42 revisions/head0732); that case then passed.
- Scoped Ruff and strict typing passed. Independent bounded review found no
  required correction in migration/catalog, signed measures, schema branches or
  additive receipt/history types.

M05 codec/repository work is separate. Actual successful commit, replay/conflict,
receipt recovery, source comparison and API/browser money proof are Not Run
until a genuine report and production fence are connected. No constructed
report crossed an I/O boundary. No owner state, provider profile or installed
database was changed by these tests. Full gates and T005 remain open.
