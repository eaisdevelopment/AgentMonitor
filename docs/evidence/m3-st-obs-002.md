# Test evidence: M3 ST-OBS-002 runtime observation foundation

- Evidence ID: `M3-ST-OBS-002-2026-09-22`
- Module/plan/increment: M06 / A01 / A04-LINUX / DB; M3 Task 5
- Requirements/acceptance IDs: `FR-DISC-001..008`, `FR-STATE-001/002`,
  `AC-PROC-001..005`, applicable `M06-LNX-*`, `M06-LIVE-*`, `LNX-*`, and
  `CLA-*`
- Contract versions: `CTR-PLAT-001`, `CTR-RUN-001..003`,
  `CTR-RUN-006..007`, and the M04 runtime commit seam at V1
- Commit/worktree reference: M3 working tree before milestone commit
- Recorder/date: AgentMonitor Task 5 implementation and independent review,
  2026-09-22
- Overall status: **Partial / Blocked**. The generic Linux process and durable
  storage foundation passed. Exact Claude executable/version/installation,
  local session, account, hierarchy, and runtime-state claims did not run
  because the approved M0 handoff provides no executable fingerprint,
  targeted-profile probe, or approved local-session source.

## Test inventory and status

| Test/scenario | Layer | Real dependencies | Status | Evidence | Notes |
|---|---|---|---|---|---|
| Runtime contract invariants and Strong-only correlation | Pure domain | Constructed typed values; no I/O | Passed | focused Task 5 suite | Production Strong-rule catalog is empty; unapproved evidence stays unresolved |
| A01 local-session, metrics, and correlation ports | Adapter contract | Production adapters; no provider read is authorized | Passed | focused Task 5 suite | Exact result is `unsupported`, retry `never`, with capability-specific safe codes |
| Generic Linux process inspection | Platform | Real `/proc`, same UID, naturally running `comm=claude` candidates | Passed | focused Task 5 suite | Independent bounded `/proc/<pid>/stat` oracle confirmed UID, comm, PID, and start ticks for at least one returned record |
| Bounded procfs reads and units | Platform | Real `/proc/self/stat`, real `sysconf` | Passed | focused Task 5 suite | Boot and stat reads use `read(maximum + 1)` and reject oversize input |
| Linux portable capability producer | Platform | Real Linux kernel/process ownership/monotonic clock | Passed | focused Task 5 suite | Unsupported filesystem/deployment capabilities remain explicitly unsupported |
| Runtime migrations and direct constraints | DB | Real file-backed SQLite, production migrations | Passed | 18 focused migration tests | Includes fail-closed downgrade refusal and no seeded rows |
| Runtime commit/replay/current/history | DB/integration | Real `/proc` facts and real file-backed SQLite reopened through production repository | Passed | focused Task 5 suite | Provider version/install/account remain null; safe provenance survives persistence |
| Adjacent migration/provider compatibility | DB/integration | Real file-backed SQLite and production chain | Passed | 61 tests | Guards prior migration and provider-system behavior |
| Contract/import boundaries | Architecture | Real checkout and adoption manifests | Passed | `boundaries: PASS (0 violations)` | Symbol-level shared-SQLite and runtime contract use validated |
| Exact Claude 2.1.278 executable/install attribution | Provider/live | Missing approved executable fingerprint and installation join | **Blocked / Not Run** | M0 handoff | Caller-supplied version and `comm` are insufficient evidence |
| Claude local session and same-account correlation | Provider/live | Missing approved session source and targeted-profile probe | **Blocked / Not Run** | M0 handoff | No session/account row was invented or seeded |
| Representative parent/subagent tree | Provider/live | Missing session/hierarchy source | **Blocked / Not Run** | M0 handoff | Parent PID alone is not durable provider hierarchy |
| `CTR-RUN-004/005` minimum types and fail-closed evaluator | Pure domain | Constructed typed values; no I/O | Passed | focused Task 5 suite | Exact approved vocabulary, stale/unknown/missing-input degradation, wait exclusion, and inferred 600-second result |
| State persistence/events, policy precedence, and real ten-minute stall/wait behavior | Domain/DB/live | No approved session activity/wait source | **Blocked / Not Run** | scope review and M0 handoff | Must not be counted toward full `FR-STATE-*` or `AC-PROC-005` acceptance |
| Real macOS runtime | Platform/live | No real supported Mac in this run | **Blocked / Not Run** | platform scope | Linux-first result only |
| Canonical M0 live handoff authorization | Governance | Bound acceptance still records provider/live/later-task authorization false and review roles pending | **Blocked** | `m3-handoff-acceptance-v1.json` | Implementation evidence does not override the canonical acceptance record |

No focused Task 5 test was skipped in the recorded Green run.

## Red evidence

The following pre-production failures were retained during Red-Green-Refactor:

1. The initial focused command failed during collection because
   `agentmonitor.contracts.runtime_observation_v1` did not exist.
2. The real repository test failed during collection because the runtime
   persistence adapter did not exist.
3. False-attribution regressions failed because an unverified caller version
   returned success and an arbitrary `strong` rule selected an account. The
   corrections removed provider/install attribution from generic procfs facts
   and made production correlation fail closed with an empty approved-rule
   catalog.
4. A01 port tests failed because unavailable sources returned version-review
   advice. They now return exact unsupported/not-approved results with retry
   `never` and perform no I/O.
5. Executable-label tests failed because a multi-character `comm` was passed
   through the one-character kernel-state type. A separate bounded label type
   now preserves the kernel-state invariant.
6. Linux unit and platform-capability tests failed before their validators and
   real producer existed.
7. The bounded-read test failed at collection with
   `ImportError: cannot import name '_read_bounded'`; the production helper was
   then implemented and applied to boot ID and both synchronized stat reads.
8. The first migration constraint run was `11 failed, 1 passed`. A later
   downgrade regression was `4 failed, 14 passed` because the four migrations
   still had destructive downgrade handlers. All four now refuse downgrade
   before issuing DDL.
9. Session-query contract coverage failed `1 failed` because
   `AgentSessionRecordV1` had no `provenance` field. The record now requires
   closed provenance and list/tree queries reconstruct it from the current
   observation and durable receipt.
10. The first state/stall/owner-check command failed during collection with two
    missing symbols: `_same_owner` and `RuntimeStallPolicyViewV1`. Exact
    vocabulary/time-policy regressions later failed `2 failed`; policy
    precedence initially failed collection because
    `select_effective_stall_policy` did not exist.
11. The generic-attribution correction produced `4 failed, 6 passed`: nullable
    attribution was rejected by the request contract, and caller attribution
    returned the prior version-only code. The real requests now carry no
    provider/version/installation assertion; any asserted tuple is rejected
    before procfs I/O.
12. The final provenance-lineage correction failed `1 failed` because the
    persisted receipt used an `unresolved` sentinel as a provider key. It now
    uses `claude` only for the M0-approved capability/selector lineage, with the
    process subject provider/install still null and an explicit
    `procfs_fields_confirmed_provider_attribution_unresolved` confidence reason.

These Reds failed for the intended missing or defective behavior. No production
branch was added solely to detect a test environment.

Exact later-review Red commands and exit results:

```text
backend/.venv/bin/pytest \
  backend/tests/runtime_observation/test_contracts.py::test_session_query_record_requires_closed_observation_provenance \
  -q --tb=short
# exit 1: 1 failed; AgentSessionRecordV1 fields omitted provenance

backend/.venv/bin/pytest \
  backend/tests/runtime_observation/test_contracts.py \
  backend/tests/runtime_observation/test_linux_process_policy.py \
  backend/tests/runtime_observation/test_runtime_state_policy.py \
  -q --tb=short
# exit 2: 2 collection errors; _same_owner and RuntimeStallPolicyViewV1 absent

backend/.venv/bin/pytest \
  backend/tests/runtime_observation/test_runtime_state_policy.py::test_approved_normalized_state_vocabulary_is_exact \
  backend/tests/runtime_observation/test_runtime_state_policy.py::test_naive_evaluation_time_is_rejected_with_a_typed_safe_error \
  -q --tb=short
# exit 1: 2 failed; approved state rejected and naive time leaked base error

backend/.venv/bin/pytest \
  backend/tests/runtime_observation/test_runtime_state_policy.py \
  -q --tb=short
# exit 2 before precedence implementation: missing select_effective_stall_policy

backend/.venv/bin/pytest \
  backend/tests/live/claude/test_runtime_observation.py \
  backend/tests/runtime_observation/test_linux_process_policy.py \
  backend/tests/runtime_observation/integration/test_real_linux_commit.py \
  -q --tb=short
# exit 1: 4 failed, 6 passed before nullable attribution/fail-closed correction

backend/.venv/bin/pytest \
  backend/tests/runtime_observation/integration/test_real_linux_commit.py::test_real_linux_process_commit_replays_and_queries_history \
  -q --tb=short
# exit 1: 1 failed before provider capability-lineage provenance correction
```

### 2026-09-23 M06 commit-boundary hardening

The current real Linux process population made the previously skipped process
commit path execute and exposed that its evidence helper hardcoded the obsolete
Linux adapter version `1.0.0`; production emitted `1.1.0`, so the real test
failed closed with `runtime_provenance_mismatch`. The helper now takes the exact
adapter version from the freshly collected typed process observations and
requires one consistent version. It does not substitute a configured or test
value.

At `2026-09-23T09:12:31Z`, real procfs observations and a freshly migrated
file-backed SQLite database produced two intended Reds:

```text
backend/.venv/bin/pytest \
  backend/tests/runtime_observation/integration/test_real_linux_commit.py::test_real_batch_terminal_state_must_match_completeness \
  backend/tests/runtime_observation/integration/test_real_linux_commit.py::test_same_run_and_real_payload_with_changed_provenance_is_a_conflict \
  -q --tb=short
# exit 1: 2 failed; contradictory terminal metadata committed and changed
# safe provenance replayed as though it were the original request
```

At `2026-09-23T09:13:59Z`, the same command passed `2 passed`. M06 now rejects
terminal/completeness contradictions before persistence, and exact replay
compares the complete safe provenance stored in the durable receipt. The
original receipt remains authoritative after a conflicting replay.

At `2026-09-23T09:21:44Z` and `2026-09-23T09:22:31Z`, direct production
repository tests each failed because incompatible payload schema and
contradictory terminal metadata were accepted behind the application port.
After fail-closed repository validation, the corresponding Green commands at
`2026-09-23T09:22:03Z` and `2026-09-23T09:22:48Z` each passed `2 passed`.
The application and persistence boundaries now both enforce
`runtime-observation-batch.v1` and terminal/completeness consistency.

The broader post-refactor results were:

```text
backend/.venv/bin/pytest backend/tests/runtime_observation -q --tb=short
# 58 passed in 9.16s

backend/.venv/bin/pytest \
  backend/tests/runtime_observation \
  backend/tests/persistence/sqlite/migrations/test_v1_0000.py \
  backend/tests/integration/provider_system/test_compatibility.py \
  backend/tests/integration/provider_system/test_compatibility_repository.py \
  -q --tb=short
# 119 passed in 25.17s
```

Changed-file Ruff, formatting, and strict mypy passed; the repository boundary
checker reported `boundaries: PASS (0 violations)`, and `git diff --check`
passed. No contract, DDL, migration digest, dependency, provider, account, or
process state changed. Exact provider-session persistence and live
session/account conflict handling remain Blocked / Not Run because the approved
M0 handoff still provides no real session source or correlation rule.

### 2026-09-23 production M04-to-A04-to-M06 composition

The production composition now resolves the one present Claude installation
through the published M02 query port, verifies the exact installed executable,
durably admits an M04 run, and only then invokes the bounded A04 procfs
inspection. It commits the typed batch to the production M06 repository,
finalizes M04 from the durable receipt, and queries the resulting process
projection. Executable evidence supplies installation attribution only;
`account_id`, profile, and resource remain null because account correlation is
not proven.

The original real-boundary Red at `2026-09-23T10:21:41+01:00` was:

```text
AGENTMONITOR_RUN_LINUX_RUNTIME_DATA_ROOT=/home/dev/.local/share/agentmonitor \
  PYTHONPATH=backend/src backend/.venv/bin/python -m pytest \
  backend/tests/integration/collection_control/test_linux_runtime_run.py -q
# 1 failed: ModuleNotFoundError for the absent production composition
```

After the first implementation, the same real test reached M06 and failed with
`runtime_repository_unavailable`. This exposed a genuine contract defect: the
frozen schema required an executable identity for attributed processes, while
the published snapshot DTO could not carry it and the repository wrote SQL
NULL. The corrected CTR-RUN-001/002/006 path carries a lowercase SHA-256 safe
fingerprint derived from approved non-content executable metadata. No raw path,
command line, environment, executable content, prompt, response, or provider
credential is read or retained.

The first post-correction attempt at `2026-09-23T10:37:06+01:00` stopped before
procfs because the earlier failed commit still held its M04 lease. That known
no-receipt run was finalized as `failed` with safe code
`collection_commit_interrupted`; its lease is released and its conservative
budget reservation remains visible. The non-concurrent real Green at
`2026-09-23T10:37:52+01:00` was:

```text
AGENTMONITOR_RUN_LINUX_RUNTIME_DATA_ROOT=/home/dev/.local/share/agentmonitor \
  PYTHONPATH=backend/src backend/.venv/bin/python -m pytest \
  backend/tests/integration/collection_control/test_linux_runtime_run.py -q
# 1 passed in 0.16s
```

The public M04 query subsequently reported two runtime runs and zero in
`committing`: the new run is `succeeded` with two real observation IDs and null
account, while the earlier run is `failed` with zero observations and null
account. Focused Ruff, format, strict mypy, and the contract/import boundary
gate passed; the boundary result was `boundaries: PASS (0 violations)`.

### TDD evidence custody deviation

Exact commands and sanitized summaries for the later review fixes are retained
above and in the agent execution transcript. Exact UTC timestamps and raw output
files were not captured for the earlier increments, so this packet does **not**
claim full compliance with the SDLC's durable Red-evidence custody requirement.
The missing historical timestamps/raw files were not recreated. This is an
explicit evidence deviation, not a Passed gate.

## Green evidence

From the repository root:

```text
backend/.venv/bin/pytest \
  backend/tests/runtime_observation/test_contracts.py \
  backend/tests/runtime_observation/test_claude_runtime_ports.py \
  backend/tests/runtime_observation/test_linux_process_policy.py \
  backend/tests/runtime_observation/integration/test_runtime_migration_constraints.py \
  backend/tests/runtime_observation/integration/test_runtime_schema_chain.py \
  backend/tests/runtime_observation/integration/test_real_linux_commit.py \
  backend/tests/live/claude/test_runtime_observation.py \
  backend/tests/live/runtime/test_linux_primitives.py -q --tb=short
```

An intermediate result was `43 passed in 7.52s`. After the session-provenance,
state/stall, same-UID recheck, full-set oracle, and no-attribution review fixes,
the complete focused command became:

```text
backend/.venv/bin/pytest \
  backend/tests/runtime_observation \
  backend/tests/live/claude/test_runtime_observation.py \
  backend/tests/live/runtime/test_linux_primitives.py -q --tb=short
```

Final result after the provenance-lineage correction: `55 passed in 6.96s`,
with no skips.

```text
backend/.venv/bin/pytest \
  backend/tests/persistence/sqlite/migrations/test_v1_0000.py \
  backend/tests/integration/provider_system/test_compatibility.py \
  backend/tests/integration/provider_system/test_compatibility_repository.py \
  -q --tb=short
```

Result: `61 passed in 13.82s`.

The final migration-only constraint run was `18 passed`. A direct production
procfs-to-migration-to-repository check also committed a non-empty generic
process set and returned one history entry.

## Refactor and quality evidence

- Scoped Ruff: `All checks passed!`
- Strict mypy over 13 Task 5 source paths: `Success: no issues found in 13
  source files`
- Contract/import boundary gate: `boundaries: PASS (0 violations)`
- Migration catalog digest:
  `e988eeb989d194ada46480c2a134c9fcdc7eb59e73e41b9dffebc06f99cfbafc`
- Frozen migration SHA-256 values:
  - `v1_0600`: `ae024d3d205067adbaa50ca7c3e5802920661065bd217e172f23f83d94b67a84`
  - `v1_0601`: `97c9aefd0106f03be427ba45dfd59d59a9470cfad0113313971e6c110d799a7f`
  - `v1_0602`: `8d4b14fadf240dd08e809c8fb42f1587493ccd67db5aae6168a8b84f5cd64f4d`
  - `v1_0603`: `c4c0013307d033a91ef83dd33f155867a1bd4c1a2645fae832e3ed8d6d81fcea`

## Real-system evidence

The Green path used the workstation's real procfs, real clock/page units, real
process ownership, real monotonic clock, production migration runner, real
file-backed SQLite, production repository, and database reopen/query path. It
did not launch, signal, attach to, write to, restart, or otherwise control a
process. The oracle independently re-read every returned row: every still-live
row with the same start identity had to match UID, comm, and start ticks; only a
demonstrable exit or PID reuse could be omitted.

The earlier generic path proves same-UID process facts only. The later
production composition additionally proves exact Claude 2.1.278 executable and
registered-installation attribution through the approved selector. It does not
prove a local provider session or account correlation; those claims remain
Blocked / Not Run.

## Integrity declaration

No mock, fake, stub, emulator, recorded response, demo account, seeded
telemetry, placeholder live attribution, disabled assertion, hardcoded passing
result, or test-only production branch was used. Constructed opaque and invalid
inputs appear only in pure contract/policy tests that perform no external I/O.
The generic real boundary passes without attribution; the production
composition boundary separately passes with exact provider/version/installation
attribution. Both use real procfs and real SQLite.

## Data, secret, security, license, and migration review

- The contract, DDL, repository, and test scans contain no command line,
  environment, prompt, response, terminal content, source content, credentials,
  or raw provider payload fields.
- Only numeric process metadata, a bounded executable label, hashed boot/PID
  namespace scope, safe IDs/codes, and closed provenance are retained.
- Production-composed process rows carry only exact-selector-backed provider and
  installation attribution plus safe provider-version provenance. Session and
  account remain null/unresolved because no approved evidence correlates them.
- There is no process-control or credential-switching surface.
- Migrations are additive, create no telemetry rows, enforce direct-SQL
  constraints, and reject downgrade before mutation.
- No dependency was added, so there is no new license or transitive-security
  impact.
- Module and operator documentation was added under `docs/modules` and
  `docs/operations`.

## Conclusion and residual gaps

The generic Linux process contract, exact-selector read-only adapter,
production M04-to-M06 composition, persistence/query foundation, capability
producer, and fail-closed A01 seams passed their tested boundaries.
**ST-OBS-002 as worded is not fully accepted**, because its real Claude
session/account provenance example and same-account tree/state/stall acceptance
remain impossible with the current M0 evidence. They remain Blocked / Not Run
until an owner-reviewed M0 packet approves a local-session/correlation source,
the canonical handoff authorization is reconciled, and the TDD
evidence-custody deviation is accepted or remediated where still possible.

## Executable-identity contract correction

The attributed-process persistence gap was corrected without changing the
`v1_0600` migration. `ProcessSnapshotInputV1.executable_identity` is an
optional, safe lowercase SHA-256 fingerprint. Provider or installation
attribution now fails closed unless that fingerprint is present and valid;
generic unresolved observations may omit it. The fingerprint participates in
the canonical batch digest and is persisted into the existing
`runtime_process_instance.executable_identity` column. Reconciliation permits a
generic row to gain verified attribution, prevents a later generic observation
from erasing it, and rejects contradictory fingerprint/provider/installation
values.

Focused Red evidence:

```text
2026-09-23T09:32:16Z
backend/.venv/bin/pytest backend/tests/runtime_observation/test_contracts.py \
  -k 'executable_identity or attributed_process' -q --tb=short
7 failed: ProcessSnapshotInputV1 rejected the new executable_identity argument.

2026-09-23T09:34:09Z
backend/.venv/bin/pytest \
  backend/tests/runtime_observation/test_process_attribution_policy.py \
  -q --tb=short
Collection failed: _reconcile_process_attribution did not exist.
```

Focused Green evidence after implementation and formatting:

```text
backend/.venv/bin/pytest backend/tests/runtime_observation/test_contracts.py \
  -k 'executable_identity or attributed_process' \
  backend/tests/runtime_observation/test_process_attribution_policy.py \
  backend/tests/runtime_observation/integration/test_real_linux_commit.py::test_real_attributed_process_fingerprint_persists_in_migrated_sqlite \
  -q --tb=short
8 passed, 15 deselected in 0.72s

backend/.venv/bin/pytest \
  backend/tests/runtime_observation/test_process_attribution_policy.py \
  -q --tb=short
5 passed in 0.16s
```

The integration selection used real procfs observations, the production Linux
selector, the production migration runner, and a fresh real file-backed SQLite
database. It first committed generic observations and then committed the
attributed observations, proving the durable generic-to-attributed upgrade and
stored fingerprint. No path, device, inode, raw stat data, or content entered
the DTO or database. No dependency or migration was added.
