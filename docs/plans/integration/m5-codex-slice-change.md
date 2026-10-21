# Change plan: executable V1-M5 Codex slice

- Status: **Approved 1.10.0 for one managed-profile effective-containment
  correction folded into the approved but not-yet-run fifth rollover**.
- Plan version: `1.10.0`; owner approval: 2026-10-21.
- Safety correction: exact-version review proved that authenticated app-server
  queries may perform Codex's automatic credential refresh. The approved
  managed-auth lifecycle therefore classifies those queries as
  `managed_profile_write`, and an empty/uninitialized managed root is rejected
  before any app-server child starts.
- Owner: `PLAN-INT`, with A02 provider behavior and the exact PLAN-DEP/D01
  service-activation exception owned under this bounded change. Approved 1.8.0
  is the sole bounded exception to PLAN-P02's Draft implementation prohibition;
  PLAN-P02 remains semantic owner and the root integration agent acts as the
  P02 shell steward for only the enumerated files, with no concurrent writer.
- Parent plans:
  [V1-M5 milestone](../../superpowers/plans/2026-09-19-agentmonitor-v1-m5-codex-slice.md)
  and [A02 adapter](../adapters/codex/plan-v1.md).
- Authority: the active owner objective, **fully implement M5 with our SDLC and
  runbook**, approved version 1.4.0 and its first corrective rollover. The
  owner's explicit 2026-10-16 approvals extend the same focused A02 and
  PLAN-DEP/D01 exception only by the exact complete-scope lifecycle correction,
  the second rollover from `063445154bca0bf5ec43db94ba57c17fd193fd99`,
  the paginated live-history verification, and the third rollover from
  `6d6e1aa9d9b64d50e3f83d0f1686e6cff04b7c17` specified below. The owner's
  explicit 2026-10-20 approval adds only the browser-proof termination
  correction and fourth rollover from
  `e066d7e1ba0124f0454c07002ea7b2ad0817d6b9` specified below. The owner's
  explicit 2026-10-20 approval of version 1.8.0 adds only the bounded
  P02 correction below and supersedes only 1.7.0's candidate-content
  restriction. The owner's explicit 2026-10-21 approval of version 1.9.0 adds
  only the quota-witness correction and fifth rollover specified below. The
  owner's explicit 2026-10-21 approval of version 1.10.0 adds only the
  managed-profile effective-containment correction specified below. All
  remaining A02, OpenAI API, PLAN-DEP/D01, and
  `AUTO-DEPLOY` lanes stay Draft or Blocked as already recorded.
- Stories: `ST-CDX-001..005`.
- Requirements: `FR-ACC-001/004..006`, `FR-AUTH-001/002/004..006`,
  `FR-QUOTA-001..006`, `FR-COL-003..008`, `FR-HIST-001/002`,
  `FR-DISC-001/003/004/006/008`, `FR-STATE-001/002`, `FR-SAFE-002`,
  `FR-ALERT-002..006`, `FR-UI-001..006`, `FR-IAM-001/003`,
  `NFR-API-001/002`,
  `NFR-TEST-001/002`,
  `NFR-SEC-001`, `NFR-PRIV-001/002`, `NFR-RES-001`, `NFR-OBS-001`,
  `NFR-COMP-001`, and `NFR-DOC-001`.
- Acceptance contributions: `AC-LIVE-002/004/005/007`,
  `AC-UI-002/005/006`, `AC-PROC-001..004`, `AC-HIST-001`,
  `AC-ALERT-002`, `AC-OPS-003/006`, and `AC-TEST-001..006` within
  M5's Codex boundary; approved 1.8.0 also contributes bounded
  `AC-UI-001/003/004/005` and `AC-V1-005/007` evidence.
- Contracts: compatible V1 use of `CTR-PROV-001..008`, `CTR-REG-001/002/004/
  005/006/009/010`, `CTR-COL-002/004/006/007`, `CTR-CAP-001/003/004/007`,
  `CTR-RUN-001/002/003/006/007`, `CTR-PLAT-001`, `CTR-OPS-004/006`,
  `CTR-ALERT-001..005`, `CTR-CAP-008/009`, `CTR-EVT-001`, `CTR-API-001`,
  `CTR-API-002`, `CTR-IAM-003/004/005`, and `CTR-UI-001`.

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
percentages and reset facts from each account's official Codex `/status` view;
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

The completed activation receipt retains the PID/start identity of the process
that originally proved activation. A later ordinary systemd or workstation
restart may produce a different PID/start identity for the same exact clean
completed revision without rewriting that immutable receipt. Before rollover,
the command independently validates the current same-user systemd process,
unit bytes, executable, working directory, source revision, authenticated
browser, Registry digest, database identity, journal, rollback unit, rollback
runtime, and receipt material. A changed process generation is accepted only
when all of those same-revision proofs agree; an unknown revision, unit, or
runtime still blocks before mutation.

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

## Approved paginated-history verification and third exact rollover — 2026-10-16

**Status: Owner-approved 1.6.0 on 2026-10-16. Production implementation and
the bounded live transition are authorized only within this exact correction
and rollover. Approval is not a completion claim; approved version 1.5.0 and
its retained evidence remain unchanged.**

### New real-system evidence

After the approved 1.5.0 correction was activated as exact revision
`6d6e1aa9d9b64d50e3f83d0f1686e6cff04b7c17`, three newer genuine complete
Codex collections succeeded. The named live regression proved that the public
current set now contains one window and that it binds only the newest run. Its
history assertion nevertheless failed because the test read only the first
200 rows of an ascending cursor-paginated 30-day history. The genuine account
had 1,606 retained rows over nine pages, and the newest run was correctly the
last row. A read-only traversal through the production `CTR-CAP-006` query
found all 1,606 unique observations, the exact current observation once, and
older immutable observations.

This is a verification defect, not a product, persistence, ordering, or
contract defect. `CTR-CAP-006` and PLAN-M05 require deterministic ascending
semantic-time and observation-ID ordering with bounded cursor pages. Changing
repository ordering, narrowing the range, deleting retained history, or
raising the 200-row page limit is prohibited.

### Approved test-only correction

The existing named live test may traverse the unchanged 30-day query through
at most 128 pages of 200 rows. Every `has_more` page must provide a new opaque
cursor, the terminal page must provide no cursor, and the combined result must
contain unique observation IDs in production order. The existing latest-run
current-window assertions then apply to the complete traversal, with an
additional assertion that at least one prior-run observation remains. This
changes no production module, public contract, API, schema, migration,
provider behavior, dependency, license, generated client, or ADR.

The existing Red is the live first-page failure at the newest-lineage
assertion. Green requires the same real service and database to pass after the
bounded traversal, while retaining all 1,606 observations. Synthetic history,
database cleanup, clock changes, altered ordering, and skipped live evidence
cannot satisfy this correction.

### Approved one-time third service rollover

Committing the test and evidence correction creates a new Git revision, while
`AUTO-M5-EXIT` requires the clean checkout, running Operations source
revision, and immutable activation receipt to agree exactly. No approved
command can rebind those facts: prerequisite archival does not change service
activation evidence, general deployment remains unauthorized, and manual
receipt editing or deletion is prohibited. Version 1.6.0 therefore authorizes
one exact third corrective rollover from completed clean detached revision
`6d6e1aa9d9b64d50e3f83d0f1686e6cff04b7c17` to one eventual reviewed clean
candidate containing the pagination test, this rollover implementation and
tests, synchronized controls, documentation, and evidence in one commit.

The command must use the same exclusive transition guard and preserve a closed
ordered chain for the completed `6bfa69d`, `0634451`, and `6d6e1aa` revisions.
It must retain the complete `6d6e1aa` transition directory by Linux
same-filesystem atomic no-replace rename into the fixed owner-only parent
`m5-service-activation-corrective-archive-6d6e1aa`, whose sole child is bound
to the full revision and activation-receipt digest. The new candidate must be
different from the pinned trusted revision and all three completed corrective
revisions. No archive is discovered generically or selected by recency.

Before any mutation, the command must validate the current `6d6e1aa` receipt,
journal, rollback unit, clean detached checkout, exact same-user systemd and
`/proc` process shape, Operations revision, authenticated browser, Registry
digest, database identity, and pinned rollback runtime. A later PID/start
generation is accepted only through the approved same-revision restart policy.
Descriptors retain each earlier archive parent, directory, and artifact;
owner, mode, link count, inode, and digest are revalidated before every
filesystem or service mutation. Empty, partial, multiple, collided,
cross-filesystem, changed, or unknown archive and transition states block
without cleanup or replacement.

After proving the trusted rollback service, the command fsyncs the source and
target parents around the no-replace move, creates one fresh owner-only
transition root, binds the eventual candidate in the journal, and returns the
existing typed rerun-required result. The second invocation revalidates all
three exact singleton archives and the exact prepared state before performing
the existing real rollback drill and activating only that candidate. A failed
or interrupted attempt preserves or restores the same evidence and service
guarantees already approved for 1.5.0.

Red/Green evidence extends the existing frozen activation nodes for exact
candidate/reserved-revision policy, atomic inode move, ordered three-archive
retry, partial/multiple/collision rejection, browser proof, and restarted
same-revision service handling. It must preserve the canonical story inventory
or explicitly rebind that inventory before live work. Required local proof is
the full activation suite, Ruff/format, strict mypy, diff, documentation,
planning, quality, build, test, mutation, and Git preflight gates. Live proof
requires stage one to return typed status 5 with the trusted service active,
stage two to activate the exact clean candidate, and HTTP, authenticated
browser, Registry, database, service, and receipt checks to agree. Every
prerequisite bound to `6d6e1aa` is then archived and recollected canonically.

This approval adds no general deployment, upgrade, repair, cleanup, provider
or profile operation, Registry or database mutation, agent control, or
`AUTO-DEPLOY` authority. Production implementation may proceed only through
the stated Red/Green/refactor, review, clean-candidate, and fail-closed live
preconditions.

## Approved alert browser-proof termination correction and fourth exact rollover — 2026-10-20

**Status: Owner-approved 1.7.0 on 2026-10-20. Production implementation and
the bounded live transition are authorized only within the exact correction
and one-time rollover below. Approval is not a completion claim; version 1.6.0
and its retained evidence remain unchanged.**

### New real-system Red

The current exact clean service revision
`e066d7e1ba0124f0454c07002ea7b2ad0817d6b9` has a fresh genuine Codex alert
lifecycle with opening, repeated-condition, owner-action, and recovery
lineage. During `AUTO-M5-ALERT-WITNESS`, the real built-browser child
`tools/ui/verify_m5_codex_alert_lifecycle.mjs` successfully emits exactly one
valid `agentmonitor.m5-alert-browser-proof.v2` JSON document, closes its
temporary page, and then remains alive because its Playwright CDP client is
still connected. The Python `_browser_proof` boundary reaches its 180-second
timeout, reports `m5_alert_witness_browser_unavailable`, and correctly writes
no alert witness.

This is a root-owned verification-process lifecycle defect. The alert,
history, API, UI, service-revision, browser presentation, zero-mutation, and
Registry proofs completed successfully before the hang. No provider, M07,
Registry, Capacity, persistence, API, UI product, or public-contract behavior
is changed by this finding.

### Test-first correction boundary

Production change is limited to
`tools/ui/verify_m5_codex_alert_lifecycle.mjs` and the smallest directly owned
automation tests. A focused Red must execute the exact script against the real
authenticated shared Chrome, running service, database, and recovered alert;
observe one schema-valid proof document; and prove that the child fails to
exit within a bounded deadline. Source-text inspection, a fake CDP endpoint,
constructed alert data, or a forced success after timeout cannot satisfy the
Red.

The minimal Green retains the connected browser handle and, after closing only
the page created by this script, explicitly closes the Playwright CDP client
connection so Node has no retained transport handle. It must preserve the
script's existing error status and cleanup behavior when page or connection
cleanup fails. It must not close, relaunch, log out, or otherwise control the
owner's Chrome process, pre-existing contexts or pages, authenticated session,
or any application/provider state. `process.exit()` and an ignored/unreferenced
timer or socket are prohibited substitutes for releasing the owned client
resource.

Green requires the exact real child to emit one valid proof and exit zero well
inside the parent timeout. Independent before/after evidence must prove the
same Chrome PID/start identity and CDP endpoint remain live, the script-created
page is gone, one pre-existing authenticated dashboard target remains open at
the same URL, and a new CDP client can still use the authenticated dashboard,
the selected service PID/start/revision remains unchanged, browser mutations
remain zero, and the complete public Registry digest is unchanged. The Python
writer must then consume that proof and create the fixed owner-only alert
witness once. A retained timeout continues to fail closed as
`m5_alert_witness_browser_unavailable` and cannot create a witness.

This correction contributes `M5-CDX-ALERT-007` to `FR-ALERT-004/005`,
`NFR-RES-001`, `AC-ALERT-002`, `AC-OPS-006`, and `AC-TEST-003/004`. It changes
no public API, event, database, provider, UI, configuration, generated-client,
dependency, license, migration, or ADR contract.

### Approved one-time fourth service rollover

The correction and its evidence must be committed, but the M5 service,
Operations source revision, and immutable activation receipt currently bind
exact revision `e066d7e1ba0124f0454c07002ea7b2ad0817d6b9`. Manual receipt
editing, deletion, or rebinding remains prohibited. Version 1.7.0 therefore
authorizes one exact fourth corrective rollover from that completed revision to
one eventual reviewed clean candidate containing only this correction, its
tests, the fourth-rollover extension, synchronized controls, documentation,
and evidence in one commit.

The existing `AUTO-M5-SERVICE-ACTIVATE` guard and two-stage transition remain
the only transition path. Before mutation, it must validate the current
`e066d7e` receipt, journal, rollback unit, clean detached checkout, exact
same-user systemd and `/proc` identity, Operations revision, authenticated
browser, Registry digest, database identity, pinned trusted rollback runtime,
and the three fixed singleton archives for `6bfa69d`, `0634451`, and
`6d6e1aa`. A later PID/start generation is accepted only by the existing
same-revision restart policy.

Under the existing exclusive guard, stage one proves the pinned trusted
runtime, then preserves the complete `e066d7e` transition directory by Linux
same-filesystem atomic no-replace rename into the fixed owner-only parent
`m5-service-activation-corrective-archive-e066d7e`. Its sole child is bound to
the full revision and activation-receipt digest. The command fsyncs both
parents, creates one fresh owner-only transition root, and returns the existing
typed rerun-required status 5. Stage two revalidates all four ordered archives
and the prepared state, performs the existing real rollback drill, and
activates only the new clean candidate. The candidate must differ from the
pinned trusted revision and all four completed corrective revisions.

Descriptors retain every earlier archive parent, directory, and artifact;
owner, mode, link count, inode, and digest are revalidated before each
filesystem or service mutation. Empty, partial, multiple, collided,
cross-filesystem, changed, unknown, interrupted, or browser-unavailable states
retain the existing fail-closed recovery and trusted-service restoration
guarantees. No archive is discovered by recency, replaced, cleaned up, or
generalized into deployment authority.

### Fresh evidence and acceptance gates

1. Extend the frozen activation tests first. Red must show that `e066d7e` is
   reserved without a fourth-rollover policy. Green covers exact
   candidate/reserved-revision policy, the fourth atomic inode move, four
   ordered singleton archives, retry/interruption recovery, collision and
   partial-state rejection, authenticated browser preservation, and restarted
   same-revision service handling.
2. Run the focused browser Red and Green above, the complete alert-witness
   automation suite, the M5 UI policy suite, and the full activation suite.
   Ruff/format, strict mypy, diff, documentation, planning, quality, build,
   test, mutation, and Git preflight gates must pass on the clean candidate.
3. Live activation stage one must return status 5 with the trusted service
   proven active. Stage two must leave the exact clean candidate active with
   matching HTTP, Operations revision, authenticated browser, Registry,
   database, systemd, rollback, archive, journal, and receipt evidence. The
   owner Chrome process and authenticated session must remain open throughout.
4. Every create-once prerequisite bound to `e066d7e` becomes stale after the
   transition. Preserve the existing set only through
   `AUTO-M5-ARCHIVE-PREREQUISITES`, then recollect owner outcomes against the
   candidate service. The lifecycle that exposed this Red remains retained
   history but cannot satisfy the new service-bound witness. Create a fresh
   post-service, post-owner-confirmation occurrence using only genuine
   scheduled collections: opening or reopening, a distinct repeat, one owner
   action, and a distinct source-proven recovery.
5. `AUTO-M5-ALERT-WITNESS` must then pass once against that fresh lifecycle and
   create its private witness without timing out or closing Chrome. Create the
   short-lived quota witness afterward, immediately run `AUTO-M5-EXIT`, and
   require its exact clean-revision receipt before any M5 completion claim.

This approval adds no provider/profile operation, telemetry edit, Registry or
database repair, agent control, general deployment, `AUTO-DEPLOY`, or broader
PLAN-DEP/D01 authority. Production implementation and the fourth transition
may proceed only through the exact test-first, review, clean-candidate,
fail-closed transition, evidence, and completion boundaries above.

## Approved P02 canonical-browser correction within the pending fourth rollover — 2026-10-20

**Status: Owner-approved 1.8.0 on 2026-10-20. Production implementation is
authorized only within the exact boundary below. Approved version 1.7.0 and
all retained evidence remain unchanged.**

### Real-system Reds discovered by the required 1.7 gate

The approved 1.7 correction passed its focused real-browser proof, quality, and
build lanes. The canonical `AUTO-TEST` gate and focused real-browser follow-up
then exposed two P02 product defects and one P02 browser-oracle race against
the production build and real local HTTP/IAM stack:

1. At the required 390 by 844 viewport, `documentElement.clientWidth` and
   `window.innerWidth` were 390 while `documentElement.scrollWidth` was 392.
   The dashboard header occupied 390 pixels, but `.header-actions` and the
   visible **Sign out** control ended at x=392. The primary navigation retained
   its intentional internal horizontal scroll and was not the document
   overflow source.
2. After the real secondary browser session was revoked through the production
   API, an already-running protected request could receive the resulting 401
   and move that context to **Sign in** before the scenario clicked **Check
   session**. The unconditional click then timed out even though automatic
   revocation recovery had already reached the required secure state.
3. Repeated real password-change runs reproduced an inconsistent shell after a
   completed mutation: `PATCH /api/v1/session/password` returned 204 and the
   renewed `GET /api/v1/session` returned 200 within one second, yet the safe
   browser state remained at `/login` with the authenticated AgentMonitor shell
   visible, no Sign-in heading, no busy button, and no success status through
   120 seconds. An Overview read begun with the previous cookie had invoked the
   current immediate expiry callback while the password panel concurrently
   renewed the session. The expiry path cleared the route and password panel;
   the later successful `onChanged` restored only the session object. This is a
   product race, not a slow-password or widened-timeout case.

These Reds contribute `UI-RESP-006`, `UI-AUTH-008`, and `UI-AUTH-009` to
`FR-UI-001`, `FR-IAM-001/003`, `NFR-RES-001`, `NFR-SEC-001`,
`NFR-PRIV-001/002`, `NFR-TEST-001/002`, `AC-UI-001/003/004/005`,
`AC-V1-005/007`, and `AC-TEST-001/003`.

### Exact correction boundary

The approved production and browser-test scope is limited to:

- `frontend/src/app/dashboard.css` and
  `frontend/tests/browser/p02/responsive.mjs`: at 400 pixels and below, return
  the existing dashboard header to its two-row mobile layout so both header
  controls remain visible and keyboard reachable inside the viewport. Preserve
  the compact row above that breakpoint and the navigation's internal scroll.
  Hiding or truncating a control, globally masking overflow, or weakening any
  of the six viewport assertions is prohibited.
- `frontend/tests/browser/p02/revocation.mjs`: after the real server revocation,
  accept exactly the two secure production outcomes—automatic arrival at
  **Sign in**, or one explicit **Check session** action followed by **Sign in**.
  If the one-time click loses its target during automatic recovery, that is
  accepted only after **Sign in** is actually visible. Both branches must prove
  protected navigation absent, reload still signed out, and the primary
  session still active. Retrying, sleeping, widening the timeout, or accepting
  any protected/unknown secondary state is prohibited.
- `frontend/src/app/DashboardApp.tsx`,
  `frontend/src/features/auth/PasswordChangePanel.tsx`, and
  `frontend/tests/browser/p02/password_change.mjs`: implement a closed parent
  lifecycle of `closed`, `draining`, `ready`, and `submitting`. Opening the
  password flow synchronously advances a protected-feature generation and
  enters `draining`, unmounts every protected feature page, fences callbacks
  from the obsolete generation, and makes header/nav/session actions and
  popstate route changes inert for every non-`closed` phase while
  canonicalizing the browser URL and internal route to `/`. The bounded
  draining view exposes an accessible preparation status. A
  parent React effect may acknowledge `ready` only after the removed subtree's
  effect cleanup has fired its existing AbortControllers; only then may the
  password form mount and become interactive. The fence prevents a late
  consumer of an already-started safe read from invoking expiry after that
  barrier; it does not claim to cancel server-side read work.

  Submitting advances to the exclusive `submitting` phase before any request.
  The panel remains mounted while all protected feature pages, navigation,
  **Check session**, **Sign out**, repeat submit, and route changes remain
  inert. Exactly one preflight is allowed before mutation, exactly one password
  PATCH is allowed per submit, and at most one post-dispatch session GET is
  allowed; no PATCH retry is permitted. Success requires the exact ordered pair
  of an observed PATCH 204 followed by that single GET 200. Only that pair may
  install the returned session coherently, close the panel, return to `/`,
  remount protected content under the current cookie, and present the success
  status in the persistent shell. Only the typed
  `dashboard_authentication_required` outcome enters login. The typed
  `invalid_dashboard_credentials` outcome and other known noncommitted 4xx
  outcomes return to `ready` with their existing generic safe message;
  missing/rejected CSRF uses the existing proof-renewal path. After a transport
  or other unknown PATCH outcome, one optional session GET may classify only
  whether authentication remains active; a 200 never confirms the mutation or
  permits success, and the protected view remains locked for owner
  verification. A pre-mutation validation failure may return to `ready`. A
  visible cancel/back action is available only in `ready` and closes the form
  without mutation. Entering `ready` moves focus to the password heading or
  current-password input. Cancel returns focus to the remounted **Change
  password** control; successful close moves focus to the persistent success
  status or remounted page heading.

  Only this closed set of non-secret lifecycle phase and acknowledgement
  signals crosses the new parent/component interface. Password values,
  cookies, headers, bodies, and
  error objects remain component/client local and never enter DashboardApp
  state, browser storage, logs, diagnostics, evidence, or chat. Existing form
  reset and credential privacy behavior remain binding. Global 401 suppression,
  timeout/sleep barriers, mutation retries, cookie changes, or history repair
  after an inconsistent state are prohibited.
- `frontend/tests/browser/p02/run_browser.py`: its change is limited to a
  bounded repeat option accepting only integers 1 through 30 so the same
  isolated real-server/real-Chrome scenario can run an exact number of
  consecutive times and fail on the first Red. For these
  three scenarios it also validates child output against a closed safe-line
  grammar and emits only a stable `browser_output_invalid` code for unexpected
  stdout/stderr instead of propagating raw child text. It must not retry a
  failed run or convert a failure into a pass.
- `frontend/tests/browser/p02/test_run_browser_policy.py` (or the existing
  canonical pure P02 policy-test path): add an I/O-free test for only the
  runner's closed output and repeat policy. Constructed strings are permitted
  at this pure boundary. Red/Green must prove allowlisted stage/pass lines are
  accepted; nonpositive/out-of-bound repeat counts are rejected; and arbitrary
  exception, full-URL, or secret-shaped text produces only
  `browser_output_invalid` without retaining or returning the raw child text.

The responsive proof must require both header-action rectangles fully inside
the 390-pixel viewport and keyboard reachability while preserving nav-only
horizontal scroll. The password browser proof must observe the real lifecycle
and request ordering: the cleanup acknowledgement precedes form interactivity;
no non-password feature-page request starts during `ready` or `submitting`;
only the named preflight/PATCH/reconciliation sequence crosses that interval;
the feature view is absent and shell controls are inert; exactly one PATCH is
sent; the one post-PATCH session GET returns 200 before feature remount; and
requests from the new protected-feature generation begin only after the phase
is `closed` with the current session and `/` route installed. The route remains
`/` with the protected shell and success status stable afterward. The proof
also checks the draining status, ready focus target, Cancel focus restoration,
success focus target, and URL/route coherence after blocked popstate.
It retains the existing sign-out, old-password rejection, and new-password
acceptance assertions and rejects any late expiry. All three modified browser
scenarios limit committed failure output to stable stage codes and allowlisted
method/path/status classes plus safe route/UI-state classifications. They must
never emit credentials, cookies, headers, bodies, arbitrary exception text, or
full URLs; the current temporary revocation diagnostic is replaced rather than
retained.

### Contracts, ownership, and verification

P02 owns the React shell, styles, and browser scenarios. This correction uses
existing compatible `CTR-API-002`, `CTR-IAM-003/004/005`, and `CTR-UI-001` V1
behavior. It changes no API, OpenAPI, generated client, backend, database,
provider adapter, configuration, dependency, license, migration, or ADR
contract and adds no provider or Registry operation.

After approval, planning control synchronization covers
`docs/plans/README.md`, `docs/plans/deployment/linux-native/plan-v1.md`,
`docs/plans/contract-adoption.toml`, `docs/plans/parallel-ownership.toml`,
`docs/plans/plan-baseline.toml`,
`docs/plans/integration/cs1-full-plan-synchronization.md`, and
`docs/plans/integration/cs1-final-readiness-audit.md`. Implementation evidence
then synchronizes `docs/modules/react-dashboard.md`,
`docs/evidence/m5-codex-implementation.md`,
`docs/evidence/v1-implementation-status-v1.json`, and `docs/README.md`.
Requirement ownership, API/OpenAPI/client artifacts, backend and database
contracts remain unchanged.

Green requires 30 consecutive isolated real-server/real-built-Chrome passes for
each of responsive, revocation, and password change through the bounded runner
option (`run_browser.py <scenario> --repeat 30`, with `--no-build` permitted
only after one successful production build), followed by the complete P02
browser lane, `AUTO-QUALITY`, `AUTO-BUILD`, and the complete canonical
`AUTO-TEST` with no retry-hidden pass. Timeouts, sleeps, retries, scenario
deselection, or accepting an unknown state cannot satisfy Green. Documentation
and evidence must synchronize the P02 module, M5 implementation status, plan
hashes, and cross-plan snapshots before planning, documentation, mutation, and
Git preflight gates run.

The service still runs exact `e066d7e1ba0124f0454c07002ea7b2ad0817d6b9`, and
the approved fourth rollover has not started. Version 1.8.0 folds
these bounded P02 corrections into the same one eventual reviewed clean
candidate and the same fourth rollover already authorized by 1.7.0. It does not
authorize a fifth rollover, a second candidate activation, broader P02 work,
or any relaxation of the M5 completion gate. Version 1.8.0 supersedes only
1.7.0's candidate-content restriction that said the fourth-rollover candidate
contained only the alert browser correction; every other 1.7 transition,
evidence-preservation, rollback, stop, and safety condition remains binding.

## Approved quota-witness policy-projection correction — 2026-10-21

**Status: Owner-approved 1.9.0 on 2026-10-21. Production implementation and one
fifth service rollover are authorized only within the exact boundary below.
Approved version 1.8.0 and its retained evidence remain unchanged.**

### Real-system Reds discovered by the required 1.8 completion gate

The exact clean `d81afab9e5b1c1dbdb690f390e77cee66eba5437` candidate passed
its focused and complete local gates, was activated through the approved fourth
rollover, and retained a live authenticated browser plus the required external
Codex process set. `AUTO-M5-QUOTA-WITNESS` then completed its real authenticated
API, DOM, current history, Registry, identity, collection-lineage, and
zero-mutation proof and accepted all four owner-entered quota windows. Final
reconciliation returned `m5_quota_witness_input_invalid` and created no private
file. A no-write diagnostic rerun located the rejection at
`m5_codex_quota_witness.py:500`: the validated browser window intentionally
contains the opaque browser-proof/history-binding-only
`current_observation_id`, while the closed
quota policy record accepts exactly the five provider-neutral quota fields. The
same function already builds the correct five-field policy projection for
digest verification but returns the six-field browser record to the final
reconciliation path.

This Red contributes `M5-CDX-GATE-001..014`, `FR-QUOTA-001..006`,
`FR-HIST-001/002`, `NFR-TEST-001/002`, `AC-LIVE-005`, `AC-HIST-001`,
`AC-OPS-003/006`, and `AC-TEST-001..006` within the existing M5 boundary.

### Exact correction boundary

Implementation is limited to all of the following:

- In `tools/automation/implementations/m5_codex_quota_witness.py`, return or
  rebuild the already verified five-field provider-neutral policy projection
  before final reconciliation. The opaque `current_observation_id` remains
  mandatory input to the private browser/history digest and is removed only
  after that digest is independently recomputed. No accepted value, freshness
  interval, owner confirmation, identity, Registry, DOM, history, mutation,
  permission, create-once, or revision/service binding is weakened.
- Add pure Red/Green coverage proving the browser-proof/history-binding-only
  observation field is
  required for history binding and absent from the closed reconciliation
  input; the complete validated browser record reconciles after shaping; extra
  non-browser fields remain rejected; and the existing private browser-proof
  schema and digest stay unchanged.
- Synchronize only the affected M5 plan, runbook, module/evidence/status,
  automation registry, and planning-control documents. No API, OpenAPI,
  database schema, Registry contract, provider payload contract, dependency,
  UI behavior, default provider profile, agent control, or broader deployment
  scope changes.

### Fifth evidence-preserving rollover

Because every M5 prerequisite and the running Operations inventory bind the
exact source revision, the correction must produce one reviewed clean detached
candidate and one fifth controlled rollover from
`d81afab9e5b1c1dbdb690f390e77cee66eba5437`. Extend the frozen activation
policy and tests by one exact fixed archive namespace
`m5-service-activation-corrective-archive-d81afab`; require the four existing
archives as an unchanged ordered prefix; atomically retain the complete `d81`
activation directory by same-filesystem no-replace rename; fsync both parents;
and preserve the existing two-stage status-5 rerun, rollback drill, authenticated
browser, file identity, digest, collision, interruption, and trusted-service
restoration rules. The new candidate must differ from the pinned rollback
revision and all five archived corrective revisions. The transition is not
general deployment authority.

Before activation, Green requires the focused quota-witness and activation
suites, then the complete canonical quality, build, test, mutation,
documentation, planning, and Git
preflight gates. After activation, archive the now stale create-once M5
prerequisites through the existing canonical archive command, recreate owner
outcomes from the already owner-confirmed four-account disposition, create one
fresh genuine alert lifecycle and alert witness, reconcile fresh official
Codex status readings through `AUTO-M5-QUOTA-WITNESS`, and immediately run
`AUTO-M5-EXIT`. M5 remains incomplete unless the exact clean-revision receipt
is created and passes its final rereads.

This approval adds no relaxation, bypass, fabricated collection, replacement
of a create-once file, sixth-rollover execution, provider or scheduler
behavior, provider login, provider mutation, default-profile access, telemetry
edit, process control, `AUTO-DEPLOY`, OpenAI API billing, or broader
PLAN-DEP/D01 authority.

## Approved managed-profile effective-containment correction — 2026-10-21

**Status: Owner-approved 1.10.0 on 2026-10-21. Version 1.10.0 supersedes only
1.9.0's candidate-content restriction and folds this correction into the
already authorized, not-yet-run fifth rollover from
`d81afab9e5b1c1dbdb690f390e77cee66eba5437`. It authorizes no sixth
rollover.**

### Real-system Reds discovered by the required 1.9 preactivation suite

The zero-skip M5 Story run reached the real managed-profile containment test
and failed before provider execution with
`m5_codex_containment_profile_tree_invalid`. Read-only metadata inspection of
all three verified Codex profiles established the same real layout:

- the owner data root, `profiles`, `profiles/codex`, and each selected profile
  root are plain owner-owned directories with exact mode `0700`;
- each `auth.json` is an owner-owned, single-link regular file with mode `0600`;
- every descendant is a same-UID, same-device regular file or directory, with
  no symlink, hardlink, nonregular type, special permission bit, or foreign
  owner; and
- Codex and its runtime create ordinary plugin, cache, and runtime entries with
  modes `0444`, `0600`, `0644`, `0664`, `0700`, `0755`, or `0775`.

The automation-only `_managed_profile_tree_digest` currently rejects every
descendant with any group or other permission bit. That is stricter than the
approved security boundary, which requires the enclosing managed roots to be
owner-only and validates the credential store separately. An exact `0700`
root prevents every other UID from traversing to a descendant regardless of a
descendant's ordinary permission bits; mode `0600` also does not isolate a file
from another process running as the same UID. Direct `chmod`, profile copying,
profile replacement, or reauthentication would mutate provider state, would
not durably match provider behavior, and is prohibited.

The same run exposed one independent test-expectation defect in
`test_live_connected_profile_enrollment_is_idempotent_when_selected`.
The second enrollment intentionally reconciles the real Codex installation and
therefore advances the global Registry snapshot watermark once while leaving
the account, profile, resource, and aggregate record versions unchanged. The
test incorrectly required exact equality including `registry_revision`.
Test-only Red/Green now compares aggregate fields without that global watermark
and separately proves the one expected revision advance. This changes no
Registry production behavior or contract.

### Exact correction boundary

Production change is limited to
`tools/automation/implementations/m5_codex_containment.py`:

- Define the tree check by effective enclosing-root containment. Keep the
  owner data root, profiles root, provider root, and selected managed-profile
  root exact owner-owned `0700` directories with no symlink and pinned inode,
  and revalidate them after provider work.
- Permit ordinary permission bits on nested provider-owned regular files and
  directories only while they remain enclosed by those exact private roots.
  Retain every nested mode in the pre-provider and post-provider evidence
  digests.
- Continue rejecting every nested symlink, nonregular type, foreign UID,
  cross-device entry, regular-file hardlink, setuid/setgid/sticky bit,
  over-limit count or path, or traversal error. Require each nested directory
  to be owner-readable and owner-searchable, and make filesystem-walk errors
  fail closed so an incomplete scan cannot pass.
- Keep the production transport's `auth.json` rule unchanged: owner-owned,
  single-link regular file, no group or other permission bits, and bounded
  size, validated before and after provider use.
- Keep real syscall tracing, provider-write confinement, zero default-profile
  access and writes, executable/runtime/service/revision binding, private
  channels, closed result schema, and create-once receipt behavior unchanged.

This approval authorizes no `chmod` or `chown`, profile read/copy/delete/move/
replacement, provider login or reauthentication, default-profile operation,
Registry or database mutation, API, UI, scheduler, configuration, dependency,
schema, migration, public-contract change, gate bypass, or sixth rollover.

### TDD, live proof, and synchronization

Red adds real-filesystem coverage showing that an exact `0700` managed root
containing representative provider-created `0755`/`0775` directories and
`0444`/`0644`/`0664`/`0755` files is rejected by the current tree check. Green
must prove that this tree produces a digest and that changing one permitted
nested mode changes that digest. Negative real-filesystem cases must retain or
add exact rejection of a nonprivate selected root, symlink, hardlink, FIFO or
other nonregular entry, special permission bit, foreign device/owner where
safe to exercise, owner-unsearchable directory, traversal error, and bounded
count/path violations.

Required local proof is the focused new Red/Green, complete containment suite,
the corrected real enrollment test, Ruff, format, strict mypy, an explicit
Story inventory rebind if added test identifiers change it, and every canonical
1.9 preactivation gate. Read-only metadata validation must cover all three
verified real managed roots. After the single fifth activation, the canonical
live containment test and `AUTO-M5-EXIT` must invoke real identity and quota
operations, prove zero default-profile access/write and confinement of every
declared write to the selected managed profile, and bind the resulting tree
digests into the exact completion evidence. Skips cannot pass.

The local correction is present in commits `1143d96` and `f4d4bf7`; commit
`ae33540` provides an interim Story inventory of `478` Python tests and digest
`ba070544ac4f8e7aabe53492b6afa91f74d8b1c149bd20134b7f19badfa0df9c`.
The focused intermediate-root Red failed because a `0755` `profiles`
directory was admitted; its two-test Green passed. The current non-live
containment suite passed `28` tests, while the complete `29`-test file passed
those same `28` and skipped the owner-selected authenticated case. That skip
is not live evidence. Review then found that the plan-required negative
entry-count and path-length cases are absent. Local 1.10 proof therefore
remains incomplete, and the inventory must be rebound after those cases are
added.

A later real containment attempt against the still-running `d81afab` service
passed its safe metadata and driver stages, then failed closed as
`m5_codex_containment_path_mutator_unverifiable`. Trace classification found
two successful provider app-server `chmod` calls, both inside the selected
managed profile and none under default roots, but did not yet prove their path
arguments through the closed mutator policy. It created no completion receipt
and does not expand this approval. Passing authenticated containment remains
pending after this Failed attempt; the fifth service rollover and
`AUTO-M5-EXIT` remain Not Run.

Documentation synchronization is limited to this plan, the Codex adapter
boundary, M5 implementation evidence/status, operations wording where needed,
the documentation indexes, and generated planning-control hashes. There is no
public contract, ADR, database, migration, dependency, license, API, generated
client, UI, or provider-payload impact. M5 remains Intermediate until the
already specified fifth rollover, refreshed prerequisites, corrected quota
witness, and `AUTO-M5-EXIT` all pass.

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
   official `/status` view at exact whole percentage, displayed reset precision,
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
authoritative `/status` reconciliation, and the capacity-alert opening, action,
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
