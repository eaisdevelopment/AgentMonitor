# V1-M3 local foundation handoff

- Outcome: **V1-M3 accepted on the Linux owner workstation**
- Milestone/plan: `V1-M3`, Tasks 1–6 in
  `docs/superpowers/plans/2026-09-19-agentmonitor-v1-m3-claude-slice.md`
- Modules: M02 Registry, M03 Provider system, A01 Claude, M04 Collection
  control, M05 Capacity, M06 Runtime observation, A04 Linux, P01 API, P02 UI
- Requirements/acceptance: the requirement and scenario IDs allocated to M3
  Tasks 1–6; full `AC-TEST-001` is not claimed because of the chronology
  deviation below
- Contracts: compatible V1 additions to `CTR-REG-001..010`,
  `CTR-PROV-001..008`, `CTR-COL-001..007`, `CTR-CAP-001/003/004/009`,
  `CTR-RUN-001..007`, `CTR-BOUNDARY-001..003`, `CTR-PLAT-001`, and
  `CTR-API-001..003`
- Worktree basis: parent commit `b23015b`; final milestone-foundation commit is
  recorded in the Git log containing this handoff
- Recorder/date: root integration steward, 2026-09-23 Europe/London

## Delivered outcome

The local M3 foundation provides versioned registry/provider/collection/
capacity/runtime contracts, the ordered SQLite migration chain through
`v1_0603`, evidence-scoped Claude and Linux read-only adapters, producer-owned
query ports, nine authenticated observation API operations, a 22-operation
generated OpenAPI/TypeScript client, and responsive dashboard views for
accounts, providers, collection runs, quota/capacity, processes, and sessions.

Account detail requests sessions with an `account_id` selector and renders
`Running sessions` beside quota windows. The browser passively verifies that
the real same-origin observation GETs return 200; it does not intercept or
replace responses. Populated quota, collection, health, and session views
render their available trace/provenance fields and label unavailable contract
data explicitly.

## Final verification

| Boundary | Command/result | Status |
|---|---|---|
| Canonical test | `python3 tools/automation/run.py AUTO-TEST` — `780 passed, 5 skipped, 1 failed in 394.95s` | **Failed / Blocked** |
| Live Claude | `test_real_subscription_observation_has_current_structural_semantics` returned `deadline_exceeded` / `usage_blocked_workspace_trust` | **Blocked** |
| Independent focused review | 250 backend/API/boundary/runtime tests; no skips | Passed |
| Independent API/error regression | 18 tests | Passed |
| Real browser | P02 `quick`, ten production-browser scenarios using migrated file SQLite, Uvicorn, authentication, production bundle, and installed Chrome | Passed |
| Populated account browser lane | Browser reported no real registered account in the isolated database | **Blocked** |
| Quality | `python3 tools/automation/run.py AUTO-QUALITY` | Passed |
| Build | `python3 tools/automation/run.py AUTO-BUILD` | Passed |
| Documentation | `python3 tools/automation/run.py AUTO-DOCS-CHECK` — 227 Markdown files | Passed |
| Planning | `python3 tools/automation/run.py AUTO-PLAN-CHECK` | Passed |
| Contract generation | 22 operations; OpenAPI SHA-256 `74e48f5066dc76e7d4b7946a4411b00ccf94a5504db7dbca1ac96016ad2acfb7` | Passed |
| Static/boundary | strict mypy 170 files; boundary checker zero violations; `git diff --check` | Passed |

The five skipped cases are visible live/provider declarations, not passes:
three real Registry reconciliation/enrollment cases, one real Collection run,
and one real Capacity commit. They require the same unavailable live Claude
observation and no provider data was constructed to satisfy them.

## Red, Green, and review corrections

Story evidence is retained in:

- `docs/evidence/m3-st-prov-001.md`
- `docs/evidence/m3-st-reg-001.md`
- `docs/evidence/m3-st-cla-001-provider-system-persistence.md`
- `docs/evidence/m3-st-obs-001.md`
- `docs/evidence/m3-st-obs-002.md`
- `docs/evidence/m3-st-obs-003-p01.md`
- `docs/evidence/m3-st-obs-003-p02.md`

The final review batch caught and corrected safe 404/503 mapping, bounded
provider keys, account-scoped session queries, browser request mutation
sensitivity, and populated capacity/collection provenance rendering. Each
behavioral correction records its real Red and subsequent Green where the Red
still existed. The repository-unavailable catalog test was coverage of already
working behavior and is truthfully recorded as Green-first, not as a fabricated
Red.

The initial P01 Red record has no exact timestamp/worktree reference and the
initial P02 Red timestamp is approximate. Their chronology cannot be recreated.
This is a documented TDD evidence deviation and leaves universal
`AC-TEST-001` unaccepted unless the owner explicitly accepts it. Current tests
remain meaningful and mutation-sensitive.

## Contract, migration, and compatibility impact

- OpenAPI and generated TypeScript changes are compatible V1 additions.
- M06 session list adds a bounded optional `account_id` filter; its cursor is
  bound to that filter.
- Database migrations are additive and ordered from `v1_0200` through
  `v1_0603`; real fresh-file migration and repository tests passed.
- No destructive migration or downgrade claim is made.
- Full provider/filter/sort profiles outside the approved M3 narrowing remain
  deferred to their owning module plans.

## Security, privacy, dependency, and operations impact

- Provider profiles and running processes were read-only; no logout, login,
  signal, restart, routing, or credential change occurred.
- No prompt, response, source content, tool activity, arbitrary environment,
  credential value, raw provider payload, or personal account identifier was
  retained.
- No mock, fake, stub, emulator, response interception, recording/replay, demo
  account, seeded telemetry, placeholder metric, test-only endpoint, or
  hardcoded passing branch was used.
- No new dependency or license-input change was introduced by M3.
- Runtime observation operations documentation was added; installed native
  lifecycle, backup/restore, macOS, hosted CI, full SAST/secret/vulnerability
  scans, fresh frozen install, SBOM/notices release generation, and publication
  remain Not Run or outside this milestone.

## Historical blocking exit conditions

At the initial foundation handoff, V1-M3 was blocked until the following became
real and Green:

1. The owner accepts Claude workspace trust for the test workspace without
   changing or relocating the default provider profile.
2. One fresh Claude quota observation reaches the real collection and capacity
   persistence path.
3. One real runtime session is safely correlated to the same confirmed account.
4. The populated account/quota/session path is rendered through authenticated
   generated-client browser views with matching observation/run IDs.
5. Populated quota/session pagination is exercised if the real data volume
   produces a second page.
6. The owner accepts or rejects the documented initial Task 6 Red-evidence
   chronology deviation.

Items 1–4 and 6 are resolved by the accepted live/deviation records. The real
data volume produced no second history page, so item 5 was truthfully Not Run;
the first-page `has_more` behavior remains tested and visible. It does not block
the one-observation-per-lane M3 exit rule.

M4 has not begun.

## 2026-09-24 final M3 acceptance update

This update supersedes the handoff's earlier live blockers. One owner-confirmed
Claude account now has real quota and official-OTLP runtime observations, real
M04/M05/M06 receipts, durable same-account correlation, versioned API transport,
generated-client consumption, and authenticated production-browser rendering.
Capacity history and bounded session-tree operations raise the generated OpenAPI
operation count from 23 to 25 without a breaking V1 change.

`AUTO-M3-LIVE` passed against `/home/dev/.local/share/agentmonitor` using a
native memory-only password prompt. The real browser reconciled the exact
account, quota observations, collection runs, process/session lineage, history,
topology counts, and complete provenance at the required desktop and responsive
viewports. Natural stall and ambiguous-manual-correlation examples remain Not
Run and were not replaced with synthetic data. M4 has not begun.
