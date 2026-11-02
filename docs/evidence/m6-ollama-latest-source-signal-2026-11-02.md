# Test evidence: M6 exact Ollama cloud source signal

- Evidence ID: M6-OLLAMA-LATEST-SOURCE-SIGNAL-2026-11-02
- Module/plan/increment: M02 `PLAN-M02`, M03 `PLAN-M03`, M04 `PLAN-M04`
- Requirements/acceptance IDs: M6-A03, M6-A04, M6-A05, M6-A07, M6-A09, M6-A10
- Contract versions: registry V1 access-target/read port, `CTR-COL-008` V1,
  `CTR-PROV-003` V1
- Commit/worktree reference: `codex/m6-m04-latest-signal` based on `20bd758`
- Recorder/date: Codex, 2026-11-02

## Test inventory and status

| Test/scenario ID | Layer | Real dependencies | Status | Evidence reference | Notes |
|---|---|---|---|---|---|
| M6-SIGNAL-PURE | Pure | None | Passed | Focused pytest | Closed outcome mapping, exact lineage and fail-closed transient combinations |
| M6-SIGNAL-MIGRATE | DB | Private SQLite backup of the real dashboard database | Passed | `AUTO-MIGRATE` | `v1_0707` to `v1_0716`; service activation Not Run |
| M6-SIGNAL-REAL-ROW | DB | Natural Ollama cloud target and run rows | Not Run | Private-copy count only | The real private copy contained zero cloud targets and zero cloud runs; no rows were fabricated |
| M6-SIGNAL-PROVIDER | Provider | Owner credential and official endpoint | Not Run | None | No credential, provider request or profile access occurred |
| M6-SIGNAL-API-UI | API/browser | Running candidate service and built UI | Not Run | None | This slice publishes internal module ports only |

## Red evidence

The initial structural Red failed during collection because
`OllamaCloudLatestSourceSignalQueryV1` did not exist. After the first candidate
implementation, a behavioral review added two pure cases for inconsistent
transient signals. The focused command reported `2 failed, 43 passed`: both a
successful M04 projection and a successful M03 lineage incorrectly accepted
`transient_failure`. A separate pure Red (`1 failed, 14 passed`) proved that an
unclassified unexpected HTTP response was incorrectly labelled as provider
schema incompatibility instead of remaining unresolved. No I/O or
provider-shaped payload was constructed.

## Green evidence

The same focused command passed `45 passed` after the projection, lineage,
proof and derivation boundaries required a failed run and a known-start
certainty for transient signals. The final coordinated M02/M03/M04 focused set
passed `77 passed`. Ruff, mypy over the eight changed source modules,
`AUTO-DOCS-CHECK`, and `git diff --check` passed.

## Real-system evidence

An owner-only private SQLite backup was created with SQLite's real backup API.
The canonical offline migration command passed from `v1_0707` through
`v1_0716` and reported a verified preflight backup; service activation was Not
Run. Read-only counts found no natural Ollama cloud access target or cloud run,
so the exact SQL row projection and target lookup could not be exercised
without prohibited fabricated I/O. The private copy was removed after review.

## Integrity declaration

No mock, fake, stub, emulator, recorded provider response, demo account,
seeded telemetry, placeholder value, disabled assertion or test-only
production branch was used. Constructed values were limited to pure domain
tests with no I/O behavior.

## Data and secret review

No API key, credential, profile, provider payload, prompt, response, source
content, account address or arbitrary environment value was read or recorded.
Evidence retains only schema revisions, aggregate counts and sanitized test
results.

## Conclusion and residual gaps

The evidence supports the pure closed classifier, exact provenance contracts,
read-only port implementations and migration compatibility on the available
real private database. It does not prove a natural populated target/signal
read, provider access, service composition, scheduled dispatch, API, browser,
deployment or M6 completion. Those remain explicit integration and live-gate
work.
