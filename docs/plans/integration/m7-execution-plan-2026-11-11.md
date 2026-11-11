# M7 API budgets: focused execution plan

- Status: Draft — prepared for owner approval; no M7 production implementation authorized yet.
- Plan version: 1.0.0.
- Owner: root integration steward; primary semantic owner: M05 Capacity.
- Parent: [M7 five-story plan](../../superpowers/plans/2026-09-19-agentmonitor-v1-m7-api-budgets.md).
- Requirements: FR-BUDGET-001..006; AC-LIVE-004/005/007;
  AC-UI-002..006; AC-HIST-001; AC-OPS-003/006; AC-TEST-001..006.
- Scope ledger: [M7 ticket catalog](m7-ticket-catalog-v1.json).
- Source evidence: [official provider discovery](../../evidence/m7-provider-discovery-2026-11-11.md).
- Baseline: `f7a1799b04be762e1eb81c79d83d50d9bbcfcceb` on
  `codex/m7-api-budgets`. Accepted M6 is not reopened.

## Outcome and fixed boundary

The owner can configure real API billing accounts through the dashboard, connect
their credentials locally without exposing them, and see exact API spend,
provider-exposed balances/limits, supported breakdowns, history and forecasts.
Subscription quota remains visibly separate. Unknown data never becomes zero,
unlimited capacity, a healthy state, or a fabricated exhaustion date.

All five existing stories ST-BUDGET-001..005 remain in scope. Anthropic, OpenAI
and supported Ollama cloud APIs are included. Account counts and names are
owner-configured, not hardcoded test conditions. Missing API access is not
inferred from subscription sign-in state. No local Ollama inventory/activity,
model execution, inference spending, payments, provider budget mutations,
agent switching, unrelated UI redesign, or M8 release-wide work is included.

## Current implementation evidence

`BudgetViewV1` is a reserved four-field DTO. Existing exact quantities, tagged
cloud subjects, collection receipts, provenance, quota history, IAM and real
browser runner are reusable. Budget write/query ports, HTTP endpoints, budget
history/forecast contracts and UI panels are absent. Existing quota forecasts
require an installation/window and cannot be silently reused for cloud money.

Existing M6 deployment routines require a fixed M6 checkout. M7 deployment and
rollback are an explicit ticket now. Historical M7 npm browser/accessibility
commands do not exist; use the real P02 browser runner behind the new canonical
M7 commands. No production service changes are part of this planning change.

## Module ownership and contract synchronization

| Owner | Allowed implementation area | Published/consumed contract decision |
|---|---|---|
| M02 Registry | `modules/registry`, registry persistence and `registry_v1.py` additive types | Owner-created billing resource and credential binding metadata; opaque references only; dashboard organization distinct from provider organization |
| M03/A01 | `adapters/providers/claude/anthropic_api`, provider contract schema | Typed exact usage/cost batch; official analytics beta admission; no default profile access |
| M03/A02 | `adapters/providers/codex/openai_api`, provider contract schema | Typed usage/cost batches, per-category capability matrix, administrative API authentication |
| M03/A03 | `adapters/providers/ollama/api`, approved cloud transport seams | Usage purpose and shared balance references; do not duplicate M6 pools |
| M04 | `modules/collection_control`, its persistence | Additive capability and result routing through CTR-COL-006; bounded jobs, leases, retry/backoff, independent source failures |
| M05 | `modules/capacity`, `adapters/persistence/capacity`, additive contracts | CTR-CAP-002 V2 budget views/queries; V2 history/forecast variants and typed budget commits; exact semantics in the linked module plan |
| P01 | `api/v1/routers`, `api/v1/schemas`, `api/v1/dependencies.py` | Additive `/api/v1` HTTP operations; generated artifact writer is root only |
| P02 | `frontend/src/features/accounts`, `history`, `overview`, shared client wrapper | API-only budget panels; no browser credential values or provider requests |
| Integration/M08 | composition, migrations catalog, `tools/automation`, operations documentation | Serial wiring, candidate deployment, backup/recovery and completion evidence |

The [M05 increment](../modules/m05-capacity/m7-budget-increment-2026-11-11.md)
owns exact DTO fields, arithmetic, persistence and forecast policy. Shared types,
migration catalog, generated OpenAPI/client and composition have one writer:
root. Allocate additive migrations after `v1_0720`: M05 `v1_0730`, M02 `v1_0731`,
M04 `v1_0732` only if its routing requires stored schema. Do not alter old
migrations or rename existing routes. Freeze the chain before parallel writers.

New contract definitions are published before their implementation wave.
`BudgetViewV1` and quota APIs stay compatible; no fabricated installation IDs.
Existing M07 consumers must tolerate the new event variants without treating
money as quota percentages. M08 retention/export must preserve budget lineage
and exclude credentials; release-wide M08 features remain M8 scope.

### API/UI surface

All reads require `read:telemetry`; configuration mutations require the existing
administrative scope, CSRF and concurrency checks. No GET performs collection.

| Route under `/api/v1` | Stable operation ID | Behavior |
|---|---|---|
| `GET /accounts/{account_id}/budgets` | `capacity_list_budgets_v1` | Bounded list of distinct billing pools |
| `GET /budgets/{budget_id}` | `capacity_get_budget_v1` | Exact current fields and provenance |
| `GET /budgets/{budget_id}/usage-breakdowns` | `capacity_list_usage_breakdowns_v1` | Allowlisted dimensions, bounded period/cursor |
| `GET /accounts/{account_id}/api-capacity` | `capacity_get_account_api_budget_v1` | Account summary with explicit completeness |
| `GET /budgets/{budget_id}/history` | `capacity_list_budget_history_v1` | Immutable monetary observations and revision lineage |
| `GET /budgets/{budget_id}/forecast` | `capacity_get_budget_forecast_v1` | Method, inputs, confidence or insufficient-input reason |

M02 billing enrollment uses an additive billing-connection resource under an
account: GET status, POST create/update metadata, POST verify, DELETE disconnect
only AgentMonitor's binding. No key value enters these bodies. A local no-echo
credential command accepts the opaque binding ID and an owner-selected `.env`.
The account page supplies an actionable command and status before asking the
owner to connect. Connection verification is queued, bounded and auditable.
Owner organization/account configuration is never performed by a coding agent.

Overview gains a compact, separately labeled API-budget section with existing
organization/provider filters. Account detail preserves subscription quota and
adds budget, exact breakdown table, history chart/table, and source details.
Keep promotion, donation link, footer, sorting, low-quota semantics and 24-hour
session behavior unchanged. No cross-currency or overlapping-pool totals.

## Proposed credential permission — requires this plan's approval

Extend the existing M6 exception only for the AgentMonitor runtime: it may
store an owner-entered Anthropic administrative API credential, OpenAI
administrative API credential, or Ollama API key in a selected protected
AgentMonitor-managed `.env`, then read the binding-specific entry transiently
for the approved read-only billing requests. The coding agent does not view
keys. Owner enters them locally without echo; no keys in browser, logs, source,
database, backups, exports, evidence, shell history or command arguments.

Allowed HTTPS destinations are fixed provider origins and documented GET cost/
usage paths in the discovery record; Ollama balance keeps its existing scope.
No redirects, arbitrary URLs, provider profile access, inference, key-listing,
key-creation, budget updates, or authentication changes. Administrative keys
can be powerful upstream: the local transport nevertheless exposes only the
read allowlist. Connection status says access verified, not identity verified,
unless the provider response actually establishes the identity/scope.

No new dependency is proposed. Use existing admitted HTTP/SQLite/frontend tools
and exact decimal primitives. Changing credential custody or adding a dependency
requires a separate concrete approval; routine internal fixes do not.

## Delivery tickets and sequence

The linked JSON catalog is the status/dependency ledger, not evidence of
implementation. Every ticket has a requirement, expected Red, acceptance,
deliverable and verification command. Sequence:

1. **M7-T001..003:** source/contract freeze, credential enrollment, executable
   exit-catalog foundation. Start independent pure and empty real-stack tests.
2. **M7-T004..007:** exact budget core, Anthropic collector, real persistence
   and scheduling. Demonstrate one complete real API budget slice.
3. **M7-T008..009:** OpenAI and Ollama collectors through the same contracts.
   An unavailable account blocks only its live verification lane.
4. **M7-T013, then M7-T010..012:** exact forecasts and bounded history/retention,
   HTTP/generated client, account budget/history screens and Overview.
5. **M7-T014..016:** portable candidate deployment/rollback, real provider/UI
   reconciliation and continuity, one bounded review, publication and acceptance.

Planning range: roughly 7–12 focused engineering days after plan approval and
usable billing access, excluding owner/provider wait time. This is an estimate,
not a completion promise. Re-estimate against delivered tickets after the first
vertical slice; report the reason and affected tickets rather than extending
scope silently. Each work session reports delivered behavior, current ticket,
actual failing test and next observable result.

Enrollment HTTP/UI belongs to M7-T002, including truthful queued/unavailable
verification status. Its completion does not claim a provider read. M7-T006
supplies the real Anthropic adapter output used by M7-T005 persistence tests;
M7-T007 later supplies full scheduler and multi-page completion proof. This
avoids a store/scheduler completion cycle. HTTP work can start from frozen DTOs,
but M7-T010 closes only after M7-T013 supplies history and forecast ports.

## Fixed acceptance catalog

| ID | Required observable result | Primary ticket |
|---|---|---|
| M7-A01 | Owner-controlled enrollment and safe access/status for each configured billing account | M7-T002 |
| M7-A02 | Exact money, currency, periods, field availability and pool separation end to end | M7-T004 |
| M7-A03 | Anthropic real permitted collection and authoritative reconciliation | M7-T006 |
| M7-A04 | OpenAI real permitted collection and authoritative reconciliation | M7-T008 |
| M7-A05 | Ollama supported real usage with preserved shared balance semantics | M7-T009 |
| M7-A06 | Supported dimensions/time buckets, immutable revisioned history and truthful forecast | M7-T013 |
| M7-A07 | Authenticated versioned HTTP/generated client and real accessible built UI | M7-T010 |
| M7-A08 | Compact filtered Overview/account panels with separate pools and truthful unavailable states | M7-T012 |
| M7-A09 | Rate/deadline/size bounds, independent failure and scheduled recovery, unchanged default profiles | M7-T007 |
| M7-A10 | Candidate-bound rollout/rollback, existing provider/dashboard continuity and prepared evidence | M7-T016 |

## Test-first sequence and evidence rules

| Test IDs | Boundary and expected Red | Green proof |
|---|---|---|
| M7-REG-001..004 | Real SQLite/HTTP: billing binding/status absent; missing authority rejected | Owner-created resource, binding isolation, idempotent verification; no key disclosure |
| M7-CAP-001..008 | Pure exact-domain missing budget policies/typed fields | Money/period/scope/availability/forecast invariants; constructed inputs only here |
| M7-DB-001..005 | Real migrated SQLite: budget commit/query/history absent | Provider-collected observations round-trip exactly, receipt conflict/replay, revisions retained |
| M7-PROV-A01..A03 | Real selected provider read: missing collection/mapping capability | Each official source reconciles exact fields, dimensions and completeness; absent access is Blocked, not Red |
| M7-COL-001..004 | Real scheduler: budget capability not routed | Bounded jobs, safe failures, another provider and dashboard remain live, genuine later success |
| M7-HTTP-001..006 | Real Uvicorn/IAM: missing budget routes | 401/403, safe errors, bounded pages, schemas, no collection from GET, exact field propagation |
| M7-UI-001..006 | Built browser: budget sections/actions missing | Real API-to-DOM equality, 1920×1080/responsive/keyboard/table checks and quota continuity |
| M7-OPS-001..004 | Real candidate: M6 fixed-checkout updater refuses M7 | Reproducible sealed candidate, backup/rollback journal and revision-bound installed browser |

No recorded provider payloads, network fakes or inserted telemetry. Fresh empty
SQLite is valid for migration/empty/IAM tests, not proof of budget collection.
Provider-only cases await actual provider conditions. Exhaustion, 401/403/429
and provider revisions need not be induced; unobserved cases stay explicit.
Required core coverage cannot be silently converted to optional coverage.
Compare a single authoritative observation with the same scope, period and
source freshness; reuse that timestamped evidence without repeated attestations.

## Completion and operations

`python3 tools/planning/validate_m7_tickets.py` is the planning-only check.
M7-T003 implements `AUTO-M7-TEST`, `AUTO-M7-LIVE`, `AUTO-M7-BROWSER` and
`AUTO-M7-EXIT`; they are unavailable until implemented, never presumed passing.
The exit command must check all ten acceptance items, all five stories, real
checkout/deployed lineage, Red/Green evidence and required live lanes. Optional
natural-state limitations are listed separately. One report suffices; no manual
account-ID paste ceremony. Gate state and milestone owner acceptance are distinct.

Use additive migrations, backup before migration and preserve a sealed previous
runtime. Validate rollback compatibility before service transition. Never
restore an old database after new writes without explicit recovery authority.
The live dashboard stays on accepted M6 until the candidate passes the relevant
checks; never stop the service merely to gather evidence. M7-T014 must include
recovery after interrupted activation and loopback/LAN health verification.

Update module/API/provider docs, security permission, configuration/runbook,
traceability, generated artifacts and current status overlay with each slice.
At stabilization, freeze the known defect batch, run one full exit gate and one
independent review under the existing convergence rule. Only a demonstrated
scope/invariant violation reopens the batch. Publish the current branch's actual
code to GitHub main with existing user authority and verify remote revision;
do not call a locally staged tree published. GitLab authentication does not
block GitHub delivery. M8 remains the final release-wide milestone.

M7-T015 closes on the candidate-bound live and browser lanes. M7-T016 runs the
full technical exit gate, then publishes the verified revision and records
remote verification and owner acceptance. Publication is not a prerequisite of
the technical gate; it remains a required T016 completion condition. The gate
checks scenario evidence rather than requiring its own closing ticket already
be marked done.

## Approval and stopping rules

Approval of this 1.0.0 plan covers the bounded cross-module increments and the
runtime credential exception above, not provider mutations or new dependencies.
The existing blanket system-action authorization does not fabricate an M7
module-plan approval. Record the owner's actual approval once; do not request
it again for internal corrections within this scope.

A new real secret exposure, destructive migration, incompatible public contract
or missing required authentication pauses that affected action only. Identify
the exact evidence, continue independent authorized work, and ask only for the
smallest required user input. A draft document, assumed account name or
unavailable optional natural-state test is not authority to halt all work.
