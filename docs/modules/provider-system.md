# M03 provider-system module

Status: **provider-neutral protocol and compatibility persistence implemented;
the bounded Claude Code 2.1.289 admission passed; V1-M4 is accepted at its
revision-bound current gate**.

Owner: `PLAN-M03`

Contracts: `CTR-PROV-001..008` V1

Database revision: `v1_0300`

## Conditional scheduled cloud-source admission

The additive `CTR-PROV-003` V1 scheduled-source policy and proof values keep a
one-shot owner-authorized probe distinct from recurring collection. M03 admits
recurring work only for the exact current account, credential-binding
generation and cloud target whose real probe lineage has a response-received
successful M04 run and a matching committed M05 payload. The reviewed policy
binds the provider authority, source and adapter fingerprint, payload schema,
request count, concurrency, retry, minimum interval, rate, fairness and
invalidation policy versions.

The proof is an ephemeral composition value, not a database permission or a
global provider-manifest claim. Composition must rebuild it before every
dispatch from current M02, M04 and M05 views. Rotation, disconnect, archive,
monitoring disable, target change, owner-authorization removal, source-policy
change, an unresolved outcome, 401/403, or incompatible provider data blocks
admission. Rate limiting, temporary provider/network failure and a temporarily
unavailable credential store retain the prior generation-bound admission but
remain subject to M04's durable gate and backoff. The value carries only
`owner_asserted` identity provenance and cannot claim provider identity, team
membership or sharing scope.

This is a compatible additive use of `CTR-PROV-003` V1. It adds no database,
HTTP, generated-client, event or dependency change. The Ollama composition
still needs a narrow M04 read that classifies the latest exact binding/source
outcome without interpreting free-form reason text, then projects the actual
M02/M04/M05 receipts into this proof.

## Exact Claude Code 2.1.289 admission

The owner-approved
[`A01-M03-CLAUDE-2-1-289-001`](../discovery/m0/m0-to-m03-claude-2.1.289-v1.json)
record admits only Claude Code `2.1.289` on Linux x86-64 for read-only
installation discovery, subscription quota, authentication health, identity
verification, and owner-interactive official login to an AgentMonitor-managed
profile. The quota adapter and parser are `1.0.3` and the source remains
`claude.usage.ax-screen-reader.v1`. Unknown versions fail closed;
protected-default writes, credential handling, and running-agent control are
outside the admission. Generic `local.process.observation` remains an A04/M06
platform/runtime capability and is not published by the A01 manifest.

The workstation default `claude` command observed on 2026-10-11 is `2.1.296`
and remains outside this admission. The retained exact `2.1.289` native
executable is currently absent, so quota, identity and authentication reads
remain unavailable until a separately approved exact-version admission is
completed. Historical `2.1.289` observations stay visible as stale and are not
presented as current. The unretained `2.1.282` executable remains the separate
OTLP requirement; no version is substituted for another.

Process-only discovery is independent of that quota/auth admission. For
`local.process.observation`, A01 may enumerate at most 32 owner-controlled
native executables in the existing Claude versions directory, validate each
file identity and official bounded `--version` banner, and pass the verified
executable handles to A04/M06. This reveals current OS metadata only; it does
not authorize quota parsing, authentication, identity reads, provider writes or
process control for those versions. Unsafe, changed, invalid, timed-out or
deleted executable images are omitted. The view therefore cannot prove a
complete fleet when a running image is no longer present on disk. Detected
permission, process-exit, deadline and candidate-limit omissions mark the scan
partial. If no safe native executable remains, discovery fails closed rather
than reporting a successful empty Claude fleet.

The public contracts remain `CTR-PROV-001..008` V1. In particular,
`ClaudeSubscriptionQuotaV1@1.0` keeps its closed three-key allowlist. Claude
Code `2.1.289` may render one bounded model-specific weekly card outside that
allowlist. A01 validates and omits that card, returns `partial` with
`claude_model_specific_window_unsupported` and `availability=unsupported`, and
retains the required current session and all-model weekly windows. Multiple
such cards, an unallowlisted shaped label, duplicate/conflicting values, or a
missing required window fails closed. There is no provider-extension, API,
generated-client, event, or database-contract change.

A recognized quota window may contain a valid provider-reported percentage and
no reset line. A01 preserves that percentage and publishes the existing
`ClaudeResetDisplayV1` Unknown state: no value, Unknown availability, and
Unknown precision. It never infers reset text or an instant. A present reset
still requires the existing bounded provider-display form; malformed or
conflicting reset-shaped text fails closed rather than becoming Unknown. This
changes no V1 schema or public API.

The official OTLP session lane is separate. Its adapter remains `1.0.0` and
its manifest remains exact-pinned to Claude Code `2.1.282`. Quota admission on
`2.1.289` does not widen OTLP support. When the old executable is absent, OTLP
preparation returns `claude_version_unverified` before profile access or a
monitored launch.

Exact-version installation discovery produces one `DiscoveryOutcomeV1@1.0`
installation and zero account candidates. M02 consumes it through the existing
`ReconcileProviderDiscoveryV1` port so a retained installation row can advance
through one strict transaction without changing its stable ID or the
provider-scoped account, monitoring-profile, profile-resource-link, or
discovery-candidate records. The same transaction creates and verifies the
operation receipt before commit. The canonical command first acquires the
stable owner-only exclusive service lock and returns Blocked without mutation
if AgentMonitor is running. This adds no public contract, schema, migration, or
dependency.

Focused native checks passed exact installation selection, genuine quota,
managed identity/authentication/quota reads, and the fail-closed OTLP version
gate. The stopped-service owner reconciliation also preserved the existing
opaque installation ID while advancing the registered version from `2.1.282`
to `2.1.289`; privacy-minimized digests for six accounts, one candidate, six
profiles, and six resource links were unchanged. See the
[exact admission evidence](../evidence/claude-2.1.289-admission.md).
One new owner-completed `2.1.289` managed sign-in and its genuine sparse-reset
quota read passed. The authenticated M4 gate then passed for six accounts, two
organizations, six distinct identities, six fresh post-restart quota/history
lineages, one owner-confirmed live process link, and zero mutations. The
revision-bound `AUTO-M4-EXIT` receipt and explicit owner countersignature record
formal V1-M4 acceptance.

The canonical M4 technical lane now runs `AUTO-M3-TEST` plus exact current
authentication/quota, manifest/parser, installation/reconciliation, and OTLP
version-gate tests. Its fleet witness requires exact source, adapter/parser,
provider-version, and decision-reference provenance in every current window
and matching history point. The built account page must render the exact
source, adapter/version, and provider version for every quota window.

## Persistence boundary

The bounded [managed Claude connection](../plans/integration/claude-managed-account-connection-change.md)
extends `CTR-PROV-005` V1 quota identity receipts with optional
`profile_protection` (existing callers retain `protected_default`). The API
publishes it as `unknown` until a current service collection is attested.
Managed identity is verified around the provider read before quota is
committed, and against the registry before display. The legacy wire `scope`
remains for compatibility; consumers use `profile_protection` for actual
profile selection. This operator increment does not enable the generic
dashboard reauthentication workflow. See
[real connection evidence](../evidence/claude-managed-account-connection.md).

M03 owns only `provider_system_compatibility_assessment` and
`provider_system_event_outbox`. The SQLite repository accepts the public
`CompatibilityAssessmentInputV1` and returns immutable safe compatibility
views. It never calls a provider or reads a profile.

An exact replay of the current canonical compatibility input returns the
existing assessment and does not append another event. Request metadata
(`assessed_at` and `correlation_id`) is excluded from that fingerprint. A
changed compatibility input creates a new assessment, marks the prior row
non-current, links the supersession, and appends one outbox event in the same
`BEGIN IMMEDIATE` transaction. The transaction also serializes nullable
installation/source scopes, for which SQLite's ordinary unique-index `NULL`
behavior is insufficient. Discovery of more than one current row fails closed.

History and pending-outbox reads require an explicit limit from 1 through 100.
Every query validates opaque-ID types and bounds, capability syntax, optional
source syntax, optional installation-ID type, and limits before opening the
database. Invalid query input crosses the boundary only as
`provider_system_query_invalid`.
Persistence and corrupt-record failures cross the adapter boundary only as
stable `ProviderSystemRepositoryErrorV1` codes; SQL, paths, stored values, and
driver messages are not exposed.

## Data and privacy

Compatibility rows contain safe scalar IDs, declared versions/states, stable
reason codes, manifest/input SHA-256 fingerprints, UTC instants, and
supersession metadata. Outbox rows contain only safe event routing metadata.
Neither table accepts credentials, account identity, profile paths, provider
payloads, prompts, responses, source content, or free-form provider errors.

Non-available provider versions require the value, scheme, and rule to all be
absent at the public contract, repository, and `v1_0300` database-constraint
boundaries. DTO construction rejects naive/non-UTC assessment and validity
instants, and persisted non-UTC timestamps fail closed as invalid records.
The database also requires lower-case hexadecimal SHA-256 fingerprints,
canonical microsecond UTC `Z` timestamps, nondecreasing validity, the closed
compatibility/version-scheme vocabularies, and complete available-version
tuples.

Outbox DTO and database rows require
`occurred_at <= recorded_at <= available_at <= claimed_at <= delivered_at`
for timestamps that are present. Pending rows have no claim/delivery time;
claimed rows have one positive attempt and no delivery time; delivered rows
have both times and a positive attempt. The implemented repository publishes
and lists only the bounded pending lifecycle. Claim, retry, delivery, consumer
receipt, and replay operations remain Not Run and are not implied by these
storage invariants.

## Verification and limitations

Real file-backed SQLite tests cover reopen/round-trip, deterministic replay,
supersession/history, concurrent nullable scopes, exhaustive query validation,
direct-SQL constraint rejection, bounded pending ordering, and assessment/
outbox rollback on an actual SQLite write failure. See
[the ST-CLA-001 persistence evidence](../evidence/m3-st-cla-001-provider-system-persistence.md).

This persistence evidence alone does not establish Claude conformance or
milestone completion. The exact `2.1.289` adapter, selected live provider
profiles, and installation reconciliation are covered by the current admission
section above. The complete `ST-CLA-001` collection/capacity/runtime, API,
built-browser evidence and aggregate M4 acceptance are established separately;
neither is implied by this persistence slice.
