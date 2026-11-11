# M7 API budgets: deliver a working dashboard first

- Status: Draft for review; planning refactor requested by the owner, not implementation approval.
- Plan version: 1.1.0; supersedes focused 1.0.0.
- Owner: root integration; primary financial semantics: M05 Capacity.
- Baseline: `a47fc53` on `codex/m7-api-budgets`; accepted M6 remains deployed.
- Requirements: FR-BUDGET-001..006, FR-ORG-003, FR-ACC-001..004/006;
  AC-LIVE-004/005/007, AC-UI-002..006, AC-HIST-001, AC-OPS-003/006,
  AC-TEST-001..006.
- Parent scope: [five M7 stories](../../superpowers/plans/2026-09-19-agentmonitor-v1-m7-api-budgets.md).

## 1. The delivery promise

The owner adds a real billing account, connects it, and sees its reported spend
on Overview and account detail, with organization, billing scope, period and
freshness. That whole journey is the first usable slice. Other providers and
advanced views do not precede that demonstration.

The full M7 scope still includes Anthropic, OpenAI and supported Ollama cloud
usage, provider-exposed budgets/credits/limits, supported breakdowns, history,
forecasts, real comparisons and safe deployment. Names/counts are owner-defined.
M6 is not reopened. No local Ollama work, agent switching, provider mutations,
inference spending, invoices/tax/FX, local budget editing or unrelated redesign.

Critical expectation: cost APIs may expose spend without exposing remaining
funds or an enforced limit. In that case M7 shows useful spend/history and a
clear missing-balance/forecast reason. It must not promise a percentage or date
that the provider data cannot support. A subscription login is not billing API
access. These are known product limitations, not surprises to discover at exit.

## 2. One authoritative plan set

| Artifact | Owns |
|---|---|
| [UI and user journeys](m7-ui-and-user-journeys.md) | Exact screens, controls, setup, LAN flow, state copy and browser acceptance |
| [Calculation and data rules](m7-calculation-and-data-rules.md) | Formulas, exactness, time/coverage, shared pools, empty reports, corrections and forecast eligibility |
| [M05 increment](../modules/m05-capacity/m7-budget-increment-2026-11-11.md) | Contracts, storage, import boundaries and test sequence |
| [Ticket catalog](m7-ticket-catalog-v1.json) | Sixteen stable ticket IDs, dependencies, delivery slices, acceptance and actual status |
| [Source discovery](../../evidence/m7-provider-discovery-2026-11-11.md) | Official documentation versus unverified live account facts |
| [Refactor review](../../evidence/m7-plan-refactor-2026-11-11.md) | Actual hazards found, bounded review and validation results |

These focused documents override conflicting implementation instructions in the
historical M7 plan only within this proposed change: additive money/report
contracts, necessary new migrations, supported empty results, UI-first delivery
and simple query-time forecasts. They do not waive the real-boundary/TDD rules.
Approval covers the synchronized focused set once. Routine fixes inside it do
not require a new plan version or owner ceremony. New financial meaning, secret
custody, dependency, destructive operation or incompatible contract does.

## 3. What the owner sees

Keep existing navigation/header/footer. Accounts gains Add API billing account
and capability-based sections so an API-only account is not sent to CLI login.
Setup has a visible connection action, one copied nonsecret local command and
an explicit Enable API monitoring action. The owner never manually types opaque
account IDs or supplies repeated account attestations.

Overview keeps subscription quotas and adds a compact API usage & spend table:
Billing account | Organization | State | Reported spend | Available | Data through.
Both sections share organization/provider filters. Grouped organization/global
spend summaries preserve currency, exact period and cost basis, deduplicate
known shared pools and disclose missing coverage. No misleading mixed total.

Account detail presents money and its meaning first, then supported breakdowns,
exact history/chart, and a forecast or reason it is unavailable. Connection and
source diagnostics are compact/expandable. Refresh readings rereads stored data;
Collect now is a separate rate-limited action. See the UI document for exact
states, sorting, controls, pagination, responsive and accessibility behavior.

## 4. Delivery slices and checkpoints

Ticket dependencies express prerequisites, not permission to hide all UI until
all backend work is finished. Each slice ends with the indicated running result.

| Slice | Tickets in execution order | Demonstration / exit |
|---|---|---|
| S0: known prerequisites | T001; start T003; T004 exactness; T002 owner setup | Plan/contract freeze, scoped test commands, tested setup UI; known access needs identified once |
| S1: first usable dashboard | First available provider T006/T008/T009 → T005 → T007 → T010 → T011 → T012; T014 deployment | One real owner-created billing account goes through collection, exact history table, Overview/detail and installed browser. No numeric-forecast prerequisite |
| S2: provider coverage | Remaining T006/T008/T009 | All three provider lanes use the same working screens; actual unsupported fields remain explicit |
| S3: complete M7 views | T013 | One-dimension breakdowns, simple history chart and explainable query-time forecast; later refinements are not added |
| S4: stabilize and publish | T015 → T016 | Real cross-provider/browser reconciliation, one bounded independent review, one full exit run, remote revision verified and owner demonstration |

First provider defaults to Anthropic if access is available; otherwise use a real
available OpenAI or Ollama lane without dropping Anthropic from M7. A requests-only
legacy source can advance its own usage lane but cannot substitute for the first
demonstrated monetary report. T005 depends
on one completed provider adapter, not a hardcoded account. Missing access to one
lane blocks its live evidence only. No invented demo account or seeded telemetry.

T010 closes the current/list/summary/history HTTP slice; forecast/breakdown HTTP
and later UI enhancement belong to T013. This removes the earlier UI↔forecast
completion dependency. T014 begins operational design immediately and supports
the first installed slice; it does not wait until the last week.

First-slice results are explicitly partial M7 delivery. They are not milestone
completion. The full original three-provider/five-story scope remains required.

## 5. Minimal architecture and exact ownership

| Owner | Allowed work / contract |
|---|---|
| Foundation/root | Correct context-dependent exact decimal conversion under CTR-COMMON-003 without changing its public range; sole shared contract writer |
| M02 | Registry account/resource purpose, scope association, opaque credential binding/generation; independent billing monitoring; API-only eligibility and archive/disconnect rules |
| A01/A02/A03 | Official read-only endpoint allowlists, role/version admission, exact mapping, scope/dimension semantics and source delay; no direct DB writes |
| M04 | Existing one-run admit/collect/commit/reconcile flow; budget receipt/run variants for empty and observation-only reports; bounded per-report pagination and source throttling |
| M05 | Exact signed cost, report coverage/replacement, budget/current/history/aggregation query ports and pure forecast policy |
| P01 | Authenticated typed HTTP, safe action/response states, schema/client generation; no adapter or database access in handlers |
| P02 | Existing Accounts/Overview/detail components, capability-driven rendering, API-only values and formatting; no financial computation in React |
| Root/operations | Serial composition/generated files/migration catalog, installed setup command, selected-candidate build/deploy/recovery and canonical verification |

Root owns contracts, migration order, composition and generated artifacts;
module agents receive nonoverlapping paths after synchronization. Provider-specific
code stays under `adapters/providers/{claude/anthropic_api,codex/openai_api,ollama/api}`.
Capacity code stays under its domain/application/ports and SQLite adapter.
P02 extends existing account/overview features and a budget-history component.

Reuse frozen budget/usage tables where their semantics fit. Allocate additive
M05 revision `v1_0730` after `v1_0720`, M02 `v1_0731`, and M04 `v1_0732` only if
its typed receipt/run change needs schema. Preserve old migration digests.
Do not automatically create one-to-one tables for every field: use necessary
additive context columns, a report-coverage relation and signed cost storage.
No forecast storage table or parent/child job engine. The first real report
measures whether the documented bounds fit; query page size is not a collection
batch size. Exact details are in the M05 and calculation documents.

### API contract allocation

All telemetry reads require `read:telemetry`; mutations use existing admin/CSRF
and concurrency controls. GET never starts collection. Additive V2 budget types
use the existing tagged cloud subject; old quota/V1 DTO semantics stay intact.

| Route under `/api/v1` | Operation | Ticket |
|---|---|---|
| `GET /budgets` | `capacity_list_budget_overview_v1`: filtered rows and backend grouped summaries | T010 |
| `GET /accounts/{account_id}/budgets` | `capacity_list_budgets_v1` | T010 |
| `GET /budgets/{budget_id}` | `capacity_get_budget_v1` | T010 |
| `GET /accounts/{account_id}/api-capacity` | `capacity_get_account_api_budget_v1` | T010 |
| `GET /budgets/{budget_id}/history` | `capacity_list_budget_history_v1` | T010 |
| `GET /budgets/{budget_id}/usage-breakdowns` | `capacity_list_usage_breakdowns_v1` | T013 |
| `GET /budgets/{budget_id}/forecast` | `capacity_get_budget_forecast_v1` | T013 |

T002 owns account billing-connection status/metadata, verify and disconnect
HTTP/UI; T007 wires verification/collect-now jobs. POST metadata/verify returns
real IDs/status with idempotency and account generation. No key values in JSON.
M04/M05 expose additive receipt/run variants supporting real empty coverage
without fictitious observations/events. Existing consumers are tested against
new budget capability routing; quota alert semantics remain unchanged.
New budget alert rules are outside M7; do not build forecast events for them.

## 6. Credential permission and owner work

Proposed extension of the existing protected `.env` mechanism: AgentMonitor
runtime alone can store an owner-entered Anthropic/OpenAI administrative API
credential and read the binding-specific entry for admitted read-only billing
GETs, and use Ollama's key for its official usage GET in addition to balance.
The coding agent never views keys. No secrets in browser, arguments, source,
logs, database, evidence, exports or backups. No provider profile read/write,
key listing, inference or provider mutation. Fixed HTTPS origins, no redirects.

The account page supplies the exact installed command and host context. Owner
creates records/associations, enters keys locally and enables monitoring. The
agent builds/tests that experience and opens required pages; it does not ask
for unavailable buttons or manually configure owner accounts. Key rotation
invalidates old access proof and in-flight generation without deleting history.
No new dependency. Approval is needed for this focused plan/permission, once;
all repeatable implementation/test/deploy actions inside it proceed autonomously.

## 7. Fixed completion catalog

| ID | Required result | Principal tickets |
|---|---|---|
| M7-A01 | Owner-created billing setup, API-only/mixed-purpose UI and safe credential lifecycle | T002/T007/T011 |
| M7-A02 | Exact money, signed corrections, valid totals, periods, availability and separate pools | T004/T005 |
| M7-A03 | Real Anthropic permitted reports and source comparison | T006/T015 |
| M7-A04 | Real OpenAI permitted reports and source comparison | T008/T015 |
| M7-A05 | Real supported Ollama usage with shared balance semantics | T009/T015 |
| M7-A06 | Supported breakdowns, immutable corrected/empty-report history, chart and conditional forecast | T010/T013 |
| M7-A07 | Authenticated HTTP/client and built UI; real IAM, keyboard/responsive checks | T010/T011/T012 |
| M7-A08 | Compact filtered Overview, valid organization/global grouped totals and useful states | T012 |
| M7-A09 | Rate/size/deadline bounds, one source failure isolation and genuine recovery; protected profiles untouched | T007/T015 |
| M7-A10 | Revision-bound install/recovery, existing dashboard/provider continuity and final evidence | T014/T016 |

Required live coverage is one real successful billing report per provider plus
inventory accounting for every configured active billing resource. No fixed
six/four-account ceremony. Existing comparisons record exact resource, interval,
source time and precision once; reuse them for documentation changes. Technical
changes invalidate only affected evidence lanes until the final candidate run.

Numerical forecast validation is conditional on naturally adequate compatible
source history/remaining funds. Correct unavailable/insufficient-input behavior
is required and tested when that is the real state. Report the numerical live
scenario Not Run/Blocked; do not mistake it for a pass or force spend to obtain it.
Natural 401/403/429/exhaustion cases are listed individually when unobserved;
required access/reconciliation cannot be silently declared optional. Controlled
failure/recovery uses isolated real resources without taking the live dashboard
down, revoking credentials or restarting owner agents.

## 8. Testing, deployment and closure without an endless loop

T003 implements one runner with technical/live/browser/exit selections behind
the registered canonical commands; reuse existing checks. No new general gate
framework, detached approval hierarchy or manual owner-code paste workflow.
Start each changed behavior with meaningful Red at its real boundary. The money
rules document provides exact pure test cases; I/O proof uses real provider
reports, real SQLite/migrations, real HTTP and a real built browser.

T014 is limited to this AgentMonitor user service and an explicitly selected
clean revision. Reuse build sealing/locks/backup/recovery helpers, remove only
the M6 fixed-worktree assumption. Do not build a general deployment platform.
Before transition verify schema/backup/rollback, then loopback/LAN readiness and
installed revision. On failure restore the known-good runtime safely. Never
restore an old database after new writes without explicit recovery authority.
Promotion/support/footer/quota/filter behavior must survive each rollout.

After S3, freeze known defects. Run one full `AUTO-M7-EXIT` and one bounded
independent review. New blockers must prove a stated requirement/invariant is
violated and name the smallest fix. Enhancements go to the deferred list below;
no silent gate expansion. T015 uses live/browser lanes; T016 runs the technical
exit, publishes current code to GitHub, verifies remote revision, demonstrates
the result and records acceptance separately. Publication never gates itself.
GitLab mirror authentication cannot block authorized GitHub delivery.

Planning check: `python3 tools/automation/run.py AUTO-M7-PLAN-CHECK`.
Documentation, quality, Git preflight and synchronized baseline checks retain
their existing commands. M7 execution commands remain fail-closed until built.
The already-passing 66 automation/planning tests are prerequisites, not M7 proof.

## 9. Risks, scope control and estimates

Known risks are now explicit: administrative access, absent balances/limits,
provider lag, complete-empty/corrected reports, shared pools, exact-decimal
context, oversized minimum reports, API-only account eligibility, later-page
accounts and installed setup/deployment. Each maps to a named ticket and test.
Provider documentation proves a supported interface, not owner credentials or
live behavior. Missing input pauses its dependent lane only.

Deferred improvements: user-set budgets, FX/invoice reconciliation, arbitrary
multi-dimension query builder, custom reports, advanced/statistical forecasts,
new budget alert policies, durable page/child-job orchestration without proven
need, remote secret entry, additional top-level history screens, general
multi-host deployment and all local Ollama work. These are not exit conditions.
Existing supported one-dimension breakdowns, aggregation, chart and conditional
forecast are retained in M7; they are not removed under the word simplification.

Effort estimate, not promise: S0/S1 about 3–5 focused engineering days after
usable access; S2 2–3; S3 1–2; S4 1–2. Total 7–12, excluding provider/owner wait.
The first installed vertical is the checkpoint to revise estimates from measured
work. Report completed tickets and visible behavior, current failing test and
next demo every work session. If two sessions produce no new user-visible slice,
review the dependency causing delay instead of adding more infrastructure.

## 10. Approval state

This refactor was authorized as planning work. Production implementation and the
new runtime credential scope are still pending approval of version 1.1.0; the
previous 1.0.0 question no longer describes the proposed plan. No hidden account
configuration, production migration, deployed change or new dependency is made
by preparing these artifacts. After approval record it once and execute S0/S1.
