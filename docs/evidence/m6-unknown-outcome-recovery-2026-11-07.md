# M6 unknown Ollama outcome recovery — 7 November 2026

Status: focused implementation verification; not M6 acceptance or live recovery.
Requirements: FR-COL-003/007; M6-A07/A09; M6-T011/T012. Owner: M04.
Contracts: CTR-COL-008 1.2.0; existing CTR-COL-002 run lifecycle; schema v1_0720.
The parent integration agent approved this correction within the already approved
M6 cloud timeout/network recovery scope.

The actual database contained one expired `dispatched` request with nullable
outcome, response time and retry metadata. Restart did not resolve it. Initial
real-backup tests failed because recovery returned `outcome_unknown` rather than
recovering and never reached stale-owner discrimination. No provider data was
seeded. The additive migration and dedicated receipt preserve the original
journal/admission and known gate deadlines. A full 300-second fallback plus
bounded jitter starts at recovery; only the expired, stale, exactly fenced owner
can be released. A separately classified known unrepresentable Retry-After is
held indefinitely, including when recorded after lease expiry.

Pure contract Red: `test_recovered_unknown_projection_keeps_dispatch_uncertainty`
failed with `ollama_cloud_source_signal_invalid` before CTR-COL-008 1.2.0 admitted
the explicit failed/unknown combination. Pure time-policy Red: conservative hold
after expiry returned false under the previous time rule. Dispatch/commit still
require the original unexpired time window.

Private actual-copy composition verification exercises `recover_journals`, exact
run failure, source-signal projection, repeated idempotent recovery, retained
minimum cooldown, unchanged historical admission/journal, foreign-key check and
SQLite integrity. It opens no provider session and sends no balance request.
Historical unknown metadata cannot establish whether a response carried a lost
Retry-After; the plan explicitly records this limitation. A successful live
provider response and the canonical M6 gate are still required separately.

Security/privacy: no credential/profile/account mutations, no raw payload or
secret output, no dependency/license changes. Backup copies use owner-only
permissions and are removed after tests. Migration adds only technical recovery
receipts and rejects contradictory hold/release shapes. Rollback restores the
verified pre-migration backup with its matching service revision; no destructive
in-place downgrade is introduced.

Focused Green command (backend virtualenv Python, `PYTHONPATH=backend/src`):

```sh
python -B -m pytest -q \
  backend/tests/integration/collection_control/test_cloud_unknown_recovery.py \
  backend/tests/persistence/sqlite/migrations/test_v1_0000.py \
  backend/tests/collection_control/domain/test_ollama_latest_source_signal.py \
  backend/tests/collection_control/domain/test_ollama_unknown_recovery.py
```

Result: **75 passed**, zero skips, 31.59 seconds. Focused Ruff check over all
changed M04, contract, compatibility and regression files also passed. Full
quality, exact deployment, live recovery and canonical completion remain owned
by integration; they are not implied by this focused result.

Independent review found an additional known-deadline loss: the existing
`record_completion` expiry check could reject an already received, representable
Retry-After before journaling it. The correction permits only a truthful
`rate_limited` outcome to be journaled after expiry, retaining every exact active
gate/owner/fence check. Both before and inside the write transaction, response
time must be no earlier than start and no later than the actual wall clock.
Late success/quota commits remain forbidden. Pure Red showed the old expiry
rule reject the rate-limit record; Green covers this restriction-only exception.
No live 429 was induced or fabricated; that external case is not claimed tested.

Integration checks before rollout: the canonical source/security selection
passed 118 tests with zero skips; completion-policy and actual-copy recovery
selection passed 30 tests with zero skips. Combined quality initially identified
an optional-string annotation and an outdated boundary contract version; both
were corrected, and `AUTO-QUALITY` passed, including strict typing, module
boundaries, generated API compatibility, frontend typecheck and build.
`AUTO-DOCS-CHECK`, `AUTO-PLAN-CHECK` and local `AUTO-GIT-PREFLIGHT` passed.
These are pre-rollout results, not evidence of restored live provider collection.

## Downstream scheduled readmission correction

After deployment recovered the actual orphan, its next scheduled attempt exposed
three downstream M03 guards that still rejected failed/transient uncertainty.
The new actual-state backup test `test_actual_recovered_target_can_rederive_scheduled_proof`
failed with `scheduled_source_lineage_invalid` through the public composition
method before correction. The pure lineage-to-proof test failed at the same
contract guard. CTR-PROV-003 1.2.0 now accepts this exact combination throughout
lineage, domain derivation and proof construction, retaining all original
verification/binding/source checks. The pure suite is included in the canonical
M6 source-security selection; the state-dependent real backup test is retained
as explicit evidence rather than a permanently assumed provider state.

Independent review also found that terminal unknown verification jobs conflict
with the immutable v1_0716 database constraint. No such job is fabricated for
testing. Recovery now refuses to release a request associated with a verification
job and retains its prior unresolved state; the invalid terminal UPDATE was
removed. Pure Red produced a retry deadline for four verification-job states;
Green requires no deadline for every one. CTR-COL-010 remains 2.0.0. This is an
explicit limitation, not a claim that verification interruption recovery passed.
The earlier three orphan-copy tests are historical pre-repair evidence; after
the live orphan recovered they can skip and are not claimed as a new pass.

Final focused consumer verification: **55 passed, zero skips** in 9.87 seconds
(provider scheduled admission, actual recovered-target proof, unknown-recovery
policy and existing strict verification-job contracts). Focused mypy passed all
seven changed source/test files; Ruff check and format check passed.
`AUTO-PLAN-CHECK` passed after canonical adoption/snapshot regeneration;
architectural boundaries passed with zero violations. OpenAPI/client generation
passed with compatible output. No live DB, account, key or provider request was
mutated by this verification.
