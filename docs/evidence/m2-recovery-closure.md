# M2 local forgotten-password recovery closure — M01

- Status: **Accepted M01 correction for the M2 slice** after independent specification/security and QA reviews; not an M2 exit claim.
- Date/environment: 2026-09-21 UTC; real Linux host, Python 3.12, production Argon2id adapter, real migrated file-backed SQLite, real controlling PTY and Uvicorn service lock.
- Scope: approved M2 `ST-IAM-001` correction; `FR-IAM-001/002/003/004/005`, `NFR-SEC-001`, `AC-OPS-005`; `M01-OPS-005`, `M01-SEC-001/006`, `M01-DB-003/009`.
- Contracts: `CTR-IAM-004` V1 recovery application port; `CTR-IAM-003/006` V1 credential invalidation effects; existing service-lock protocol. No REST/OpenAPI, schema, migration, configuration, UI, or provider contract change.
- Files: `backend/src/agentmonitor/modules/identity_access/application/bootstrap.py`, `backend/src/agentmonitor/composition/iam_operator.py`, `backend/src/agentmonitor/adapters/persistence/identity_access/sqlite/repository.py` (docstring), `backend/tests/integration/identity_access/test_operator_recovery.py`, `docs/modules/identity-access.md`, this record.

## Red → Green → refactor

| Stage | Exact command | Exit/result |
|---|---|---|
| Red, before production changes | `backend/.venv/bin/python -m pytest backend/tests/integration/identity_access/test_operator_recovery.py -q` | 1; **3 failed**. Real migration/bootstrap/login/token setup succeeded in each test. Recovery command returned `invalid_operator_arguments` instead of recovery success, service-lock refusal, and noninteractive-specific refusal. No setup/syntax failure was counted as Red. |
| Initial Green, after application/CLI change | Same command | 1; 2 passed, one test-harness SQL query error after the recovery itself returned success and both old credentials were rejected. **Not counted as Green.** |
| Green, after fixing the test query and adding unsafe-lock coverage | Same command | 0; 4 passed. |
| Refactor/final focused | `backend/.venv/bin/python -m ruff check --config backend/pyproject.toml backend/src/agentmonitor/modules/identity_access/application/bootstrap.py backend/src/agentmonitor/composition/iam_operator.py backend/src/agentmonitor/adapters/persistence/identity_access/sqlite/repository.py backend/tests/integration/identity_access/test_operator_recovery.py && backend/.venv/bin/python -m pytest backend/tests/integration/identity_access/test_operator_recovery.py -q` | 0; Ruff clean, **5 passed in 3.57 s**. The fifth test proves policy denial leaves real credentials usable. |
| Targeted strict typing | `MYPYPATH=backend/src backend/.venv/bin/python -m mypy --config-file backend/pyproject.toml --explicit-package-bases backend/src/agentmonitor/modules/identity_access/application/bootstrap.py backend/src/agentmonitor/composition/iam_operator.py backend/tests/integration/identity_access/test_operator_recovery.py` | 0; no issues in 3 files. Earlier mypy commands without the repository's required package-base options failed on import discovery only and are not counted as product defects or passes. |
| Wider real M01 regression | `backend/.venv/bin/python -m pytest backend/tests/identity_access backend/tests/integration/identity_access -q` | 0; **137 passed in 212.61 s**. |

Bounded QA evidence-safety correction after the wider run: PTY output and database-byte comparisons now feed booleans before assertion, so a failed pytest assertion does not rewrite and print a random password, captured terminal output, or verification material. No production behavior changed. The exact focused command above was rerun and exited 0 with **5 passed in 4.99 s**; targeted Ruff, Ruff format, and strict mypy each exited 0. The earlier 137-test run predates this test-only assertion correction; root's final canonical gate must rerun the full set against the frozen checkout.

## Real-boundary assertions

The new regression migrates an absent SQLite file through the production Alembic chain; uses production bootstrap with OS-random isolated administrator passwords; obtains an actual browser session via `AuthenticateAdministratorV1`; creates an actual scoped API token via `CreateApiTokenV1`; and invokes the installed local CLI through a real controlling PTY. Successful recovery changes the verifier: old password login fails, new password login works, old session and bearer both fail, one prior session and one prior token have terminal `local_recovery` rows with nulled digests, and one safe audit event records aggregate count **2** with the fixed local correlation ID. The test checks that the new password is not echoed and that the stable lock file remains present.

A second test starts the actual M2 IAM Uvicorn service on a loopback socket. While its lifespan holds `.agentmonitor-service.lock`, recovery exits nonzero with `service_lock_occupied` **before** a password prompt; the prior password/session/token remain usable. A symlinked unsafe lock file also refuses before prompting without modifying its target or SQLite. Redirected/noninteractive input and password argv are refused. A too-short replacement is denied by the production policy without invalidating credentials or writing a recovery audit event.

The application use case owns password policy and Argon2id hashing; the composition root owns TTY and `flock`; the existing repository owns the atomic verifier/session/token/audit transaction. No HTTP route or second credential path was added.

## Security, compatibility, and limitations

- Secrets never enter argv, `.env`, logs, audit, docs, screenshots, or evidence. The test stores OS-random values only in process memory and writes actual verification material through production ports. No provider profile, agent process, or operator database was touched.
- The permanent, owner-only `0600` lock file is never unlinked; the operator checks root ownership/mode and exact inode and holds nonblocking exclusive `flock` before schema inspection, password prompt, hashing, transaction, and close. This coordinates legitimate service/operator processes; it does **not** isolate a malicious same-UID actor or eliminate a directory-replacement race. That residual is documented in the M01 operator guide.
- Existing `v1_0100` schema and all migrations remain unchanged. No dependency/package/license impact. The command is a compatible implementation of the already-approved `CTR-IAM-004` V1 behavior; no new public API or version bump is needed.
- **Not Run:** owner-entered recovery of a real installed service/database, installed service stop/start and verified offline backup, macOS PTY/lock behavior, post-restore credential invalidation, full M2 canonical gate, live provider/account tests. These are not inferred from the isolated real test.
- Independent specification/security review found no contract or security blocker and reran the five real recovery tests (exit 0). Independent QA found and closed one test-output secrecy issue: on failure, pytest assertion rewriting could have displayed the entered password or captured PTY output. A post-fix independent rerun passed all five tests, Ruff, strict typing, and diff checks. No production behavior was changed by that bounded review fix.
- Next integration step: root runs the frozen M2 `AUTO-TEST`, `AUTO-QUALITY`, `AUTO-BUILD`, `AUTO-DOCS-CHECK` and Story 6 HTTP/browser gate. This record alone is not a milestone completion gate.

## Integrity declaration

No mock, fake, stub, emulator, replay, demo account, seeded telemetry, direct credential-row seeding, placeholder UI data, test-only production branch, disabled assertion, or swallowed failure was used. The earlier vacuous zero-row repository recovery test was **not** cited as proof of credential-wide invalidation; the new test creates and invalidates nonzero real credentials.
