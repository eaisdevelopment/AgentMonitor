# M6 native USD account view candidate

- Evidence ID: `M6-NATIVE-USD-ACCOUNT-UI-2026-11-03`
- Owner: P02; approved [M6 cloud plan](../plans/integration/m6-ollama-cloud-implementation-change.md)
- Requirements: FR-QUOTA-001/002/004/006; acceptance M6-A04/A05/A08, AC-UI-005
- Candidate base: `1e6eb7d`
- Recorder/date: AgentMonitor engineering, 3 November 2026
- Status: implementation candidate; actual deployed-browser Green pending

## Behavior

Account allowance cards display exact native USD balances and a reported
allowance when present. Decimal coefficients are formatted without conversion
to floating-point numbers. Zero purchased credit remains a real `$0.00`
reading; it is not unknown and receives no fabricated percentage or limit.
Existing reported/derived percentage meters remain tied to the API metric.

The account summary separates reading availability from identity verification.
An owner-provided name is explicitly labelled as such even when a genuine
balance is available. Existing provider-verified identity/run checks remain
unchanged. A successful balance read is not represented as identity proof.

History defaults to the native remaining amount when current USD readings
exist. An explicit metric selector keeps ratio history available, including
when money and percentage windows coexist or semantics changed historically.
Each query and continuation retains its selected metric. If returned numeric
points have different units, the UI presents their exact table and an
explanation instead of a combined chart. No balances are summed. Native USD
history rows show readable decimal USD beside the existing exact technical
representation, preserving observation and run lineage.

## Contracts and compatibility

Only P02 presentation changed. It continues to consume the generated
`AccountCapacityViewV2`, `QuotaWindowPageV2`, `QuotaWindowViewV2`,
`CapacityHistoryPageV2`, `CapacityHistoryPointV2`, `ExactMetricFieldWireV1` and
`ProviderAccountIdentityViewV1` types through the shared API client. Existing
`/api/v1/accounts/{account_id}/capacity/v2`, quota V2 and capacity history V2
GET operations supply the data; the history API already permits `remaining`
and `remaining_ratio`. Generator 2.0.8 and generated OpenAPI/client artifacts
are unchanged. No backend, API, schema, migration or configuration change.

## Red evidence

The actual signed-in owner account page was inspected through its existing
Chrome CDP connection without navigating or changing the owner tab. The
browser check read only the real application API and DOM. Two actual available
USD windows existed. Before production edits the check exited 1:

```text
native_usd_windows: 2
native_usd_missing_from_allowance_card
unknown_left_despite_native_usd
native_usd_allowance_missing
real_balance_shown_as_waiting
owner_identity_conflated_with_quota
owner_asserted_identity_not_explicit
native_usd_history_unit_missing
```

The dedicated pure presentation test also failed before implementation because
the required `capacityHistoryMetric` export did not exist. Constructed values
are confined to this deterministic no-I/O test; they are not browser or provider
fixtures.

## Candidate Green and build checks

```bash
node --experimental-strip-types frontend/tests/pure/native-usd-capacity.mjs
node --experimental-strip-types frontend/tests/pure/quota-reset-presentation.mjs
node --experimental-strip-types frontend/tests/pure/provider-account-presentation.mjs
node --experimental-strip-types --experimental-loader ./frontend/tests/pure/typescript-source-loader.mjs ./frontend/tests/pure/capacity-history-pagination.mjs
npm --prefix frontend run typecheck
npm --prefix frontend run build
```

All commands above passed. The first attempt at the existing pagination test
omitted its documented source loader and failed with `ERR_UNSUPPORTED_DIR_IMPORT`;
the documented command above passed without changes to that test or its loader.
The new pure test covers exact decimal preservation beyond JavaScript's safe
integer range, zero, stale values, unavailable values, wrong units, native USD
selection, legacy ratio selection and mixed current metrics.

The frontend build used the already installed dependency tree; no package was
added, upgraded or downloaded. The candidate was not served through an
alternate-origin proxy because that would change the deployed origin/cookie
trust boundary.

## Required integration verification

After root deploys the candidate through the canonical service update, run:

```bash
node frontend/tests/browser/m6/native_usd_account.mjs \
  http://127.0.0.1:9225 http://127.0.0.1:43110 ACCOUNT_ID new
```

`ACCOUNT_ID` is an existing actual account with available native USD readings;
it is supplied by the operator, never hardcoded. The check creates and closes
only its own tab in the existing signed-in context. It compares visible cards
and history with actual typed API data, checks owner-provided identity wording,
keyboard expansion and desktop/mobile document overflow, and prints only safe
result codes and counts. It does not extract cookies, credentials, raw provider
payloads or account names. The `existing` mode inspects an already open matching
page without navigating or closing it, as used for Red.

Same-origin deployed-browser Green, real mixed-unit history, other-provider
browser regression, and the canonical M6 exit remain **Not Run** for this
isolated candidate. Pure mixed-metric checks are not claimed as live mixed
provider evidence. Root owns deployment and those integration results.

## Integrity and rollback

No mock, fake, response interception, recorded provider response, seeded
telemetry, default profile access, provider request or agent process control
was used. No production database or service was changed. There are no new
dependencies, license implications or secret-handling paths. Rollback is a
frontend code revert and rebuild; no data migration is necessary. This
candidate does not close M6.
