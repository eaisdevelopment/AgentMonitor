# M3-FIX-004 reproducible Claude OTLP fingerprint binding evidence

- Evidence ID: `M3-FIX-004-FINGERPRINT-BINDING`
- Module/plan/increment: M02 registry plus M3 composition operator repair
- Requirements: `FR-ACC-004/005/006`, `NFR-SEC-001`
- Stories: `ST-REG-001`, `ST-OBS-002`
- Contract: CTR-REG-006 V1, compatible implementation only
- Recorder/date: implementation worktree, 2026-09-24

## Test inventory and status

| Test/scenario | Layer | Real dependencies | Status | Notes |
|---|---|---|---|---|
| `test_real_tty_decline_leaves_migrated_registry_unchanged` | DB/operator | real file-backed SQLite, Alembic head, Linux PTY/subprocess | Passed | Exact decline returns before DB/provider work |
| `test_binding_operator_rejects_redirected_or_fingerprint_arguments` | DB/operator | real file-backed SQLite and subprocess | Passed | No redirected-input or fingerprint-argv path |
| `test_owner_binding_command_closes_the_actual_metric_to_exact_source_tuple` | Pure policy | constructed typed domain values only | Passed | Exact account/version/scheme/source/parser/evidence mapping |
| Owner initial binding against the real default Claude profile | Live provider/operator | owner account, protected default profile, natural Claude session | Passed | Owner-confirmed controlling-terminal run completed; profile remained provider-managed and read-only |
| Existing-binding evidence integrity | Live DB/provider/operator | real owner SQLite, exact current Claude fingerprint, real M06 observation/receipt | Passed | The final read-only integrity test resolved one active claim to one committed M06 observation/receipt |

## Red evidence

Before production edits:

```text
uv run --project backend pytest -q \
  backend/tests/integration/registry/test_provider_identity_operator.py

FAILED test_real_tty_decline_leaves_migrated_registry_unchanged
expected return code 2, actual 1
1 failed in 0.79s
```

The production module did not exist, so the real PTY could not reach an owner
confirmation prompt. A second focused Red imported the intended exact command
builder and failed during collection with:

```text
ImportError: cannot import name '_owner_binding_command'
1 error in 0.54s
```

Both failures were the expected missing production/operator path, not a provider
or environment failure.

The audit repair added a read-only real-owner evidence-chain test before the
refresh implementation. Its pre-fix Red was:

```text
AGENTMONITOR_TEST_DATA_ROOT=<owner-data-root> PYTHONPATH=backend/src \
  backend/.venv/bin/pytest \
  backend/tests/live/claude/test_provider_identity_evidence.py -q --tb=short

FAILED: active Claude identity evidence does not resolve to an M06 observation
1 failed
```

A pure transition test was also added first and failed during collection with
an `ImportError` for the absent
`decide_provider_identity_confirmation`. It now passes and permits only a new
unresolved claim or a fresh explicit confirmation for the same resolved
account; conflict/missing-claim combinations remain rejected.

## Green and refactor evidence

After the minimum implementation and evidence-order hardening:

```text
uv run --project backend pytest -q \
  backend/tests/adapters/providers/claude/test_otel_runtime_static.py \
  backend/tests/integration/registry/test_provider_identity_operator.py \
  backend/tests/registry/test_provider_identity_fingerprint_contract.py \
  backend/tests/integration/registry/test_registry_persistence.py

62 passed in 9.40s
```

Focused Ruff passed. Focused strict Mypy passed with the repository's canonical
`MYPYPATH=backend/src`, config file, and explicit-package-bases settings.

The final real-owner read-only integrity command, scoped through
`AGENTMONITOR_TEST_DATA_ROOT` and `AGENTMONITOR_TEST_ACCOUNT_ID`, also passed:

```text
backend/tests/live/claude/test_provider_identity_evidence.py
1 passed in 0.03s
```

## Production evidence order

The binding mode is fail closed in this order:

1. explicit owner confirmation on a real controlling TTY, before DB/provider work;
2. reviewed transparent Claude exec plus authenticated loopback OTLP metric;
3. independent exact Linux process/install/version verification;
4. unbound M04-to-M06 session commit and repository reopen;
5. CTR-REG-006 confirmation with the actual in-memory fingerprint, exact opaque
   account/version, fixed source tuple, committed session observation ID, and
   reopened payload digest;
6. fresh read-only M02 resolution to that exact account/version;
7. quiescent SQLite checkpoint;
8. exporter HTTP success acknowledgment.

The exact composition-owned identity tuple is:

- provider: `claude`;
- scheme/scope/version: `claude.otel.account.sha256` / `provider_account` / `1`;
- source/version/parser: `claude.otel.metrics.http-json.v1` / `1.0.0` / `1.0.0`;
- provider version: the exact verified launch-plan version, not caller input.

## Security, privacy, compatibility, and operations

- The official account UUID/ID are domain-separated and hashed by the approved
  parser; raw values never cross into the operator or registry command.
- The fingerprint exists only in the parsed metric and typed registry command;
  it is absent from argv, terminal prompts, stdout/stderr, logs, evidence, and
  result DTOs.
- The operator requires an explicit account ID and current account/profile
  versions. It never selects a sole account and never mutates the protected
  default profile.
- Existing M02 tables, idempotency receipts, uniqueness/conflict rules, and
  CTR-REG-006 are reused. There is no migration or breaking contract change.
- No configuration key, dependency, license, API, UI, OpenAPI, client, manifest,
  or M0 approval change is introduced.

## Live owner step

The owner completed the controlling-terminal checkpoint by typing `CONFIRM` and
exited the resulting Claude session normally. The read-only evidence-chain test
then passed against the same owner database.

```text
PYTHONPATH=backend/src backend/.venv/bin/python -m \
  agentmonitor.composition.claude_otel_identity_binding \
  --data-root /absolute/owner-approved/data-root \
  --account-id '<opaque-account-id>' \
  --account-version '<current-record-version>'
```

The receiver child exited and the owner session was closed normally. The final
verification reopened M02 and M06, proved one current exact process link and
the immutable observation reference/digest, inspected sanitized output, and
confirmed the default profile was unchanged. Replay and changed-request
conflict checks remain covered by the focused registry suite.

## Integrity declaration

No mock, fake, stub, emulator, recorded response, constructed provider payload,
demo account, seeded telemetry, direct SQL composition path, or test-only
production branch was used. Constructed values appear only in the pure command
policy test. The real external-boundary test uses file-backed SQLite and a real
Linux controlling PTY. The positive provider/account mutation remains truthfully
Not Run.
