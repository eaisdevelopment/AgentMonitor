# Test evidence: M3-FIX-009 capacity-history pagination

- Evidence ID: `M3-FIX-009`
- Module/plan/increment: P02 React dashboard / V1-M3 audit repair
- Requirements/acceptance IDs: `FR-HIST-002`, `AC-HIST-001`, `AC-UI-006`, M3 Task 6
- Contract versions: consumes `CTR-CAP-006` V1 and the existing P01 `capacity_list_history_v1` cursor operation; no contract change
- Commit/worktree reference: uncommitted M3-FIX-009 worktree
- Recorder/date: Codex sub-agent / 2026-09-24

## Test inventory and status

| Test/scenario ID | Layer | Real dependencies | Status | Evidence reference | Notes |
|---|---|---|---|---|---|
| M3-FIX-009-PURE-001 | Pure | Production TypeScript pagination functions loaded directly by Node | Passed | Green command below | Constructed pages are used only for deterministic no-I/O state behavior. |
| M3-FIX-009-TYPE-001 | Static | Production frontend TypeScript projects | Passed | `npm --prefix frontend run typecheck` | Both node and app projects passed. |
| M3-FIX-009-BUILD-001 | Build | Production Vite build and installed dependency tree | Passed | `npm --prefix frontend run build` | 33 modules transformed; production assets emitted. |
| M3-FIX-009-BROWSER-001 | Browser | Real migrated file SQLite, production loopback service, real IAM cookie, built frontend, Chrome | Passed | `backend/.venv/bin/python frontend/tests/browser/p02/run_browser.py monitoring_dashboard --no-build` | Empty-database dashboard/regression path passed; account detail was correctly reported Blocked because this isolated database has no real account. |
| M3-FIX-009-QUALITY-001 | Repository quality | Canonical `AUTO-QUALITY` | Failed | `python3 tools/automation/run.py AUTO-QUALITY` | Frontend checks were not reached because Ruff found six pre-existing/concurrent out-of-scope backend/automation formatting errors listed below. |
| M3-FIX-009-LIVE-002 | Owner/live browser | Owner database with a naturally occurring first page of 200 rows plus a continuation cursor | Not Run | `frontend/tests/browser/p02/populated_monitoring_dashboard.mjs` | No owner credential or confirmed greater-than-200 real history set was available to this isolated task. The test now exercises and reconciles the second page only when the real API exposes a cursor; it never inserts telemetry. |

## Red evidence

The behavioral Red was run before the pagination implementation:

```text
node --experimental-strip-types --experimental-loader ./frontend/tests/pure/typescript-source-loader.mjs ./frontend/tests/pure/capacity-history-pagination.mjs
exit 1
SyntaxError: ... client.ts does not provide an export named 'appendCapacityHistoryPage'
```

This failed for the expected missing production pagination behavior, not for a missing package or test setup fault.

A later fail-closed cursor-invariant Red was also run before its production correction:

```text
node --experimental-strip-types --experimental-loader ./frontend/tests/pure/typescript-source-loader.mjs ./frontend/tests/pure/capacity-history-pagination.mjs
exit 1
AssertionError: actual { kind: 'complete' }; expected { kind: 'invalid' }
```

The failing input was the contradictory page metadata `has_more=false` with a non-null cursor.

## Green evidence

After the minimum implementation and after the cursor-invariant correction, the same command exited `0`:

```text
CAPACITY HISTORY PAGINATION PURE: PASSED
```

The production helper proves that one page is appended without replacing or transforming earlier observation objects, rejects selector drift, rejects duplicate observation IDs, distinguishes complete/available/invalid continuation states, and rejects a missing initial sequence.

## Refactor evidence

The following final checks passed after UI integration:

```text
npm --prefix frontend run typecheck
# exit 0

npm --prefix frontend run build
# exit 0; 33 modules transformed

node --check frontend/tests/browser/p02/populated_monitoring_dashboard.mjs
node --check frontend/tests/pure/capacity-history-pagination.mjs
node --check frontend/tests/pure/typescript-source-loader.mjs
# exit 0

git diff --check -- frontend/src/shared/api/client.ts \
  frontend/src/features/command/CapacityPanel.tsx \
  frontend/tests/pure \
  frontend/tests/browser/p02/populated_monitoring_dashboard.mjs
# exit 0
```

## Real-system evidence

The regression browser command used a real migrated file-backed SQLite database, production FastAPI/Uvicorn loopback service, real generated-client HTTP, real IAM login/cookie, the production frontend build, and Chrome. It exited `0`:

```text
P02 MONITORING DASHBOARD: PASSED — real database/API/browser; account detail BLOCKED — no real registered account in the isolated database
P02 BROWSER: PASSED — monitoring_dashboard
```

The owner-populated script now waits for an actual `capacity/history` response containing an opaque cursor, verifies HTTP 200, the 200-row bound, unique exact observation IDs, preservation of the first page, chart/table lineage equality, and the visible two-page state. Because no naturally occurring greater-than-200 owner dataset and credential were available in this task, that scenario remains **Not Run**, not Passed.

The canonical repository-wide quality command was run and failed before its
frontend steps because Ruff reported out-of-scope worktree findings:

- unsorted imports in `backend/src/agentmonitor/adapters/persistence/runtime_observation/sqlite/repository.py`;
- unsorted imports in `backend/tests/adapters/providers/claude/test_otel_runtime_static.py`;
- unsorted imports in `backend/tests/runtime_observation/integration/test_real_session_tree_read.py`;
- unsorted imports and two lines longer than 88 characters in `tools/automation/implementations/auto_m3_exit.py`.

M3-FIX-009 did not modify those files. This failed gate is not represented as a
pass; the scoped frontend typecheck, build, syntax, diff, and browser checks are
reported separately above.

## Integrity declaration

No mock, fake, stub, emulator, response interception, recorded response, demo account, seeded telemetry, placeholder dashboard value, hardcoded pass, disabled assertion, or test-only production branch was used. Constructed page values exist only in the pure no-I/O pagination test. The browser test consumes only the real service and real persisted owner data when available.

## Data and secret review

No credential, provider payload, prompt, response, source content, personal account identifier, or arbitrary environment value was recorded. The opaque cursor remains in component memory and the existing authenticated request only; it is not displayed or stored in browser storage. User-facing failures use fixed safe messages and retain already verified observations.

## Contract, migration, dependency, and operations impact

- Contract: no new or changed backend/OpenAPI/generated contract. P02 now consumes the already published optional cursor in `CTR-CAP-006`/P01.
- Compatibility: nonbreaking. The initial request remains identical; each owner click issues at most one additional request with the original subject, metric, series, start, and end filters.
- Migration: none.
- Dependencies/licenses: none.
- Operations: no collection occurs on GET and no provider or process is changed. A pending continuation is aborted on component cleanup or account reload.
- Documentation: this evidence record only; no plan or contract documentation changed.

## Conclusion and residual gaps

The dashboard no longer labels the first 200 rows as the complete 365-day view. It always exposes the loaded observation/page count and whether another page remains, offers one bounded owner-triggered cursor request at a time, accumulates only exact returned points, and fails closed on page incompatibility. Full owner-browser proof with a naturally available greater-than-200 history remains `Not Run` and must not be promoted to Passed until that real condition exists.
