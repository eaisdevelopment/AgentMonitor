# M6 exact recovery evidence contract impact

Status: additive implementation scope confirmed by the integration owner under
the approved M6 cloud plan on 2026-11-03. This does not approve the unrelated
Draft module-plan baseline or claim the live acceptance condition occurred.

Requirement trace: FR-COL-003..008, M6-A07, AC-LIVE-007, AC-OPS-003.
Semantic owner: M04 collection control. Consumer: integration / AUTO-M6-EXIT.
Contract: CTR-COL-012 `CollectionRecoveryQueryV1` 1.0.0.

## Additive boundary

Existing CTR-COL-002 views cannot identify the exact access target and source
fingerprint. CTR-COL-012 adds a separate typed read port; existing records,
commands, API DTOs, SQLite schema and consumers are unchanged. No migration,
new dependency or ADR for a breaking change is required.

The query selects one provider and a UTC interval of at most 24 hours, optionally
one exact account/access target/binding generation/capability/source ID/adapter
version/source fingerprint/payload schema. Limit is 1–500 terminal runs. A
`has_more` response is incomplete evidence and cannot be accepted by the gate.
SQLite reads are restricted to M04-owned tables with a 1.9-second deadline.

Each immutable row contains opaque run/account/access-target identities, source
lineage, requested/completed UTC timestamps, terminal status, nullable durable
dispatch certainty/outcome/failure code, payload digest and at most 200 opaque
committed observation references. Null journal facts mean unproven dispatch;
missing account/target means no exact cloud recovery candidate. No amount,
email, organization, credential, prompt or provider body crosses this port.
The port creates no event, receipt, schedule, lease or provider call. It uses
existing collection history retention and has no independent purge lifecycle.
Invalid, ambiguous, incomplete or unavailable rows fail closed; they are never
reinterpreted as a provider failure. Read access is local integration-owned
repository access, not a new unauthenticated HTTP route.

## Recovery and continuity decision

Pure M04 policy accepts only a received authoritative authentication,
authorization or rate-limit response and a later committed successful/partial
run under the identical scope. `provider_unavailable` does not qualify: the
durable M04 facts do not preserve the HTTP status and therefore cannot
distinguish an upstream unavailable response from a local post-header transport
or body-read failure. Pre-dispatch failures, parser/internal errors, uncertain
requests, changed keys/generations/sources and older superseded failures do not
qualify. Provider response journals and commit observation references are
required; a successful HTTP request without a committed observation is not
recovery evidence.

The canonical gate invokes the bounded interval producer. It first checks the
actual running systemd invocation and searches only that invocation's current
exact-source failure. With no qualifying failure it immediately reports
`not_run`. Otherwise it probes the authenticated built dashboard and its
versioned revision endpoint, then observes scheduled recovery with browser
probes every approximately 15 seconds. The observation budget is 600 seconds;
the gate terminates the whole subprocess group after 660 seconds. It never
triggers a collection, changes an account, or manipulates provider availability.

A positive result requires the same service invocation and revision throughout,
the failed target still failing at the first browser observation, genuine exact
recovery during the observed interval, and actual Claude and Codex committed
quota runs in that interval. The artifact includes invocation/revision identity,
UTC interval, actual dashboard sample count, counts and a lineage digest. A
probe proves availability only when sampled; it does not claim uninterrupted
HTTP availability between samples. Historical dashboard availability is never
inferred from database rows. Missing conditions remain `not_run` or `blocked`.

## Acceptance evidence and rollout

Pure tests cover exact lineage, local failures, dispatch ambiguity, received
provider failures, superseded failures and absent commits. The repository test
queries real retained history through the public port, without seeded rows.
The actual browser probe and absent-natural-failure execution are recorded in
[implementation evidence](../../evidence/m6-recovery-evidence-producer-2026-11-03.md).
A positive natural recovery remains a real-environment prerequisite, not a
waiver. Integration owns candidate deployment and the final canonical gate.
