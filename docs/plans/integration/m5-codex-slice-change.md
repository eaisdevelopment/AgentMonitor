# Change plan: executable V1-M5 Codex slice

- Status: **Approved for root-owned V1-M5 implementation and live verification**.
- Plan version: `1.1.0`; root integration review: 2026-10-07.
- Safety correction: exact-version review proved that authenticated app-server
  queries may perform Codex's automatic credential refresh. The approved
  managed-auth lifecycle therefore classifies those queries as
  `managed_profile_write`, and an empty/uninitialized managed root is rejected
  before any app-server child starts.
- Owner: `PLAN-INT`, with A02 provider behavior owned under this bounded change.
- Parent plans:
  [V1-M5 milestone](../../superpowers/plans/2026-09-19-agentmonitor-v1-m5-codex-slice.md)
  and [A02 adapter](../adapters/codex/plan-v1.md).
- Authority: the active owner objective, **fully implement M5 with our SDLC and
  runbook**. This focused approval supersedes the A02 Draft prohibition only
  for the exact M5 scope below; the remaining A02 and OpenAI API lanes stay
  Draft.
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
an owner reason. The file accepts no private identity fingerprint; distinct
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
| 7 | `M5-CDX-GATE-001..014` | no fail-closed milestone command | register and implement `AUTO-M5-EXIT` | exact-revision four-account/process/browser/local-gate receipt with zero skips |

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
5. a genuine Codex capacity condition traverses
   the existing alert lifecycle through dedupe, browser presentation, an owner
   action, and source-proven recovery;
6. real file-backed SQLite, production HTTP, generated client, built Chrome,
   provider capability/health/failure isolation, and zero registry mutation by
   verification; a real syscall trace of the production managed-profile
   identity and quota calls must prove zero default-profile access or writes
   and confine declared provider-controlled auth/runtime writes to the selected
   managed profile;
7. the running service's Operations version inventory reports the exact clean
   implementation revision selected by the gate, rather than trusting the
   launch working directory or the checkout's later state;
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
authoritative `/usage` reconciliation, and the capacity-alert
open/action/recovery witness happen beforehand through the running application
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
