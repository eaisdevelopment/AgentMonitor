# M7 delivery worksheet: from setup to a useful budget dashboard

Status: execution clarification within approved focused plan 1.1.0, following
the owner's request for deeper planning. No new milestone, approval cycle,
dependency, acceptance requirement or financial product is introduced.
Primary owner: root integration; financial owner: M05.

The [ticket catalog](m7-ticket-catalog-v1.json) remains the task tracker.
This worksheet explains implementation order and known gaps; it is not a
second completion tracker. Sixteen tickets, five stories and M7-A01..A10 remain
the fixed scope. The [UI plan](m7-ui-and-user-journeys.md) and
[calculation rules](m7-calculation-and-data-rules.md) own their detailed behavior.

## 1. Starting position and the finish line

At committed revision `032a43f`, metadata enrollment, safe credential status,
local entry foundations and pure exact-money/report policies exist. Additional
uncommitted setup UI, credential reader and Anthropic source work is partial.
There is no verified M7 source → stored report → installed dashboard journey.
Provider authentication success, monetary persistence, budget screens and the
full M7 exit must not be inferred from those partial tests.

M7 finishes when all three required provider lanes have their admitted real
reports, the actual dashboard shows correct values/history/supported breakdowns
and conditional forecasts, continuity/recovery checks pass, and the delivered
revision is published and demonstrated for owner acceptance. Unsupported fields
have explicit reasons. Missing required provider access is an open live item,
not a pass. Local Ollama and the other listed deferrals remain outside M7.

## 2. Five visible deliveries using the existing tickets

| Order | Tickets/increment | Demonstrable result | Evidence before calling this increment delivered |
|---|---|---|---|
| 1. Working setup | T002; narrow T003 checks; early T014 activation | Owner creates/attaches a billing account, sees the correct provider/group, runs its actual server-local command, and sees stored-key status | Real API/browser, hidden-input/file safety, installed command selection, migration/recovery and existing dashboard continuity; stored is not verified access |
| 2. First real money on screen | T004; first provider part of T006/T008/T009; T005/T007; T010–T012; final T014 activation | Owner checks connection and enables monitoring; Overview and detail show the same genuine spend, period, scope and history | Real source → atomic SQLite commit/reopen → HTTP → built and installed browser, plus scheduled collection with browser closed |
| 3. All required providers | Remaining parts of T006/T008/T009 | Anthropic, OpenAI and Ollama use those same screens with honest field/category availability | One admitted successful report per provider, all active configured resources accounted for; no fixed account-count ceremony |
| 4. Complete analysis views | T013 | Supported single-dimension breakdowns, exact history table/chart and an estimate or specific unavailable reason | Pure math plus actual history/API/browser reconciliation; numeric forecast live check only when genuine inputs qualify |
| 5. Release and closure | T015/T016 | Correct deployed dashboard, current public code, concise limitations and owner demonstration | Fixed technical/live/browser/recovery matrix, remote and installed revisions verified; owner acceptance recorded separately |

`depends_on` describes **ticket closure**, not a ban on independent work.
The first provider increment needs one valid cost report; its entire usage and
breakdown catalog need not finish before storage/UI development starts. T005's
final closure still requires the relevant provider evidence. The same rule lets
T014 prepare and activate setup before its full dashboard dependencies close.
Do not close a ticket merely because an intermediate demonstration passed.

T013 pure/chart work can proceed after the first genuine history exists while
another provider awaits access. Its final all-provider coverage remains required.
At most one end-to-end first-provider path is the integration priority; parallel
agents work only on its independent owned components or ready provider lanes.

## 3. Known contract work before first-report integration

These are observed implementation gaps, not new owner prerequisites. Root owns
shared contract edits/version registration, then hands stable ports to modules.
Preserve existing quota consumers and generated-wire compatibility.

| Existing constraint | Smallest planned correction | Owner/ticket and proof |
|---|---|---|
| `ProviderSourceV1` equates experimental with private/browser source | Permit an official documented beta source to remain explicitly experimental; retain private-source restrictions | Root/M03, T006; pure manifest rejection → accepted documented-beta manifest, old private rules still tested |
| `CollectionRunAdmissionV2` requires a profile for its cloud target | Add a billing target carrying actual account/resource/binding/scope generations; never create a fictitious CLI profile | Root/M04, T007; pure target validation and real registry/run integration |
| `ScheduledSourceAdmissionPolicyV1` admits one request only | Add bounded report admission using the existing one-run executor and published request/page/deadline limits | Root/M03/M04, T007; actual admitted source and run counters/deadlines |
| Successful commit/run contracts require observations/projections/events | Add the already-planned budget receipt with a real report/coverage reference and zero-or-more facts | Root/M05/M04, T004/T005/T007; genuine empty result when available, pure policy always; no invented IDs |
| Candidate setup command resolves the older installed service | T014 activates the tested setup increment first; candidate-only checks remain partial | Root/operations, T002/T014; actual selected executable/data root/host and continuity |
| Credential presence is not access or scope proof | Recheck actual active binding and scope generations when issuing the worker grant and before commit | M02/root/M04, T002/T007; rotation/disconnect/archive cannot commit an obsolete report |
| HTTP source has a process-local alarm | Run it only in the existing supervised worker pattern with an outer hard deadline; never in the API process | Root/A01, T006/T007; real timeout/cleanup and dashboard responsiveness |

Current A01 review also identified an original-deadline validation defect:
validate finite input before clamping it. Keep that specific correction in T006;
do not widen it into a new timeout framework. Proposed contract additions remain
unpublished until their types, producers/consumers and registry are synchronized.

## 4. UI decisions that prevent an unusable first release

1. **Find the resource.** Accounts supports API-only and mixed accounts. Overview
   uses the same organization/provider filters across both sections. Add a small
   resource-type choice All / Subscriptions / API billing, with counts, to avoid
   burying API billing below a long quota list. Default All; preserve URL state.
   No new top-level menu, dashboard or design system. T011/T012.
2. **Understand ownership.** Show owner account label, dashboard group and
   provider billing scope separately. Whole-organization spend is not the
   individual user's or terminal's spend. Do not invent agent attribution.
   Shared pools appear once in totals, with their other access paths discoverable.
3. **Understand the figures.** Main detail shows spend and period first, then
   supported balance/limits and freshness. Unavailable fields use concise text,
   not a grid of empty cards. Connection controls collapse after setup. T011.
4. **Know the action.** Stored credential, access verified, monitoring enabled
   and recent data are four distinct states. Check connection and Collect now
   are real bounded jobs; Refresh readings only refreshes stored views. Show
   retry time/error remedy without throwing away the last known report. T007.
5. **Navigate reliably.** Detail opens at the selected pool/period; Back/reload
   preserves filters. A filter/range change cancels the old query generation,
   resets its cursor and ignores late responses. Expired sign-in returns to the
   same safe URL and never replays a write automatically. T010–T012.
6. **Operate from another computer.** Setup explains which server to use and
   provides selectable command text if clipboard permission is absent. Test
   localhost and the approved LAN path. Do not add browser secret entry. T002/T014.
7. **Remain readable.** Keyboard, 200% zoom and existing desktop/tablet widths;
   exact text/table alternatives to charts; no hidden required controls. The
   promotion/support header, footer, quotas and existing alerts stay usable.

## 5. Financial decisions and tests to settle before UI polish

The existing M7-MATH-01..16 remain the test families, not new tickets.

| Risk | Defined result | Owning tickets |
|---|---|---|
| Spend confused with funds or soft budget | Separate fields; no inferred cash, denominator or service-stop guarantee | T004/T011 |
| Large/very small/negative amounts | Exact signed decimal storage and calculations; zero canonicalization; explicit sub-cent display; overflow rejected | T004/T005 |
| Repeated polls and provider corrections | Complete-report replacement, retained earlier revisions; no addition of repeated reports or phantom removed buckets | T004/T005 |
| Empty, missing and late data conflated | Genuine complete no-usage coverage differs from denied/missing/partial source; collector success differs from source update | T005/T007/T011 |
| Shared keys or parent/project overlap | Deduplicate established pools; exclude unresolved overlap with reason/count, preserve visible rows | T002/T004/T010/T012 |
| Cross-currency or inconsistent-period totals | Separate compatible groups; subtotal across all selected inventory, never only the loaded page | T004/T010/T012 |
| Partial current day becomes a full-period total | Use complete UTC buckets for selected 7/30-day ranges; today shown separately if available | T006/T008/T009/T010 |
| Misleading chart | Same actual report inputs as exact table; missing intervals stay gaps; cost adjustments remain signed | T013 |
| Unjustified forecast | Query-time observed rate only with adequate compatible history; remaining-funds requirement, reset/horizon and unavailable reasons as specified | T013 |
| Scope/group/key changes during collection | New financial scope epoch; group movement does not rewrite provider history; key rotation invalidates access proof, not history | T002/T005/T007 |

Initial collection is one source/report/range/grouping per run. Reuse leases,
idempotency and recovery; no parent/child jobs, checkpoint-per-page storage,
generic analytics engine, token-price estimates or persistent forecast state.
No new dependency is planned. Breakdown queries use one supported dimension at
a time; they do not require a combinatorial report builder.

## 6. Provider scope and evidence boundaries

| Provider | Initial useful report | Full M7 extension | Do not promise |
|---|---|---|---|
| Anthropic Console | Official beta cost report, exact cents-to-USD mapping, explicit discount/credit basis | Admitted usage and supported single-dimension breakdowns | Subscription sign-in as billing access; a prepaid balance/limit absent from admitted data |
| OpenAI Platform | Official organization cost report with administrative access | Explicit category coverage and supported dimensions; completions alone is not all usage | ChatGPT/Codex allowance as API funds, or spend inferred from token pricing |
| Ollama Cloud | Official usage using existing owner connection and balance pool | Actual self/team capability, model breakdown, available monetary/token/request fields | Duplicated credits, local-model monitoring, unsupported key/member attribution |

Sources rechecked for this review: [Anthropic analytics](https://platform.claude.com/docs/en/manage-claude/usage-cost-analytics-api),
[OpenAI usage/cost reference](https://developers.openai.com/api/reference/resources/admin/subresources/organization/subresources/usage),
[Ollama usage](https://docs.ollama.com/api/cloud-usage).
Documentation is capability evidence only; credential access and field behavior
remain live checks. Native Ollama 7d/30d boundaries are corrected in the math
plan; no speculative wider-range/backfill machinery is planned.

For each admitted category record endpoint, role, unit/basis, dimensions,
pagination bounds, source watermark/lag and comparison method in its adapter
evidence before enabling it. Missing natural 401/429/revisions/exhaustion stays
individually Not Run/Blocked; do not manufacture spend or revoke working keys.
Official scope changes require an explicit capability finding, not silently
replacing API data with scraping or expanding the accepted product scope.

## 7. Verification, deployment and owner participation

Use existing canonical planning, technical, live, browser, deployment and exit
commands. Add only the missing scoped selectors in T003 as their behavior is
implemented; the ticket catalog labels unavailable commands Planned. No new
approval or gate platform. Required financial cases have pure Red/Green;
provider/database/HTTP/browser claims require those real boundaries.

The same real normalized report can be checked through commit, query and DOM
in one run; do not ask the owner to reconfirm it after a documentation change.
Do not persist raw responses or replay them. A changed provider mapping,
credential generation or scope needs the affected live lane reverified.

Before each activation: clean selected candidate, compatible migrations,
verified secret-excluding backup/recovery, then health and authenticated
Overview/detail/continuity. Failed activation uses tested recovery, never a
blind old-database restore after writes. The first setup activation is explicitly
partial; final closure verifies the complete installed and public revision.

Owner actions are limited to normal account/group configuration, local key entry
and official login where needed, then the final demonstrated acceptance. Ask
only after the actual workflow exists, with exact URL/host, purpose and expected
result. No bulk opaque IDs, repeated account attestations or manual test orchestration.
No owner input is needed for this planning refactor. Missing access pauses only
the dependent provider proof; continue other authorized engineering work.

## 8. Reporting and bounded scope

Report: latest visible delivery; exact ticket and evidence; actual remaining
first-delivery work; observed blocker and its affected lane, if any. State local,
committed, pushed and installed separately. Number of tests or files is not a
percentage of product completion. Status corrections must not erase past evidence.

The prior 7–12 focused-engineering-day range is an uncalibrated estimate, not a
deadline. Re-estimate remaining effort after the first installed real-money
journey and measured source integration, including any live-access wait
separately. If a session produces no visible increment, identify the actual
critical-path work and its next demonstrable result; do not fill the next session
with unrelated infrastructure.

One bounded final review checks the fixed requirements. Fix demonstrated
violations; log enhancements in the existing deferred list. No guarantee of
zero surprises is credible, but surprises must map to a stated requirement,
evidence and a smallest correction rather than creating another milestone inside M7.
