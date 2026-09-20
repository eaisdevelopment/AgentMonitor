# M01 identity/access — V1-M2 Story 1

- Owner: `PLAN-M01`; implementation slice `ST-IAM-001`.
- Published contracts: `CTR-IAM-001/002/004/005/007/008` V1; shared database contract `CTR-DB-002` V1.
- Status: Story 1 implemented on isolated real SQLite; M2 API, browser, live owner bootstrap, and installed recovery remain separate gates.

## Boundaries and state

`modules/identity_access/domain/policy.py` contains deterministic policy only. `application/bootstrap.py` consumes repository and hasher protocols. `adapters/identity_access/argon2_password.py` is the only Argon2 implementation; `adapters/persistence/identity_access/sqlite/repository.py` owns `iam_*` writes. `adapters/identity_access/tty_operator.py` handles local no-echo input; `composition/iam_operator.py` wires the production bootstrap command. P01 must use published M01 application ports, not the repository or tables directly.

The immutable Alembic chain has `v1_0000 → v1_0100`. The latter creates exactly seven IAM tables, no credential row, and one nullable safe `reason_code` audit column. The catalog pins revision bytes; the runtime separately checks exact admitted IAM table/index DDL, including columns, foreign keys, checks, and index definitions. Fresh initialization accepts only a previously absent database file. Existing empty or `v1_0000` files are preserved and refused until a separately approved offline backup/quiescence upgrade workflow exists. No startup DDL or downgrade is available.

## Local operator sequence

Run from the repository root as the normal owner user, never root. Use an absolute owner-only (`0700`) data root; never pass a password in argv, `.env`, stdin redirection, or shell history. This is the current M2 development/local flow; `backend/pyproject.toml` has `package=false`, so a plain system `python -m` invocation is not installed or supported.

```bash
PYTHONPATH=backend/src backend/.venv/bin/python -m agentmonitor.composition.iam_fresh_init --data-root ABSOLUTE_0700_ROOT
PYTHONPATH=backend/src backend/.venv/bin/python -m agentmonitor.composition.iam_operator bootstrap --data-root ABSOLUTE_0700_ROOT
```

The first command is the M2-only fresh absent-file initializer, not an existing-file migration/backup routine. The second command requires a controlling TTY and asks for password plus confirmation with echo disabled. It creates one implicit administrator and one safe audit event atomically. A second bootstrap refuses without prompting for another password. The commands are installed/composed by the integration steward; live owner password entry is still Not Run. Do not use a test database as a replacement for the owner's real setup.

If the stored policy version is incompatible, the operator command returns `iam_repository_unavailable` without a password prompt or database mutation. It must not misreport that state as an ordinary already-initialized installation.

Recovery is intentionally not an installed command yet. The repository transaction can rotate the verifier and revoke every stored session/token in one transaction, but an operator entrypoint needs a service-held quiescence receipt and later credential-populated integration verification. No HTTP setup or recovery endpoint is permitted.

## Password and audit policy

New passwords require at least 15 Unicode code points and at most 1,024 UTF-8 bytes; malformed Unicode fails safely. The admitted Argon2id profile is 65,536 KiB, three passes, four lanes, 16-byte random salt, 32-byte tag, PHC version 19, with at most two simultaneous operations. Only PHC verification material is stored, never plaintext. Audit views currently allow exactly Story 1's administrator-initialized/recovered event and corresponding outcome codes; later Stories must extend the safe code registry deliberately before publishing new events. The database audit row permits only bounded technical fields, not token names, raw request text, credentials, or provider content.

## Verification and limitations

Use the [Story 1 evidence record](../evidence/m2-st-iam-001.md) for exact Red/Green/refactor commands, real DB/PTY/workload results, and Not Run items. The canonical backend test discovery includes `backend/tests/identity_access` and `backend/tests/integration/identity_access`; Story 1 uses no in-memory database, fake hasher, or seeded credential state. M2 end-to-end HTTP/browser, owner-live bootstrap, session/token revocation with active credentials, and macOS remain later gates.
