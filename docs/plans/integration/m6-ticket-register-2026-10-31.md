# M6 ticket register

**State: technical gate passed; final owner review pending.** Thirteen active tickets are done. M6-T018 remains in progress only for the M6-A10 owner review. The [technical completion record](../../evidence/m6-technical-completion-2026-11-10.md) and its exact-revision receipt bind these results. All local Ollama work remains deferred by the owner.

The [active catalog](m6-ticket-catalog-v1.json) contains 14 tickets across four stories and eight M6 acceptance IDs. [Future local Ollama backlog](future-local-ollama-backlog-v1.json) preserves the local-only tickets and local portions of mixed tickets, with their prior evidence and status. The [scope decision](m6-local-ollama-deferral-2026-11-04.md) governs both.

Validate with `python3 tools/planning/validate_m6_tickets.py --stage plan`. Planning validation is not M6 acceptance; `AUTO-M6-EXIT` remains the technical authority.

| ID | Story | Ticket | Depends on |
|---|---|---|---|
| M6-T001 | ST-OLL-001 | Reconcile implementation baseline | — |
| M6-T004 | ST-OLL-003 | Discover SDK and EAIS account scopes | M6-T001 |
| M6-T005 | ST-OLL-004 | Validate official cloud balance behavior | M6-T004 |
| M6-T006 | ST-OLL-001 | Freeze capability and contract decisions | M6-T004, M6-T005 |
| M6-T007 | ST-OLL-005 | Define canonical M6 completion gate | M6-T006 |
| M6-T008 | ST-OLL-001 | Implement cloud capability admission | M6-T006 |
| M6-T010 | ST-OLL-003 | Integrate accounts, identity and authentication health | M6-T004, M6-T006, M6-T008 |
| M6-T011 | ST-OLL-004 | Map real cloud balance and legacy windows | M6-T005, M6-T006, M6-T010 |
| M6-T012 | ST-OLL-004 | Persist capacity history and alert events | M6-T011 |
| M6-T014 | ST-OLL-005 | Implement dashboard views and provider filter | M6-T010, M6-T011 |
| M6-T015 | ST-OLL-005 | Verify cloud failure isolation and recovery | M6-T010, M6-T011, M6-T014 |
| M6-T016 | ST-OLL-005 | Security, compatibility and dependency review | M6-T006, M6-T010, M6-T011 |
| M6-T017 | ST-OLL-005 | Run live end-to-end M6 scenarios | M6-T007, M6-T012, M6-T014, M6-T015, M6-T016 |
| M6-T018 | ST-OLL-005 | Deploy, operate and close M6 | M6-T017 |

Original ticket-hour estimates remain historical planning inputs, not a remaining-work estimate or delivery promise. No model setup or local Ollama evidence is needed to close the current M6 scope.

## Ticket details

### M6-T001 — Reconcile implementation baseline

- **Status / owner:** done / M6 integration steward
- **Story:** ST-OLL-001; **depends on:** none.
- **Requirements:** FR-COL-008.
- **Acceptance:** AC-V1-002; M6: M6-A10.
- **Work:** Select one clean branch containing accepted M5 and the current dashboard, preserve both branch histories and receipt; document conflicts, service revision and rollback.
- **Done when:** A reviewable merge/baseline exists; M5 receipt and promotion remain intact; real dashboard remains reachable.
- **Verification:** git status --short --branch; git log --oneline --graph --all -30.
- **Evidence:** [m6-baseline-discovery-2026-11-01.md](../../../docs/evidence/m6-baseline-discovery-2026-11-01.md).

Technical result: [10 November completion evidence](../../evidence/m6-technical-completion-2026-11-10.md).

### M6-T004 — Discover SDK and EAIS account scopes

- **Status / owner:** done / A03 adapter
- **Story:** ST-OLL-003; **depends on:** M6-T001.
- **Requirements:** FR-ACC-001, FR-ACC-004, FR-ACC-006.
- **Acceptance:** AC-LIVE-003; M6: M6-A03.
- **Work:** Use official owner-controlled flows to document each account or shared/team relationship, aliases and key permissions.
- **Done when:** Two real outcomes or documented actual relationship, captured once privately with no credentials in evidence.
- **Verification:** official account and team views; owner-guided once.
- **Evidence:** [m6-delivery-checkpoint-2026-11-03.md](../../../docs/evidence/m6-delivery-checkpoint-2026-11-03.md).

Technical result: [10 November completion evidence](../../evidence/m6-technical-completion-2026-11-10.md).

### M6-T005 — Validate official cloud balance behavior

- **Status / owner:** done / A03 adapter
- **Story:** ST-OLL-004; **depends on:** M6-T004.
- **Requirements:** FR-QUOTA-006, FR-COL-007.
- **Acceptance:** AC-LIVE-005, AC-OPS-006; M6: M6-A04, M6-A09.
- **Work:** Discover GET /api/balance access and real account variants, reset times, rate limits and display precision against provider UI.
- **Done when:** Each available scope has source/version/role/field/side-effect decision and reconciliation; unavailable remains explicit.
- **Verification:** bounded official read-only balance request through approved credentials.
- **Evidence:** [m6-delivery-checkpoint-2026-11-03.md](../../../docs/evidence/m6-delivery-checkpoint-2026-11-03.md).

Technical result: [10 November completion evidence](../../evidence/m6-technical-completion-2026-11-10.md).

### M6-T006 — Freeze capability and contract decisions

- **Status / owner:** done / M6 integration steward
- **Story:** ST-OLL-001; **depends on:** M6-T004, M6-T005.
- **Requirements:** FR-ACC-004, FR-COL-004, FR-COL-006.
- **Acceptance:** AC-V1-002, AC-UI-006; M6: M6-A09.
- **Work:** Publish cloud capability decisions, source/version/rate, identity, contracts, migration and M7 boundary. Local capability decisions are deferred.
- **Done when:** Every active cloud lane has a source decision and contract impact under the existing approved cloud plan.
- **Verification:** python3 tools/automation/run.py AUTO-PLAN-CHECK; python3 tools/automation/run.py AUTO-DOCS-CHECK.
- **Evidence:** [m6-ollama-cloud-implementation-change.md](../../../docs/plans/integration/m6-ollama-cloud-implementation-change.md), [m6-recovery-evidence-contract-impact.md](../../../docs/plans/integration/m6-recovery-evidence-contract-impact.md), [m6-ollama-local-vertical-change.md](../../../docs/plans/integration/m6-ollama-local-vertical-change.md), [m6-ollama-process-implementation-change.md](../../../docs/plans/integration/m6-ollama-process-implementation-change.md), [m6-local-ollama-deferral-2026-11-04.md](../../../docs/plans/integration/m6-local-ollama-deferral-2026-11-04.md).

Technical result: [10 November completion evidence](../../evidence/m6-technical-completion-2026-11-10.md).

### M6-T007 — Define canonical M6 completion gate

- **Status / owner:** done / M6 integration steward
- **Story:** ST-OLL-005; **depends on:** M6-T006.
- **Requirements:** FR-COL-008.
- **Acceptance:** AC-TEST-001, AC-TEST-006; M6: M6-A10.
- **Work:** Build versioned M6 completeness catalog and canonical AUTO-M6-EXIT before dependent closure; test blocked/failed/missing evidence.
- **Done when:** Gate checks eight active M6 acceptance IDs and four active stories, rejects missing/skipped cloud evidence, and emits one scope-bound sanitized receipt; deferred local IDs are never counted Passed.
- **Verification:** python3 tools/automation/run.py AUTO-M6-EXIT.
- **Evidence:** [m6-exit-catalog-v1.json](../../../tools/automation/m6-exit-catalog-v1.json), [auto_m6_exit.py](../../../tools/automation/implementations/auto_m6_exit.py), [m6-local-ollama-deferral-2026-11-04.md](../../../docs/plans/integration/m6-local-ollama-deferral-2026-11-04.md).

Technical result: [10 November completion evidence](../../evidence/m6-technical-completion-2026-11-10.md).

### M6-T008 — Implement cloud capability admission

- **Status / owner:** done / A03 adapter
- **Story:** ST-OLL-001; **depends on:** M6-T006.
- **Requirements:** FR-ACC-005, FR-COL-004.
- **Acceptance:** AC-LIVE-004, AC-TEST-001; M6: M6-A09.
- **Work:** Admit the cloud provider capability and exact official balance source independently of local CLI or daemon installation.
- **Done when:** Cloud lane enforces its supported source/version and pre-I/O refusal policy without requiring local Ollama installation.
- **Verification:** cloud source policy and security tests; real cloud account verification.
- **Evidence:** [m6-ollama-local-preview-2026-11-01.md](../../../docs/evidence/m6-ollama-local-preview-2026-11-01.md), [m6-delivery-checkpoint-2026-11-03.md](../../../docs/evidence/m6-delivery-checkpoint-2026-11-03.md), [m6-native-usd-account-ui-2026-11-03.md](../../../docs/evidence/m6-native-usd-account-ui-2026-11-03.md), [m6-local-ollama-deferral-2026-11-04.md](../../../docs/plans/integration/m6-local-ollama-deferral-2026-11-04.md).

Technical result: [10 November completion evidence](../../evidence/m6-technical-completion-2026-11-10.md).

### M6-T010 — Integrate accounts, identity and authentication health

- **Status / owner:** done / M02 Registry + A03
- **Story:** ST-OLL-003; **depends on:** M6-T004, M6-T006, M6-T008.
- **Requirements:** FR-ACC-001, FR-ACC-002, FR-ACC-003, FR-AUTH-001.
- **Acceptance:** AC-LIVE-003, AC-UI-005; M6: M6-A01, M6-A03.
- **Work:** Use provider-neutral registry CRUD for SDK/EAIS aliases and source-backed identity/auth; preserve unknown and existing history.
- **Done when:** User can add, assign and enable accounts, with verified/unresolved/auth-required status and no hardcoded accounts.
- **Verification:** real SQLite/API and real account identity checks (to be defined).
- **Evidence:** [m6-delivery-checkpoint-2026-11-03.md](../../../docs/evidence/m6-delivery-checkpoint-2026-11-03.md).

Technical result: [10 November completion evidence](../../evidence/m6-technical-completion-2026-11-10.md).

### M6-T011 — Map real cloud balance and legacy windows

- **Status / owner:** done / A03 adapter + M05
- **Story:** ST-OLL-004; **depends on:** M6-T005, M6-T006, M6-T010.
- **Requirements:** FR-QUOTA-001, FR-QUOTA-004, FR-COL-003.
- **Acceptance:** AC-LIVE-005, AC-OPS-006; M6: M6-A04.
- **Work:** Map official balance variants with exact decimal money, native legacy windows, scope and reset; enforce shared account limit and 429 backoff.
- **Done when:** Owner-visible real data reconciles within documented precision and lag; included/purchased/shared not conflated.
- **Verification:** pure mapping tests plus real cloud reconciliation (to be defined).
- **Evidence:** [m6-delivery-checkpoint-2026-11-03.md](../../../docs/evidence/m6-delivery-checkpoint-2026-11-03.md).

Technical result: [10 November completion evidence](../../evidence/m6-technical-completion-2026-11-10.md).

### M6-T012 — Persist capacity history and alert events

- **Status / owner:** done / M04 collection + M05 capacity + M07 alerts
- **Story:** ST-OLL-004; **depends on:** M6-T011.
- **Requirements:** FR-COL-005, FR-COL-008.
- **Acceptance:** AC-HIST-001, AC-ALERT-002; M6: M6-A05.
- **Work:** Commit real source observations idempotently to existing capacity history and derive configured alerts.
- **Done when:** Real account reading reaches API, history, chart and genuine alert lifecycle as available; duplicate processing does not duplicate observation.
- **Verification:** real SQLite, HTTP and built-browser history/alert tests (to be defined).
- **Evidence:** [m6-delivery-checkpoint-2026-11-03.md](../../../docs/evidence/m6-delivery-checkpoint-2026-11-03.md).

Technical result: [10 November completion evidence](../../evidence/m6-technical-completion-2026-11-10.md).

### M6-T014 — Implement dashboard views and provider filter

- **Status / owner:** done / P02 dashboard
- **Story:** ST-OLL-005; **depends on:** M6-T010, M6-T011.
- **Requirements:** FR-ACC-002, FR-COL-006.
- **Acceptance:** AC-UI-002, AC-UI-003, AC-UI-004, AC-UI-005, AC-UI-006; M6: M6-A01, M6-A08.
- **Work:** Render cloud Ollama account, organization, resource type, balances/windows, source, freshness and failure states via versioned API. Local model/process views are deferred.
- **Done when:** Real Overview/detail/filter/history accessible on desktop and mobile; no placeholder values; existing promotion retained.
- **Verification:** npm --prefix frontend run typecheck; real dashboard browser checks (to be defined).
- **Evidence:** [m6-ollama-local-preview-2026-11-01.md](../../../docs/evidence/m6-ollama-local-preview-2026-11-01.md), [m6-delivery-checkpoint-2026-11-03.md](../../../docs/evidence/m6-delivery-checkpoint-2026-11-03.md), [m6-native-usd-account-ui-2026-11-03.md](../../../docs/evidence/m6-native-usd-account-ui-2026-11-03.md), [m6-local-ollama-deferral-2026-11-04.md](../../../docs/plans/integration/m6-local-ollama-deferral-2026-11-04.md).

Technical result: [10 November completion evidence](../../evidence/m6-technical-completion-2026-11-10.md).

### M6-T015 — Verify cloud failure isolation and recovery

- **Status / owner:** done / M6 integration steward
- **Story:** ST-OLL-005; **depends on:** M6-T010, M6-T011, M6-T014.
- **Requirements:** FR-COL-003, FR-COL-006.
- **Acceptance:** AC-LIVE-007, AC-OPS-003; M6: M6-A07.
- **Work:** Verify real natural cloud failure/recovery or the approved single isolated-network collector request followed by normal scheduled recovery, with Claude/Codex/dashboard continuity. No account configuration, user-agent or host-network changes. Local-daemon tests remain deferred.
- **Done when:** Exact target/binding/source and run lineage proves real failure then recovery with dashboard and Claude/Codex continuity; controlled namespace ownership and cleanup are witnessed separately from natural provider errors. Missing real evidence remains Blocked/Not Run.
- **Verification:** AUTO-M6-EXIT: natural or controlled recovery producer, actual namespace/lock tests, versioned API and rendered dashboard probes.
- **Evidence:** [m6-delivery-checkpoint-2026-11-03.md](../../../docs/evidence/m6-delivery-checkpoint-2026-11-03.md), [m6-local-ollama-deferral-2026-11-04.md](../../../docs/plans/integration/m6-local-ollama-deferral-2026-11-04.md).

The [approved controlled-recovery amendment](m6-cloud-controlled-recovery-proposal-2026-11-04.md) governs this bounded alternative. Implementation and live execution are recorded separately.

Technical result: [10 November completion evidence](../../evidence/m6-technical-completion-2026-11-10.md).

### M6-T016 — Security, compatibility and dependency review

- **Status / owner:** done / M6 integration steward
- **Story:** ST-OLL-005; **depends on:** M6-T006, M6-T010, M6-T011.
- **Requirements:** FR-SAFE-001, FR-SAFE-002, FR-COL-007.
- **Acceptance:** AC-V1-005, AC-V1-007, AC-PROC-004; M6: M6-A09.
- **Work:** Review cloud request scopes, secrets, fields, rate limits, default-profile integrity, dependencies/license and versioned contracts; local-specific acceptance moves to the future backlog.
- **Done when:** Review names each finding and resolution; no mandatory security/privacy blocker remains; no new dependency without approval.
- **Verification:** python3 tools/automation/run.py AUTO-QUALITY; bounded source and existing-evidence security/privacy review.
- **Evidence:** [m6-delivery-checkpoint-2026-11-03.md](../../../docs/evidence/m6-delivery-checkpoint-2026-11-03.md), [m6-security-privacy-review-2026-11-04.md](../../../docs/evidence/m6-security-privacy-review-2026-11-04.md), [m6-local-ollama-deferral-2026-11-04.md](../../../docs/plans/integration/m6-local-ollama-deferral-2026-11-04.md).

Technical result: [10 November completion evidence](../../evidence/m6-technical-completion-2026-11-10.md).

### M6-T017 — Run live end-to-end M6 scenarios

- **Status / owner:** done / M6 integration steward
- **Story:** ST-OLL-005; **depends on:** M6-T007, M6-T012, M6-T014, M6-T015, M6-T016.
- **Requirements:** FR-COL-004, FR-COL-008.
- **Acceptance:** AC-LIVE-004, AC-LIVE-005, AC-HIST-001, AC-TEST-003, AC-TEST-006; M6: M6-A04, M6-A05, M6-A08.
- **Work:** Run the active cloud test catalog and source-to-history/dashboard comparisons across SDK and EAIS; local models/processes are excluded by the owner decision.
- **Done when:** Record exact observed pass/block outcomes, no hidden skips and no repeated owner attestations for unchanged evidence.
- **Verification:** python3 tools/automation/run.py AUTO-M6-EXIT.
- **Evidence:** [m6-delivery-checkpoint-2026-11-03.md](../../../docs/evidence/m6-delivery-checkpoint-2026-11-03.md), [m6-local-ollama-deferral-2026-11-04.md](../../../docs/plans/integration/m6-local-ollama-deferral-2026-11-04.md).

Technical result: [10 November completion evidence](../../evidence/m6-technical-completion-2026-11-10.md).

### M6-T018 — Deploy, operate and close M6

- **Status / owner:** in_progress / M6 integration steward
- **Story:** ST-OLL-005; **depends on:** M6-T017.
- **Requirements:** FR-SAFE-002, FR-COL-008.
- **Acceptance:** AC-OPS-003, AC-TEST-006; M6: M6-A10.
- **Work:** Run canonical gate, one bounded independent review, safe dashboard rollout/rollback and owner demonstration; record acceptance.
- **Done when:** Gate passed at exact revision, service responds, promotion retained, runbook updated, owner reviews once; M7/M8 remain separate.
- **Verification:** python3 tools/automation/run.py AUTO-M6-EXIT; python3 tools/automation/run.py AUTO-DOCS-CHECK.
- **Evidence:** [m6-delivery-checkpoint-2026-11-03.md](../../../docs/evidence/m6-delivery-checkpoint-2026-11-03.md), [m6-local-ollama-deferral-2026-11-04.md](../../../docs/plans/integration/m6-local-ollama-deferral-2026-11-04.md).

Technical result: [10 November completion evidence](../../evidence/m6-technical-completion-2026-11-10.md).
