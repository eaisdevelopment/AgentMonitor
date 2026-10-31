# Module plan: M07 — M4 dashboard alerting

- Status: Approved for I01 contracts/pure policies and I02 owned rule persistence/migration files; producer signal integration remains synchronized separately.
- Plan ID: M4-M07-ALERTING-2026-09-29
- Plan version: 0.2.0
- Module contract version: CTR-ALERT-001..005 V1, proposed additive package.
- Owner: independent M07 planning agent; root is integration and shared-contract steward.
- Reviewers: root, M02/M04/M05/M06 producers, M01/P01/P02, DB/M08, security/test.
- Requirements: FR-ALERT-001..006; FR-HIST-001..003.
- Acceptance criteria: AC-ALERT-001..003; AC-HIST-002. P01/P02 coordinate FR-UI-001..006 and AC-UI-002..006.
- Target milestone: V1-M4, ST-ALERT-001 and ST-ALERT-002 only.
- Approved by/date: Root integration, 2026-09-29, under the active owner-authorized full M4 implementation objective.

## 1. Outcome and boundaries

Implement durable dashboard alerts from actual collected observations and producer-owned current conditions. An owner can explain which rule applied, inspect source freshness and history, and read, acknowledge or snooze an alert. Repeated polls produce one condition lifecycle. Recovery requires explicit newer producer evidence.

This focused module plan implements [M4 Tasks 4 and 5](../../superpowers/plans/2026-09-19-agentmonitor-v1-m4-claude-fleet-alerts.md) and concretizes the [full M07 draft](../modules/m07-alerting/plan-v1.md). It does not approve the whole older draft or claim M07/M4 completion. Shared contracts and producer gaps below require root synchronization before the affected increment begins.

### Ownership and assigned paths

| Owner | Responsibility and paths |
|---|---|
| M07 | `backend/src/agentmonitor/modules/alerting/{domain,application}/**`; `backend/src/agentmonitor/adapters/persistence/alerting/sqlite/**`; `backend/tests/alerting/**`; `backend/tests/integration/alerting/**`. Rules, fingerprints, lifecycle, receipts, commands, notification projection, history, deadlines, reevaluation and module retention. |
| Root/contract steward | Sole writer of `backend/src/agentmonitor/contracts/alerting_v1.py`, proposed `events_v1.py`, consumed contract additions, registries and compatibility baselines. M07 supplies the exact proposal below and reviews it. |
| Root/DB steward | Serial migration allocation/catalog/head and supported schema ranges. May explicitly delegate only the three named M07 revision files after approval; no other migration is changed by M07. |
| Producer owners | M02 scope/auth truth; M04 collector/stale truth; M05 capacity/forecast/availability truth; M06 runtime/stall truth and source ordering. |
| Root/P01/P02/M01 | Composition and workers, real HTTP/auth, OpenAPI generation, TypeScript client, alert/rule pages, routes, browser evidence and permissions. |
| M08/root | Retention scheduling, global health/diagnostics, export, backup/restore and canonical automation. M07 publishes bounded participants and owns its SQL. |

Domain imports only standard library, common technical primitives and approved immutable alert contracts. Application depends on published ports. SQLite adapters may use the admitted SQLAlchemy stack and DB access contract. No M07 import of provider/OS/CLI/FastAPI/UI, producer repositories or producer internals; no cross-module SQL or foreign key. No provider recollection, account identity inference, runtime classification, agent control, external notifications or free-form rule expression engine.

Root reviewed this independent plan, actual producer notices, public scope
contracts and M01 permissions. I01/I02 freeze the exact section 4 alert/rule/
decision/lifecycle/notification types and section 5 owned table allocation.
The M07 agent is sole assigned writer of `contracts/alerting_v1.py` under root
stewardship, its module/application ports/repository/tests/module evidence and
the three named M07 migration files. Root alone edits the shared migration
catalog, schema compatibility checker/head/ranges, events/producer contracts,
API/UI/generator/composition and automation. Do not run service migrations.
Producer-owned fact unions/events/current queries remain a later synchronization;
pure normalized decision/lifecycle inputs do not establish real producer truth.
No generic commit notice or target generation may be used to bypass that seam.
Pure policy and real persisted rule CRUD can proceed with the frozen public
registry snapshot ports and truthful closed inputs. Real alert consumption
requires a genuine implemented producer path before integration acceptance.

## 2. Requirements and traceability

| Requirement/AC | Planned behavior | Contract V1 | Scenario IDs | Required evidence |
|---|---|---|---|---|
| FR-ALERT-001; AC-ALERT-001 | Whole-rule specificity, persisted CRUD, disabled override and resolution explanation | CTR-ALERT-001; CTR-REG-009 | A-P01, A-DB01, A-HTTP01, A-UI01 | Pure plus real SQLite/HTTP/browser |
| FR-ALERT-002 | Inclusive warning 3000bp / critical 1500bp and exact user thresholds | CTR-ALERT-001/002; CTR-CAP-005 | A-P02, A-DB01, A-LIVE01 | Pure boundaries; actual current quota |
| FR-ALERT-003; AC-ALERT-003 | Capacity, forecast, auth, stale, collector, possible stall and explicit recovery/reset | CTR-ALERT-002..004; producer ports in §4 | A-P03, A-DB02, A-LIVE01..05 | Real source evidence; rare unavailable cases Blocked |
| FR-ALERT-004 | Stable condition fingerprint, generation ordering, receipt deduplication and restart replay | CTR-ALERT-002..004; CTR-EVT-001 | A-P04, A-DB02/03 | Pure policies and actual durable source delivery |
| FR-ALERT-005; AC-ALERT-002 | Read/unread, ack, snooze, recovery/reopen, ordered notifications/history | CTR-ALERT-002/005 | A-P05, A-DB04, A-HTTP02, A-UI02 | Actual alert through SQLite/HTTP/built browser |
| FR-ALERT-006 | Dashboard-only projection and events, no external delivery surface | CTR-ALERT-003..005 | A-ARCH01, A-UI03 | Import/config/schema/network review |
| FR-HIST-001..003; AC-HIST-002 | UTC immutable history, 365-day expiry, bounded auditable module purge | CTR-ALERT-002/004; M08 participant | A-P06, A-DB05/06 | Pure cutoff plus real migration, deletion and restore; actual aged-data limitation explicit |

FR-HIST applies here to M07-owned alert history; other histories remain owned by their modules. Full 365-day live deletion is not Passed using backdated or invented telemetry.

## 3. Domain design

### Rules and exact comparisons

Resolve a complete rule document in this order: **account > provider > organization > global > built-in**. The closest enabled or disabled document wins; a disabled override suppresses the condition and never falls back. No field merging. A subject with unresolved account identity has no account or organization candidate. Provider scope uses the producer's safe registered provider key. Registry revision and candidate versions accompany the explanation.

Built-in `capacity_remaining` has `warning_remaining_basis_points=3000`, `critical_remaining_basis_points=1500`, enabled. Validate integers with `0 <= critical <= warning <= 10000`; bool is not an integer. Compare an exact source ratio against these thresholds, critical first, using inclusive `<=`. Do not floor a fractional basis point before comparing. Zero is available exhausted capacity; missing/unknown/stale/unsupported is never zero. Preserve source rounding, precision and confidence. M05 health policy remains separate; M05 never imports M07 thresholds.

Other built-in conditions are enabled with fixed severity mapping, overridable only by a complete enable/disable rule: exhausted/unavailable capacity critical; predicted exhaustion warning; reauth-required/revoked/wrong-account critical; expiring auth warning; stale data warning; collector degraded/failure warning and explicit infrastructure blocked/unavailable critical; inferred possible stall warning. Recovery/reset is an informational transition on the existing alert. No new forecast horizon or stall timeout is introduced by M07.

### Condition identity and ordering

Fingerprint version 1 hashes canonical `(condition_type, subject_kind, subject_id, dimension_kind, dimension_id, condition_semantic_major)`. Dimension identifies the native quota window, resource, forecast, monitoring profile, collector target/capability or session. Exclude severity, rule/version, organization membership, mutable labels, generation, timestamps and source references. Store canonical collision material privately; equal digest with different material is a hard conflict. Same condition reopens the same alert with a new occurrence generation.

Producer identity is `(producer_key, condition_stream_key, source_generation)`, with a monotonically increasing positive generation owned by that producer for that condition stream. **Collection target_generation is not this generation**: different polls may share it. Timestamps, run IDs, event IDs and M07 sequence allocation cannot manufacture upstream ordering. Duplicate event ID and identical canonical content returns its durable receipt; changed content under that ID conflicts. A new event with lower/equal generation is recorded as ignored stale and cannot regress current state. Even a newer not-evaluable input advances the observed-stream checkpoint, without inventing a current value or recovering an alert.

Current-condition refresh uses the producer's published port and its committed generation. An old commit notice may trigger a read of a newer actual condition; the receipt records both triggering event and observed generation. It is not an assertion that the historical notice contained that condition. Query failure leaves alerts unchanged and exposes degraded consumer health. Never treat collection success, silence, restart, missing data or cache expiry as recovery.

### Lifecycle reducer

Lifecycle is `open | recovered | closed_by_configuration`, independent of severity, unread, acknowledgement and snooze. Every accepted source generation and command is deterministic given explicit aware UTC `as_of`.

| Input | Projection/history result |
|---|---|
| New active condition | Open; occurrence generation/count 1; unread; notification revision 1. |
| Equivalent newer active condition | Same alert; count +1, last-seen and record version change; retain ack/snooze; no notification-revision increment. One immutable repeated event per new accepted generation; no per-poll notification. |
| Escalation | Same lifecycle; clear ack/snooze, cancel old deadline, unread, notification revision +1. |
| Deescalation still active | Same lifecycle with explicit history; unread and notification revision +1. |
| Explicit newer recovered/non-triggering current condition | Recover; informational notification and history; clear snooze/cancel deadline, retain prior acknowledgement history, unread, revision +1. |
| New active evidence after terminal lifecycle | Reopen same alert; occurrence generation +1, count 1; clear ack/snooze, unread, notification revision +1. |
| Disabled effective rule or archived/ineligible subject | Close by configuration with cause; never claim source recovery; cancel deadline and remove active notification. |
| Mark read | Match notification revision; unread false only. GET never marks read. |
| Acknowledge | Open only; opaque actor/time, mark read, preserve underlying condition; no free-form note. |
| Snooze | Open only; integer duration 60..2592000 seconds inclusive (30 days); mark read; durable UTC expiry and deadline generation. Ack and snooze may coexist. |
| Unsnooze / actual due expiry | Open only: clear snooze, unread, notification revision +1. Stale/cancelled deadline generation is an idempotent no-op receipt. |

Each source family proves its inverse: newer available above-warning/current reset for remaining; newer explicit not-exhausted or available for exhausted/unavailable; newer forecast non-triggering with sufficient current inputs or reset; newer verified healthy authentication; newer current collection freshness/healthy collector; M06 newer progress/cleared/terminal stall evaluation. Unknown state, refreshing authentication, unsupported source, partial query and arbitrary success cannot prove those inverses. Waiting for input/permission is excluded by M06's policy, not reclassified by M07.

Notifications order unsnoozed open critical, unsnoozed open warning, unread recovered information, then remaining, each by latest notification time descending and alert ID descending. Counts distinguish visible unread (excludes active snooze) from total unread. Read/ack never conceal a later escalation. UI labels and IDs are resolved separately through authorized registry views, not copied into alert evidence.

## 4. Public contracts

### Exact proposed immutable vocabulary

All public records use `@dataclass(frozen=True, slots=True)` and existing `TechnicalValueV1`, `OpaqueIdV1`, `CanonicalDecimalV1`, UTC/provenance types. Tuples are bounded; no `Any`, arbitrary dictionaries, provider extensions, generic errors or text notes. Constructors validate token lengths/enums, integer types, UTC order, value/availability pairs and cross-field consistency. The following signatures are a proposal for the root's sole contract writer; existing names below are not silently redefined.

```python
AlertConditionTypeV1 = Literal[
    "capacity_remaining", "capacity_exhausted", "capacity_unavailable",
    "forecasted_exhaustion", "authentication_attention", "data_stale",
    "collector_failure", "possible_stall",
]
AlertSeverityV1 = Literal["information", "warning", "critical"]
AlertLifecycleV1 = Literal["open", "recovered", "closed_by_configuration"]
AlertRuleScopeV1 = Literal["global", "organization", "provider", "account"]
AlertTransitionV1 = Literal[
    "opened", "repeated", "escalated", "deescalated", "recovered", "reopened",
    "closed_by_configuration", "marked_read", "acknowledged", "snoozed",
    "unsnoozed", "snooze_expired",
]

AlertScopeRefV1(scope_kind: AlertRuleScopeV1, scope_id: str | None)
# global: None; provider: registered provider key; other scopes: opaque ID.
CapacityRemainingRuleConfigurationV1(
    schema_major: Literal[1], warning_remaining_basis_points: int,
    critical_remaining_basis_points: int)
ConditionRuleConfigurationV1(schema_major: Literal[1])
AlertRuleConfigurationV1 = (
    CapacityRemainingRuleConfigurationV1 | ConditionRuleConfigurationV1)
AlertRuleViewV1(
    rule_id: OpaqueIdV1 | None, condition_type: AlertConditionTypeV1,
    scope: AlertScopeRefV1, enabled: bool,
    configuration: AlertRuleConfigurationV1, record_version: int,
    created_at: datetime | None, updated_at: datetime | None,
    archived_at: datetime | None, actor_id: OpaqueIdV1 | None,
    is_builtin: bool, builtin_policy_version: str | None)
EffectiveAlertRuleViewV1(
    selected: AlertRuleViewV1, candidates: tuple[AlertRuleViewV1, ...],
    registry_revision: int, explanation_code: str)

AlertSubjectV1(
    subject_kind: Literal["account", "resource", "profile", "collector", "session"],
    subject_id: OpaqueIdV1, dimension_kind: str, dimension_id: str,
    account_id: OpaqueIdV1 | None, provider_key: str | None,
    organization_id: OpaqueIdV1 | None, registry_revision: int)
AlertSourceReferenceV1(
    producer_key: str, condition_stream_key: str, source_generation: int,
    event_id: OpaqueIdV1, observation_ids: tuple[OpaqueIdV1, ...],
    evidence_ids: tuple[OpaqueIdV1, ...], observed_at: datetime | None,
    recorded_at: datetime, freshness_deadline: datetime | None,
    precision: PrecisionV1, confidence: ConfidenceV1, reason_code: str)
AlertDecisionSummaryV1(
    reason_code: str, truth_state: Literal[
        "current", "stale", "unknown", "unsupported", "unavailable"],
    remaining_basis_points: CanonicalDecimalV1 | None,
    warning_remaining_basis_points: int | None,
    critical_remaining_basis_points: int | None,
    reset_at: datetime | None, forecast_exhaustion_at: datetime | None,
    source: AlertSourceReferenceV1)
AlertViewV1(
    alert_id: OpaqueIdV1, fingerprint_version: Literal[1],
    condition_type: AlertConditionTypeV1, subject: AlertSubjectV1,
    severity: AlertSeverityV1, lifecycle: AlertLifecycleV1,
    occurrence_generation: int, occurrence_count: int, record_version: int,
    opened_at: datetime, last_seen_at: datetime, recovered_at: datetime | None,
    closed_at: datetime | None, latest_notification_at: datetime,
    notification_revision: int, unread: bool,
    acknowledged_at: datetime | None, acknowledged_by: OpaqueIdV1 | None,
    snoozed_until: datetime | None, rule: AlertRuleViewV1,
    decision: AlertDecisionSummaryV1, aggregate_sequence: int)
AlertHistoryEntryV1(
    event_id: OpaqueIdV1, alert_id: OpaqueIdV1, aggregate_sequence: int,
    transition: AlertTransitionV1, occurred_at: datetime,
    previous_lifecycle: AlertLifecycleV1 | None,
    current_lifecycle: AlertLifecycleV1,
    previous_severity: AlertSeverityV1 | None, current_severity: AlertSeverityV1,
    actor_id: OpaqueIdV1 | None, reason_code: str,
    source_event_id: OpaqueIdV1 | None, command_id: OpaqueIdV1 | None)
DashboardNotificationViewV1(
    alert: AlertViewV1, rank: int, is_visible_unread: bool)
DashboardNotificationCountsV1(
    active_critical: int, active_warning: int, visible_unread: int,
    total_unread: int, acknowledged: int, snoozed: int, recovered: int)
```

`dimension_kind`, reason codes, producer keys and stream tokens are enumerated/allowlisted by the finalized contracts, not arbitrary administrator text. Fingerprint digest/material and private storage metadata are not public views. Built-in rules have no persisted rule ID/actor/timestamps and expose their fixed policy version with record version 0; persisted rules have positive versions. Rule snapshot in an alert records the applied revision, not whatever rule currently exists.

### CTR-ALERT-001 — rules and resolution

Ports: `CreateAlertRuleV1`, `UpdateAlertRuleV1`, `ArchiveAlertRuleOverrideV1`, `GetAlertRuleV1`, `ListAlertRulesV1`, `ResolveEffectiveAlertRuleV1`. Create input: `(command_id, actor_id, condition_type, scope, enabled, configuration, as_of)`; update additionally `(rule_id, expected_record_version)`; archive `(command_id, actor_id, rule_id, expected_record_version, as_of)`. Create asserts no active identical type/scope; existing scope must be eligible at the published registry revision. List filter is bounded by type/scope/archive flag and cursor. Effective query accepts typed subject, condition and `as_of`. Output is rule view/effective view; commands return persisted receipt plus the resulting view.

No builtin mutation. Archive retains audit/history and schedules reevaluation, allowing the next candidate to apply. Rule changes and registry moves trigger durable bounded reevaluation against current producer queries; they do not relabel historical evidence or recover from old observations. Reevaluation compares rule/registry versions as well as source generation, so unchanged current source generation can be reevaluated once under a new policy revision without masquerading as newer producer data.

### CTR-ALERT-002 — alert commands, queries and internal consumption

Ports: `GetAlertV1`, `ListAlertsV1`, `ListAlertHistoryV1`, `AcknowledgeAlertV1`, `SnoozeAlertV1`, `UnsnoozeAlertV1`, `ConsumeAlertSignalV1`, `ReevaluateAlertScopeV1`, `ExpireAlertSnoozesV1`, `PurgeExpiredAlertHistoryV1`, `GetAlertingHealthV1`.

Commands have `(command_id, actor_id, alert_id, expected_record_version, as_of)`; snooze adds `duration_seconds`. View queries have bounded enum/scope filters, optional UTC time range, opaque cursor and limit 1..200. History uses `(alert_id, limit, after_key, as_of)` and aggregate-sequence ordering. Consumer command carries the typed durable event, producer-owned current-condition snapshot and registry scope snapshot; returns `AlertSignalReceiptV1(receipt_id, event_id, disposition, alert_ids, source_generation, processed_at)` with dispositions `applied | duplicate | stale_ignored | not_evaluable | rejected`. No public route can inject a signal.

`AlertSignalV1` is M07's internal normalized immutable input: source reference, subject, condition type, condition semantic major 1, transition `active | recovered | not_evaluable`, decision summary and a **closed union of producer-owned fact records**, described below. Mapping is schema-specific and never decodes raw provider payloads. Purge accepts actual `as_of`, limit 1..1000 and stable job ID; returns `AlertRetentionResultV1(job_id, cutoff_at, examined_count, deleted_alert_count, deleted_history_count, has_more, completed_at)` without row contents. Health returns safe counts/codes/revisions and last successful work time only.

### CTR-ALERT-003/004 — immutable events

`AlertOpenedV1` (003): `(envelope: EventEnvelopeV1, alert: AlertViewV1, aggregate_sequence: int)`; only an actual open transition. `AlertStateChangedV1` (004): `(envelope, history: AlertHistoryEntryV1, alert: AlertViewV1)`. Every payload is the bounded immutable post-transition snapshot and safe cause references. Envelope follows CTR-COMMON-006; durable record follows CTR-EVT-001. Reopen is state changed, not a second newly-created alert. Aggregate sequences are strictly positive and unique per alert. At-least-once delivery, no external sender.

### CTR-ALERT-005 — notification projection and read command

Ports: `ListDashboardNotificationsV1`, `GetDashboardNotificationCountsV1`, `MarkAlertReadV1`. Query filters and pages use the exact backend ordering in §3. Mark read input `(command_id, actor_id, alert_id, expected_notification_revision, as_of)` matches notification revision, not merely record version. A newer escalation cannot be consumed by a stale read. Same receipt replay is safe and cannot mark a newer revision read. No mark-unread or bulk action is added in this increment.

### Shared command rules and authorization

Root has frozen **existing `read:status` for every alert/rule/notification query and new `write:alerts` for commands**. Root reports the M01 authorization/token addition with real Red/Green evidence (four expected failures, then four passes, then twenty Green including real file/reopen behavior); this planning agent has not rerun that evidence. Root owns the remaining OpenAPI/UI synchronization. Do not substitute `write:accounts`. Browser writes require existing Origin/Host/CSRF/session controls; bearer writes require explicit `write:alerts` scope. Workers have internal composed authority, no bearer route for signal injection/expiry/purge. Actor is derived from the authenticated principal, never trusted from JSON.

Every command requires existing P01 `Idempotency-Key`; record mutation also requires `If-Match`. Missing precondition 428, stale nonidentical mutation 412, reused key/different canonical request 409, bad type/range 422, denied 403, absent resource 404, dependency unavailable 503; existing RFC 9457 safe code/correlation response. Store `(principal_id, command_id, canonical_request_digest)` and result references transactionally. An identical authorized replay returns its original receipt before testing the now-stale precondition, with a current view explicitly distinguished if queried; authorization still runs. A new key with stale version cannot mutate even if the requested value equals current state.

### Actual consumed contracts and necessary producer work

The current checkout has no `alerting_v1.py` or `events_v1.py`, no M07 module/repository, and catalog head `v1_0603`. Existing M02/M04/M05/M06 outboxes are real and durable. They are insufficient for alert meaning:

| Owner/contract | Actual source surface | Required additive producer-owned port/payload |
|---|---|---|
| M02 CTR-REG-009 | `RegistryScopeSnapshotV1` and `AlertScopeAndSubjectQueryV1` exist; membership only. | Add `AlertSubjectScopeV1(account_id, provider_key, organization_id, eligible, registry_revision)` and `ResolveAlertSubjectScopeV1(account_id)`; revisioned eligible subject enumeration for reevaluation. No account labels/profile locators. |
| M02 CTR-REG-010 | `AuthenticationHealthChangedV1` DTO exists, with string states and source generation; no current-health query or verified durable producer path was found. | Add `AuthenticationAlertConditionV1(profile_id, account_id, provider_key, generation, state, identity_state, observed_at, freshness_deadline, evidence_ids, reason_code)`; closed normalized auth state, current query and enveloped persisted transition. Healthy recovery requires verified matched identity. |
| M04 CTR-COL-007 | Absent. `CollectionCompletedV1`, `CollectionFailedV1`, global `CollectorHealthV1` and latest run queries exist. `collection.run_terminal.v1` stores only `run_id/state`. | Add `CollectorAlertConditionV1(target_id, account_id?, provider_key, capability_id, generation, health_state, freshness_state, latest_run_id?, last_successful_at?, freshness_deadline?, evaluated_at, reason_code)` and current page/transition event; producer owns staleness deadline, retry/backoff meaning and explicit healthy/current inverse. |
| M05 CTR-CAP-005 | Absent as a published DTO. `QuotaWindowViewV1`, allowance/history/health queries exist. `capacity.committed.v1` stores only `capability_id/projection_count/state`. | Add `CapacityAlertConditionV1(resource_id, account_id, provider_key, window_id, generation, remaining_basis_points?, denominator_kind, availability, exhausted?, reset_at?, freshness_deadline?, observation_ids, precision, confidence, reason_code)` and bounded current query/event. Exact bp derived by M05; missing denominator cannot invent remaining ratio. |
| M05 CTR-CAP-008/009 | Forecast/availability tables allocated, published generation/current alert contracts absent. | Add `ForecastAlertConditionV1(resource_id, account_id, window_id, generation, state, exhaustion_at?, reset_at?, before_reset?, confidence, observation_ids, reason_code)` and `CapacityAvailabilityAlertConditionV1(resource_id, account_id, generation, state, observation_ids, evaluated_at, reason_code)`; current pages and explicit transition/inverse events. M05 owns actual forecast/availability derivation. |
| M06 CTR-RUN-004/005 | `RuntimeStateChangedV1` and `PossibleStallDetectedV1` exist. Current outbox emits `runtime.committed.v1` with `capability_id/observation_count/state`, not these transitions. | Add `RuntimeAlertConditionV1(session_id, account_id?, provider_key, generation, evaluation: PossibleStallEvaluationV1, current: RuntimeStateEvidenceSummaryV1, evidence_ids)`; current port and enveloped detected/cleared events with comparable producer generation. No PID/path/session content in alert payload. |

Question-mark fields in this table mean typed `| None`, never omitted availability meaning. Exact final fields/enums and bounded query selectors are root-owned synchronization output. New types must reuse the already published runtime/provenance/quantity vocabulary rather than duplicate it. `source_generation` is derived from each producer's actual durable projection/health revision; target_generation/run IDs are not a fallback. M07 may evaluate only a fact record whose producer port is implemented and verified; unsupported producer paths remain visibly unavailable.

### CTR-EVT-001 and event topology proposal

Publish `DurableEventV1[TPayload]` with `(envelope, event_schema_major: int, stream_key: str, stream_sequence: int, payload: TPayload, payload_digest: str)`; payload is a finalized typed producer record or a closed typed commit notice, never `dict`. Generic `ReadEventBatchV1` takes `(consumer_key, after_cursor: str | None, as_of, limit=1..200)` and returns `DurableEventBatchV1` with typed events, next cursor and `QueryAvailabilityV1`. `AcknowledgeEventDeliveryV1(consumer_key, event_id, payload_digest, receipt_id, as_of)` records delivery only after the consumer commit. Each producer implements storage/decode/ack **inside its own adapter**; composition dispatches typed payloads, not SQL or imported producer repositories.

Cursor is producer-owned and stable; no global producer-sequence assumption because M04 presently provides stream sequence only. Ordered generations, not delivery order, determine condition state. M07's owned receipt and stream checkpoint commit with projection/history/outbox; producer ack is a second transaction. Crash before ack redelivers into that receipt. A durable consumer checkpoint advances only across committed dispositions; query-unavailable failures remain retryable. Poison/unknown-major events get bounded rejected receipt and degraded health, retained/quarantined by their producer, never silently dropped. Existing commit notice may request a typed current read; it is never interpreted as an activation or recovery itself.

This formalizes the already planned module-owned durable topology. Root determines whether its first executable dispatcher/ack convention needs a new ADR; any reinterpretation of existing published delivery/enum semantics does. No central mutable event table or producer-table reader inside M07 is approved.

## 5. Data and persistence

### Owned schema and exact chain

Root allocates a single linear chain: **`v1_0603 -> v1_0700 -> v1_0701 -> v1_0702`**. Named files are `v1_0700_m07_alert_rules.py`, `v1_0701_m07_alert_lifecycle.py`, `v1_0702_m07_alert_deadlines_outbox.py`. Existing shared revisions are immutable. Built-in policy is code, not seeded rule/telemetry rows. All DDL runs through the existing migration adapter/catalog checks, never startup `create_all`.

| Revision | Owned table / key / principal columns |
|---|---|
| 0700 | `alert_rule`: rule_id PK; condition_type, scope_kind, scope_key (global sentinel only in storage), enabled, closed config_schema/config_json, record_version, actor_id, created/updated/archived_at. Active unique `(condition_type, scope_kind, scope_key)`. |
| 0700 | `alert_rule_revision`: `(rule_id, record_version)` PK; immutable complete config, actor, command_id/time; M07-local FK only. |
| 0701 | `alert_alert`: alert_id PK; unique fingerprint_version/digest plus canonical material; subject/scope scalar IDs; rule snapshot ref or builtin version; severity/lifecycle; occurrence generation/count; record/notification/aggregate revisions; opened/last_seen/recovered/closed/latest_notification times; unread, ack actor/time, snoozed_until/deadline_generation; typed bounded decision JSON. |
| 0701 | `alert_evidence_reference`: reference_id PK; alert_id + aggregate_sequence, producer/event/observation/evidence IDs, stream/generation, code/UTC only; M07-local FK. No copied source payload. |
| 0701 | `alert_event`: event_id PK; unique `(alert_id, aggregate_sequence)`; immutable transition/prior/current state, safe cause/actor/rule refs/time. |
| 0701 | `alert_event_receipt`: receipt_id PK; unique `(producer_key, event_id)`; payload_digest, observed stream/generation, disposition, result alert IDs, processed_at. No upstream payload persistence. |
| 0701 | `alert_stream_checkpoint`: `(producer_key, condition_stream_key)` PK; greatest observed source generation, current evaluable generation/reference, last event/digest, registry/rule evaluation revisions, updated_at. Retained tombstone after alert purge prevents an old source event reopening it. |
| 0701 | `alert_command_receipt`: receipt_id PK; unique `(principal_id, command_id)`; canonical_request_digest, command kind/subject, resulting revision/result IDs, created_at, expires_at; bounded safe canonical response refs. |
| 0702 | `alert_deadline`: deadline_id PK; alert_id, kind='snooze_expiry', deadline_generation, due_at, state, lease_owner/fence/lease_until, completion/receipt ref; unique `(alert_id, kind, deadline_generation)`. |
| 0702 | `alert_reevaluation_job`: job_id PK; cause rule/registry revision, scope, cursor/checkpoint, state, lease/fence/attempt, next_due_at, safe outcome/time. Unique triggering cause/revision/scope. |
| 0702 | `alert_event_outbox`: event_id PK and M07-local event FK; typed schema/envelope/payload; unique alert aggregate sequence, available_at, delivery/attempt/lease fields; no external destination. |
| 0702 | `alert_retention_run`: job_id PK; actual as_of/cutoff, bounded examined/deleted counts, has_more, state/safe code/times; no row contents. |

Checks enforce positive versions/generations/counts, enum vocabulary, paired ack actor/time, snooze/open/deadline consistency, UTC timestamps, threshold bounds and closed JSON schemas. Global/provider/account/org scope validation occurs in published registry ports and domain; no cross-module FK. Indexes cover active rules, subject/scope + lifecycle/severity, notification rank/time/ID, unread/snooze, event sequence, stream generation, due leases/jobs/outbox and terminal retention cutoff. Real query plans decide additional indexes.

### Repository and atomic operations

Define `AlertRuleRepositoryV1`, `AlertQueryRepositoryV1` and `AlertWriteUnitOfWorkV1` in M07 application ports. Queries return published immutable views/pages. Write UoW exposes these specific transactions, not a generic external SQL/session handle:

```python
create_or_change_rule(command, registry_snapshot) -> AlertRuleCommandResultV1
apply_signal(signal, effective_rule, delivery_identity) -> AlertSignalReceiptV1
apply_alert_command(command) -> AlertCommandResultV1
claim_due_deadlines(worker_id, as_of, limit, lease_seconds) -> tuple[AlertDeadlineClaimV1, ...]
complete_deadline(claim, as_of) -> AlertSignalReceiptV1
claim_reevaluations(worker_id, as_of, limit, lease_seconds) -> tuple[AlertReevaluationClaimV1, ...]
apply_reevaluation(claim, producer_snapshot, registry_snapshot, as_of) -> AlertSignalReceiptV1
purge_expired_history(job_id, as_of, limit) -> AlertRetentionResultV1
```

Signal transaction: recheck durable receipt/digest, checkpoint, applied policy revisions and projection version; atomically write receipt, checkpoint, alert projection, evidence, immutable transition, deadline change and outbox. A conflicting writer rolls back and retries from authoritative state; no double count. Rule transaction: receipt + rule/revision + reevaluation job + event/outbox. Command/deadline transactions: receipt + version/fence/generation checks + projection/history/deadline/outbox. An old worker's lease/fence cannot complete a newer snooze. Deadline claims and completion use real UTC; no patched clock.

Published producer/registry queries run before the SQLite write transaction. Snapshots include their revisions; reject and retry if a required snapshot is outdated when reevaluation is admitted. Historical event scope is stored with its actual snapshot; concurrent registry changes enqueue a newer reevaluation, so race handling never silently rewrites history. Root composition supplies only published current snapshots. Transactions remain short with parameterized SQL and existing DB locking policy.

### Retention, backup and portability

Use actual UTC cutoff `as_of - timedelta(days=365)`. Purge terminal alerts/history only when the latest terminal transition is strictly older than cutoff. Retain active alert history, referenced rule revisions/evidence, required idempotency receipts and pending deadlines/jobs/outbox. Never purge a receipt/checkpoint before the producer's documented replay lower bound; unknown replay horizon retains the small stream checkpoint/tombstone. Purge is bounded/idempotent and audited through `alert_retention_run`, using M07 SQL only.

Real fresh and supported prior-file upgrades, foreign-key/integrity checks and isolated backup/restore must preserve fingerprints, aggregate order, receipts, checkpoints and pending work. Restore cannot contact providers or infer recovery. No destructive downgrade; preserve failed DB and use verified backup plus compatible prior binary or forward fix. Exact numeric values are coefficient/scale or canonical decimal strings; SQLite JSON/partial index/BEGIN IMMEDIATE details stay in adapter/migrations, portable relational constraints and scalar IDs remain the contract.

## 6. External and platform boundaries

M07 has no direct provider, OS, subprocess, auth browser or delivery network boundary. It consumes actual persisted producer outputs and reads its own SQLite via DB contract. Provider credentials, default profiles and running agents remain untouched. Producer queries are side-effect-free and do not start collection in a request. Bounded local dispatcher/reevaluation retries use producer availability and safe codes, not provider-error strings. M04 owns collection timeout/backoff/rate limiting; M07 cannot increase polling to satisfy a test.

## 7. Security and privacy

Root-owned HTTP admission/Origin/CSRF/IAM applies before M07 commands. Validate all scope IDs through published registry authority, versions, command keys, ranges, page limits, UTC and closed fact schemas. No signal-injection API, arbitrary URL/path, free-text note, external destination or expression evaluation. Bound payload/tuple/config sizes and processing batches; invalid/unknown fields fail before persistence. Diagnostics and test evidence contain module/condition codes, counts, opaque refs, versions and times only: **no account email, label, project/provider path, prompt/response/source, environment, credential, raw terminal or provider output**. Authorized product labels use separate registry/UI mapping. Alert DB holds no secrets. Audit actor identity is opaque and transport-derived.

## 8. Configuration and operations

Persist rule overrides as runtime settings with version/audit; no hardcoded accounts and no environment override of owner rules. Built-in threshold policy version `m07-builtin-1`; 3000/1500bp. Snooze bounds 60..2592000 seconds; retention 365 days. The existing draft allocation of `AGENTMONITOR_ALERTING_DEADLINE_SCAN_INTERVAL_SECONDS`, `AGENTMONITOR_ALERTING_WORK_BATCH_COUNT`, `AGENTMONITOR_ALERTING_LEASE_SECONDS` remains unapproved until root synchronizes exact settings. Proposed technical defaults: scan every 30 seconds (5..300), batch 100 (1..1000), lease 120 seconds (30..600) for strictly bounded local work; lease extension/fenced retry is explicit. No secret setting or new scheduler package.

Composition runs bounded due-deadline, reevaluation, delivery and retention participants with browser closed. M07 health reports DB availability, pending/due counts, oldest backlog age, last successful work and safe rejected-source codes. Failure preserves existing alert truth and marks module degraded; it never fails unrelated collection/UI queries. M08 schedules daily retention through M07 port and collects sanitized health/export/restore participants. Root must provide canonical commands before dependent lifecycle readiness; absent routines are not replaced by manual success claims.

## 9. Test design before implementation

All rows below are **Not Run for this proposed increment**. Each changed behavior requires its own meaningful behavioral Red before production change, then Green/refactor. Missing Python import alone is not sufficient behavioral Red once dependencies are available. No fabricated telemetry at any I/O boundary.

| ID | Layer / dependencies | Initial expected Red | Pass condition |
|---|---|---|---|
| A-P01 | Pure; constructed typed scopes/rules only | Wrong specificity/disabled fallback | Every precedence pair; whole-document replacement; unresolved identity has no invented candidates. |
| A-P02 | Pure; exact quantities | Wrong inclusive boundary/rounding | 3001bp no alert, 3000 warning, 1500 critical; fractional bp on either side; validation and unknown/zero distinctions. |
| A-P03 | Pure; closed condition facts | False recovery from success/unknown or old generation | Each source family and explicit inverse, current/stale/unknown separation, waiting exclusions, newer-only recovery. |
| A-P04 | Pure; fingerprints/reducer | Duplicate count, wrong merged condition/order | Stable identity under severity/rule/group change, collision reject, duplicate/equal/older generation, current snapshot ordering and explicit policy reevaluation. |
| A-P05 | Pure; lifecycle/explicit UTC | Stale read/ack/snooze hides escalation | Repeat/ack/snooze/escalation/recovery/reopen; duration bounds; fenced deadline generation; notification ordering/counts. |
| A-P06 | Pure; retention/cursor | Boundary removes active or retained evidence | Exact 365-day cutoff, dependency/replay guards, bounded stable cursor and aware UTC. |
| A-DB01 | Real file SQLite/full migrations + actual admin-created rule configuration | Rules/migration/constraint/version behavior absent | Fresh and 0603 upgrade, active uniqueness, optimistic write, exact replay, restart persistence and effective source. Rules are configuration, not seeded telemetry. |
| A-DB02 | Real file SQLite + actual live quota/history producer output via published port | Consumer/receipt/projection/outbox absent or non-atomic | Actual source opens according to dynamic quota and configured rule; same real event redelivery has one receipt/transition/outbox; newer real poll repeats once; restart/older real events cannot regress. |
| A-DB03 | Same actual durable source + concurrent production connections | Double receipt/count or partial commit | Concurrent duplicate/competing generations and database transaction failure leave atomic receipt/checkpoint/history/deadline/outbox. Exercise real constraint/locking failure, no patched repository. |
| A-DB04 | Real active alert from A-DB02 + actual UTC wait/service restart | Ack/read/snooze absent, stale write accepted, lost deadline | Authorized settings actions persist; min-duration real snooze expires once; race/escalation requires actual newer producer evidence or stays Blocked. No backdated source/snooze timestamps. |
| A-DB05 | Real migrations/backup/isolated restore | Wrong head/integrity or replay after reopen | Exact three revisions, existing row preservation, no hidden DDL, checkpoints/outbox/lifecycle survive restart/restore. |
| A-DB06 | Real naturally aged alert DB | Retention missing or wrong eligible deletion | Actual >365-day terminal history purged in bounded audited batches and active/required data retained; **Blocked if no real aged alert exists**, pure cutoff is separate. |
| A-HTTP01 | Real Uvicorn/IAM/SQLite + actual registry config | Rule routes/permission/schema absent | CRUD, effective explanation, query bounds, If-Match/key/conflicts, anonymous/CSRF/scoped-bearer denials cause no mutation. |
| A-HTTP02 | Same server + actual source-opened alert | Commands/history/notifications absent or GET mutates | Safe GET, read revision, ack/snooze/unsnooze/version/key/restart, correct counts/history; generated schema compatibility. |
| A-UI01 | Production build/real browser/server/registry | Threshold editor/precedence explanation absent | Whole rule source shown, units/bounds, keyboard/focus, honest empty/unavailable states. |
| A-UI02 | Built browser + real alert | Console/actions/history absent | Text/icon severity, actual subject/source/freshness, unread/ack/snooze filters/counts and timeline; reload; 1920x1080/responsive/zoom. |
| A-UI03/A-ARCH01 | Actual bundle/routes/imports/schema/network + review | Forbidden module/external path or schema drift | Generated client only; no external sender, direct producer SQL, provider mutation, arbitrary payload, PII diagnostics or unapproved dependency. |
| A-LIVE01 | Existing actual Claude quota/history | Current condition port/alert source absent | Reconcile same account/window/provenance and threshold with dynamic actual reading. Safe owner alert-rule override can place the **real** current value in warning/critical without inventing capacity or consuming credits; restore prior rule through its versioned command. |
| A-LIVE02 | Real naturally reauth-required profile then approved healthy auth | Auth source/open/recovery path missing | Durable auth condition with verified identity and newer inverse; no default-profile write. Blocked if actual state is unavailable. |
| A-LIVE03 | Real stale collector/current resumed collection | Explicit stale/healthy source missing | Producer-owned freshness generation opens/recover once; actual elapsed deadline; no arbitrary process interruption. |
| A-LIVE04 | Actual M06 inferred stall and waiting/clear evidence | Runtime condition/recovery source absent | Detected/cleared generations and waiting exclusion; no sending input/signals to an agent. Blocked if naturally unavailable. |
| A-LIVE05 | Actual M05 exhausted/unavailable/forecast/reset | Source condition/inverse missing | Correct distinct truth, severity and newer recovery with real lineage. Blocked rare conditions remain named, not covered by pure construction. |

Initial commands follow the canonical M4 story test paths but must be registered by root in the executable runner before dependent readiness. Proposed backend selection: `backend/.venv/bin/python -m pytest -vv backend/tests/alerting/pure/test_policy.py backend/tests/alerting/persistence/test_v1_0700_0702_alerting.py backend/tests/integration/alerting/test_signal_lifecycle.py`. Root supplies the real HTTP/browser commands and a fail-closed `AUTO-M4-ALERTS` scope gate, then composes the M4 exit gate. These are planned names, **not an assertion that an executable gate exists or passed**. `AUTO-DOCS-CHECK`, `AUTO-QUALITY`, contract/OpenAPI/client checks, real migrate/backup/restore and branch-safe Git preflight are required at their owning phases. Real rare/aged/performance acceptance limitations are explicit; no universal TDD/live/full M07/M4 claim follows from a narrow Green.

## 10. Implementation increments

| Increment | Assigned change | Failing test first | Exit condition |
|---|---|---|---|
| I0 | Root freezes exact contract fields/enums/generations, producer storage/current ports, M01 permission and migration ownership; publishes ADR if needed. | Contract/API/boundary scenario design plus actual existing source inventory | Approved plan/contract baseline, canonical planning readiness; no private-gap workaround. |
| I1 | M07 `domain/policy.py`, `fingerprint.py`, `lifecycle.py` and pure tests | A-P01..06 | Meaningful pure Red/Green/refactor; every critical decision branch and admitted mutation control. |
| I2 | Root-allocated revisions + M07 application ports and SQLite repository rule/receipt/query operations | A-DB01/05 | Fresh/upgraded real files, catalog/range integrity, persistent actual configuration. |
| I3 | M07 `application/consume.py`; producer current/storage ports composed by root | A-DB02/03, A-LIVE01 | Actual source atomic receipt/checkpoint/transition/deadline/outbox and durable redelivery/restart. |
| I4 | M07 `application/commands.py`, due workers, notification/history/retention participants | A-DB04/06 | Real actions/time/restart; unavailable aged deletion remains explicitly Blocked. |
| I5 | Root/P01/P02 API, composition, generated schema/client and alert/rule feature | A-HTTP01/02, A-UI01..03 | Real server/built browser command guards and truthful console; no fake alert setup. |
| I6 | Producer families, M08 operations and canonical acceptance | A-LIVE02..05, A-ARCH01; migrate/restore/security/docs gates | Source-specific results Passed/Failed/Blocked/Not Run; completion claim equals actual green gate scope. |

Producer gaps block only their affected integration; approved pure and owned repository increments may proceed once root freezes their contracts. No parallel shared contract/catalog/compose/OpenAPI/generated write. The root allocates each shared write and integration sequence. If frozen contracts change, stop affected work and return to synchronization; never duplicate a DTO or read another module's table.

## 11. Documentation outputs

Root coordinates `docs/modules/alerting.md`, CTR-ALERT/EVT/producer contract reference, configuration registry, traceability, API/client notes, migration/recovery notes, threat/privacy updates, operations runbook, alert Red/Green/live matrix and M4 acceptance record. Explain default/specificity, precision, evidence, recovery, notification counts/read/ack/snooze, retention/replay and limitations. Add operator commands only after canonical implementations exist and were exercised. Each handoff lists IDs, versions, files, Red/Green/refactor and every real boundary/status without emails or paths.

## 12. Dependency and license impact

No dependency added. Standard-library dataclasses/typing/hashlib/Decimal/time values and admitted DB/FastAPI/React/Playwright stack are sufficient in their owning layers. No scheduler/event-bus/rules-engine/notification library. Manifests/lockfiles/SBOM/notices remain unchanged for M07; any later admission returns to security/license/transitive review before use.

## 13. Risks and unresolved synchronization

| Item | Impact | Required root/owner resolution |
|---|---|---|
| Missing typed source generation/current inverse/event storage | False alert/recovery or no delivery | Freeze §4 producer additions and dispatcher/ack/checkpoint semantics before I3. Generic commit notices are insufficient. |
| Source/registry/rule race | Wrong specificity or stale policy | Revisioned snapshots, distinct policy reevaluation token, durable jobs, no historical relabel. |
| Freshness/forecast/availability meaning unimplemented upstream | FR-ALERT-003 falsely claimed | Producers implement actual derivation/current query or keep affected source unavailable and acceptance Blocked. |
| New `write:alerts` compatibility | Commands denied or overbroad access if mappings drift | Root reports M01 authorization/token Red/Green; complete OpenAPI/UI synchronization and actual route denial/success tests. |
| Receipt retention/replay horizon unspecified | Old input reopens purged lifecycle | Retain checkpoints/tombstones; producers publish replay lower bounds before deleting relevant receipts. |
| Real aged/rare/multiaccount conditions absent | Overstated live acceptance | Explicit Blocked evidence; no backdating, seeded telemetry, manufactured stalls/credit exhaustion. |
| Automation/ADR/migration allocation absent | Premature lifecycle claim | Root publishes canonical gates, approves exact migration and topology review; plan status stays Proposed until then. |

Stop/escalate on missing/version-changing producer contract, inferred identity, required raw provider/process/credential data, other-module SQL/import, destructive migration, extra dependency, unavailable real gate, or overlapping shared-file ownership. The authorized product goal is preserved; affected work cannot silently bypass these boundaries.

## 14. Delivery and rollback

Publish synchronized additive V1 contracts/permissions first; freeze migration metadata; take verified backup and upgrade explicitly; enable M07 durable workers only after actual source/replay evidence; expose generated API/UI; run canonical scope gate and record rare/aged limitations. Existing APIs and producer profile/process behavior retain their meaning. New payload/scope/identity/ordering reinterpretations require a major migration/ADR, not silent reuse of V1.

Prefer forward fix preserving alert history. Disable a defective consumer through approved service configuration while retaining source/outbox/checkpoints for replay. If rollback requires an unsupported schema downgrade, preserve current DB and restore a verified isolated backup using a compatible binary; run integrity/receipt/fingerprint/deadline checks before service restart. No rollback deletes provider state or controls running agents.

## 15. Definition of ready

- [x] M4 user implementation authority and exact M07 requirements/non-goals identified.
- [x] Module paths, privacy constraints, ownership, expected Reds and real resource needs proposed.
- [x] Root froze read:status, new write:alerts, and genuine producer condition-stream generation semantics.
- [ ] Root approves plan version and exact CTR-ALERT/EVT/producer contract synchronization.
- [ ] Migration/catalog/schema-range/shared-write allocation and topology ADR decision recorded.
- [ ] Configuration, security/privacy/license/retention/backup review accepted.
- [ ] Canonical planning readiness and dependent test/migrate/backup/restore/completion automation available and green for the claimed scope.
- [ ] Source-specific live prerequisites/status acknowledged; no unresolved decision permits materially different production behavior in the next increment.

## 16. Approval record and planning handoff

| Reviewer | Decision | Evidence/conditions | Date |
|---|---|---|---|
| Root/integration | Pending | Approve this 0.1.0 proposal; freeze source contracts and shared write ownership before implementation | — |
| Producer / DB / IAM / API / UI / operations / security / test reviewers | Pending | Review respective boundaries and exact typed schema/generation/replay/migration/test semantics | — |

Planning result: only this document added. No tests/gates/live actions run in this planning task, no production implementation or full M4 completion claimed. Root's next step is concrete contract synchronization/approval and explicit M07 pure/repository/migration allocation. The proposed module interfaces and real-source test design are inspectable here; missing producer/automation artifacts remain named work, not satisfied gates.

## 17. Approved bounded I03 contract packet — 2026-09-29

Root approved I03 under the owner-authorized M4 objective after reviewing the
published M05 current-condition and durable-delivery ports. This approval covers
capacity remaining/exhausted mapping and real source-to-owned-storage consumption.
Other producer families, user commands and operational retention remain separate.

```python
# Additive CTR-ALERT-002 V1, M07 sole writer under root stewardship.
class ConsumeCapacityAlertEventV1(Protocol):
    def __call__(
        self, event: DurableEventV1[CapacityCommittedNoticeV1],
        account_id: OpaqueIdV1, *, as_of: datetime,
    ) -> AlertSignalReceiptV1: ...

# Internal M07 application records/ports, not API signal-injection DTOs.
PreparedCapacityAlertV1(
    signal: NormalizedAlertSignalV1, effective_rule: EffectiveAlertRuleViewV1)

class CapacityAlertReceiptRepositoryV1(Protocol):
    def lookup_capacity_event(
        self, event: DurableEventV1[CapacityCommittedNoticeV1],
    ) -> AlertSignalReceiptV1 | None: ...

    def commit_capacity_event(
        self, event: DurableEventV1[CapacityCommittedNoticeV1],
        prepared: tuple[PreparedCapacityAlertV1, ...], *, as_of: datetime,
        recheck_current: Callable[[], None],
    ) -> AlertSignalReceiptV1: ...

class DeliverCapacityAlertEventV1:
    # Compose the published consumer and AcknowledgeCapacityEventV1.
    # Acknowledge only after a genuine committed receipt; retries replay it.
    def __call__(self, event, account_id, *, as_of) -> AlertSignalReceiptV1: ...
```

The consumer receives `ListCapacityAlertConditionsV1`,
`ResolveAlertSubjectScopeV1`, `ListAccountResourcesV1` and
`ResolveEffectiveAlertRuleV1` through published typed contracts only. Composition
finds the supplied account through its actual registry resource inventory;
`event.envelope.subject_id` is a **resource ID**. Consumer admission rechecks that
the resource is active and belongs to the supplied eligible account at the
authoritative registry revision. No account identity is inferred from notice text.

Current-condition reads are bounded and fail closed on partial/unavailable pages,
duplicate dimensions, changed membership or changed rule/current revisions.
Before the transaction writes, an application-owned guard repeats published
current/membership/rule queries. Production composition uses the same installation
database so its owned `BEGIN IMMEDIATE` excludes concurrent writer commits while
those read-only published queries validate admission. No M07 foreign SQL or
producer repository import is permitted.

Condition stream identity is `"capacity:" + sha256(canonical_json([
account_id.value, resource_id.value, window_id.value]))`, at most 73 characters.
The original window remains the typed subject dimension. Each condition gets an
independent checkpoint keyed with its condition type so exhausted and remaining
evaluation cannot suppress each other. Generation is exactly the current fact's
durable projection generation; producer stream sequence and collection target
generation are never substituted. M07 does no remaining-percent derivation.

Current exact facts yield remaining/exhausted activation or explicit inverse;
stale, unknown, unsupported, unavailable and partial facts yield not-evaluable.
Threshold precision and original observation lineage are retained. An old notice
may cause a read of a newer current fact; its projection count does not constrain
signal count. Unavailable capacity awaits a genuine dedicated producer condition.

One transaction commits the trigger event's exact digest/receipt, affected alert
IDs, independent checkpoints, projections, immutable history/evidence and typed
outbox. Same event ID/digest returns the original receipt; changed digest conflicts.
Current-read failures write nothing. Producer acknowledgement follows only the
successful consumer commit and supplies that actual receipt ID. A failed
acknowledgement leaves the durable receipt available for exact retry.

Real tests may read selected actual M05/M02 source ports and write the resulting
genuine alerts to isolated M07 storage. They must not insert telemetry, mutate the
owner database, manufacture generations/recovery, or acknowledge owner producer
delivery. Root performs the installation's actual acknowledgement/restart gate.
Pure constructed mapper inputs prove policy only. Root owns canonical gates,
API/UI/composition, migration catalog/fingerprint and operational deployment.

## 18. Approved bounded I04 alert actions and read models — 2026-09-29

Root approved this next owned increment after the genuine I03 isolated SQLite
consumer proof. It covers existing public `CTR-ALERT-002/005` V1 ports exactly:

```python
GetAlertV1(alert_id: OpaqueIdV1, *, as_of: datetime) -> AlertViewV1 | None
ListAlertsV1(query: AlertListQueryV1) -> QueryPageV1[AlertViewV1]
ListAlertHistoryV1(query: AlertHistoryQueryV1) -> QueryPageV1[AlertHistoryEntryV1]
ListDashboardNotificationsV1(query: AlertListQueryV1) -> QueryPageV1[DashboardNotificationViewV1]
GetDashboardNotificationCountsV1(query: AlertListQueryV1) -> DashboardNotificationCountsV1
AcknowledgeAlertV1(command: AcknowledgeAlertCommandV1) -> AlertCommandResultV1
SnoozeAlertV1(command: SnoozeAlertCommandV1) -> AlertCommandResultV1
UnsnoozeAlertV1(command: UnsnoozeAlertCommandV1) -> AlertCommandResultV1
MarkAlertReadV1(command: MarkAlertReadCommandV1) -> AlertCommandResultV1

# M07-internal owned persistence port; no foreign SQL or web auth bypass.
class AlertActionRepositoryV1(Protocol):
    def get_alert(self, alert_id: OpaqueIdV1) -> AlertViewV1 | None: ...
    def list_alerts(self, query: AlertListQueryV1) -> QueryPageV1[AlertViewV1]: ...
    def list_history(self, query: AlertHistoryQueryV1) -> QueryPageV1[AlertHistoryEntryV1]: ...
    def lookup_alert_command(self, command: AlertUserCommandV1) -> AlertCommandResultV1 | None: ...
    def apply_alert_command(self, command: AlertUserCommandV1) -> AlertCommandResultV1: ...
```

`AlertUserCommandV1` is the closed union of existing acknowledge, snooze,
unsnooze and mark-read commands. One real SQLite `BEGIN IMMEDIATE` transaction
checks durable `(principal_id,command_id)` receipt/digest first, matches the
record or notification revision and applies the existing pure reducer. It writes
projection, immutable history and published alert outbox, plus a versioned
deadline for snooze or an atomic cancellation for unsnooze/recovery/escalation.
The original result snapshot is retained for exact replay after later changes.
Same command ID with different canonical input fails; new stale versions fail.
GET/list never acknowledge or mark read. Counts separate visible unread from
total unread; bounded UTC/keyset pages and account/provider/organization scopes
use only M07 projection columns and approved read:status. Web admission/CSRF and
write:alerts remain root/P01-owned.

Tests use actual I03-produced alerts from genuine M05/M02 facts in a private
real migrated SQLite file; there are no fabricated alert rows or provider
outputs. Actual user alert commands are local admin actions on that isolated
file. Source recovery/elapsed deadlines still require genuine newer conditions
and clock evidence; no backdated telemetry or invented recovery is admissible.
Root will wire HTTP/client/browser only after owned I04 real Red/Green evidence.
