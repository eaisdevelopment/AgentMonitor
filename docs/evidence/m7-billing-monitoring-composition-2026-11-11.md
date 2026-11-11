# M7 billing monitoring composition and integration

Status: Intermediate T007/T011 under approved focused plan 1.1.0.
Requirements: FR-BUDGET-001/006, FR-ACC-001..004/006;
acceptance: M7-A01/A07/A09, AC-TEST-001/003/006, AC-UI-005.
Root owns the composition and shared contracts; M02 owns authority mutation,
P01 HTTP and P02 rendering. No full monitoring or M7 completion is claimed.

## Contract and implementation

CTR-REG-014 advances additively to 1.4.0: owner monitoring intent, internal
verification proof, server-derived eligibility and ports. Existing metadata
and quota contracts are unchanged. The same M02 producer/six consumers are
synchronized in the catalog; independent review verified all twenty parent
plans unchanged. No migration, dependency, licensing or secret-custody change.

Composition reads the actual M04 run/captured target and M05 commit receipt and
immutable report through their public adapter methods. Pure policy checks
account/resource/provider, exact scope and binding generations, run/report
identity, committed payload digest, complete coverage and temporal consistency.
A complete empty report qualifies as access evidence without invented facts;
it is not automatically a monetary zero. Re-enabling after a preference change
can reuse unchanged access; a different credential or scope cannot.

M02 rechecks the fresh full target in its mutation transaction. Disable needs
no provider proof or key. Durable command replay precedes fresh eligibility and
rejects a subsequently superseded outcome. Credential rotation/disconnect and
archive revoke enabled authority atomically; the scope-edit implementation must
use the same hook. Default provider profiles and running agents are untouched.

The browser consumes current server eligibility. An old Check success is not
permission to enable. The shared HTTP status exposes safe versions/generations,
not credential IDs/values. Missing keys never enable monitoring. Production
seven-day due scheduling is now connected to the supervised worker. Monitoring
readiness requires that worker to be available; other provider scheduling and
thirty-day durable intent remain explicit T007 work. A positive browser-closed
provider run is still required before live monitoring is claimed.

## Red, Green and scope of evidence

Root Red: the new command import was absent; the proof policy module was absent;
the actual migrated SQLite metadata/status test could not import the monitoring
service. Each failed before the corresponding implementation existed.

Root Green: nine focused contract/lineage/real missing-key status tests passed.
The combined registry/proof/HTTP selection passed 40 tests in 18.81 seconds;
foundation contract/boundary tests passed 191 in 10.84 seconds. Strict typing
passed the five root files. Pure constructed records remained in no-I/O policy
tests; SQLite metadata came from production creation commands, with no seeded
provider success, credential or telemetry.

Independent read-only review found no concrete gap in the bounded proof policy
and verified the additive contract catalog. API Red/Green and registry transaction
cases are recorded in [HTTP evidence](m7-billing-monitoring-http-2026-11-11.md)
and [registry evidence](m7-billing-monitoring-registry-2026-11-11.md).
The existing installed dashboard service remained active throughout.

Root UI review found that the initial Disable intent retained a verification
run reference, which the closed command rejects. The correction and built-browser checks passed, as recorded in
[P02 evidence](m7-billing-monitoring-ui-2026-11-11.md); missing-key browser success is not proof
of a real enabled-account mutation. Final aggregate results follow execution.

## Remaining boundaries

Positive provider-backed enable, normal browser-closed periodic refresh,
rotation while enabled and installed financial source-to-screen verification
remain Not Run. Overview/group totals, thirty-day intent, remaining provider
coverage, dedicated history, analysis and full release remain existing M7 work.
No owner account or key was configured by this implementation.

The earlier integration is committed locally as `32b16fc`. This monitoring
increment and financial activation preparation are subsequent local work;
publication and installed activation are separate outcomes.


## Final local integration checks

`AUTO-QUALITY` exited 0 at 20:18 UTC on 11 November 2026: Ruff passed,
708 Python files already formatted, strict mypy passed 648 files, boundaries
zero violations, 85 compatible generated operations, TypeScript/lockfile checks
and Vite build passed. The final OpenAPI artifact SHA-256 is
`1e4b4a021ca7421126dd5be81aa1e4ad894978064662b833c03e2dbb27eb5e0d`.

The normal first-lane scheduler is now wired to the existing supervised worker,
and monitoring eligibility uses its actual availability. It admits one due
seven-day Anthropic report with shared remaining lifetime, paged inventory,
15-minute cadence and persisted scope-level retry enforcement at admission and
claim. Check respects the same cooldown. The scheduler/cooldown/cadence selection
passed 44 tests; [scheduler evidence](m7-billing-schedule-2026-11-11.md) names
its real empty/pending boundaries and still-unobserved provider cases. Thirty-day
and other-provider scheduling remain unfinished, not implicitly supported.

The new financial activation preparation passed 21 scoped tests including a
real isolated 0731-to-0733 migration, backup and built-candidate rehearsal; see
[activation evidence](m7-financial-activation-selector-2026-11-11.md). Installed
activation has not yet run. No test counts here are summed as unique coverage.

Shared Chrome was checked read-only: fresh /accounts navigation rendered Sign
in, with zero mutation requests and no cookie/credential inspection. Other tabs
were left untouched. Authentication affects the later installed browser proof,
not this completed local engineering increment or independent remaining work.

Local commit preflight passed. The staged Gitleaks8.30.0 scan returned one
generic-api-key finding: generated client line3, whose complete value was
verified against SHA-256 of the actual OpenAPI JSON above. This is a reviewed
public artifact hash, not a credential. Raw scan exit1 is retained; no rule
was suppressed and no clean-scan or full release-security claim is made.
