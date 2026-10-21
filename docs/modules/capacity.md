# M05 capacity module

Status: **M4 capacity delivery implemented and its standalone milestone gate
Passed; the focused M5 1.9 quota-witness policy projection is local
deterministic Green**. The focused increments below publish current native
metadata, the M05 30%/15% health policy, revisioned scope coverage, pure
burn/forecast derivations, current alert facts, and typed existing commit
notice delivery. Their later real integration, post-upgrade migration, fleet,
browser, and canonical results are recorded in the
[M4 completion evidence](../evidence/m4-completion.md). The fourth M5 service
rollover activated exact `d81afab`; its owner-outcome and alert witnesses are
current, but the authoritative quota witness created no file after the real
policy-shape Red. The approved fifth rollover and `AUTO-M5-EXIT` are Not Run.
Full M05 master-plan and V1 release acceptance are not claimed.

Owner: `PLAN-M05`
Contracts: compatible `capacity.v1` extensions to
`CTR-CAP-001/003/004/005/006/007`, existing `CTR-COMMON-003/004/007`,
`CTR-COL-006`, `CTR-REG-009`, `CTR-EVT-001`.
Database allocation: `v1_0500..v1_0504`, additive `v1_0703/0704`.

## Purpose and boundaries

M05 owns immutable capacity observations, exact measures, native quota-window
definitions, current and health projections, commit receipts, derivation and
forecast allocations, retention audit state, and its transactional event
outbox. It never invokes a provider, reads provider state, infers missing
values, or controls a running process.

M04 owns admission, request/run history, leases, fencing, request budgets,
retry state, and collection terminalization. Provider-specific normalization
stays in the provider adapter. M05 accepts only a closed
`ProviderQuotaInputV1` with complete M03 provenance through the versioned commit
boundary. Queries do not trigger collection.

## Exactness and truthfulness

- Numeric values use a canonical decimal coefficient and scale. Binary floats,
  non-finite values, redundant trailing zeroes, negative zero, over-scale
  values, negative quota quantities, and incompatible units are rejected.
- Exact zero is an available value. Unknown, unsupported, not applicable,
  withheld, stale, and unavailable collection conditions are not converted to
  zero.
- Every provider-native quota window remains separate. A complete batch is
  bounded to 32 unique windows; subscription and API pools are never summed.
- Partial input carries a closed, explicit omission-code set; warnings alone
  cannot silently turn missing scope or fields into a complete result.
- A canonical digest is recomputed from the closed payload before persistence.
  Window order is normalized by typed identity, and a caller-supplied
  mismatching digest is rejected.
- `CTR-CAP-001` provenance mechanism versions use the existing bounded safe
  ASCII token grammar, including `+` for SemVer build metadata. This compatible
  validation widening preserves an admitted provider schema digest without
  changing the meaning of any previously accepted version.
- The Claude mapper stores the reported rounded percent-used value. Because the
  accepted source does not report a trustworthy limit, remaining value, or
  remaining ratio, those fields remain explicitly Unknown. Reset display text
  is not parsed into an invented instant.

## M4 current views and pure derivations

Current quota views expose actual stored semantic role, definition version,
registry revision, current projection version, completeness and reset evidence.
Constraint evidence is nullable: an old definition remains Unknown until an
actual fresh collection creates a definition with the reported constraint flag.
There is no backfill from labels or guessed provider semantics.

The default M05 health thresholds are 30% constrained and 15% critical. The
classifier runs on actual current selected observations inside the commit
transaction and during freshness-aware reads. Partial or unresolved constraints
cannot become complete Available health. Alert rules and UI coloring remain
separate consumers of published facts.

`GetCapacityAggregateV1` receives one immutable public M02 scope snapshot with
account/resource metadata at the same registry revision. It rechecks membership
before and after its bounded reads, rejecting a race. Eligible, covered, missing
and excluded accounts and health/freshness counts remain explicit. Native
window groups are inventories. Absent identity equality or additive-pool
evidence means Unknown relationship and no summed percentage or numeric total.

`ListCapacityForecastsV1` reads the actual recent immutable history. Its pure
bounded-secant method requires three samples, 900 seconds of span, no gap over
900 seconds, matching source/definition/native unit, an evidenced reset segment,
positive monotonic consumption, fresh latest evidence and valid precision
bounds. It returns an explained rate and exhaustion interval only with those
inputs; otherwise it returns explicit insufficiency/staleness/conflict with no
numbers. Rounded values without evidenced bounds and the current Claude source's
unknown reset instant cannot produce a numeric forecast. Query derivations are
read-only; durable forecast generation/alerts remain a separate integration.

`CTR-CAP-005` publishes `CapacityAlertConditionV1`, its bounded query and the
`ListCapacityAlertConditionsV1` protocol. Its generation is the actual current
projection `record_version`, never target generation. Fresh complete native
remaining ratios produce exact canonical basis points. The supported native
percent-used source uses the existing `100_minus_used_percent` allowance and
labels its denominator `used_percent_complement`, preserving original rounded
precision/confidence and observation provenance. Unknown, stale, conflicted or
partial sources carry no remaining/exhausted value and cannot imply recovery.

`ReadCapacityEventsV1` and `AcknowledgeCapacityEventV1` publish typed delivery of
the existing `capacity.committed.v1` notice. Its closed payload remains exactly
capability ID, projection count and terminal commit state. The stable cursor is
the immutable producer sequence; historical producer version comes from the
actual matching M05 receipt. A notice asks a consumer to read current facts; it
does not assert condition truth. Acknowledgement verifies the exact digest and
preserves its committed consumer receipt reference. Identical retry is
idempotent; different proof conflicts. No other module's tables are read. The
caller must have committed its receipt before acknowledgement. Since that port
does not supply consumer build version, a new delivery records explicit Unknown
consumer version; historical known versions are retained.

## Commit and projection behavior

One `(collection_run_id, capability_id)` has one durable receipt. Replay with
the same generation, schema, and recomputed payload digest returns the original
receipt; any difference is `capacity_commit_conflict` and preserves the first
commit.

The repository inserts immutable provenance, window definitions, observations,
exact measures, current projections, a conservative health projection, the M05
event, and the receipt in one short real SQLite transaction. `stored_at` is the
actual storage instant and remains distinct from provider `observed_at` and
collector `collected_at`. Current projections advance by semantic observation
time, not arrival order; an older observation remains history, and an equal-time
different payload marks the projection conflicted.

An accepted `complete_scope` snapshot also evaluates current-projection window
keys whose definitions are `active` or `not_observed_currently` inside the
exact provider, installation, account, resource, capability, and
identity-scheme scope. An active key omitted by that snapshot changes to
`not_observed_currently` only when the incoming semantic observation time is
strictly newer than that key's current observation. `partial_scope`, failed,
older, equal-time, cross-scope, or identity-unproven input cannot retire an
omitted key. A matching key returns to `active` only when a later accepted
observation wins the same strict-newer projection precedence.

Each later strictly newer complete snapshot that continues to omit an already
`not_observed_currently` key advances its lifecycle watermark without creating
a quota observation. A delayed presence older than that latest absence cannot
reactivate the key. `retired` definitions do not participate.

For this internal lifecycle decision, a definition's `last_observed_at` is the
semantic watermark of the latest accepted presence or complete-scope absence
observation for that native key. `first_observed_at` remains the first genuine
presence observation. Carrying the lifecycle watermark across semantic
definition versions prevents an out-of-order reappearance from undoing a newer
absence decision. This is definition lifecycle metadata; quota history remains
the immutable genuine observation rows and is never synthesized from absence.

Current window, account, health, forecast-refresh, availability, alert, API,
and dashboard paths consume only active definitions. Inactive definitions and
all of their immutable observations, measures, provenance, receipts, and event
history remain available to history queries. The lifecycle update occurs in
the existing commit transaction before current health, events, and the receipt
are derived; no provider-shaped repair, synthetic replacement observation, or
schema migration is involved.

`ListQuotaWindowsV1`, `GetCapacityHealthV1`, `GetAccountCapacityV1`, and
`GetCollectionCommitStatusV1` are provider-neutral query boundaries. Window,
health, and account queries require explicit capability and `as_of` semantics;
health is evaluated against `valid_until`, not lexical capability order. Empty
history returns an empty window tuple or a bounded not-found error; it never
returns placeholder telemetry.

## Persistence allocation

The M05 base chain through v1_0504 creates 24 empty tables and no rows:

| Revision | Allocation |
|---|---|
| `v1_0500` | resource/window/budget definitions; immutable quota, budget, usage, exact usage measures, and provenance |
| `v1_0501` | run/capability receipts, observation references, generic current projections |
| `v1_0502` | health/aggregate/availability projections and M05 outbox/delivery |
| `v1_0503` | derivation lineage, forecast projection, measured history indexes |
| `v1_0504` | fenced retention audit and export-cursor indexes |

All foreign keys remain within `capacity_*`; collection, registry, provider,
and operations identities are opaque scalar references. The migration chain is
expand-only and downgrade is unsupported. Later budget, forecast, retention,
export, and provider-extension behaviors use this frozen allocation but are not
claimed by M3 Task 4. No extension-value table is allocated because no approved
V1 extension consumer requires one; unknown provider fields are discarded.

## Security and privacy

Persisted data is restricted to opaque IDs, exact operational quantities,
field states, safe labels approved by the provider contract, safe codes,
versions, digests, and UTC instants. Raw provider output, reset display text,
prompts, responses, source code, arbitrary environment values, credentials,
tokens, profile paths, and free-form provider errors have no persistence field.

No dependency or configuration key is introduced. Provider-owned profiles are
read-only and were not modified during this slice.

## M4 durable current capacity projections

The focused I04 increment adds a separate `SqliteCurrentCapacityRepositoryV1`
over the existing owned quota history. `RefreshCurrentCapacityProjectionsV1`
pages current native windows (at most 32), derives a forecast only from the
latest compatible definition, source and exact reset segment, then rechecks
the actual source projection generation and selected immutable observation IDs
under one short `BEGIN IMMEDIATE` transaction. It writes the durable forecast,
capability availability condition and matching typed outbox changes atomically.
The persisted derivation digest binds the selected input set to the current
projection generation and observation, so a later source generation cannot
silently reuse older derivation provenance.
An identical reread leaves record versions and events unchanged. The query-only
I01 forecast still has a synthetic generation and is not an alert source.

`ListCurrentCapacityForecastsV1` and `ListForecastAlertConditionsV1` read only
complete persisted snapshots whose source window generation remains current.
The forecast alert uses the latest exhaustion bound conservatively. `before_reset`
is true only if the entire interval ends before an exact native reset; crossing
or unknown reset remains unknown. `ListCapacityAvailabilityConditionsV1` pages
independent capability streams by account/resource/capability. Current quota
facts do not include a per-observation provider identity-binding proof, so the
live capability producer reports `unknown/identity_binding_unproven` even for
fresh values. It cannot declare healthy recovery. Auth and collector ingestion
wait for normalized published runtime ports and composition.

`ReadCapacityProjectionEventsV1` is a separate closed union over original
commit notices and the new forecast/availability changes. The original
`ReadCapacityEventsV1` remains commit-only. New event `subject_version` is the
durable producer generation; original commit `subject_version` retains target
generation meaning. Both readers use the same producer sequence cursor and
exact digest acknowledgement proof. The internal ack call still requires an
actual committed consumer receipt established by composition; that live proof
is Not Run in this M05 assignment.

Pinned `v1_0707` adds nullable forecast snapshot/source fields, a nullable
producer-version field on the owned outbox, and one independent current
availability table with source-stream uniqueness. Existing forecasts, notices
and availability signals are preserved without backfill. No owner installation
was migrated or provider profile modified in this assignment; testing used a
private temporary SQLite backup of genuine owner data, removed afterward.

## Operations and incomplete acceptance

### M5 quota-witness policy projection

The real `AUTO-M5-QUOTA-WITNESS` attempt against exact `d81afab` completed its
authenticated API, rendered DOM, retained-history, Registry, identity,
collection-lineage, and zero-mutation checks. Final reconciliation then
returned `m5_quota_witness_input_invalid` and created no private witness. The
validated browser row carries `current_observation_id` solely to bind the
current reading to immutable history, while the existing quota reconciliation
policy admits exactly five provider-neutral quota fields.

The approved 1.9 correction retains that opaque observation ID through the
independently rebuilt browser/history digest, then returns the already
validated five-field projection to quota policy. Its focused Red failed at the
closed reconciliation boundary; Green passed the new shaping case and the two
strict rejection variants, and the complete quota-witness file passed `27`
tests. Ruff, format, and strict mypy also passed. No Capacity contract, public
API, schema, migration, provider payload, dependency, persistence rule, or
quota value semantics changed. The fifth service rollover is a separate
revision-binding operation and remains locally Green but live Not Run.

Writable startup requires the reviewed migration catalog, compatible schema,
SQLite policy, integrity check, and foreign-key check. Receipt conflicts,
canonical-value violations, schema mismatch, and repository failures fail
closed with bounded codes.

The following are **Blocked / Not Run**, not Passed:

- fresh post-0703 provider-to-M04-to-M05 classified commit/receipt replay and
  persisted default-policy inspection in this M4 assignment;
- nonempty exact delivery acknowledgement/reopen with an actual committed
  consumer receipt, pending root's integrated dispatcher proof;
- naturally observed numeric forecast with a trustworthy native reset segment
  and uncertainty bounds; the current source does not supply those facts;
- later budget, retention, export, API, browser, scale, backup, and
  restore behavior.

See [M3 ST-OBS-001 evidence](../evidence/m3-st-obs-001.md) for exact Red/Green
commands and the live acceptance ledger.
See [M4 capacity evidence](../evidence/m4-capacity.md) and the
[approved focused packet](../plans/integration/m4-capacity-change.md) for this
bounded implementation, migration allocation and remaining integration work.
