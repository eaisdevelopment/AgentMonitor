# Test evidence: M6 exact cloud-verification replay

- Evidence ID: `M6-CLOUD-REPLAY-20261102`
- Module/plan/increment: M04 under the approved M6 Ollama cloud plan
- Requirements/acceptance IDs: `FR-COL-003`, `FR-COL-005`, `FR-COL-007`, `FR-SAFE-001`, `M6-A07`, `M6-A09`, `NFR-DATA-001`
- Contract versions: `CTR-COL-010@2.0.0`; existing one-request V2 application boundary retained; additive atomic V2 persistence port; database `v1_0717`
- Commit/worktree reference: `defecd0` plus the later atomic-initiation
  correction in `codex/m6-v2-enqueue-port`
- Recorder/date: Codex sub-agent, 2026-11-02

## Test inventory and status

| Test/scenario ID | Layer | Real dependencies | Status | Evidence reference | Notes |
|---|---|---|---|---|---|
| `M6-REPLAY-PURE` | Pure | None | Passed | focused pytest, 45 passed | Exact account/version replays; changed and legacy-null identities fail closed; server-derived graph/binding facts remain frozen from the first call |
| `M6-ENQUEUE-V2-COMPAT` | Pure | None | Passed | focused pytest, 45 passed | Existing one-request V2 call surface retained; atomic initiation is additive; malformed snapshot inputs fail closed before DB access |
| `M6-REPLAY-MIGRATE-716` | DB | Private copy of real dashboard data migrated to `v1_0716` | Passed | `AUTO-MIGRATE` | Exact `v1_0716` to `v1_0717` transition, verified backup; activation Not Run |
| `M6-REPLAY-MIGRATE-707` | DB | Private backup of real dashboard database at `v1_0707` | Passed | `AUTO-MIGRATE` | Full admitted chain reached `v1_0717`; activation Not Run |
| `M6-REPLAY-SQLITE-JOB` | DB | Natural credential-backed Ollama verification job | Not Run | unavailable real state | No real job exists; no account, graph, credential, or telemetry row was fabricated |
| `M6-REPLAY-HTTP` | API/browser | Candidate deployment and authenticated session | Not Run | revision mismatch | Running service is an older checkout; no cookies or credentials were accessed |
| `M6-REPLAY-PROVIDER` | Provider | Real Ollama cloud credential | Not Run | outside this non-I/O correction | No key lookup or provider request was performed |

## Independent-review correction

The first V2 compatibility correction still left a concurrency window in
composition: after an initial read-only replay miss, it could reconcile the
current M02 graph and register an M04 schedule before the transaction-owned job
repository observed a concurrently inserted replay. An exact replay after
credential rotation could therefore fail current-state fencing, and a
conflicting account request could leave an inert derived schedule.

The corrected boundary adds an additive `CTR-COL-010@2.0.0` atomic-initiation
port. Its integration implementation opens one `BEGIN IMMEDIATE` transaction
and evaluates the external principal/idempotency/account/expected-version
replay before any M02 or M04 write. Only a genuine miss acquires and revalidates
the existing account credential lock before it may reconcile the code-owned
access target, apply or replay the owner assertion, register the exact schedule,
recheck current M02 authority and insert the M04 job; all of those mutations
commit or roll back together. The implementation retains M04 as the semantic
owner of `CTR-COL-010`; integration placement does not create a second producer.

The pure contract Red failed with:

```text
AttributeError: module 'agentmonitor.modules.collection_control.application.ollama_cloud_admission' has no attribute 'OllamaCloudVerificationAtomicInitiationRepositoryV2'
1 failed, 3 passed
```

After the correction, the expanded focused suite passed `45 passed`. There is
still no natural real verification job, so cross-process SQLite replay and
credential-rotation concurrency remain **Not Run**, not inferred from the pure
port check. `ruff check`, `git diff --check`, Python compilation and
`AUTO-DOCS-CHECK` passed. The strict source-root mypy command reported 16
pre-existing errors in `cloud_balance/collection.py` and
`composition/ollama_cloud_collection.py`, and no error in this correction's
changed files; it is therefore recorded as a wider-tree failure rather than a
passing full type gate. `AUTO-PLAN-CHECK` retains its two previously recorded
independent-review binding failures.

## Red evidence

The first candidate (`ae9bcc2`, landed elsewhere as `9001904`) was independently
reviewed and rejected: composition performed current account-version handling
before the durable M04 replay lookup, while the job identity omitted the external
expected account version. That made an identical original request fail after a
later account edit and allowed a changed expected version to match the old job.

The earlier replay correction first failed during collection:

```text
/home/dev/Nextcloud/Code/AI/AgentMonitor/backend/.venv/bin/pytest -q backend/tests/registry/domain/test_cloud_owner_assertion.py
ImportError: cannot import name 'decide_cloud_verification_replay'
```

The pure behavior was then moved to its owning M04 test module during refactor.

The compatibility review then rejected changing the already-existing
`EnqueueOllamaCloudVerificationV2` call signature in place. Before `defecd0`,
the focused compatibility test failed twice because the repository accepted V1
instead of V2 and the V2 application service required four new authority
arguments. The new snapshot input guard also failed during collection because
the closed validator did not exist:

```text
backend/tests/contracts/test_ollama_cloud_verification_enqueue_versions.py
2 failed, 1 passed

backend/tests/contracts/test_ollama_cloud_schedule_snapshot_inputs.py
ImportError: cannot import name '_require_authorized_snapshot_inputs_v1'
```

## Green evidence

Focused pure, contract, schedule, and API-surface checks:

```text
/home/dev/.local/share/agentmonitor/worktrees/m6-cloud-final/backend/.venv/bin/pytest -q \
  backend/tests/contracts/test_ollama_cloud_verification_enqueue_versions.py \
  backend/tests/contracts/test_ollama_cloud_schedule_snapshot_inputs.py \
  backend/tests/contracts/test_ollama_cloud_verification_jobs.py \
  backend/tests/collection_control/domain/test_ollama_verification_completion.py \
  backend/tests/registry/domain/test_cloud_owner_assertion.py \
  backend/tests/api/test_ollama_cloud_connection_surface.py
44 passed in 1.70s
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
mypy --strict --explicit-package-bases [five contract/application/adapter files]
Success: no issues found in 5 source files

python -m py_compile backend/src/agentmonitor/composition/ollama_cloud_connection.py
passed

ruff format --check [affected Python files]
passed

ruff check [affected Python files]
All checks passed!

git diff --check
passed

AUTO-DOCS-CHECK
PASSED (operational)

AUTO-PLAN-CHECK
FAILED (2 remaining governance bindings): final independent readiness audit and
cross-plan synchronization review are not bound to the updated plan snapshot.
The candidate therefore remains intermediate; those findings were not
self-approved or rewritten as Passed.
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

The candidate proves the pure replay policy, compatible/additive port shape,
closed snapshot input validation, catalog, and previously recorded real-data
migration path. It does not prove repository replay against a natural real
verification job, candidate HTTP/browser behavior, provider access, or
deployment. The integration-owned coordinator keeps raw SQL details out of the
application/composition port while one consuming use case owns the transaction.
The independent review rejected the original composition race and semantic-owner
metadata; the later atomic-initiation correction addresses those two findings.
Migration `v1_0717` must not be used for activation before the corrected
candidate is integrated, independently re-reviewed, and the broader M6
completion gates pass.
