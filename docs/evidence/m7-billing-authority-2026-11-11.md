# M7 current billing authority and commit composition

Status: intermediate local implementation; installed service remains setup0731.
Requirements FR-BUDGET-001/002/004, FR-ACC-006, M7-A01/A02/A09.
Modules M02/M04/M05 and root composition, approved focused plan1.1.0/T002/T007.

## Contract and behavior

CTR-REG-0141.3.0 adds profile-free billing access target/lookup. Existing metadata
and local command DTOs are unchanged. CTR-COL-0022.1.0 adds a billing admission
and run projection with report identity; quota admissions still require their
cloud profile and quota success still requires observation references.
CTR-COL-0062.0.0 commit port is parameterized by the normalized commit type so
M05's CTR-CAP-0042.1.0 BudgetCollectionInputV1 satisfies it directly.

M02 independently checks account/resource lifecycle, connection record/scope,
current active binding and billing monitoring. A first access check works before
billing monitoring is enabled; subscription identity is not used. The root
billing_capacity_commit factory invokes M04's current run/lease fence and M02's
current authority fence inside M05's actual write transaction. No unchecked
callback is installed. This factory is not yet a running billing worker.

## Actual verification

- New pure access tests initially failed14 for missing policy. A test identifier
  then failed the existing binding-ID syntax; corrected test input, not policy.
  Pure policy/status checks passed15. No constructed values crossed I/O.
- Real empty SQLite access tests initially had an incorrect database basename,
  corrected to the required agentmonitor.db. The meaningful preimplementation
  result was2 missing-port failures; subsequent empty access, existing credential
  lifecycle and pure access checks passed24 in7.25s.
- New billing run contracts initially failed3 for missing types; receipt/run and
  existing cloud contract checks then passed22 in0.25s.
- Actual0733 schema test failed because collection_budget_run did not exist.
  After its additive migration, fresh M04/M02/M05 empty storage checks passed6.
  Schema, upgrade and migration inventory regression checks passed32 in20.75s.
- Strict mypy passed five source files including commit composition. Scoped
  Ruff passed. These checks do not exercise an authenticated report commit.

The0732 structural digest remained unchanged when upgrading a real empty DB;
0733 adds one M04 table with bounded nonsecret target metadata and an all-or-none
report receipt. Catalog/digests are pinned; older migration bytes are unchanged.
No provider data, credentials, default profiles or installed database were used
or modified. No dependency/license change. Rollout still requires the selected
candidate's installed checks; isolated recovery evidence is separate.

At18:04:11UTC the installed read-only browser probe still returned
`authentication_required` (six requests, zero mutations). Dashboard service was
active and rootHTTP200. Authentication blocks that proof only, not implementation.
No repeated owner request was sent.

Changed files: registry_billing_v1.py, collection_control_v1.py, M02 billing
policy/repository and tests; composition/billing_capacity_commit.py;0733 migration,
catalog/compatibility and schema tests; canonical M7 test selection and module
notes. M04 repository/executor and source/grant increments have separate evidence.

Still Not Run: populated current-binding resolver using genuine credential
custody, successful/empty genuine provider report commit, rotation racing a real
worker, scheduler recovery of that report, and source→HTTP→installed UI. Ollama
usage must reuse its existing cloud graph fence; this new resolver does not
silently reinterpret it as a separate billing connection.


Bounded independent M02/composition review found no required correction: current
binding/scope/lifecycle checks share the actual M05 transaction and leave
subscription controls independent. It did not claim a positive live resolver or
report write. Subsequent canonical checks passed: pure164, registry_metadata36;
combined provider-source/physical-grant suite145. Planning/catalog and docs checks
passed. Source imports were subsequently normalized by the canonical root-level
Ruff invocation; no behavioral production change was made by that formatting.

Final local checkpoint: canonical pure lane192 passed, persistence_schema lane13
passed, registry_metadata lane36 passed. Combined provider/grant suite145 passed;
scoped strict mypy9 root source/test files and Ruff/format checks for53 changed
Python files passed. Documentation356 files, focused16-ticket planning, synchronized
planning and Git local preflight passed. Staged secret scan found zero findings.
These numbers describe the executed scopes, not a financial live/UI acceptance.
