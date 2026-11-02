# M6 Ollama process observation — implementation evidence

- Scope: `M6-T013`, `M6-A06`, `AC-PROC-001..004`.
- Approved change plan:
  `docs/plans/integration/m6-ollama-process-implementation-change.md`, SHA-256
  `d808df37e3a0bb88c61beff9fc939316476a3735a9148e8492f675222281e218`.
- Status: **Intermediate**. Exact same-user process observation, registry
  reconciliation, real SQLite persistence, and authenticated HTTP passed.
  Model/process semantics, representative hierarchy, built-browser evidence,
  and another host remain open.

## Boundary and result

The Linux adapter now admits `linux.proc.ollama-process.v1` only when A03 has
resolved the exact admitted Ollama `0.24.0` executable. A03 retains a hidden
eight-field executable identity and revalidates it before A04 constructs the
selector. A04 then verifies the same executable identity before and after each
bounded procfs observation, together with same-user ownership and PID/start
identity. It reads no argv, environment, process content, provider profile, or
communications.

The current real host supplied at least one stable same-user process whose
`/proc/<pid>/exe` was the admitted executable. A process owned by another user
remains outside the same-user scan and is not counted as absent. The scan is
bounded to 16,384 candidates, 512 results, and the request deadline; omissions
and result truncation remain visible as partial coverage.

The real installation is reconciled through the existing installation-only M02
port as `ollama-installation-primary`. The durable path reuses M04 collection
admission and M06 commit/projection contracts. Its persisted and current HTTP
views report provider `ollama`, exact version/source/time/process identity, and
safe process metrics. Account association remains unresolved. No model,
account, session, daemon/client role, loaded-model relationship, or active-work
claim is derived from the process name, parent PID, or local catalog.

No dashboard service or provider process was stopped, restarted, signalled,
attached to, or given terminal input. No default provider profile was read or
modified.

## Red, Green, and refactor evidence

All commands used the isolated implementation checkout and the repository's
existing pinned backend environment with `PYTHONPATH=backend/src`.

1. Real selector Red, 2 November 2026 at `13:59:57Z`:

   ```bash
   python -m pytest backend/tests/live/ollama/test_process_discovery.py -q --tb=short
   ```

   Result: `1 failed`; the real request returned `unsupported` with exact error
   `linux_selector_unverified`.
2. A03 handle/shared-view Red, at `14:02:51Z`: the expanded real test returned
   `2 failed` because `InstallationResult` had no stable installation reference
   or revalidating process-observation handle.
3. Direct real process Green, at `14:03:25Z`: the same file returned
   `2 passed`. It independently rechecked the live executable and proved the
   shared process-location view kept account association absent.
4. Real registry Red/Green:

   ```bash
   python -m pytest \
     backend/tests/integration/registry/test_ollama_installation_reconciliation.py \
     -q --tb=short
   ```

   Red at `14:04:16Z`: the typed Ollama installation discovery module did not
   exist. Green at `14:04:41Z`: `2 passed` against a migrated real SQLite file,
   including idempotent installation reconciliation and no account candidate.
5. Durable M04/M06 Red/Green:

   ```bash
   python -m pytest \
     backend/tests/integration/collection_control/test_ollama_runtime_run.py \
     -q --tb=short
   ```

   Red at `14:05:05Z`: `run_ollama_runtime_collection` did not exist. Green at
   `14:06:14Z`: `1 passed`; current real observations committed to migrated
   temporary SQLite without account/model fields.
6. Authenticated real HTTP, at `14:07:15Z`: `1 passed`. The production loopback
   service returned both persisted `/api/v1/processes?provider_key=ollama` and
   current `/api/v1/process-locations` values with unresolved account linkage.
7. Refactor regression, at `14:08:26Z`: `126 passed`, `1 skipped`, `2 failed`.
   The failures were unrelated live prerequisites:
   `m4_explicit_owner_selection_required` and the current default Claude version
   no longer matching its exact admitted version (`claude_version_unverified`).
   A separate provider live batch returned `20 passed`, with four Claude/Codex
   failures caused by their current default versions being outside the exact
   admitted tuples. No provider profile was changed to force those tests green.
8. Final focused implementation set: `20 passed in 14.85s`. This covered the
   real Ollama installation and process boundary, registry reconciliation,
   durable collection/recovery, authenticated current and persisted HTTP views,
   and the shared Linux selector policy. Changed-file Ruff lint and format,
   `git diff --check`, `AUTO-DOCS-CHECK`, and limited local
   `AUTO-GIT-PREFLIGHT` also passed.

`AUTO-QUALITY` was run but did not reach its static commands: it failed closed
with `minimum_m1_local_control_failed` because an isolated Git worktree does not
contain the Git-ignored `backend/.venv` or `frontend/node_modules` admitted
toolchain directories. The focused checks used the repository's existing pinned
backend interpreter explicitly. Full canonical quality remains required after
integration into a checkout with both admitted toolchain directories.

## Contract and version impact

- A03 Ollama adapter implementation version: `1.0.0` to `1.1.0`.
- A04 Linux process adapter implementation version: `1.1.0` to `1.2.0`.
- Provider tuple: exact Ollama CLI `0.24.0`, Linux `x86_64`.
- Compatible existing contracts: `CTR-REG-004`, `CTR-COL-002/006`, and
  `CTR-RUN-001/002/006`. The API and runtime schemas are unchanged.
- No database migration, dependency, generated-client change, license change,
  credential handling, or provider-state write was introduced.

## Open acceptance

This work contributes real evidence to `AC-PROC-001`, `AC-PROC-003`, and
`AC-PROC-004`. It does not close `AC-PROC-002` or all of `M6-A06`: OS parent PID
alone is not an Ollama model/agent hierarchy, the naturally observed executable
does not prove daemon versus active client or active work, and no safe source
currently links it to a loaded model or cloud account. Those relationships stay
Unknown until independent real evidence exists. Built-browser and second-host
verification are **Not Run** for this increment.

Integration verification on `m6-next` after cherry-picking the process
contribution: 47 focused live Ollama process, real SQLite registry/runtime,
authenticated HTTP and collection-control tests passed. The running dashboard
was not restarted; its `/login` endpoint returned HTTP 200. The contribution
remained intermediate at that revision because no production lifecycle invoked
durable Ollama collection.

## Production lifecycle increment

The follow-up Red ran the real production lifespan against migrated temporary
SQLite and failed with zero reconciled Ollama installations; the separate
failure-isolation test failed because `OllamaRuntimeCollectorV1` did not exist.
Green wires one optional collector into the authenticated service lifespan. It
uses scheduled M04 admission (`internal_scheduler`, no owner principal or
idempotency claim), recovers pending commits once, reconciles the exact
installation only when absent, and follows the existing five-minute unknown-
activity cadence with a matching five-minute freshness lease. Expected
installation, database, or exact-process failures produce one safe status and a
five-minute in-memory backoff rather than stopping HTTP or hot-looping provider
discovery. The M03 Ollama manifest remains unpublished and unknown.

The neutral live query now starts its three-second deadline before discovery,
runs provider discovery concurrently, and does not label a successful
Claude/Codex scan truncated merely because optional Ollama is unavailable. A
deadline-expired unknown discovery scope remains explicitly truncated. A
complete exact Ollama scan with no matching same-user process is a valid empty
observation; the live stopped/idle boundary was **Not Run** because user
processes were not stopped for testing.

Final focused lifecycle, real SQLite/API, exact process, recovery, association,
and compatibility set: `34 passed in 14.94s`. Changed-file Ruff lint and format
and `git diff --check` passed. The existing provider-neutral Sessions/Overview
table already renders persisted Ollama rows; its real browser scenario was
extended but is **Not Run** in this isolated worktree and remains required after
integration. Capability admission, model/process relationship, browser proof,
and other-host coverage remain open.
