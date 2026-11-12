# M7 delivery-plan clarification after scheduling delivery

Status: planning/documentation review on checkout
`d5cd774de75175f18711ad2e31fd272477813857`, not implementation or live
acceptance. Owner request: deep planning for proper UIs, budget calculations and
predictable delivery, keeping the first working result simple. Root integration
owns this reconciliation; M05 owns financial meaning and P02 owns presentation.

The approved plan remains 1.1.0: sixteen tickets, five stories and M7-A01..A10.
No new ticket, acceptance condition, approval, dependency or runtime contract is
introduced. Ticket states remain two done, eleven in progress and three planned.

## Findings and decisions

| Evidence / existing requirement | Choice and owner | Reason / rejected alternative |
|---|---|---|
| Scheduling evidence records concurrent Overview HTTP 504; serial probes pass. M7-A07/A08, T010/T012 | Pull the existing reliability packet forward; reproduce concurrent real reads under ordinary collection, measure and correct the smallest bottleneck | Dashboard correctness includes working concurrent reads; serial tests, a larger timeout or hidden missing rows cannot establish that |
| Worksheet requires both ranges for first demonstration but later defines one interval. T005/T006/T008/T010–T012 | First money demonstration is one genuine complete interval, end to end; both ranges remain mandatory for provider/collection closure | Deliver useful money early without silently reducing M7 scope |
| Current worksheet/calculation text still calls delivered cloud actions, fair range scheduling and counts-only state handling unimplemented. T007/T009/T012 | Retain installed code/evidence and specify only outstanding category/live/recovery cases | Prevent rebuilding completed increments or reopening T004 |
| AccountPage uses initial_connection_purpose for apiOnly; UI plan requires resource-driven mixed sections. M7-A01/A07, T002/T011 | Explicit API-origin → mixed-resource acceptance, published capability classification and pending fallback | Creation intent is not current resource capability; do not build another account page or mutate owner configuration |
| Calculation section4 promises missing new-day coverage while Refresh preserves the interval. T010/T012, M7-MATH-15 | Refresh checks selected coverage; only Latest completed window advances the cutoff | Prevent misleading date labels and unwanted collection |
| Multiple ranges/categories/pages share the source request allowance. M7-A09, T007 | Compare actual scheduled request demand and service time with admitted allowance; distinguish due cadence from full refresh time | Do not multiply allowance per key, silently drop categories or add workers to evade a source limit |
| Execution plan repeats old installed revision, operation count and scheduling state | Worksheet remains deployment/order authority; execution plan names stable scope and links current evidence | Avoid competing current-state records |

Read-only independent M05 and P02 reviews supplied the range, refresh, mixed
account and stale-status findings. Root inspected the actual AccountPage routing,
Overview application path, ten-second transport deadline and recorded installed
browser failure. The performance correction is planned, not implemented here.
Provider capability inventory is retained from the existing discovery; this pass
does not claim a new official-source check or newly successful provider access.

## Detailed coverage retained

The existing UI plan covers owner setup, API-only/mixed accounts, organization
and provider filters, compact tables, funds-only/counts-only states, shared pools,
period/history navigation, current versus historical funds, failed refresh,
conflicts, sign-in return, keyboard/zoom/layout, and separate collection actions.
The calculation plan retains exact decimal arithmetic, signed adjustments,
whole-report replacement, empty versus missing, compatible totals, deduplication,
coverage/time cutoffs, independent funds, exact low thresholds, forecast input
eligibility/expiry/renewal and bounded retention. These are existing scenarios,
not new implementation systems. The catalog keeps their requirement/test links.

The eight delivery batches remain: cloud action verification; first real money;
source lifecycle/history discovery; finite provider coverage; final UI/totals;
chart/breakdown/conditional forecast/retention; operational proof; fixed release.
The known Overview defect is pulled forward from UI/totals. Missing monetary
access affects its live assertions only; independent implementation continues.
All account setup stays owner-controlled. No repeated credentials, account lists,
opaque-code confirmations or owner setup request is introduced by this review.

Keep deferred: local Ollama, custom budgets, FX/invoices/tax, token-price cost
estimates, new alerts, multidimension report builders, statistical forecasting,
remote secret entry and general deployment/queue infrastructure. Required charts,
supported breakdowns and conditional forecast remain M7. No calendar delivery
promise is inferred from test counts; re-estimate remaining work after the first
genuine monetary vertical using measured work and explicit access waits.

## Impact and verification

Changed: focused execution plan, delivery worksheet, UI journeys, calculation
rules, ticket catalog, M05 increment and this evidence. No production files,
provider calls, account settings, credentials, database, migrations, public
contract versions, dependencies, license, service or public repository changed.
This review requires planning/documentation checks, not production Red/Green.

Validation against this planning change:

- `python3 tools/automation/run.py AUTO-M7-PLAN-CHECK`: Passed; sixteen tickets,
  five stories and ten acceptance items traced.
- `python3 tools/automation/run.py AUTO-DOCS-CHECK`: Passed; 390 Markdown files.
- `python3 tools/automation/run.py AUTO-PLAN-CHECK`: Passed; synchronized baseline.
- `git diff --check`: Passed.

These checks validate planning structure/references, not implementation. Full
live monetary, analysis, recovery and final acceptance work remains as described
in the worksheet. Changes are local to the M7 worktree; no runtime activation or
publication was performed for this planning task.
