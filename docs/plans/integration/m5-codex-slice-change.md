# Change plan: executable V1-M5 Codex slice

Current amendment: [owner-approved 1.21.0 timeout recovery and deployment](m5-timeout-recovery-change.md)
supersedes the production/ninth-rollover exclusions below only for its named
scope. Revision `468a937d796efcb7ff1785a749789f07a3322abc` is active after
the eighth rollover; its fresh owner and alert prerequisites passed. Its quota
prerequisite is Blocked by a retained timeout preventing future scheduled runs.
The 1.20 checkpoint below is preserved as preactivation history.

- Status: **Owner-approved 1.20.0 is locally implemented with owner-approved
  1.19.0 and 1.18.0 in one combined, unactivated candidate. Focused Green,
  the exact zero-skip Story inventory, authenticated containment, and the
  local preactivation routines through `AUTO-TEST` pass. Detached clean-revision
  Git preflight, the single eighth activation, refreshed live prerequisites,
  `AUTO-M5-EXIT`, and owner acceptance remain Not Run. The active clean
  service remains revision
  `1ada84f71e827bb4f7ea966462a6cf51d050e9af`. No activated combined revision,
  quota witness, M5 receipt, or completion claim is credited.**
- Plan version: owner-approved `1.20.0`; owner-approved `1.19.0` and `1.18.0`
  remain incorporated unchanged.
- Safety correction: exact-version review proved that authenticated app-server
  queries may perform Codex's automatic credential refresh. The approved
  managed-auth lifecycle therefore classifies those queries as
  `managed_profile_write`, and an empty/uninitialized managed root is rejected
  before any app-server child starts.
- Owner: `PLAN-INT`, with A02 provider behavior and the exact PLAN-DEP/D01
  service-activation exception owned under this bounded change. Approved 1.8.0
  was the sole active exception to PLAN-P02's Draft implementation
  prohibition before 1.16.0. The owner's explicit 2026-10-23 approval adds one
  bounded exception for only the enumerated PLAN-M05 and PLAN-P02 files below;
  those plans remain semantic owners, and the root integration agent acts as
  their file steward with no concurrent writer.
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
  managed-profile effective-containment correction specified below. The
  owner's explicit 2026-10-21 approval of version 1.11.0 adds only the exact
  inode-bound provider `chmod` and private-channel diagnostic correction
  specified below. The owner's explicit 2026-10-22 approval of version 1.12.0
  adds only the trace-completeness correction specified below. The owner's
  explicit 2026-10-22 approval of version 1.13.0 adds only the descriptor-bound
  `ftruncate` correction specified below. The owner's explicit 2026-10-22
  approval of version 1.14.0 adds only the
  exact pinned Codex 0.160.0 temporary Arg0 symlink lifecycle specified below;
  the owner's explicit 2026-10-22 approval of version 1.15.0 adds only the
  exact session creation and literal `.lock` regular-file child lifecycle
  specified below. The owner's explicit 2026-10-23 approval of version 1.16.0
  supersedes only the earlier statement that 1.8.0 is the sole PLAN-P02
  exception and adds only the enumerated PLAN-M05, PLAN-P02, witness, and
  sixth-rollover scope below. The owner's explicit 2026-10-23 approval of
  version 1.17.0 adds only the exact pytest-node artifact correction, one
  seventh evidence-preserving rollover from
  `35f50d8c4865505a9112d8aef7ea788f425ae658`, refreshed service-bound
  prerequisites, and one corrected `AUTO-M5-EXIT` rerun specified below;
  all remaining A02, OpenAI API, PLAN-DEP/D01, and
  `AUTO-DEPLOY` lanes stay Draft or Blocked as already recorded.
  The owner's explicit 2026-10-24 approval of version 1.18.0 adds only the
  exact full-unused-window reset relation,
  its focused tests, the exact Story inventory rebind, one eighth
  evidence-preserving rollover from
  `1ada84f71e827bb4f7ea966462a6cf51d050e9af`, refreshed
  revision/service-bound prerequisites, and one complete `AUTO-M5-EXIT`
  rerun. It supersedes only 1.17.0's prohibitions on quota-policy and quota-test
  changes and an eighth rollover; every other 1.17.0 boundary remains binding.
  The owner's explicit 2026-10-25 approval of version 1.19.0 adds only the
  exact pinned-pytest JUnit
  identity/outcome distinction, its focused tests, and the final zero-skip
  inventory binding. It retains 1.18.0's single pending eighth rollover from
  `1ada84f71e827bb4f7ea966462a6cf51d050e9af`; it adds no ninth rollover or
  second candidate transition. It supersedes only 1.18.0's restriction of
  `auto_m5_current_exit.py` changes to the count/digest constants.
  The owner's explicit 2026-10-25 approval of version 1.20.0 adds only
  deterministic real-filesystem modes to two
  existing selected test fixtures, their focused Red/Green proof, and the
  final zero-skip Story inventory binding. It changes no production behavior
  and retains the same single pending eighth rollover.
- Stories: `ST-CDX-001..005`.
- Requirements: `FR-ACC-001/004..006`, `FR-AUTH-001/002/004..006`,
  `FR-QUOTA-001..006`, `FR-COL-003..008`, `FR-HIST-001/002`,
  `FR-DISC-001/003/004/006/008`, `FR-STATE-001/002`, `FR-SAFE-002`,
  `FR-ALERT-002..006`, `FR-UI-001..006`, `FR-IAM-001/003`,
  `NFR-API-001/002`, `NFR-ARCH-002`,
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
the routine requires exact account/window membership, semantic roles, whole
percentages, and at most 300 seconds between the provider observation and
AgentMonitor collection. Resets must match at the displayed
second/minute/hour/day precision. Only when two readings are exactly `100%`,
both resets are present, the AgentMonitor reset is exact, and the owner
observation follows collection by 1--300 seconds may the displayed owner reset
instead overlap the reset's one-for-one forward movement during that bounded
interval. Non-100, fixed, null, imprecise, missing/extra-window, and otherwise
unexplained reset cases retain the strict rule. The routine records only counts
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

The local correction is present in commits `1143d96` and `f4d4bf7`. Commit
`d71b79c` adds the required real-filesystem entry-count and overlong-relative-
path cases and rebinds the Story inventory to `480` Python tests with digest
`e90485d6866065f3149cf1285b5c18c665d26068de2da5c4c61862830bb56bf9`.
The focused intermediate-root Red failed because a `0755` `profiles`
directory was admitted; its two-test Green passed. The two bounds cases passed,
the non-live containment suite passed `30` tests, the complete file passed
those same `30` and skipped only the owner-selected authenticated case, and
the current-exit suite passed `66` tests. That skip is not live evidence.

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

## Approved inode-bound idempotent chmod correction — 2026-10-21

**Status: Approved 1.11.0. This approval authorizes one automation-only
correction folded into the already authorized, not-yet-run fifth rollover from
`d81afab9e5b1c1dbdb690f390e77cee66eba5437`. It authorizes no sixth rollover.**

### Real-system Red and observed boundary

The required authenticated 1.10 live containment run reached both production
Codex app-server operations and then failed closed as
`m5_codex_containment_path_mutator_unverifiable`. Privacy-safe in-memory
classification established exactly two successful plain `chmod` calls, one in
each app-server operation lineage. Both requested literal mode `0700` on the
same preexisting strict-descendant directory inside the selected managed
profile. Before and after the run the target was mode `0700` and retained the
same device, inode, owner, and directory type; its change time advanced.
Neither call named a default-profile path. No raw trace, provider payload,
private path, identity, or credential was retained.

The current trace policy intentionally rejects all successful path-following
mutators because `strace -yy` does not report a kernel-resolved target for
plain `chmod`. Accepting a lexical in-root string alone would weaken the gate.
Plan 1.10 also explicitly excluded a `chmod` policy change, so the real Red is
outside its approval even though the provider operation itself is the already
approved `managed_profile_write` lifecycle.

Two earlier attempts returned
`m5_codex_containment_private_channel_invalid` before a result payload was
available. The current collector collapses missing, invalid, or late channel
outcomes into that one code and can discard the other completed outcome. No
retained artifact can distinguish the causes of those two attempts, so this
plan makes no narrower historical claim.

### Exact proposed correction boundary

Production change remains limited to
`tools/automation/implementations/m5_codex_containment.py`:

- Before provider execution, keep one `O_PATH | O_DIRECTORY | O_NOFOLLOW |
  O_CLOEXEC` descriptor for the selected managed-profile root and retain an
  in-memory bounded directory identity table from the existing maximum-10,000-
  entry, maximum-4,096-byte-relative-path tree walk. Do not open one descriptor
  per tree entry.
- Apply default-root detection and the existing generic access/write
  confinement to every trace record before considering the narrow exception.
  Parse `chmod` with a full-match argument grammar: exactly one quoted absolute
  normalized path plus literal mode `0700`; substring or partial matches fail.
- Require exactly two `chmod` records in the complete traced process tree,
  both with syscall result exactly `0`: exactly one in each of the two
  ordered, fixed-sequence-mapped app-server operation lineages, none in the
  version lineage or unattributed processes. Require strict provider execution
  order `(version, identity app-server, quota app-server)` with no overlap, and
  bind descendants to that exact operation object. Both records must name the
  same strict-descendant target. Any
  additional, failed, differently shaped, differently targeted, or differently
  moded `chmod` fails closed.
- After trace extraction, walk that target from the already pinned profile root
  one component at a time with descriptor-relative `O_PATH | O_DIRECTORY |
  O_NOFOLLOW | O_CLOEXEC` opens. Revalidate every ancestor and the target
  against the pre-execution table and the post-execution tree: owner UID,
  device, inode, directory type, and path identity must match; the target must
  be `0700` before and after. Use a rolling maximum of three descriptors for
  this walk—the pinned root, current parent, and next child—and fail closed on
  any open, close, metadata, identity, or resource error. Retain the final
  target descriptor through the post-tree validation. A later change time is
  required only as corroboration that metadata changed during the run; it is
  not evidence that independently attributes both calls.
- Replace the current trace selector with this exact admitted expression:

  ```text
  trace=%file,%process,chdir,fchdir,fchmod,fchown,ftruncate,fallocate,clone,clone3,setns,unshare,chroot,pivot_root,mount,umount,umount2,open_tree,move_mount,fsopen,fsconfig,fsmount,fspick,mount_setattr
  ```

  Before any provider child, invoke the exact root-owned tracer on validated
  root-owned, non-writable `/usr/bin/true` and fail closed if the installed
  tracer rejects the expression. Real Linux tests must issue deliberately
  invalid, no-effect namespace syscalls and prove the selector records the
  named calls; category names alone are not evidence of coverage. The current
  installed strace 6.8 accepts this exact expression.
- Reject any traced link, symlink, rename, unlink, mount, or other namespace
  replacement affecting the target or an ancestor. Continue rejecting every
  `chown`, `fchmod*`, `fchown*`, `truncate`, `utime*`, unresolved path/fd
  mutator, default-root access/write, and out-of-profile write under the
  existing policy. Reject `chroot`, `pivot_root`, all legacy and modern mount
  operations, `setns`, successful `unshare(CLONE_NEWNS)`, and `clone`/`clone3`
  creation of a mount namespace; any unknown operation that can change path-
  resolution or mount-namespace context fails closed.
- Keep the full before/after tree digest, four exact private enclosing roots,
  `auth.json` metadata rule, service/revision/executable binding, and closed
  evidence schema unchanged. The directory identity table, descriptors, path,
  and target metadata remain in process only; only the existing digest and
  aggregate counts may enter completion evidence. Every pin descriptor closes
  in `finally` and none is inherited by or passed to the provider process.

The verification-only write set is
`tools/automation/test_m5_codex_containment.py`, the inventory assertions in
`tools/automation/test_m5_current_exit.py`, and only the exact count/digest
constants in
`tools/automation/implementations/auto_m5_current_exit.py`. Documentation may
change only in this plan, the Codex adapter boundary, M5 evidence/status,
completion/runbook wording if the new safe codes require it, indexes, and
generated planning controls. Any other production file or contract change is a
stop condition and requires a new approved plan.

The private-channel collector must settle input, result, and trace futures
independently under one shared five-second monotonic deadline after driver exit
or process-group termination, close every owned descriptor to unblock pending
I/O, and never allow executor shutdown to wait without that bound. It then uses
this first-match precedence.
No raw exception, stderr, trace, path, provider output, or payload may cross
the boundary:

| Priority | Closed outcome | Classification |
|---:|---|---|
| 1 | Driver deadline, including failure to settle after process-group termination | `Unavailable: m5_codex_containment_driver_deadline_exceeded` |
| 2 | Result EOF with zero bytes | `Failed: m5_codex_containment_result_channel_empty` |
| 3 | Result oversize, read/descriptor failure, or late result future | `Failed: m5_codex_containment_result_channel_invalid` |
| 4 | Trace EOF with zero bytes | `Failed: m5_codex_containment_trace_channel_empty` |
| 5 | Trace oversize, read/descriptor failure, or late trace future | `Failed: m5_codex_containment_trace_channel_invalid` |
| 6 | Result bytes are not the exact closed result schema | `Failed: m5_codex_containment_result_invalid` |
| 7 | Input write/close/descriptor failure or late input future | `Failed: m5_codex_containment_input_channel_invalid` |
| 8 | Return `3` plus exact `unavailable` result | `Unavailable: m5_codex_containment_provider_unavailable` |
| 9 | Return `2` plus exact `failed` result | `Failed: m5_codex_containment_operation_failed` |
| 10 | Return `0` plus exact `passed` result | Continue to UTF-8, trace-policy, filesystem, and evidence checks |
| 11 | Any other return code/result-state pair | `Failed: m5_codex_containment_driver_status_invalid` |

Every row remains non-passing except row 10 after all later checks pass.
The exact `unavailable` and `failed` shapes have zero operation/bucket/window
counts and a null identity digest. Result and trace channel outcomes plus exact
result-schema validation precede input failure, so an early child exit with
both empty result and broken input reports the useful result cause. The
collector must still settle and close every channel. Trace UTF-8, grammar, and
security policy are evaluated only after the exact row-10 `0`/`passed` pair;
malformed UTF-8 and structurally invalid trace records then retain the existing
`m5_codex_containment_trace_invalid` failure, and security-specific policy
codes remain more specific. Rows 8 and 9 require a nonempty bounded trace
channel but do not interpret its contents and can never create evidence.
Missing output never passes, and a valid provider-unavailable result never
becomes Failed solely because the provider did not complete all three
successful executions.

This narrow proof does not claim atomic isolation from a malicious process
already running as the same Unix UID. V1's documented local single-user threat
disposition already accepts that such a process can access or change the same
owner-controlled files directly; the correction grants it no new capability.
The root-anchored walk, identity table, post-tree scan, and complete traced
provider process tree prevent a provider-controlled replacement within the
admitted syscall model from passing. They do not exclude a transient
substitution by a separate untraced same-UID process. A future multi-user or
hostile-same-UID deployment requires a separately approved kernel-mediated
isolation design.

This correction adds no new provider call or authorized side effect, login, profile
copy, default-profile access, dependency, OS sandbox, API, UI, database,
migration, schema, public contract, scheduler behavior, service transition,
process control, gate bypass, or broader deployment authority. Landlock cannot
mediate `chmod`; Bubblewrap would add a separate executable, namespace
topology, and security-advisory surface, so neither is proposed for this
focused correction.

### TDD and live proof

Before production changes, Red must preserve the current real failure and add
pure trace-policy plus real-filesystem tests for: the exact positive two-call
pattern; zero, one, or three calls; two calls in one operation lineage;
different targets; failed calls; wrong mode, type, owner, inode, device, root,
relative path, `..`, default-root path, and parser suffix/prefix; target and
ancestor replacement; version-lineage or unattributed calls; links, hard links,
and every other mutator. The existing lexical `truncate` case must remain Red.
Constructed trace strings prove only pure policy. Real filesystem tests must
exercise the root-anchored descriptor walk, rolling descriptor cap, and
pre/post identity validation.

The channel Red must reproduce the current collapsed code. Green must use real
anonymous pipes and real child processes to cover every row and precedence
collision in the table, including EOF, oversize, malformed schema, read/write
failure, rc `0/2/3/other`, deadline termination, and futures that finish in a
different order. These tests retain no raw child data and use no mocks, fakes,
stubs, recordings, or test-only production route.

Required local proof is focused Red/Green, the complete containment/current-
exit suites, Ruff, format, strict mypy, exact Story inventory rebind, and every
canonical preactivation gate. Before activation, a safe authenticated rerun
against the unchanged `d81afab` service must pass the corrected containment
policy with no skip; this is development evidence, not the final receipt.
After the single fifth activation, the exact live test must perform real
identity and quota operations, observe only the two allowlisted inode-bound
`0700` directory calls, prove zero default-profile access/write and all other
writes confined to the selected profile, and pass inside `AUTO-M5-EXIT` with
zero skips. M5 remains Intermediate until the final receipt exists and survives
its canonical rereads.

## Approved descriptor-metadata trace completeness correction — 2026-10-22

**Status: Approved 1.12.0 by the owner on 2026-10-22. This correction is folded
into the already authorized, not-yet-run fifth rollover; it does not authorize
a sixth rollover or any additional provider operation.**

### Real-system Reds and closed boundary

The 1.11 implementation review proved three ways that a provider process can
change an owner-controlled file without producing a policy-visible mutator in
the exact approved trace:

- successful `fsetxattr` and `fremovexattr` calls on an `O_RDONLY` descriptor
  were omitted by strace 6.8's `%file` category;
- successful `ioctl(FS_IOC_SETFLAGS)` on an `O_RDONLY` descriptor changed the
  private test inode's flags and change time, while `ioctl` was absent from the
  selector; and
- a private real `io_uring` probe created a new file through
  `IORING_OP_OPENAT`, while the trace contained none of `io_uring_setup`,
  `io_uring_enter`, `io_uring_register`, or the submitted open operation.

Each probe used only a temporary owner-controlled test file and restored or
removed its change. No default profile, provider profile, account, service,
browser, or running agent was changed. At plan approval the focused suite was
therefore deliberately Red and no containment pass or completion receipt was
claimed.

The same review found and corrected, within approved 1.11 scope, exact child
PID parsing, lexical and shared working-directory tracking, quoted-dirfd token
spoofing, `CLONE_UNTRACED`, visible path xattrs, `lchown`, `futimesat`, global
forbidden-mutator attribution, and duplicate JSON result members. Independent
review found no remaining blocker in the private-channel precedence and
deadline implementation, descriptor cleanup, process-group termination,
inode-bound walk, or sanitized evidence shape. Those corrections do not make
the selector Reds pass and remain intermediate until the complete gate passes.

### Exact proposed correction

Production changes remain limited to
`tools/automation/implementations/m5_codex_containment.py`:

- Replace the 1.11 trace selector by this exact expression:

  ```text
  trace=%file,%process,chdir,fchdir,fchmod,fchown,ftruncate,fallocate,fsetxattr,fremovexattr,ioctl,io_uring_setup,io_uring_enter,io_uring_register,clone,clone3,setns,unshare,chroot,pivot_root,mount,umount,umount2,open_tree,move_mount,fsopen,fsconfig,fsmount,fspick,mount_setattr
  ```

- Add this exact raw-argument qualifier to the selector probe and production
  trace command so xattr values, ioctl buffers, and asynchronous-I/O
  structures cannot enter the trace payload:

  ```text
  raw=fsetxattr,fremovexattr,ioctl,io_uring_setup,io_uring_enter,io_uring_register
  ```

- Classify the six raw calls globally and before path, ordinary-write, access,
  or lineage-mutator accounting. An exact `-1 ERRNO (...)` result is a proven
  no-effect call and is excluded from those later classifiers. Any successful
  `fsetxattr`, `fremovexattr`, `ioctl`, `io_uring_setup`, `io_uring_enter`, or
  `io_uring_register` call is rejected with one plan-fixed sanitized failure.
  Ambiguous or malformed results fail closed as invalid trace. This preserves
  normal failed terminal `ioctl` probes without permitting a successful ioctl
  allowlist.
- Keep the exact three provider operations, two inode-bound `chmod` allowance,
  process-lineage rules, default-profile prohibition, generic write
  confinement, private-channel precedence, filesystem proof, evidence schema,
  and every service/revision/account binding unchanged.

The verification write set remains
`tools/automation/test_m5_codex_containment.py`, the inventory assertions in
`tools/automation/test_m5_current_exit.py`, and only the exact count/digest
constants in
`tools/automation/implementations/auto_m5_current_exit.py`. Documentation may
change only in the already authorized 1.11 locations and generated planning
controls. There is no public contract, API, UI, database, migration,
dependency, license, provider-payload, login, account, scheduler, or service
behavior change.

### Required Red, Green, and live proof

The existing real tests are the Red: the old exact selector does not record
the successful fd-xattr or inode-flag changes, and pure policy accepts the
constructed successful inode-flag record. Green must use the installed
root-owned strace and private temporary files to prove the new exact selector
records `fsetxattr`, `fremovexattr`, and `ioctl`, records safe no-effect or
private-temp `io_uring` activity, and exposes no test xattr value or ioctl
buffer in the trace. Pure policy cases must prove every successful or
ambiguous raw-call record fails closed, while exact failed raw calls are
treated as no effect and do not create a false pass.

The full focused containment and current-exit suites, Ruff, format, strict
mypy, exact Story inventory rebind, complete canonical preactivation gates,
and independent review are required. The safe authenticated containment rerun
must then pass against the unchanged `d81afab` service with the pinned Codex
0.160.0 executable. Only after that pass may the already authorized fifth
activation proceed. The final clean exact-revision `AUTO-M5-EXIT` must include
the same real containment test with zero skips. M5 remains Intermediate until
that receipt exists and survives canonical rereads.

### Local implementation checkpoint — 2026-10-22

The exact selector and raw qualifier now cover all six calls in both the
root-owned strace prerequisite probe and the production trace. Pure policy
rejects successful calls globally, rejects malformed results as invalid, and
retains exact failed calls as no effect without dropping process chronology.
Real temporary-file proof records fd xattrs and inode-flag ioctl in raw numeric
form without the private xattr name, value, or decoded ioctl buffer. Safe raw
io_uring calls are visible to the selector.

The complete local containment file passes `64` cases and `202` subtests; its
one authenticated case is skipped only because the explicit live selectors
are absent. The current-exit file passes `66` cases. Ruff lint, Ruff format,
strict production mypy, and `git diff --check` pass. Independent review found
and the implementation corrected strict-result and post-exit chronology gaps.
The exact canonical Story inventory is now `514` unique test identifiers with
SHA-256
`fd9c6c87d07e1ab759a2a2db23c8d6cd3997d416687784e4c13525ac8e2cf1bd`.
No service, browser, provider profile, account, or running agent was changed by
this local checkpoint. Canonical preactivation and authenticated containment
against the unchanged d81 service remain required before activation.

## Approved descriptor-bound `ftruncate` correction — 2026-10-22

**Status: Owner-approved 1.13.0 on 2026-10-22. This correction is folded into
the already authorized, not-yet-run fifth rollover; it does not authorize a
sixth rollover or any additional provider operation.**

### Authenticated Reds and closed boundary

The complete local preactivation set passed on clean revision `b64bbb5`,
including build, planning, documentation, quality, mutation, Git preflight,
`307` M3 technical tests, and `AUTO-TEST` with `1361` backend tests plus its
real browser sequence. The first standalone authenticated containment rerun
against the unchanged clean d81 service then failed closed at
`m5_codex_containment_result_channel_empty`. A real descriptor Red proved that
the private-channel parser admitted only single-digit descriptors beginning at
three and descriptors whose first digit was three through nine, while an
ordinary inherited descriptor such as `10` was rejected. The approved 1.11
private-channel scope corrects that grammar to exact decimal descriptors
`3..999999`; the focused Red and Green use real inherited kernel descriptors.

With that channel correction, the same live test completed the real identity
and quota operations and failed closed at
`m5_codex_containment_fd_write_unverifiable`. Sanitized structural inspection
of the same raw trace found exactly ten successful `ftruncate` records: five
in identity lineage and five in quota lineage, across five distinct relative
targets. Every descriptor had an strace `-yy` absolute normalized path inside
the selected managed profile; the exact length argument was decimal `3`.
There were no default-profile, outside, deleted, relative, malformed, or
unresolved targets, no unattributed successful fd mutator, and no other
successful fd-only mutator. All `284` observed raw `ioctl` records were exact
failed no-effect terminal probes. No path, alias, provider payload, prompt,
response, token, or credential value was retained or placed in evidence.

These calls are the fd form of a managed-profile write already permitted for
identity and quota. The 1.11 policy nevertheless rejects every successful
fd-only mutator before it can apply managed-root confinement. That literal
approved boundary cannot be widened without this amendment. The live test
remains Failed and no containment, activation, or completion pass is claimed.

### Exact proposed correction

Production changes remain limited to
`tools/automation/implementations/m5_codex_containment.py`:

- Keep the exact 1.12 trace selector and raw qualifier unchanged.
- Before the existing recursive pre-tree scan, and before releasing the
  selected input to the traced driver, bind the check to the real Linux mount
  namespace. Capture a bounded, strictly parsed
  `/proc/self/mountinfo` plus the `(device, inode)` identity of
  `/proc/self/ns/mnt`; after starting `strace`, while its driver is still
  blocked on the private input channel, capture the same values through
  `/proc/<strace-pid>` and require the namespace identity to match. Require
  that the deepest mount covering the managed-profile root has the same mount
  ID, parent ID, device, mount root, and mount point in both views, and that
  neither view contains a mount point equal to or below the managed-profile
  root. Repeat the self view after the driver exits but before the recursive
  post-tree scan, and require the same namespace identity, covering mount, and
  absence of nested mount points.
  Missing, changing, oversized, duplicate, noncanonical, or malformed proc
  data fails closed as
  `m5_codex_containment_mount_topology_unverifiable`, without a path or raw
  proc value in the error or evidence, before any `ftruncate` can be admitted.
  Provider-created mount namespaces and mount operations remain covered and
  rejected by the unchanged complete syscall trace.
- Parse every `ftruncate`, including an exact failed call, only when its
  arguments are exactly one decimal descriptor in `3..999999`, one
  nonempty strace `-yy` descriptor-path annotation, and one nonnegative decimal
  length in `0..9223372036854775807`, each with no leading zero except the
  literal `0`. The path content must contain no CR, LF, NUL, angle bracket, or
  backslash, must be absolute, and must be unchanged by lexical normalization.
  Reject leading-double-slash, dot or `..` components, escaped,
  suffix-bearing, prefix-bearing, and ambiguous forms as invalid trace. Treat
  a syntactically identifiable missing or `(deleted)` descriptor annotation as
  `m5_codex_containment_fd_write_unverifiable` because it cannot prove the
  inode-bound target.
- Admit that successful record only when its PID belongs to the identity or
  quota provider lineage and the resolved descriptor path is within the exact
  selected managed-profile root. Count it as one provider access and one
  provider write under the existing generic managed-write confinement.
  A valid path in a default Codex root fails under the existing
  `m5_codex_default_profile_access_detected` policy; any other valid path
  outside the managed root fails as
  `m5_codex_managed_profile_write_escape`; a successful
  unattributed or version-lineage call fails as
  `m5_codex_containment_fd_write_unverifiable`.
- After that complete argument validation, treat only an exact
  `-1 ERRNO (...)` `ftruncate` result as no effect while retaining its record
  for ended-PID and closed-operation chronology. Exact `0` is the only success;
  every positive, restarted, unknown, suffix-bearing, prefix-bearing, or
  otherwise malformed result is invalid trace.
- Continue to reject successful `fchmod`, `fchown`, `fallocate`, fd xattrs,
  every successful raw call, and every other fd-only mutator. Keep the two
  inode-bound `chmod` allowance, root/tree snapshots, hard-link rejection,
  default-profile prohibition, process rules, private-channel precedence,
  evidence schema, service binding, account binding, and provider operations
  unchanged.

`ftruncate` acts on the open descriptor's inode, while strace `-yy` supplies a
namespace path rather than an inode identity. The new mount proof therefore
excludes a pre-existing bind mount at or below the managed root before relying
on that path. Together with the existing before/after tree scans, single-link
regular-file rule, global link rejection, protected-target rename/unlink
rejection, and namespace-operation rejection, this closes the descriptor-path
boundary under the documented single-user threat model. The existing
hostile-concurrent-same-UID limitation remains unchanged.

The verification write set remains
`tools/automation/test_m5_codex_containment.py`, inventory assertions in
`tools/automation/test_m5_current_exit.py`, and only the exact count/digest
constants in
`tools/automation/implementations/auto_m5_current_exit.py`. Documentation may
change only in the already authorized M5 evidence/status/runbook locations and
generated planning controls. There is no public contract, API, UI, database,
migration, dependency, license, provider-payload, login, account, scheduler,
or service behavior change.

### Required Red, Green, review, and live proof

The authenticated failures above and the real multidigit-descriptor case are
the Reds. Pure policy tests must cover identity and quota admission plus
unattributed, version, default-root, outside-root, relative, double-slash,
`..`, deleted, missing-annotation, escape-bearing, control-bearing,
delimiter-bearing, descriptor boundaries `0`, `1`, `2`, and `1000000`,
leading-zero descriptor or length, length boundaries `0`,
`9223372036854775807`, and `9223372036854775808`, negative length,
positive/ambiguous/malformed result, suffix/prefix, failed-after-exit, and
every still-forbidden fd mutator. A real temporary-file strace test must prove
the exact `-yy` annotation for an ordinary private target and prove
delimiter-like or escaped filename content fails closed without persisting its
path. A real isolated user and mount namespace test must create an actual bind
mount beneath a private temporary managed root and prove the mount check rejects
it; a real `/proc` test must prove the ordinary current/traced namespace is
accepted. Pure parser cases must cover bounded canonical mountinfo, namespace
identity mismatch, covering-mount drift, nested file and directory mounts,
missing or malformed proc data, and mountinfo escape and delimiter boundaries.
The inherited-channel cases must cover a real open descriptor above nine plus
closed, leading-zero, and out-of-range descriptor values.

Green requires the complete containment and current-exit files, Ruff, format,
strict mypy, exact Story inventory rebind, independent review, and the full
canonical preactivation set on one clean revision. The standalone
authenticated containment test must then pass, with no skip, against the
unchanged d81 service and pinned Codex 0.160.0 executable. Only after that pass
may the already authorized fifth activation proceed. The final clean
exact-revision `AUTO-M5-EXIT` must include the same live case with zero skips.
M5 remains Intermediate until its private completion receipt exists and
survives canonical rereads.

### Local implementation checkpoint — 2026-10-22

The 1.13 implementation now validates every mountinfo row, permits only
canonical absolute roots or bounded `nsfs` namespace roots, binds the current
and actual blocked `strace` process views to namespace, mount, PID, and start
identity, and rejects any mount at or below the selected managed profile. It
admits only the closed descriptor-bound `ftruncate` grammar and confines each
successful provider-lineage target to the selected managed root. Process
cleanup holds a pidfd-bound new-session leader until its whole process group is
signalled, uses one shared settlement deadline, and then reaps the leader.

The complete containment file passed `76` cases: `75` local cases passed and
the one authenticated case was explicitly skipped because its live selectors
were absent. The current-exit file passed `66` cases. Ruff lint and format,
strict production mypy, and `git diff --check` passed. Two independent final
reviews reported no remaining 1.13 blocker. The exact canonical Story
inventory remains `525` unique identifiers with SHA-256
`99c3b5f579aac5091939209c8f3603f88a283bb3a4444dbdfa10f8f1d91de15f`.
These are provider-free implementation results. The complete canonical
preactivation set, authenticated zero-skip containment against the unchanged
d81 service, fifth activation, refreshed live prerequisites, `AUTO-M5-EXIT`,
and owner acceptance remain Not Run.

## Authenticated numeric-dirfd trace correction — 2026-10-22

The complete preactivation set passed on clean revision `87eb40d`. The
standalone authenticated containment run then completed the real identity and
quota provider operations against the unchanged `d81afab` service before trace
evaluation failed closed as `m5_codex_containment_trace_invalid`. Sanitized
structural inspection identified one successful write-class `unlinkat` record
with one quoted relative target, one required numeric directory descriptor
annotated by `strace -yy`, and no `AT_FDCWD` token. No path, provider payload,
identity, credential, prompt, or response was retained. A separate real
owner-temporary-file probe reproduced the installed strace 6.8 form as
`unlinkat(3<ABS>, "REL", 0) = 0`.

This is a trace-representation defect in the already approved generic
managed-profile write confinement. It adds no provider method, operation,
side effect, contract, schema, dependency, or service transition and therefore
does not create plan 1.14. The correction parses only exact `unlinkat`
signatures. A relative target uses either literal `AT_FDCWD` with the tracked
working directory or a decimal descriptor `3..999999` with one canonical
absolute normalized annotation. Missing, deleted, relative, escaped,
control-bearing, noncanonical, or ambiguous annotations and results fail
closed. Default-profile and outside-profile targets retain their existing
specific failures, and replacement of the inode-bound `chmod` target or an
ancestor remains rejected. Other numeric-dirfd syscall signatures remain
unresolved and fail closed.

Red reproduced both the pure policy failure and the real temporary-filesystem
trace failure. Green at production-code commit
`f1c2c2e9a7f4434c49014646bff220273282603b` passes `77` containment cases:
`76` local cases and one explicit authenticated-selector skip. Current-exit
passes `66/66`; Ruff and format, strict production mypy, and `git diff --check`
pass for the changed containment files. Two independent adversarial reviews
are clean. The exact Story inventory is `526` unique identifiers with SHA-256
`5b3c8dcbdcdff7303e7364417b6d7d5c6bd4efd3286fba48ba885bcf0bdd968e`;
removing only the new real-strace test reproduces the prior `525` count and
digest. Current-revision preactivation and the corrected authenticated rerun
remain required before the already approved fifth activation.

## Approved pinned Arg0 symlink lifecycle correction — 2026-10-22

**Status: Owner-approved 1.14.0 on 2026-10-22. This approval authorizes only
the successful symlink lifecycle below and remains folded into the already
authorized, not-yet-run fifth rollover; it authorizes no sixth rollover.**

### Authenticated Red and exact provider behavior

The complete canonical preactivation set passed on clean revision
`a0f2dc16e2330c048d652845f20b2585bcf64c5e`: planning, documentation, build,
quality, mutation, M3, `AUTO-TEST`, and local Git preflight were Green. The
standalone authenticated containment test then completed the real identity and
quota operations against the unchanged d81 service before failing closed as
`m5_codex_default_profile_access_detected`.

Privacy-safe in-memory classification found eight successful plain `symlink`
records. All eight first arguments were absolute strings in the pinned Codex
installation release; all eight created-link paths were absolute paths inside
the selected managed profile. Directional parsing then proved that the first
argument was payload text and the second was the created path. Its focused Red
and Green preserve the approved global-link rule, and the same real run now
fails at the more precise `m5_codex_containment_link_operation_rejected`.
There was no access to default account, configuration, or runtime state and no
default-root write; only the already allowed pinned installation reads were
observed.

A second bounded live classification, retaining no path or provider payload,
proved the exact lifecycle: four successful links in the identity root process
and four in the quota root process; every payload equalled the retained pinned
provider executable; each operation created exactly the closed four-alias set
below beneath one managed session parent; and every created path had a later
matching successful cleanup unlink. The bounded post-run managed-tree scan
succeeded and therefore found no retained symlink. It did not require the full
tree digest to remain equal because the already approved managed-auth
lifecycle may update ordinary managed-profile state.

The [official `rust-v0.160.0` Arg0 implementation](https://github.com/openai/codex/blob/rust-v0.160.0/codex-rs/arg0/src/lib.rs#L214-L452)
corroborates this result. Before the app-server async body begins, Arg0 creates
a temporary directory below managed `CODEX_HOME/tmp/arg0`, obtains the current
executable, creates four aliases, retains the temporary-directory guard for the
app-server lifetime, and removes the directory when the body returns. The
pinned `tempfile 3.27.0` name has literal prefix `codex-arg0` plus exactly six
ASCII alphanumeric characters. Linux creation order is:

1. `apply_patch`;
2. `applypatch`;
3. `codex-linux-sandbox`;
4. `codex-execve-wrapper`.

Cleanup enumeration order is filesystem dependent and is not an accepted
ordering signal. The reviewed official app-server and configuration
documentation exposes no supported switch that removes this setup. Moving
temporary state elsewhere would change the provider environment and would not
prove the production managed-profile boundary.

Plan 1.13 explicitly retains global link rejection. Admitting these eight real
successful calls therefore changes policy and cannot be treated as another
trace-format correction.

### Exact proposed correction boundary

Production change is limited to
`tools/automation/implementations/m5_codex_containment.py`:

- Parse plain `symlink` with an exact full-match two-string grammar and exact
  result grammar. The first argument is opaque link payload text and is never
  classified as a filesystem access or write by the syscall. The second
  argument is the created path and remains a managed-profile access, write,
  and namespace-replacement target. Empty, truncated, escaped, control-bearing,
  noncanonical, suffix-bearing, prefix-bearing, ambiguous, or malformed forms
  fail closed without exposing either string.
- Admit successful plain `symlink` only in the root PID of each of the exact
  ordered identity and quota app-server operations. Descendant, version,
  pre-provider, post-operation, overlapping, or additional provider processes
  cannot use the exception.
- Require exactly four successful records per operation, in the fixed creation
  order above. Each payload must equal the already retained, inode-validated
  provider executable exactly. Merely being inside its installation release
  is insufficient.
- Require every created path to be an absolute canonical strict descendant of
  the selected managed profile with exactly these four relative components:
  literal `tmp`, literal `arg0`, exact
  `codex-arg0[A-Za-z0-9]{6}`, and the corresponding alias basename. All four
  paths for one operation must have the same session parent and unique alias.
  No dot, `..`, leading-double-slash, separator-bearing component, control
  byte, alternate case, alternate alias, additional component, or second
  session parent is accepted.
- Require one matching successful cleanup `unlinkat` for every admitted
  created path. The cleanup PID must belong to the same identity or quota
  operation lineage as that link; either its root or a traced descendant may
  perform cleanup. Preserve syscall invocation and successful-completion order
  separately across complete and `<unfinished ...>`/`<... resumed>` records.
  Each link must complete successfully before its cleanup is invoked or
  completes, and cleanup must complete before that operation invokes
  `exit`/`exit_group`. Invocation position alone is insufficient. Reject an
  unresolved or ambiguous interleaving, but accept any proven cleanup order
  among the four aliases. A cleanup from another operation or unattributed
  process, before create, after operation close, against a different path,
  missing, duplicate, or unresolved through its directory descriptor fails
  closed. The existing numeric-dirfd parser and managed-root confinement apply
  unchanged.
- From each successful creation through its matching cleanup, reject every
  namespace operation that names an admitted alias path or its session parent,
  or that can move or exchange the link inode, except that alias's one exact
  cleanup `unlinkat` and ordinary removal of the now symlink-free session
  directory after all four alias cleanups. In particular, reject `rename`,
  `renameat`, `renameat2`, `RENAME_EXCHANGE`, link, unlink, or parent movement,
  even when every lexical path remains inside the selected managed profile.
- Require the existing bounded post-operation tree snapshot to remain
  symlink-free. The selected profile root, its private enclosing roots, the
  inode-bound `chmod` target and its ancestors, mount topology, auth-store
  metadata, service identity, executable identity, and account identity retain
  all existing checks. The existing concurrent-hostile-same-UID limitation is
  unchanged.
- Continue rejecting every hard link, `symlinkat`, any plain symlink outside
  this exact eight-record lifecycle, and every link that names a default or
  outside created path or affects the protected target or an ancestor. The
  exception grants no read or write under the default Codex profile. Resolved
  writable opens, fd mutators, namespace operations, and all other path
  mutations retain their existing fail-closed policies.
- Count each admitted record once as a managed provider access and write. Keep
  the closed evidence schema and digest-only sanitized output unchanged; no
  path, alias, session component, PID, raw trace, provider payload, identity,
  credential, prompt, response, or source content enters evidence or logs.

No provider method, API, UI, database, migration, scheduler, service
transition, dependency, license, login, account, default profile, or running
agent behavior changes. This amendment remains folded into the already
authorized, not-yet-run fifth rollover and authorizes no sixth rollover.

The verification write set is limited to
`tools/automation/test_m5_codex_containment.py`, inventory assertions in
`tools/automation/test_m5_current_exit.py`, and the exact inventory constants
in `tools/automation/implementations/auto_m5_current_exit.py`. Documentation
may change only in the existing M5 plan, Codex adapter boundary, implementation
evidence/status, runbook, plan indexes, and generated planning controls.

### Required Red, Green, review, and live proof

The authenticated `m5_codex_containment_link_operation_rejected` result is the
real Red. Pure policy tests must prove the exact four-plus-four admission and
reject missing, extra, duplicate, reordered, wrong-alias, wrong-source,
other-release-source, relative-source, mixed-parent, malformed-session,
relative-destination, default-destination, outside-destination,
version/unattributed/descendant lineage, successful hard-link or `symlinkat`,
failed or malformed result, cleanup-before-create, cleanup-after-exit,
wrong-operation or unattributed cleanup, missing/duplicate/wrong/unresolved
cleanup, cleanup invoked before create but resumed after, cleanup invoked
before exit but resumed after exit, symlink unfinished/resumed across operation
boundaries, alias rename out and back, alias `RENAME_EXCHANGE`, session-parent
rename, final-clean-tree movement, and protected-target or ancestor replacement
cases. Exception text and evidence representations must contain no payload or
path.

A real owner-temporary-filesystem strace test must prove Linux plain-symlink
argument direction and descriptor-annotated cleanup without retaining its
path. A real tree test must prove a remaining symlink is rejected. The complete
containment and current-exit files, Ruff lint and format, strict production
mypy, exact Story inventory rebind, `git diff --check`, and two independent
adversarial reviews must pass.

The full canonical preactivation set must then pass on one new clean revision.
The standalone authenticated containment test must pass with no skip against
the unchanged d81 service and pinned Codex 0.160.0 executable. Only after that
pass may the already authorized two-invocation fifth activation begin. Fresh
owner, alert, process, and quota evidence and the exact-revision
`AUTO-M5-EXIT` remain required. This amendment is not M5 completion or owner
acceptance.

### Plan 1.14 local implementation checkpoint

The unchanged d81 service supplied the real Red
`m5_codex_containment_link_operation_rejected` after identity and quota both
completed. The implementation now admits only the exact four ordered Arg0
aliases for each operation and their same-operation cleanup. It preserves
syscall invocation and completion chronology, rejects overlapping unfinished
working-directory changes, rejects leading-double-slash path and successful
open annotations, and fails closed on any successful unowned write overlapping
the protected Arg0 lifecycle. These last checks prevent lexical aliases such as
Linux proc-root paths from bypassing the inode-movement boundary.

The provider-free containment file reports `88` cases: `87` pass and the one
authenticated selector case is explicitly skipped and receives no completion
credit. Current-exit passes `66/66`; Ruff check and format, strict production
mypy, and `git diff --check` pass. The exact Story inventory is `537` unique
identifiers with SHA-256
`19d4244cfd50335839776af9b847af134eba0451c3dee2ad66d0daa9e321ec2d`.
Independent test and implementation reviews are clean after their findings
were reproduced as Reds and corrected. At this local checkpoint the canonical
clean-revision preactivation set and authenticated no-skip containment rerun
remained pending; the subsequent results below supersede that status. This
checkpoint is not M5 completion.

## Approved pinned Arg0 lock-child lifecycle correction — 2026-10-22

**Status: Owner-approved 1.15.0 on 2026-10-22. This approval adds only the exact
session creation and `.lock` lifecycle below to the already authorized,
not-yet-run fifth rollover and authorizes no sixth rollover.**

### Authenticated Red and exact provider behavior

Clean revision `842a4d4da20b1286d4d68b03b46f88a9cd66504e` passed the
complete canonical preactivation set: planning, documentation, build, quality,
mutation, M3, `AUTO-TEST`, and local Git preflight were Green. Its first
authenticated containment rerun completed the real provider work and failed
closed at `m5_codex_containment_path_mutator_unverifiable` on a failed
same-operation `mkdir(...)= -1 EEXIST (File exists)`. That record has no
namespace effect, and its narrowly bounded correction remains inside the
approved 1.14 lifecycle.

The authenticated feedback rerun after that correction again completed the
real provider work and returned the same fail-closed code. A privacy-safe
in-memory classification identified the first remaining record as one
successful cleanup of a literal `.lock` regular-file child directly beneath
the identity operation's already admitted Arg0 session directory. The cleanup
was `unlinkat` with an annotated directory descriptor resolving to that
session, the literal single child component `.lock`, flags exactly `0`, and
result exactly `0`. A traced descendant in the same identity operation invoked
it after all four aliases were created, after three alias cleanups completed,
before the fourth alias cleanup, and before descendant and root exit.

The matching creation was one successful `open` by the identity operation's
root process. Its path was the same absolute session child; flags were exactly
`O_RDWR|O_CREAT|O_LARGEFILE|O_CLOEXEC`, mode exactly `0666`, and its successful
descriptor result carried the same absolute-path annotation. The call
completed before the first alias creation and before any cleanup. The bounded
classification retained only these structural facts. A second bounded
cardinality check confirmed that identity and quota each had exactly one such
root `open` and one matching descendant `unlinkat`, with identical shapes and
cleanup positions: after three alias cleanups and before the fourth. It
also confirmed one structurally identical session creation per operation:
exactly one successful complete root-process `mkdir` with the absolute session
path, mode exactly `0777`, and result exactly `0`. Each `mkdir` completed before
its `.lock` open was invoked. From that `mkdir` invocation through the `.lock`
open completion, the only successful writes overlapping the interval were the
equal-session `mkdir` and equal-child `open`. The classification retained no
path, PID, identity, provider payload, credential, prompt, response, or source
content, and the raw trace was discarded.

The [official `rust-v0.160.0` Arg0 source](https://github.com/openai/codex/blob/rust-v0.160.0/codex-rs/arg0/src/lib.rs#L25-L43)
defines `LOCK_FILENAME` as literal `.lock` and retains both the temporary
directory and opened file in `Arg0PathEntryGuard`. Its
[session and lock creation path](https://github.com/openai/codex/blob/rust-v0.160.0/codex-rs/arg0/src/lib.rs#L378-L390)
creates the temporary session, opens its lock child with read, write, create,
and no-truncate options, then calls `try_lock()`. The guard remains alive
through the app-server async body and is dropped afterward. The current syscall
selector observes the exact session creation, file creation/open, and cleanup
lifecycle but does not select `flock` or `fcntl`. This amendment therefore
makes no claim about advisory-lock acquisition and does not widen the selector
or acceptance scope to prove it.

Plan 1.14 admits only the four symlink children and their cleanup, followed by
optional removal of an empty session directory. The real `.lock` cleanup is a
fifth child mutation during that protected interval, so admitting it changes
policy and requires owner approval rather than being treated as trace syntax.
At approval, no authenticated containment run had passed for 1.14 or 1.15.

### Exact proposed correction boundary

Production change is limited to
`tools/automation/implementations/m5_codex_containment.py`:

- Require each exact identity and quota app-server operation to contain one
  and only one literal `.lock` regular-file child directly beneath that
  operation's single already admitted `tmp/arg0/codex-arg0[A-Za-z0-9]{6}`
  session. Both operations must independently satisfy the complete lifecycle;
  an observation from one operation cannot authorize or satisfy the other.
- Require exactly one successful complete session-creation record per
  operation: `mkdir("<absolute-session>", 0777) = 0` by that operation's root
  PID. Its absolute canonical target must equal the one session parent shared
  by the later `.lock` and four aliases. It must be invoked after operation
  start, complete before `.lock` open invocation, and remain a complete record
  rather than an unfinished/resumed pair. Exact zero proves that this session
  path did not already exist when `mkdir` created it.
- Admit the child creation only as one exact full-match `open` by that
  operation's root PID, with one absolute canonical path equal to
  `<session>/.lock`, flags exactly
  `O_RDWR|O_CREAT|O_LARGEFILE|O_CLOEXEC`, mode exactly `0666`, and a successful
  nonnegative descriptor result whose path annotation resolves exactly to the
  same canonical child. The call must be invoked and completed after the
  session `mkdir` completes and before its first alias creation. From the
  session-creation invocation through `.lock` open completion, the only
  successful writes that may overlap are the exact equal-session `mkdir` and
  exact equal-child `open`. This closed interval proves a fresh session with no
  preceding child or alternate creator and supplies the regular-file creation
  proof despite `open` lacking `O_EXCL` and `O_NOFOLLOW`.
- Reject a missing, failed, duplicate, relative, leading-double-slash,
  malformed, alternate-name, wrong-session, wrong-mode, wrong-result,
  descendant, other-operation, or non-root session `mkdir`; `mkdirat` or any
  other creation call; a session creation invoked before operation start or
  after `.lock` open; and an unfinished/resumed session creation. Reject every
  additional successful write overlapping session-creation invocation through
  `.lock` open completion, plus any failure-reporting namespace mutation whose
  effect the existing policy cannot prove absent.
- Reject `openat`, `openat2`, `creat`, any second open/create, a relative or
  leading-double-slash path, another basename or case, another directory or
  session, a nested child, missing or reordered flags, additional flags,
  another mode, failed/unknown/malformed result, missing/mismatched/deleted
  descriptor annotation, another PID or operation, and creation after any
  alias creation or cleanup. Reject `.lock` creation by `mkdir`, `mknod`, hard
  link, symlink, rename, or any other entry type or namespace operation.
- Require exactly one matching successful cleanup
  `unlinkat(<annotated-session-dirfd>, ".lock", 0) = 0`. The directory
  descriptor must resolve exactly to the same session; the caller must be the
  root or a traced descendant of the same operation; creation must complete
  before cleanup is invoked; all four alias creations must complete before
  cleanup is invoked; and cleanup must complete before that actor and the
  operation root invoke exit. A different operation, unattributed process,
  absolute or alternate child argument, unresolved or mismatched descriptor,
  other flags/result, cleanup before create, duplicate cleanup, missing
  cleanup, or cleanup after actor/root/operation close fails closed.
- Permit the one `.lock` cleanup to interleave in any proven order among the
  four already required alias cleanups because temporary-directory enumeration
  order is filesystem dependent. Require all five child cleanups to complete
  successfully before the existing optional exact session-directory
  `rmdir`/`unlinkat(..., AT_REMOVEDIR)` may be invoked. Session removal before
  any child cleanup, or a remaining child after removal, fails closed.
- Extend the protected Arg0 interval from invocation of the exact session
  `mkdir` through completion of all five child cleanups. During that interval
  reject every unowned successful write, session or child movement,
  replacement, exchange, additional link, write-through alias, any `.lock`
  access beyond the one exact open and one exact cleanup unlink, and ancestor
  mutation already forbidden by 1.14. Invocation and completion ordinals
  remain authoritative across complete and unfinished/resumed records; lexical
  path containment alone is insufficient.
- Count the admitted session `mkdir`, `.lock` `open`, and `.lock` `unlinkat`
  once each as managed provider access and write. Keep the bounded
  post-operation symlink-free tree check, selected managed-root confinement,
  executable/account/service identity, mount and inode protections,
  default-profile prohibition, and every other 1.14 check unchanged. Keep the
  closed evidence schema and digest-only sanitized output unchanged; neither
  `.lock` nor any path, descriptor, PID, trace line, or provider value enters
  evidence or logs.

No provider method, API, UI, database, migration, scheduler, service unit,
login, account, default profile, dependency, license, or running-agent behavior
changes. There is no public or versioned contract change and no ADR or data
migration. The amendment remains part of the already approved fifth
evidence-preserving rollover and authorizes no additional activation.

The verification write set is limited to
`tools/automation/test_m5_codex_containment.py`, inventory assertions in
`tools/automation/test_m5_current_exit.py`, and exact inventory constants in
`tools/automation/implementations/auto_m5_current_exit.py`. Documentation may
change only in the existing M5 plan, Codex adapter boundary, implementation
evidence/status, runbook, plan indexes, and generated planning controls.

### Required Red, Green, review, and live proof

The authenticated
`m5_codex_containment_path_mutator_unverifiable` result on the exact successful
`.lock` cleanup is the real-system Red. The first focused policy test must
reproduce that failure before production changes. Pure policy tests must then
prove the exact session creation, one-plus-four child creation, and five-child
cleanup lifecycle for both identity and quota, including `.lock` cleanup at
every permitted position among the four alias cleanups.

Negative cases must reject a missing, extra, duplicate, renamed, wrong-case,
wrong-path, nested, nonregular, moved, replaced, or exchanged `.lock`; wrong
call, PID, operation, lineage, flag set/order, mode, result, descriptor
annotation, or chronology; missing, duplicate, wrong-call, wrong-path,
wrong-mode, failed, foreign-lineage, pre-operation, post-open, or
unfinished/resumed session creation; any additional successful write
overlapping session-create invocation through lock-open completion, including a
write invoked before session creation and resumed inside the interval or
invoked inside it and resumed after lock-open completion; open before session
creation completes or after alias creation; cleanup before open completion or
before all alias creations; cleanup after actor/root exit; cleanup from another
session or operation; duplicate or unresolved cleanup; session removal before
any of the five child cleanups; and unfinished/resumed calls crossing operation
or exit boundaries. Regression tests must retain all 1.14 rejections, including
failed-reporting rename variants whose filesystem effect can be uncertain.

A real owner-temporary-filesystem strace test must prove the exact complete
Linux session `mkdir`, `open` flags/mode/successful descriptor annotation, and
descriptor-resolved `unlinkat` grammar without retaining a path. A real tree
test must prove that a remaining `.lock`, symlink, or other session child is
rejected. These tests do not claim that `try_lock()` succeeded because its
syscall is outside the unchanged selector.

After focused Green, the complete containment and current-exit files, Ruff
lint and format, strict production mypy, exact Story inventory rebind,
`git diff --check`, and two independent adversarial reviews must pass. The
standalone authenticated containment test should then run as a feedback gate
with no skip against the unchanged d81 service and pinned Codex 0.160.0
executable. Its pass must prove the complete exact lifecycle independently for
both identity and quota.

The correction must then be committed as one clean revision, and the full
canonical preactivation set must pass on that exact revision. The standalone
authenticated containment test must pass again with no skip against that exact
revision before the already authorized two-invocation fifth activation begins.
Fresh owner, alert, process, and quota evidence and exact-revision
`AUTO-M5-EXIT` remain required afterward. Until all of those gates pass, M5,
plan 1.15, live containment, activation, and owner acceptance remain Not Run or
Failed as their actual results require.

### Plan 1.15 implementation feedback checkpoint

The first frozen implementation checkpoint passed `96` provider-free
containment cases, with one authenticated live-selector case explicitly
skipped and receiving no completion credit, across `552` subtests. Current-exit
passed `66/66`; Ruff lint and format, strict production mypy, and
`git diff --check` were Green. Two independent pre-live reviews were CLEAN
after their findings had first been reproduced as Reds and corrected.

The first authenticated 1.15 feedback run used the unchanged d81 service and
the pinned Codex `0.160.0` executable. Both provider operations reached the
line guard, which failed closed because the implementation's broad Arg0 guards
began at app-server execution. A privacy-safe in-memory classification retained
only structural facts: before each operation's exact session creation, the
official implementation attempted `mkdir(arg0_root, 0777)`, received
`EEXIST`, and then completed the already approved
`chmod(arg0_root, 0700)`. It retained no path, PID, account identity, provider
payload, credential, prompt, response, source content, or raw trace.

The focused policy test first failed on that exact official pre-session setup.
The correction leaves both calls under ordinary confinement and changes only
the two broad Arg0 guards: each now begins at the exact session `mkdir`
invocation and ends after the final fifth-child cleanup completes. Negative
records invoked in or crossing that interval remain rejected; the valid
pre-session root setup completes before it and receives no new lifecycle
exception.

After the correction, the complete containment file passed `97` provider-free
cases, with the one uncredited live-selector skip, across `558` subtests.
Current-exit remained `66/66`; Ruff lint and format, strict production mypy,
and `git diff --check` were Green. The exact Story inventory is `547` unique
identifiers with SHA-256
`3a97e0103ae4ba3390d10567c9130821abaa7a5a7e9640cf0091bc56a49b6a0c`.
The focused post-correction official-source and code reviews were CLEAN.

The second authenticated feedback run then passed with zero skips: `1 passed
in 3.79s` against the unchanged d81 service and pinned Codex `0.160.0`. This is
feedback against the working implementation. The correction still must be
committed as one clean revision, the complete preactivation set and standalone
authenticated test must pass again on that exact revision, and the fifth
activation plus refreshed prerequisites and `AUTO-M5-EXIT` remain required.
This checkpoint is not activation, milestone completion, or owner acceptance.

## Approved bounded alert-witness scale correction — 2026-10-23

**Status: Owner-approved 1.16.0 on 2026-10-23.**

Plan 1.16.0 incorporates approved 1.15.0 and changes only the two real-system
failures below plus one exact sixth corrective rollover from
`8cc683d946b58f5eb72955e08a520195582e1a28`.

### Current real-system evidence

The fifth rollover activated clean revision
`8cc683d946b58f5eb72955e08a520195582e1a28`. Its complete preactivation set,
zero-skip authenticated containment rerun, two-stage service transition, fresh
four-account owner outcome, and a genuine post-confirmation Codex alert
opening, repeated delivery, owner acknowledgement, and recovery all passed.
The dashboard remained HTTP 200 on the exact receipt-bound service.

`AUTO-M5-ALERT-WITNESS` then exposed two independent defects:

1. The writer searched the complete capacity outbox for three source event
   IDs. At the observed snapshot the owner database held more than `36,000`
   capacity events and matching commit receipts. Every decoded event performed
   an unindexed `json_each` scan of the receipt set, making this path
   quadratic. A bounded read-only run remained CPU active for more than eleven
   minutes, had performed hundreds of gigabytes of logical reads, and was
   interrupted before create-once output. No witness file existed.
2. The next unchanged canonical run completed that database proof and reached
   the authenticated browser. The versioned API returned all `192` retained
   entries for the selected recovered alert, while the built Alerts page
   requested and rendered only its first `100`. The proof failed closed as
   `selected_alert_history_not_rendered`, surfaced as
   `m5_alert_witness_browser_unavailable`, and again created no witness.

Read-only inspection also found real alert histories beyond one 200-entry
page. Changing only the current `100` limit to `200` would therefore preserve
silent truncation and is outside this approved correction.

### Requirement and scenario binding

- `M5-CDX-ALERT-008` adds and verifies the exact-ID acknowledged-event read
  for `FR-ALERT-004/005`, `AC-ALERT-002`, `NFR-ARCH-002`,
  `NFR-TEST-001/002`, and `AC-TEST-001/003/006`.
- `M5-CDX-UI-013` defines and verifies complete alert-history pagination for
  `FR-HIST-002`, `FR-ALERT-005`, `FR-UI-002/005`, `AC-ALERT-002`,
  `AC-UI-002/005`, and `AC-TEST-001/003/006`.
- `M5-CDX-UI-014` is the authenticated built-browser equality and
  zero-mutation proof for the same requirements and acceptance criteria.
- `M5-SVC-ACT-021` is the exact sixth archive/activation scenario contributing
  `NFR-RES-001`, `NFR-TEST-001/002`, and `AC-TEST-001/003/006` without
  expanding general deployment authority.

Their implementation evidence is appended to
`docs/evidence/m5-codex-implementation.md`; none of these scenario IDs can be
marked Passed until its named real boundary executes on the clean candidate.

### Exact correction boundary

#### Bounded acknowledged-capacity-event lookup

Add the compatible internal M05 facade `ReadAcknowledgedCapacityEventsV1` under
`CTR-CAP-004`. Its repository port is
`CapacityEventEvidenceRepositoryV1.read_acknowledged_capacity_events`, and its
immutable result is `AcknowledgedCapacityEventV1`, containing the existing
typed `DurableEventV1[CapacityCommittedNoticeV1]`,
`acknowledgement_receipt_id: OpaqueIdV1`, and `acknowledged_at: datetime`.
`CTR-EVT-001` event and delivery semantics are consumed unchanged; this
approved correction does not publish or revise a PLAN-INT event contract.

The facade accepts one consumer key matching the existing
`[A-Za-z0-9_.-]{1,64}` grammar, one input-ordered tuple of between one and 200
unique `OpaqueIdV1` event IDs, and one aware UTC `as_of` value. It returns one
result per selector in the caller's exact order. Its closed
`CapacityEventEvidenceErrorV1.code` vocabulary is:

- `capacity_event_evidence_selector_invalid` for an invalid consumer, empty,
  duplicated, over-200, malformed selector tuple, or invalid `as_of`;
- `capacity_event_evidence_event_missing` when any selected event is absent;
- `capacity_event_evidence_delivery_unacknowledged` when its exact consumer
  delivery is absent or not acknowledged; and
- `capacity_event_evidence_invalid` for a wrong event type, incomplete or
  future acknowledgement proof, duplicate/conflicting row, or digest mismatch.

The M5 witness maps `capacity_event_evidence_selector_invalid` and
`capacity_event_evidence_invalid` to its existing
`m5_alert_witness_source_event_invalid`, maps
`capacity_event_evidence_event_missing` to
`m5_alert_witness_source_event_missing`, and maps
`capacity_event_evidence_delivery_unacknowledged` to
`m5_alert_witness_source_event_unacknowledged`. It adds no evidence schema or
public error.

The SQLite implementation must perform one bounded parameterized selection
that resolves `capacity_event_outbox` through its event-ID primary key and
`capacity_event_delivery` through its composite `(event_id, consumer_key)`
primary key. Every selected row must be an available
`capacity.committed.v1` event with an acknowledged delivery, non-null proof,
acknowledgement no later than `as_of`, and acknowledgement payload digest equal
to the independently decoded event digest. Empty, duplicated, over-200,
missing, partial, future, conflicting, malformed, or differently typed
evidence fails closed. Only selected events are decoded; event order,
delivery, replay, acknowledgement, and payload semantics do not change.

For the live witness the selector count is exactly three, the repository may
execute one bounded selection and decode exactly three rows, and
`read_capacity_events` pagination is prohibited. Existing producer-version
resolution may scan `capacity_commit_receipt`/`json_each` at most once for each
of those three selected events; it must never run once per outbox event.
`EXPLAIN QUERY PLAN` must show indexed lookup for both the outbox and delivery
tables. Against the current owner database at its observed
greater-than-36,000-event scale, the exact three-event repository call must
finish within 30 monotonic seconds; timeout, a scan of either indexed table, a
fourth decoded event, more than three producer-version resolutions, or any
whole-outbox traversal fails the focused gate.

The M5 alert witness must replace its full-outbox source lookup and three
full-outbox acknowledgement scans with one targeted query for exactly the
distinct opening, repeated, and recovery source event IDs and fixed consumer
`m07-alert-capacity-v1`. For each stage it must also use M07's existing
published capacity-event receipt lookup and prove equal event ID,
acknowledgement receipt ID, acknowledgement/processed time, and payload
digest. Query results remain in memory. Only the existing sanitized digests
enter the private witness; its schema does not change.

#### Complete cursor-paginated history in the built Alerts UI

Keep the existing `/api/v1/alerts/{alert_id}/history` contract and 200-row
maximum page size. The generated-client wrapper must accept an optional cursor
and request at most 200 entries. The Alerts page must retain the first page,
show a card-scoped **Load more history** control when `has_more` is true,
request exactly the returned cursor, and append entries in API order without
discarding prior entries.

A pure pagination policy must reject missing, empty, control-character,
repeated, or mismatched cursors; terminal pages that retain a cursor;
duplicate event IDs or aggregate sequences; another alert ID; and
non-progressing chronology. Cursor length remains the existing API bound of
one through 1,024 characters. Entries must be strictly ordered by
`aggregate_sequence ASC`, matching M07. A later invalid or unavailable page
preserves the already rendered history and presents a visible error. It never
guesses that the history is complete.

The M5 browser proof must use an all-page API oracle bounded to 200 pages of
200 entries, at most 40,000 unique entries and 199 progressing cursor
transitions after the first page. It validates terminal cursor state and the
unique ascending sequence, then uses only the selected card's history control
for at most 199 clicks until the UI reaches the same terminal sequence. A
nonterminal 200th page, 40,001st entry, over-1,024-character cursor, repeated
cursor, or non-progressing sequence fails closed. The complete rendered count,
order, and digest must equal the API oracle. The proof remains read-only and
requires zero dashboard mutations.

### Authorized files

Production and integration code is limited to:

- `backend/src/agentmonitor/modules/capacity/application/events.py`;
- `backend/src/agentmonitor/modules/capacity/application/queries.py`;
- `backend/src/agentmonitor/adapters/persistence/capacity/sqlite/repository.py`;
- `tools/automation/implementations/m5_codex_alert_witness.py`;
- `frontend/src/shared/api/client.ts`;
- `frontend/src/shared/api/alertHistoryPagination.ts`;
- `frontend/src/features/alerts/AlertsPage.tsx`;
- `tools/ui/m5_registry_pages.mjs`;
- `tools/ui/verify_m5_codex_alert_lifecycle.mjs`;
- `tools/automation/implementations/m5_service_activation.py`;
- `tools/automation/routines.toml`, limited to truthful sixth-rollover catalog
  wording.

Verification and inventory changes are limited to:

- `backend/tests/integration/capacity/test_m4_event_delivery.py`;
- `backend/tests/integration/alerting/test_codex_capacity_lifecycle.py`;
- `tools/automation/test_m5_codex_alert_witness.py`;
- `frontend/tests/pure/alert-history-pagination.mjs`;
- `tools/ui/test_m5_codex_policy.mjs`;
- `tools/automation/test_m5_service_activation.py`;
- `tools/automation/test_m5_current_exit.py`; and
- `tools/automation/implementations/auto_m5_current_exit.py`.

Documentation is limited to this plan, implementation evidence, operations
runbook, affected module/adapter pages, documentation indexes, and generated
planning controls. Any additional production file requires a new approved
amendment.

### Contract, security, and data impact

- `CTR-CAP-004` receives one compatible additive M05 internal read query.
  `CTR-EVT-001` is consumed with unchanged event and delivery semantics.
  `CTR-ALERT-001..005`, REST/OpenAPI fields, generated client schema, private
  witness schemas, and completion receipt schemas do not change.
- Database schema, migration chain, retention, scheduler, alert thresholds,
  provider adapter, provider calls, authentication, collection, quota
  semantics, Registry, and provider profiles do not change.
- No dependency, lockfile, SBOM, notice, licence, compatibility migration, or
  ADR change is required.
- No account identity, provider/profile path, provider payload, prompt,
  response, credential, arbitrary database row, or raw browser material may
  enter logs or evidence.

### Required Red, Green, and review evidence

The retained real Reds are the quadratic owner-database run and the exact
`192` API versus `100` DOM mismatch. Before production changes, focused tests
must also fail because the public M05 boundary cannot read acknowledged events
by exact ID, the pagination policy is absent, and the activation policy does
not reserve `8cc683d` as a sixth rollover revision.

Green must prove on real migrated file-backed SQLite that selector bounds fail
closed; three genuine lifecycle IDs return exactly three input-ordered events
despite decoys; missing or partial delivery proof fails closed; M05 and M07
receipt IDs, times, and payload digests agree; and SQLite query-plan evidence
uses the outbox event-ID and delivery composite primary keys. A real
owner-database scale check must complete without whole-outbox event decoding.

Pure pagination Green covers 192 terminal entries, exactly 200 terminal
entries, 201 entries across two pages, cursor failures, duplicate IDs or
sequences, wrong alert IDs, and non-progressing order. The production build
and authenticated shared browser must render every selected history entry in
API order and perform zero mutations.

The complete affected backend, frontend, witness, browser-policy, activation,
and current-exit suites; Ruff lint/format; strict mypy; frontend typecheck and
build; API compatibility; documentation; planning; mutation; Git preflight;
exact Story inventory; and standalone zero-skip authenticated containment must
all pass on one clean candidate. Independent M05 contract/performance, P02
browser, activation-safety, and security/privacy reviews must be clean.

### Approved sixth evidence-preserving rollover

One sixth corrective rollover is approved from exact revision
`8cc683d946b58f5eb72955e08a520195582e1a28` into fixed namespace
`m5-service-activation-corrective-archive-8cc683d`. The activation policy must
append `8cc683d` as the sixth and final approved rollover revision, require the
five existing archives as an unchanged ordered prefix, and reserve every
completed revision from candidate selection.

The first canonical invocation must validate the complete current transition,
exact service/browser revision, clean detached checkout, Registry and database
identity, rollback runtime, and all five archives. Under the existing
exclusive guard it restores the trusted rollback service, atomically moves the
complete transition directory without replacement into the sixth archive,
fsyncs both parents, and returns the existing status-5 rerun result. The second
invocation must revalidate all six archives and the prepared candidate before
the existing rollback drill and activation. Descriptor, inode, digest,
ownership, mode, link-count, collision, interruption, retry, and trusted
restoration protections remain unchanged. Partial, multiple, unknown,
replaced, linked, colliding, skipped-prefix, dirty-checkout, wrong-service, or
wrong-revision states block without cleanup or replacement.

After activation, the canonical sequence remains: archive stale prerequisites;
create a new service-bound four-account owner outcome; complete one fresh
genuine opening or reopening, distinct repeat, one owner action, and distinct
source-proven recovery; pass `AUTO-M5-ALERT-WITNESS`; refresh genuine quota,
process, and browser evidence; pass `AUTO-M5-QUOTA-WITNESS`; and immediately
pass `AUTO-M5-EXIT`.

### Explicit exclusions

This correction authorizes no seventh rollover, general deployment, event or
history deletion, receipt rewrite, history truncation, retention change,
server page-limit increase, hardcoded live counts or identities, migration,
new index, REST/OpenAPI schema change, provider call/login/profile mutation,
default-profile access, running-agent control, fabricated/replayed/edited
telemetry, scheduler or provider behavior change, dependency change, M6, M7,
M8, release, OpenAI API billing, or macOS acceptance.

M5 remains **Intermediate** until this approved correction is implemented, the
sixth rollover and refreshed live prerequisites pass, `AUTO-M5-EXIT` passes,
and the owner separately accepts the milestone.

### Plan 1.16 local implementation checkpoint

The approved production correction is locally implemented and reviewed in the
development worktree. This checkpoint is preactivation evidence only: the
receipt-bound service remains exact clean revision
`8cc683d946b58f5eb72955e08a520195582e1a28`, and no 1.16 live witness,
rollover, completion receipt, or acceptance result is claimed.

The M05 work began with the expected absent-boundary import Red. Independent
review then found that the first selector validation imposed an unapproved
64-character token restriction on `OpaqueIdV1`; its focused Red was corrected
without widening the approved 1-to-200 tuple or consumer-key grammar. Real
owner-database scale verification at more than 36,000 capacity events returned
`2 passed in 9.64s`, including an exact three-event indexed lookup below the
30-second bound and no whole-outbox traversal. Independent review found no
production defect and closed two test gaps: exact-200 selector acceptance and
receipt ID, acknowledgement-time, and payload-digest cross-binding, with all
three targeted mutations first Red. The final owner-bound run returned
`3 passed in 12.96s`, and the focused cross-binding run returned `1 passed in
7.37s`. The focused Capacity result is `1 passed` plus one pre-existing owner-
live skip that receives no pass credit; the alert-witness policy file passes
`16` tests, and the lifecycle pure selection passes `6` tests. Independent
backend review is CLEAN.

The UI first failed because the pagination module and its policy export were
absent. Green covers terminal histories of 192 and 200 entries and a 201-entry
two-page history, plus the approved cursor, identity, ordering, duplicate, and
partial-failure rules. The M5 UI policy suite passes `17/17`; frontend typecheck
and the production build pass. Independent UI review is CLEAN. This local
result does not pass `M5-CDX-UI-014`: the authenticated shared-browser
all-page equality and zero-mutation proof remains Not Run.

Activation tests first failed because the exact sixth source revision,
six-rollover catalog wording, and rebound Story inventory were absent. Green
passes `45` activation tests, `66` current-exit tests, and `3` dispatcher
tests. The Node inventory contains `21` identifiers with SHA-256
`ac6afb5a290f5bf5940581ef13db21acccce947f3d40f97b498b57189f2db7e7`.
The Python inventory contains `557` identifiers with SHA-256
`f9bf5d58f37032239377741a8ab74f96c220348cf5cad46323c47e6c71682035`;
its exact 10-ID 1.16 delta reproduces the prior `547` inventory and digest
`3a97e0103ae4ba3390d10567c9130821abaa7a5a7e9640cf0091bc56a49b6a0c`
when removed. Its event-delivery selection names only the new exact query node,
so the M5 gate does not require unrelated opt-in M4 receipt selectors.
Independent activation review is CLEAN. These results do not pass
`M5-SVC-ACT-021`; both live canonical invocations remain Not Run.

The complete exact-revision preactivation set, standalone authenticated
containment rerun, sixth rollover, refreshed owner and alert lifecycle,
`AUTO-M5-ALERT-WITNESS`, `AUTO-M5-QUOTA-WITNESS`, canonical process proof,
`AUTO-M5-EXIT`, and owner acceptance remain required in that order. Until
their actual boundaries pass, M5 remains **Intermediate** with canonical gate
state `not_run`.

## Approved AUTO-M5-EXIT artifact-selector correction — 2026-10-23

**Status: Owner-approved 1.17.0 on 2026-10-23.**

Plan 1.17.0 incorporates owner-approved 1.16.0 unchanged and authorizes only one
completion-automation correction, its focused Red/Green regression, and one
exact evidence-preserving rollover from the currently active revision
`35f50d8c4865505a9112d8aef7ea788f425ae658`. It does not reopen any M5
product, provider, API, UI, persistence, quota, alert, or process behavior.

### Current exact-revision evidence

The sixth rollover activated clean revision
`35f50d8c4865505a9112d8aef7ea788f425ae658`. Fresh service-bound owner
outcomes, the genuine Codex alert lifecycle and alert witness, and the official
`/status` quota reconciliation and quota witness passed for that exact service.
They do not constitute milestone completion.

`AUTO-M5-EXIT` then failed before its technical suite with
`m5_current_story_artifact_missing` and created no completion receipt. The
static Story artifact tuple contains the intentional exact pytest selector
`backend/tests/integration/capacity/test_m4_event_delivery.py::test_acknowledged_event_evidence_selector_bounds_fail_closed`.
The selected source file exists, but the gate passes the complete node ID to
`Path.exists()`, which treats the `::test_...` suffix as part of the filesystem
name and therefore reports a false missing artifact. This is an automation
defect, not evidence that the source file or selected test is missing. The
failed invocation gives no pass credit to the downstream lanes it did not run.

Because the correction creates a new implementation revision, the existing
activation receipt and all revision/service-bound prerequisites cannot be
reused. One exact seventh rollover and a complete prerequisite refresh are
therefore required before the corrected gate can run.

### Requirement and scenario binding

- `M5-CDX-GATE-015` verifies that the canonical gate resolves an exact pytest
  node ID to its source file only for the static artifact-presence check while
  preserving that complete node ID for pytest execution and inventory. It
  contributes `NFR-TEST-001/002`, `NFR-RES-001`, `NFR-COMP-001`, and
  `AC-TEST-001/003/006`.
- `M5-SVC-ACT-022` verifies the exact seventh archive and activation from
  revision `35f50d8c4865505a9112d8aef7ea788f425ae658`. It contributes
  `NFR-RES-001`, `NFR-TEST-001/002`, and `AC-TEST-001/003/006` without
  creating general deployment authority.

Neither scenario may be marked Passed until its named boundary runs against
the clean corrected revision and real owner service state.

### Exact artifact-selector correction

Add one bounded helper to the existing M5 exit implementation that receives
the repository root and static Story artifact entries and returns the entries
whose source artifacts are missing. For an entry containing a pytest node
separator, the helper must use only the nonempty path before the first `::` for
the filesystem existence check. An entry without `::` is checked unchanged.
The original entry, including its complete node suffix, remains in
`STORY_ARTIFACTS` and `STORY_TEST_PATHS` and remains the selector passed to
pytest and included in the exact Story inventory.

An absent source file must still return the original entry as missing and
produce the unchanged `m5_current_story_artifact_missing` failure. The helper
must not turn the node selection into a whole-file test selection, skip the
selected test, make a missing artifact optional, inspect test source content,
or accept a path derived from runtime/user input.

Before changing the implementation, the focused regression must be run Red:
an existing temporary source plus `test_selected.py::test_selected` is
misclassified by the current direct existence check, or the new helper is
absent. Green must prove that the exact node selector resolves to the existing
source, a missing selected source remains missing, and ordinary non-node
artifacts retain their existing behavior. The complete current-exit test file
must then pass. The Python Story inventory count and digest may be rebound only
from the exact collected inventory after adding these tests; no test may be
removed, renamed, skipped, or excluded to recover the prior digest.

### Authorized files

Implementation and focused verification are limited to:

- `tools/automation/implementations/auto_m5_current_exit.py`;
- `tools/automation/test_m5_current_exit.py`;
- `tools/automation/implementations/m5_service_activation.py`;
- `tools/automation/test_m5_service_activation.py`; and
- `tools/automation/routines.toml`, only for truthful seven-rollover scope
  wording;
- `docs/plans/plan-baseline.toml`, only as the deterministic synchronized
  snapshot generated after that catalog wording changes;
- `docs/plans/integration/cs1-final-readiness-audit.md` and
  `docs/plans/integration/cs1-full-plan-synchronization.md`, only for their
  append-only binding to that exact regenerated snapshot;
- `docs/evidence/m5-codex-implementation.md`, `docs/operations/runbook.md`,
  `docs/README.md`, and `docs/evidence/v1-implementation-status-v1.json`, only
  to reconcile their M5 status with the verified 1.16 live outcome, failed
  exit, and local 1.17 evidence.

This amendment initially changed only this plan. Verified
implementation outcomes may additionally update the existing M5 implementation
evidence, operations runbook status, primary documentation index, and
implementation-status overlay without widening behavior. No other
production, test, generated, contract, migration, dependency, or documentation
file is authorized by 1.17.0. The baseline snapshot is generated by the
existing renderer and carries no independent behavior or authority.

### Contract, security, privacy, data, and dependency impact

The correction is internal completion automation. It changes no public or
module contract, REST/OpenAPI schema, generated client, private receipt schema,
database schema, migration, retention rule, provider adapter, provider call,
authentication flow, quota meaning, alert lifecycle, Registry behavior,
browser behavior, or running-agent behavior. It adds no dependency and needs
no licence, SBOM, notice, ADR, compatibility, backup, or data migration change.

The artifact helper reads filesystem metadata for repository-owned static
paths only. It must not read source content, arbitrary environment values,
provider/profile state, account identity, credentials, prompts, responses, or
raw live evidence. Existing secret, ownership, symlink, clean-checkout,
revision, and receipt protections remain unchanged.

### Approved seventh evidence-preserving rollover

After focused and complete preactivation Green on one new clean detached
revision, one seventh corrective rollover is approved from exact active
revision `35f50d8c4865505a9112d8aef7ea788f425ae658` into fixed singleton
namespace `m5-service-activation-corrective-archive-35f50d8`. The activation
policy must append that revision as the seventh and final approved rollover,
require the six existing archives as an unchanged ordered prefix, and reserve
every completed revision from candidate selection.

The first canonical activation invocation must validate the complete current
transition, exact service/browser revision, clean detached checkout, Registry
and database identity, rollback runtime, and all six prior archives. Under the
existing exclusive guard it must restore the trusted rollback service,
atomically move the complete transition directory without replacement into
the seventh archive, fsync both parents, and return the existing status-5 rerun
result. The second invocation must revalidate all seven archives and the
prepared corrected candidate before the unchanged rollback drill and
activation. Existing descriptor, inode, digest, ownership, mode, link-count,
collision, interruption, retry, and trusted-restoration protections remain
unchanged. Partial, multiple, unknown, replaced, linked, colliding,
skipped-prefix, dirty-checkout, wrong-service, or wrong-revision state must
block without cleanup or replacement.

After activation, the canonical prerequisite archive must remove only the
stale revision/service-bound prerequisite files under its existing policy. A
new four-account owner outcome, one new genuine opening or reopening, distinct
repeat, owner action and source-proven recovery, a new
`AUTO-M5-ALERT-WITNESS`, and a new official `/status` reconciliation plus
`AUTO-M5-QUOTA-WITNESS` must bind to the corrected revision and selected
service. `AUTO-M5-EXIT` must then rerun immediately and execute its complete
process, browser, technical, planning, quality, mutation, documentation, and
Git-preflight lanes before it may write its create-once receipt. No prerequisite
or completion result bound to revision `35f50d8c4865505a9112d8aef7ea788f425ae658`
may be copied, edited, or credited to the corrected revision.

### Required verification and exclusions

Focused Green must include the artifact-helper regression, complete
current-exit tests, exact seventh-rollover activation tests, dispatcher tests,
Ruff lint/format, strict mypy, `git diff --check`, and the exact rebound Story
inventory. The full canonical preactivation set and zero-skip authenticated
containment must pass on the clean corrected revision before activation. The
two real activation invocations, refreshed prerequisites, and complete
`AUTO-M5-EXIT` must then pass in that order. The owner reviews the resulting
receipt before the existing separate M5 acceptance step.

This amendment authorizes no gate relaxation, whole-file replacement for the
exact pytest node selector, eighth rollover, general deployment, receipt or
witness rewrite, prerequisite reuse, provider call/login/profile mutation,
default-profile access, running-agent control, fabricated/replayed/edited
telemetry, product behavior, new test scope beyond the focused regression and
seventh-rollover policy, contract/schema/migration/dependency change, M6, M7,
M8, release, OpenAI API billing, or macOS acceptance.

### Plan 1.17 local implementation checkpoint

The approved 1.17 correction is locally implemented but not yet committed or
activated. The artifact-helper Red failed for the expected absent helper;
Green passes its three exact cases. The seventh-rollover Red failed for the
expected absent exact revision; Green passes the complete activation and
dispatcher selection. The combined current-exit, activation, and dispatcher
selection passes `119` tests. Existing sixth-rollover test IDs remain intact,
separate seventh scenarios were added, and independent review is CLEAN.

The exact Python Story inventory now contains `562` identifiers with SHA-256
`4ca56497a7fdaa1e80c7c01a3ee1e41c2029288966b1fe969790606fad0cbb7b`.
`AUTO-PLAN-CHECK`, `AUTO-DOCS-CHECK`, `AUTO-BUILD`, and `AUTO-QUALITY` pass.
The first `AUTO-MUTATION` attempt truthfully failed before mutation analysis
because the caller's default `codex` resolved to unadmitted `0.163.0`; the
unchanged rerun with the approved pinned `0.160.0` path passed all `1,708`
mutants with `1,698` killed, `10` accepted equivalents, and no unaccepted
survivor. `AUTO-M3-TEST` passes `307` tests. `AUTO-TEST` passes `104`
automation tests, two Argon2 cases, `1,362` backend tests with `40` declared
external-live skips, and every required production-browser scenario. The
literal 24-hour elapsed, owner-local M0, hosted, and separate T5/T6/T7 lanes
retain their existing truthful Not Run or Blocked classifications and receive
no M5 credit.

The active service and its three private prerequisites remain bound to
`35f50d8c4865505a9112d8aef7ea788f425ae658`; they receive no credit for the
new candidate. A clean committed revision, exact detached Git preflight,
standalone authenticated containment, the two-stage seventh rollover,
prerequisite archive and refresh, corrected `AUTO-M5-EXIT`, and separate owner
acceptance remain required.

M5 remains **Intermediate**. The latest canonical result is `failed` on
`35f50d8`; the corrected candidate is `not_run`. Completion still requires the
seventh rollover on one clean revision, all refreshed live prerequisites, a
passing `AUTO-M5-EXIT` receipt, and separate owner acceptance.

## Approved full-unused rolling-reset reconciliation and eighth exact rollover — 2026-10-24

**Status: Owner-approved 1.18.0 on 2026-10-24.**

Plan 1.18.0 incorporates owner-approved 1.17.0 unchanged and authorizes only one
correction to the private `AUTO-M5-QUOTA-WITNESS` reconciliation policy, its
focused Red/Green coverage and exact Story inventory rebind, and one
evidence-preserving rollover from the currently active clean revision
`1ada84f71e827bb4f7ea966462a6cf51d050e9af`. It does not reopen provider
collection, quota meaning, API, UI, persistence, alert, process,
authentication, or managed-profile behavior.

### Current real-system evidence

The seventh rollover activated clean detached revision
`1ada84f71e827bb4f7ea966462a6cf51d050e9af`; the selected systemd service and
authenticated shared browser report that revision. Fresh owner outcomes and
the source-proven alert lifecycle/witness passed for that service. They do not
constitute M5 completion.

Fresh owner-observed Codex 0.160.0 `/status` evidence showed naturally unused
windows at exactly `100%` remaining. Thirty-five five-hour observations and
two weekly streams of thirty-five and thirty-six observations retained stable
native horizons near 17,999 and 604,799 seconds while each absolute reset moved
with the later collection. Reset movement tracked collection movement within
1.037 seconds. A naturally non-full weekly stream retained one fixed reset
across nine observations. One genuine account exposed only its weekly window
and no five-hour window. No missing window may be synthesized.

The existing pure policy compares only absolute reset buckets. A sanitized
reproduction with collection and owner observation six minutes apart, both
values `100%`, and both weekly reset timestamps advanced by the same six
minutes returns `m5_quota_witness_reconciliation_mismatch`. That is a false
mismatch between two consistent rolling observations. Broad reset tolerance
would weaken fixed-window evidence and is not proposed.

### Requirement and scenario binding

- `M5-CDX-GATE-016` verifies the closed fixed-or-rolling reset relation for the
  owner-observed Codex quota witness. It contributes `FR-QUOTA-001..006`,
  `FR-HIST-001/002`, `AC-LIVE-005`, `AC-HIST-001`, `AC-OPS-003/006`,
  `NFR-TEST-001/002`, `NFR-RES-001`, and `AC-TEST-001/003/006`.
- `M5-SVC-ACT-023` verifies the exact eighth archive and activation from
  revision `1ada84f71e827bb4f7ea966462a6cf51d050e9af`. It contributes
  `NFR-RES-001`, `NFR-TEST-001/002`, and `AC-TEST-001/003/006` without
  creating general deployment authority.

Neither scenario may be marked Passed until its named boundary runs on the
clean corrected revision and the real owner service state.

### Exact reconciliation correction

Preserve exact account/window-set equality, window keys, semantic roles, whole
percentages, reset nullness, display-precision validation, and the existing
300-second observation/collection bound. Preserve the fixed relation first:
two absent resets match, and two present resets match only when their absolute
timestamps occupy the same owner-displayed second, minute, hour, or day bucket.

Only when that fixed relation fails may one window use the rolling relation.
The rolling relation passes only when every condition below is true:

1. AgentMonitor and the owner both report exactly `100` percent remaining;
2. both reset timestamps are present;
3. AgentMonitor's retained reset precision is exactly `exact`, rather than
   `rounded`, `range`, `estimated`, or `unknown`;
4. AgentMonitor's exact reset is strictly future relative to collection;
5. the owner observation follows collection by 1--300 seconds; and
6. the half-open owner reset interval implied by its displayed precision
   overlaps the interval from AgentMonitor's exact reset through that reset
   advanced by the observation delay, and their intersection contains a point
   strictly after the owner observation.

Condition 6 proves that the official reset could have moved one-for-one at
some point between the two bounded observations. It is not an arbitrary
`+/- 300 seconds` reset tolerance. A non-100 window always requires the
existing absolute reset match. A fixed reset at any percentage continues
through the existing absolute relation. A full window whose reset does not
either match absolutely or fall within the exact bounded rolling interval
fails with the unchanged `m5_quota_witness_reconciliation_mismatch` code.
Negative, zero, or excessive observation skew, a past/equal AgentMonitor reset,
an overlap wholly at or before owner observation, a displayed bucket outside
the rolling interval, non-exact source precision, null mismatch,
missing or extra windows, duplicate windows, fractional percentages, changed
roles/keys, or unknown display precision remain rejected.

`_agent_records` already validates and serializes `reset_precision`; the
correction retains that existing value in `_AgentQuotaWindowV1` solely for the
rolling guard. Canonical digest input and the private witness schema do not
change.

The correction compares only windows already present in both closed sets. It
must not invent, rename, drop, or infer a five-hour, weekly, primary, or
secondary window; hardcode a provider duration, account, alias, window key, or
live value; invoke Codex; reread a provider profile; or change the owner
attestation phrase. An account for which the admitted source and official view
expose only one weekly window remains a one-window account in this witness.

### Test-first sequence

Before implementation, add a pure regression whose AgentMonitor and owner
observations are within 300 seconds, both report `100%`, and whose reset moves
inside the bounded interval across a displayed bucket. It must fail Red under
1.17 with `m5_quota_witness_reconciliation_mismatch` because the absolute
buckets differ.

Green must prove all of the following:

- valid full-window movement passes at second and minute precision, plus
  hour/day boundary cases with the documented half-open interval behavior;
- an unchanged fixed reset passes through the existing absolute relation for
  both `100%` and non-100 values;
- a non-100 reset shifted across the displayed bucket by the observation delay
  fails, while the existing displayed-precision equality remains unchanged;
- a full reset bucket entirely before or after the bounded rolling interval
  fails;
- negative and zero observation deltas cannot use the rolling branch, the exact
  300-second boundary passes, and 301 seconds fails;
- an AgentMonitor reset that is not future at collection, an intersection with
  no point after owner observation, and `rounded`, `range`, `estimated`, or
  unknown AgentMonitor reset precision cannot use the rolling branch;
- null/present mismatch, missing/extra/duplicate windows, and a synthesized
  five-hour window remain rejected; and
- canonical value and owner-observation digests plus
  `agentmonitor.m5-quota-witness.v1` parsing remain unchanged.

Existing tests remain named and present; focused cases are additive. Run the
focused Red, focused Green, the complete quota-witness file, complete
current-exit and activation files, and dispatcher tests. Recollect the exact
Python Story inventory and update its count/digest only from the real
collection; no test may be removed, renamed, skipped, or excluded to preserve
the old value.

### Authorized files

Implementation and focused verification are limited to:

- `tools/automation/implementations/m5_codex_quota_witness.py`;
- `tools/automation/test_m5_codex_quota_witness.py`;
- `tools/automation/implementations/auto_m5_current_exit.py` and
  `tools/automation/test_m5_current_exit.py`, only for the exact collected
  Story inventory count/digest and its assertions;
- `tools/automation/implementations/m5_service_activation.py`;
- `tools/automation/test_m5_service_activation.py`;
- `tools/automation/routines.toml`, only for truthful eight-rollover and
  reconciliation wording;
- `docs/engineering/completion-and-automation-gates.md`, only for truthful
  eight-rollover wording and the exact fixed-or-full-rolling reconciliation
  rule;
- this plan and `docs/plans/plan-baseline.toml`, with the baseline generated
  only by the existing renderer;
- `docs/plans/integration/cs1-final-readiness-audit.md` and
  `docs/plans/integration/cs1-full-plan-synchronization.md`, only for
  append-only binding to the regenerated snapshot; and
- `docs/evidence/m5-codex-implementation.md`, `docs/operations/runbook.md`,
  `docs/README.md`, and `docs/evidence/v1-implementation-status-v1.json`, only
  to record the real 1.17 outcome, this correction, and later verified 1.18
  results.

No other production, test, generated, contract, migration, dependency, or
documentation file is authorized. If implementation proves another file or
contract is required, stop and amend/reapprove the plan.

### Contract, security, privacy, data, and dependency impact

The correction is internal completion-evidence policy.
`CTR-CAP-001/003/004/007`, provider contracts, REST/OpenAPI, generated client,
database schema, migrations, retention, Registry, browser rendering, quota
collection, scheduler, alert lifecycle, and private witness/receipt schemas do
not change. No ADR or compatibility migration is required.

The command remains provider-read-free and application-read-only. It stores
only existing counts and digests in the create-once owner-only file. It must
not persist or log aliases, account identities, entered percentages/resets,
profile paths, provider payloads, prompts, responses, credentials, or raw
browser material. No dependency, lockfile, SBOM, notice, or licence change is
authorized.

### Approved eighth evidence-preserving rollover

Because implementation changes the clean revision, no revision/service-bound
1.17 activation receipt, owner outcome, alert witness, quota observation,
process evidence, or completion result may be copied, edited, or credited to
the corrected candidate.

After owner approval and complete preactivation Green on one new clean detached
revision, permit one eighth corrective rollover from exact revision
`1ada84f71e827bb4f7ea966462a6cf51d050e9af` into fixed singleton namespace
`m5-service-activation-corrective-archive-1ada84f`. Append that revision as the
eighth and final approved rollover, require the seven existing archives as an
unchanged ordered prefix, and reserve every completed revision from candidate
selection.

The first canonical activation invocation must validate the complete current
transition, exact service/browser revision, clean detached checkout,
Registry/database identity, rollback runtime, and all seven prior archives.
Under the existing exclusive guard it restores the trusted rollback service,
atomically moves the complete transition directory without replacement into
the eighth archive, fsyncs both parents, and returns the existing status-5
rerun result. The second invocation revalidates all eight archives and the
corrected candidate before the unchanged rollback drill and activation.
Existing descriptor, inode, digest, ownership, mode, link-count, collision,
interruption, retry, and trusted-restoration protections remain unchanged.
Partial, multiple, unknown, replaced, linked, colliding, skipped-prefix,
dirty-checkout, wrong-service, or wrong-revision state blocks without cleanup
or replacement.

After activation, run the canonical prerequisite archive, create a new
four-account owner outcome, complete a new genuine opening/reopening, distinct
repeat, one owner action and distinct source-proven recovery, pass a new
`AUTO-M5-ALERT-WITNESS`, obtain fresh scheduled quota lineage, and run the
corrected `AUTO-M5-QUOTA-WITNESS`. Live quota evidence must naturally exercise
at least one bounded rolling `100%` window and one strict non-100 fixed reset
if those genuine conditions remain available; an unavailable required
condition is Blocked and is never manufactured. Refresh the five-to-six
process proof and immediately run `AUTO-M5-EXIT` while the 15-minute quota
witness is current.

### Completion and exclusions

Before activation, require focused tests, complete affected suites, exact
Story inventory, Ruff lint/format, strict mypy, frontend typecheck/build, API
compatibility, `AUTO-PLAN-CHECK`, `AUTO-DOCS-CHECK`, `AUTO-BUILD`,
`AUTO-QUALITY`, `AUTO-MUTATION`, `AUTO-M3-TEST`, `AUTO-TEST`, detached
`AUTO-GIT-PREFLIGHT`, zero-skip authenticated containment, `git diff --check`,
and clean independent policy, activation-safety, test-integrity, and
security/privacy reviews. After activation, both real activation invocations,
every refreshed prerequisite, and complete `AUTO-M5-EXIT` must pass before a
receipt can be reviewed for separate owner acceptance.

This amendment authorizes no arbitrary reset tolerance, omitted-window
substitution, hardcoded duration/value/account, ninth rollover, general
deployment, witness/receipt rewrite, prerequisite reuse,
fabricated/replayed/edited telemetry, provider call/login/profile mutation,
default-profile access, running-agent control, public
contract/schema/migration/dependency change, M6, M7, M8, release, OpenAI API
billing, or macOS acceptance. M5 remains **Intermediate** until the corrected
exact-revision gate passes and the owner separately accepts it.

## Approved pytest 9.1.1 JUnit identity/outcome correction within the pending eighth rollover — 2026-10-25

**Status: Owner-approved 1.19.0 on 2026-10-25.**

Plan 1.19.0 incorporates owner-approved 1.18.0 unchanged and authorizes only one
correction to the private `AUTO-M5-EXIT` Story-report validator, its focused
Red/Green coverage, and a final exact inventory binding from one successful
zero-skip run. The 1.18 quota policy, tests, eighth-rollover implementation,
documentation, and synchronization changes remain part of the same uncommitted
candidate.

This amendment creates no additional service rollover. After complete Green,
the combined 1.18 and 1.19 changes form one clean revision and use the single
already approved eighth rollover from active revision
`1ada84f71e827bb4f7ea966462a6cf51d050e9af`.

### Current exact-tool evidence

The locked development dependency and executing environment both use pytest
`9.1.1`.

A real minimal pytest 9.1.1 invocation over one `unittest.TestCase` method
containing three successful `subTest` blocks reports one passed parent and
three passed subtests in the terminal, one `<testcase>` identity in JUnit, and
`<testsuite tests="4" failures="0" errors="0" skipped="0">`. Pytest therefore
uses the JUnit `tests` attribute for executed outcomes while emitting one
`<testcase>` identity for the parent node. The current
`_validate_pytest_report_inventory_v1` incorrectly requires the declared
outcome count to equal the number of emitted parent identities.

The exact selected M5 Story run exposed the same shape:

- `588` unique emitted `<testcase>` identities;
- provisional identity digest
  `77f4ab235b47c36520352a7de048c08eba90bd708e6b5cb20277e27b75890bf8`;
- `1,146` declared outcomes, including `558` successful subtest outcomes; and
- zero skipped outcomes.

The direct harness run itself finished with `585` passed and `3` failed parent
tests. It is not completion evidence, and its measured counts and digest remain
provisional until the exact selected suite passes with zero failures and zero
skips.

The three failures were separate from JUnit parsing: current managed-profile
containment state, a required service-start binding omitted by the direct
harness, and private copied-database mode under the caller's shell umask. This
amendment does not reinterpret those failures as passing and authorizes no
behavior change for them. They must be rerun with the exact canonical service
binding, managed-profile prerequisites, private execution environment, pinned
provider-tool path, and complete M5 selectors. If any reproduces under that
canonical environment, stop and amend the plan from the new Red.

### Requirement and scenario binding

`M5-CDX-GATE-017` verifies that the pinned pytest 9.1.1 report validator binds
the exact selected parent identities and the exact executed outcome count
without confusing successful subtests with additional parent identities. It
contributes `NFR-TEST-001/002`, `NFR-RES-001`, `AC-OPS-003/006`, and
`AC-TEST-001/003/006`.

The scenario remains Not Run until its focused boundary and the complete
selected Story suite pass on the clean combined candidate.

### Exact validator correction

Preserve the existing normalized repository-relative file policy, nonempty
bounded test names, unique parent identity set, exact identity count, exact
identity digest, selected Story paths, selected automation IDs, zero-skip
plugin, subprocess success requirement, timeout, and fail-closed error
vocabulary.

Separate two exact values that pytest 9.1.1 represents differently:

1. **Parent identity inventory:** the number and digest of emitted `<testcase>`
   file/name pairs.
2. **Executed outcome inventory:** the `<testsuite tests>` count, including
   successful `subTest` outcomes that pytest does not emit as separate
   `<testcase>` elements.

Add one explicit expected declared-outcome constant beside the existing
expected parent count and digest. The final values may be bound only from one
successful zero-failure, zero-error, zero-skip execution of the exact selected
Story command. The current measurements of `588` parent identities, digest
`77f4ab235b47c36520352a7de048c08eba90bd708e6b5cb20277e27b75890bf8`, and
`1,146` declared outcomes must be revalidated by that successful run before
they receive Green credit.

For the pinned pytest report shape, require exactly one direct `<testsuite>`
below the `<testsuites>` root and no nested or additional suite. Require its
`tests`, `failures`, `errors`, and `skipped` attributes to be present, decimal,
nonnegative integers. The declared outcome count must equal the exact bound
expected-outcome constant and must not be smaller than the emitted parent
count. Failures, errors, and skips must each equal zero. A `<failure>`,
`<error>`, or `<skipped>` result element must also fail closed.

Continue to require every emitted parent identity to be valid, unique, and
part of the exact count/digest. Do not derive identities from suite totals,
terminal prose, subtest labels, arbitrary XML text, or caller-supplied paths.

Preserve the validator's existing top-level Story-count meaning for callers by
returning the emitted parent-identity count and skip count. The separately
bound declared-outcome count is validation evidence and does not inflate the
receipt's top-level test count. This correction changes only internal
completion-evidence validation; it does not change a public, module, witness,
receipt, API, provider, database, or UI contract.

### Test-first sequence

Before production implementation, add a regression generated by the real
pinned pytest 9.1.1 executable: one temporary `unittest` parent with successful
subtests must produce one parent identity and multiple declared outcomes. The
current validator must fail Red with `m5_current_story_inventory_invalid`.

Green must prove:

- the exact pinned-pytest subtest report passes with one parent identity and
  the separately bound declared outcomes;
- a report without subtests passes when its exact parent and outcome counts are
  equal;
- the final real Story report passes only with its exact separately bound
  parent count, parent digest, and declared outcome count;
- changing the declared outcome count while preserving parent identities
  fails;
- changing, adding, removing, or duplicating a parent identity fails;
- multiple, missing, or nested suites fail;
- malformed, missing, negative, or nondecimal count attributes fail;
- any declared failure, error, or skip fails;
- any `<failure>`, `<error>`, or `<skipped>` result element fails;
- an invalid, absolute, traversing, unselected, overlong, or NUL-bearing
  file/name value fails;
- the no-skip plugin and subprocess nonzero-exit behavior remain unchanged;
  and
- no selected test, parameterization, subtest, path, or automation ID is
  removed, renamed, skipped, filtered, or excluded to obtain Green.

Run the focused Red, focused Green, the complete current-exit test file,
complete quota-witness and activation files, affected dispatcher tests, and
the exact selected Story command. Recollect the final constants only from the
successful zero-failure and zero-skip report.

### Authorized files

Implementation and focused verification are limited to:

- `tools/automation/implementations/auto_m5_current_exit.py`;
- `tools/automation/test_m5_current_exit.py`;
- this plan; and
- `docs/evidence/m5-codex-implementation.md`,
  `docs/operations/runbook.md`, `docs/README.md`, and
  `docs/evidence/v1-implementation-status-v1.json`, only to record the verified
  combined 1.18/1.19 result and later live outcome.

Owner-approved 1.18.0's already authorized files remain available solely for
completing and documenting their approved changes. No provider, API, UI,
persistence, contract, migration, dependency, lockfile, activation-policy,
witness-schema, receipt-schema, or other test file is authorized by 1.19.0.

If the exact canonical rerun proves that any of the three direct-harness
failures is a code defect rather than missing or invalid environment state,
stop and amend/reapprove the plan before changing its owning file.

### Contract, security, privacy, data, and dependency impact

This is an internal fail-closed test-evidence correction. It parses only the
bounded temporary JUnit file already produced by the selected local test
process. It adds no provider call, profile access, account data, process
control, network access, secret, database access, retained raw report, or new
dependency.

Only aggregate counts and the existing SHA-256 identity digest enter
completion evidence. Test names remain bounded repository test identifiers.
No prompt, response, provider payload, account identity, profile path,
credential, arbitrary environment value, source content, or raw live evidence
may be persisted or logged.

No public/module contract, API/OpenAPI schema, generated client, database
schema, migration, retention rule, compatibility promise, SBOM, notice,
licence record, ADR, backup, or restore change is required.

### Single pending eighth rollover

Plan 1.18.0's eighth-rollover authority remains unchanged. No 1.18 candidate
has been committed or activated, so the 1.19 correction must be included in
the same clean candidate revision.

After all combined preactivation checks pass, the first canonical activation
invocation archives completed active revision
`1ada84f71e827bb4f7ea966462a6cf51d050e9af` into
`m5-service-activation-corrective-archive-1ada84f` and returns the existing
status-5 rerun result. The second invocation activates the one combined
corrected candidate after revalidating all eight archives and the trusted
rollback runtime.

No intermediate 1.18 revision may be activated, archived, or treated as a
separate rollover. No ninth rollover is authorized.

After activation, refresh owner outcomes, the genuine alert lifecycle/witness,
official `/status` quota evidence/witness, and process proof once for the
combined revision and service. Then run complete `AUTO-M5-EXIT` while the
quota witness remains current.

### Required verification and exclusions

Before commit and activation require:

- focused and complete affected tests;
- the exact successful parent-identity/outcome inventory;
- Ruff lint/format and strict mypy;
- `git diff --check`;
- `AUTO-PLAN-CHECK`, `AUTO-DOCS-CHECK`, `AUTO-BUILD`, `AUTO-QUALITY`,
  `AUTO-MUTATION`, `AUTO-M3-TEST`, and `AUTO-TEST`;
- detached `AUTO-GIT-PREFLIGHT`;
- zero-skip authenticated containment; and
- independent test-integrity, policy, activation-safety, and security/privacy
  review.

Use the approved pinned Codex 0.160.0 path for every provider-sensitive gate.
The three direct-harness failures must either pass under the exact canonical
prerequisites or produce a new explicit Red and stop condition.

This amendment authorizes no relaxed or ignored suite total; arbitrary
`declared >= emitted` acceptance; removal, flattening, suppression, or
rewriting of subtests; terminal-output parsing; test deletion or skip;
fabricated XML; dependency/plugin change; ninth rollover; general deployment;
prerequisite reuse; witness/receipt rewrite; provider call/login/profile
mutation; default-profile access; running-agent control; public
contract/schema/migration change; M6, M7, M8, release, OpenAI API billing, or
macOS acceptance.

M5 remains **Intermediate** until the combined clean revision is activated,
every refreshed prerequisite passes, `AUTO-M5-EXIT` writes its create-once
receipt, and the owner separately accepts that exact receipt.

## Owner-approved deterministic private-fixture correction within the pending eighth rollover — 2026-10-25

**Status: Owner-approved 1.20.0 on 2026-10-25. Test implementation is
authorized only within the exact scope below; no production behavior change is
authorized.**

Plan 1.20.0 incorporates owner-approved 1.18.0 and 1.19.0 unchanged and
authorizes only two existing real-filesystem test fixtures to establish their
intended modes independently of the caller's process `umask`. It adds no
production behavior, new test node, service rollover, or provider operation.
After approval and Green, all combined 1.18--1.20 changes form one candidate
for the single pending eighth rollover from
`1ada84f71e827bb4f7ea966462a6cf51d050e9af`; no ninth rollover is authorized.

### Current exact evidence

The exact selected Story run used pinned pytest `9.1.1` and reported `596`
passed parent tests, `558` successful subtests, and two failed parent tests.
Its provisional report contained `598` emitted parent identities and `1,156`
declared outcomes. Because the run was not zero-failure, those values and its
identity digest are not final inventory bindings.

The two failures have one bounded fixture cause:

1. The real owner-database enrollment test copies the selected database through
   `sqlite3.Connection.backup` into an absent disposable file. SQLite creates
   that file from mode `0666`; the workstation's ordinary `0002` umask leaves
   mode `0664`. Production `DatabaseRefV1` correctly rejects anything other
   than an owner-owned, single-link regular `0600` database. The disposable
   test fixture failed to establish the production precondition.
2. A whole-suite `0077` umask is not a valid correction. It also changes an
   intentional `mkdir(mode=0o755)` hostile managed-root fixture to `0700`, so
   the negative containment test no longer constructs the unsafe root it
   claims to reject.

The separate authenticated containment failure is not part of this proposed
code change. After the owner exited the final stale `/status` session, a
privacy-safe in-memory rerun retained no trace or path and emitted only closed
structural facts: the unchanged policy accepted exactly ten successful,
canonical, selected-managed-profile `ftruncate` calls, no successful other
descriptor mutator, and no default-root annotation. The complete verification
passed. The exact unmodified pytest node then passed with zero skips (`1 passed
in 2.70s`) under ordinary `0002` umask. No containment production-policy change
is justified or authorized. A later recurrence of
`m5_codex_containment_fd_write_unverifiable` stops the gate and requires a new
evidence-specific amendment rather than a retry-hidden pass.

### Requirement and scenario binding

`M5-CDX-GATE-018` verifies deterministic private and deliberately nonprivate
real-filesystem fixtures for `M5-CDX-REG-004..006`, `M5-CDX-GATE-001`,
`NFR-TEST-001/002`, `NFR-SEC-001`, `NFR-PRIV-001/002`,
`AC-OPS-003/006`, and `AC-TEST-001/003/006`.

The local scenario is Passed: both focused tests pass under both named umasks
and the exact selected Story suite passes with zero failures, errors, and
skips. This is preactivation evidence only. The earlier failed run remains Red
evidence and is never relabelled Passed.

### Exact test-only correction

In the existing owner-selected live enrollment test, create the disposable
`agentmonitor.db` target before copying any owner data. Use direct POSIX
`os.open` with `O_CREAT | O_EXCL | O_RDWR | O_CLOEXEC` and requested mode
`0600`, immediately apply `os.fchmod(..., 0o600)`, and close the descriptor in
`finally`. Then run the unchanged real SQLite backup into that already-existing
private file. Before constructing `DatabaseRefV1`, require `lstat` to prove an
owner-owned, single-link regular file with exact mode `0600`. Any creation,
permission, close, backup, type, owner, link-count, or post-copy mode failure
must fail the test; no owner database bytes may first enter a group-readable
inode.

Do not use a global or process-local `umask` as the fixture control, repair the
mode only after backup, weaken `DatabaseRefV1`, initialize a replacement schema,
copy through shell utilities, or alter the owner database. The existing backup
remains a real SQLite backup and the existing before/after owner Registry
equality remains mandatory.

In the existing nonprivate-selected-root negative containment test, explicitly
apply and verify mode `0755` to the disposable selected root after `mkdir` and
before invoking the production tree check. This test-only setup guarantees the
hostile root remains hostile even under a restrictive caller umask. It must not
change the production tree policy or any real managed profile.

Both corrections modify existing test parents only. No test, parameterization,
subtest, selector, assertion, path, or automation ID may be removed, renamed,
skipped, filtered, or excluded. Final Story parent count, parent digest, and
declared-outcome count may be rebound only from one successful exact zero-skip
run under the 1.19 report validator.

### Test-first sequence

The retained Reds are:

- under shell-scoped umask `0002`, the selected real enrollment test creates a
  `0664` disposable database and fails the exact production permission policy;
  and
- under shell-scoped umask `0077`, the nonprivate-root negative test receives
  `0700` from `mkdir` and fails to observe the expected rejection.

Green must prove:

- the selected real enrollment test passes under both `0002` and `0077`, the
  disposable copied database is always exact `0600`, real identity and
  idempotent enrollment execute, and the owner Registry remains unchanged;
- the nonprivate-root negative test passes under both `0002` and `0077`, and
  the root is exact `0755` at the production-check boundary;
- the exact unmodified authenticated containment node passes once with zero
  skips, pinned Codex `0.160.0`, the selected service binding, and ordinary
  `0002` umask; and
- the complete selected Story command then passes with zero failures, errors,
  and skips without a whole-suite umask override.

### Verified local implementation evidence

Both retained Reds reproduced before the fixture correction. Under shell-scoped
`umask 0002`, the selected real enrollment test failed with
`database_permissions_unsafe`; under shell-scoped `umask 0077`, the hostile
managed-root test failed because no containment error was raised.

After the two test-only changes, the pair passes under both named umasks (`2`
passes per run). The complete two affected files pass `106` parents and `558`
subtests. The exact unmodified authenticated containment node passes with the
pinned Codex `0.160.0`, active service revision/PID/start binding, ordinary
`0002` umask, and zero skips (`1 passed in 3.69s`). Independent test-integrity
and security/privacy review both returned GO with no blocker.

One direct Story attempt then truthfully failed three environment-dependent
parents and reported six prohibited skips: this detached worktree lacked its
locked Playwright installation, resolved the workstation's unreviewed Claude
version instead of the admitted `2.1.289`, and selected a verified Codex
account different from the retained alert witness. No code was changed for
those results. After restoring the ignored locked dependencies, pinning both
provider tools, and selecting the witness-bound verified account, all four
focused nodes passed and the unchanged exact Story command passed `598`
parents and `558` subtests.

Independent combined review then found two in-scope fail-closed defects. A
syntactically valid rolling-reset observation near year 9999 escaped as
`OverflowError`, and a genuine pytest `<skipped>` result child reached the
generic inventory-invalid code instead of the preserved suite-skipped code.
Each new regression failed Red with that exact behavior. Green bounds all
rolling datetime arithmetic so overflow returns the existing reconciliation
mismatch, and classifies a genuine skip child as
`m5_current_story_suite_skipped` while failures and errors remain inventory
invalid. The complete quota-witness and current-exit files then pass `131`
tests.

Because those two regressions add parents, the final-code Story command was
recollected rather than arithmetically adjusted. Its pytest `9.1.1` JUnit
report contains exactly `600` unique direct parent identities, `1,158`
declared outcomes, zero errors, zero failures, zero skips, and parent-identity
SHA-256
`ad0b77bd19a52f0b0ff29958963414e6836882a659096d7f291cafb7368e4b3e`.
The production validator accepts that final report as `(600, 0)`, and the
complete current-exit file passes `80` tests after binding those constants. The exact
Node inventory passes `21/21`, and the authenticated real-API/file-SQLite
`account_beyond_page` browser scenario passes.

Canonical local preactivation results are: synchronized planning, documentation,
build, quality with strict mypy over `372` source files and zero boundary
violations, all `1,708` mutation cases with no non-equivalent survivor,
`AUTO-M3-TEST` `307` passes, and `AUTO-TEST` with `104` automation tests, `2`
locked M0-runtime tests, `1,362` backend passes plus its separately declared
`40` opt-in skips, and all required production-browser lanes. The first
`AUTO-TEST` invocation stopped only because the detached worktree lacked the
ignored locked M0 runtime; the unchanged rerun passed after that runtime was
made available. Planning, documentation, build, quality, mutation, M3, and
`AUTO-TEST` all passed again after the independent-review corrections on the
final candidate bytes. These local results do not substitute for detached
clean-revision Git preflight, activation, refreshed live evidence, the canonical M5
receipt, or owner acceptance.

After focused Green, run the complete affected files, Ruff lint/format, strict
mypy where applicable, `git diff --check`, dispatcher/catalog tests, and every
combined 1.18/1.19 preactivation gate. Recollect final JUnit inventory constants
only from that successful exact Story report. Independent test-integrity and
security/privacy review must confirm that the correction neither weakens the
production permission policy nor reads, persists, or emits owner database
content.

### Authorized files and impacts

Test implementation is limited to:

- `backend/tests/integration/registry/test_codex_managed_connection.py`;
- `tools/automation/test_m5_codex_containment.py`; and
- `tools/automation/implementations/auto_m5_current_exit.py` plus
  `tools/automation/test_m5_current_exit.py`, only for the final exact Story
  parent count, parent digest, declared-outcome count, and their assertions if
  those values change.

Planning and verified-result documentation is limited to this plan,
`docs/plans/plan-baseline.toml`, append-only CS1 snapshot bindings,
`docs/evidence/m5-codex-implementation.md`, `docs/operations/runbook.md`,
`docs/README.md`, and `docs/evidence/v1-implementation-status-v1.json`.
The baseline is generated only by the existing renderer. No containment,
persistence, provider, Registry, API, UI, quota, alert, activation, witness, or
receipt production file is authorized by 1.20.0.

This correction preserves the existing exact `0600` SQLite contract and exact
containment rejection. It changes no public/module/provider contract,
REST/OpenAPI schema, generated client, database schema, migration, retention,
backup, configuration, dependency, lockfile, SBOM, notice, licence, ADR,
provider profile, service, account, telemetry, or running-agent behavior.

### Activation and exclusions

After all combined preactivation checks pass, the one clean combined revision
uses only the already approved eighth two-invocation rollover. All earlier
revision/service-bound prerequisites are archived and recollected once through
their canonical commands, followed by one complete `AUTO-M5-EXIT` while the
quota witness is current. Plan approval is not activation, completion, or M5
acceptance.

This amendment authorizes no production permission relaxation, global umask,
post-copy exposure, owner-database mutation, fabricated database, containment
policy change, ignored or retried live failure, ninth rollover, general
deployment, witness/receipt rewrite, prerequisite reuse, provider login or
profile mutation, default-profile access, running-agent control, contract,
schema, migration, dependency change, M6, M7, M8, release, OpenAI API billing,
or macOS acceptance.

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
   official `/status` view at exact account/window membership, semantic roles,
   whole percentages, displayed reset precision, and at most 300 seconds of
   observation/collection skew; resets match absolutely unless two exact
   `100%` readings satisfy the bounded one-for-one rolling relation specified
   by plan 1.18.0;
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
