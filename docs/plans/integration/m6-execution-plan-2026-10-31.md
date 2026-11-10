# M6 execution plan: Ollama cloud monitoring

**State:** technical gate passed at `0f7ca54` on 10 November; [M6-A10 owner acceptance recorded](../../evidence/m6-owner-acceptance-2026-11-10.md); milestone closed. See the [technical completion record](../../evidence/m6-technical-completion-2026-11-10.md). Scope remains under the approved [cloud implementation plan](m6-ollama-cloud-implementation-change.md), amended by the owner's [4 November local-scope deferral](m6-local-ollama-deferral-2026-11-04.md). The local-service and process plans are retained as deferred future work, not M6 prerequisites.

**Owner:** A03 Ollama adapter; integration steward owns shared contracts, deployment and the completion command. **Prerequisites:** accepted M3 and M5. This plan follows the [SDLC](../../engineering/sdlc.md), [completion gates](../../engineering/completion-and-automation-gates.md) and [sub-agent runbook](../../engineering/subagent-runbook.md).

## Outcome and boundaries

Operators register and organize Ollama cloud accounts through the dashboard and see native subscription balances or legacy limits for SDK and EAIS, with real source, observation time, precision and freshness. Real observations reach history and configured alerts. Cloud-provider failure must not interrupt the dashboard or Claude/Codex collection.

All local Ollama tasks are deferred to [future versions](future-local-ollama-backlog-v1.json): installation/daemon discovery, installed or loaded models, local processes/resources/correlation, their UI and all local live verification. No installed model, local endpoint or agent enumeration is required from the owner for M6. Existing local code/evidence remains retained without a completion claim. M7 API accounting and M8 release hardening remain separate; neither receives local Ollama as an implicit prerequisite.

## Active acceptance catalog

The owner-approved scope contains eight acceptance IDs and four stories. The catalog's stable gaps represent deliberate deferral, not passed/skipped tests. Every active item still requires real evidence.

| ID | Observable acceptance | Evidence |
|---|---|---|
| M6-A01 | Ollama appears as a provider and can be added to existing organization/account administration without hardcoded account names. | Built dashboard, versioned API and real SQLite; `FR-ACC-001..005`, `AC-UI-002`. |
| M6-A03 | SDK and EAIS accounts or their actual team/shared relationship are identified with owner-confirmed, non-secret aliases; unavailable/ambiguous roles stay explicit. | Real owner-guided source check, per-account outcome, `AC-LIVE-003`; no need to enumerate every agent. |
| M6-A04 | For each accessible account/scope, the native `balance` variant and timestamp are displayed and reconciled with the provider's authoritative view. Included and purchased balances and legacy windows remain distinct; team balance is not duplicated. | Real account/provider UI comparison with documented precision/lag; `AC-LIVE-005`, `FR-QUOTA-001/002/004/006`. No data or no documented access is explicitly unavailable/unsupported with evidence, not zero. |
| M6-A05 | New real observations reach capacity history and appropriate configured alerts; no duplicate event or silent stale-as-current display. | Real source → M04 → M05 → API → built UI and real alert lifecycle as naturally available; `AC-HIST-001`, `AC-ALERT-002`. |
| M6-A07 | Provider offline/auth failure and recovery are truthful and do not interrupt the dashboard or Claude/Codex collection. | Natural failure/recovery or the approved isolated-network collector scenario, with exact lineage and interval continuity; otherwise Blocked/Not Run; `AC-LIVE-007`, `AC-OPS-003`. No deliberate daemon/agent stop. |
| M6-A08 | Existing dashboard remains responsive; product links and account features work, including mobile and keyboard. | Real built-browser tests; `AC-UI-003..006`. |
| M6-A09 | Cloud collection respects approved host/method/field scope, limits, privacy, profile integrity and exact source/version. | Privacy/security review and real read-only evidence, `FR-COL-003..008`, `FR-SAFE-002`, `AC-OPS-006`, `AC-TEST-001..006`. |
| M6-A10 | The exact implementation has one passing canonical M6 completion result, a reproducible operator runbook, explicit unsupported/blocked results, and the owner's review. | Canonical command and receipt, full-scope checks, documentation and owner decision. |

ST-OLL-001 covers independent cloud capability/source admission; ST-OLL-003 cloud account scope and authentication; ST-OLL-004 balances/history; ST-OLL-005 cloud dashboard integration and closure. ST-OLL-002 and M6-A02/A06 are recorded in the future backlog. Local failure/recovery is deferred. The owner-approved [4 November controlled recovery amendment](m6-cloud-controlled-recovery-proposal-2026-11-04.md) permits one isolated cloud collector request followed by normal scheduled recovery; controlled evidence remains separate from natural provider-error evidence.

## Tasks, order and owner participation

The [14-ticket catalog](m6-ticket-catalog-v1.json) and [ticket register](m6-ticket-register-2026-10-31.md) are the active work list. Local-only M6-T002/T003/T009/T013 and local portions of mixed tickets are retained in the future backlog with original evidence. Active tickets no longer depend on those local tasks.

1. Preserve the reconciled integration baseline, accepted M5 evidence and running dashboard.
2. Complete SDK/EAIS cloud coverage through existing dashboard CRUD and official connection flows. The owner creates the SDK record and supplies its key locally; do not invent accounts or repeat known names/approvals.
3. Verify each real available scope against the provider's authoritative balance view, including exact source/time/precision and shared-pool semantics.
4. Verify current readings, history, applicable configured alerts, authentication/failure behavior, source security and browser usability.
5. Run the exact cloud-scope `AUTO-M6-EXIT`, resolve actual failures, retain unavailable cloud evidence honestly, and present the result for owner review.

Existing scoped implementation authority persists. Automatic local dashboard sign-in is already authorized; passwords and keys remain local and unexposed. The owner is not asked to operate internal gates or repeat unchanged confirmations. A genuine missing provider credential or scope choice is requested only when necessary.

## Verification, contracts and operations

Use pure domain tests for mapping, money, limits/backoff and evidence classification, and real official cloud sources, SQLite, HTTP and built browsers at external boundaries. No simulated sources, seeded telemetry, copied responses or guessed identity/capacity. No provider profile or running-agent mutation.

The internal exit catalog advances to schema 1.1.0 and binds its revised selection by hash. Required cloud evidence cannot be waived by local deferral. `AUTO-M6-LOCAL-ADMIT`, local inventory and process/model observations are outside the M6 gate. No public API/schema/dependency change is needed for this scope correction.

Shared `AUTO-BUILD`, `AUTO-QUALITY`, `AUTO-DOCS-CHECK` and `AUTO-PLAN-CHECK` remain technical checks. `python3 tools/planning/validate_m6_tickets.py --stage plan` validates ticket coverage/dependencies only. `AUTO-M6-EXIT` remains the full technical completion command. Deferred results are not Passed; historical receipts are not reinterpreted for the new catalog.

## Risks and scope control

Missing SDK credentials or authoritative cloud scope evidence affects the relevant cloud checks, not independent engineering work. Natural cloud recovery may remain unobserved; do not fabricate it or trigger an outage without a separate concrete approved scenario. Shared balances must not be double counted. Keep `.env` secrets, provider profiles and running agents protected and the dashboard available.

The original 73–118-hour whole-slice estimate included local work and is historical; it is not a forecast of remaining cloud work. No extra feature, local requirement, new gate or repeated account confirmation may be added as a blocker without an applicable requirement and evidence. New enhancements go to the backlog.

## Historical scope

The 31 October plan and 3 November host clarification originally required local model-present and process evidence. The owner's 4 November decision supersedes those requirements for M6 and V1 release scope. The [3 November checkpoint](../../evidence/m6-delivery-checkpoint-2026-11-03.md) and [4 November corrections](../../evidence/m6-dashboard-corrections-2026-11-04.md) retain the actual earlier results. Deferral does not rewrite that evidence or claim those scenarios ran.
