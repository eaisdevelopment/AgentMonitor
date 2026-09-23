# V1-M3 authenticated dashboard runner evidence

- Date: 2026-09-23
- Story: `ST-OBS-003`
- Requirements: `AC-V1-001`, `AC-UI-002`, `AC-TEST-001`, `NFR-SEC-001`
- Contracts: `CTR-API-001..003` V1 and `CTR-IAM-001..008` V1; no contract shape changed
- Modules: integration composition, P01, M01, and P02

## Red and Green

The real subprocess test first failed because the production CLI accepted only
the M1 foundation mode and emitted no dashboard readiness record. The same test
then passed after the CLI gained the mutually exclusive
`--authenticated-dashboard` mode.

```text
PYTHONPATH=backend/src backend/.venv/bin/python -m pytest \
  backend/tests/integration/api/test_dashboard_html_routes.py::test_production_cli_starts_authenticated_dashboard_mode \
  -q --tb=short
# Red: 1 failed in 1.55s; no JSON readiness record
# Green: 1 passed in 1.94s

PYTHONPATH=backend/src backend/.venv/bin/python -m pytest \
  backend/tests/integration/api/test_dashboard_html_routes.py \
  backend/tests/integration/foundation/test_loopback_app.py::test_real_process_sigterm_is_bounded_and_restartable \
  -q --tb=short
# Green/refactor: 4 passed in 7.28s
```

Both commands use a real migrated file-backed SQLite database, a real child
process, an actual prebound IPv4 loopback socket, Uvicorn, HTTP, and the
production frontend build. `SIGTERM` performs bounded shutdown and the process
restarts against the same file. No in-process transport, provider fixture,
seeded telemetry, mock, fake, or stub is used.

## Owner-local initialization

The owner-local installation was initialized under an existing owner-only path
outside the Nextcloud-synchronized repository because the SQLite policy
correctly rejects group-writable ancestors. The data directory is `0700`, the
database and explicit empty service configuration are `0600`, and the real
administrator bootstrap completed through a controlling PTY with terminal echo
disabled. The credential value is not present in source, evidence, output, or
chat. The production command then bound `127.0.0.1:43110`; a real HTTP password
login returned `204`, issued the two approved cookies, and the resulting session
read `/api/v1/accounts` successfully. The service stopped cleanly afterward so
the provider collection could use the persistent database while quiescent.
A second real authenticated session issued one 365-day, read-only
`read:diagnostics` API token through `/api/v1/api-tokens`. Its one-time bearer
was written directly to the owner-only ignored `.env` without being printed;
only the configuration key name was verified afterward.

Provider collection and the populated production-browser result are recorded
separately because this runner neither invokes providers nor creates telemetry.

## Impact

- Security/privacy: loopback-only binding, existing Host/Origin/session/CSRF
  guards, stable service lock, no credential logging, and no implicit migration.
- Migration: none; startup requires the already compatible schema.
- Dependencies/licenses: none.
- Documentation: the local operator sequence now includes the exact dashboard
  start command.
