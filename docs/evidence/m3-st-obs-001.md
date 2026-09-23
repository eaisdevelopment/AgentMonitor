# Test evidence: M3 ST-OBS-001 collection and capacity foundation

- Status: **Partial — production Claude→M04→M05 composition, deterministic
  contracts, empty schema, and non-observational durable paths Green; real
  Claude run/observation commit Blocked / Not Run**
- Evidence ID: `M3-ST-OBS-001-2026-09-22`
- Module/plan/increment: M04 collection control + M05 capacity / approved M3
  Task 4
- Requirements/acceptance: `FR-COL-001..008`, `FR-QUOTA-001..005`,
  `AC-HIST-001`, `AC-OPS-003`; applicable `M04-DB-001..019`,
  `M04-LIVE-004/009..011`, `M05-DB-001..010/016..021`,
  `M05-LIVE-001..006`
- Contracts: `CTR-COL-001..007`, `CTR-CAP-001/003/004/009`,
  `CTR-PROV-001..004`, `CTR-DB-002`, `CTR-COMMON-003/004/007` V1
- Recorder/date: Task-4 implementation agent, 2026-09-22 UTC

## Integrity declaration

No mock, fake, stub, emulator, provider response recording/replay, demo account,
seeded telemetry, placeholder value, test-only production branch, or fabricated
provider observation was used. Constructed quantities and policy values appear
only in pure no-I/O tests. Persistence evidence uses a real temporary file,
SQLite policy, and Alembic migrations. The live files each collect one explicit
skip whose reason is **Blocked / Not Run**; no skipped scenario is counted as a
pass while the required provider tuple is blocked.

## Red evidence

The first correct pure Red was run at `2026-09-22T17:34:23Z`:

```text
uv run --project backend python -m pytest \
  backend/tests/collection_control/test_policy.py \
  backend/tests/capacity/test_quantity_and_health.py -q
```

Result: collection failed with
`ModuleNotFoundError: agentmonitor.modules.collection_control` and
`ModuleNotFoundError: agentmonitor.contracts.capacity_v1` (two errors). An
earlier `.venv/bin/python` command failed because that path did not exist; it is
a setup failure and is not counted as Red.

The first real-persistence Red at `2026-09-22T17:34:32Z` used:

```text
uv run --project backend python -m pytest \
  backend/tests/integration/collection_control/test_collection_repository.py \
  backend/tests/integration/capacity/test_capacity_schema_chain.py -q
```

Result: collection failed because both production persistence packages were
absent. This is structural Red; no live/provider success is inferred.

Behavioral Reds added during review were:

- `2026-09-22T18:04:38Z`: `1 failed, 4 passed`; M05 incorrectly accepted the
  collection-level `unavailable` state as a metric field.
- `2026-09-22T18:12:22Z`: `1 failed, 5 passed`; negative/incompatible quota
  window inputs were accepted.
- `2026-09-22T18:14:07Z`: the real temporary SQLite/Alembic schema assertion
  failed because receipt uniqueness was
  `(run, generation, capability, schema)` rather than the required
  `(run, capability)` conflict boundary.
- `2026-09-22T18:44:46Z`: the real file-backed M04 manual-idempotency test
  failed with `collection_repository_unavailable` when a retry supplied a new
  request/run identity for the already-admitted key. The repository had relied
  on the database uniqueness error instead of coalescing to the first run.

Catalog checksum failures observed while the migration steward deliberately
unpinned the chain are setup/serialization failures and are not counted as
behavioral Red or Green.

The residual review work produced the following additional behavioral Reds:

- `2026-09-22T19:09:42Z`: the real migrated-file composition test failed with
  `ModuleNotFoundError: No module named 'agentmonitor.composition.providers'`.
  It discovered the installed Claude `2.1.278` executable but did not invoke
  its quota collector or persist telemetry.
- `2026-09-22T19:15:26Z`: the pure suite was `5 failed, 8 passed`. It showed
  that free-form failure codes, incomplete recovery receipts, unbounded
  positive decimal exponents, caller-order-sensitive window digests, and
  partial inputs without explicit omissions were incorrectly accepted.
- `2026-09-22T19:15:32Z`: an empty real SQLite query failed because the quota
  query did not accept the required capability and `as_of` boundary.
- `2026-09-22T19:16:39Z`: four real M04 repository checks failed because a
  dispatched reservation was released, scoped budget oversubscription was
  admitted, definitive interrupted commit recovery was absent, and outbox
  sequencing/correlation used run-local values instead of schedule/persisted
  values.
- `2026-09-22T19:23:18Z`: the real migrated SQLite DDL check failed because
  the frozen aggregate/health/derivation/currency constraints were incomplete.

## Green and refactor evidence

The focused pure suite at `2026-09-22T18:31:46Z` completed:

```text
uv run --project backend python -m pytest \
  backend/tests/collection_control/test_policy.py \
  backend/tests/capacity/test_quantity_and_health.py -q
```

Result: `10 passed in 0.07s`.

The corrected owned migration chain was applied through real Alembic
operations to a real temporary SQLite file at `2026-09-22T18:35:52Z`. Result:
AST-literal metadata valid; 24 empty `capacity_*` tables; receipt uniqueness
valid; `PRAGMA foreign_key_check` empty; `PRAGMA integrity_check` `ok`.

At `2026-09-22T18:36:24Z`, a second real file-backed SQLite/Alembic check used
the production M04 repository. It durably admitted request/schedule/run/lease/
budget state, generated fence 1, replayed the identical admission, advanced the
current fence, finalized a natural safe failure atomically, released lease and
budget, and returned the stored failed run. No provider observation was
inserted.

At `2026-09-22T18:45:56Z`, the complete M04 real-persistence file was Green:
`6 passed in 1.97s`. It covers atomic admission, generated fencing, identical
run replay, manual-key coalescing across new request/run identities,
same-key/different-fingerprint conflict preservation, stale-fence rejection,
and atomic safe-failure terminalization.

The residual pure fixes are Green at `13 passed in 0.07s`. They cover safe-code
failure contracts and run-state coupling, complete receipt recovery data,
positive-exponent rejection before expansion, order-independent canonical
window digests, and explicit partial omissions.

The production composition is Green over a real migrated file database. It
constructs the real Claude adapter, M04 request/executor/recovery surfaces, one
digest-validating M05 sink, and M05 status/account/window/health queries. The
empty/status and definitive no-receipt recovery tests do not invoke a provider
or insert an observation.

After the catalog steward re-pinned the corrected chain, the final focused
command at `2026-09-22T19:28:14Z` was:

```text
uv run --project backend python -m pytest \
  backend/tests/adapters/providers/claude/test_capacity_mapper.py \
  backend/tests/collection_control/test_policy.py \
  backend/tests/capacity/test_quantity_and_health.py \
  backend/tests/integration/collection_control/test_collection_repository.py \
  backend/tests/integration/collection_control/test_claude_composition.py \
  backend/tests/integration/capacity/test_capacity_schema_chain.py \
  backend/tests/integration/collection_control/test_claude_quota_run.py \
  backend/tests/integration/capacity/test_claude_quota_commit.py -q
```

After adding the definitive recovery assertion and formatting refactor, the
same command completed with `29 passed, 2 skipped in 3.34s`. The skipped count
is the two explicit live **Blocked / Not Run** declarations.

The exact Task-4 live/schema command completed with `3 passed, 2 skipped in
0.84s`:

```text
uv run --project backend python -m pytest \
  backend/tests/integration/collection_control/test_claude_quota_run.py \
  backend/tests/integration/capacity/test_claude_quota_commit.py \
  backend/tests/integration/capacity/test_capacity_schema_chain.py -q
```

Targeted Ruff completed with `All checks passed!`; strict mypy completed with
`Success: no issues found in 15 source files`; `git diff --check` passed. The
canonical boundary checker completed with `boundaries: PASS (0 violations)`.
Root independently verified the current integrated worktree with 29 focused
Task-4 tests Green and strict mypy across 74 source files.

Final owned migration SHA-256 values:

```text
554f1e085c45d7732f7fac20fc64d100413a5e89effdb98d70dfaccaa52294a9  v1_0400_m04_collection.py
bc0912e82c420f20a1384095e723175bbfede85f38e445f566aef26dde8c3907  v1_0500_m05_capacity_observations.py
bc17375fcc8f0f0f8c2694b0ec8622fd08fc3ce9a241d984ed5e4ae42f376fd2  v1_0501_m05_capacity_receipts.py
54fdceb51fdd1073023698a2ce1fc4d0f5992b273843daa8c070b749840d1642  v1_0502_m05_capacity_health.py
c8cd48a58c88df90c323c82820638ef5dad7b944a6310d0fc66dcfda82f3b476  v1_0503_m05_capacity_forecasts.py
07e165d2b2900b94a9aee49f0eb7faa4cd17b04a7076f64a5e0b62dcef43fd2b  v1_0504_m05_capacity_retention.py
```

The authorized unpublished-schema corrections changed `v1_0500` from
`49ba1d4d...` to `bc0912e8...`, `v1_0502` from `ae5e48e9...` to
`54fdceb5...`, and `v1_0503` from `3d93a3c2...` to `c8cd48a5...`. The root
steward atomically re-pinned the combined chain: catalog
`af68a432b2168758fe02200747e75ec3fc9ecd23d7c9b662151c278cdd28d88e`,
M3 schema `533fb37b8107b799efac46861a2f0a79009cd340cc489f97fc96573b859bedb1`,
and M5 schema `cc0ad2bc40fe168a88491fa980e1a911deee32aeb59d595a23cd062d6cc713c0`.

## Live and real-provider status

| Scenario | Status | Reason |
|---|---|---|
| `M04-LIVE-004/009/010/011` | **Blocked / Not Run** | The accepted current Claude collector is version/workspace blocked; no alternate source or recorded response is allowed. |
| `M05-LIVE-001..006` | **Blocked / Not Run** | No real typed Claude quota outcome is available to commit/reconcile. Fabricated observations are prohibited. |
| Production composition construction/recovery | **Passed** | Real Claude adapter and real M04/M05 application/repository stack over migrated file SQLite; no provider invocation and no telemetry rows. |
| Real provider → M04 → M05 execution | **Blocked / Not Run** | Production route exists, but live execution requires the compatible real tuple and owner-approved workspace trust. |
| Empty schema/repository and M04 admission/failure/recovery paths | **Passed** | Real file-backed SQLite and production Alembic/repositories; no telemetry rows. |
| M05 non-empty commit/replay/conflict/current/outbox behavior | **Blocked / Not Run** | These assertions require a fresh real provider observation; project policy forbids a fabricated persistence payload. |

The files `test_claude_quota_run.py` and `test_claude_quota_commit.py` are
executable blocked-scenario declarations. Each collects one explicit skip and
neither is included in the Passed count.

## Impact assessment

- Security/privacy: reduced, typed allowlists only; no raw provider output,
  credential, profile content, prompt/response, source code, or arbitrary
  environment persistence/logging.
- Migration: additive `v1_0400` and `v1_0500..v1_0504`; no rows seeded;
  downgrade unsupported; unpublished V1 corrections and final hashes serialized
  by the root steward.
- License/dependencies: no dependency change.
- Configuration: no key or secret change.
- Documentation: `docs/modules/capacity.md` and this evidence file added.
- Residual work: real Claude collection/commit/replay/reconciliation and M05
  non-empty transactional assertions; later budget/forecast/retention behavior
  and full API/browser/operations acceptance.

## Task-4 artifact inventory

- Contracts: `common_quantity_v1.py`, `collection_control_v1.py`, and
  `capacity_v1.py`.
- Production: `modules/collection_control/{application,domain}/`,
  `modules/capacity/{application,domain}/`, the collection/capacity SQLite
  repositories, `adapters/providers/claude/subscription/mapper.py`, and
  `composition/providers.py`.
- Migrations: `v1_0400_m04_collection.py` and
  `v1_0500_m05_capacity_observations.py` through
  `v1_0504_m05_capacity_retention.py`.
- Tests: Task-4 files under `tests/collection_control/`, `tests/capacity/`,
  `tests/integration/collection_control/`, `tests/integration/capacity/`, and
  `tests/adapters/providers/claude/test_capacity_mapper.py`.
- Documentation/policy: this evidence file, `docs/modules/capacity.md`, and the
  exact composition contract consumptions in `docs/plans/contract-adoption.toml`.
