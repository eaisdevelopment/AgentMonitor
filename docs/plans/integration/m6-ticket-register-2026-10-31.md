# M6 ticket register

**State: implementation in progress.** M6-T001 and M6-T002 are done. Other implementation and verification tickets are in progress except M6-T003, whose real model-host evidence remains pending. See the [3 November delivery checkpoint](../../evidence/m6-delivery-checkpoint-2026-11-03.md) for deployed results and remaining work. The local adapter/API/dashboard candidate has narrow real-system evidence; the canonical M6 technical-exit orchestrator directly runs the available checks but does not yet have all required real outcomes, M6-A10 remains pending, and cloud work remains unfinished.

The machine-readable [ticket catalog](m6-ticket-catalog-v1.json) is the source for the IDs and links below. Validate it with `python3 tools/planning/validate_m6_tickets.py --stage plan`. The validator rejects a completed ticket whose prerequisite is unfinished. It does not verify the substance of linked evidence or establish milestone completion. See the [execution plan](m6-execution-plan-2026-10-31.md) for the acceptance criteria M6-A01–M6-A10, assumptions, scope control and risks.

| ID | Story | Ticket | Depends on | Hours |
|---|---|---|---|---:|
| M6-T001 | ST-OLL-001 | Reconcile implementation baseline | — | 3–5 |
| M6-T002 | ST-OLL-001 | Inventory local Ollama installation | M6-T001 | 2–4 |
| M6-T003 | ST-OLL-002 | Verify model-host read-only access | M6-T002 | 3–5 |
| M6-T004 | ST-OLL-003 | Discover SDK and EAIS account scopes | M6-T001 | 3–5 |
| M6-T005 | ST-OLL-004 | Validate official cloud balance behavior | M6-T004 | 3–5 |
| M6-T006 | ST-OLL-001 | Freeze capability and contract decisions | M6-T002, M6-T003, M6-T004, M6-T005 | 4–6 |
| M6-T007 | ST-OLL-005 | Define canonical M6 completion gate | M6-T006 | 3–5 |
| M6-T008 | ST-OLL-001 | Implement installation and capability admission | M6-T006 | 4–6 |
| M6-T009 | ST-OLL-002 | Implement local catalog and loaded-model observation | M6-T003, M6-T008 | 5–8 |
| M6-T010 | ST-OLL-003 | Integrate accounts, identity and authentication health | M6-T004, M6-T006, M6-T008 | 5–8 |
| M6-T011 | ST-OLL-004 | Map real cloud balance and legacy windows | M6-T005, M6-T006, M6-T010 | 6–10 |
| M6-T012 | ST-OLL-004 | Persist capacity history and alert events | M6-T011 | 4–6 |
| M6-T013 | ST-OLL-005 | Discover real Ollama processes and correlation | M6-T003, M6-T008 | 6–10 |
| M6-T014 | ST-OLL-005 | Implement dashboard views and provider filter | M6-T009, M6-T010, M6-T011, M6-T013 | 6–9 |
| M6-T015 | ST-OLL-005 | Verify failure isolation and natural recovery | M6-T009, M6-T010, M6-T011, M6-T014 | 3–5 |
| M6-T016 | ST-OLL-005 | Security, compatibility and dependency review | M6-T006, M6-T009, M6-T010, M6-T011, M6-T013 | 4–6 |
| M6-T017 | ST-OLL-005 | Run live end-to-end M6 scenarios | M6-T007, M6-T012, M6-T013, M6-T014, M6-T015, M6-T016 | 5–8 |
| M6-T018 | ST-OLL-005 | Deploy, operate and close M6 | M6-T017 | 4–7 |

**Total: 73–118 engineering hours**, preliminary; revise after real account and model-host discovery.

## Ticket details

### M6-T001 — Reconcile implementation baseline

- **Status / owner:** done / M6 integration steward
- **Story:** ST-OLL-001; **depends on:** none.
- **Requirements:** FR-COL-008.
- **Acceptance:** AC-V1-002; M6: M6-A10.
- **Work:** Select one clean branch containing accepted M5 and the current dashboard, preserve both branch histories and receipt; document conflicts, service revision and rollback.
- **Done when:** A reviewable merge/baseline exists; M5 receipt and promotion remain intact; real dashboard remains reachable.
- **Verification:** git status --short --branch; git log --oneline --graph --all -30.
- **Evidence:** [merged baseline and live dashboard check](../../evidence/m6-baseline-discovery-2026-11-01.md).

### M6-T002 — Inventory local Ollama installation

- **Status / owner:** done / A03 adapter
- **Story:** ST-OLL-001; **depends on:** M6-T001.
- **Requirements:** FR-ACC-005, FR-DISC-008.
- **Acceptance:** AC-LIVE-004; M6: M6-A02.
- **Work:** Record real CLI and daemon version, trusted host, process ownership and response bounds without profile or agent mutation.
- **Done when:** Local version and availability have sanitized real evidence; missing or mismatched service is explicit.
- **Verification:** ollama --version.
- **Evidence:** [local installation and canonical admission results](../../evidence/m6-delivery-checkpoint-2026-11-03.md): real CLI/server 0.24.0, present installation, and AUTO-M6-LOCAL-ADMIT passed at `9ac684c`; model-present host evidence remains M6-T003.

### M6-T003 — Verify model-host read-only access

- **Status / owner:** planned / A03 adapter
- **Story:** ST-OLL-002; **depends on:** M6-T002.
- **Requirements:** FR-DISC-003, FR-SAFE-002.
- **Acceptance:** AC-PROC-001, AC-PROC-004; M6: M6-A02, M6-A09.
- **Work:** Confirm owner-selected remote host and safe access to existing model; document exposed surface, authentication and transport before requests.
- **Done when:** One approved reachable real host and model state, or specific documented blocker; no daemon change or LAN exposure.
- **Verification:** read-only host and API discovery; exact command selected after host/trust review.
- **Evidence:** not yet recorded.

### M6-T004 — Discover SDK and EAIS account scopes

- **Status / owner:** in progress / A03 adapter
- **Story:** ST-OLL-003; **depends on:** M6-T001.
- **Requirements:** FR-ACC-001, FR-ACC-004, FR-ACC-006.
- **Acceptance:** AC-LIVE-003; M6: M6-A03.
- **Work:** Use official owner-controlled flows to document each account or shared/team relationship, aliases and key permissions.
- **Done when:** Two real outcomes or documented actual relationship, captured once privately with no credentials in evidence.
- **Verification:** official account and team views; owner-guided once.
- **Evidence:** [3 November implementation checkpoint](../../evidence/m6-delivery-checkpoint-2026-11-03.md); remaining acceptance is explicit.

### M6-T005 — Validate official cloud balance behavior

- **Status / owner:** in progress / A03 adapter
- **Story:** ST-OLL-004; **depends on:** M6-T004.
- **Requirements:** FR-QUOTA-006, FR-COL-007.
- **Acceptance:** AC-LIVE-005, AC-OPS-006; M6: M6-A04, M6-A09.
- **Work:** Discover GET /api/balance access and real account variants, reset times, rate limits and display precision against provider UI.
- **Done when:** Each available scope has source/version/role/field/side-effect decision and reconciliation; unavailable remains explicit.
- **Verification:** bounded official read-only balance request through approved credentials.
- **Evidence:** [3 November implementation checkpoint](../../evidence/m6-delivery-checkpoint-2026-11-03.md); remaining acceptance is explicit.

### M6-T006 — Freeze capability and contract decisions

- **Status / owner:** in progress / M6 integration steward
- **Story:** ST-OLL-001; **depends on:** M6-T002, M6-T003, M6-T004, M6-T005.
- **Requirements:** FR-ACC-004, FR-COL-004, FR-COL-006.
- **Acceptance:** AC-V1-002, AC-UI-006; M6: M6-A09.
- **Work:** Publish capability matrix and update A03 plan, data flow, source/version/rate, identity, contracts, migration and A03-M7 boundary.
- **Done when:** Every enabled lane has source decision and contract impact; owner approves exact implementation plan.
- **Verification:** python3 tools/automation/run.py AUTO-PLAN-CHECK; python3 tools/automation/run.py AUTO-DOCS-CHECK.
- **Evidence:** not yet recorded.

### M6-T007 — Define canonical M6 completion gate

- **Status / owner:** in progress / M6 integration steward
- **Story:** ST-OLL-005; **depends on:** M6-T006.
- **Requirements:** FR-COL-008.
- **Acceptance:** AC-TEST-001, AC-TEST-006; M6: M6-A10.
- **Work:** Build versioned M6 completeness catalog and canonical AUTO-M6-EXIT before dependent closure; test blocked/failed/missing evidence.
- **Done when:** Gate checks M6-A01..A10 and five story deliverables, rejects skipped/missing evidence, emits one sanitized receipt; no repeated owner copy-paste.
- **Verification:** `python3 tools/automation/run.py AUTO-M6-EXIT`.
- **Evidence:** [versioned completeness catalog](../../../tools/automation/m6-exit-catalog-v1.json) and canonical command implementation; a complete passing real run remains Not Run.

### M6-T008 — Implement installation and capability admission

- **Status / owner:** in progress / A03 adapter
- **Story:** ST-OLL-001; **depends on:** M6-T006.
- **Requirements:** FR-ACC-005, FR-DISC-008.
- **Acceptance:** AC-LIVE-004, AC-TEST-001; M6: M6-A02, M6-A09.
- **Work:** Implement provider manifest and installation discovery with separate client/daemon versions, source and compatibility.
- **Done when:** Each lane independently admits exact supported version/source; invalid lane fails before I/O; real installation produces provenance.
- **Verification:** adapter pure policy tests; real installation test (to be defined).
- **Evidence:** [local preview](../../evidence/m6-ollama-local-preview-2026-11-01.md); installation discovery is now wired and the real local admission passed at `9ac684c`; see the [current checkpoint](../../evidence/m6-delivery-checkpoint-2026-11-03.md). Populated-model and second-host acceptance remain pending.

### M6-T009 — Implement local catalog and loaded-model observation

- **Status / owner:** in progress / A03 adapter
- **Story:** ST-OLL-002; **depends on:** M6-T003, M6-T008.
- **Requirements:** FR-DISC-003, FR-COL-004.
- **Acceptance:** AC-UI-005, AC-LIVE-004; M6: M6-A02.
- **Work:** Use bounded local GET version/tags/ps sources, map installed and loaded models with source/time and real empty/offline states.
- **Done when:** Actual empty and real model-present cases render distinctly; no inference/loading request or mutation.
- **Verification:** real local service integration tests and browser checks (to be defined).
- **Evidence:** [local preview](../../evidence/m6-ollama-local-preview-2026-11-01.md); populated models and natural failure remain unverified.

### M6-T010 — Integrate accounts, identity and authentication health

- **Status / owner:** in progress / M02 Registry + A03
- **Story:** ST-OLL-003; **depends on:** M6-T004, M6-T006, M6-T008.
- **Requirements:** FR-ACC-001, FR-ACC-002, FR-ACC-003, FR-AUTH-001.
- **Acceptance:** AC-LIVE-003, AC-UI-005; M6: M6-A01, M6-A03.
- **Work:** Use provider-neutral registry CRUD for SDK/EAIS aliases and source-backed identity/auth; preserve unknown and existing history.
- **Done when:** User can add, assign and enable accounts, with verified/unresolved/auth-required status and no hardcoded accounts.
- **Verification:** real SQLite/API and real account identity checks (to be defined).
- **Evidence:** [3 November implementation checkpoint](../../evidence/m6-delivery-checkpoint-2026-11-03.md); remaining acceptance is explicit.

### M6-T011 — Map real cloud balance and legacy windows

- **Status / owner:** in progress / A03 adapter + M05
- **Story:** ST-OLL-004; **depends on:** M6-T005, M6-T006, M6-T010.
- **Requirements:** FR-QUOTA-001, FR-QUOTA-004, FR-COL-003.
- **Acceptance:** AC-LIVE-005, AC-OPS-006; M6: M6-A04.
- **Work:** Map official balance variants with exact decimal money, native legacy windows, scope and reset; enforce shared account limit and 429 backoff.
- **Done when:** Owner-visible real data reconciles within documented precision and lag; included/purchased/shared not conflated.
- **Verification:** pure mapping tests plus real cloud reconciliation (to be defined).
- **Evidence:** [3 November implementation checkpoint](../../evidence/m6-delivery-checkpoint-2026-11-03.md); remaining acceptance is explicit.

### M6-T012 — Persist capacity history and alert events

- **Status / owner:** in progress / M04 collection + M05 capacity + M07 alerts
- **Story:** ST-OLL-004; **depends on:** M6-T011.
- **Requirements:** FR-COL-005, FR-COL-008.
- **Acceptance:** AC-HIST-001, AC-ALERT-002; M6: M6-A05.
- **Work:** Commit real source observations idempotently to existing capacity history and derive configured alerts.
- **Done when:** Real account reading reaches API, history, chart and genuine alert lifecycle as available; duplicate processing does not duplicate observation.
- **Verification:** real SQLite, HTTP and built-browser history/alert tests (to be defined).
- **Evidence:** [3 November implementation checkpoint](../../evidence/m6-delivery-checkpoint-2026-11-03.md); remaining acceptance is explicit.

### M6-T013 — Discover real Ollama processes and correlation

- **Status / owner:** in progress / M06 runtime + Linux platform
- **Story:** ST-OLL-005; **depends on:** M6-T003, M6-T008.
- **Requirements:** FR-DISC-001, FR-DISC-004, FR-SAFE-002.
- **Acceptance:** AC-PROC-001, AC-PROC-002, AC-PROC-003, AC-PROC-004; M6: M6-A06.
- **Work:** Read approved process metadata, distinguish loaded model and active client, preserve evidence-backed hierarchy and unresolved links.
- **Done when:** Representative real processes display correct sampled state/paths where permitted; no environment, prompt, response, source or process mutation.
- **Verification:** real Linux process and provider checks (to be defined).
- **Evidence:** [3 November implementation checkpoint](../../evidence/m6-delivery-checkpoint-2026-11-03.md); remaining acceptance is explicit.

### M6-T014 — Implement dashboard views and provider filter

- **Status / owner:** in progress / P02 dashboard
- **Story:** ST-OLL-005; **depends on:** M6-T009, M6-T010, M6-T011, M6-T013.
- **Requirements:** FR-ACC-002, FR-COL-006.
- **Acceptance:** AC-UI-002, AC-UI-003, AC-UI-004, AC-UI-005, AC-UI-006; M6: M6-A01, M6-A08.
- **Work:** Render Ollama account, organization, resource type, values, source, freshness, model/process and failure states via versioned API.
- **Done when:** Real Overview/detail/filter/history accessible on desktop and mobile; no placeholder values; existing promotion retained.
- **Verification:** npm --prefix frontend run typecheck; real dashboard browser checks (to be defined).
- **Evidence:** [local preview](../../evidence/m6-ollama-local-preview-2026-11-01.md); the [native USD account/history browser check](../../evidence/m6-native-usd-account-ui-2026-11-03.md) and installed Overview now show fresh real monetary values; remaining account-scope and model-host acceptance are explicit in the [checkpoint](../../evidence/m6-delivery-checkpoint-2026-11-03.md).

### M6-T015 — Verify failure isolation and natural recovery

- **Status / owner:** in progress / M6 integration steward
- **Story:** ST-OLL-005; **depends on:** M6-T009, M6-T010, M6-T011, M6-T014.
- **Requirements:** FR-COL-003, FR-COL-006.
- **Acceptance:** AC-LIVE-007, AC-OPS-003; M6: M6-A07.
- **Work:** Exercise available real auth/offline/throttle/recovery conditions without stopping a user service, and verify Claude/Codex/dashboard continuity.
- **Done when:** Observed conditions pass with source/time; absent natural conditions remain Blocked/Not Run without simulation.
- **Verification:** real service and provider failure-isolation checks (to be defined).
- **Evidence:** [3 November implementation checkpoint](../../evidence/m6-delivery-checkpoint-2026-11-03.md); remaining acceptance is explicit.

### M6-T016 — Security, compatibility and dependency review

- **Status / owner:** in progress / M6 integration steward
- **Story:** ST-OLL-005; **depends on:** M6-T006, M6-T009, M6-T010, M6-T011, M6-T013.
- **Requirements:** FR-SAFE-001, FR-SAFE-002, FR-COL-007.
- **Acceptance:** AC-V1-005, AC-V1-007, AC-PROC-004; M6: M6-A09.
- **Work:** Review request scopes, secrets, allowed fields, no default-profile mutation, no agent control, dependencies/license and versioned contracts.
- **Done when:** Review names each finding and resolution; no mandatory security/privacy blocker remains; no new dependency without approval.
- **Verification:** python3 tools/automation/run.py AUTO-QUALITY; project privacy/security review (to be defined).
- **Evidence:** [3 November implementation checkpoint](../../evidence/m6-delivery-checkpoint-2026-11-03.md); remaining acceptance is explicit.

### M6-T017 — Run live end-to-end M6 scenarios

- **Status / owner:** in progress / M6 integration steward
- **Story:** ST-OLL-005; **depends on:** M6-T007, M6-T012, M6-T013, M6-T014, M6-T015, M6-T016.
- **Requirements:** FR-COL-004, FR-COL-008.
- **Acceptance:** AC-LIVE-004, AC-LIVE-005, AC-HIST-001, AC-TEST-003, AC-TEST-006; M6: M6-A02, M6-A04, M6-A05, M6-A06, M6-A08.
- **Work:** Run fixed real test catalog and source-to-history/dashboard comparisons across SDK, EAIS and model host.
- **Done when:** Record exact observed pass/block outcomes, no hidden skips and no repeated owner attestations for unchanged evidence.
- **Verification:** `python3 tools/automation/run.py AUTO-M6-EXIT`.
- **Evidence:** [3 November implementation checkpoint](../../evidence/m6-delivery-checkpoint-2026-11-03.md); remaining acceptance is explicit.

### M6-T018 — Deploy, operate and close M6

- **Status / owner:** in progress / M6 integration steward
- **Story:** ST-OLL-005; **depends on:** M6-T017.
- **Requirements:** FR-SAFE-002, FR-COL-008.
- **Acceptance:** AC-OPS-003, AC-TEST-006; M6: M6-A10.
- **Work:** Run canonical gate, one bounded independent review, safe dashboard rollout/rollback and owner demonstration; record acceptance.
- **Done when:** Gate passed at exact revision, service responds, promotion retained, runbook updated, owner reviews once; M7/M8 remain separate.
- **Verification:** `python3 tools/automation/run.py AUTO-M6-EXIT`; `python3 tools/automation/run.py AUTO-DOCS-CHECK`.
- **Evidence:** [3 November implementation checkpoint](../../evidence/m6-delivery-checkpoint-2026-11-03.md); remaining acceptance is explicit.
