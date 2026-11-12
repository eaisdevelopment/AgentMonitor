# M02 registry module

Status: **Partially implemented for M3 `ST-REG-001`**. The deterministic
domain, migration, organization, query, and repository foundation is present.
Reconciliation, confirmation, and monitoring-graph persistence against a real
Claude discovery outcome remain **Not Run** until `ST-CLA-001` supplies that
outcome. No constructed provider record is an acceptable substitute.

Owner: `PLAN-M02`
Contracts: `registry.v1`, `CTR-REG-001..010`
Database head introduced by this module: `v1_0204`

## Purpose and boundaries

M02 owns organizations, provider definitions/installations, accounts, identity
claims and decisions, discovery candidates, monitoring profiles, account
resources, account-configuration references, registry changes, command
receipts, and its transactional outbox. It publishes stable AgentMonitor IDs
and safe masked views.

M02 does not invoke providers, collect capacity or runtime telemetry, inspect
credential contents, or expose private provider/profile locators. Provider I/O
belongs to provider adapters through M03. API and UI integration belong to P01
and P02 and are outside this implementation slice.

For the M6 cloud increment, the additive registry V1 access-target contract
keeps an official cloud access target distinct from every local provider
installation. The read-only
`ProviderAccessTargetReadPortV1` returns one exact target only while both the
target and its provider definition are active. It never reconciles, creates or
updates a target and exposes no credential reference. Composition must still
verify the returned provider authority and manifest fingerprint against the
reviewed source policy; the port itself neither authorizes provider I/O nor
claims provider identity.

Allowed dependencies are foundation/common and provider-system V1 contracts,
plus the SQLite persistence adapter. Domain and application code contain no
FastAPI, SQLAlchemy, provider SDK/CLI, operating-system, or UI dependency.

## Implemented invariants

- Internal organization, account, profile, resource, installation, candidate,
  claim, and decision IDs are opaque and distinct from provider identity.
- Ambiguous or non-unique identity evidence requires owner confirmation;
  conflicting evidence never overwrites an association.
- A confirmation command identifies the exact candidate `record_version` and
  exact SHA-256 `evidence_set_digest` shown to the owner. A stale version returns
  `registry_candidate_version_conflict`; changed evidence returns
  `registry_candidate_evidence_conflict`; neither path mutates registry state.
- A repeated command key replays only when its safe request fingerprint is
  identical. Reuse with different intent returns
  `registry_idempotency_conflict`.
- Discovery reconciliation records the receipt even when a valid real outcome
  contains no installation or account candidate. Reusing its operation ID with
  different safe input is a typed idempotency conflict.
- If current evidence changes after owner confirmation, the account and claim
  become ineligible/conflicted, the prior decision is invalidated but retained,
  and the candidate-to-account relationship remains available for review. The
  provider evidence class remains distinct from the owner-confirmation action.
- Monitoring-graph enrollment is one transaction containing the profile,
  resource, link, registry revision, safe history, outbox event, and command
  receipt. Its private locator is excluded from fingerprints, history, events,
  and public views. The locator fingerprint is the safe idempotency input.
- Protected default profiles fail authentication eligibility before locator
  resolution. An authentication target must also be active, AgentMonitor
  managed, locator-configured, compatible, and owner- or provider-verified.
- Resource parents are account-local and cannot self-reference. Migrations add
  composite account-local foreign keys for parent and profile-resource edges,
  and add no cross-module foreign key.
- Every stored instant is UTC. Public views distinguish withheld, unknown,
  unsupported, and unavailable fields from known masked values.

## M3 Task-2 application surface

The implemented application entry points are:

- `CreateOrganizationV1` and `ListOrganizationsV1`;
- `ReconcileProviderDiscoveryV1` and `ListDiscoveryCandidatesV1`;
- `ConfirmIdentityAssociationV1` and the reviewed-candidate-only
  `RegisterAccountV1` entry point;
- `ListAccountsV1`;
- `EnrollMonitoringGraphV1`, `ListMonitoringProfilesV1`, and
  `ListAccountResourcesV1`;
- `AlertScopeAndSubjectQueryV1`, returning a deterministic registry-only
  membership snapshot and its committed registry revision.

`RegisterAccountV1` cannot bypass identity review. It uses the same typed
confirmation command and repository transaction as
`ConfirmIdentityAssociationV1`.

List queries are bounded to 100 records in this M3 slice and are side-effect
free. The scope snapshot reads the complete selected membership in one database
transaction and never labels a truncated result complete. An empty completed
query returns an empty tuple. Database/policy failures return the sanitized
`registry_repository_unavailable` boundary error rather than a misleading empty
result.

## Identity and privacy model

`DiscoveryCandidateViewV1` exposes candidate/install IDs, safe evidence class,
record version, and the evidence-set digest required for confirmation. It does
not expose the source identity fingerprint, evidence payload, full identity,
email, provider output, path, or locator.

`ConfirmProviderIdentityFingerprintV1` is the only additive V1 seam for attaching
an adapter-approved, domain-separated SHA-256 provider fingerprint to an existing
owner-confirmed account. The owner command must name the exact account and its
current record version, provider/scheme/scope/version, authenticated principal,
UTC request time, idempotency key, immutable source/parser tuple, exact M06
observation reference, and expected evidence digest. It never selects the sole
account. The claim stores the M06 observation ID and the decision stores the
expected digest; the provider composition validates its own approved source tuple
before issuing the generic M02 command.
`ResolveProviderIdentityFingerprintV1` is read-only and returns only an exact
active owner-confirmed account, `unresolved`, or `conflict`; it never returns the
fingerprint. Both ports use the existing `reg_provider_identity_claim`,
`reg_identity_decision`, and `reg_command_receipt` records, so no migration is
introduced.

### Claude OTLP identity binding and evidence refresh

`agentmonitor.composition.claude_otel_identity_binding` is the local owner-only
entry point for the first exact Claude OTLP account binding and for replacing a
matching binding's stale evidence with a newly committed observation. It accepts only an
absolute AgentMonitor data root, explicit opaque account ID, and exact expected
account record version. The command
requires a controlling terminal and the exact interactive word `CONFIRM` before
opening the database, starting the receiver, or launching Claude. Decline,
redirected input, extra arguments, and any attempted fingerprint argument fail
without provider or database work.

After confirmation, the parent process transparently replaces itself with the
reviewed Claude executable in the owner's terminal. The locked receiver child
accepts only its authenticated loopback metric and exact launch/process/install
tuple. It first commits and reopens an unbound M06 session observation through
M04, then passes the in-memory domain-separated fingerprint, exact selected
account/version (rechecked before launch), fixed official source/parser tuple, committed session
observation ID, and reopened payload digest to
`ConfirmProviderIdentityFingerprintV1`. It reopens M02 through the read-only
resolver and checkpoints SQLite before acknowledging exporter success. The
fingerprint is never accepted on argv/stdin, printed, logged, or returned.

For an already resolved fingerprint on that exact account, a new explicit owner
command atomically updates the claim's evidence reference, invalidates (but does
not delete) the prior decision, appends a new owner-confirmed decision with the
fresh M06 payload digest, advances the registry revision and claim version, and
records the command receipt/outbox event. A conflicting fingerprint/account,
missing claim, stale account version, older verification time, or changed
idempotency request fails without partial state.

An initial binding launch intentionally leaves its already-committed session
correlation unresolved: its immutable evidence predates the new M02 decision. A
subsequent normal `agentmonitor.composition.claude_otel_runtime` launch resolves
the official metric to the confirmed account and commits it as
`automatic_matched`. An evidence-refresh launch is already resolved before M06
commit, so its fresh session is automatically matched and is the exact evidence
referenced by the refreshed M02 decision. Neither path modifies the protected
default Claude profile.

`PrivateProfileLocatorRefV1` is deliberately non-serializable and redacts its
string representation. Only the M02 persistence adapter may resolve it for its
owned `private_locator_ref` column. Provider credentials remain provider-owned
and are never stored in registry tables.

Registry history/outbox payloads contain only safe IDs, codes, aggregate
versions, registry revisions, and timestamps. Owner-facing mutable names may be
retained only in the protected `reg_registry_change` history described by the
approved M02 plan; they are absent from outbox payloads.

## Persistence and migrations

M02 owns these additive migrations:

| Revision | Owned records |
|---|---|
| `v1_0200` | registry state, organizations, provider definitions, accounts, changes |
| `v1_0201` | installations, discovery candidates, identity claims/decisions |
| `v1_0202` | monitoring profiles, account resources, profile-resource links |
| `v1_0203` | opaque account-configuration references |
| `v1_0204` | command receipts and transactional event outbox |

Fresh initialization runs the real Alembic chain on a file-backed SQLite
database. M02's migration range ends at `v1_0204`; the shared application
writable-schema receipt requires the current integrated target, presently
`v1_0504`. Downgrade is unsupported;
recovery preserves the database and uses a verified backup or approved forward
fix. Existing older databases require the separately approved offline
backup/quiescence migration workflow.

## Operations and diagnostics

Schema compatibility, SQLite integrity, and foreign-key checks must pass before
writes. A registry repository or schema failure makes the registry unavailable;
it never starts provider discovery or repairs data automatically. Diagnostics
may report only schema revision, safe reason codes, counts, and opaque IDs.

No new configuration key or dependency is introduced by this slice. Database
backup, restore, and retention continue to follow the deployment and operations
runbooks; full installed backup/restore evidence is not part of this task.

## Verification status

Deterministic evidence covers `M02-PURE-006/007`, `M02-PURE-010/011`,
`M02-PURE-013..023`, and `M02-PURE-025`. At the last integrated `v1_0504`
head, the full fresh Alembic chain, exact empty registry schema/account-local
graph constraints, organization atomicity/idempotency, and empty Task-2 query
surface passed against a real file-backed SQLite database. The current
concurrent checkout contains unintegrated M06 migration files and therefore
fails migration catalog validation; those database checks are not currently
Green. Supplemental checks cover three mutation-port signatures and selected
DTO fields only; they do not satisfy the broader `M02-ARCH-001/002` scenarios.
See
[M3 ST-REG-001 evidence](../evidence/m3-st-reg-001.md).

The following remain **Not Run**, not Passed:

- `M02-PURE-008/012` production identity-derivation and aggregate-collapse
  policies (current DTO inequality/type checks are supplemental only);
- `M02-PURE-009` protected prior/new rename and organization-move history;
- `M02-PURE-026` approved account-configuration reference policy;
- `M02-ARCH-002` full contract/schema/OpenAPI prohibited-field scan;
- reconciliation of a current real Claude `DiscoveryOutcomeV1`;
- stale-version/evidence-conflict confirmation against that real candidate;
- owner-confirmed account/profile/resource graph creation and receipt/history
  replay against that real subject;
- all other M02 live provider/account, API, browser, installed backup/restore,
  and platform scenarios outside this M3 Task-2 slice.

`M02-ARCH-001` is currently **Failed**, not Passed: the canonical repository
boundary checker reports three unresolved M06/runtime contract modules in the
concurrent M3 worktree. The registry-only signature check cannot override that
canonical result.

## Extension points and limitations

Task 3 must pass a current, typed, sanitized `DiscoveryOutcomeV1` through
`ReconcileProviderDiscoveryV1`; it must not insert registry rows or share raw
provider output. The owner then confirms the returned candidate using its exact
record version and evidence digest before graph enrollment can be verified.

Additional organization/account lifecycle mutations, persisted reauthentication
workflows, history pagination/retention, API/browser surfaces, and operations
hardening remain later M02 increments and are not claimed by `ST-REG-001`.

## M4 ST-FLEET-001 interim registry increment

### Verified managed Claude connection increment

The owner-directed [connection change](../plans/integration/claude-managed-account-connection-change.md)
adds explicit `activate_pending_account=False` to the internal V1 fingerprint
confirmation command. The default keeps the existing active owner-confirmed
precondition and historical request fingerprints. Explicit activation checks
the current record version and exact evidence, rejects a conflicting identity,
then atomically activates the existing account with its identity decision,
receipt, revision, and safe outbox. Its ID, label, organization, and disabled
monitoring preference remain intact. The operator separately enrolls a private
managed subscription graph and enables that selected account after verification.
No registry column, raw provider identity, credential, or public mutation route
is added. The service consumes the published resolution port to validate each
managed identity. See [real evidence](../evidence/claude-managed-account-connection.md).

M02 now provides admin organization rename, reorder, archive, and restore, plus
pending account registration, rename, group assignment, monitoring preference,
archive, and restore through its versioned V1 ports. Writes use the existing
M02 tables, registry revision, optimistic record versions, idempotency receipts,
change history, and outbox; there is no new migration. P01 exposes the operations
through authenticated V1 routes and P02 consumes the generated client. Pending
registration records owner-entered metadata only and does not assert provider
identity. Monitoring enablement checks a confirmed identity and eligible active
profile/resource. See [M4 interim evidence](../evidence/m4-st-fleet-001-interim.md)
for real-boundary results and the unresolved six-account gate.


## Organization provider coverage (M6 increment)

CTR-REG-013 1.0.0 adds durable owner declarations for an organization's own
account, use of another organization's account, or an explicit unavailable
reason. The reviewed scope is recorded in
[the M6 coverage impact plan](../plans/integration/m6-cloud-scope-outcomes-contract-impact.md).
These declarations are separate from provider identity, credential access,
quota, and financial pool aggregation.

Schema v1_0719 adds current and immutable revision tables without backfill.
The runtime API uses `read:accounts` / `write:accounts`; writes require ordinary
CSRF proof, an operation key and the current ETag. Version zero creates only an
absent declaration. Revocation retains history and never disconnects an account.
The selected account version fences reassignment races. Structural changes
invalidate declarations permanently; renames and monitoring toggles preserve them.

Organizations contains a collapsible **Provider coverage** editor with named
account/source-organization choices. An incomplete organization list disables
shared choices explicitly; no unavailable declaration is selected automatically.
The editor distinguishes a committed write from a failed refresh. This increment
remains intermediate until its installed-service and canonical M6 checks pass.


## M7 billing runtime authority

The additive `BillingAccessTargetV1` / `BillingAccessPortV1` under CTR-REG-014
1.3.0 resolve Anthropic/OpenAI billing resource, current credential generation,
scope epoch and verification/monitoring purpose without a CLI profile or
subscription identity prerequisite. M02 re-resolves this target in the caller's
report-write transaction; changed/disconnected/archived authority is rejected.
This does not prove provider permission or enable monitoring. Ollama usage still
needs its existing cloud graph adapter. See the
[billing authority evidence](../evidence/m7-billing-authority-2026-11-11.md).

CTR-REG-014 1.7.0 adds explicit reconnect for a restored account's disconnected
billing connection. Account/connection/scope versions and idempotency fence one
transaction returning it to pending/disabled. Scope, resource, pool membership
and retained reports stay unchanged; retired credentials and old access checks
do not regain authority. Reconnect requires no active/pending credential. P02
then exposes the existing local setup command and Check workflow. See the
[bounded reconnect evidence](../evidence/m7-billing-reconnect-2026-11-12.md).
