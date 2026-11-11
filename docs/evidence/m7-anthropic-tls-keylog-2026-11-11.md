# M7 Anthropic TLS key-log correction

- Owner/scope: A01, approved T006 transport security; bounded delegated correction.
- Requirements: FR-BUDGET-006, NFR-SEC-001, NFR-OBS-001; AC-V1-005/007; M7-A03 prerequisite.
- Baseline: `7e252b8`, M7 worktree; no commit by this delegate.
- Contract impact: none. Existing A01 provider/source contracts and admission remain unchanged.
- Date: 2026-11-11, verification at 17:29 UTC.

## Finding and minimum change

The A01 `_read_page` supplied `ssl.create_default_context()`, which honors
`SSLKEYLOGFILE`. A default unconnected HTTPS context can therefore enable a
key-log destination before a provider request. This violates the existing
no-secret-artifacts requirement even though no key material was generated in
this test.

The actual private `_Connection` constructor now creates
`ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)` directly, enables hostname checks,
requires certificate verification and loads default server-authentication
trust. It admits only the existing fixed provider host and preserves port 443
and REQUEST_SECONDS. `_read_page` uses that constructor without the
environment-sensitive helper. This matches the existing M6 cloud-balance and
new A03 direct-context pattern; no provider-private cross-import was added.

Files changed:

- `backend/src/agentmonitor/adapters/providers/claude/anthropic_api/source.py`.
- `backend/tests/adapters/providers/claude/anthropic_api/test_tls_security.py`.
- This evidence file.

## Real Red and Green

The new test starts an actual isolated Python subprocess with only explicit
PYTHONPATH and a temporary SSLKEYLOGFILE destination. It constructs the real
A01 connection without connecting. It checks no socket, no key-log destination,
TLS client protocol, hostname/CERT_REQUIRED verification, loaded default CA
trust, fixed host/port/timeout, and absence of a created key-log file.

Before the production change, the focused test failed at the child assertion
`connection._context.keylog_filename is None`: **1 failed in 0.45s**. This is
behavioral Red from the actual TLS implementation, not a missing-symbol or
unavailable-provider failure. No network request or TLS handshake occurred.

After the minimum change, the complete existing A01 directory passed:
**35 passed in 1.35s**. The new real subprocess test passed with no key-log file.

```bash
/home/dev/Nextcloud/Code/AI/AgentMonitor/backend/.venv/bin/python -m pytest -c backend/pyproject.toml --import-mode=importlib -q --tb=short -p no:cacheprovider backend/tests/adapters/providers/claude/anthropic_api
```

Scoped Ruff check and format check passed for both changed Python files using
`--config backend/pyproject.toml`. Strict mypy passed the A01 source with
`MYPYPATH=backend/src --explicit-package-bases --follow-imports=silent` and the
backend configuration. Scoped `git diff --check` passed. No production refactor
followed those checks.

## Integrity and residual verification

No mock, fake connection, response replay, provider payload, credential, API
request or seeded telemetry was used. No inherited arbitrary environment was
copied or inspected. The test's SSLKEYLOGFILE contains only an owned temporary
path; no credential or environment file was read. No handshake means no session
keys existed to log. The connection is closed in a finally block.

No dependency/license, schema, migration, shared contract, composition, service,
profile or owner-account change. Existing installed Python tooling was reused
without temporary links. Live provider authentication, HTTP behavior and real
report mapping remain Not Run by this correction; it does not close T006 or M7.
