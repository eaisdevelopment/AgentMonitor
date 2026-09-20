# V1-M1 hosted CI and clean-runner evidence

- Evidence ID: `M1-CI-2026-09-20`.
- Scope: approved `ST-FND-002` hosted execution and M1 completion gate; no V1-M2 work.
- Requirements: `NFR-TEST-001/002`, `NFR-API-002`, `NFR-DOC-001`, `NFR-LIC-001`; acceptance `AC-TEST-001/002/004/006`; scenarios `FND-CI-001/002`, `FND-TEST-001`, `FND-UI-001/002`.
- Contract impact: `CTR-FND-008` V1 evidence and `CTR-UI-001` V1 test consumer; no public API, database, configuration, or event contract change and no migration.
- Recorder: Codex, 2026-09-20. The independent CI-boundary reviewer performed a read-only review of the runner/browser correction; the hosted result is verified separately by the real GitLab API.

## Red

| Boundary | Real command or run | Observed result before correction |
|---|---|---|
| Private Git transport | Unauthenticated `git ls-remote` against the configured private project | Exit 128. Authenticated `tools/git/gitlab_ci.py probe` then passed without placing the token in a URL or command argument. |
| Missing clean-runner toolchain | Hosted pipeline `2865413501`, `foundation_test` | Failed at `AUTO-TEST: FAILED — admitted_backend_toolchain_missing`; the other three jobs were skipped. |
| Clean checkout without owner-local M0 files | Real non-root Docker checkout, `AUTO-TEST` and `AUTO-M0-G1-EXIT` | Original broad test discovery failed on absent ignored M0 assets; the exact M0 gate errored rather than returning Blocked. The corrected M1 selector runs only applicable M1 tests and reports the owner-local M0 suite Not Run and exact gate Blocked separately. |
| Downloaded toolchain in docs scan | Real clean Docker checkout after toolchain bootstrap, `AUTO-DOCS-CHECK` | Downloaded Node Markdown was treated as project documentation; excluding `.ci-tools` removed the false link failures. |
| Browser selection and evidence | Real clean Docker browser test and independent read-only review | The image has Chromium, not branded Chrome. After initial CI selection, the reviewer found that default headless-shell execution differed from the full Chromium binary being versioned. `channel: "chromium"` now selects the full executable that the evidence producer measures. |
| Git ownership on hosted runner | Hosted pipeline `2865426758`, `foundation_test`; then a real Docker checkout owned by a different UID | Hosted test failed two M1 tooling tests: local `git clone` returned 128 and `AUTO-QUALITY` failed its source control. The mismatched-owner Docker run reproduced `git ls-files` and `git clone` exit 128. Exact checkout and `.git` `safe.directory` entries made both real commands pass; no wildcard or global trust of other directories was added. |
| GitLab CI lint routine | `python3 tools/git/gitlab_ci.py lint` before the action existed | Exit 2, invalid action. The action now calls the configured private project's real lint API and requires four named jobs. |

No secret-bearing raw GitLab job trace is copied into this record. The status and failure signatures above were selected from the real API result.

## Green and refactor

On the development checkout, `AUTO-TEST` exited 0 with 67 tools tests, 277 backend tests, two real system-Chrome browser tests, and real SQLite, migration, loopback HTTP, generated-client, and production-build checks. `AUTO-QUALITY`, `AUTO-BUILD`, `AUTO-DOCS-CHECK`, `AUTO-PLAN-CHECK`, npm application/tooling typecheck, and GitLab CI lint each exited 0. The separate owner-local M0 exact-digest gate remained **Failed, exit 2**, outside M1.

A fresh local Git clone was mounted into the pinned Playwright image as UID `1001:1001` with a different repository owner, no `.env`, and no owner-local M0 files. After exact Git trust and hash-verified frozen bootstrap, `AUTO-TEST` exited 0: 47 applicable M1 tools tests, 277 backend tests, two real full-Chromium browser tests at 1920×1080 and 390×844, file-backed SQLite/migrations, loopback FastAPI, OpenAPI/client drift check, and production Vite build. `AUTO-QUALITY`, `AUTO-BUILD`, and `AUTO-DOCS-CHECK` also exited 0. M0 local tools were **Not Run** and its exact approval gate was **Blocked, exit 3** in that clean container, explicitly outside M1. The evidence producer recorded Playwright Chromium `153.0.8010.12`; the independent reviewer checked that the launch channel and versioned executable resolve to the same installed binary.

The runner is pinned to a digest and runs non-root. Node and uv archives are SHA-256 verified before extraction; Python dependencies and frontend packages are installed from frozen locks. This is a real clean install, not a copied local environment. GitLab CI lint returned `valid=true` with the four required jobs. The correction was rerun under both the local workstation and the real mismatched-owner container before a non-forced branch push.

## Real hosted result

GitLab.com hosted pipeline `2865439962` for code commit `3705355048027216f05d058e36d23d70f731679a` on `codex/v1-m1` completed with aggregate status **success**. The real GitLab API reported all four required jobs **success**: `foundation_test`, `foundation_quality`, `foundation_build`, and `foundation_docs`. The test job used the real clean checkout and exact CI image/toolchain above; the other jobs ran the canonical quality, build, and documentation commands. Earlier pipelines `2865413501` and `2865426758` remain **Failed** historical Red evidence, not concealed passes.

An `AUTO-TEST` job cannot certify its own enclosing pipeline, so its emitted `FND-CI-001` row remains `Not Run`; the external pipeline aggregate above is the `FND-CI-001` hosted evidence. The checked-in documentation-only acceptance commit must also have its own hosted pipeline verified before the final M1 handoff claims a green final checkout.

## Security, privacy, license, and remaining boundaries

The configured project was verified private. The Git remote contains no credential, `main` was not changed, no `.env` entered the clean runner, and no token was stored as a CI variable or printed. No provider state, default profile, prompt, response, source content, account credential, or running agent was accessed. No mock, fake, stub, emulator, recording, seeded telemetry, placeholder UI value, disabled test, or hardcoded pass was used.

The test-only image and exact Node/uv inputs are reviewed in [the runner admission](../dependencies/m1-ci-runner-admission.md). The known development-browser advisory and release-only binary SBOM/notices remain follow-ups, not a claim of cleared release security. `T5` workstation platform, `T6` live provider/account, `T7` native lifecycle, full secret/SAST/vulnerability scanning, and release publication remain **Not Run**; the separate owner-local M0 approval is **Failed** on the current development checkout. The earlier bounded reviewer also left full HTTP/background log-sink propagation **Not Run**; M1 covered its constructor seam only. All five approved M1 Stories have local review/evidence and the code-bearing hosted run has passed; this is foundation acceptance, not delivery of monitoring features.
