# Ollama cloud collection candidate — 2 November 2026

Scope M6-T004/T005/T006/T010/T011; M6-A01/A03/A04/A07/A09; CTR-COL-002/008, CTR-REG-011 and CTR-CAP-004 1.0.0. This is an unwired intermediate candidate, not a live collection or M6 completion claim.

The candidate delegates due-account selection and durable rate admission to M04's existing fair global gate. It converts only a typed successful Ollama source result to M05 windows and uses a fence-required capacity writer. Inside the same SQLite write transaction, the writer checks the active M04 rate lease, a real M04 run already in committing state with its collection lease and matching account, scope, source, digest and generation, and the current M02 active credential binding. It records cooldown after successful commit; source failures can complete separately. Scope remains explicitly partial so unknown windows are not retired. The source is not registered in the service. Acquisition rejects before touching the database while authenticated-source admission, strict source/DNS deadline, or strict wire-header bounds remain false.

Pure cross-account and source-outcome tests failed before their functions existed, then passed. Nineteen focused tests including actual empty SQLite migration and unadmitted-source rejection passed; lint passed. Atomic SQL guard tests, actual scheduled selection, real M04 run creation and finalization, source invocation, failure/cooldown flow, capacity writes and concurrent lease/credential rotation are Not Run. Full red/green evidence is absent for these I/O behaviors. No real account, keyring item, provider API request, existing dashboard service, or live database was accessed.

Outstanding before use: implement the caller that creates and progresses the normal M04 collection run and marks it committing, handles durable receipt/finalization and interrupted rate leases; implement the approved private keyring grant and bounded authenticated source; verify actual account target/resource ownership; add real account and concurrency tests; preserve the provider period start, which current M05 window projection does not store; and integrate dashboard/history/status through contracts. The new M04-owned in-transaction validators are internal adapter ports; the generic M05 contract remains unchanged. Scheduling and authenticated collection remain disabled.

Follow-up candidate adds non-run schedule registration to resolve the first-account scheduling cycle, account/profile/resource and active-binding eligibility, M04 `admit_run` / `mark_running` / `mark_committing` / receipt finalization, and M04 committing-run receipt recovery without another provider request. The M02 transaction fence now additionally checks account monitoring state and the current profile/resource graph at capacity commit. Registration, admission and dispatch remain blocked by the actual source policy; no running service wires these functions. A thrown source operation leaves the durable global rate lease unresolved rather than guessing whether a late 429 occurred.

The pure account eligibility test failed before implementation and then passed. Twenty focused tests and empty-schema migration checks passed; lint passed. The new real-DB schedule registration, actual run transitions/recovery, account graph SQL, simultaneous disable/rotation and source invocation have not been exercised; their complete red/green and live evidence are outstanding. The caller still needs to construct a real `CollectionRunAdmissionV1` from eligible M02 data and actual provider manifest, and supply the admitted source and credential-grant boundary; no collector service or scheduler is enabled. Existing schedule generation changes currently fail closed rather than being reconciled. The 64-bit gate and M04 run lease have independent crash lifecycles: receipt recovery intentionally does not clear an unresolved global rate lease. No live data or provider was accessed.

Further candidate work based on b90b587 constructs `CollectionRunAdmissionV1` from actual M02 account/profile/resource views, the real supported manifest, and fresh non-secret operation identifiers. A tick enumerates eligible records, registers real target schedules, reserves the fair M04 gate, invokes the existing isolated `read_cloud_balance_for_binding_v1` worker for the selected active binding, constructs typed provenance, and sends the result through the M04/M02-fenced capacity writer and run finalization. The target cannot run until the existing source policy is admitted and the actual provider manifest declares the documented cloud quota source as supported; the current manifest has no such declaration. The source/manifest checks prevent inaccurate claims of cloud admission. The collector is still not wired into the running service.

The real current-manifest test failed before the manifest-binding guard existed and passed after implementation. Twenty-one focused policy/empty-schema tests passed and lint passed. The actual registry-to-run construction, first schedule registration, authenticated worker, typed response mapping, M04 state lifecycle/recovery, race fences, cooldown, account graph and dashboard flow have not been run against real Ollama accounts. Existing-generation schedule reconciliation, profile/resource provisioning for cloud accounts, preserving provider period start, strict source/DNS/wire limits and owner-assisted live verification are outstanding. Source and manifest remain unadmitted; this is not an M6 completion or live-success claim. No account credential, API response, live database, or service was accessed.

Follow-up: an unchanged schedule can now advance its target generation atomically only when neither the M04 run lease nor cloud request lease is active; it retains its existing next-due and backoff values. Pure generation policy failed before implementation and passed after. Real target generation/lease concurrency is Not Run. The capacity commit now also cross-checks rate/run scheduler, account, schedule, profile, request digest, manifest, adapter/policy versions and deadline in the same transaction. Collector selection catches only the dedicated ineligible-target error; other failures remain visible. Source deadline uses the shorter remaining run/rate lease budget and a fresh clock. Pre-dispatch crash recovery, durable completion journaling, recovery after source outcome, and exact cloud source-lane selection remain unresolved and block enabling collection.

Provider-reported source-period starts are carried in the M05 input window and payload digest, persisted in a nullable quota-observation column under additive offline v1_0710, returned in M05 history, and exposed as an optional public history API field with regenerated OpenAPI/TypeScript contracts. Existing observations remain null and old no-period payload digests remain unchanged. Pure period projection and a real empty SQLite migration test failed before their changes and passed after; the OpenAPI generator reports compatible. Real provider period observation persistence/API/browser verification is Not Run. v1_0710 requires verified backup and offline upgrade; it has no downgrade, so old application rollback requires restoring that backup or a forward repair. No live data was migrated.

The canonical offline AUTO-MIGRATE routine now supports v1_0709 to v1_0710 as well as the earlier admitted upgrade sources. Its real isolated v1_0709-to-v1_0710 test failed before the routine was updated and passed afterward with a verified prior backup. All 10 offline migration integration tests and 38 focused schema/contract/policy tests passed. This was an isolated empty database, not a populated customer upgrade or live deployment. OpenAPI/client drift verification passed after regeneration. No dashboard or production database was changed.

A further disabled candidate adds offline M04 schema v1_0711: an exact source-lane schedule table and a durable non-secret rate-attempt journal. The journal records a bound M04 run, reserved/dispatched/outcome phases, and exact outcome/time/jitter. The M04 run and journal binding are written in the same admission transaction. A reservation can be cancelled only against the exact owner lease; cross-owner recovery requires expired/stale ownership. Known outcomes can replay their original cooldown; unknown post-dispatch outcomes remain explicitly unresolved. Bounded recovery attempts to reconcile linked expired queued/running runs and existing committing receipts. Old completed rate attempts are backfilled from existing sanitized rows; old active/expired attempts become legacy-unresolved rather than being guessed safe. The M04 fair selector joins the exact cloud source lane. The standard offline migration supports v1_0710→v1_0711 with verified backup.

The real empty-registry migration and no-candidate admission test, isolated v1_0710 upgrade with backup, and other targeted schema/contract/policy tests passed: 62 tests total. These do not cover populated legacy backfill, authenticated source dispatch, actual account/graph transitions, mark-dispatched/outcome journal operations, CAS races, crash/replay, or M04/rate journal convergence; all remain Not Run and require real-system evidence and independent review. The source still has no admitted authenticated live operation. v1_0711 is not deployed, requires offline upgrade and verified backup, and has no downgrade. No live database, keyring item or provider data was accessed.

Dispatch-certainty follow-up: the isolated worker now reports a closed `not_started`, `may_have_started`, or `response_received` state (source work from commit 583fe47). The collector journals a recoverable failed attempt for a proven pre-wire credential failure and retains the global gate for ambiguous may-have-started outcomes; it does not infer dispatch from an error string. An actual M04 run is attached to its rate journal in the same transaction as run admission. Same-owner cancellation requires the exact rate lease; cross-owner replay requires stale ownership and an expired lease. Legacy active/expired rate attempts remain explicitly unresolved, and legacy completed outcomes are backfilled. This supersedes earlier text suggesting a reason-code inference.

The collector invokes the isolated binding worker only. Its readiness check therefore uses the worker isolation/deadline flags, not the unrelated in-process deadline/DNS flags. Authenticated live validation, the approved wire-header bound and a supported cloud manifest are still missing. This candidate remains unwired. Full real-account tests for populated legacy backfill, rate/run journal transitions, concurrent cancellation/dispatch, source certainty, graph and credential races, recovery convergence and the user-facing result remain Not Run; the source agent independently verified its anonymous 401 and bounded child deadline, not authenticated collection. Persisted failure reason/retry provenance across interrupted-run recovery also still needs review. No real account/keyring item or live service was touched by the collector work.

A follow-up candidate adds `CTR-COL-009` 1.0.0 / `OllamaCloudNoResponseCompletionV2` and offline schema v1_0712. It stores a proven no-request terminal time, closed source category and certainty separately from the V1 response-received timestamp; the overlay is authoritative over the retained V1 admission shadow. The rate gate and overlay transition are atomic, prior cooldown is preserved, and exact lease identity is required. A V2-proofed M04 finalizer releases rather than consumes a provider-request budget when no request was sent. This supersedes the earlier no-response limitation and reason-string inference; it does not establish live correctness. The same migration retains safe failure category and enforces one journal per M04 run. The cloud selector removes stale source-lane registrations, and rate advice never shortens a provider-directed wait.

The V2 type and real empty-schema migration checks pass; the isolated v1_0711→v1_0712 backup-and-upgrade check has been run during development. Populated legacy upgrades, exact V2 replay, same/different-admission uniqueness, concurrent dispatch/cancellation, crash journal convergence, keyring-unavailable execution, real source and dashboard observations remain Not Run. The canonical AUTO-PLAN-CHECK currently fails on stale contract counts/adoption snapshots and other pre-existing automation catalog drift; it is not a passing lifecycle gate. v1_0712 is not deployed, needs an offline verified backup/upgrade, and has no downgrade. Source and scheduler remain disabled.

## V2 no-response persistence checkpoint

The candidate adds CTR-COL-009 v1.0.0 and schema v1_0712 to record a proven no-request outcome without inventing a provider response time. It preserves the exact sanitized failure category and rate-limit outcome for journal recovery, releases the associated request budget only with fenced no-request evidence, and keeps unknown dispatched outcomes unresolved. This affects M04 collection contracts and persistence, the Ollama adapter and the M04/M05 collection composition; it does not enable cloud scheduling.

Verification on this checkout: 16 focused domain, provider-policy, real empty-SQLite migration and registry tests passed, including an empty v1_0711-to-v1_0712 upgrade with a backup. Ruff and Git whitespace checks passed. The schema digest was recomputed from an isolated fresh Alembic migration. The V2 domain test had previously failed before its contract was added; the new persistence and recovery behavior has **not** received its required behavioral red/green or concurrency tests. Populated migration, crash and compare-and-set recovery, live Secret Service enrollment, authenticated provider collection, dashboard verification and the completion gate remain **not run**. The prior planning validator remains failing and must be reconciled before lifecycle approval. No dependency or license changes were made. The migration is forward-only and requires the documented backup; no live database, user profile or agent was modified. No provider credentials or response content were recorded.

## Cloud-target migration checkpoint

The offline `AUTO-MIGRATE` candidate now supports v1_0712 to v1_0713 and
preserves the previously admitted upgrade sources. The v1_0712 upgrade test
first failed because that source was not supported, then passed with a verified
private backup after the update. The full isolated offline migration suite
passed 13 tests, including prior source revisions. This exposed and corrected
an earlier accidental change to the v1_0700–v1_0702 schema digest. These tests
used empty real SQLite schemas; populated upgrades, installed activation and
restore remain Not Run. No live application database was changed.

## Unwired owned-worker candidate

The cloud worker supervisor launches a separate AgentMonitor-owned process and
uses bounded termination waits; it is not registered with the dashboard and
source admission remains disabled. The real unadmitted-worker test failed before
the worker module existed and passed afterwards without creating a database or
sending a provider request. Ruff passed. Timeout, cancellation and orphan-helper
races, real credential use, authenticated reads, crash recovery and the
completion gate remain Not Run. Pending independent review, this is not an
activation or shutdown-safety claim. No dependency or license changed.

A real worker cancellation check then failed because a subsequent worker could
start; after shielding process creation and quarantining the supervisor on
cancellation or timeout, both real unadmitted-process checks pass. This does
not verify whole-tree containment: the provider helper currently starts a
separate session. The worker stays unwired until that issue and real
interruption/recovery checks are resolved.

## Transient-unit containment candidate

The unwired supervisor now creates one uniquely named systemd user service per
attempt, checks its exact executable arguments, invocation and control-group
properties, and stops only that unit. A private cross-process lock and a
synchronized uncertainty marker prevent a subsequent start after an ambiguous
attempt. Seven real local subprocess and user-manager checks passed, including
independent-process contention, cancellation during startup, and stopping a
transient unit containing the actual anonymous Ollama source and its observed
helper. No key or account was used and no provider payload was retained. Ruff
passed. The earlier process-group candidate was withdrawn.

The manager-command timeout after a queued start has not been reproduced on a
real manager; code inspection indicates it retains the uncertainty marker and
quarantines later starts. Independent security review, populated migration,
authenticated provider operation, live browser behavior and the completion
gate remain Not Run. The supervisor is not wired into the dashboard service;
no user-agent process was targeted by the checks.

A real data-directory-with-spaces check showed that `systemctl show` flattens
arguments ambiguously. The unwired supervisor now quarantines such executable or
data-root paths before creating a unit. The follow-up real-path check passes;
its defensive pre-start behavior does not have separate Red evidence. This is a
known portability limitation until exact argument inspection is admitted.

The candidate now pins and revalidates the data-root and locked inode; a real
lock-path replacement check failed before that verification existed and passes
now. Cancellation cleanup uses one 20-second monotonic deadline and attempts
exact-unit cleanup even after a manager-start failure, preserving the durable
uncertainty marker on ambiguity. Nine real process/user-manager checks pass.
A real manager hang after queueing and an aggregate slow-manager shutdown have
not been reproduced; independent review and live service wiring remain open.

## v1_0715 and supervisor review follow-up

The v1_0713-to-v1_0715 offline upgrade check failed before those source
revisions were admitted and passed after updating the bounded command. The
complete isolated offline migration suite passed 15 tests, including verified
backups from v1_0713 and v1_0714. These use empty real schemas; populated
upgrade and installed activation remain Not Run.

The unwired supervisor now pins and rechecks its root and lock inode, owner and
mode, uses a single 20-second cancellation-cleanup deadline, and attempts
exact-unit cleanup even when the start command fails or times out. The real
lock-replacement check failed before the inode check and passes afterwards;
nine real worker checks pass. Manager `show` and `reset-failed` results are
checked and manager subprocesses use an allowlisted session environment.
A manager that accepts a start after the cleanup check, a truly slow manager,
and total shutdown under that condition have not been reproduced. In those
cases the durable marker prevents another start but does not prove cessation;
the worker remains unwired pending independent review.

The lock verification now also reasserts its nonblocking exclusive flock.
Nine real worker checks and the real application API-surface check passed after
that change. A queued unit can still appear after an absent-unit check and the
20-second cleanup deadline can expire before its 30-second runtime limit. The
marker blocks another attempt, but cannot prove the unit has stopped; worker
activation and settled-shutdown claims remain blocked.

## Populated cloud-target migration correction

The first real private-copy upgrade from v1_0707 failed at commit with a deferred
foreign-key error even though SQLite reported no current FK violations. The
v1_0714 and v1_0715 rebuilds now explicitly reject null cloud target fields,
check every FK in the same write transaction before resetting the stale deferred
counter, and verify both that deferral is off and foreign-key enforcement is on.
SQLite documents the counter-reset risk in its
[defer_foreign_keys reference](https://sqlite.org/pragma.html#pragma_defer_foreign_keys).
An independent reviewer inspected this bounded sequence. On the exact updated
migration snapshot, a real private copy upgraded and committed v1_0707→v1_0715;
row counts for five affected tables matched, and postcommit full integrity and
foreign-key checks passed. No rows were printed, the copy was deleted, and the
live database was untouched. Sixteen isolated migration checks also passed.
This does not validate installed activation, restore or other M6 behavior.

## Durable-job migration checkpoint

The v1_0715-to-v1_0716 offline upgrade test failed before the source revision
was admitted and passed after the bounded automation was updated. The combined
migration/job contract suite passed 22 checks. Independently, two real private
copies of v1_0707 upgraded and committed to v1_0716 with five key table counts
and all 12 alert-table counts preserved; postcommit integrity, FK enforcement,
FK checks and schema validation passed. No rows were printed and the copies
were deleted. No event with the new non-constraining reason was manufactured;
its real persistence remains Not Run. Installed activation is also Not Run.

The unwired transient worker candidate now checks queued verification before
scheduled collection. HTTP success remains pending until the exact historical
M02 verification receipt, M05 commit receipt and terminal M04 run reconcile;
interrupted terminal runs are finalized only after authoritative absence checks.
Recovery pages the bounded M04 query and fails closed on inconsistent or
excessive backlog. Focused domain/contract and real owned-worker boundary tests
pass; populated SQLite finalization, interruption races, authenticated provider
I/O and dashboard integration remain Not Run. Source and manifest admission
remain closed, and no key operation was executed. Worker time limits and
shutdown quarantine require independent review before activation.

`M6-OLLAMA-CLOUD-PROBE` is the separate one-shot source decision associated
with the approved `docs/plans/integration/m6-ollama-cloud-implementation-change.md`.
Its source metadata identifies the documented Ollama balance API; the first
observation is marked experimental and does not claim the scheduled provider
capability is supported. The source descriptor fingerprint binds the target,
run and receipt. The static source admission and owner key-use restriction
remain closed; no probe, secret access or live validation was performed.

The candidate runtime grant stores only the non-secret 64-character probe-policy
fingerprint. It is absent on this workstation. The fingerprint includes the
adapter version, source descriptor, payload schema and fixed transport policy;
it does not hash executable or parser files. Every parser, worker or protocol
semantic change therefore requires an adapter-version or fingerprint-schema
version bump before a grant or receipt can be reused. Revocation prevents new
dispatch but does not interrupt an already dispatched request. Marker creation,
revocation, authenticated probing and scheduled-source admission are Not Run.

The isolated signal-composition candidate rederives per-binding M03 scheduled
permission from the exact current M02 authority and credential generation,
terminal M04 verification job, M05 commit receipt, and latest M04 source
signal. Its final pre-dispatch query excludes only the caller's exact reserved
lease. Focused contract/domain tests and static checks pass. A credential
rotation race remains: the shared account lock must stay held through the
network helper and nested Secret Service subprocess, including parent death.
The populated SQL, race, authorization, provider and dashboard paths remain
Not Run; this candidate must not be activated.

The signal-composition candidate now checks the original terminal verification
job and exact M02/M04/M05 lineage before deriving M03 scheduled permission;
its final latest-signal read excludes only its own still-reserved lease. M05's
transaction also rechecks the active official cloud target and exact source
fingerprint. The pure target-fence test failed before the validator existed and
passes afterward; 50 focused contract/domain tests pass. A real populated
SQLite fence race, worker/helper credential-lock survival and authenticated
provider/dashboard flow remain Not Run. The candidate is not activated.

The account connection status candidate also reads the exact M04 latest signal
before presenting an older successful receipt as current access. Unauthorized,
incompatible or unresolved later outcomes are not displayed as current. The
pure status policy test failed before this mapping and passes afterward; real
account status/API and browser checks remain Not Run.

Connection status treats a verified signal as current only when monitoring is
on and an exact-run capacity window is fresh. Stale and transient-failure states
are distinct and retryable only when the durable gate permits; unknown freshness
stays unavailable. The new unshipped status states were checked against public
GitHub main rather than the intermediate candidate schema. Pure status checks
went red then green; real cloud status and browser behavior remain Not Run.

The candidate Ollama account page now reads the versioned connection status and
can request a check only when the server permits it. It displays stale and
retryable wording and the actual last-check time, and never accepts a credential.
Frontend typecheck and production build pass. No authorized cloud account was available
for a browser check; UI red/green, authenticated browser behavior and provider
verification remain Not Run. The running dashboard was not changed.
