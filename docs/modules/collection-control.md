# M04 collection control

M04 owns collection schedules, durable runs, local event history and current collector conditions. Its versioned public surface is `contracts/collection_control_v1.py`; consumers use these contracts and M04 application facades rather than reading M04 tables.

The M4 alert increment publishes `CollectorAlertConditionV1` with a target-scoped positive generation from `collection_alert_condition.record_version`. The named internal `refresh` command classifies actual M04 schedule/run/reference records and atomically writes a changed condition plus `collector.health_changed.v1` event. Repeated identical evidence does not advance a generation. Read-only `get_current` never invokes a provider or mutates storage; it reports partial availability for missing, mismatched or expired unevaluated projections.

A fully succeeded current-target run with committed references and a current collection deadline is the only healthy/current inverse. Partial, running, failed, blocked, unsupported, paused and missing inputs cannot prove recovery. Freshness is the fully succeeded run's completion plus the schedule's actual effective interval. An advised retry is persisted in nullable run metadata but is not an applied backoff unless the schedule actually carries a deferral.

The M04 SQLite adapter owns the projection and event read/ack path. Acknowledgement binds the exact payload digest to a consumer receipt. Other modules consume the published typed event and never import M04 SQL or provider data. The bounded writer's two-second budget covers local SQLite busy/VM work on the approved data root; filesystem and OS scheduling stalls are outside that guarantee.

See `docs/plans/integration/m4-collector-alert-condition-change.md` for the approved increment and `docs/evidence/m4-collector-alert-conditions.md` for test status and remaining real-history verification.

## Exact Ollama cloud source signal

The additive `CTR-COL-008` read port projects the latest M04-owned result for
one exact Ollama cloud account, credential generation, access target,
capability, source, adapter, source-policy fingerprint and payload schema. It
classifies only closed journal facts: verified success, credential
unauthorized, provider-schema incompatibility, rate limit, transient failure,
credential-store authorization unavailable, or unresolved. It never interprets
free-form reason text and never calls the provider. The view also carries the
exact run/admission lineage, dispatch certainty, observation time and the
authoritative provider-global rate-gate state.

A changed source fingerprint or target has no matching signal and therefore
returns unresolved. An active or uncertain attempt also remains unresolved.
The sole exclusion is the caller's own still-active, exact, pre-dispatch rate
lease: M04 revalidates the global gate, schedule, account, target, credential
generation, source lineage, fencing token and reserved journal phase before it
can look past that one attempt. A bare admission ID, dispatched attempt,
expired lease or mismatched source cannot be excluded. The projection is a
read-only composition input; it does not grant a request, replace M04
admission, or establish provider identity. Actual scheduled dispatch must
still use that same durable lease.

The companion exact verification-job read accepts the original probe's
`(run_id, admission_id)` from the M02 receipt. Composition must require its
terminal response-received success and matching M05 commit; a later scheduled
signal cannot substitute for the original probe result.
