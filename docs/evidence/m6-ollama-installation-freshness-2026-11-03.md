# M6 Ollama installation observation freshness

- Evidence ID: `M6-OLLAMA-INSTALLATION-FRESHNESS-2026-11-03`
- Module/plan: integration composition, A03/M02/M04/M06 under the approved
  [local vertical plan](../plans/integration/m6-ollama-local-vertical-change.md)
- Requirements: FR-DISC-001/003, ST-OLL-001; acceptance M6-A02/A06/A09
- Contracts: provider protocol 1.0.0, installation discovery schema 1.0,
  parser 1.0.0, Ollama adapter 1.1.0; all unchanged
- Candidate base: `580026b`
- Recorder/date: AgentMonitor engineering, 3 November 2026

## Delivered behavior

The optional runtime collector reconciles actual CLI installation metadata on
each due collection. The existing five-minute source schedule and failure
backoff precede discovery; one-second supervisor checks do not repeatedly
refresh the registry. Permanent installation-readiness caching was removed.
The existing ambiguous-installation guard, exact admitted CLI-version check,
cancellation checkpoints and collection deadline remain in place.

The regression initializes a real temporary migrated SQLite database, discovers
the actual installed Ollama CLI through production discovery, then runs the
production collector against real local process metadata. It asserts that a
pre-existing installation receives a new observation time, retains its ID and
version, and is not changed by an immediate non-due collector tick. No provider
response, installation row, account, clock or telemetry is fabricated.

## Red and Green

Before changing production code, the new regression failed at the freshness
assertion. The actual tick started at `2026-11-03T09:24:44.304837Z`, but the
installation retained its earlier `2026-11-03T09:24:44.280102Z` observation:

```text
assert started_at <= refreshed[0].last_seen_at <= datetime.now(UTC)
AssertionError
1 failed in 0.97s
```

Command, from this candidate checkout (developer Python, no sealed runtime):

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=backend/src \
  /home/dev/Nextcloud/Code/AI/AgentMonitor/backend/.venv/bin/python -B \
  -m pytest -q --tb=short \
  backend/tests/integration/collection_control/test_ollama_installation_freshness.py
```

After the minimum fix, the new test and existing real interval/backoff
regressions passed:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=backend/src \
  /home/dev/Nextcloud/Code/AI/AgentMonitor/backend/.venv/bin/python -B \
  -m pytest -q --tb=short \
  backend/tests/integration/collection_control/test_ollama_installation_freshness.py \
  backend/tests/integration/collection_control/test_ollama_runtime_lifecycle.py \
  -k 'freshness or reuses_registry or failure_backoff or backs_off'
```

Result: `4 passed, 2 deselected in 3.51s`. The deselected lifecycle scenarios
were not claimed as executed. Ruff lint and format checks using explicit
`--config backend/pyproject.toml` passed for both changed Python files. Strict
mypy with that configuration and explicit package bases passed for both files.

## Compatibility, privacy and operations

No API, contract, schema, migration, dependency, license or configuration
changes. Only the composition collector and its dedicated regression changed.
The runtime makes bounded read-only CLI and process-metadata observations. The
test writes only its own real SQLite database and collector backoff state.
The installed dashboard database, service, provider profiles, `.env`, secrets,
prompts, responses and user agent processes were not changed or inspected.

Each fresh discovery intentionally uses a new operation ID. Existing registry
reconciliation advances the global registry revision and installation record
version even when the product version is unchanged. The integration steward
was notified because a separately discovered cloud-admission generation bug
must not confuse this registry revision with credential-binding generation.
No cloud logic was changed within this task.

## Remaining verification

Live service deployment, sustained scheduled observation in the deployed
dashboard, browser verification, unsupported-version behavior on a different
actual installation, and the canonical M6 exit are **Not Run** for this isolated
candidate. The actual machine has the admitted Ollama 0.24.0 installation; it
was not replaced to simulate another version. Root owns deployment and final
M6 evidence. This record establishes the bounded correction, not M6 closure.

No mocks, fakes, stubs, emulators, recorded responses, seeded telemetry, default
profile mutations or secret exposure were used. Rollback is a code revert;
no migration or provider-state restoration is required.
