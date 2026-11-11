# M7 cloud usage authority and unresolved report lineage

Status: local contract/codec/policy increment within approved focused plan 1.1.0,
M05 increment 0.3.0; T004/T005/T007/T009 remain open. No cloud usage dispatcher
or new provider read is enabled by this increment. Installed dashboard remains
the separately verified `14dee16` funds increment.

## What changed

- Root publishes additive CTR-COL-002 2.2.0 cloud budget admission/context.
  Existing CTR-REG-012 graph and service-target DTOs retain the real cloud
  profile/resource/binding. No fabricated billing connection, new registry
  wrapper or migration is needed. Original balance service authority is
  `ollama.com`; its fingerprint is captured separately from the usage source.
- Scope self/team, native seven/thirty-day range and exact completed UTC-day
  interval are immutable. Recovery may retain an older interval; the adapter
  still must reject a range it cannot dispatch. Usage is not balance verification.
- M04 adds a canonical tagged cloud target codec beside the unchanged billing
  codec: exact keys, duplicate rejection, canonical UTC/ASCII and 8192-byte bound.
  Decoding validates structure/consistency, not live authorization.
- M05 partitions unresolved reports by existing binding ID/generation in both
  pure compatibility and SQL metadata grouping. Resolved compatible financial
  scope still permits rotation. Old report lineage remains retained.

Requirements: FR-BUDGET-001/004/005/006, M7-MATH-04/05/10/11/15; partial
collection authority/history prerequisites for M7-A01/A06/A10. Collection owns
the codec/run; M05 owns report selection; root owns the shared contract and
integration. Existing report/commit shapes and SQL schema remain unchanged.

## Red / Green and review

- Cloud admission/context Red: 37 failed, four existing checks passed, with
  `cloud budget run admission is absent` or
  `immutable cloud budget report context is absent`. Root reproduced this before
  implementation. Green: 41 passed including existing billing contracts.
- Codec Red: missing encoder assertion; Green/post-format: 92 passed across
  cloud codec, existing dispatch policy and cloud contracts. Constructed DTOs
  remain in pure tests; no synthetic telemetry crosses storage/provider I/O.
- Unresolved lineage Red: two failures (`DID NOT RAISE ValueError`), twenty
  passes. Green/refactor: 24 passed across report-selection/current-selection
  tests and actual migrated empty SQLite query. Populated SQL is not proved.
- Root combined contract/policy/empty-SQLite run: 65 passed, zero skips.
- Independent read-only review: 93 scoped pure tests passed. No blocking
  contract/codec defect found; the current-query gap below is explicitly open.

Exact scoped commands use the admitted project interpreter with
`PYTHONPATH=backend/src:.`, `-m pytest -c backend/pyproject.toml -q --tb=short`
and `-p tools.automation.pytest_no_skip`. Suites:

- `backend/tests/contracts/test_cloud_budget_run_contract.py`
- `backend/tests/contracts/test_budget_run_contract.py`
- `backend/tests/collection_control/pure/test_cloud_budget_target_codec.py`
- `backend/tests/collection_control/pure/test_budget_dispatch_policy.py`
- `backend/tests/capacity/pure/test_budget_report_selection.py`
- `backend/tests/capacity/pure/test_budget_current_selection.py`
- `backend/tests/integration/capacity/test_budget_current_empty.py`

The existing M7 pure lane includes the new contract and codec suites. Strict
test typing/import issues were corrected separately; not behavioral Red.

Final local `AUTO-QUALITY` passed at 21:40 UTC: 715 formatted files, strict
typing across 654 source files, boundaries, compatible 85-operation generated
API/client, frontend types, locked dependencies and production build. Existing
M7 `--lane pure` passed **352 tests**, zero skips. These checks do not execute
the unfinished cloud collection or a populated financial persistence journey.

## Required next integration, not hidden completion work

1. M04 capture/restore/claim/commit must use the tagged authority and actual
   registry fences. The DTO and codec alone authorize no provider request.
2. Existing balance and usage must share the real request gate, cooldown and
   uncertain-request recovery. Preserve the accepted balance target fingerprint.
3. Root composes the existing supervised worker and report sink with the
   real existing cloud graph. No owner account/key re-creation is justified by
   this missing wiring. Read-only installed inventory still has zero independent
   billing connections; existing Ollama cloud funds remain available.
4. **Current-query gap:** SQL separates unresolved lineages but
   `BudgetCurrentQueryV1` has no active binding selector and current application
   reads would return all partitions. Supply the active lineage through an
   authorized contract and filter current unresolved results before enabling
   cloud spend. Older lineages belong in explicit retained history.
5. Genuine usage report → atomic commit/retry/reopen → HTTP → built DOM and
   browser-closed scheduling remain required. If real usage exposes counts only,
   it cannot satisfy the monetary demonstration. No populated result is claimed.

Security/privacy: no keys, credentials, provider state, default profiles or
owner configuration read/changed; no new dependency/license/migration. Runtime
provider access and exact source comparison remain Not Run for this increment.
