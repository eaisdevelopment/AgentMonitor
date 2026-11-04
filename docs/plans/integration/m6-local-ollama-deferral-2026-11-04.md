# M6 scope decision: defer local Ollama to future versions

- Decision: **Approved**, 4 November 2026.
- Authority: the owner's direct instruction: **“defer all local ollama tasks to the next versions to backlog”**.
- Owner: integration steward; affected delivery owners A03, M03, M04, M06, P01 and P02.
- Scope: M6 acceptance and planning correction; this is not M6 completion.

## Decision and retained scope

All local Ollama tasks move to the [future-version backlog](future-local-ollama-backlog-v1.json), with no assigned release date. This includes installation/version discovery, daemon availability, model inventories and model-present evidence, local process/resource observation, hierarchy/correlation, local views, and their local verification, failure/recovery and operational work. They are not moved into M7 or M8 as hidden prerequisites.

M6 now covers cloud account/organization administration, SDK/EAIS coverage, official balance or legacy subscription windows, source/freshness/history, configured alerts, cloud failure/recovery, security/privacy, browser usability and technical closure. Existing local implementation and historical results are retained; neither their existence nor their deferral claims future local acceptance.

The current cloud recovery requirements remain unchanged. This decision does not approve a controlled outage, waive missing cloud evidence, or authorize installing/loading a model, stopping a daemon, deleting code/data or changing a provider profile.

## Traceability and backlog

| Future ID | Deferred scope | Original IDs |
|---|---|---|
| FUT-OLL-LOCAL-001 | Local installation/version discovery and capability admission | M6-T002; local portions of M6-T008 and ST-OLL-001; M6-A02 |
| FUT-OLL-LOCAL-002 | Host/service discovery, installed/loaded model inventory, model-present observation | M6-T003/M6-T009, ST-OLL-002, M6-A02 |
| FUT-OLL-LOCAL-003 | Local processes, resource metrics, hierarchy and model/account correlation | M6-T013; local portion of ST-OLL-005; M6-A06 |
| FUT-OLL-LOCAL-004 | Local UI/API integration, history/alerts as applicable, security, recovery, deployment and acceptance | Local portions of M6-T006/T007/T014/T015/T016/T017/T018 and ST-OLL-005; M6-A02/A06 |

The backlog retains the original ticket records, including historical evidence and prior status. The active [ticket catalog](m6-ticket-catalog-v1.json) removes M6-T002/T003/T009/T013 and their dependency edges. Mixed tickets retain only cloud work. No deferred ticket is marked Done or Passed.

Active acceptance IDs: **M6-A01, M6-A03, M6-A04, M6-A05, M6-A07, M6-A08, M6-A09, M6-A10**. Active stories: **ST-OLL-001, ST-OLL-003, ST-OLL-004, ST-OLL-005**. ST-OLL-001 now admits cloud capabilities independently of local installation; ST-OLL-005 integrates and closes the cloud scope. M6-A02/A06 and ST-OLL-002 remain stable historical IDs in the future backlog.

Shared requirements FR-DISC-001..008, FR-STATE-001..004, AC-PROC-001..005 and related UI/collection requirements remain applicable to Claude/Codex. Their local Ollama portions are deferred. Cloud requirements FR-ACC-001..006, FR-QUOTA-001..006, FR-COL-001..008, AC-LIVE-003/005/007, AC-HIST-001, AC-ALERT-002, AC-OPS-003/006 and AC-UI-002..006 remain in scope where already allocated.

## Contract and completion impact

Owning module: integration/completion automation. The internal `agentmonitor.m6_exit_catalog.v1` catalog advances to schema version **1.1.0** with the eight active acceptance IDs, four active stories and cloud-only prerequisites. The private snapshot producer also advances to schema **1.1.0**, omitting local installation/process fields and queries; its only consumer is updated together. The catalog's existing hash binding prevents prior receipts from proving the revised scope. Deferred IDs are excluded from the active evidence set rather than reported as passing tests.

`AUTO-M6-EXIT` must not invoke local inventory/admission or require local installation/model/process evidence. Shared cloud admission, source security, exact scope/account reconciliation, history/alert, browser, natural-recovery and quality checks remain fail-closed. Existing dedicated local commands and tests are retained for the future backlog, not used as M6 prerequisites.

No product HTTP contract, generated client, database schema, migration, dependency or license changes are required. Existing runtime collection/display code is preserved; the scope decision is not a promise to remove an already installed view. No provider credentials/content are read or changed. No deployment or running-agent action is required to record this decision.

## Verification and re-entry

The changed completion policy requires pure Red/Green regression evidence: failed, blocked or unexecuted local evidence cannot contaminate cloud-only outcomes; required cloud evidence must still fail closed. The initial pure Red run produced four expected failures against the previous scope. The integration handoff records the final Green result, catalog/ticket validation and documentation checks.

Canonical planning checks are `python3 tools/planning/validate_m6_tickets.py --stage plan`, `python3 tools/automation/run.py AUTO-PLAN-CHECK` and `python3 tools/automation/run.py AUTO-DOCS-CHECK`. They validate the scope change; they do not assert that cloud M6 passed. A full M6 result still requires its real current-revision technical gate and owner review.

Re-entry is an explicit future-version scheduling decision followed by review of the retained code, sources, safety boundaries and live test resources. It does not happen automatically when M6 or M7 closes. Historical local Not Run/Blocked outcomes remain historical; no invented model or replacement telemetry is permitted.
