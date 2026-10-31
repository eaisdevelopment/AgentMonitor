# Test evidence: M3 ST-REG-001 registry correction

- Status: **Partial — deterministic non-live scope Green; real Claude and owner
  actions Not Run**
- Evidence ID: `M3-ST-REG-001-2026-09-22`
- Module/plan/increment: M02 registry / approved M3 Task 2 slice
- Requirements/acceptance IDs: `FR-ACC-001..006`, `NFR-DATA-001`,
  `NFR-SEC-001`; the M3 slice selects `M02-PURE-006..023`,
  `M02-DB-007..024/028`, and `M02-LIVE-001..010` where a selected real
  account exists. The table below, rather than this selection list, is the
  authoritative execution status.
- Contract versions: `registry.v1`, `CTR-REG-001..010`,
  `CTR-PROV-002/005/006/007`, and `CTR-DB-002` at V1
- Migration range: M02 `v1_0200..v1_0204`; integrated application head
  `v1_0504`
- Worktree base: `b23015b`
- Recorder/date: M02 implementation agent, 2026-09-22 UTC

## Exact status

| Scenario or check | Real boundary | Status | Claim |
|---|---|---|---|
| `M02-PURE-006/007`, `M02-PURE-010/011`, `M02-PURE-013..023`, and `M02-PURE-025` | Immutable constructed domain values; no I/O | Passed | Exact scope/identity continuity, monitoring/lifecycle, graph/deduplication, reconciliation/correlation/conflict/invalidation, confirmation, profile eligibility, re-auth continuity, and safe event/log projection behaviors exercised by named tests |
| Supplemental contract checks (no allocated M02 scenario) | Pure source/contract introspection | Passed | Three concrete mutation signatures match their published protocols, and selected profile/masked-field DTOs exclude obvious prohibited fields; these narrow checks do not satisfy `M02-ARCH-001/002` |
| `M02-ARCH-001` | Canonical repository boundary/ownership checker | Failed | The current checkout has three concurrent M06 `unresolved-contract-module` violations; this scenario cannot be Passed while the canonical boundary is Red |
| `M02-ARCH-002` | All registry contracts, schemas, and OpenAPI prohibited-field scan | Not Run | The selected-DTO introspection is narrower than the exact scenario and is not promoted to a full contract/schema/OpenAPI claim |
| `M02-PURE-008/012` | Identity derivation and aggregate-collapse policies | Not Run | Current DTO inequality/type assertions do not exercise production derivation/collapse policy and are retained only as supplemental checks |
| `M02-PURE-009` | Protected history plus event/log projections | Not Run | The safe event/log half is covered by `M02-PURE-025`; no exact test yet proves prior/new protected rename and organization-move history, so this scenario is not claimed |
| `M02-PURE-026` | Account-configuration reference policy | Not Run | The earlier mutation-port signature test was mislabeled; approved namespace/kind and opaque-reference policy requires its own exact scenario and is not claimed |
| `M02-DB-001/002` | Real temporary file-backed SQLite, Alembic, and production repository | Failed (integration) | Previously Passed at the integrated `v1_0504` head; the current concurrent M06 worktree has unintegrated `v1_0600..0603` files, so migration catalog validation now fails before registry setup |
| `CTR-REG-009` empty-state query | Real temporary file-backed SQLite and production repository | Failed (integration) | Previously Passed at revision zero; current execution is stopped by the same migration catalog failure and is not represented as currently Passed |
| `M02-DB-007..024/028` requiring an account, discovery, identity decision, profile, or resource | Current real Claude data plus owner action | Not Run | No fabricated account, provider outcome, direct row insert, or seeded telemetry substitutes for the selected real subject |
| `M02-LIVE-001..010` applicable to the selected account | Current owner-controlled Claude installation/account/profile | Not Run | No real reconciliation or owner confirmation was performed |

Three executable placeholders remain skipped and visibly Not Run:

- `M02-LIVE-005`: real Claude candidate reconciliation;
- `M02-LIVE-006`: stale-version/evidence conflict against that candidate;
- `M02-LIVE-004`: real account/profile/resource enrollment receipt replay.

The other live IDs are not represented by passing or skipped tests in this
slice and are not claimed as covered.

## Red evidence

The independent QA correction added exact tests for previously over-claimed
pure semantics. Before its production changes, this command ran on 2026-09-22
UTC. The runner output did not emit a sub-minute timestamp, so none is
invented here:

```text
backend/.venv/bin/pytest \
  backend/tests/registry/test_identity_policy.py -q --tb=short
```

Result: `7 failed, 30 passed in 0.17s`. The seven intended behavioral Reds
were:

- duplicate real inputs made deterministic scope projection violate its
  no-duplicate contract;
- `AccountMonitoringDecisionV1` did not preserve monitoring preference;
- account archive continuity had no policy operation;
- partial discovery had no fail-closed reconciliation policy;
- malformed discovery had no fail-closed reconciliation policy;
- an unverified provider version had no fail-closed reconciliation policy;
- an owner-confirmed decision could discard the original evidence class.

These were production-behavior failures, not syntax, dependency, credential,
or environment failures.

Before the corrective production changes, this exact focused command was run:

```text
cd backend && .venv/bin/python -m pytest \
  tests/registry/test_identity_policy.py::test_unavailable_locator_is_rejected_before_authentication \
  tests/registry/test_identity_policy.py::test_published_mutation_ports_match_concrete_call_signatures \
  tests/integration/registry/test_registry_persistence.py::test_v1_0200_through_v1_0204_create_owned_schema_without_rows \
  -q --tb=short
```

Result: `3 failed`. The profile policy did not reject an unavailable locator;
the published and concrete reconciliation call signatures differed; and the
`v1_0202` resource-parent foreign key lacked the account component. These were
the intended missing behaviors, not setup failures.

An earlier contract Red also showed that a candidate could simultaneously be
`owner_confirmed` and require owner action:

```text
backend/.venv/bin/python -m pytest \
  backend/tests/registry/test_identity_policy.py::\
test_candidate_owner_action_flag_must_match_current_state -q
```

Result before correction: `Failed: DID NOT RAISE ValueError`. The focused test
then passed after the candidate-state invariant was implemented.

Persistence Reds for real candidate confirmation, changed-evidence
invalidation, zero-candidate reconciliation receipts, and graph replay are
**Not Run**. Their required input is a current real `DiscoveryOutcomeV1` and/or
owner-confirmed account. Creating equivalent rows or outcomes for a DB test is
prohibited, so source/static Green is not represented as real persistence
evidence.

## Green and refactor evidence

The review-requested explicit ambiguity and attribution regressions were added
after the relevant production behavior already existed:

```text
backend/.venv/bin/pytest \
  backend/tests/registry/test_identity_policy.py::\
test_nonunique_provider_verified_identity_still_requires_confirmation \
  backend/tests/registry/test_identity_policy.py::\
test_owner_confirmation_requires_both_actor_and_timestamp \
  -q --tb=short
```

Initial result: `3 passed in 0.09s`. This is characterization/regression
evidence, not a fabricated Red, and it caused no production change. The tests
prove that provider verification without uniqueness still requires owner
confirmation and that owner-confirmed decisions reject either a missing actor
or a missing timestamp.

Pure policy and contract scenarios:

```text
cd backend && .venv/bin/python -m pytest tests/registry/test_identity_policy.py -q
```

Result after the first independent QA correction: `37 passed in 0.10s` (root
independent rerun: `37 passed in 0.09s`). After the bounded review correction,
the focused result is `40 passed in 0.09s`.

Focused registry, live-placeholder, and real migration regression:

```text
cd backend && .venv/bin/python -m pytest \
  tests/registry/test_identity_policy.py \
  tests/integration/registry/test_registry_persistence.py \
  tests/integration/registry/test_claude_reconciliation.py \
  tests/persistence/sqlite/migrations/test_v1_0000.py -q
```

The current broader command is:

```text
backend/.venv/bin/pytest \
  backend/tests/registry \
  backend/tests/integration/registry \
  backend/tests/persistence/sqlite/migrations/test_v1_0000.py -q -rs
```

Last stable pre-M06-inventory result: `70 passed, 3 skipped in 7.47s` (root
independent rerun without skip reasons: `70 passed, 3 skipped in 6.67s`). The
three skips are the real Claude cases listed above and are not counted as
Passed.

Current result after concurrent `v1_0600..0603` files appeared:
`29 failed, 44 passed, 3 skipped in 1.11s`. Every failure shown is downstream
of `migration_catalog_invalid` because the shared catalog/compatibility owner
has not yet integrated that M06 inventory. This is a real current failure, not
a registry pass and not repaired from this isolated M02 task.

Exact boundary registration and fail-closed negative coverage:

```text
backend/.venv/bin/python -m pytest \
  backend/tests/foundation/test_contract_boundaries.py -q
python3 tooling/foundation/check_boundaries.py .
```

Historical result before concurrent M06 work: `180 passed in 4.30s` and
`boundaries: PASS (0 violations)`. The current checkout rerun is **Failed**:
`178 passed, 2 failed`; the checker reports three
`unresolved-contract-module` violations in concurrent M06/runtime files:
`local_agent_processes.py`, `api/v1/dependencies.py`, and
`runtime_observation/application/overview.py`. No registry file is identified,
but this gate is not represented as currently Passed.

Registry-scoped quality:

```text
cd backend && .venv/bin/ruff check \
  src/agentmonitor/contracts/registry_v1.py \
  src/agentmonitor/modules/registry \
  src/agentmonitor/adapters/persistence/registry \
  tests/registry tests/integration/registry \
  ../tooling/foundation/check_boundaries.py \
  tests/foundation/test_contract_boundaries.py
cd backend && .venv/bin/ruff format --check \
  src/agentmonitor/contracts/registry_v1.py \
  src/agentmonitor/modules/registry \
  src/agentmonitor/adapters/persistence/registry \
  tests/registry tests/integration/registry \
  ../tooling/foundation/check_boundaries.py \
  tests/foundation/test_contract_boundaries.py
cd backend && MYPYPATH=src .venv/bin/mypy --strict \
  --explicit-package-bases \
  src/agentmonitor/contracts/registry_v1.py \
  src/agentmonitor/modules/registry \
  src/agentmonitor/adapters/persistence/registry
```

Current registry-scoped results: Ruff lint passed; Ruff format reports all 9
files formatted; strict mypy reports `Success: no issues found in 6 source
files`. Repository documentation validation reports `DOCUMENTATION CHECK:
PASSED (222 Markdown files)`. The shared boundary checker remains Failed as
recorded above.

## Migration and compatibility evidence

The corrected unpublished `v1_0202` bytes were frozen at SHA-256
`661f7bdfa45dd365a23d16d3ccfba86edd60bf04e69a571f363fa74ab3040f2b`.
The root integration owner atomically repinned the shared migration catalog and
M02/M03/M05 schema digests; the resulting catalog digest is
`1540b1c21bc7c49c78ef3c10be1084453e88ce212d115a226ce77151c1739e2a`.
Root's integrated M02/M03/M04/M05 real-chain run reported `78 passed in
14.45s`. That is historical evidence for the integrated `v1_0504` checkout.
The current concurrent checkout contains unintegrated M06 migration inventory,
so fresh-file migration verification is Failed as recorded above and must be
rerun after the shared owner completes the `v1_0603` catalog/compatibility
integration.

## Security, privacy, dependency, and documentation impact

- Changed discovery evidence makes the account and claim conflicted,
  invalidates the prior current decision while retaining it as history, and
  preserves the reviewed relationship for resolution.
- Provider evidence class remains stored separately from the owner-confirmation
  action. Public views expose no raw identity, provider payload, locator, path,
  credential, prompt, response, source code, or arbitrary environment value.
- Profile eligibility fails closed for default, unmanaged, incompatible,
  unavailable, inactive, or unverified profiles before locator resolution.
- `v1_0202` enforces account-local resource ancestry and profile-resource links
  with composite foreign keys.
- No dependency, license, provider write, provider authentication, default
  profile mutation, process control, API, UI, or cross-module schema change was
  introduced by this correction.
- Module documentation records `CTR-REG-009`, the integrated schema head,
  compatibility states, and exact live limitations.

## Integrity declaration and residual live work

No mock, fake, stub, emulator, recorded provider response, demo account,
fabricated persistence row, seeded telemetry, placeholder value, hardcoded
pass, or disabled assertion was used. Constructed values occur only in pure
domain/contract tests.

The exact named non-live registry tests above are Green. This is not a blanket
claim for every selected M02 scenario: `M02-PURE-008/009/012/026`,
`M02-ARCH-002`, the listed real Claude tests, and the remaining live/
persistence/API/browser scenarios remain Not Run. `M02-ARCH-001` and the
checkout-wide boundary gate are currently Failed because of concurrent M06
work. `ST-REG-001` as a whole remains Partial: Task 3 must
provide a current typed real Claude discovery outcome, and the owner must
confirm the returned exact candidate before real reconciliation,
conflict/invalidation, account/profile/resource enrollment, persistence
reopen/concurrency, API, or browser scenarios can move from Not Run to Passed.
