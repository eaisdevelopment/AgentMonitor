# Change plan: owner-confirmed live agent account associations

- Status: **Approved for the bounded owner-directed increment after root review and contract synchronization**.
- Plan version: `1.0.0`; date: 2026-09-29.
- Owner: M06 Runtime observation; coordinated M02, A04-LINUX, P01, P02,
  and root composition/automation/operations.
- Parent: [M06 plan](../modules/m06-runtime-observation/plan-v1.md),
  `0.2.0-draft`; this change does not approve the whole module plan.
- Authority: the owner requested account drill-down for existing agents and
  confirmed ordinary Claude CLI terminals as their launch method. Existing
  implementation/system-action authorization persists; no new owner permission
  is requested. Root approved this concrete scope under that authority.
- Requirements: `FR-ACC-006`, `FR-DISC-001/002/004/007`,
  `FR-UI-002/004/006/007`, `FR-SAFE-002`, `FR-IAM-003/006/007`,
  `NFR-ARCH-001/002`, `NFR-DATA-001`, `NFR-API-001/002`, `NFR-SEC-001`,
  `NFR-PRIV-001/002`, `NFR-COMP-001`, `NFR-DOC-001`.
- Bounded acceptance: `AC-PROC-001/003/004`, `AC-UI-002/004/005/006`,
  `AC-TEST-001/002/003/004/006`; not full M4 or V1 acceptance.
- Contracts: additive `CTR-RUN-006/007` V1; existing M02 registry query V1,
  M01 authorization V1, P01 `/api/v1` schemas and P02 generated client V1.
- Storage decision: accepted [ADR 0015](../../decisions/0015-owner-process-account-associations.md).

## Outcome

An account page shows the currently observed Claude processes explicitly
associated with that account: PID, Running presence, current working directory,
observation time, and **Owner confirmed** provenance/time. Unassigned candidates
have a separate confirmation section; processes confirmed for another account
are not counted for the selected account. Running does not mean Working.
Unavailable model/task/token/activity/session fields remain unavailable. Quota
stays account-scoped; it is never described as the process's own allowance.

## Scope and ownership

M06 owns the settings repository and association/clear/query rules. A04 owns
fresh OS identity checks; M02 supplies account eligibility through its published
query; P01 authorizes/maps contracts; P02 uses the generated client; root wires
composition, automation, backup guidance and shared artifacts.

Allowed implementation areas after review: runtime contracts/application/ports,
a new `adapters/persistence/runtime_observation/settings/` adapter, necessary
A04 guarded recheck, runtime API router/schema/dependencies, account/live-process
UI, generated-client sources, root composition, tests and documentation.
The owner-reported real terminal uses a different installed native Claude
version than the current default executable. A01/root also discovers guarded
native executables within that existing installation's versions directory;
their actual official `--version` reads identify each admitted candidate. A04
scans each exact executable without changing any profile or running process.
Version coverage is verified against the owner's actual terminal, not invented
processes. Other installation types keep the existing single-executable seam.
Optional parent PID, CPU ticks and RSS details use the already approved stat
fields and published process snapshot contract. They do not prove Working.
Shared paths receive one assigned writer. This planning task writes only this
file. `FR-ACC-006` remains primarily PLAN-M02 in canonical requirement ownership;
M06 owns this runtime increment.

No automatic inference from default/current login, quota identity, directories,
organization, timing, executable name, sole account, or parent processes. No
launcher, provider/session instrumentation, process control, terminal input,
profile/auth change, argv/environment/content read, or fabricated sessions.
Children require independent evidence or confirmation. Domain code imports
contracts/ports, never OS/provider/framework/persistence implementations; API/UI
cannot read tables/settings or bypass public module ports.

## Current evidence and confirmation prerequisite

Current `/api/v1/process-locations` supplies real same-user processes matching
an admitted Claude executable, with boot/PID-namespace + PID + start identity
and guarded memory-only cwd. Its provider `account_correlation` is unresolved.
There is no established safe retrospective identity source for ordinary mixed
Claude terminals. Existing provider-session evidence does not identify them all.

Root recorded a real shared-browser Red through
`tools/ui/verify_account_agents.mjs`: exit 3,
`process_account_contract: process_account_association_contract_missing`.
Root also reports authored pure transition tests. This planning agent ran no
tests, browser, provider, or process operations; new Green/live results are
**Not Run** in this plan.

Before confirming, the owner identifies the exact corresponding terminal and
personally checks its actual Claude `/status` account against the selected
registry account. AgentMonitor neither sends `/status` nor captures terminal
output, screenshots, conversations or credentials. The owner may voluntarily
supply minimal non-secret account/path facts for coordination. If the terminal or
account cannot be distinguished, that row stays unassigned. The dashboard
requires an explicit `owner_confirmed=true` attestation.

Owner delegation update, 2026-09-29: after supplying genuine `/status` identity,
version, cwd and peer/PID details, the owner explicitly directed root to perform
the dashboard confirmation and test it through the shared browser. That
authorization permits this one corresponding metadata link and its verification
using those supplied facts. It does not authorize inspecting terminal content,
changing a provider login or assigning other unknown terminals. Canonical
verification still remains read-only and never creates its own attestation.

The timestamp records owner confirmation, not current provider verification.
Changing accounts inside the same PID cannot be detected from OS identity;
the UI explains that a terminal account change requires renewed `/status`
confirmation or clearing. Existing agents and launch workflows remain intact.

## Contract and data impact

Preserve existing GET fields and `account_correlation='unresolved'`. Add optional
`association_key` (opaque guarded selector), `association_record_version`
(default 0), and nullable `account_association` containing owner-confirmed
account ID, confirmation time, opaque actor ID and record version. The separate
revision exposes a cleared record's tombstone even when association is null.
M06 supports optional account filtering after joining fresh observations to
settings; P02 filters the generated global read to the selected account. Keep
the existing HTTP GET operation and query grammar unchanged: the canonical
conservative compatibility checker treats new GET parameters as breaking.
Keep availability and partial/truncated results;
an unavailable scan must not become a successful empty account fleet.

Add browser-administrator-only
`PUT /api/v1/process-locations/{association_key}/account` with nullable
`account_id` (null clears), `owner_confirmed=true`, mandatory per-process
`If-Match`, browser administrator authorization/`write:accounts`, transport
Origin proof, and CSRF. Bearer mutation is rejected. Publish initial revision 0
explicitly without relaxing other routes' existing version grammar.

Non-null association requires an active provider-matching M02 account and a
fresh A04 recheck of the complete process identity, owner and admitted executable.
Clearing also requires a current guarded process and its revision in this
increment. Inactive settings review/maintenance is a separate follow-up. No
response may invent Running presence for an exited process. Identical retries
return the stored actor/time/revision; stale nonidentical writes return 412.
Old requests cannot restore a cleared/replaced link. Missing preconditions,
invalid selector, exited/reused process, ineligible account, unavailable source
and storage failure have distinct sanitized outcomes with no partial write.
OpenAPI/client are regenerated normally; new DTOs/ports are additive V1.

ADR 0015 accepts the M06-owned
`owner-process-account-associations-v1.json` file in the validated owner-only
data root, separately from telemetry/history. Closed V1 records contain only
boot/namespace scope, PID/start identity, provider key, opaque account/actor IDs,
confirmation/update timestamps and revision. No paths, emails, raw boot ID,
provider sessions, credentials or arbitrary evidence strings are stored.
SQLite schema/migrations, stored observations and provider state are unchanged.
The ADR is necessary because this is a narrow exception to M06's planned SQLite
runtime persistence and introduces distinct compatibility/backup behavior.

The adapter enforces finite file/record bounds, version/shape/duplicate checks,
root ownership, regular-file mode/owner/link count and no symlinks. Missing file
means no settings. Unsafe, corrupt, unsupported or oversized files are
unavailable and never silently reset. A permanent protected lock serializes
writers; reload/check revision under lock, recheck process at commit, fsync a
private exclusive temporary file, atomic replace, then directory fsync. Keep
versioned null-account tombstones across clear/restart. GET never writes.

Only fresh matching observations contribute current attribution. Exit, PID
reuse, boot/namespace/executable/owner change or account archive excludes a
saved link; absence in a failed/truncated scan does not prove exit. Never show a
cached path/process as current. Preserve settings without presenting inactive
records as live agents; disclose failed/stale refreshes at the existing cadence.

## Test-first sequence

| Scenario | Boundary / expected Red | Required Green and evidence |
|---|---|---|
| M06-ASSOC-01 | Existing real shared browser: missing association contract/control (recorded Red above) | Selected-account rows, other-account exclusion, unassigned candidates, actual PID/path/presence and Owner confirmed provenance through generated API |
| M06-ASSOC-02 | Real migrated registry/SQLite, filesystem, Uvicorn/HTTP: missing association persistence/query | Owner-completed actual-process link survives reopen; account filtering is correct; no invented session/telemetry rows |
| M06-ASSOC-03 | Real HTTP: missing auth/precondition/security enforcement | Anonymous, bearer mutation, bad Origin/CSRF, missing/stale version, invalid key and wrong/archived account are inert; genuine owner browser confirmation succeeds |
| M06-ASSOC-04 | Pure identity/revision policy: missing guards/tombstone/replay rules | No PID-only match; scope/start differences fail; stale different changes reject; identical replay is safe; clear retains revision |
| M06-ASSOC-05 | Actual protected isolated filesystem: missing safe/durable settings behavior | Atomic/concurrent/restart/clear behavior; corrupt/version/size/permission/symlink failure is closed; no prohibited stored/output fields |
| M06-ASSOC-06 | Real admitted Linux process + owner `/status` confirmation | Read-only acceptance gate observes owner receipt and fresh identity; naturally exited process is excluded; unavailable actual PID-reuse/boot cases remain Blocked/Not Run |

Use genuine registered accounts and actual processes at I/O boundaries. Pure
constructed identity inputs prove policies only, not OS/provider compatibility.
No mocks, fabricated account/session/process telemetry or provider replay.
Do not stop/signal owner agents to manufacture an exit. Each behavior retains
its meaningful Red, Green and refactor evidence; the one browser Red is not
universal TDD evidence.

The final browser/owner acceptance gate is read-only: it checks an actual
owner-completed confirmation receipt and never clicks Confirm or submits an
attestation itself. Owner terminal interaction remains a named prerequisite;
unavailable live confirmation blocks only its acceptance scenario while
independent implementation proceeds.

## Security, operations, documentation and rollback

No new dependency: current stack/standard library suffices; verify unchanged
license/lock/SBOM impact. Authorization, origin proof, CSRF, guarded identities,
metadata-only storage and truthful provenance address R-003/005/007/015.
ADR 0015 records R-020's backup consequence: SQLite-only backups do not include
these settings. Document offline same-installation backup of settings/lock,
permissions/checksum/version checks, and identity revalidation after restore.
Full M08/native backup acceptance is outside this bounded increment.

Root updates M06/P02 guides, API/client artifacts, settings/schema reference,
backup/restore/user runbook, sanitized evidence and exact traceability. Rollback
the binary/frontend; old code ignores the separate file and keeps unresolved
legacy reads. No destructive database downgrade or provider change is needed.

## Stop conditions and completion gate

Root reviewed the independent M06 proposal and synchronized exact revision,
tombstone and initial-version semantics, finite limits, permissions and root
write ownership. ADR 0015 is Accepted. Stop affected work for incompatible contracts, owner conflicts,
prohibited data, process/profile mutation, fabricated sessions, new dependency,
or destructive migration; escalate the smallest sufficient correction to root.
No additional owner permission is needed for the authorized scope.

Canonical gate registered and executed by root; the owner's explicitly delegated
confirmation, real receipt and named post-restart gate Passed:
`python3 tools/automation/run.py AUTO-ACCOUNT-AGENTS`. Root must codify the real
HTTP/filesystem/reopen and read-only owner/browser checks with explicit private
data-root, account/process/dashboard selectors and an owner-completed receipt;
missing prerequisites exit Blocked. Include generated-client/build checks and
applicable `AUTO-DOCS-CHECK`/`AUTO-QUALITY`; report Failed/Blocked/Not Run separately.
No completion claim until the exact bounded gate passes and independent review
accepts the contract/privacy boundary. Full M4, automatic terminal attribution,
macOS and universal M06 acceptance remain separate.

Approval: independent M06 planning proposal reviewed by root; bounded contract,
security/privacy, P01/P02/A04/M02 and operations assessment accepted under the
owner's implementation authority. Independent bounded implementation reviews
and the named account-link/browser/persistence gate Passed; unexecuted live
edge cases are recorded in the progress evidence. This does not approve the
whole Draft M06 plan or full M4.
