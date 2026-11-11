# M7 first implementation checkpoint

Status: implementation in progress. No M7 completion, installed change or live
billing verification is claimed. The accepted M6 dashboard remains deployed.

## Authority, scope and contracts

[Owner instruction](m7-implementation-authority-2026-11-11.md) authorizes focused
execution plan 1.1.0 and M05 increment 0.3.0. T001 is complete as planning only;
T002/T003/T004 are in progress. Requirements FR-BUDGET-001..006, FR-ACC-001,
AC-TEST-001/003/005/006 and M7-A01/A02 govern this checkpoint.

- CTR-COMMON-003 keeps the exact 78-digit/18-scale representation and corrects
  context-dependent conversion; no wire/schema range change.
- CTR-CAP-002 2.0.0 adds typed exact money/report/coverage contracts beside the
  original reserved BudgetViewV1. Old quota contracts remain intact.
- CTR-REG-002 adds optional initial_connection_purpose with null legacy default.
  RegisterAccount request/command accepts api intent; identity and monitoring
  are not asserted by this metadata. Generated HTTP/client change is compatible.
- M02 v1_0730 adds one nullable checked column. Existing migration bytes stay
  intact; schema/catalog admission is updated and exact new DDL fingerprint was
  measured from a genuine isolated Alembic migration. It contained zero accounts
  and passed SQLite integrity. Installed upgrade/recovery remains Not Run.

## Exact-money Red/Green

`tests/capacity/pure/test_budget_exact_arithmetic.py` first produced four expected
failures and two passes: valid 38/78-digit values rounded, and a low-precision
caller context raised decimal.Inexact. Replacing arithmetic scaleb with exact
Decimal string construction passed six new cases and the related 44-case
regression selection. No global Decimal context was changed.

[Money policy evidence](m7-money-policy-2026-11-11.md) covers 44 additional pure
cases: exact sums/subtraction, final overflow, cents scaling, USD half-even and
sub-cent display, signed soft/hard headroom, unclipped ratios and mixed-currency
rejection. Caller compatibility is checked from report context before use; no
cash balance is inferred from a soft budget. New-module absence assertions are
identified separately from the existing conversion behavioral regression.

## Reports and correction semantics

Seven contract-availability tests initially failed for the missing typed report.
Nine selection tests initially failed for the absent immutable report/selection
policy. After implementation both selections passed. Additional behavioral Reds
found duplicate charge intervals and lagging-watermark empty-zero claims were
accepted; both were corrected. The independent M05 review then found two actual
issues: rows outside declared partial coverage and distinct adjustments sharing
an interval being rejected. Two new tests failed for those reasons before the
fix, then the eleven-case contract suite passed.

Current selection replaces a whole compatible report, including removal of old
charges by a complete empty revision. A later partial attempt never refreshes
or overwrites the prior complete facts. Rotation preserves same-scope history;
changed scope generation, currency, grouping or reporting period cannot be
combined. Distinct adjustment IDs can share an interval and apply once.

The pure test suite uses constructed typed values with no external I/O. After
Green, temporary new-module availability probes were refactored to ordinary
static imports. No provider payload, account fixture or seeded telemetry exists.

## Executable evidence

- Final canonical M7 pure selection passed 83 tests after both independent
  review corrections. The real existing capacity schema regression passed four
  tests against the new empty v1_0730 database.
- [Mutation evidence](m7-budget-mutation-2026-11-11.md): seven meaningful mutants
  killed in disposable copies, unchanged baseline passed, no skips/setup errors.
- [Registry evidence](m7-billing-intent-2026-11-11.md): actual file SQLite
  schema/repository Reds, then seven new tests and 18 scoped registry/HTTP
  regression tests passed after correcting the P01 field mapping.
- [HTTP setup evidence](m7-billing-enrollment-http-2026-11-11.md): initial create
  returned 422; now creation returns 201 and GET billing-connections returns
  404. That remains the explicit next behavioral Red, not a passing setup flow.
- [Runner evidence](m7-command-progress-2026-11-11.md): technical/live/browser/
  deploy/exit commands invoke a real runner; pure/mutation run, remaining
  boundaries remain Not Run. AUTO-M7-TEST exits nonzero; not full M7 acceptance.
- Scoped strict mypy and Ruff passed for the changed contract/domain surfaces.
- OpenAPI/client generator reports compatible additive change, 78 operations.
- AUTO-BUILD passed generated-contract check, TypeScript and production build;
  no candidate activation or installed-browser behavior is implied.

## Security, migrations, license and remaining work

No coding agent read keys, arbitrary environments or provider profiles. No
provider requests, account configuration, user-agent control or installed-service
changes occurred. No dependency/license change. Runtime-only credential scope is
recorded with the owner's implementation instruction and security/config docs.
The additive migration was exercised only in isolated databases; no owner data
was migrated or restored. Planning control hashes are rebound separately without
rewriting historical reviews or approving the frozen 20-plan baseline.

Next: publish and implement the independent billing connection/resource/status
contract, local owner credential entry, and actual UI setup; continue the first
real provider report through persistence, scheduling and Overview/detail. No
owner action is needed for these implementation steps. Live billing access will
be requested only through the working owner flow when it is actually needed.

## Commit checks

Documentation and synchronized planning checks pass. The staged secret scan
reported only the removed and added generated `openapiArtifactSha256` constants.
Both were independently matched to SHA-256 of the corresponding old/new OpenAPI
JSON bytes; these are reviewed nonsecret artifact digests, not API credentials.
No other finding was reported. The dashboard service remains active and its
loopback page returned HTTP 200; this is availability, not M7 browser acceptance.

## Subsequent credential-entry increment

The independent billing metadata connection is now implemented, and the
[safe status projection](m7-billing-credential-status-2026-11-11.md) adds
CTR-REG-014 1.1.0 lifecycle status through real SQLite, HTTP and the built UI.
The [provider-neutral protected writer](m7-billing-env-store-2026-11-11.md)
and [local operator](m7-billing-credential-operator-2026-11-11.md) preserve legacy
Ollama isolation while adding selected Anthropic/OpenAI owner entry. Real
empty-file and hidden-terminal cancellation checks do not establish successful
key storage or provider access. The candidate builds; it is not deployed.

Remaining first-journey work includes the copy-command/installed setup wiring,
actual provider access, one monetary report through durable storage/collection,
then detail/history and Overview. The current report contract can represent the
first ungrouped cost report. Provider credential readers remain provider-specific;
generic storage alone does not authorize a billing HTTP request. Collection
integration must handle API-only targets without invented CLI profiles and
report receipts without invented observations. These remain the existing
T002/T005/T006/T007 implementation work, not new owner approvals or scope.
