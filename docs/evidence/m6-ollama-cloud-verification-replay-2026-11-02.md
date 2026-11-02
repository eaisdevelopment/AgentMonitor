# Test evidence: M6 exact cloud-verification replay

- Evidence ID: `M6-CLOUD-REPLAY-20261102`
- Module/plan/increment: M04 under the approved M6 Ollama cloud plan
- Requirements/acceptance IDs: `FR-COL-003`, `FR-COL-005`, `FR-COL-007`, `FR-SAFE-001`, `M6-A07`, `M6-A09`, `NFR-DATA-001`
- Contract versions: `CTR-COL-010` V1 enqueue retained; additive `OllamaCloudVerificationEnqueueV2@2.0.0`; database `v1_0717`
- Commit/worktree reference: `4a756dd` in `codex/m6-atomic-enqueue-fence`
- Recorder/date: Codex sub-agent, 2026-11-02

## Test inventory and status

| Test/scenario ID | Layer | Real dependencies | Status | Evidence reference | Notes |
|---|---|---|---|---|---|
| `M6-REPLAY-PURE` | Pure | None | Passed | focused pytest, 49 passed | Exact account/version replays; changed and legacy-null identities fail closed |
| `M6-REPLAY-MIGRATE-716` | DB | Private copy of real dashboard data migrated to `v1_0716` | Passed | `AUTO-MIGRATE` | Exact `v1_0716` to `v1_0717` transition, verified backup; activation Not Run |
| `M6-REPLAY-MIGRATE-707` | DB | Private backup of real dashboard database at `v1_0707` | Passed | `AUTO-MIGRATE` | Full admitted chain reached `v1_0717`; activation Not Run |
| `M6-REPLAY-SQLITE-JOB` | DB | Natural credential-backed Ollama verification job | Not Run | unavailable real state | No real job exists; no account, graph, credential, or telemetry row was fabricated |
| `M6-REPLAY-HTTP` | API/browser | Candidate deployment and authenticated session | Not Run | revision mismatch | Running service is an older checkout; no cookies or credentials were accessed |
| `M6-REPLAY-PROVIDER` | Provider | Real Ollama cloud credential | Not Run | outside this non-I/O correction | No key lookup or provider request was performed |

## Red evidence

The first candidate (`ae9bcc2`, landed elsewhere as `9001904`) was independently
reviewed and rejected: composition performed current account-version handling
before the durable M04 replay lookup, while the job identity omitted the external
expected account version. That made an identical original request fail after a
later account edit and allowed a changed expected version to match the old job.

Before the production correction, this focused command failed during collection:

```text
/home/dev/Nextcloud/Code/AI/AgentMonitor/backend/.venv/bin/pytest -q backend/tests/registry/domain/test_cloud_owner_assertion.py
ImportError: cannot import name 'decide_cloud_verification_replay'
```

The pure behavior was then moved to its owning M04 test module during refactor.

## Green evidence

Focused pure, contract, schedule, and API-surface checks:

```text
/home/dev/Nextcloud/Code/AI/AgentMonitor/backend/.venv/bin/pytest -q backend/tests/registry/domain/test_cloud_owner_assertion.py backend/tests/collection_control/domain/test_ollama_verification_completion.py backend/tests/contracts/test_ollama_cloud_verification_jobs.py backend/tests/contracts/test_cloud_binding_verification.py backend/tests/adapters/providers/ollama/test_cloud_schedule_generation.py backend/tests/contracts/test_ollama_cloud_api_guards.py backend/tests/api/test_ollama_cloud_connection_surface.py
49 passed in 1.84s
```

The final catalog and migration command passed against private copies of real
dashboard data for both the exact new transition and the full currently installed
source chain:

```text
AUTO-MIGRATE: PASSED — v1_0716 to v1_0717; service activation Not Run
AUTO-MIGRATE: PASSED — v1_0707 to v1_0717; service activation Not Run
```

## Refactor evidence

```text
mypy --strict --explicit-package-bases [eight affected source files]
Success: no issues found in 8 source files

ruff format --check [affected Python files]
11 files already formatted

ruff check [affected Python files]
All checks passed!

git diff --check
passed

AUTO-DOCS-CHECK
PASSED (operational)
```

## Real-system evidence

The real dashboard database was opened read-only and copied with SQLite's backup
API into owner-only temporary directories. Only schema metadata and the Alembic
revision were inspected. `AUTO-MIGRATE` created and verified its own private
pre-migration backup, migrated each private copy, and passed schema, integrity,
and policy validation. All temporary database copies and their backups were then
deleted. The live database and service were not modified or restarted.

There was no natural Ollama cloud verification job in the real source revision,
so repository replay behavior remains explicitly Not Run rather than being
tested with a seeded job.

## Integrity declaration

No mock, fake, stub, emulator, recorded response, demo account, seeded telemetry,
placeholder value, disabled assertion, or test-only production branch was used.
The migration retains `NULL` for legacy request versions and rejects their replay;
it does not invent a historical value.

## Data and secret review

No credentials, provider payloads, cookies, account identities, business rows,
prompts, responses, environment secrets, or source content were read or recorded.
The added column stores only a bounded account record version.

## Conclusion and residual gaps

The candidate proves the pure replay policy, versioned contract shape, catalog,
and real-data migration path. It does not prove repository replay against a
natural real verification job, candidate HTTP/browser behavior, provider access,
or deployment. Migration `v1_0717` remains `implemented` with reviewer
`pending-M04-independent-review`; it must not be promoted to `shared` or used for
activation before that review and the broader M6 completion gates.
