# Test evidence: M6 retained-release v1_0718 cutover

- Evidence ID: `M6-V0718-RETAINED-CUTOVER-2026-11-03`
- Module/plan/increment: integration operations, approved M6 Ollama cloud plan
- Requirements/acceptance IDs: `FR-SAFE-001`, `NFR-DATA-001`, `M6-A03`,
  `M6-A04`, `M6-A07`, `M6-A09`
- Contract versions: no public contract change; database target `v1_0718`
- Commit/worktree reference: `codex/m6-registry-revision-fix`
- Recorder/date: Codex, 2026-11-03

## Test inventory and status

| Test/scenario | Layer | Real dependencies | Status | Notes |
|---|---|---|---|---|
| v1_0717 normal cutover | Platform/DB | Disposable systemd user unit and file-backed SQLite | Passed | Exact backup created and schema reached catalog head |
| killed backup/commit recovery | Platform/DB | Disposable systemd, SQLite and real process interruption | Passed | Earlier backups retained; migration recovered without starting service |
| pre-start restore and restart | Platform/DB | Disposable systemd and atomic SQLite restore | Passed | Exact v1_0717 database and baseline process restored |
| override-installed interruption | Platform/DB | Real `strace` scheduling, systemd and SQLite | Passed | Candidate override was normalized before verified backup restore |
| candidate-start interruption | Platform/DB | Real `strace` scheduling, systemd and SQLite | Passed | Only the recorded v1_0718 candidate resumed; no database rollback |
| unchanged-schema update/recovery | Platform/DB/HTTP | Disposable systemd, SQLite and real local HTTP | Passed | Existing no-backup path remained separate |
| historical v1_0707 cutover/finalize | Platform/DB/HTTP | Disposable systemd, SQLite and real local HTTP | Passed | Original fixed-baseline migration path remained operational |
| registered `AUTO-MIGRATE` | Real private DB copy | SQLite online backup of installed v1_0717 database | Passed | Dispatcher migrated the copy and preserved the real current receipt |
| fixed installed dashboard rollout | Platform | Installed service and live data root | Not Run | Root steward owns deployment after integration and review |
| provider verification | Provider | Ollama cloud | Not Run | No provider call is needed for migration/cutover correctness |

## Red evidence

Before production changes, the existing real disposable cutover test initialized
an actual SQLite database at `v1_0717` and ran a real systemd user unit. The
cutover failed at the intended behavior boundary:

```text
tools.automation.implementations.m6_cutover.CutoverError:
cutover_selection_invalid
```

The command was:

```text
PYTHONPATH=.:backend/src .../backend/.venv/bin/pytest -q \
  tools/automation/tests/test_m6_cutover.py -k normal --maxfail=1
```

## Green and refactor evidence

```text
tools/automation/tests/test_m6_cutover.py
24 passed in 281.15s

tools/automation/tests/test_m6_same_schema_update.py
9 passed in 164.75s

tools/automation/tests/test_m6_actual_candidate_finalization.py
1 passed in 11.89s

backend/tests/live/ollama/test_verification_receipt_history_migration.py
1 passed in 25.11s
```

The live migration test invokes the registered dispatcher form
`tools/automation/run.py AUTO-MIGRATE` against an owner-only private SQLite
backup, not the installed database.

Static production checks:

```text
ruff check --config backend/pyproject.toml \
  tools/automation/implementations/m6_cutover.py
All checks passed!

MYPYPATH=backend/src mypy --strict --config-file backend/pyproject.toml \
  tools/automation/implementations/m6_cutover.py
Success: no issues found in 1 source file
```

## Real-system and safety result

`AUTO-M6-CUTOVER` remains the schema-changing command. It now accepts only the
exact retained sealed baseline with source `v1_0717` when the reviewed catalog
head is `v1_0718`. `AUTO-M6-CURRENT-UPDATE` remains same-schema and backup-free.
The historical fixed `v1_0707` cutover remains accepted.

Before candidate startup is attempted, recovery retains the verified backup and
can restore the exact retained baseline. If the candidate override was already
installed, it is returned to the exact baseline override under the transition,
service-quiescence and settings locks before the database exchange. After the
durable candidate-start boundary, recovery may resume only the exact candidate
and never restores the old database.

No mock, fake, stub, emulator, seeded row, fabricated provider response,
placeholder value, disabled assertion or test-only production branch was used.
No API key, `.env` content, provider payload, account identifier, prompt,
response or arbitrary process environment was read or recorded. No dependency,
license, API or provider-profile change was made.

## Residual deployment boundary

The installed fixed-service rollout and browser/provider verification are Not
Run here. Before rollout, the root steward must prove that no older active
`.m6-cutover-journal.json` exists. An older target-catalog journal must be
recovered with its matching retained controller; this change does not reinterpret
it under the v1_0718 catalog.
