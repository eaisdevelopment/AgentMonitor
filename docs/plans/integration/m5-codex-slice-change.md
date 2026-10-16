# Change plan: executable V1-M5 Codex slice

- Status: **Approved 1.5.0 for the root-owned M5 complete-scope lifecycle
  correction and one exact second service rollover**.
- Plan version: `1.5.0`; owner approval: 2026-10-16.
- Safety correction: exact-version review proved that authenticated app-server
  queries may perform Codex's automatic credential refresh. The approved
  managed-auth lifecycle therefore classifies those queries as
  `managed_profile_write`, and an empty/uninitialized managed root is rejected
  before any app-server child starts.
- Owner: `PLAN-INT`, with A02 provider behavior and the exact PLAN-DEP/D01
  service-activation exception owned under this bounded change.
- Parent plans:
  [V1-M5 milestone](../../superpowers/plans/2026-09-19-agentmonitor-v1-m5-codex-slice.md)
  and [A02 adapter](../adapters/codex/plan-v1.md).
- Authority: the active owner objective, **fully implement M5 with our SDLC and
  runbook**, approved version 1.4.0 and its first corrective rollover. The
  owner's explicit 2026-10-16 approval extends the same focused A02 and
  PLAN-DEP/D01 exception only by the exact complete-scope lifecycle correction
  and one second rollover from
  `063445154bca0bf5ec43db94ba57c17fd193fd99` specified below. The remaining
  A02, OpenAI API, PLAN-DEP/D01, and `AUTO-DEPLOY` lanes stay Draft or Blocked
  as already recorded.
- Stories: `ST-CDX-001..005`.
- Requirements: `FR-ACC-001/004..006`, `FR-AUTH-001/002/004..006`,
  `FR-QUOTA-001..006`, `FR-COL-003..008`, `FR-HIST-001/002`,
  `FR-DISC-001/003/004/006/008`, `FR-STATE-001/002`, `FR-SAFE-002`,
  `FR-ALERT-002..006`, `FR-UI-001..006`, `NFR-API-001/002`,
  `NFR-TEST-001/002`,
  `NFR-SEC-001`, `NFR-PRIV-001/002`, `NFR-RES-001`, `NFR-OBS-001`,
  `NFR-COMP-001`, and `NFR-DOC-001`.
- Acceptance contributions: `AC-LIVE-002/004/005/007`,
  `AC-UI-002/005/006`, `AC-PROC-001..004`, `AC-HIST-001`,
  `AC-ALERT-002`, `AC-OPS-003/006`, and `AC-TEST-001..006` within
  M5's Codex boundary.
- Contracts: compatible V1 use of `CTR-PROV-001..008`, `CTR-REG-001/002/004/
  005/006/009/010`, `CTR-COL-002/004/006/007`, `CTR-CAP-001/003/004/007`,
  `CTR-RUN-001/002/003/006/007`, `CTR-PLAT-001`, `CTR-OPS-004/006`,
  `CTR-ALERT-001..005`, `CTR-CAP-008/009`, `CTR-EVT-001`, `CTR-API-001`,
  and `CTR-UI-001`.

## Outcome

AgentMonitor admits the exact installed Codex CLI, lets an administrator create
and organize any number of Codex account records, connects only explicitly
selected AgentMonitor-managed profiles through Codex's official browser login,
verifies the returned identity, and schedules native subscription limit
collection into the existing capacity/history model. Provider-controlled
authentication maintenance may update only that selected managed profile.
Overview, account,
history, process, provider-capability, and operations views remain
provider-neutral and show Codex alongside Claude.

The M5 fleet witness selects four real Codex accounts, or records an actual
owner-unavailable outcome allowed by `AC-LIVE-002`, and observes five to six
representative real Codex processes. Process/account correlation uses existing
guarded owner confirmation when provider evidence is insufficient; it never
guesses or controls a process.

The canonical interactive `AUTO-M5-OWNER-OUTCOMES` routine reads the real
owner Registry through its public query composition and creates
`<owner-data-root>/m5-owner-outcomes.json`: one owner-only, no-symlink,
single-link regular file containing exactly four unique opaque account IDs and
unique private aliases. It binds the explicit owner confirmation and timestamp
to the current clean implementation revision and selected pre-gate service
PID/start identity. Each row is either `verified` or `owner_unavailable` with
an owner reason. At selection, disposition, and confirmation checkpoints, each
alias and opaque account ID is shown with the fixed safe labels `vendor: OpenAI`
and `provider: Codex`; those labels are not added to the persisted closed
schema. The file accepts no private identity fingerprint; distinct
verified identities are derived from current authenticated API results in the
live browser gate. The gate rejects `unresolved`, duplicate, extra, missing,
public, stale, wrong-revision, wrong-service, or changing rows. Only its SHA-256
digest and aggregate counts enter sanitized evidence.

The canonical interactive `AUTO-M5-QUOTA-WITNESS` routine depends on that
owner-outcome file and creates
`<owner-data-root>/m5-quota-witness.json`. It invokes no provider operation. A
new page in the authenticated shared loopback browser proves each verified
account's current identity, collection lineage, exact API, DOM and retained
history quota values, and zero browser mutations. The owner reads only whole
percentages and reset facts from each account's official Codex `/usage` view;
the routine requires exact percentages and semantic roles, reset agreement at
the displayed second/minute/hour/day precision, and at most 300 seconds between
the provider observation and AgentMonitor collection. It records only counts
and digests in the closed `agentmonitor.m5-quota-witness.v1` schema.

The quota witness binds its owner confirmation, clean revision, an equal
running-service source revision from the Operations inventory, selected
pre-gate service PID/start identity, owner-outcome digest, exact Codex version
and source, identity set, collection runs, value set, API/DOM/history proof and
complete public Registry graph. It is an owner-only, no-symlink, single-link
`0600` file of at most 16 KiB, created once and never replaced. It is current
for 15 minutes with one minute of future clock skew. `AUTO-M5-EXIT` rejects a
missing, stale, changed, wrong-revision, wrong-service, wrong-outcome,
value-mismatched, or Registry-mismatched witness before a completion claim.
The private browser proof retains only each current observation's opaque ID
beside its safe quota window facts. Python independently rebuilds the canonical
history material and digest; display text is not retained. The main browser
witness exposes that digest, the gate binds the quota-witness digest to the
pre-restart witness, and a distinct post-restart digest proves fresh
observation lineage. The final sanitized receipt records both digests.

`python3 tools/automation/run.py AUTO-M5-EXIT` becomes the sole milestone
completion command. It must bind one clean implementation revision to exact
provider compatibility, current real account/quota lineage, real process
evidence, built browser behavior, local engineering gates, and a create-once
sanitized receipt.

## Scope and ownership

### In scope

- A02 production code and tests under
  `backend/src/agentmonitor/adapters/providers/codex/**`.
- A02 provider extension contracts under
  `backend/src/agentmonitor/contracts/providers/codex/**` when the existing
  provider-neutral contracts cannot express the exact observed payload.
- Root-owned Codex composition, managed connection, scheduled collection,
  process selection, capacity alert delivery, API integration,
  UI rendering, browser verification, milestone automation, runbook,
  traceability, and sanitized evidence.
- Compatible reuse of existing Registry, Collection, Capacity, Runtime,
  Operations, API, and UI contracts. Shared modules change only when a Red
  proves a provider-neutral gap.
- Linux x86_64 and exact `codex-cli 0.160.0` for the initial admission.

### Out of scope

- OpenAI API usage, cost, billing, budgets, projects, API keys, and admin APIs;
  those remain `V1-M7` even though A02 owns their eventual adapter lane.
- Reading or modifying the default `CODEX_HOME`, copying its credentials, or
  logging out its account.
- `thread/list`, rollout JSONL, prompts, responses, reasoning, previews, tool
  activity, source content, Git content, arbitrary logs, or arbitrary process
  environments.
- Automatic account inference from the current login, process arguments,
  environment, terminal, or content.
- Reauthentication of a previously connected Codex account and its
  history-preservation proof. M5 supplies first managed-profile enrollment;
  `FR-AUTH-003` and `AC-LIVE-006` remain release-gate work.
- Process stop, restart, signal, input, routing, account switching, or session
  migration.
- Codex reset-credit consumption, credit-purchase/nudge actions, workspace
  mutations, account logout, and every app-server method outside the closed
  allowlist below.
- macOS acceptance; it remains visibly Blocked until a real Mac is available.
- `FR-STATE-003/004` and `AC-PROC-005` live stall/wait acceptance. The exact
  admitted Codex and Linux sources do not distinguish an owner/permission wait
  without reading content, so M5 reports state/certainty as unknown instead of
  guessing. A later separately admitted content-free source is required before
  the release gate can claim those criteria.

## Accepted discovery and exact source boundary

The sanitized
[Codex 0.160.0 discovery record](../../evidence/m5-codex-0.160.0-discovery.md)
is the evidence basis for this increment. Official OpenAI documentation and the
installed version-specific generated schema establish this closed allowlist:

| Operation | Exact use | Side effect and bound |
|---|---|---|
| `codex --version` | installation/version admission | one local read, 3-second deadline, 128-byte output cap |
| `codex login` | owner-started official authentication | AgentMonitor-managed `CODEX_HOME` only; owner completes browser/MFA; ten-minute deadline |
| `codex app-server --listen stdio://` | private per-operation JSONL transport after official managed login | selected managed root only; one child, minimal environment, no shell, bounded lines, deadline, terminated after response; provider runtime/auth maintenance may write only there |
| `initialize` / `initialized` | required protocol handshake | client identifies as AgentMonitor; no experimental API capability opt-in |
| `account/read` | identity and auth category | `refreshToken=false`; Codex can still perform automatic auth maintenance; allow account type, email, plan type, required-auth flag, and `workspaceRouting.chatgptAccountId` solely as ephemeral fingerprint input |
| `account/rateLimits/read` | native Codex subscription windows | Codex can perform automatic auth maintenance; `excludeResetCreditDetails=true`, `supportsLunaReserve=false`; allow rate-window and availability fields plus `accountId` solely for same-profile comparison and one-way fingerprint input |

The app-server command is documented as experimental by OpenAI. The initial
manifest therefore binds it to exact CLI version `0.160.0`, records mechanism
stability as `experimental`, and fails closed for another version. It does not
enable experimental protocol methods or private/browser endpoints. A provider
upgrade requires a new schema digest and live admission before collection.

Authentication uses `cli_auth_credentials_store="file"` under the selected
managed root. Analytics and OpenTelemetry exporters are disabled for these
short-lived children and raw prompts are never enabled. AgentMonitor does not
read `auth.json` content; it checks only safe file metadata before launching
app-server. An absent, linked, public, nonregular, or unbounded credential
store fails before provider startup. Codex owns creation, automatic refresh,
and use of that credential after the owner completes official login. The
manifest classifies identity, authentication-health, and quota queries as
`managed_profile_write`; installation discovery alone is `read_only`.

## Contract and data impact

- Provider: add exact `codex-adapter.v1` manifest/source/parser metadata and a
  closed versioned Codex subscription response schema. App-server query sources
  declare the bounded managed-profile auth/runtime side effect. No raw JSON
  crosses A02. The compatible `CTR-PROV-002/004` V1 deadline ceiling is
  600,000 ms so the manifest and runtime can express the approved ten-minute
  owner-completed login; existing deadline values and meaning are unchanged.
- Registry: use existing provider-neutral account, managed-profile,
  subscription-resource, identity-fingerprint, monitoring, and organization
  contracts. Account names and organizations remain administrator CRUD data;
  no account address or account count is compiled into production code.
- Collection/capacity: use existing scheduling, fencing, single-attempt,
  idempotent commit, quota-window, current projection, history, health, and
  forecast contracts. Codex windows retain native limit IDs and primary/
  secondary roles. They remain `subscription_pool` resources and are never
  combined with OpenAI API billing.
- Runtime: extend the existing Linux exact-executable selector to Codex. Reuse
  the live-process and owner-association contracts; do not read provider thread
  content or add a provider-shaped process API. M5 preserves unknown state and
  certainty when safe metadata cannot prove activity or a wait.
- Alerting: reuse the existing provider-neutral capacity condition consumer and
  dashboard lifecycle. Prove that a real Codex capacity condition can open,
  deduplicate, display, acknowledge or snooze, and recover without
  provider-shaped alert code. Existing threshold precedence remains the
  accepted M4 contract; M5 does not claim `AC-ALERT-003` stale/auth condition
  coverage. Delivery traverses every Registry account page under one stable
  complete snapshot and rejects missing, repeated, archived, inactive, or
  revision-changing subject membership.
- API/UI: add the optional V1 wire field `source_revision` to the existing
  Operations version inventory. The running service emits its exact 40-hex Git
  revision only when startup observed the same HEAD before and after a clean
  tracked and untracked worktree check through the fixed local Git boundary;
  otherwise the field is explicitly unknown and the inventory is partial. The
  milestone browser must match the available value to the gate's clean
  revision. Regenerate OpenAPI/client through the canonical generator and pass
  compatibility checks. The Accounts view must make every Registry page
  reachable through visible generated-client controls. The authenticated
  service allows 45 seconds to drain a bounded 30-second app-server operation,
  its at-most-four-second owned-child termination, and local scheduling/SQLite
  cleanup before resources close.
- Database/migration: no new table is planned. Existing generic rows must be
  proven sufficient with real file-backed SQLite tests before deciding no
  migration is required.
- Configuration: no new public secret. Managed roots derive from opaque
  registry IDs below the selected AgentMonitor data root.
- Dependencies/licenses: none. Use the standard library and admitted existing
  stack only.

## Test-first sequence

| Step | Test/evidence ID | Expected Red | Minimal production change | Green/refactor proof |
|---|---|---|---|---|
| 1 | `M5-CDX-PURE-001..012`, `M5-CDX-INSTALL-001..004` | Codex package/manifest/version resolution absent | exact manifest, installation identity, closed schema and mapper | pure policy plus real installed executable/version suite |
| 2 | `M5-CDX-SOURCE-001..010` | managed-root app-server source absent | bounded JSONL client, pre-start authenticated-root metadata gate, identity and rate-limit parsing, sanitized typed failures | real empty root rejected with zero descendants plus owner-authenticated managed-root runs; no raw output retained |
| 3 | `M5-CDX-CONNECT-001..010`, `M5-CDX-REG-001..006` | Codex accounts cannot connect/enroll | provider-dispatched connection coordinator and M02 enrollment | real HTTP/browser login, expected identity match, wrong-account fail closed, default untouched |
| 4 | `M5-CDX-COL-001..012`, `M5-CDX-CAP-001..008` | no Codex schedule or capacity history | provider-neutral route plus Codex collector | real SQLite admission/commit/history and one genuine managed-account quota read |
| 5 | `M5-CDX-RUN-001..008` | Linux selector rejects Codex | exact executable selector and Codex process composition | five to six real same-user PID/start/executable observations; unresolved identity and unavailable state evidence remain visibly unresolved/unknown |
| 6 | `M5-CDX-ALERT-001..006`, `M5-CDX-API-001..008`, `M5-CDX-UI-001..012` | service/browser expose no usable Codex vertical or alert lifecycle | composition, provider-neutral capacity alert delivery, health, presentation and generated artifacts if required | real server/database, genuine Codex capacity condition lifecycle, generated client, production build and shared Chrome browser |
| 7 | `M5-SVC-ACT-001..012` | the working persistent service runs from an extracted tree, so Operations cannot prove its Git revision and the M5 prerequisites cannot bind to it | register and implement the bounded `AUTO-M5-SERVICE-ACTIVATE` transition below | real user-service transition from the pinned trusted rollback runtime to the clean M5 checkout, exact source-revision/API/browser proof, and automatic restoration of the trusted runtime on every failed activation |
| 8 | `M5-CDX-GATE-001..014` | no fail-closed milestone command | register and implement `AUTO-M5-EXIT` | exact-revision four-account/process/browser/local-gate receipt with zero skips |

Each behavior records a meaningful Red before production Green. Pure tests may
construct only closed domain values. Filesystem, subprocess, SQLite, HTTP,
browser, Linux, and provider claims use their real boundaries and production
code. Provider unavailability is Blocked, never simulated.

## Security, privacy, operations, and license impact

- Provider credentials remain Codex-managed in owner-only managed roots.
  AgentMonitor accepts no credential, code, cookie, or secret value.
- Only the owner can initiate login through the existing cookie/CSRF/
  `write:reauth` flow. Status reads and service startup never start login or
  query an empty profile. Scheduled authenticated queries can invoke only
  Codex's official automatic auth maintenance inside that managed root.
- Identity email is transient allowlisted provider data used for owner-visible
  verification. Persistence retains the approved fingerprint linkage, not
  credential material or raw provider payloads.
- JSONL is bounded and parsed at source. Unknown keys are ignored only after
  the entire object shape and required closed fields pass validation; errors
  expose stable codes, never provider text.
- Every child uses an absolute verified executable, argument vector, minimal
  environment, private cwd/root, null stderr, output/line limits, one attempt,
  explicit timeout, and owned-child termination only.
- Linux observation reads only `/proc/<pid>/stat`, exact executable identity,
  cwd for the existing live path view, boot scope, and PID namespace. No argv,
  environment, memory, file contents, or terminal access.
- The dashboard service may be restarted by the milestone gate; Codex agents
  are never restarted or controlled.
- No new dependency, lockfile, SBOM, notice, or license impact.

## Documentation changes

- Create `docs/adapters/codex.md` and M5 Red/Green/live evidence.
- Update the operations runbook for managed Codex connection, monitoring,
  disable/rollback, version drift, and incident handling.
- Update module pages, README, roadmap, traceability/status overlay, and M5
  acceptance records only as their evidence becomes true.
- Preserve the synchronized Draft A02 plan as historical full-lane planning;
  this focused plan owns the current M5 implementation authority.

## Owner-directed Overview provider filter addendum — 2026-10-11

The owner's direction to separate Claude and Codex accounts on Overview
approves this bounded P02 increment within `M5-CDX-UI-001..012`. It contributes
to `FR-UI-001/002/003/004/007` and `AC-UI-002/003/004/005`. The UI consumes the
existing `provider_key` in `CTR-REG-002` through compatible `CTR-API-001` V1 and
`CTR-UI-001` V1 behavior; no API, OpenAPI, generated client, persistence,
provider adapter, configuration, dependency, migration, or ADR change is
authorized or expected.

Overview derives its provider choices from the real account page already
returned by the API. A compact labeled Provider control initially selects all
providers and lets the administrator show Claude only, Codex only, or all
loaded providers together. Provider and organization filters compose before
identity grouping and the existing quota sort. Provider selection remains
while manual and 30-second reads refresh the open page, uses no browser
storage, performs no mutation, and displays an explicit empty result. If the
selected provider disappears from a later real Registry page, selection
returns to All providers so the user retains an actionable view. Account
names, provider keys, organizations, and telemetry remain dynamic; no account
or quota value is compiled into production code.

Implementation begins with a separate authenticated mixed-provider built-
browser Red. The Green must prove Claude-only, Codex-only, all-provider reset,
keyboard use, composition with organization filtering, refresh retention,
accurate filtered counts, and zero API mutations against the real service.
The focused fail-closed browser command is also consumed by the M5 completion
path. A bounded first API page remains visibly bounded by the existing
`has_more` notice and cannot be described as a complete fleet query.

## Approved exact-revision service activation addendum — 2026-10-16

The active owner objective to finish M5 with the SDLC and runbook approves this
bounded PLAN-INT operations increment before its production implementation.
It closes one prerequisite gap in the already approved M5 completion design:
the working persistent dashboard is served from an extracted runtime whose
Operations inventory truthfully reports `source_revision` as unknown. The M5
owner, quota, and alert prerequisites require an already running service whose
process identity and reported source revision both match the clean checkout
that will execute `AUTO-M5-EXIT`.

`AUTO-M5-SERVICE-ACTIVATE` is the sole approved transition for that gap. It is
a prerequisite coordinator, not an M5 completion command and not a general
install, upgrade, release, or rollback implementation. `AUTO-M5-EXIT` remains
the sole V1-M5 completion command. The general `AUTO-DEPLOY` lifecycle remains
Blocked under PLAN-DEP.

### Deployment ownership and contract impact

PLAN-DEP/D01 normally owns native unit materialization, activation, installed
service lifecycle, deployment journals, and rollback. The active owner's M5
objective grants PLAN-INT one explicit exception to that exclusive ownership:
the root-owned M5 automation and tests may inspect and atomically retarget the
already installed fixed `agentmonitor-dashboard.service` only for the exact
candidate/trusted-runtime transition in this addendum. The corresponding D01
Draft plan cross-references and accepts this exception while retaining its
Draft status and every broader prohibition.

This exception does not implement or approve installation, repair, upgrade,
uninstall, release-bundle activation, database activation, generic service
control, arbitrary unit selection, installed-layout policy, or `AUTO-DEPLOY`.
It grants no write ownership under D01's proposed packaging/deployment paths
and cannot be reused by another milestone or target. The fixed service name,
trusted runtime, candidate checkout, four permitted unit differences, private
journal, real rollback exercise, and final M5 evidence sequence are closed
inputs.

No public contract changes. `CTR-DEP-001` remains proposed, produced solely by
PLAN-DEP/D01, and unchanged; the M5 coordinator neither publishes nor claims a
native-service lifecycle receipt through it. Existing API, Operations,
Registry, configuration, database, provider, UI, event, and integration
contract versions retain their meanings. There is no migration, public schema,
configuration-key, dependency, license, generated-client, or ADR impact. The
implementation is an internal root integration routine over the already
installed fixed user unit, and its private journal is not a domain event or a
public deployment artifact.

### Selected and rollback runtimes

- The candidate is the absolute Git worktree from which the command runs. It
  must be detached at one committed 40-hex `HEAD`, outside temporary
  directories, with no symbolic branch reference and a clean tracked and
  untracked status. The command revalidates the same resolved worktree,
  detached state, clean status and unchanged `HEAD` before preparation,
  immediately before service mutation, and after readiness. Its backend Python
  entry point, frontend build, and service process working directory remain
  that one exact revision.
- The currently working extracted runtime at revision
  `77a3bad12a096a81587b94b8981ceee812b6445b` is the only trusted rollback
  runtime for this transition. The coordinator must verify the existing user
  service selects that runtime and a live same-user process before changing
  service state. It never modifies, replaces, moves, or deletes that runtime.
- The existing owner data root, `service.env`, database, loopback/LAN bind
  arguments, provider-tool `PATH`, cache location, user-service security
  settings, and restart policy are preserved exactly. Only the candidate
  `WorkingDirectory`, `PYTHONPATH`, backend Python path, and `TimeoutStopSec`
  may differ in the candidate unit. The trusted unit's 30-second stop timeout
  is corrected to 45 seconds for the candidate so its service manager allows
  the already approved 30-second provider operation, at-most-four-second owned
  child termination, and local scheduling/SQLite cleanup to drain. Rollback
  restores the trusted unit's exact original 30-second value. Secret values
  are neither read into evidence nor printed.
- The candidate worktree must be owner-controlled and stable across restart.
  A linked, public, unresolved, attached, dirty, moving, or differently revised
  root blocks before the trusted service is stopped.

### Atomic transition and rollback

Before stopping the trusted service, the coordinator builds the production
frontend and completes every candidate-only check that can run without changing
the service. It then validates and privately journals the exact current unit
bytes, file identity and mode, trusted process PID/start identity, trusted
runtime revision, candidate revision, and digests of the preserved launch
fields. The journal and rollback unit copy are owner-only, bounded, fsynced,
no-symlink files below the existing AgentMonitor data root. They contain no
credential, cookie, account identity, provider payload, prompt, response, or
source content.

The unit update uses a same-directory temporary file, owner-only permissions,
file and directory fsync, atomic replacement, and `systemctl --user
daemon-reload`. The coordinator starts the candidate with the preserved
configuration and waits for one bounded readiness interval. It accepts success
only when all of these remain true at the same observation boundary:

1. systemd reports one active candidate process owned by the current user;
2. `/proc` independently confirms its PID/start identity, exact worktree cwd,
   and the candidate checkout's backend Python launch path;
3. the real loopback HTTP service is ready and the authenticated built browser
   remains usable;
4. the versioned Operations inventory reports an available 40-hex
   `source_revision` equal to the candidate's unchanged clean `HEAD`;
5. the existing database and complete public Registry digest are unchanged by
   the transition itself; and
6. the trusted rollback runtime and private rollback material remain present
   and unchanged.

Any validation, stop, unit-write, reload, start, readiness, browser, revision,
Registry, or final recheck failure triggers rollback before the command
returns. Rollback stops only the candidate process it owns, atomically restores
the exact prior unit, reloads the user manager, restarts the pinned trusted
runtime, and verifies its independent process identity and real HTTP readiness.
The command reports Blocked or Failed only after the trusted runtime is proven
restored. If restoration itself cannot be proven, it returns the distinct
sanitized failure `m5_service_activation_rollback_failed` and preserves the
journal and both runtime trees for diagnosis. An interrupted journal is never
discarded or overwritten; the next invocation must first reconcile it to a
proven trusted or proven candidate state.

After success, the candidate user service remains selected and the command
reports its non-secret PID for `AGENTMONITOR_M5_SERVICE_PID`. Automation may
read that PID directly from the user manager; the owner is never asked to copy
or transcribe process identifiers. Fresh M5 prerequisites are collected only
after the candidate is proven active. Stale create-once prerequisites are then
preserved through `AUTO-M5-ARCHIVE-PREREQUISITES` in the existing documented
order.

The detached checkout becomes immutable operational input for the rest of the
M5 run. `AUTO-M5-ARCHIVE-PREREQUISITES`, `AUTO-M5-OWNER-OUTCOMES`,
`AUTO-M5-ALERT-WITNESS`, `AUTO-M5-QUOTA-WITNESS`, and `AUTO-M5-EXIT` each
revalidate the same resolved worktree, detached state, clean tracked and
untracked status, unchanged committed `HEAD`, candidate process identity, and
matching Operations source revision before using existing evidence and again
before writing their own create-once artifact. `AUTO-M5-EXIT` repeats the check
before restart, after its technical/browser/local lanes, and immediately before
the final receipt. A checkout, branch, revision, status, service, or Operations
change blocks without writing a success artifact. Evidence collected before a
new detached revision or service generation is stale and follows the existing
archive-and-recollect procedure.

The existing `AUTO-GIT-PREFLIGHT` branch requirement remains unchanged for
ordinary commit, push, and release use. While running its own local-gate lane,
`AUTO-M5-EXIT` alone supplies the exact internal selector
`AGENTMONITOR_M5_DETACHED_GIT_PREFLIGHT=1`. That selector is valid only for the
commit preflight and replaces the ordinary branch assertion with proof that the
exact checkout root has a detached `HEAD`, one stable lowercase 40-hex commit,
and empty tracked and untracked status. An attached checkout, dirty checkout,
moving or malformed revision, another selector value, or use with push or
release blocks. Operators do not set this selector for prerequisite commands
or general Git work.

The coordinator itself never invokes Claude or Codex, reads or copies a
provider profile, starts authentication, changes monitoring, alters Registry
records, acknowledges alerts, changes quota history, or controls an agent
process. Normal scheduled work performed by the selected AgentMonitor service
continues under the existing managed-profile and collection contracts. The
transition adds no public API or contract field, database table or migration,
configuration setting, dependency, license, or ADR.

### Test-first and live proof

Production work is limited to the root-owned automation implementation,
dispatcher/catalog registration, and corresponding documentation. Before that
code, a Red must prove the absent coordinator cannot produce the required
revision-bound running service. The Green suite must cover closed unit parsing,
path and ownership rejection, attached/dirty/changing Git rejection, exact
launch-field preservation, atomic journal and unit writes, process-race
detection, readiness and revision mismatch, boundary-by-boundary detached HEAD
revalidation, idempotent interruption recovery, and fail-closed rollback
policy. Pure policy tests may construct only closed values; filesystem, Git,
process, systemd, HTTP, browser, and service claims use their real boundaries.
The M5 Git-preflight Green additionally uses real attached and detached Git
worktrees to prove that the internal selector accepts only the clean stable
detached commit while the ordinary branch requirement and push/release rules
remain intact.

The live Green uses the real AgentMonitor user service and data root on this
workstation. It must show the trusted `77a3bad12a096a81587b94b8981ceee812b6445b`
runtime healthy before transition, the candidate healthy with the exact clean
source revision after transition, unchanged public Registry state, and the
trusted service automatically restored after one real post-stop activation
failure. A final successful activation then leaves the exact candidate running
for fresh M5 prerequisites. A simulated service manager, fake HTTP server,
placeholder revision, manually edited receipt, or untested rollback path is not
credited.

## Approved corrective activation rollover addendum — 2026-10-16

The active owner objective to finish M5, together with the explicit authority
for all system actions needed to do so, approves this bounded correction before
its production implementation. The first real activation completed at clean
revision `6bfa69dc13cc9e1ded9c6baa6e803cb99bc8c20b`. The immediately following
canonical prerequisite archive then exposed two fail-closed gaps: a fresh
detached worktree had no automated owner-only final-receipt directory, and the
final M5 receipt path was not revalidated against its retained inode after the
post-write service observation. Those findings invalidate M5 completion at the
first candidate revision; they do not invalidate its successful rollback drill
or authorize manual evidence deletion, unit editing, or a general upgrade.

The existing `AUTO-M5-SERVICE-ACTIVATE` command gains one corrective rollover
mode. It is available only when the fixed service is the exact clean detached
`6bfa69dc13cc9e1ded9c6baa6e803cb99bc8c20b` candidate and the completed private
activation receipt, journal, rollback unit, current systemd generation,
authenticated Operations revision, pinned rollback runtime, database identity,
and complete public Registry digest all validate together. Under the existing
exclusive transition guard it restores and proves the pinned trusted
`77a3bad12a096a81587b94b8981ceee812b6445b` runtime using the recorded rollback
material. It then atomically renames the complete transition directory, without
replacement and on the same filesystem, into an owner-only corrective archive
whose name binds the prior revision and receipt digest; the directory and both
parents are fsynced. It creates a fresh owner-only transition directory and
returns a typed rerun-required result carrying no private data. Automation
rereads the trusted systemd PID and invokes the same canonical activation
command again for the new clean detached candidate. It never deletes, copies,
edits, hard-links, or overwrites the prior activation artifacts.

An interruption before proven rollback leaves the original transition set in
place. An interruption after proven rollback but before the directory rename is
reconciled from the same exact receipt and trusted service. The directory rename
is the archive commit point: after it, a retry sees either the complete archived
directory plus an absent fresh root, or the complete archive plus a valid fresh
root. A target collision, cross-filesystem move, unsafe parent, changed inode,
partial archive, mismatched service, dirty or moving checkout, changed Registry
or database, or unprovable trusted runtime blocks without starting the new
candidate. Rollback failure remains the distinct activation rollback failure.
The old candidate worktree stays untouched and verifiable throughout recovery.

The completion-lock acquisition also becomes the canonical first-use setup for
its ignored `.agentmonitor-local` parent. It may create only that exact missing
directory with mode `0700`, using one atomic `mkdir`; `EEXIST` continues through
the existing owner, mode, resolved-path, descriptor-identity, and no-symlink
checks. Any other error or unsafe existing object blocks. `AUTO-M5-EXIT` adds one
final descriptor-relative proof that its canonical receipt entry is still the
same owner-owned regular `0600`, single-link retained inode after the post-write
service observation and both final lock validations. A mismatch enters the
existing exact-inode cleanup and cannot produce a Passed result.

This correction changes no public API, event, database, configuration,
provider, UI, generated-client, dependency, license, or migration contract. It
does not authorize another prior revision, arbitrary service, general upgrade,
artifact garbage collection, `AUTO-DEPLOY`, or reuse outside this M5 recovery.
Red/Green evidence must use real directories, descriptors, processes, Git,
systemd, HTTP, and the authenticated shared browser at every external boundary.
The live proof must show `6bfa69d` restored to the pinned runtime, the complete
old transition directory preserved, and the corrected exact revision completing
the original rollback drill before any M5 prerequisite is recollected.

## Approved complete-scope window lifecycle correction and second exact rollover — 2026-10-16

**Status: Owner-approved on 2026-10-16. Production implementation and live
verification are authorized only within the exact correction and rollover
bounds below. Approval is not a completion claim; approved version 1.4.0 and
its retained evidence remain unchanged.**

### Current real-system evidence

The live real-system scenario
`backend/tests/integration/capacity/test_codex_capacity_history.py::test_running_service_persisted_native_codex_windows_and_history`
failed against the running exact `063445154bca0bf5ec43db94ba57c17fd193fd99`
service. The latest successful complete Codex collection contained one current
native window, while the public API retained two current windows. The current
window `collection_run_id` set therefore contained exactly one extra stale
prior run ID. `AUTO-M5-QUOTA-WITNESS` would correctly block this state as
`m5_quota_current_lineage_required`.

This is a missing implementation of the already specified `FR-QUOTA-001` /
`M05-PURE-005` rule in PLAN-M05: only an approved complete collection can prove
that a previously current native window disappeared, and such a window becomes
`not_observed_currently`; a partial or failed collection cannot do so. The
finding changes no provider fact, requirement meaning, or public contract.

### Approved behavior and ownership

M05 remains the sole owner of capacity window definitions, lifecycle, current
and health projections, immutable history, and the `capacity_*` tables.
PLAN-INT owns the focused integration, completion automation, and the bounded
PLAN-DEP/D01 service transition. Implementation authority is limited to M05
domain/persistence code and tests, the root-owned M5 automation and tests, and
the corresponding M05/M5 documentation and evidence.

For an accepted `complete_scope` quota snapshot, M05 compares the exact set of
incoming native window keys with current-projection keys whose definitions are
`active` or `not_observed_currently`, only inside the same provider,
installation, account, resource, capability, and identity-scheme scope. It
reuses M05's existing per-key semantic observation precedence rather than
introducing one batch-wide timestamp comparator. An active current key absent
from the incoming set changes to
`not_observed_currently` only when the complete snapshot's semantic time is
strictly newer than that key's current observation. Equal-time conflict,
out-of-order input, `partial_scope`, failed collection, changed scope, or an
unproven identity scheme cannot change an omitted key's lifecycle.

A later strictly newer complete snapshot that still omits an already
`not_observed_currently` key advances only that definition's lifecycle
watermark. This prevents a delayed presence observation between the two
absence times from reactivating the key. It creates no quota observation or
history row, and `retired` definitions are excluded.

The lifecycle decision and persistence update occur in the existing M05 commit
transaction before health, current condition, event, and receipt derivation.
Every current-window, current-health, current-forecast refresh, capacity-alert
condition, account, API, and dashboard read excludes definitions whose
lifecycle is not `active`. Immutable observations, measures, provenance,
history series, commit receipts, and event history remain available and
unchanged. If the exact native key is later present in a newer accepted
snapshot, its matching definition returns to `active` before it can become
current; a semantic definition change still follows the existing definition
version policy. No manual database repair or fabricated replacement row is
permitted. The owner's existing database converges only through a fresh genuine
complete provider collection processed by the corrected production path.

This behavior uses the existing `complete_scope`/`partial_scope` contract and
the existing `active`/`not_observed_currently` database lifecycle values. It
adds no public API, event, provider, configuration, database schema, migration,
generated-client, dependency, license, or ADR change. A contract-meaning or
schema change discovered during Red/Green stops implementation and returns to
review.

### Test-first correction sequence

| Step | Test/evidence ID | Expected Red | Minimal Green | Required proof |
|---|---|---|---|---|
| 1 | `M05-PURE-005` | complete-scope set difference policy is absent; partial omission or a repeated newer absence could leave an unsafe lifecycle watermark | one pure provider-neutral lifecycle decision over closed window keys, lifecycle, and completeness | constructed side-effect-free set cases prove exact complete omission, repeated-absence watermark advancement, stale and newer reappearance, partial no-op, retired no-op, scope isolation, strict-newer ordering, and equal-time conflict |
| 2 | `M5-CDX-CAP-002..008` live regression | latest genuine complete run has one window while current reads retain one stale prior-run window | apply lifecycle and current-read filtering inside the existing atomic M05 commit path | the named real-system test passes after a fresh genuine complete Codex collection; current API windows all bind the latest run and immutable prior-window history remains queryable |
| 3 | `M5-CDX-ALERT-001..006`, `M5-CDX-API-001..008`, `M5-CDX-UI-001..012` | derived health, alert condition, API, or built dashboard can still consume the inactive window | reuse the corrected M05 current set throughout existing provider-neutral readers | real SQLite, production HTTP and built shared Chrome agree on the active current set; complete Registry digest and mutation count remain unchanged |
| 4 | `M5-SVC-ACT-013..020` | activation accepts only the first corrective archive and cannot preserve a second completed transition | extend the same canonical command by the one revision-pinned rollover below | real filesystem/Git/systemd/HTTP/browser tests prove two fixed exact singleton archive namespaces, interruption recovery, trusted rollback, corrected activation and no replacement |
| 5 | `M5-CDX-GATE-001..014` | quota witness blocks `m5_quota_current_lineage_required` | no gate relaxation; recollect fresh revision/service-bound prerequisites | `AUTO-M5-QUOTA-WITNESS` and then `AUTO-M5-EXIT` pass on the corrected clean exact revision with zero skips |

Pure tests may construct only the closed lifecycle inputs. SQLite, provider,
HTTP, browser, Git, filesystem, process, and systemd claims use their real
production boundaries. A naturally unavailable partial or reappearance case
remains Blocked at the live boundary; the pure policy does not turn it into a
live pass. The existing real failure is retained as Red evidence, and Green is
not claimed until a newer genuine complete collection exercises the corrected
service.

### Approved one-time second service rollover

After the correction is implemented through Red/Green/refactor, reviewed, and
committed as one clean detached candidate, the existing
`AUTO-M5-SERVICE-ACTIVATE` command may perform exactly one second corrective
rollover. It is available only when the running service and complete canonical
transition set both bind clean detached revision
`063445154bca0bf5ec43db94ba57c17fd193fd99`, the pinned trusted rollback remains
`77a3bad12a096a81587b94b8981ceee812b6445b`, and the already completed first
`6bfa69dc13cc9e1ded9c6baa6e803cb99bc8c20b` corrective archive validates before
every mutation boundary.

The new candidate must be distinct from the pinned trusted revision and both
named completed corrective revisions. The command rejects any of those three
reserved revisions before restoring the trusted service, moving an archive,
or writing transition state. This preserves the sole permitted path into one
new reviewed correction revision and prevents a prepared transition from being
stranded on an ineligible candidate.

Under the same exclusive transition guard, the command retains descriptors,
inodes, modes, link counts and digests for the existing first archive and the
current transition artifacts; restores and proves the pinned trusted service
using the current rollback unit; then moves the complete `0634451` transition
directory by Linux same-filesystem atomic no-replace rename into the fixed
owner-only singleton namespace
`m5-service-activation-corrective-archive-0634451`. The existing
`m5-service-activation-corrective-archive` parent remains an unchanged exact
singleton for `6bfa69d`; the second parent is an exact singleton for `0634451`.
Both retained directories and both parents are fsynced and revalidated. The
command creates a fresh private transition root and returns the existing typed
rerun-required result. Its next invocation validates each archive through its
own revision-pinned singleton selector before activating only the new clean
detached correction commit, including the already approved real rollback drill
and final candidate restoration.

An interruption before proven trusted rollback leaves the canonical transition
set in place. An interruption after trusted rollback but before the second
archive commit reconciles from that same set. After the no-replace rename, a
retry first validates both exact singleton archives. If interruption occurred
before fresh-root creation, only the absent canonical root is accepted and the
existing guarded exact-root creation must produce the empty `fresh` state. An
existing owner-only canonical root must be in one exact recovery state: `fresh`
with no entries, `journal_only` with only the exact candidate-bound journal,
`rollback_only` with only the exact trusted rollback unit, or `prepared` with
exactly the valid journal and rollback unit bound to the candidate and trusted
material. Any
other preexisting archive entry, root entry, count, state, collision, partial
set, cross-filesystem move, changed first-archive inode or digest, changed
current evidence, dirty/moving checkout, Registry/database drift, unprovable
trusted runtime, or service/browser revision mismatch blocks without cleanup
or replacement and before a new candidate starts. Neither archive may be
deleted, edited, copied, hard-linked, replaced, or garbage-collected.

The second rollover extends only the existing private M5 prerequisite
transition. It grants no general install, upgrade, repair, rollback, unit edit,
provider/profile action, Registry mutation, process control, `AUTO-DEPLOY`, or
PLAN-DEP approval. The current owner-outcome and any later prerequisites bound
to revision `0634451` become stale after the service identity changes; they are
preserved through `AUTO-M5-ARCHIVE-PREREQUISITES` and recollected through their
canonical owner/live routines. No file is manually deleted or rebound.

### Approved authority and completion boundary

On 2026-10-16 the owner explicitly approved both parts of this addendum: the
M05 complete-scope lifecycle correction and the one exact second rollover from
`063445154bca0bf5ec43db94ba57c17fd193fd99`. Production implementation and the
bounded live transition may proceed only through the test-first sequence,
review, clean detached candidate, and fail-closed preconditions above. The
approval does not itself change production, service, or evidence state.
Completion still requires the unchanged canonical `AUTO-M5-EXIT` result and
separate owner acceptance; plan approval is never a completion claim.

## Stop conditions

Stop the affected increment if the installed version or generated schema
changes; app-server emits unbounded or content-bearing data on an allowlisted
method; the default Codex profile could be read or written; identity differs
from the administrator-selected account; a secret/content value reaches logs,
database, API, UI, tests, evidence, or chat; a private endpoint/browser cookie
is needed; a new dependency or breaking contract is required; a migration
could destroy data; or live work would interrupt a running agent.

An owner browser login is an expected milestone checkpoint. The owner keeps
passwords, MFA, and codes in Codex's official page. The implementation and all
noninteractive verification continue before and after that checkpoint without
requesting broader permission already granted by the active objective.

## Completion gate

M5 is incomplete until `AUTO-M5-EXIT` passes on one clean exact revision and
writes its private create-once receipt. The gate must prove:

1. exact `codex-cli 0.160.0` installation and admitted schema/mapping digests;
2. four selected real Codex account outcomes with distinct verified identities,
   or explicit owner-unavailable rows permitted by `AC-LIVE-002`, loaded from
   the fixed owner-only outcome file and bound by digest/count only;
3. current genuine quota plus matching history lineage for every available
   monitored account, reconciled through `AUTO-M5-QUOTA-WITNESS` with Codex's
   official `/usage` view at exact whole percentage, displayed reset precision,
   and at most 300 seconds of observation/collection skew;
4. five to six representative real Codex processes outside AgentMonitor's
   managed-profile subtree, exact independently reread PID/start/executable
   identity, safe hierarchy/location presentation, and truthful unresolved or
   owner-confirmed account association with unknown state retained when no
   safe state evidence exists;
5. a genuine Codex capacity condition starts a fresh occurrence through
   `opened` or `reopened` for a retained recovered fingerprint, then traverses
   the existing alert lifecycle through dedupe, browser presentation, an owner
   action, and source-proven recovery without deleting retained history;
6. real file-backed SQLite, production HTTP, generated client, built Chrome,
   provider capability/health/failure isolation, and zero registry mutation by
   verification; a real syscall trace of the production managed-profile
   identity and quota calls must prove zero default-profile access or writes
   and confine declared provider-controlled auth/runtime writes to the selected
   managed profile;
7. the service worktree remains detached at the exact committed revision, with
   clean tracked and untracked state revalidated at every prerequisite/gate
   boundary, and the running service's Operations version inventory reports
   that revision rather than trusting the launch working directory or an
   earlier checkout observation;
8. required local technical, build, planning, quality, mutation,
   documentation, and Git-preflight lanes with zero skipped tests; and
9. sanitized evidence containing no account identity, provider/profile path,
   process ID, credential, provider payload, prompt, response, source content,
   or arbitrary environment value.

For milestone closure, every selected account row is either verified and
current or carries an owner-recorded unavailable outcome; unresolved is not a
permitted substitute. Every other item in the numbered list above is required
for `AUTO-M5-EXIT`. Broader cross-provider release acceptance remains a V1-M8
contribution and is not credited by this gate.

The gate is finite and noninteractive. Owner authentication, owner outcomes,
authoritative `/usage` reconciliation, and the capacity-alert opening, action,
and recovery witness for the fresh occurrence happen beforehand through the
running application
and write bounded owner-only prerequisite receipts below the same data root.
`AUTO-M5-EXIT` validates their closed schemas, permissions, source lineage,
timestamps, exact selected service/revision, and immutable digests. It binds
the 15-minute quota witness to both the pre-restart and fresh post-restart
built-browser values and rereads the unchanged witness and complete Registry
graph against the actual completion time before writing its final receipt.
Missing, expired, mismatched, or changed receipts are Blocked and never trigger
provider login or wait for a natural condition inside the gate.

The owner reviews that exact result before formal M5 acceptance. M5 acceptance
does not accept M6, M7, M8, hosted release publication, macOS, OpenAI API
billing, or the complete V1 release.
