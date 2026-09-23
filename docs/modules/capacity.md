# M05 capacity module

Status: **Partially implemented for M3 `ST-OBS-001`**. Exact capacity
contracts, health policy, the complete empty M05 schema allocation, durable
commit/query repositories, and the typed Claude-normalization route are
present. Production composition constructs the real Claude adapter, M04
executor/recovery path, exactly one digest-validating M05 sink, and the M05
query surfaces. The current real Claude subscription collector tuple is
version/workspace blocked, so a real collection and capacity commit remain
**Blocked / Not Run**. No constructed or seeded provider observation is used as
a substitute.

Owner: `PLAN-M05`
Contracts: `capacity.v1`, `CTR-CAP-001/003/004/009`,
`CTR-COMMON-003/004/007`, `CTR-COL-006`
Database allocation: `v1_0500..v1_0504`

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
- The Claude mapper stores the reported rounded percent-used value. Because the
  accepted source does not report a trustworthy limit, remaining value, or
  remaining ratio, those fields remain explicitly Unknown. Reset display text
  is not parsed into an invented instant.

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

`ListQuotaWindowsV1`, `GetCapacityHealthV1`, `GetAccountCapacityV1`, and
`GetCollectionCommitStatusV1` are provider-neutral query boundaries. Window,
health, and account queries require explicit capability and `as_of` semantics;
health is evaluated against `valid_until`, not lexical capability order. Empty
history returns an empty window tuple or a bounded not-found error; it never
returns placeholder telemetry.

## Persistence allocation

The fresh M05 chain creates 24 empty tables and no rows:

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

## Operations and incomplete acceptance

Writable startup requires the reviewed migration catalog, compatible schema,
SQLite policy, integrity check, and foreign-key check. Receipt conflicts,
canonical-value violations, schema mismatch, and repository failures fail
closed with bounded codes.

The following are **Blocked / Not Run**, not Passed:

- `M04-LIVE-004/009..011` real Claude dispatch, typed outcome, source/version,
  and one-sink verification;
- `M05-LIVE-001..006` real quota reconciliation, exact persisted values,
  projection/health, and idempotent replay;
- the real provider-to-M04-to-M05 composition run while the accepted Claude
  version/workspace tuple is unavailable (production construction and
  no-provider recovery are Green);
- non-empty M05 commit/replay/conflict/current/outbox assertions, because they
  require a fresh real provider observation;
- later budget, forecast, retention, export, API, browser, scale, backup, and
  restore behavior.

See [M3 ST-OBS-001 evidence](../evidence/m3-st-obs-001.md) for exact Red/Green
commands and the live acceptance ledger.
