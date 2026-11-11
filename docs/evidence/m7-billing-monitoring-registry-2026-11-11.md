# M7 billing monitoring registry increment — 11 November 2026

## Scope

- Requirements: FR-BUDGET-001/006, FR-ACC; M7-A01/A09; M7-T007.
- Owner: M02 Registry.
- Contract: additive `CTR-REG-014` 1.4.0 consumed as published by root.
- Database: no migration. Existing `reg_billing_connection` lifecycle,
  preference, version and revision remain the complete current authority.

## TDD evidence

Red, before production implementation:

```text
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=backend/src \
/home/dev/Nextcloud/Code/AI/AgentMonitor/backend/.venv/bin/python -B -m pytest -q --tb=short \
backend/tests/integration/registry/test_billing_connections.py::test_disable_replays_without_credential_or_registry_mutation \
backend/tests/integration/registry/test_billing_connections.py::test_enable_without_current_verified_proof_writes_nothing \
backend/tests/integration/registry/test_billing_credential_binding.py::test_prepare_and_archive_retire_only_pending_binding_metadata
```

Result: four expected failures and one pass. The repository lacked both
monitoring methods, and real archived Claude/Codex billing rows remained
`pending` instead of becoming `disconnected`.

Green after the bounded implementation:

```text
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=backend/src \
/home/dev/Nextcloud/Code/AI/AgentMonitor/backend/.venv/bin/python -B -m pytest -q --tb=short \
backend/tests/registry/test_billing_monitoring_policy.py \
backend/tests/integration/registry/test_billing_connections.py::test_disable_replays_without_credential_or_registry_mutation \
backend/tests/integration/registry/test_billing_connections.py::test_enable_without_current_verified_proof_writes_nothing \
backend/tests/integration/registry/test_billing_credential_binding.py::test_prepare_and_archive_retire_only_pending_binding_metadata
```

Result: 29 passed across the complete billing-connection, credential-binding
and monitoring-policy files. A further 22 billing contract/access/enrollment
guard tests and 10 composition/API status tests passed without a credential or
provider request.

Strict static and formatting checks:

```text
MYPYPATH=backend/src PYTHONDONTWRITEBYTECODE=1 \
/home/dev/Nextcloud/Code/AI/AgentMonitor/backend/.venv/bin/python -B -m mypy \
--config-file backend/pyproject.toml --explicit-package-bases <seven changed Python files>
```

Result: success, no issues in seven source files. Exact-config Ruff check and
format check passed for the same bounded files; `git diff --check` passed.

## Security, privacy and compatibility

- No credential value, provider profile, provider request or secret-bearing file
  was accessed.
- Enabling requires a composition-supplied genuine M04/M05 proof and an exact
  fresh M02 transaction recheck. Local credential metadata alone is rejected.
- Disabling requires no credential access. Exact replay is receipt-bound and a
  later authority invalidation makes the old outcome stale.
- Active-binding replacement/disconnect and account archive invalidate billing
  monitoring in the same SQLite transaction. The technical invalidation uses a
  system audit identity, not a fabricated owner.
- No dependency, public HTTP, schema or migration change is introduced here.

## Explicitly not run

- A positive enable and enabled-to-disabled persistence transition require a
  genuine successful billing report for the current real binding and scope.
  That live boundary remains Not Run for this M02 increment; constructed
  provider success or credential metadata was not substituted.
- Scope mutation is not implemented in this increment. Its future M02
  transaction must advance `scope_generation` and invoke the same monitoring
  invalidation before commit.
