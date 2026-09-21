# ST-IAM-001 M01 bootstrap/persistence handoff and test evidence

- Status: **Accepted for M2 integration** by root plus independent specification/quality reviewers on 2026-09-20; not an M2 milestone completion claim.
- Owner/date: M01 Story worker, 2026-09-20.
- Scope: `ST-IAM-001`; `FR-IAM-001/002/005`, `NFR-DATA-001`, `NFR-SEC-001`, `NFR-PRIV-001`, `NFR-COMP-001`; `M01-PURE-001/002/005`, `M01-CRYPTO-001/002/004`, `M01-DB-001/002`, `M01-SEC-006`, `M01-OPS-001` partial.
- Contracts: `CTR-IAM-001/002/004/005/007/008` V1 and `CTR-DB-002` V1. Story 1 is the first producer implementation; later M01 Stories must review extensions to safe audit codes. No OpenAPI or UI contract changed here.

## Delivered behavior and files

Real Argon2id password policy/adapter, one-administrator application bootstrap, local no-echo controlling-TTY input, atomic file-backed SQLite repository, seven-table `v1_0100` Alembic revision, exact schema compatibility guard, and fresh-only migration behavior. Recovery repository transaction exists but no installed recovery command is exposed. The integration steward separately owns the fresh-init CLI (`composition/iam_fresh_init.py`) and automation/generated artifacts; this Story did not edit them.

Added: `backend/src/agentmonitor/contracts/identity_access_v1.py`; M01 `modules/identity_access/**`, `adapters/identity_access/**`, `adapters/persistence/identity_access/**`; `composition/iam_operator.py`; `backend/migrations/versions/v1_0100_m01_identity_access.py`; `backend/tests/identity_access/**`; `backend/tests/integration/identity_access/**`; this evidence and `docs/modules/identity-access.md`. Changed: `backend/pyproject.toml`, `backend/uv.lock`, `backend/migrations/catalog.toml`, shared SQLite `schema/compatibility.py`, and historical `backend/tests/persistence/sqlite/migrations/test_v1_0000.py`. No provider state, default profile, `.env`, GitLab remote, UI, P01 route, or M2 Story 2–6 source was touched. No Story commit was made before root review.

## Genuine Red → Green evidence

All commands run from the repository root; `backend/.venv/bin/python` uses the exact installed lock. Initial system-Python/module-path failures were environment setup failures and **are not counted as behavioral Red**.

| Behavior | Expected behavioral Red (exit 1) | Green |
|---|---|---|
| Pure creation policy | `PYTHONPATH=backend/src python3 -m pytest backend/tests/identity_access/test_password_policy.py -q`: missing `agentmonitor.modules` implementation | Same test file: 9 passed after initial policy implementation. |
| Real migration/bootstrap | `PYTHONPATH=backend/src backend/.venv/bin/python -m pytest backend/tests/integration/identity_access/test_bootstrap.py -q --tb=short`: three failures for absent IAM tables/repository and existing empty-file preflight | Same file: 3 passed after real Alembic/repository implementation; later expanded to concurrent singleton, independent salts, and schema refusal. |
| Real controlling TTY | `backend/.venv/bin/python -m pytest backend/tests/integration/identity_access/test_operator_tty.py -q --tb=short`: two failures, `agentmonitor.composition.iam_operator` missing | Same file: 2 passed after TTY adapter/composition; a subsequent real PTY failure exposed `getpass` incompatibility and was fixed with `termios`. |
| Recovery transaction | `backend/.venv/bin/python -m pytest backend/tests/integration/identity_access/test_recovery_transaction.py -q --tb=short`: `SqliteIdentityAccessRepositoryV1` lacked `recover_administrator` | Same file: 1 passed after atomic transaction implementation; active-credential revocation remains Not Run. |
| Contract pairing | `backend/.venv/bin/python -m pytest backend/tests/identity_access/test_contract.py -q --tb=short`: two `DID NOT RAISE` for invalid initialization/bootstrap pairings | Same file: 12 passed after invariants. |
| Incompatible state | `backend/.venv/bin/python -m pytest backend/tests/identity_access/test_password_policy.py::test_bootstrap_precondition_distinguishes_initialized_from_incompatible -q --tb=short`: missing `bootstrap_state_error` | Same test: 1 passed after explicit fail-closed policy. |
| Altered real SQLite schema and malformed Unicode | `backend/.venv/bin/python -m pytest backend/tests/integration/identity_access/test_bootstrap.py::test_altered_credential_schema_is_never_certified_writable backend/tests/identity_access/test_password_policy.py::test_password_policy_rejects_unencodable_unicode_without_exception -q --tb=short`: two failures, tampered schema returned `compatible`; unpaired surrogate raised `UnicodeEncodeError` | Same command: 2 passed after exact DDL guard and safe policy rejection. |
| Audit code closure | `backend/.venv/bin/python -m pytest backend/tests/identity_access/test_contract.py::test_security_event_view_refuses_unreviewed_codes -q --tb=short`: four `DID NOT RAISE` failures | Same four cases passed after current-producer code/metadata allowlist. |
| Real verifier malformed Unicode | `backend/.venv/bin/python -m pytest backend/tests/integration/identity_access/test_bootstrap.py::test_real_verifier_rejects_unencodable_candidate_without_exception -q --tb=short`: unpaired surrogate raised `UnicodeEncodeError` | Same test: 1 passed after adapter rejection. |
| Recovery outcome invariant | `backend/.venv/bin/python -m pytest backend/tests/identity_access/test_contract.py::test_recovery_outcome_refuses_failure_counts_and_noninteger_counts backend/tests/identity_access/test_contract.py::test_recovery_contract_includes_policy_violation_outcome -q --tb=short`: two failures, nonzero failure counts were accepted and policy-violation code was rejected | Same command: 2 passed after exact integer/zero-on-failure invariant and safe policy outcome. |
| Incompatible operator state | `backend/.venv/bin/python -m pytest backend/tests/integration/identity_access/test_operator_tty.py::test_operator_reports_incompatible_iam_without_prompt_or_mutation -q --tb=short`: one expected failure, unavailable marker absent because the CLI mislabeled incompatible as already initialized | Same real-DB/PTY test: 1 passed after explicit incompatible → `iam_repository_unavailable` mapping. |

The concurrency, distinct-salt, second-CLI-attempt, valid-view, and workload assertions were added as additional real regression/acceptance checks after their underlying behavior existed; **no pre-implementation Red is claimed for those checks**. No assertion was disabled or hardened to a preselected result.

## Green/refactor and real-boundary results

- `backend/.venv/bin/python -m pytest backend/tests/identity_access backend/tests/integration/identity_access backend/tests/persistence/sqlite/migrations/test_v1_0000.py -q --tb=short`: 74 passed, exit 0 after operator closure.
- After the operator follow-up and root's independently reviewed catalog rebind, `backend/.venv/bin/python -m pytest backend/tests -q --tb=short` passed **336 tests**, exit 0. Default discovery from `backend/` using `.venv/bin/python -m pytest -q --tb=short` also passed **336 tests**, exit 0. An earlier full-suite run during the steward's catalog promotion/rebind **Failed** (`43 failed, 270 passed, 23 errors`, `migration_checksum_mismatch`); that interrupted result is not relabeled as passing. The migration source SHA stayed unchanged while the catalog was marked `shared`/reviewed 2026-09-20 and its pinned catalog digest was rebound.
- Real PTY tests: password never echoed, one administrator and one audit row persist, second CLI attempt exits refusal without asking for a password, and incompatible policy reports unavailable without prompting or mutation; 3 passed.
- Additional real PTY/SQLite state test: after production bootstrap, a test-only safe policy-version metadata alteration makes the repository incompatible; CLI now reports safe unavailability, prompts for no secret, and leaves administrator/audit rows unchanged. No credential material is emitted or asserted raw.
- Real file SQLite: absent-file Alembic to `v1_0100`, seven IAM tables, constraints/foreign-key check, owner-only mode, one admin, one safe audit row, concurrent singleton, random salt, existing empty and historical `v1_0000` preservation, altered-schema writable refusal. No seeded credential state.
- Real production Argon2 workload: 100 verifications with two workers in a clean child process; p95 about 104 ms, peak RSS about 151 MiB, all verified; `backend/.venv/bin/python -m pytest backend/tests/integration/identity_access/test_argon2_workload.py -q --tb=short` passed. An initial measurement inside the large pytest process failed the RSS gate because the test host's inherited high-water mark was about 1.4 GiB; it measured pytest, not the isolated adapter workload. The corrected test launches the actual production adapter in a fresh child process and asserts both budgets. This is test-harness correction, not a product behavior Red.
- Exact source controls: `backend/.venv/bin/ruff check --config backend/pyproject.toml backend/src backend/tests` passed; `ruff format --check` with same config passed; mypy on backend source/tests passed; `python3 tooling/foundation/check_boundaries.py .` passed. An earlier Ruff invocation without explicit backend config was narrower/misleading; canonical config was rerun after fixing five import-order findings.
- `python3 tools/automation/run.py AUTO-DOCS-CHECK`: passed on 193 Markdown files; `git diff --check` passed. Full AUTO-TEST/QUALITY/BUILD remains the root integration gate after generated-artifact refresh.

## Security, privacy, migration, dependency, operations

No password/PHC/digest is printed, logged, included in assertions likely to render raw values, saved in documentation, or exposed in the contract view. `SecretInputV1` is transient/redacted/non-serializable. Audit view accepts only Story 1's reviewed codes and bounded schema version/count; nullable `reason_code` exists in migration for later reviewed M01 events, not arbitrary text. Repository errors are sanitized. TTY input refuses redirected I/O and password argv. Recovery has no unsafe installed entrypoint without a tested service-held quiescence receipt.

Argon2-cffi `25.1.0` and exact reviewed Linux transitive graph (`argon2-cffi-bindings 26.1.0`, `cffi 2.1.1`, `pycparser 3.0`) are in manifest/lock and installed without source builds. Admission, license and provenance decision: `docs/dependencies/m2-argon2-admission.md`. The integration steward owns SBOM/notices and full AUTO-QUALITY/BUILD regeneration. `v1_0100` has no destructive downgrade. Existing DB upgrades remain refused pending separately approved backup/quiescence/recovery. Migration/catalog/source and DDL digests were rebound after the approved nullable audit column; historical anchor bytes remain unchanged.

## Blocked / Not Run / follow-up

- **Not Run (Story 2/3):** successful-login rehash `M01-CRYPTO-003`, permission mapping/terminal lifecycle `M01-PURE-003/004`, token digest/plaintext `FR-IAM-005`, and real active session/token revocation through production credential use cases. Zero-row recovery transaction passed but does not prove credential-wide invalidation.
- **Not Run (integration/owner):** real owner-password TTY setup, installed service lifecycle/recovery, full AUTO-* gates, loopback FastAPI/OpenAPI/generated client, production browser, provider/account tests, and remote/macOS platform verification. Root's fresh-init CLI has separate evidence; this handoff does not claim its gate.
- **Blocked outside Linux-first M2:** native Intel macOS no-build Argon2 wheel availability and real macOS workload, per admission record.
- **Risk/owner:** later M01 Story 2/3 agents must extend the exact audit-code allowlist and verify malformed DB rows are refused before P01 publishes `/api/v1/iam/security-events`; root reviews contract impact. Root/integration must run generated artifacts, SBOM/notices, canonical AUTO-* and final M2 gate after shared sources freeze.

## Declaration

Work stayed within assigned M01/source/test/migration and explicitly allocated shared paths. Only isolated temporary real SQLite databases and real PTY/Argon2 processes were used. No mock, fake, stub, emulator, recorded response, seeded telemetry, demo account, test-only production branch, provider write, `.env` access, secret disclosure, or external resource creation occurred. The accepted Story 1 implementation was committed as `e05d8d8`. The root steward must still run the M2 milestone gate; Story 1 evidence is not a release or milestone pass.

## Independent integration acceptance

- Root independently reran the complete backend suite after the final catalog/operator freeze: `backend/.venv/bin/python -m pytest backend/tests -q --tb=short` exited 0 with **336 passed**. Specification review reran the 20 contract tests and the boundary checker; independent quality review reran 72 IAM/migration tests and nine targeted closure regressions. The reviewers accepted the bounded Story 1 slice and explicitly did not accept later session/token/recovery/browser behavior.
- The independent migration reviewer inspected the seven-table source, real absent-file/old-anchor/tampered-schema behavior, and matching catalog/revision/DDL digests; root promoted `v1_0100` to `shared`, dated 2026-09-20, and rebound its pinned catalog digest. The historical anchor source SHA was unchanged.
- After regenerating the still-empty M1 OpenAPI/client provenance artifact, root ran `AUTO-QUALITY`, `AUTO-BUILD`, `AUTO-TEST`, `AUTO-DOCS-CHECK`, and `AUTO-PLAN-CHECK`; each exited 0. **AUTO-TEST remains an M1-only routine** (291 backend tests plus two real built-browser foundation-shell cases) and does not substitute for the independently run 336-test backend suite or the future M2 API/browser gate. Its separate `AUTO-M0-G1-EXIT` result was Failed (exit 2), outside the M1/M2 authenticated-shell acceptance path; it is not called Passed.
- Owner-live bootstrap, active-credential recovery, fresh frozen no-build install, SBOM/notices, M2 HTTP/browser and provider/account boundaries remain **Not Run** as recorded above. This is Story 1 acceptance only; no M2 completion is inferred.

## M2 integration workload correction — 2026-09-21

The M2 full backend run observed real two-worker Argon2id verification p95 of 0.4578 s, above the approved 0.250 s target. Focused runs also varied with heavy unrelated workstation CPU load; this performance criterion remains **Failed**, not retried into a pass. Two bounded direct probes under `/usr/bin/time -v` agreed with their own OS peak RSS readings at 151,508 and 151,288 KiB, below the approved 256 MiB limit. A separate fresh Python process with no Argon2 work exposed an `ru_maxrss` accounting anomaly: 1,824,872 KiB versus its actual `/proc/self/status` `VmHWM` of 9,436 KiB. The workload test now measures Linux peak RSS from that real process's `VmHWM`; macOS retains `getrusage` byte-to-KiB conversion. No Argon2 parameters, concurrency, threshold, production behavior, or contract changed.

TDD for this test-harness correction: `backend/.venv/bin/python -m pytest backend/tests/integration/identity_access/test_argon2_workload.py::test_linux_peak_rss_uses_current_process_vmhwm -q --tb=short` first exited 1 with expected `NameError: _peak_rss_kib is not defined`; after the correction it exited 0 (`1 passed`). The complete targeted file then exited 1 (`1 passed, 1 failed`): real p95 was 0.409983694 s against 0.250 s while the host/browser workload was active. The failing timing result is preserved. At that stage, a low-contention target-host run and independent quality review remained necessary; no live provider/account test was implied.

## Later M2 local workload gate result — 2026-09-21

The independent quality reviewer accepted the bounded Linux RSS harness correction.
Without pausing owner workloads, changing Argon2 parameters or thresholds, or
deselecting a test, the workstation later reached naturally lower CPU
contention. The targeted real two-worker workload then passed (`2 passed`, exit
0), with a separate production-adapter 100-verification probe recording p95
`0.122203s`, peak process RSS `160488 KiB`, and all verifications matched. The
canonical full `AUTO-TEST` on committed source `55d0941` also passed (exit 0;
514 backend tests with no deselections), followed by real HTTP and Chrome
checks. Earlier CPU-contended failures above remain Failed historical attempts.
The final integration review and remaining Not Run boundaries are recorded in
[the M2 gate evidence](m2-st-api-002.md).
