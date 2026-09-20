# V1-M1 post-audit fix evidence

This is the historical local reacceptance snapshot before GitLab access was supplied. The later real clean-runner and hosted-CI closure is recorded in [M1 hosted CI evidence](m1-hosted-ci.md); the `Not Run` hosted status below describes the earlier checkout, not the current acceptance result.

- Evidence ID: `M1-AUDIT-FIX-2026-09-20`.
- Scope: foundation automation, frontend typecheck, browser assertions, and evidence metadata. No V1-M2 features.
- Requirements: `NFR-TEST-001/002`, `NFR-API-002`, `NFR-LIC-001`; acceptance `AC-TEST-001/002/004/006`.
- Contracts: `CTR-FND-008` V1 evidence producer; `CTR-FND-005/007` and `CTR-UI-001` V1 consumers unchanged. No public contract, API, database, or migration version change.
- Worktree: branch `codex/v1-m1`, baseline `9a05cc2`, uncommitted fix batch at initial recording. Recorder: Codex. Bounded independent fix review passed on 2026-09-20; generated runtime evidence rows still explicitly record their own reviewer as pending.

## Red

The following failures were observed before their corresponding fix. These are sanitized summaries, not reconstructed output:

| Behavior | Real command/test | Observed expected failure |
|---|---|---|
| App TypeScript included in canonical command | `python3 -m unittest tools.automation.test_run.AutomationRoutineTests.test_frontend_typecheck_covers_application_and_tooling` | Assertion: `tsconfig.app.json` absent from the published `typecheck` command. The direct app compiler also failed TS7016/TS7026; after declaration admission, it exposed TS2882 for CSS until Vite client types were enabled. |
| Pure dependency/source policy extracted from real validators | targeted `tools.automation.test_run` policy tests | ImportError for missing production policy functions before extraction. |
| Evidence rows use published V1 type | targeted `test_evidence_rows_validate_v1_contract_and_unrun_provenance` | `ModuleNotFoundError: evidence` before the helper existed. |
| Exact runtime version extraction | targeted `test_evidence_versions_match_the_real_node_command` | Node reported `22.23.2`; the initial extractor incorrectly emitted `23.2`. The parser was corrected and the same real command passed. |
| Broader tools suite | `python3 -m unittest discover -s tools -p 'test_*.py'` | Initially two M0 exact-digest assumptions failed; later integration runs exposed evidence import and format errors, then a missing documentation target. The M0 approval itself remains Failed separately; tests now assert its real exit instead of assuming approval. |
| Browser console and asset chain | `python3 tools/automation/run.py AUTO-TEST` | The new real Chrome checks at both viewport widths failed on a 404 console error. The app lacked a favicon asset; adding a bundled same-origin favicon removed the error. |
| Local Git commit readiness without GitLab remote | `python3 -m unittest tools.git.test_preflight.GitPreflightTests.test_local_commit_preflight_does_not_require_a_remote` | Failed because the real checkout's preflight incorrectly listed missing remote/upstream as local-commit blockers. |
| Canonical Git preflight scope | `python3 -m unittest tools.automation.test_run.AutomationRoutineTests.test_git_preflight_catalog_does_not_claim_remote_readiness` | Failed because catalog status was `operational` rather than `operational_limited`; the canonical pass overclaimed upstream readiness. |

The browser assertions uncovered the real missing-favicon 404 and drove the bundled asset fix. The anti-telemetry assertions passed before that change; there is no claim that the app previously displayed fabricated metrics.

## Green

The targeted app-typecheck and V1 evidence-policy tests passed after the corresponding implementation. A separate regression runs the published command against an isolated copy of the real app and the exact pre-fix app TypeScript config (`frontend/tests/typecheck/tsconfig.app.pre-fix.json`); it exits nonzero with the real `TS2882` CSS import error. The current production config passes. The pure source, manifest, installed-inventory, stale-optional-package, and exact direct-license policy tests passed against the production policy functions. The real checkout is scanned by `AUTO-QUALITY`; the pure tests do not constitute live package/license proof.

## Refactor

The prior tests that wrote tracked source and constructed temporary installed-package metadata were removed. Two concurrent real subprocesses now exercise the pure policy tests while checking tracked file modification times before/after. `AUTO-TEST` discovers the complete tools suite and reports the separate M0 G1 exact-digest gate independently. Repeated evidence dictionaries were replaced with a single `TestEvidenceSummaryV1`-validated producer. The helper permits `Passed` only with measured tool versions, emits no Red/Green/refactor references on `Not Run`/`Failed`, and identifies reviewer status as pending rather than claiming a review occurred.

The Git preflight now separates local-commit checks from explicit push/release checks. Canonical `AUTO-GIT-PREFLIGHT` passes with a visible limited scope on this real checkout; `python3 tools/git/preflight.py --operation push` remains Blocked (exit 3) because no remote/upstream is configured. The catalog is bound into the synchronized planning snapshot. Independent read-only review passed for the catalog/snapshot coherence and A1–A5 fix scope; it did not certify hosted CI or the separate M0 G1 gate.

## Real-system verification

Executed on 2026-09-20 against the real worktree:

| Command | Exit/status | Bounded result |
|---|---|---|
| `python3 tools/automation/run.py AUTO-TEST` | 0 / Passed after the final catalog rebind | 66 tools tests, 277 backend pytest cases, real file-backed SQLite/migrations, loopback FastAPI, OpenAPI/client drift check, production Vite build, and 2 system-Chrome/Playwright tests at 1920×1080 and 390×844. No skips reported. Separate M0 G1 status was explicitly Failed (exit 2). |
| `python3 tools/automation/run.py AUTO-QUALITY` | 0 / Passed | Backend lint/format/mypy, module boundaries, generated client, npm app+tooling TypeScript, lock and installed-metadata checks, local minimum source controls, Vite build. |
| `python3 tools/automation/run.py AUTO-BUILD` | 0 / Passed | Existing locked inputs, app+tooling TypeScript, generated client, production frontend artifact. |
| `python3 tools/automation/run.py AUTO-DOCS-CHECK` | 0 / Passed | Local documentation links/routing resolved (182 Markdown files at that run). |
| `python3 tools/automation/run.py AUTO-PLAN-CHECK` | 0 / Passed | Synchronized planning baseline. |
| `python3 tools/automation/run.py AUTO-GIT-PREFLIGHT` | 0 / Passed, limited scope | Real local worktree/root/branch, configured identity, tracked `.env` absence, and readable status; remote/upstream checks explicitly Not Run for local commit. |
| `npm --prefix frontend run typecheck` | 0 / Passed | Strict app and Vite config projects. |
| `npm --prefix frontend audit --audit-level=low` | 0 / Passed for npm registry query | Reported zero advisories at query time; does not substitute for full dependency security gate. |

After the final evidence edit, `AUTO-DOCS-CHECK`, `AUTO-PLAN-CHECK`, `AUTO-QUALITY`, `AUTO-BUILD`, and `git diff --check` each exited 0. Explicit `python3 tools/git/preflight.py --operation push` remained Blocked (exit 3); no remote/upstream was fabricated.

| Boundary | Status | Exact limit |
|---|---|---|
| Hosted GitLab pipeline | Not Run | No configured remote/runner or observed hosted job. `.gitlab-ci.yml` dispatches commands but does not bootstrap a clean runner. |
| M0 G1 exact-digest approval | Failed | Current checkout differs from approved subject; no approval record was rewritten. Outside V1-M1 acceptance. |
| Live provider/account and native lifecycle | Not Run | Outside M1; no provider credentials or profiles accessed. |
| Fresh frozen install, full secret/SAST/vulnerability scans, release SBOM/notices | Not Run | Local metadata/regex controls and existing installed graph are narrower; no release-readiness claim. |

## Integrity and privacy

No mock, fake, stub, emulator, recording, demo account, seeded telemetry, placeholder dashboard value, disabled assertion, or swallowed failure was introduced. Pure constructed policy inputs have no I/O. Live tests use isolated real SQLite files, loopback HTTP, built assets and a real browser. Evidence uses only allowlisted command outcomes/version tokens; it contains no secret, provider payload, prompt, source-code content, account identifier, or process environment value. No default Claude, Codex, or Ollama profile was modified.

## Conclusion

The M1 local acceptance commands above passed. Hosted CI and release-only controls remain Not Run; M0 G1 requires a separate owner-approved exact subject if its approval must apply to this checkout. No V1-M2 work was started.
