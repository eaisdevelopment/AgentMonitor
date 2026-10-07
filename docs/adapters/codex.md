# Codex CLI adapter

Status: **implemented for the approved V1-M5 slice; live fleet acceptance is
pending `AUTO-M5-EXIT`**.

Owner: `PLAN-INT` for the focused M5 integration and A02 for provider behavior.

Requirements: `FR-ACC-001/004..006`, `FR-AUTH-001/002/004..006`,
`FR-QUOTA-001..006`, `FR-COL-003..008`, `FR-DISC-001/003/004/006/008`,
`FR-STATE-001/002`, `FR-SAFE-002`, `NFR-SEC-001`, and
`NFR-PRIV-001/002`.

Contracts: compatible V1 use of `CTR-PROV-001..008`,
`CTR-REG-001/002/004..006/009/010`, `CTR-COL-002/004/006/007`,
`CTR-CAP-001/003/004/007`, `CTR-RUN-001..003/006/007`, `CTR-PLAT-001`,
and `CTR-OPS-006`.

## Admitted tuple

The adapter admits only Codex CLI `0.160.0` on Linux x86-64. Its capability
manifest is `codex-adapter.v1`, adapter version `1.0.1`, parser version
`1.0.0`, and provider protocol version `1.0.0`. The discovery decision is
`M5-CDX-0-160-0-002`, bound to the corrected side-effect decision in the
[Codex read-side-effect evidence](../evidence/m5-codex-read-side-effect-blocker.md)
and the generated-schema digest retained in the original
[Codex discovery evidence](../evidence/m5-codex-0.160.0-discovery.md).

Another provider version, platform, schema bundle, executable identity, or
mapping fails closed. AgentMonitor does not infer compatibility from a nearby
version.

## Exact external operations

The closed allowlist is:

- `codex --version` for bounded installation admission;
- `codex login` for an owner-started official login in one
  AgentMonitor-managed `CODEX_HOME`;
- `codex app-server --listen stdio://` with only the required
  `initialize`/`initialized` handshake;
- `account/read` with explicit refresh disabled for identity continuity; Codex
  can still perform its documented automatic authentication maintenance; and
- `account/rateLimits/read` with reset-credit details excluded and Luna
  reserve support disabled.

Each child uses the exact revalidated executable, an argument vector, no shell,
an owner-only managed root and working directory, a minimal environment,
bounded JSONL lines/output, a deadline, null stderr, and owned-child cleanup.
Raw app-server objects and provider error text do not cross the adapter.
Managed login has the manifest's ten-minute owner-interaction deadline. Each
app-server request remains bounded at 30 seconds; service shutdown allows 45
seconds to include its at-most-four-second owned-child cleanup and local drain.

Before app-server starts and after its owned child is cleaned up, the adapter
checks only safe metadata for the official file credential store. It never
opens or parses that file. The store must be a single-link, owner-owned regular
file with private mode and bounded size. App-server rejects an absent store as
authentication required, and both paths reject a symlinked, hard-linked,
public, nonregular, or unbounded store. Initial login permits absence before
launch, then applies the same metadata rule to any resulting store after child
exit or cancellation. After official owner login, identity,
authentication-health, and quota queries are truthfully classified as
`managed_profile_write` because Codex may refresh credentials or maintain
runtime state inside that selected root. Installation discovery remains
`read_only`.

The app-server interface is experimental in this CLI release. The manifest
therefore records the identity, authentication-health, quota, and managed-login
sources as exact-version experimental capabilities. Installation discovery
uses the supported version command. This admission does not enable arbitrary
app-server methods, browser cookies, OpenAI API billing, or provider account
mutation.

## Managed account connection

Administrators create Codex account records through the existing account CRUD
API and assign organizations independently of provider login. A connection
starts only after the authenticated owner submits the account connection form.
The owner supplies the intended email and completes Codex's official browser
flow; AgentMonitor never receives a password, MFA value, authorization code,
cookie, or OAuth credential.

Each record has a deterministic private managed root below
`<data-root>/profiles/codex/`. Roots must be absolute, owner-only directories
inside that boundary and cannot be symlinks. Codex owns its credential file;
AgentMonitor does not read it. The default Codex profile is never selected,
read, moved, logged out, or rewritten.

After login, the connection coordinator reads the managed profile identity,
compares it with the owner-selected email, and enrolls the existing
provider-neutral monitoring profile, subscription resource, and identity
fingerprint graph. Enrollment is transactional and resumable when a prior
attempt reached only part of the registry graph. A different returned identity
produces a terminal `wrong_account` result for that account record. The managed
profile is quarantined from retry for that record; AgentMonitor does not log it
out or delete provider state.

Connection state is retained only as bounded owner-only receipts containing
opaque identifiers, state/reason codes, and timestamps. Restart changes an
in-progress flow to a cancelled state instead of pretending it completed.

## Quota and identity collection

The scheduled collector selects only active, identity-bound, effectively
enabled Codex accounts with one compatible managed subscription profile and
one linked subscription-pool resource. It revalidates the installed CLI and
the registry installation before provider I/O.

One successful run reserves and uses at most three app-server target requests:

1. one adapter `account/read` before quota;
2. one adapter `account/rateLimits/read`; and
3. one adapter `account/read` after quota.

The final identity is exposed to the collector as a one-shot receipt bound to
the exact operation and correlation IDs. It is cleared before every request
and consumed even when a caller supplies mismatched selectors. This preserves
identity-before/quota/identity-after continuity. No startup or between-run
identity reattestation is allowed; a fresh durable quota run establishes the
current in-process identity receipt after restart.

The adapter maps only closed rate-limit window fields into the provider-neutral
quota contract. Native limit IDs and primary/secondary roles stay separate.
Missing values remain Unknown or Unsupported. AgentMonitor does not combine
subscription windows with OpenAI API usage, credits, cost, or budgets.

Collection uses the existing real SQLite admission, fencing, idempotent commit,
current projection, history, health, and event contracts. The admission budget
is three provider request units in one five-minute account/source window with no
automatic provider retry. A run may terminate after fewer requests, but no
second run can exceed the reserved bound.

## API and dashboard

The provider-neutral identity resource is
`GET /api/v1/accounts/{account_id}/provider-identity`. It returns the account's
provider key, verified identity and organization when current, collection
lineage, provider version, exact identity source, and profile protection. The
older `/observed-identity` resource retains its Claude-specific V1 contract and
rejects Codex with `provider_identity_legacy_unavailable`.

Overview, account activity, capacity/history, provider capabilities,
connection status, and process locations all use the generated versioned API
client. The UI displays Codex provider labels and connection instructions
without provider-specific database or filesystem access. Accounts beyond the
first 200 are reached through the visible continuation control, and alert
delivery traverses all account pages only while their Registry membership
matches one stable complete snapshot.

## Process and operations evidence

Linux discovery matches the exact current Codex executable through the existing
safe `/proc` selector. It reads only same-user PID/start identity, executable
identity, safe hierarchy metadata, and working directory for the authenticated
owner view. It does not read argv, process environments, memory, terminals,
prompts, responses, tools, or source content. Process state and account
ownership remain Unknown unless an existing guarded owner association proves
the account. AgentMonitor never signals, stops, restarts, routes, or switches a
Codex process.

The `provider.codex` operations component performs the same bounded real
installation admission. Exact `0.160.0` reports Healthy with that component
version. Missing, unsafe, changed, or unverified installation state reports the
optional component Unavailable and does not falsely block core service
readiness.

## Failure and privacy behavior

- Wrong identity, changed executable, unsafe root, invalid JSONL, output limit,
  deadline, provider unavailability, and authentication-required conditions
  cross boundaries only as closed safe codes.
- Identity fingerprints are one-way registry links. Email is returned only to
  the authenticated owner where required for verification; credentials and raw
  provider objects are never persisted.
- Logs and gate receipts contain no account identity, managed-profile path,
  provider payload, credential, prompt, response, source content, or arbitrary
  environment value.
- No dependency, database migration, license, default-profile write, or process
  control capability is introduced by this adapter slice.

## Verification

Pure contract and parser tests cover closed shapes, provenance, exact mapping,
identity continuity, request receipts, and failure classification. Real local
tests exercise the installed CLI, bounded subprocesses, private empty managed
roots, file SQLite, loopback HTTP, generated client, built UI, and Linux
process observation. Owner-authenticated managed profiles and current native
quota require the live owner selectors and are never replaced by fixtures.

The sole milestone completion command is:

```bash
python3 tools/automation/run.py AUTO-M5-EXIT
```

Until that exact clean-revision command passes with its four account outcomes,
fresh quota/history, five to six real processes, real alert lifecycle, browser
checks, and zero skipped tests, V1-M5 remains incomplete.
