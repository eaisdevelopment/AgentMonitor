# M7 T005 normalized budget repository increment

Date: 2026-11-11. Owner: M05. Status: intermediate implementation; successful
provider-report persistence and full M7 acceptance remain **Not Run**.
Authority: approved focused M7 plan 1.1.0 and M05 increment 0.3.0; root delegated
this bounded codec/application/repository increment. No installed-state changes.

## Requirement and contract impact

- FR-BUDGET-002/004, FR-HIST-001/002; M7-T005, M7-A02/A09;
  AC-HIST-001, AC-TEST-001..006. This increment supports these requirements;
  it does not establish their complete acceptance.
- Consumes CTR-CAP-002 2.0.0 report/view, CTR-CAP-004 2.1.0 typed commit,
  CTR-CAP-006 2.0.0 history/repository, CTR-COL-006 2.0.0 budget receipt,
  CTR-COMMON-003 exact quantities, CTR-COMMON-004 provenance and
  CTR-COMMON-007 query pages. Existing contracts remain unchanged by this agent.
- Root owns additive migration v1_0732, catalog and admission. The repository
  consumes its report and signed-cost tables, including bounded canonical
  provenance. No prior migration is edited.

## Behavior and integration seam

`budget_codec.py` encodes/decodes only closed typed normalized reports. Exact
coefficient strings and integer scales survive unchanged; UTC timestamps have
canonical microsecond `Z` form. The report codec rejects extra/duplicate JSON
fields, floating numbers, invalid closed values, noncanonical JSON, and payloads
above 16 MiB. Its SHA256 is the envelope `payload_digest`. No raw provider body
has a field. The separate provenance codec preserves all typed availability,
warning, fallback, derivation and input-ID metadata within 65,536 bytes.

`validate_budget_commit` requires `budget.report.v1` and provenance capability
schema `2.0.0`, matching provider/capability/source/collection time and canonical
digest. `succeeded` requires complete full requested coverage; all other valid
reports require `partial`. Operation/correlation identifiers remain independent
lineage and are not equated to run identifiers.

`SqliteBudgetReportRepositoryV1(database_ref, transaction_fence=...)` accepts a
callback with `(sqlalchemy.engine.Connection, BudgetCollectionInputV1) -> None`.
Absent callback permits reads only; commit refuses before database I/O. Each
commit starts `BEGIN IMMEDIATE`, invokes the real M02 callback, then reconciles
or writes. Composition must check actual active binding, target generation,
account/resource and scope epoch through that same transaction. No private
registry tables or optional authorization bypass are used here.

Matching run/capability, target generation, schema, report digest and complete
canonical provenance return the existing receipt. Conflicting input raises a
safe error and leaves prior data unchanged. New report, full provenance,
normalized facts and receipt share one transaction. Zero-fact reports allocate
a report and receipt but no observation IDs, projections or events. Actual
bucket rows receive generated durable IDs; no dummy fact is added. Cost amounts
use the new signed companion table rather than changing nonnegative legacy
budget checks. Usage dimensions and cost dimensions remain recoverable in the
canonical report, without coercion into legacy dimension enums. Definitions
identify reporting spend; they do not assert cash balances or budget limits.

Report retrieval requires account ID. History requires exact account, resource
and requested period. Its cursor binds those selectors, snapshot upper sequence
and last returned sequence. Metadata is fetched before JSON, at most limit+1
rows; pure prefix policy caps materialized report JSON at 16 MiB and returned
reports at 200. A page can therefore contain fewer rows than requested while
advertising more. Append-only reports after the snapshot cannot enter later
pages. Original collection/watermark/coverage remain in returned typed reports.
API signing and mapping of this internal cursor belong to later integration.

## Red, Green and refactor evidence

All constructed report/provenance and cursor vectors are pure: no provider,
SQLite, filesystem or network I/O. Empty-database tests use real isolated
file-backed SQLite and production migration/admission/repository code.

1. `test_budget_codec.py`: expected import Red, `ModuleNotFoundError` for
   `agentmonitor.modules.capacity.domain.budget_codec`, before implementation.
   Initial Green: 9 passed, 0.20s.
2. `test_budget_commit_policy.py`: expected import Red for missing application
   module before implementation. Initial envelope Green: 7 passed (16 combined
   with codec). An initial test-construction error using an invalid
   `FieldAvailabilityV1` signature was corrected; it is not behavioral Red.
3. Full provenance capability assertion: Red 1 failed/7 passed, 0.21s before
   adding codecs, followed by Green. This records actual feature absence,
   not a deliberately broken implementation.
4. Page byte/count policy capability assertion: Red 4 failed/8 deselected,
   0.19s before pure prefix implementation. Vectors cover exact 16 MiB boundary,
   one-row cap, row limit and no rows. Repository consumes this policy.
5. `test_budget_repository_empty.py`: expected missing-repository import Red
   before implementation. Green proves real empty history/report/status reads,
   unchanged zero rows, missing-fence refusal before database creation, and
   malformed-cursor refusal before database opening. Two initial tests used a
   forbidden database basename; correcting them to actual `agentmonitor.db`
   policy is test setup repair, not a production behavioral fix.
6. Cursor regression tests cover retained sequence bounds, cross-account,
   cross-resource and cross-period rejection, and boolean/overflow/invalid
   bounds. Availability probes were replaced with ordinary static imports after
   their recorded Red. Numeric policy cases remain intact.

Focused command, from the worktree root:

```sh
/home/dev/Nextcloud/Code/AI/AgentMonitor/backend/.venv/bin/pytest -q \
  backend/tests/capacity/pure/test_budget_codec.py \
  backend/tests/capacity/pure/test_budget_commit_policy.py \
  backend/tests/capacity/pure/test_budget_history_cursor.py \
  backend/tests/integration/capacity/test_budget_repository_empty.py \
  backend/tests/integration/capacity/test_budget_report_schema.py \
  backend/tests/contracts/test_budget_commit_contract.py
```

Result: **48 passed in 2.18s**, zero skips: owned 31 pure + 3 real empty-repository
checks, plus root-owned contract/schema checks. Root owns registration in
canonical `auto_m7` automation. Scoped Ruff and strict mypy checks cover the
three production and four test files listed below.

## Limits and next real boundary

Successful report insert/readback, nonempty/empty genuine-source commit,
idempotent replay, conflicting replay, concurrent commits, populated
cross-account isolation, and history across concurrent append remain **Not
Run**. Do not infer these passed from pure policy or empty SQLite checks. They
require a genuine normalized provider report, genuine active binding and the
production transaction-bound fence. No fake report, no-op fence, seeded
telemetry or fabricated receipt was used to manufacture positive evidence.
The installed database/service was not migrated or touched. Root must compose
the dedicated worker, M02 fence and M04 receipt seam and run that real boundary
before claiming T005 or end-to-end M7 complete.

No new dependency, license change, credential read, profile/account mutation,
provider call or installation operation. No raw provider data is persisted by
these files. New table/storage capacity and migration recovery are root-owned
v1_0732 admission concerns. Full M7 executable exit gate remains outstanding.

## Owned files

- `backend/src/agentmonitor/modules/capacity/domain/budget_codec.py`
- `backend/src/agentmonitor/modules/capacity/application/budget_commit.py`
- `backend/src/agentmonitor/adapters/persistence/capacity/sqlite/budget_repository.py`
- `backend/tests/capacity/pure/test_budget_codec.py`
- `backend/tests/capacity/pure/test_budget_commit_policy.py`
- `backend/tests/capacity/pure/test_budget_history_cursor.py`
- `backend/tests/integration/capacity/test_budget_repository_empty.py`
- `docs/evidence/m7-budget-repository-2026-11-11.md`

No commit created. Root/shared files are excluded from this ownership list.
