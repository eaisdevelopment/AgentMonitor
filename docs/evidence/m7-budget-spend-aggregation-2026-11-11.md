# M7 T004 compatible spend aggregation evidence

- Status: Intermediate pure-domain contribution; no T004 or milestone completion
  claim. No provider, persistence, HTTP or browser boundary was exercised.
- Authority: approved M7 T004, focused plan 1.1.0 and calculation/data rules.
- Requirements: FR-ORG-003, FR-BUDGET-002/004/005; M7-A02; contributions to
  AC-UI-005/006 and AC-TEST-001/005. UI and real aggregation acceptance remain open.
- Module: M05. Consumes unchanged CTR-CAP-002 2.0.0 report types and
  CTR-COMMON-003 exact money. No published contract change.
- HEAD observed at final verification: `c453fe0a91c83e47fe35204fa1b0b92d9c1f780b`.

## Existing versus added behavior

`budget_reports.py` already chooses the newest complete whole report in one
compatible context, retaining the latest incomplete attempt independently.
`budget_money.py` already provides exact signed summation with explicit overflow.
Neither previously grouped selected spend or deduplicated canonical pools.
Those existing implementations were not duplicated or modified.

The adjacent `budget_aggregation.py` adds `aggregate_budget_spend` with immutable
M05-internal input/result dataclasses. The input contains each selected resource,
its explicitly established canonical pool/epoch identity and evidence kind,
and its existing `BudgetReportSelection`. No label, account name, equal amount
or credential is treated as shared-pool evidence.

Results group by currency, exact requested interval, cost basis and source
category. Categories remain separate so self/team or total/category views cannot
be silently added. Only complete coverage of the exact interval qualifies.
Grouped breakdown reports are excluded as alternative views, not added to totals.
For multiple compatible access paths to one canonical pool, the newest complete
report contributes once; the other resources remain explicit duplicate coverage.
Conflicting provider/target/source contexts for that pool/group are excluded.

All amounts use the existing `sum_money`; signed adjustments remain signed and
overflow raises explicitly. A qualified complete empty report yields derived
zero only when `empty_means_zero` authorizes it. Unknown currency, absent reports,
partial coverage, unproven empty results and unresolved overlap yield explicit
per-resource exclusions. No eligible reports yields no groups and
`no_eligible_reports`, never a fabricated monetary zero. More than 2,000 selected
canonical pools yields no truncated totals and `selection_too_large`; multiple
access paths to one pool do not consume extra canonical-pool slots.

Each included contribution retains the immutable report, source watermark,
coverage, collection/storage times and identity evidence. Each coverage row keeps
the original current/latest selection. A retained report followed by a later
incomplete report is explicitly marked. This function has no clock and never
labels old evidence fresh; it does not synthesize failed collection attempts.

## Red, Green and checks

Before the new module existed:

```text
/home/dev/Nextcloud/Code/AI/AgentMonitor/backend/.venv/bin/pytest -q backend/tests/capacity/pure/test_budget_aggregation.py
1 failed in 0.02s
AssertionError: compatible grouped spend policy is missing
```

This is a missing owned-capability Red. The behavioral vectors were then written
before production implementation; the final test module uses static imports.
Initial behavioral Green: **13 passed in 0.36s**. Additional boundary coverage
checks exercise unknown currency, exactly 2,000 pools, 2,001 access paths to one
pool and a negative net adjustment. All values are constructed pure inputs;
none cross I/O or represent provider telemetry.

Final scoped regression:

```text
/home/dev/Nextcloud/Code/AI/AgentMonitor/backend/.venv/bin/pytest -q backend/tests/capacity/pure/test_budget_aggregation.py backend/tests/capacity/pure/test_budget_money.py backend/tests/capacity/pure/test_budget_report_selection.py backend/tests/capacity/pure/test_budget_exact_arithmetic.py
80 passed in 0.47s
```

Ruff check/format and scoped strict typing passed:

```text
MYPYPATH=src /home/dev/Nextcloud/Code/AI/AgentMonitor/backend/.venv/bin/mypy --strict --explicit-package-bases src/agentmonitor/modules/capacity/domain/budget_aggregation.py tests/capacity/pure/test_budget_aggregation.py
Success: no issues found in 2 source files
```

## Integration obligations and limits

T002/T010 must supply the real canonical pool/epoch mapping and primary dashboard
group attribution. Existing report contracts do not publish that joined inventory
projection. This increment intentionally does not invent a public contract or
derive identity from labels. The caller supplies the full selected inventory,
not just the visible API page, and displays exclusions/coverage alongside each
subtotal. A scoped query must keep its cutoff fixed.

T010 must join collection failures and freshness policy separately, because a
failed collection without a normalized report is not a `BudgetReportViewV1`.
The report timestamps retained here support honest age/watermark presentation;
they do not establish current provider data. Account moves change primary group
attribution, not historical financial identity. Scope-epoch mappings must prevent
an interval spanning distinct financial scopes from masquerading as one pool.

No forecast, balance-snapshot summation, currency conversion, storage, API,
provider behavior, migration, dependency/license or operational change. Real
pool attribution, source-to-aggregate reconciliation, HTTP/UI and full canonical
T004/M7 gates are Not Run by this contribution. Root must include the new pure
test target in the appropriate canonical ticket check.

Files: `backend/src/agentmonitor/modules/capacity/domain/budget_aggregation.py`,
`backend/tests/capacity/pure/test_budget_aggregation.py`, and this evidence.
No credentials, provider profiles, owner resources or telemetry were read/written.
No commit was made.
