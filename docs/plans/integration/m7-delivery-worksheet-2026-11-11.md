# M7 delivery worksheet: the remaining path to a working dashboard

Status: execution clarification within approved focused plan 1.1.0, reviewed
against `ad7a04e` on 11 November 2026. Primary owner: root integration; financial
owner: M05. This review introduces no new milestone, approval, dependency or gate.

The [ticket catalog](m7-ticket-catalog-v1.json) is the only task tracker:
16 stable tickets, five stories, M7-A01..A10. The [UI plan](m7-ui-and-user-journeys.md)
owns screen behavior; [calculation rules](m7-calculation-and-data-rules.md) own
financial meaning. This worksheet replaces accumulated implementation notes
with the current execution order. Earlier findings remain in
[review evidence](../../evidence/m7-plan-refactor-2026-11-11.md).

## 1. What exists, and what the user still cannot do

| Boundary | Actual checkpoint | Remaining proof/work |
|---|---|---|
| Installed dashboard | Setup revision `7e252b8`, schema `v1_0731`; operational checks and later existing-provider observations recorded | Authenticated setup proof pending; no installed M7 financial screens |
| Local committed code | `ad7a04e`: exact money/report rules, three bounded source candidates, M02 billing authority, M04 budget receipts/recovery and M05 storage; financial schema `v1_0733` | Genuine financial report commit/query and full source-to-screen journey unverified; not deployed |
| Current uncommitted work | Billing CLI/supervisor/wake, Check POST and run-status GET, account financial GET and Check/detail controls have scoped tests. Real no-report HTTP/browser checks and aggregate local quality pass; boundary/private-import corrections are verified | Credential-backed Check-to-report-to-screen proof, monitoring mutation/schedules, Overview and dedicated history remain. These local results are not installed financial delivery |
| User outcome | No verified M7 monetary report on installed Overview/detail/history | Connect collection actions → worker → stored report → API → browser and install that complete slice |

Evidence: [installed setup](../../evidence/m7-setup-installed-2026-11-11.md),
[billing authority](../../evidence/m7-billing-authority-2026-11-11.md),
[collection control](../../evidence/m7-budget-collection-control-2026-11-11.md),
[storage](../../evidence/m7-budget-repository-2026-11-11.md),
[financial recovery](../../evidence/m7-financial-schema-recovery-2026-11-11.md).
These are scoped results, not M7 acceptance. The catalog retains one completed
planning ticket; no implementation ticket is closed by this review. T010/T011
are In progress with [HTTP evidence](../../evidence/m7-budget-http-2026-11-11.md),
[application query evidence](../../evidence/m7-account-financial-query-2026-11-11.md)
and [built no-report UI evidence](../../evidence/m7-account-financial-ui-2026-11-11.md).
The [Check POST evidence](../../evidence/m7-billing-check-http-2026-11-11.md)
proves HTTP guards, not a successful provider report. The
[current-query evidence](../../evidence/m7-budget-current-query-2026-11-11.md)
and [dispatch evidence](../../evidence/m7-budget-dispatch-2026-11-11.md) remain
explicitly narrower than populated financial integration.

## 2. Delivery order and visible checkpoints

Each row is an increment of existing tickets, not another tracker or gate.
Ticket dependencies govern closure; they do not prevent independent work or
require a full provider ticket before its first genuine report can feed the UI.

| Order | Existing tickets | What the owner can actually see | Completion evidence for this increment |
|---|---|---|---|
| 1. Finish the first collection journey | T002/T003/T004/T005/T007 and one of T006/T008/T009 | Check connection progresses to a genuine stored report, with scope/period or a useful access error; monitoring can be enabled independently of subscription monitoring | Real owner configuration, provider read, atomic receipt, reopen/query; queued is not connected and supervisor success is not a report |
| 2. Deliver first money on the dashboard | T010 → T011 → T012; T014 | Overview and account detail show the same exact amount, currency, scope, period and history; browser-closed scheduling updates it | Real HTTP/generated client/built browser, then installed `0731 → 0733` activation and existing-provider continuity |
| 3. Complete all required provider coverage | Remaining T006/T008/T009 and T007 integration | Anthropic, OpenAI and Ollama use the same screens; supported usage fields/categories have explicit coverage | One successful real report per provider; every active configured resource accounted for; request-only data is not money |
| 4. Finish the analysis already in scope | T013 | Supported one-dimension breakdowns, daily chart and exact table, forecast or a specific unavailable reason | Same selected financial facts through policy, HTTP and DOM; numeric forecast live proof only when genuine inputs qualify |
| 5. Reconcile, release and close | T015 → T016 | Working installed version and matching public GitHub code, run instructions and demonstration | Fixed exit catalog, bounded independent review, installed/remote revision comparison and separate owner acceptance |

First-provider preference is an accessible Anthropic/OpenAI monetary lane,
whose shared billing commit fence is already present. Ollama can be first only
after its existing cloud-graph fence and shared balance/usage rate coordination
are connected; the source candidate alone is not interchangeable. This does not
justify idling if that Ollama path is the only accessible source. Missing credentials affect their live lane only. Do not
create accounts, enter keys, generate spend or seed reports on the owner's behalf.

## 3. Concrete integration handoffs before the first dashboard

Root owns shared contracts and composition. Module agents work only against
synchronized ports in nonoverlapping paths. No private cross-module SQL/imports.

| Handoff | Smallest implementation and owner | Test/acceptance allocation |
|---|---|---|
| Owner action to durable work | T007 M04/root: reuse request/schedule/run storage and capture account/resource, binding/scope generations, source/category/grouping, requested UTC interval and idempotency identity. Add only missing typed fields/ports. Select/claim through M04, not a second queue or loose job files | M7-COL-001..004 / M7-A01,A09: duplicate clicks, process restart and UTC-midnight crossing keep one intended report; GET never collects |
| Work to supervised worker | T007 root: finish the fixed billing CLI and normal scheduler invocation; use the existing supervisor pattern, start-authority check, one bounded report and closed exit states | Real owned transient process/cleanup; no grant means no provider I/O; recovery-only means no new collection |
| Worker to admitted source | T006/T008/T009 + T007: extend the one-request scheduling policy only for bounded billing reports; issue actual purpose-specific runtime authorization and map the real provider result to M03/M05 contracts | Admitted provider/version, request counters and field allowlist; existing quota and Ollama balance admission unchanged |
| Source to atomic report | T005/T007: use committed billing fences, actual report receipt and public commit-status recovery. Deadline/lease/binding changes reject obsolete writes. Distinguish a live committing owner from an expired claimed owner | M7-CAP-DB and M7-COL cases: genuine commit, idempotent retry, reopen, interrupted reconciliation; real empty coverage when available |
| Existing Ollama connection to usage | T002/T009/root: reuse the cloud graph and balance resource; resolve self/team and compatible scope explicitly. Credential rotation is not a new financial scope epoch | M7-A05: no duplicate balance pool, no default-profile access, no inferred team authority, no separate manual account setup |
| Stored reports to query | T005/T010 M05: choose newest complete compatible report across all matching revisions, separately retain latest persisted attempt; bounded context/byte overflow is unavailable, never a truncated total | Pure correction/context policy; real empty SQLite now, populated selection using genuine reports. Older complete report outside a first history page remains selectable |
| Query plus collection state to HTTP | T010 P01/application composition: combine M02 metadata, M05 money/coverage and M04 latest run through ports. A failed run with no report must still be visible beside the previous value | M7-HTTP-001..006 / M7-A07: real IAM, exact values/IDs, no cross-account results, stable cursor/as-of and safe errors |
| HTTP to useful screen | T011/T012 P02: generated client, shared filters, API table/detail/history, separate state/freshness, no browser money calculations | M7-UI-001..006 / M7-A07,A08: direct link, reload/back, sign-in return, selected range, keyboard/zoom/narrow view |

The source's 20-request, 10-second/request and 120-second/report limits are
ceilings, not a promise that 20 slow pages finish. Admission, provider paging,
normalization and persistence must share a bounded lifetime: do not restart a
120-second allowance at each step or grant after lease expiry. Reserve time for
commit; if collection cannot finish, retain the previous complete report and
reconcile actual state. The supervisor's outer cutoff alone does not prove safe
recovery. Measure this in the first live run instead of introducing page jobs.

### Concrete first-slice contract decisions

These are implementation handoffs within T004/T007/T010, not new requirements
or approvals. Publish their additive types before delegating consumers.

1. **Use the same admitted source identity end to end (T007/root).** The local
   run factory, action producer and worker now use
   `anthropic_cost_manifest_fingerprint()` as the 64-hex audit fingerprint
   required by M02/M04. Preserve this correction; leave M03's distinct 32-hex
   catalog identifier alone. Empty-boundary tests do not prove live dispatch.
   Resolve the real registered service target through M02; a billing resource
   ID is not a cloud service target ID. Verify a genuine queued run is claimed,
   executed and finalized, rather than treating empty-queue success as proof.
2. **One application query assembles the first account read (T010/root/M05).**
   Input is authorized account ID, requested UTC period and pinned `as_of`.
   Resolve resource/scope generations through M02; the caller cannot select an
   arbitrary epoch. Output includes query availability, resource and canonical
   pool identity/evidence, current complete report, latest persisted attempt,
   latest M04 collection result, and **already-calculated reported spend** with
   exact money, basis, interval and input report IDs. Missing M04 status is
   unknown collection status, not a green report. P01 maps this published view;
   React formats it. Neither derives a total from returned report JSON.
3. **Choose the total report before aggregation (T004/T010).** The current query
   returns multiple contexts, while the existing aggregation policy accepts
   one input per resource. Select the admitted ungrouped cost report for each
   compatible currency/basis/category group. Usage-only reports and breakdowns
   are alternative views, never additional spend. Evaluate separate compatible
   groups independently; do not feed every context into the one-resource-input
   policy or silently choose its first entry. Incompatible/ambiguous contexts
   yield a named exclusion. Daily history uses the selected report's cost
   buckets; revision history and the future chart cannot recompute another total.

4. **Stable detail identity, pinned history (T005/T010/T011).** For the new
   financial routes, `budget_id` is the existing canonical billing resource ID;
   it does not identify a polling run, credential or new storage entity. A
   resource may expose several compatible financial contexts. Current output
   supplies each selected immutable `report_id`; daily history requires that
   selection and validates account/resource/scope/period authorization. Its
   cursor binds the report and query, not just an offset. A later collection
   cannot change the report halfway through pagination. If retained history is
   gone, return an explicit expired-selection response and offer Refresh;
   never silently substitute a newer report. This is additive routing: old
   reserved budget DTOs and existing quota/resource identifiers keep their meaning.

5. **Separate action progress from financial snapshot (T007/T010/T011).**
   A Check started after the page's `as_of` cannot appear in that old snapshot.
   Follow the returned run through a read-only, account/resource-authorized M04
   status query. On completion, advance only the read instant and atomically
   reload report/table for the same selected UTC interval. Reset its history
   cursor; do not reset the interval, repeat the provider call or relabel seven
   days as thirty. Scope changes invalidate old responses. No new job engine.

6. **Finish runtime wiring before broadening backend work (T003/T007/root).**
   The initial import-boundary command reported 76 violations in the
   candidate: classify stale contract/ownership declarations separately from
   forbidden imports. Fix the latter and update approved producer/consumer
   declarations precisely; do not turn off the checker or approve historical
   Draft module plans wholesale. Regenerate the API/client from their source.
   Then wire the first Check button and actual monitoring/scheduler mutations.
   These are implementation tasks, not missing owner approvals or a new gate.

   The read-only boundary review isolated three actual violations:
   `billing_collection.py` reaches M02's private access policy;
   `billing_run.py` reaches M05's private report codec; `billing_worker.py`
   reaches a private Ollama worker-start helper. T007/root replaces these with
   the owning public application surface and a shared composition start-authority
   helper. The other 73 findings were classified as missing/stale exact
   declarations by the review; that classification is not a passing checkout.
   T003/root repairs those declarations and reruns the unchanged boundary rules.

   **Current checkpoint:** those corrections and the Check/status UI are now
   implemented locally. The actual boundary command reports zero violations;
   `AUTO-QUALITY` passes types, formatting, generated API compatibility and build.
   Real no-report HTTP/browser checks pass. A successful credential-backed run
   is still unverified, and monitoring/scheduling remains unfinished. See the
   [integration evidence](../../evidence/m7-billing-integration-2026-11-11.md).

The smallest next demonstration is therefore **one owner-created account →
Check connection → durable report → application-calculated spend → real HTTP
→ detail/Overview**. Extend the existing routes/components. Do not finish all
report categories, forecasts or a generic aggregation layer before wiring that
path. This does not remove the remaining T010 endpoints from final ticket closure.

### Next implementation batch

| Order | Deliverable | Existing tickets | Evidence that ends the increment |
|---|---|---|---|
| 1 | Integrable current candidate and working Check control/status | T003/T007/T011 | Boundary/generated checks green; real button reaches a durable run and displays its terminal result; no success inferred from 202 |
| 2 | First monetary report and normal monitoring | T005/T007 plus first provider | Real read commits/reopens; enable/disable works through UI; next scheduled read completes with browser closed; failures retain prior facts |
| 3 | Same report on Overview/detail, then installed | T010/T011/T012/T014 | Exact same report context and amount across source/API/DOM; filters/back/reload work; compatible install preserves current collectors |

Continue independent required work if the live read awaits owner setup; name
only that live dependency. Do not start another round of generic infrastructure
or a plan-version cycle while these concrete integration steps are unfinished.
The remaining provider coverage and analysis are the existing S2/S3 work, not
new scope discovered after this first delivery.

## 4. Fix the UI decisions before polishing

The first viewport answers **whose money, which period, how much, how current**.
Keep the existing header/navigation/footer and subscription table. Add the API
section with shared organization/provider filters and All / Subscriptions / API
billing selection. Account label links to its selected billing resource/period.
No generic analytics dashboard or large connection-status card.

The detailed [screen plan](m7-ui-and-user-journeys.md) includes layouts and state
copy. These are the integration checks most likely to be missed:

- Display dashboard group separately from provider billing scope; neither a
  matching email nor administrative access proves per-person/agent attribution.
- Show latest collection failure beside last complete amount and its original
  time. A persisted report cannot represent a denied call that saved no report.
- A requested 30-day report must never display a 7-day amount under its heading.
  The current Anthropic candidate accepts seven days only; its 30-day extension
  belongs to T006. Show interval-specific coverage until that extension works.
- Unknown currency cannot inherit the last report's currency or freshness.
  Scope/key changes and late responses cannot relabel another resource's value.
- Retain exact history when refresh fails. Daily spend history and report
  revision history are different: the daily chart must not count repeated polls.
- Pending/disabled accounts remain discoverable; setup actions exist before an
  owner is asked to use them. From LAN, show which host runs the local command.
- Long names, later account/organization pages, no matches, expired sessions,
  200% zoom and 768px width have usable text/actions, not hidden requirements.

## 5. Calculations and coverage: agreed small rules

The [calculation document](m7-calculation-and-data-rules.md) remains authoritative;
M7-MATH-01..16 remain the test families. No new accounting feature is added.

| Question | Rule and owning tickets |
|---|---|
| What did we spend? | Exact disjoint cost facts from one complete compatible report; corrections replace prior coverage, signed adjustments count once. T004/T005 |
| What remains? | Latest authoritative balance OR separately labelled compatible limit headroom. Soft budget is not cash; no limit means no percentage. T004/T011 |
| What does red mean? | Known remaining ≤20% with a valid denominator, or reported depletion/exceeded hard limit. High spend by itself is not low capacity. T012 |
| What can be totalled? | Same currency, interval and cost basis; known shared pools once. Expose excluded/old scopes; no eligible input means unavailable, not zero. T004/T010/T012 |
| What does the chart show? | Daily buckets from the selected current report, signed values and gaps. Report revisions remain audit history, not extra daily spend. T005/T013 |
| Can we estimate exhaustion? | Bounded observed-rate formula plus compatible remaining funds and adequate complete history. Missing input yields a reason, never guessed cash/price/reset. T013 |
| How do we handle source delay? | Separate checked time, covered period and source watermark; successful collection does not advance missing/unchanged provider time. T007/T010/T011 |

Pure tests cover edge cases without fabricated I/O. Real provider → SQLite →
HTTP → DOM evidence uses the same genuine report and exact input IDs. Provider
UI rounding is compared at its documented precision, not an arbitrary tolerance.

## 6. Bound provider scope now

Use the [recorded discovery](../../evidence/m7-provider-discovery-2026-11-11.md)
as the finite category inventory, not an instruction to integrate future APIs.
The frozen inventory is Anthropic analytics cost and usage; OpenAI costs plus
completions, embeddings, moderations, images, audio speeches/transcriptions,
code-interpreter sessions, vector stores, file-search calls, web-search calls
and decisions; Ollama cloud usage plus the existing balance source. These are
the categories in the recorded discovery, not freshly verified live capability.
No additional categories enter M7 just because a later documentation page adds them.
Before each category is enabled, record its admitted endpoint/role, 7/30-day
support, unit/basis, safe dimensions, completeness, watermark and comparison
method in that provider's evidence. This is a small table in existing evidence,
not a new configuration engine or approval artifact.

| Provider | First useful read | Remaining within existing tickets |
|---|---|---|
| Anthropic | Seven-day cost candidate | T006: 30-day support, documented usage categories and supported single dimensions; beta remains explicit |
| OpenAI | Organization cost candidate | T008: the usage categories enumerated in discovery, each with truthful availability/dimensions; completions is not all usage |
| Ollama | Usage candidate plus existing balance | T009: actual self/team authority, model/remainder data and compatible balance linkage; request-only legacy data stays requests |

Source-supported but unimplemented is **unfinished**, not Unsupported. A denied
credential is an access problem, not an unsupported provider. A naturally absent
optional field is an unavailable field, not permission to invent data. Newly
introduced provider categories after this inventory go to a later change.
Full M7 still requires all three lanes and the originally approved supported
breakdowns/history/conditional forecast; simplification does not silently drop them.

## 7. Verification and operations without another M5 loop

T003 connects checks as the corresponding feature lands. Existing runnable
partial lanes are `pure`, `mutation`, `registry_metadata`, `persistence_schema`,
and the explicit `deploy --check setup_activation` selection. Remaining full
technical/live/browser/deploy checks are not assumed implemented because their
names exist. Future scoped selectors are labelled Planned until executable.
Use `python3 -m tools.automation.implementations.auto_m7 --lane <lane>` only for
an admitted existing lane; the catalog supplies the exact invocation.

T014 rehearsed the additive financial migration/recovery on isolated real data;
that is not an installed `0733` pass. Reuse the selected-revision controller,
verified secret-excluding backup and journal-based recovery. Before service
transition verify the clean build, schema and recovery target; afterward verify
HTTP, authenticated Overview/detail, installed revision and existing collectors.
An HTTP 200 alone does not certify correct account values. No provider-profile
or running-agent mutation. Do not blindly restore an old DB after new writes.

T015 reconciles the same source scope/period/basis to API and DOM. Reuse earlier
valid observations where applicable; only changed behavior invalidates its
associated evidence. Required missing coverage stays visible. Naturally absent
401/403/429/depletion or numerical-forecast cases remain individually Not Run;
no spend, revoked keys or repeated owner confirmations to manufacture them.

T016 runs the fixed exit catalog and one bounded independent review, fixes
violations of existing requirements, verifies installed/public revisions and
requests acceptance of the actual demonstration. Publication and owner
acceptance are separate from a technical exit; the gate does not require its
own future publication. The GitLab mirror cannot block GitHub delivery.

## 8. Work size, checkpoint reporting and owner actions

The previous 7–12 focused-day estimate was an initial estimate, not measured
remaining work. Do not reset it after each subtask or promise a completion date
from local test counts. Remaining uncertainty is concentrated in the first real
worker/report/UI integration and source category coverage, not another planning
phase. At the first installed monetary journey, update remaining effort for
provider completion, analysis and release from observed throughput and actual
access; expose any changed estimate with its concrete cause.

During execution, report the current ticket, newly visible result, actual failing
boundary, next demonstration and owner input only if needed. A session ending
with backend changes alone reports that limitation. If two sessions produce no
new visible increment, root inspects the integration dependency and reduces
parallel infrastructure work; it does not add another review/approval loop.

For each live prerequisite, distinguish **not yet checked**, **available**, and
**observed unavailable**. Do not infer absent billing access from a missing
account label. Root prepares the actual page/command first, requests any necessary
owner action once with provider, URL/host and expected result, and continues
independent work. A real access denial blocks that provider comparison; it does
not block financial policy, empty-stack HTTP or another provider lane. If all
monetary lanes lack usable access, disclose that precise first-demo dependency
instead of presenting request counts or an empty dashboard as the monetary result.

Owner participation: normal account/group setup and local key entry through the
working flow, official sign-in where required, final demonstration/acceptance.
No owner task is needed to finish this planning review. Names/labels are not a
reason to stop engineering. No manual run IDs, repeated attestations or agent
configuration of the owner's accounts.

Deferred: local Ollama, new alert policies, user-set budgets, price-list spend
estimation, invoices/tax/FX, multi-dimension report builders, advanced forecasts,
page-job engines, remote secret entry and general deployment frameworks.
Known unknowns resolve inside the named tickets; only a genuine requirement or
authority conflict needs a new decision. Do not promise zero future surprises.
