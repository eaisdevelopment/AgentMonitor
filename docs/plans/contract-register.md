# AgentMonitor contract register

- Status: **Draft-aligned; owner approval and implementation authorization are absent**
- Register version: 0.2.1
- Machine-readable authority: [contract-baseline.toml](contract-baseline.toml)
- Source review: [contract-alignment audit](integration/contract-alignment-audit.md)
- Ownership allocation: [parallel-ownership.toml](parallel-ownership.toml)
- Owner: integration steward
- Updated: 2026-11-02

## Purpose and authority

This register is the human index for the proposed AgentMonitor V1 contract
baseline. `contract-baseline.toml` is the complete machine-readable inventory:
99 unique contract IDs, proposed version, one semantic producer, explicit
consumers, maturity, decision reference, and semantic checklist.

`Draft-aligned` means the producer/consumer direction and cross-plan ownership
conflicts have a single proposed resolution. It does **not** mean Approved,
Implemented, live-verified, or authorized for implementation. Provider- and
platform-dependent entries remain `evidence_blocked` until real M0 evidence.

The superseded 0.1.0 Concept tables are intentionally not retained as a second
source of current status. Their history is recoverable from the read-only
alignment audit, which reviewed all 76 original IDs before this register was
normalized.

## Baseline summary

| Measure | Draft-aligned baseline |
|---|---:|
| Total contracts | 99 |
| Original registered contracts retained | 76 |
| Accepted missing contracts added | 23 |
| `proposed_aligned` | 64 |
| `evidence_blocked` | 35 |
| Synchronized/Approved/Implemented | 0 |
| Cross-plan resolutions recorded | 18 |

Every contract proposes semantic version `1.0.0`. The version is not approved
until producer, consumers, reviewers, and owner accept the exact baseline.

## Contract families and sole semantic producers

| Family | IDs | Semantic producer | Principal consumers | Maturity |
|---|---|---|---|---|
| Common values | CTR-COMMON-001..007 | PLAN-FND, except provider provenance CTR-COMMON-004 by PLAN-M03 and API problem CTR-COMMON-005 by PLAN-P01 | all modules and boundaries as enumerated in baseline | mixed; provenance evidence-blocked |
| Configuration | CTR-CONFIG-001 | PLAN-FND mechanism; each plan owns its keys | all configured components | proposed-aligned |
| Foundation | CTR-FND-001..008 | PLAN-FND | every plan as enumerated | proposed-aligned |
| Identity/access | CTR-IAM-001..008 | PLAN-M01 | P01, P02, M08, DB/DEP where enumerated | proposed-aligned |
| Registry | CTR-REG-001..011 | PLAN-M02 | M03–M08, adapters, P01/P02 | mixed; provider identity/reauth/credential integration evidence-blocked |
| Provider system | CTR-PROV-001..008 | PLAN-M03 | A01–A03, M02/M04–M08, P01/P02 | evidence-blocked |
| Collection | CTR-COL-001..008 | PLAN-M04 | M05–M08, A03, P01/P02 and PLAN-INT as enumerated | proposed-aligned |
| Capacity | CTR-CAP-001..009 | PLAN-M05 | M07/M08, P01/P02 | evidence-blocked |
| Runtime | CTR-RUN-001..007 | PLAN-M06 | A04 implementations, M02/M07/M08, P01/P02 | evidence-blocked |
| Alerting | CTR-ALERT-001..005 | PLAN-M07 | M08, P01/P02 | proposed-aligned |
| Operations/application overview | CTR-OPS-001..007, CTR-APP-001 | PLAN-M08 | all participant modules, P01/P02, DB/DEP | proposed-aligned |
| API/client | CTR-API-001..003, CTR-UI-001 | PLAN-P01 owns semantics; PLAN-FND owns generator mechanism; PLAN-INT is sole generated-artifact writer | P02 and external clients | proposed-aligned |
| Persistence | CTR-DB-001..003 | PLAN-DB technical semantics; domains retain business repository semantics | M01–M08, DEP/INT | proposed-aligned |
| Deployment | CTR-DEP-001 | PLAN-DEP | M08, DB, A04, P01/P02, INT | proposed-aligned |
| Platform | CTR-PLAT-001 | PLAN-FND portable semantic primitive; A04 Linux/macOS implement | M06/M08/DB/DEP | evidence-blocked |
| Integration/evidence | CTR-INT-001..006 | PLAN-INT | every plan/release automation | proposed-aligned |
| Durable events | CTR-EVT-001 | PLAN-INT technical governance; DB implements; domains own event meaning | M02–M08 | proposed-aligned |
| Safe external boundaries | CTR-BOUNDARY-001..003 | PLAN-FND for subprocess/file; PLAN-M03 for provider HTTP | provider/platform adapters, M06/M08/DB/DEP | mixed; provider HTTP evidence-blocked |

The exact consumer list for every ID is deliberately maintained only in the
machine-readable baseline to prevent drift between a prose table and automation.

## Accepted additions from detailed planning

| IDs | Reason |
|---|---|
| CTR-COMMON-007 | Preserve missing/null/unknown/unsupported/unavailable/not-applicable/withheld/stale/zero distinctions end to end |
| CTR-REG-008..010 | Durable reauthentication workflow, alert-scope query, and normalized auth-health change |
| CTR-REG-011 | Internal non-secret credential-binding lifecycle and exact generation fence; no key, store path, or public account-view field |
| CTR-COL-006..008 | Commit/receipt seam, current/change collector-health input, and durable Ollama cloud admission without M04 owning provider I/O or observation tables |
| CTR-CAP-008..009 | Forecast and availability generation/recovery signals required by M07 |
| CTR-OPS-007 | Module-owned retention/export/consistency participant ports for M08 orchestration |
| CTR-DB-003 | Typed database snapshot/preparation/activation receipts split from service/artifact activation |
| CTR-INT-001..006 | Executable gates, evidence references, frozen baseline, release candidate, acceptance index, and routine results |
| CTR-EVT-001 | Durable outbox/receipt/checkpoint/replay behavior beyond the common event envelope |
| CTR-BOUNDARY-001..003 | Safe subprocess, provider HTTP, and approved-root/file-read boundaries |
| CTR-APP-001 | Server-owned global dashboard overview without P01/P02 domain inference |

CTR-EVT-TOPOLOGY-001 is the machine-validated physical allocation for
CTR-EVT-001, not a second public contract: M02–M08 each own their transactional
producer outbox under their own table prefix; consumers own their processing
receipts/checkpoints; PLAN-DB implements reusable persistence/dispatcher
mechanics through published module ports; PLAN-INT governs the registry. A
central event table and cross-module SQL are prohibited. This is Draft-aligned
and still requires owner approval before implementation.

CTR-COL-009 1.0.0 is the M04-owned no-response terminal contract for the
Ollama cloud rate lane. It records a terminal time and proven `not_started`
certainty without claiming an HTTP response. The v1_0712 overlay is
transactionally authoritative over the retained V1 admission shadow. Existing
V1 response-received completion remains unchanged; older schema clients cannot
read v1_0712. Real account, concurrency, recovery and upgrade evidence remains
outstanding.

CTR-COL-008 is a narrow additive exception authorized by the owner-approved M6
Ollama cloud plan. It is distinct from CTR-COL-001 request intent and
CTR-COL-002 run state because it grants one fenced provider-global request
start, persists the next permitted start and fair cursor, and records only
sanitized completion timing. Reusing either older contract would silently
change its replay and side-effect meaning. This authorization does not approve
or implement the rest of the Draft-aligned baseline.

## Accepted cross-plan alignment decisions

The exact normative wording is stored under `[[resolutions]]` in the baseline.
In summary:

1. Full synchronization, semantic gate, and explicit owner approval precede W0.
2. Dashboard authentication and provider reauthentication use distinct states
   and UI/HTTP flows.
3. Provider auth uses canonical `reauthentication_required` mapping.
4. One-time secrets are never replayed by idempotency handling.
5. M06 owns process-inspection semantics; A04 implements them.
6. Platform semantics are portable and single-owned; OS adapters implement them.
7. P01 owns API schemas, FND owns generator mechanics, INT writes generated
   artifacts, and P02 consumes the wrapper.
8. Deployment artifact/unit activation, database activation, and restore
   authority are separate typed phases.
9. M08 owns maintenance intent; DEP owns fenced service quiescence receipts.
10. Readiness is acyclic: M08 consumes a narrow service fact, while DEP may
    display M08 readiness.
11. M05 owns normalized capacity health; M07 owns alert thresholds/precedence.
12. P01 never invokes providers and uses M02's reauthentication workflow.
13. Performance evidence means 100 registered accounts and 200 simultaneous
    real processes, never seeded provider claims.
14. Persistence implementations use one module-scoped SQLite adapter layout.
15. One contract package convention is frozen before scaffolding.
16. Provider extensions use one producer-owned versioned namespace under M03
    governance.
17. A01 owns Anthropic API, A02 OpenAI API, and A03 supported Ollama API; M0
    decides capability maturity, not ownership.

## Semantic checklist

Every baseline contract carries all nine review dimensions. `true` means the
dimension is explicitly governed by the aligned conventions and must be
specialized or marked not applicable by producer/consumer review; it is not a
claim of implemented behavior.

- field-state/null behavior;
- units and time;
- dashboard/provider authorization;
- allowed and prohibited side effects;
- idempotency and concurrency;
- event generation/delivery/recovery;
- retention/export/recovery;
- typed sanitized errors;
- compatibility and migration.

## Contract state transitions

```text
concept or plan-local proposal
  -> proposed_aligned
  -> evidence_blocked (when real facts are still required)
  -> synchronized (producer and every consumer review exact version)
  -> approved (owner/reviewer approval)
  -> implemented (real contract-boundary evidence)
```

`evidence_blocked` is not later or better than `proposed_aligned`; it identifies
a proposal whose support/shape still depends on real provider/platform evidence.

## Change and review rules

1. One contract has exactly one semantic producer. Implementers do not become
   co-producers.
2. Consumers never redefine names, nullability, units, time, auth, errors,
   idempotency, event, retention, or compatibility behavior.
3. A provider-dependent closed union may be proposed before M0, but it cannot
   assert a capability is Supported.
4. Contract examples are structural and never provider telemetry or test data.
5. Breaking changes require a new major, an ADR, consumer migration, data/API
   compatibility plan, and owner approval.
6. The UI consumes only generated API contracts; P01 consumes only application
   contracts; DB implements module repository ports; adapters remain isolated.
7. Implementation starts only after the semantic planning gate and exact owner
   approval. This Draft baseline alone provides neither.

CTR-REG-012 records owner-asserted cloud connection status and exact-binding verification evidence. CTR-COL-010 records durable verification jobs and idempotent initiation; its existing one-request V2 application boundary remains available while an additive atomic V2 port (`2.0.0`) adds exact external request-version fencing. Replay uses only the original client identity and preserves the first call's server-derived graph/binding snapshot. CTR-COL-011 is the read-only scheduled-lane status. All are candidate contracts under review; populated live behavior remains unverified.
