# V1-M2 post-audit security and test-integrity correction

- Evidence ID: `M2-AUDIT-FIX-2026-09-21`.
- Scope: `M2-AUD-01..04` from the local M2 code audit; no M3 capability.
- Owners: P01 transport/security, P02 browser test, foundation automation; M01 is a contract consumer, not a changed implementation.
- Requirements/acceptance: `FR-IAM-007`, `NFR-SEC-001`, `NFR-TEST-001/002`, `API-BROWSER-006`, `M01-HTTP-019`, `M01-SEC-008`, `AC-TEST-003/006`. `AC-TEST-001` remains subject to historical-deviation disposition below.
- Contracts: [ADR 0012](../decisions/0012-cookie-read-origin-proof.md) amends `CTR-API-002` V1 cookie-read admission. `CTR-IAM-003/005`, route/status/schema shapes, database, and configuration remain unchanged. The OpenAPI/client source-hash artifacts are regenerated, not hand-edited.
- Recorder/date: Codex, 2026-09-21. Canonical local gate completed on the changed source; independent QA countersignature remains pending.
- Implementation commit: `77eb9b5` on `codex/v1-m2`; local tracked worktree clean after commit. A documentation-only handoff amendment records this inventory.

## Change inventory and handoff

- P01 primary owner: `backend/src/agentmonitor/api/transport.py`; real HTTP/client tests in `backend/tests/integration/api/test_origin_policy.py`, `backend/tests/integration/api/test_iam_http.py`, and `frontend/tests/client/real-iam-http.mjs`.
- P02 verification consumer: `frontend/tests/browser/p02/hostile_resource.mjs` and `frontend/tests/browser/p02/run_browser.py`.
- Foundation quality/evidence consumer: `tools/automation/implementations/auto_quality.py`, `tools/automation/implementations/auto_test.py`, and `tools/automation/test_run.py`.
- Regenerated metadata-only artifacts: `contracts/openapi/agentmonitor-v1.json` and `frontend/src/generated/api/index.ts`.
- Maintained contract/status documentation: `docs/decisions/0012-cookie-read-origin-proof.md`, `docs/decisions/README.md`, `docs/evidence/m2-contract-freeze.md`, `docs/evidence/m2-st-api-002.md`, `docs/evidence/m2-st-ui-001.md`, this record, `docs/api/http-boundary.md`, `docs/architecture/security.md`, `docs/modules/react-dashboard.md`, and `docs/README.md`. The ignored owner-local `temp/M2_code_audit_report.md` has a post-fix addendum but is not a committed artifact.
- Rollback is a normal code revert plus matching generated metadata; no database migration or secret rotation is required. Do not restore the old cookie-read allowance without a new security decision and real hostile-resource test.

## Test inventory and status

| Scenario | Real boundary | Status at recording | Limit |
|---|---|---|---|
| `M01-HTTP-019`, `API-BROWSER-006` HTTP | Fresh Alembic SQLite, production Argon2 bootstrap, Uvicorn, cookie/bearer HTTP | Passed: 2 focused Origin-policy tests | Browser resource persistence is separate below. |
| Hostile resource/browser persistence | Production build, Chrome, second real loopback origin, actual 62-second wait, migrated SQLite | Passed: ordinary and no-referrer image status 403; persisted activity, idle deadline, and version unchanged | Local supported Chrome, not every browser or remote profile. |
| Canonical selector | Real automation source and installed scenario path | Passed focused governance test | Full `AUTO-TEST` pending below. |
| `.mjs` anti-interception control | Real repository source inventory plus pure source-policy test | Passed focused governance tests | Bounded static control, not SAST or proof that all tests are authentic. |
| Generated client after security rule | Node generated client against real Uvicorn/SQLite | Passed focused integration test | The non-browser cookie caller now sends exact Origin. |
| Representative historical UI regression sensitivity | Separate detached real worktree with one controlled source mutation, production Vite build, migrated SQLite, Uvicorn, Chrome | Passed sensitivity check: real `auth` browser scenario failed against the mutant and passed against unmodified source | Does not create a historical pre-fix Red for the original Story 5 correction. |
| Full M2 canonical gate | Current checkout, installed Chrome 152.0.7977.75 | Passed: `AUTO-TEST` exit 0, 74 tooling tests, 514 backend tests, generated client/build, M1 Chrome, all M2 Chrome including natural expiry and both hostile-origin suites | M0 G1 separately Failed; T5/T6/T7/hosted Not Run. |
| Fast local gates | Current checkout | Passed: `AUTO-QUALITY`, `AUTO-BUILD`, `AUTO-DOCS-CHECK`, `AUTO-PLAN-CHECK` | Local-only scopes; documentation/planning were rechecked after the full test result was recorded. |

## Red evidence

- `backend/.venv/bin/python -m pytest backend/tests/integration/api/test_origin_policy.py::test_hostile_origin_cannot_revoke_a_real_cookie_session -q --tb=short` exited 1 before the transport change: the headerless same-site cookie resource GET returned 200, not the required 403.
- `backend/.venv/bin/python frontend/tests/browser/p02/run_browser.py hostile_resource --no-build` exited 1 before the transport change after 62 actual seconds: `hostile_resource_changed_session_state`. The test used a fresh migrated file DB, real Chrome and server, and read the three persisted session fields after the hostile request. Earlier browser-script errors during development were harness failures, not counted as behavioral Red.
- `python3 -m unittest tools.automation.test_run.AutomationRoutineTests.test_m2_local_suite_selection_covers_real_backend_and_browser_boundaries` exited 1 because `p02_hostile_resource` was absent from the canonical selector.
- The two focused scanner tests exited 1 before the scanner fix: `checked_source_paths` did not exist and the pure source policy accepted a browser response interception.
- `python3 -m unittest tools.automation.test_run.AutomationRoutineTests.test_m2_local_evidence_does_not_claim_universal_historical_tdd` exited 1 because the bounded M2 acceptance-ID producer did not exist; the old M2 Passed row included `AC-TEST-001` despite documented historical gaps.
- The first 36-case real IAM HTTP run after fail-closed cookie-read enforcement had one real generated-client failure (`current_session_failed`) because its non-browser cookie GET omitted Origin. The client integration caller now supplies the exact Origin. This failure was not mislabeled as a server regression pass.

## Green evidence

- The focused real Origin-policy file passed (`2 passed`), including denial of same-site and unclassified cookie GETs, same-origin and direct-navigation acceptance, hostile unsafe denial, and origin-independent scoped bearer.
- The built Chrome hostile-resource scenario passed after 62 actual seconds. Chrome's network events showed status 403 for both an ordinary cross-port image and an image with `no-referrer`; the Python runner verified one real session with unchanged `last_activity_at`, `idle_expires_at`, and `record_version` in SQLite. The initial browser `response` event could not observe CORP-blocked image statuses, so the final test reads only CDP request IDs/status codes, never cookies or credential headers.
- The focused real generated-client/Uvicorn/SQLite test passed (`1 passed`) after its non-browser cookie GET sent canonical Origin.
- Focused scanner and canonical-selection tests passed after `.mjs` inclusion, page/context route-interception policy, and fail-closed selector wiring.
- `python3 tools/automation/run.py AUTO-TEST` exited 0 on the changed source at 13:44 UTC. It ran 74 tooling tests, 514 backend tests (no deselection reported), the compatible 13-operation generated OpenAPI/client check, production Vite build, two real M1 Chrome cases, nine quick M2 browser workflows, real ≥61-second touch/logout, real ≥1,800-second idle expiry, the original hostile-origin browser scenario, and the new two-image 62-second hostile-resource/SQLite scenario. The `M2-LOCAL-001` Passed row cites `AC-UI-001`, `AC-TEST-003/006`, not universal `AC-TEST-001`; it marks T5/T6/T7 and hosted CI Not Run, and records separate M0 G1 approval Failed (exit 2).
- `AUTO-QUALITY` and `AUTO-BUILD` exited 0 on the production/test checkout. After the full result was recorded, `AUTO-DOCS-CHECK` (211 Markdown files), `AUTO-PLAN-CHECK`, and `git diff --check` each exited 0. No production, test, generated-contract, or migration byte changed after the full `AUTO-TEST` run began.

## Refactor evidence

The hostile browser probe is now a maintained P02 scenario selected directly by `AUTO-TEST`, not an ignored local audit script. The P01 guard rejects before any M01 call; no IAM policy or database adapter was altered. The source-control checker scans installed `.mjs` scenarios and rejects route interception in pure policy tests. It does **not** write a constructed malicious `.mjs` file: the repository's no-constructed-I/O invariant takes precedence over that suggested audit technique. A real existing `.mjs` path is asserted in the actual source inventory; constructed interception snippets are used only in a pure no-I/O policy test.

## Historical TDD exceptions and disposition

The original Story 5 record already names post-implementation Green-only verification and QA corrections without independently captured pre-fix executable Reds. Exact affected corrections include false logout, route focus, history replacement, incompatible initialization mapping, and outcome-unknown messaging; setup, revocation, return-route, responsive, and denied-clipboard scenarios were also added after adjacent production behavior existed. A fabricated historical Red is prohibited. Current real browser tests can protect behavior but cannot retroactively satisfy “Red before code” for those changes.

The canonical `M2-LOCAL-001` Passed row no longer cites `AC-TEST-001`; it cites only `AC-UI-001`, `AC-TEST-003`, and `AC-TEST-006` when those local gates execute. For a representative false-logout correction, a detached worktree at baseline `f2f4626` changed only `DashboardApp.tsx`'s missing-CSRF handler to expire the UI session. Its production Vite build passed, and the real `auth` Chrome scenario exited 1 at `csrf_missing_fail_closed`; the same scenario on the unmodified main checkout exited 0. The isolated worktree was removed after the check. This proves the present regression can detect that specific false-logout behavior; it does **not** manufacture a historical pre-fix Red or verify every post-implementation UI correction. Explicit owner disposition on those historical gaps remains pending. Until then, this evidence does **not** claim universal `AC-TEST-001` compliance or unqualified M2 reacceptance.

## Security, privacy, migration, and remaining boundaries

No new package, table, migration, provider state, default profile, agent process control, or remote exposure was introduced. The test-created administrator uses OS-random input passed over a private pipe; the regression retains only status codes, elapsed-time facts, and session-field equality, not credential values or raw headers. Cookie traffic from another loopback port is denied before session activity can change. Host-only cookies are still port-shared as disclosed in ADR 0012.

The staged default-rule Gitleaks 8.30.0 scan exited **1**, with exactly one `generic-api-key` finding at `frontend/src/generated/api/index.ts:3`. Read-only inspection showed the matched value is the generator's public 64-hex-character `openapiArtifactSha256` metadata, not a credential. This is a reviewed false positive, **not** a Passed scanner result. No `.gitleaks.toml` or broad allowlist was added because M0's default-rule scanner behavior must remain intact. A full release secret/SAST scan remains Not Run.

M0 G1 exact-digest approval remains separate and Failed on the development checkout. T5 workstation, T6 provider/account, T7 installed lifecycle, macOS, hosted M2 CI, full SAST/vulnerability/SBOM/release controls, and the owner's installed-service login/recovery remain Not Run; this local correction does not convert them to Passed.
