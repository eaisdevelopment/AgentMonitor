# M7 compact account summaries and bounded daily history

Status: bounded history increment installed and published at `ff285c4`;
not full M7 completion.
Requirements FR-BUDGET-002/004/005, FR-HIST-001/002, AC-HIST-001,
AC-UI-002/005/006, AC-TEST-001/003/006; T010/T011, M7-A06/A07/A08.
M05 owns exact history selection, P01 transport, P02 rendering; root owns
contracts, composition, generated artifacts and deployment.

## Behavior and compatibility

Additive CTR-CAP-006 2.8.0 query/row/result/port types bind account, resource,
immutable report, seven/thirty-day UTC interval, cutoff and page size. M05
reauthorizes the selected retained report on every page. Facts sort by start,
end, kind and bucket key, preserve exact signed costs and native usage units,
and never fill gaps or convert counts to money. Missing reports return no
selection; a newer report is not substituted.

`GET /accounts/{account_id}/budgets` returns the same financial metadata,
spend and funds with report metadata/counts instead of entire bucket arrays.
`GET /budgets/{budget_id}/history` returns at most 200 facts (default 50),
compact metadata and the selected report's total. Old full-report endpoints
remain compatible. Root publishes the two operations through generator2.0.11,
with an exact 93-operation allowlist and the existing auth/error policies.

The account UI consumes compact summaries and requests history separately.
Loaded pages remain visible on failed continuation, with an explicit retry;
actual selection changes reset history. Pinned report headings and spend come
from that report, while current funds remain separately labelled. Cursor
identity includes the immutable body, selection and limit; the existing signed
HTTP envelope binds caller/filters and owns expiry. No new cursor system.

The existing stored-report bounds remain 10,000 facts/16 MiB. The application
still reads one bounded report internally; this change bounds HTTP/browser
transfer and does not claim SQL-level bucket pagination or infinite history.
No migration, dependency, license, credential custody, provider profile or
owner account/monitoring configuration changes.

## Red evidence

- Five contract tests failed because history query/row types were absent;
  then passed after publishing the additive types.
- Twenty-one pure projection tests and two genuine private-copy application
  tests failed for the missing history implementation, then passed.
- Two actual IAM/HTTP tests returned404 instead of401 before the routes existed.
- The new pure presentation suite failed for the missing pagination helper.
- The authenticated installed probe failed at `compact_budget_summary_missing`
  against54eab61 at01:27:29UTC, after Overview and filters passed on two real
  financial rows; zero unsafe requests.
- Populated actual HTTP reached500 because the initial internal history key
  exceeded the existing cursor's safe64 envelope. The fix must fit the current
  codec; expanding the shared pagination mechanism is unnecessary.

The cursor fix uses a complete SHA-224 context checksum inside the existing
authenticated HTTP envelope: `v1_` +56 hex characters + underscore + offset
1..9999 fits64. A pure maximum10,000-fact case proves the last continuation and
terminal page. A proposed base64 encoding was rejected by the existing domain
import checker; that checker was not broadened. The only boundary allowlist
addition is the published `BudgetHistoryPortV1` protocol for P01 dependencies.

The genuine retained reports are Ollama usage counts. Their exact paging and
missing-selection checks do not prove monetary history, source collection,
retention policy or full M7 acceptance. The disposable-copy deletion test proves
only that removal of the selected report cannot silently select another one.
Pure presentation failure retention is not a manufactured browser outage test.

## Remaining integration

Generated-client/static checks, scoped canonical tests, actual HTTP
continuations and installed browser verification passed as recorded below.
T010/T011 still include remaining financial
states/contexts, older-window navigation, monetary evidence and accessibility;
this increment does not close those whole tickets or the M7 goal.

## Candidate verification

At01:37UTC on12 November, AUTO-QUALITY passed: Ruff769 files, strict mypy708,
zero import-boundary violations, compatible93-operation generated API/client,
TypeScript and the production build. Earlier attempts caught a long docstring,
two typed cursor-filter annotations, a test-helper annotation, generated drift
after source edits, and the cursor encoding's disallowed import/formatting.
Those findings were fixed before the passing run; no checks were waived.

Canonical technical `budget_http_guards` passed15 actual IAM/HTTP tests,
including the new authenticated routes and read-scope denials. This remains
the no-report guard suite. Separate genuine snapshot tests verify populated
metadata/count projection, smaller summaries, exact paging and caller/context
binding. Actual service restart invalidates its old cursor; natural900-second
expiry was not exercised and is not claimed by that restart check.

Final canonical pure lane passed626 Python tests and eight presentation suites.
The three genuine private-copy SQLite/application/HTTP tests passed together
in14.25s against the final cursor implementation, with no skips. Source-provider
requests and owner database writes were not part of those checks.

## First installed check and correction

Code2081169 passed the same-schema updater and the dashboard remained active
with HTTP200. At01:39:36UTC the authenticated installed probe reached the new
history view but failed `ui_requested_unbounded_report`: cloud pool discovery
in `FinancialPoolPanel.tsx` still requested the old full account report solely
to extract resource IDs. The correction switches that read to the compact
summary; its resource metadata is unchanged. This is an observed browser Red,
not a claim that the first installed candidate passed the complete probe.

## Installed and published result

The corrected candidate passed AUTO-QUALITY again at01:40:35UTC. Two update
attempts returned `phase=stop reason=unit_has_children_or_not_stopped`. Read-only
inspection found the prior2081169 service active/HTTP200 and no incomplete
journal. Observed child PIDs naturally exited; the next canonical update
succeeded. No child was killed, no restart policy relaxed and no owner
monitoring setting changed. The installed schema remains `v1_0734`.

At01:44:45UTC the authenticated installed Overview probe passed all seven
checks at `ff285c46a05897f0d3a9a3e7634d85d11cf004db`: two real financial rows,
exact API/DOM history, direct limit-one server continuations, compact-only UI
reads, filters, pinned report navigation/Back/reload, responsive layout and pool
controls. Zero unsafe requests. Actual history had fewer than50 facts; the
browser did not exercise a naturally populated second default-size page.
Pure append/failure tests and real limit-one HTTP paging cover their respective
boundaries without claiming that unobserved UI case passed.

At01:45:11UTC the installed setup/shell probe passed all six checks at the same
revision,38 requests and zero unsafe requests: authentication, revision,
Overview, setup form and header/footer continuity.

Pinned Gitleaks8.30.0 scanned98cdd87..ff285c4. Raw exit1 had one generic-key
finding on the generated `openapiArtifactSha256` constant. Root compared the
exact line with the committed OpenAPI file's actual SHA-256; it is the artifact
checksum, not a credential. No finding was suppressed or misreported as exit0.
GitHub main fast-forwarded and `git ls-remote` verified the exact ff285c4
revision. Later documentation commits do not change this installed code.

Files changed span the additive query contract, M05 projection/application,
P01 schemas/routes/port bundle, root composition/generator/boundary allowlist,
P02 account/history/pool views and shared client, pure/real HTTP/private-copy
tests, canonical test inventory, installed browser probe and these planning
records. There is no new security/privacy/license/migration effect.
Next: captured collection intervals, scope lifecycle and older stored-window
navigation; genuine monetary comparisons proceed when owner billing setup exists.
