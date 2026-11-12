# M7 financial scheduling and period isolation

Status: implementation in progress in the M7 worktree; not installed or published
by this record. M7-T007 with T003/T006/T008/T009 integration; FR-COL-004/008,
FR-BUDGET-001/006, M7-A09. Root owns composition/contracts; M04 owns persisted
selection/atomic claim. This does not close T007 or M7.

## Behavior and contract impact

- Billing scheduling now prepares both seven and thirty completed UTC days.
  Latest attempts are selected for the exact report context, so a seven-day
  Check does not suppress thirty-day scheduling. Current targets include queued
  connection checks while disabled monitoring still prevents automatic work.
- Current bounded inventory is read before dispatch. Queued and automatic work
  share a key based on provider, existing request-budget scope and operation.
  Least recently started work wins; ready age and stable key break ties. A
  queued request has priority only within that same key. Shared billing scopes
  do not gain priority by adding access paths.
- CTR-COL-002 2.6.0 adds immutable bounded dispatch snapshots and a read port.
  Existing persisted run/schedule timestamps supply order; no cursor table,
  migration, queue, worker, dependency or tuning screen is added. Exact-run
  optional claim selectors retain atomic authority, deadline, lease and rate
  checks. Invalid authority rolls back and permits later work to be considered.
- Billing collection policy advances from 1.0.0 to 1.1.0. Schedule target digests
  include schedule identity to avoid the existing unique-target collision.
  Shared request-budget digests and replay-stable request identity are retained.
  New periodic identities include the policy; old queued policy runs cannot be
  executed as the new policy and remain subject to existing expiry/recovery.
  Stored reports and HTTP schemas remain readable and unchanged.
- Ollama prepares all current self schedules before selection. Team metadata is
  considered only to find explicit queued team requests; no automatic team
  collection is enabled. Global balance/usage cooldown remains authoritative.
  A consumed per-report budget yields before shared provider admission. A known
  admission race before provider dispatch releases reserved authority and yields;
  failures after possible dispatch retain the existing uncertainty handling.

One admitted request allowance is still shared across billing periods. Two due
periods do not authorize twice the source request budget or guarantee both run
in one fifteen-minute slot. Fairness changes order, not provider limits.

## Evidence so far

- Range tests: four expected failures (missing thirty-day intent/selection), then
  passing exact interval, independent identity, recent-week isolation and oldest
  range ordering.
- Schedule collision test failed on identical target digests. The correction
  initially broke two replay-stability tests; request identity was separated from
  schedule identity and the combined source/dispatch suite passed 99 cases.
- New immutable dispatch and age-ordering tests failed for missing contracts and
  policy, then passed. They cover sustained manual work versus older automatic
  work, never-served priority and deterministic input-order-independent ties.
- Real empty/pending-registry scheduling and worker checks plus focused policies:
  17 passed. They do not prove successful live monetary provider access.
- Boundary analysis caught composition import cycles. Moving the pure operation
  allowlist and passing prepared cloud admissions eliminated them: zero violations.
- Focused mypy passed six changed source modules/contracts. Generated client/API
  compatibility passed 98 operations; HTTP schema remains compatible.

- Real metadata regression: five tests passed in 5.03 seconds. A private copy
  of actual registry data proves exact later-run claim, service-age ordering,
  both scheduled periods, self-only automatic scope and real M02 disable fencing.
  The manual-budget assertion first failed because scheduled_due was true; it
  passed after filtering consumed budgets, without reading a credential or
  reaching provider access.
- Canonical pure lane: 717 Python cases plus eleven presentation suites passed.
  Collection guards: 72 passed. These do not constitute populated billing proof.
- Independent transition review found a remaining old/new manual schedule
  collision. New Check/Collect schedule IDs now include collection policy while
  run/request/idempotency identities remain stable. Exact legacy replay remains
  readable; unrelated schedules still conflict. The transition test first failed
  for the missing policy option; focused action/admission suite then passed ten.
- The installed prior revision's real Overview probe passed with two financial
  rows, API/DOM ordering, financial-entry/history/navigation and zero mutations.
  This protects continuity but does not validate the new installed scheduler.

- Canonical AUTO-QUALITY passed at 04:49 UTC: Ruff/format, mypy 732 source
  files, dependency boundaries, compatible generated API/client, TypeScript
  and production build. Earlier attempts caught a long docstring and test
  typing/export errors, corrected without changing runtime behavior.
- Independent final review found no remaining must-fix in its dispatch and
  transition scope. It checked queued versus scheduled priority, disabled
  monitoring, explicit team-only requests, current authority and old-policy replay.

- Canonical HTTP guards passed 22 cases after the policy transition change.
- Staged secret scan found two generic-api-key matches, both generated
  openapiArtifactSha256 constants independently matched to actual old/new
  OpenAPI bytes; no unresolved finding. Planning/docs/diff checks passed.

Installed collection/browser continuity and publication remain to be verified. Anthropic/OpenAI populated monetary collection remains unverified without
owner-configured administrative billing access. No account, key or monitoring
preference on the owner's installation was changed.

## Operations, privacy and scope

Use the existing same-schema selected-release update after checks pass; preserve
backup/recovery and installed revision verification. Default provider profiles,
agent processes and credentials are untouched. Isolated copied real registry
metadata supplies queue/lifecycle tests; no provider responses, readings,
credentials or timestamps are manufactured. Actual owner setup is not performed
by these tests. No license or dependency change. The scope remains the fixed
sixteen tickets and M7-A01..A10; finite category coverage and remaining live,
analysis, recovery and release work are still required.
