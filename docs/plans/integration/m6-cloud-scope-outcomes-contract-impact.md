# M6 organization/provider coverage: M02 contract impact and implementation plan

Status: **Contract design reviewed by the integration steward on 3 November
2026 for implementation within the existing owner-approved cloud scope.**
Prepared against `894f092`; production and live completion remain unproven. This is one focused M02
amendment within the [owner-approved cloud plan](m6-ollama-cloud-implementation-change.md),
not a new owner approval request or a change to M6 acceptance. Root proposed
`CTR-REG-013` version `1.0.0` and allocated migration `v1_0719`; neither is
implemented by this document.

## Outcome and authority

An administrator records how each intended organization's Ollama coverage is
provided: its own existing account, a shared relationship to another
organization's existing account, or an explicitly unavailable scope. The form
uses names and ordinary admin controls. It does not request a key, opaque ID,
terminal attestation, provider login or quota observation. Existing assertions
survive deployments and harmless renames; changes to their meaning invalidate
them. Removing an assertion never disconnects or deletes an account.

Primary owner: **M02 registry**. Consumers: P01 API, P02 organization admin, and
the M6 evidence composition. M03 credential/source behavior, M04 scheduling,
M05 monetary aggregation and M07 rules are unchanged.

Traceability: `FR-ACC-001/002/004/006`, `FR-ORG-001`, `FR-SAFE-001/002`,
`AC-LIVE-003`, `AC-UI-002..006`, `M6-A03/A04/A05/A09`, and the cloud plan's
`M6-T004/T005/T006/T011/T014/T015/T017/T018`. The existing catalog remains
authoritative for ticket ownership; these are affected criteria, not claims
that all are completed by this change.

The [execution plan](m6-execution-plan-2026-10-31.md), M6-A03 and its identity
test section, allow the two actual outcomes **or their documented shared
relationship**. The approved cloud plan's Registry, Connection and Scope
paragraphs allow credential-free records and owner-asserted relationships.
`AC-LIVE-003` explicitly permits documenting the actual provider relationship.
Its unavailable-testing rule still forbids claiming an unavailable live check
passed. This design implements those alternatives without accepting an owner
claim as provider proof.

## Inspected gaps and preserved behavior

| Current code | Gap or invariant |
| --- | --- |
| `backend/src/agentmonitor/contracts/registry_v1.py:276` | `AccountViewV1` has one primary organization. Moving/copying an account to express sharing would change its meaning. |
| `backend/src/agentmonitor/contracts/registry_v1.py:677` | `CloudMonitoringTargetV1` belongs to one account and requires an active binding. It cannot represent an unavailable or credential-free organizational outcome. |
| `backend/src/agentmonitor/contracts/registry_v1.py:1243` | `RegistryCloudResourceMembershipV2.relationship_state` is only `unresolved`. It must remain so for an owner assertion. |
| `backend/src/agentmonitor/adapters/persistence/registry/sqlite/repository.py:3810` | Capacity membership is selected from actual active cloud targets. Coverage records must not add targets/resources to this query. |
| `backend/src/agentmonitor/modules/capacity/domain/aggregation.py:280` and `:574` | Unresolved cloud relationship prevents a combined numeric total. Preserve this rule and its existing response semantics. |
| `tools/automation/implementations/m6_real_snapshot.py:479` | Required organizations are currently identified by literal names; owner scope is counted only after an active credential graph. Renames/shared/unavailable scopes cannot be represented faithfully. |
| `tools/automation/implementations/m6_direct_evidence.py:464` | A03 currently requires two accounts and two cloud targets. A real single-target shared relationship cannot satisfy this implementation, although the criterion permits it. |
| `backend/src/agentmonitor/api/v1/routers/registry.py:103` | Existing write permission, CSRF, ETag, idempotency and safe problem conventions can be reused. No new authentication ceremony is necessary. |

The missing capability is a registry disposition, not another cloud balance
request. It is independent of A02's host inventory limitation and A07's absence
of a naturally observed recovery interval; this change cannot close either.

## Additive contract: CTR-REG-013 1.0.0

Publish `backend/src/agentmonitor/contracts/registry_coverage_v1.py` under
`PLAN-M02`; no private registry or database imports in consumers. Keep
`CTR-REG-001/002/007` at their existing versions and `CTR-REG-009` V2 and
`CTR-REG-011/012` unchanged. No credential or capacity contract field is added.

`OrganizationProviderCoverageV1` is keyed by immutable `(organization_id,
provider_key)`, with an opaque coverage ID, monotonically increasing record
version and registry revision. Fields:

- `outcome`: `account`, `shared`, or `unavailable`.
- `account_id`: required for `account/shared`; absent for `unavailable`.
- `unavailable_reason`: required only for `unavailable`; closed initial reasons
  `account_unavailable`, `subscription_unavailable`, `access_unavailable`,
  `owner_unavailable`. Unknown/missing choice is not an unavailable outcome.
- `provenance`: exactly `owner_asserted`; `confirmed_by` principal ID and server
  UTC `confirmed_at`. No editable provenance, asserted date, evidence upload or raw text.
- Source account's provider and primary organization at assertion time, when
  applicable. These are semantic reference fences, not credential ownership.
- `invalidated_at` and closed `invalidation_reason` are absent while current;
  `owner_revoked` represents an explicit DELETE. Invalidation cannot predate
  confirmation. Read result gives current validity and its reason.
- No quota, currency, balance, pool identifier, credential reference, provider
  identity verification, API key, email or organization name is persisted here.
  Normal authorized UI resolves display names through existing registry reads.

`SetOrganizationProviderCoverageCommandV1` takes org/provider, outcome,
account/reason, expected version (`0` only for initial creation), the selected
account record version for account/shared writes (absent for unavailable), command ID,
authenticated principal and server timestamp. The caller cannot send a
`provider_proven` or successful quota flag. A separate
`RevokeOrganizationProviderCoverageCommandV1` applies to an existing version;
it retains the assertion for audit and does not change the account. Re-setting
a revoked/invalidated record requires its current version, not version zero.

Publish typed read/write protocols with get, bounded list, set and revoke.
Read lists carry completeness, registry revision and as-of time; do not turn a
failed/truncated read into an empty complete list. List by provider and selected
organization IDs, with stable ordering and existing pagination conventions.
API/gate reads use these ports; they never query the new table themselves.

### Validation and lasting invalidation

1. The organization and provider must exist and be eligible in the real
   registry. The account must exist, not be archived, and use that provider.
   Pending accounts are allowed; coverage is not proof of monitoring access.
2. `account` requires the account's primary organization to equal the coverage
   organization. `shared` requires a different active primary organization.
   Ungrouped accounts cannot be a shared source. Two coverage records may
   reference the same account; they do not create a second target or balance.
3. A source account cannot be both a direct and shared declaration for the
   same org/provider key. A replacement is versioned and explicit. Shared
   rows reference the account directly, not another coverage row, so no cycles
   or recursive group-resolution machinery are needed.
4. Account archive, primary organization reassignment, relevant organization
   archive, or provider withdrawal invalidate affected rows in the owning
   registry transaction. Future provider-changing commands must use the same
   invariant; the current account edit API does not offer provider changes.
   Both the covered organization and source account's primary organization
   participate in validity checks.
5. Invalidation is lasting: archive/restore or moving away and back must not
   silently revive the old assertion. Persist invalidation reason/time
   and increment its version. Query-time referential checks are an additional
   guard, not a substitute for durable invalidation. Reconfirmation uses the
   ordinary edit form only when the relationship actually changed.
6. Account/org rename, organization ordering, monitoring toggle, successful
   polling and application revision changes do not invalidate the relationship.
   Credential rotation/disconnection does not itself rewrite owner coverage;
   connection readiness and exact current-binding evidence are checked
   independently. An unavailable assertion remains an owner statement, not an
   override of real access state; contradictory current access is displayed and
   cannot be used to exclude an available target from required live checks.

### Meaning of sharing

`shared` means “the administrator says this organization uses this selected
account.” It does not establish that two keys/accounts share a provider pool,
prove their identity, or admit a canonical pool alias. The same actual account
referenced by two coverage rows has one existing target, queried once. This
deduplicates identical target IDs in an evidence set, not distinct provider
pools. Distinct accounts with equal emails/amounts remain distinct observations
with unresolved pool relationships. No new provider-proof acquisition or
deduplication mechanism is proposed.

## Storage and operations

Root-allocated `backend/migrations/versions/v1_0719_m02_organization_coverage.py`
is an additive expand migration owned by M02. Proposed table
`reg_organization_provider_coverage` contains the fields above, unique
org/provider key, same-module foreign keys where appropriate, null-shape and
positive-version checks, and indexes for account and organization invalidation.
No credentials or telemetry are copied. Existing records receive **no**
fabricated coverage row or inferred migration backfill.

Set/revoke/invalidate, `_next_revision`, existing `reg_command_receipt` and the
normal registry change/audit publication commit atomically in a short SQLite
transaction. No provider/network/file operation occurs inside the transaction.
Reuse the existing receipt conflict behavior: same principal/operation/key and
same fingerprint replays safely; changed payload conflicts; a stale replay
cannot overwrite a subsequent edit. Registry change payloads use opaque IDs,
versions, actor/time and closed outcome/reason codes, never names. Preserve the
prior assertion and revision transition in the existing audited change record;
do not rely on an ephemeral log as the revocation record. If the existing audit
payload cannot retain these safe facts, add the smallest M02-owned immutable
coverage revision storage in the same migration after root review, rather than
changing event-delivery semantics or retaining raw requests.

Read-time validity uses one consistent registry transaction. Relevant registry
mutators must invalidate before commit; no asynchronous observer, background
service or cross-module table reader is introduced.

## API and user flow

Add compatible `/api/v1` endpoints:

- `GET /provider-coverage/{provider_key}?organization_ids=...`: one bounded,
  ordered selection of 1..200 distinct comma-separated organization IDs. The
  response preserves the full selection and sparse assertions, completeness,
  registry revision and producer observation time. It performs one contract
  read, without independently looping organization reads.
- `GET /organizations/{organization_id}/provider-coverage/{provider_key}`:
  one current assertion, or typed absent state (`coverage: null`) with a
  create-only version-zero ETag. An absent organization is 404.
- `PUT` on that resource: replace the complete disposition; `Idempotency-Key`
  plus `If-Match` required. A typed absent read/create precondition represents
  version zero; it is not permission to overwrite an existing record.
- `DELETE` on that resource: revoke, not erase, with ETag and idempotency.

Use `read:accounts` / `write:accounts`, existing browser CSRF/origin rules and
scoped bearer alternative. Map missing precondition to 428, stale to 412,
conflicting replay/reference state to 409, invalid shape to 422, absent subject
to 404 and actual repository unavailability to the existing safe unavailable
mapping. Never start verification or collection from these handlers.

P02 adds a small provider coverage editor within Organizations: choose provider,
then “Own account”, “Shared account” or “Unavailable”; choose an existing account
with its readable primary organization, or select the unavailable reason. Show
“Owner declared” and current validity. The account's existing connection/balance
link remains available. Save/edit/remove use the generated client and normal
error handling. No opaque IDs, “verify ownership” claim or opaque terminal
confirmation. Do not display an unavailable declaration as zero dollars or a
green successful reading. Overview grouping and monetary aggregation need no
change for this increment; a shared coverage link is administrative metadata.

## Canonical evidence consumption

The snapshot returns typed disposition facts and exact distinct referenced
account/target sets through CTR-REG-013, not only counts. The canonical gate's
intended organizations must be bound to stable IDs from the real configured
selection; never rediscover them by literal display names or infer that any two
arbitrary records are the intended set. Root can resolve the already identified
organizations once through normal registry reads; the owner need not type IDs.
Persist/reuse that non-secret scope selection using the existing canonical
verification configuration, and bind its digest in the evidence. A missing
intended organization remains missing; it is not dropped from the denominator.

For A03, assess each intended org/provider outcome and current reference
validity. One current own-account row plus one shared row referencing that same
account documents two owner scopes and **one** cloud target. Do not require two
keys as a proxy for two organizations. A credential-free own-account declaration
can establish an owner mapping but cannot establish access or enrollment of a
working monitored target.

Keep `classified scopes`, `unavailable scopes`, `accessible target IDs`,
`verified targets`, `authoritative comparisons` and `unresolved scopes` separate.
An explicit unavailable outcome can establish that a limitation is known; it
does not make A04/A05/A09 pass. Under the approved plan, required unavailable
live evidence remains NotRun/Blocked and prevents the full-pass claim. No
successful count is incremented for absence. Do not introduce a silent
milestone waiver in the classifier.

A04/A05/A09 consume each actual available target once, using existing exact
binding/source lineage, quota/history/browser and official comparison proofs.
An active target elsewhere in the selected scope is not hidden by an
unavailable declaration. Owner coverage never changes verification receipts,
resource IDs, numeric aggregation or alert eligibility. Gate failure reasons
name the actual missing requirement rather than demanding another key when the
recorded relationship is shared. A01/A02/A06/A07/A08/A10 keep their criteria.

## Allowed implementation paths and sequence

This design task changes **only this document**. After root contract review,
implementation allocation is:

1. M02: new `contracts/registry_coverage_v1.py`, focused domain/application
   coverage modules, registry SQLite coverage adapter and existing registry
   mutator hooks. Root coordinates the shared migration chain, schema head/
   compatibility records and contract catalog/adoption/generated snapshot.
2. M02 tests: meaningful pure and real SQLite Red before implementation; then
   Green, migration/rollback and ordinary registry regressions.
3. Root/P01: additive registry schema/router and composition-port wiring;
   generated OpenAPI/client using existing generators. P02: Organizations
   feature plus shared generated-client adapter. No hand-edited generated DTOs.
4. Integration: `m6_real_snapshot.py`, `m6_direct_evidence.py`,
   `auto_m6_exit.py` and their existing parser/policy tests/catalog source hashes
   consume the typed current coverage and selected scope, preserving strict
   live outcome distinctions. No direct table access outside M02.
5. Root: combined canonical build, quality/docs/planning checks; real HTTP and
   built browser verification; deploy with verified backup; then existing
   `AUTO-M6-EXIT`. Update evidence, runbook, traceability and M02 plan amendment
   together. This is not an extra owner subgate or revision-bound attestation.

Forbidden: edits to provider adapters, credentials, default profiles, scheduling
or M05/M07 resource semantics; new dependencies; provider actions; fabricated
scope records; changing M6 acceptance to fit the available state. Additional
consumer coupling discovered during implementation returns to root contract
review, not an unapproved private import.

## Red/green scenarios

| Scenario ID | Requirement / boundary | Expected evidence |
| --- | --- | --- |
| M6-COV-PURE-01 | FR-ACC-006; no I/O | Valid shapes and forbidden provenance/unknown reason; own/shared org semantics; owner assertion never provider proof. |
| M6-COV-PURE-02 | AC-LIVE-003, M6-A03..05 | Two scopes/one exact target accepted as coverage; two targets never collapsed by amounts/labels; unavailable produces no live-success count; absent scope never removed. |
| M6-COV-DB-01 | FR-ACC-001/002; actual SQLite | Real migrations and production CRUD for owner-confirmed real registry metadata; save/replay/conflict/revoke/re-set; atomic receipts/revision/audit and rollback. |
| M6-COV-DB-02 | FR-ACC-006; actual SQLite | Archive/restore and reassignment/back do not revive assertions; renames/reorder preserve them; current validation rejects missing/wrong-provider references. |
| M6-COV-DB-03 | NFR-DATA-001; actual SQLite | Upgrade actual private 0718 backup, no fabricated backfill, integrity/FK checks, backup restore and schema refusal by unsupported binary; existing quota/history unchanged. |
| M6-COV-HTTP-01 | AC-UI-002..006; actual listening service | Real auth/CSRF/permissions, GET/PUT/DELETE, create race, ETag conflict, idempotency, closed problem codes and OpenAPI/client conformance. |
| M6-COV-UI-01 | AC-LIVE-003, AC-UI-002..006; built browser | Named org/provider/account choices, shared source org, unavailable reason, edit/revoke, invalidated feedback, keyboard/mobile and truthful connection/balance labels. |
| M6-COV-LIVE-01 | M6-A03/A04/A05/A09 | Only actual owner dispositions; canonical snapshot/API/UI agree, available target lineage still reconciles; unavailable remains explicit; no key/provider action during coverage edit. |

Constructed values are restricted to the two pure policies. SQLite/HTTP/browser
tests use actual file-backed databases, real migrations/repositories/service and
production UI; private copies may preserve actual registry facts for safe
mutation tests. Do not invent a shared relationship or unavailable owner outcome
to make a live test run. Positive shared/unavailable I/O evidence is NotRun until
the owner actually supplies that disposition; protocol errors and pure policy
coverage do not substitute for it. Capture behavioral Red before production
changes, Green and post-refactor results; unrelated import/setup failures are not Red.
The canonical gate may remain blocked on other real conditions after this code
gap is repaired.

## Compatibility, privacy and recovery

This is an additive internal 1.0.0 contract/new API resource/new table. Existing
account, membership, capacity, event envelope and money meanings remain intact;
no breaking API or provider change is intended and no new dependency/license
review is needed. Extend contract/adoption/ownership/catalog sources and
regenerate their outputs. A changed old contract meaning would instead require
the version/ADR process; this proposal does not authorize that change.

Follow the existing canonical migration/deployment/backup commands. Before
rollout take a verified owner-only backup; test 0718→0719 on a private actual
copy and confirm no provider telemetry changes. Unsupported older binaries
must refuse writable startup on 0719. Recovery is prior binary plus verified
pre-migration backup, not dropping the new audit-bearing table. Record that
post-backup coverage edits are lost on restore and must be reviewed; never
silently restore assertions from logs. No `.env` or provider credentials enter
backups. Full downgrade support is not claimed without a real tested path.

New stored data is limited to internal IDs, owner action attribution, timestamps,
closed reasons and versions, under existing DB/backup protections. Diagnostic
evidence emits only counts, digests, times and safe codes. Display aliases stay
in ordinary authorized registry UI; no email/name is copied into gate receipts.
No arbitrary notes/evidence-upload feature, provider-proof store or persistent
observer is introduced.

## Handoff state

Design only: no Red/Green or new live pass claimed; no live mutation/provider
request performed. Root must review the additive port, referential invalidation,
API creation/revocation preconditions and evidence selection before assigning
implementation. Existing owner approval is retained. The remaining real owner
information is the actual second organization's distinct/shared/unavailable
relationship if it cannot be established from existing explicit direction;
another API key is necessary only if its actual distinct scope is available
and requires monitoring. Prepare the normal UI before asking for that fact.

## Root contract review decisions

Existing owner approval of the M6 cloud plan authorizes this implementation;
no approval is inferred from this document alone. Root reviewed the existing
registry, capacity, API and gate contracts and freezes the additive contract
and v1_0719 allocation above. Existing capacity/credential contracts stay intact.
The current registry audit shape cannot retain all assertion fields, so the
expand migration will include an M02-owned immutable coverage revision table
alongside the current row, with no credential/telemetry data. Set, revoke and
lasting semantic invalidation append the resulting version atomically.
The read selection is bounded to 200 explicit organization IDs for one provider
and returns one consistent registry revision and as-of time; missing rows are
missing assertions, never unavailable dispositions or silently removed scopes.

First implementation work is the I/O-free typed contract and shape rules.
Repository, migration, HTTP, UI and canonical evidence remain separate real
boundaries to implement and verify before any feature or milestone completion
claim. Shared and unavailable assertions will never be manufactured for live
verification; their actual owner declarations remain necessary.

## Contract increment evidence (implementation remains partial)

The new immutable CTR-REG-013 values and read/write protocols are implemented;
repository, migration, HTTP, UI and live dispositions are not yet implemented.
The first six pure shape checks passed after the previously absent module was
introduced. Independent review then exposed three behavioral defects: a raw
source-organization string, invalidation after the snapshot observation time,
and out-of-selection-order rows were accepted. Their regression checks each
failed `DID NOT RAISE ValueError` before correction. The final focused suite
has **11 passing tests**, including malformed row rejection and refusal to
persist a transient access failure as lasting invalidation.

The read query now carries only explicit organization IDs and provider key.
Snapshot `as_of` is derived by the repository producer, not supplied in the
request. Snapshot rows must follow selection order, belong to that selection,
and have confirmation/invalidation timestamps no later than the producer time.
`provider_withdrawn` is a structural invalidation reason; provider/network or
credential unavailability is not. Set commands additionally fence the selected
account's displayed record version to prevent a reassignment race at save.

Commands executed from the integration checkout:

```bash
PYTHONPATH=backend/src python -B -m pytest backend/tests/registry/test_organization_provider_coverage.py -q
MYPYPATH=backend/src python -B -m mypy --explicit-package-bases --strict backend/src/agentmonitor/contracts/registry_coverage_v1.py backend/tests/registry/test_organization_provider_coverage.py
python -B tools/automation/run.py AUTO-PLAN-CHECK
python -B tools/automation/run.py AUTO-DOCS-CHECK
python -B tooling/foundation/check_boundaries.py .
```

Focused tests and strict types passed. The synchronized planning and documentation
checks passed after registering the exact 105th contract, its central file owner
and its FND/P01/P02/integration consumers; the boundary scan found zero violations.
The earlier combined six-test/contract-boundary run passed 196 tests. These are
contract/structural results, not SQLite, API, browser or provider evidence.
The planning baseline remains Draft and its approval flags stay false; the
separately approved M6 cloud scope is the implementation authority.

Changes are the new contract and pure tests, exact boundary/ownership/catalog
registration, generated adoption/snapshot records and this impact document.
No dependency, runtime configuration, credential path, provider action, schema
or live service was changed by this increment. v1_0719 is reserved, not applied.
Existing API/money/credential contracts keep their versions and behavior.

Final contract review cleared all four findings. The combined pure and actual
source-boundary suite passed **201 tests**; `AUTO-QUALITY` then passed (571 files
formatted, strict types across 515 files, zero boundary violations, unchanged
74-operation API and successful frontend build). Its initial import-order
failure was corrected using the canonical explicit Ruff configuration; no
check was disabled. Planning and documentation checks passed. The live service
remained active with HTTP 200; the new feature is not deployed or exposed yet.
