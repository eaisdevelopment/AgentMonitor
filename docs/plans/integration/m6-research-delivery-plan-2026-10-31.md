# M6 Ollama — research and delivery plan

**Status:** research and task proposal, 31 October 2026; implementation not
approved by this document. **Primary owner:** A03 Ollama provider adapter;
P02, M02–M06, P01, Linux platform and operations own their existing boundaries.
**Goal:** a useful, accurate view of local Ollama and supported cloud account
capacity, integrated with the existing dashboard without disturbing running
agents. M6 is not the full V1 release.

## What we know now

- On this workstation, read-only requests to `127.0.0.1:11434` succeeded:
  `/api/version` reported 0.24.0; `/api/tags` returned zero models and `/api/ps`
  returned zero loaded models at the time of the check. Empty is a real point
  in time, not proof the machine has never run a model. No model was loaded,
  generated, downloaded, or stopped during discovery.
- Ollama documents [GET /api/tags](https://docs.ollama.com/api/tags) for
  installed model inventory and [GET /api/ps](https://docs.ollama.com/api/ps)
  for models loaded into memory, including reported memory and VRAM sizes.
  Loaded is not equivalent to an actively working agent; the endpoints do not
  by themselves establish which user or client is using a model.
- Ollama documents [GET /api/balance](https://docs.ollama.com/api/balance)
  for included/purchased credits and period boundaries; legacy plans can
  instead return session and weekly remaining percentages. It documents
  [GET /api/usage](https://docs.ollama.com/api/cloud-usage) for scoped usage,
  time buckets and optional model grouping. Both document a per-user limit of
  10 requests/minute shared across keys and devices, suggest one-minute
  polling, and document `Retry-After` on 429. Live authorization, scope,
  exact fields and behavior for the owner's real accounts remain unverified.
- [Authentication](https://docs.ollama.com/api/authentication) distinguishes
  the local API from direct cloud API-key access. No key, account identity,
  default Ollama profile, or provider-controlled credential was read in this
  research. Cloud endpoint docs are evidence of a documented interface, not
  proof of access for these accounts.
- [Ollama's pricing explanation](https://ollama.com/blog/transparent-pricing)
  distinguishes new monthly credit plans from existing legacy plans. Do not
  assume all plans expose five-hour/week windows or all expose credits.
  [Current pricing](https://ollama.com/pricing) says team balances are shared;
  [cloud usage](https://docs.ollama.com/api/cloud-usage) distinguishes `self`
  and admin-only `team` scope. Do not double-count shared balances or infer
  scope from email. Public pricing is not a substitute for account data.
- The [existing A03 plan](../adapters/ollama/plan-v1.md) is Draft; no Ollama
  provider adapter was found in the checked implementation. The checked-in
  [M6 task breakdown](../../superpowers/plans/2026-09-19-agentmonitor-v1-m6-ollama-slice.md)
  has five stories but predates this endpoint research. Its fixture-like test
  examples must not override the real-system/no-fakes rules in `AGENTS.md`.
  The accepted M5 evidence lives on a different development branch than the
  base of this planning worktree; reconcile branch state before implementation.

## Scope and success criteria

M6 covers local Ollama service/version and model catalog/runtime, documented
Ollama account identity/relationship and cloud subscription capacity where
available, representative local process correlation, integrated UI/history/
alerts/health, and real verification. Separate local compute, cloud
subscription and API billing pools. Full organization/project API cost and
budget workflows remain M7; endpoint discovery for M6 must nevertheless
identify any shared source and avoid duplicating or double-counting it.

Contributes to `FR-ACC-001/004..006`, `FR-AUTH-001..006`,
`FR-QUOTA-001..006`, `FR-DISC-001..006/008`, `FR-COL-003..008`,
`FR-STATE-001/002/004`, `FR-SAFE-001/002`, `AC-LIVE-003..007`,
`AC-PROC-001..004`, `AC-HIST-001`, `AC-UI-002/005/006`,
`AC-OPS-003/006`, and `AC-TEST-001..006`. Universal release-wide acceptance,
365-day retention/restore and complete budget outcomes remain M8/M7 where
applicable. Exact M6 exit scenarios must be mapped to IDs before implementation.

## Ordered task list

1. **Reconcile the baseline and scope (ST-OLL-001).** Select the actual
   integration branch containing accepted M3–M5 and current dashboard changes;
   reconcile divergent histories without discarding either. Confirm exact
   requirements and M6 exit matrix, owner/contract ownership and product
   decisions. Deliver a short source-of-truth inventory and a bounded plan.
2. **Complete M0 local discovery (ST-OLL-001/002).** Record installed binary
   and daemon versions, trusted loopback endpoint and read-only `/api/version`,
   `/api/tags` and `/api/ps` schemas, bounds, error states, permissions and
   side effects. Record empty lists honestly. Compare local service and CLI
   versions and test independent unavailable/recovery conditions only if
   naturally available. Do not restart the daemon or change models.
3. **Complete cloud and identity discovery (ST-OLL-003/004).** Verify official
   `balance` and `usage` with owner-managed access, exact key role, identity,
   account/team relationship, response shapes, rate limits, plan/legacy
   variants and authoritative owner-visible comparison. The requirement is
   two intended identities *or a documented actual relationship*, not two
   invented accounts. Never log or persist credentials, raw provider payloads,
   prompts, or answers. Do not scrape undocumented routes without a separately
   reviewed, explicitly authorized decision. Unavailable data stays unknown.
4. **Freeze contracts and lane decisions (ST-OLL-001).** Update the A03 plan,
   provider capability matrix and shared contract-impact assessment. For each
   endpoint/version, define source, identity/scope, units, precision, exact
   amounts, timestamp, freshness, error/429/retry, trust boundary and supported/
   unsupported/unavailable state. Resolve the M6 balance versus M7 usage
   boundary and any migrations or ADR before implementation.
5. **Build the M6 completion command early (ST-OLL-005).** Define one canonical,
   finite, fail-closed command and real prerequisites, owned artifacts, clean
   revision binding and actionable output. Exercise missing/failed/zero-skip
   behavior before relying on it. Reuse prior owner evidence where valid; do
   not require repeated confirmation for every account or create chained
   one-off deployment gates. Keep the dashboard alive and preserve rollback.
6. **Implement installation and local catalog/runtime (ST-OLL-001/002).** TDD
   the adapter/manifest and independent capabilities; bounded read-only calls,
   version compatibility, explicit offline and empty states. Installed and
   loaded models are separate. Report provider-supplied memory fields with
   correct units; CPU/GPU utilization or queue counts only when evidenced by
   an approved real source, not inferred from VRAM or model presence.
7. **Implement identities and authentication health (ST-OLL-003).** Integrate
   approved sources with admin-managed Registry organizations/accounts and
   distinct resource IDs. Verify identities and relationships only with
   evidence; report unresolved and auth-required separately. No hardcoded
   accounts; no default-profile writes. Managed reauthentication is separately
   authorized only if discovery shows it is needed.
8. **Implement cloud capacity (ST-OLL-004).** Map real documented `balance`
   variants to the right plan and resource, retain included versus purchased
   balance and period, preserve native legacy windows and exact monetary
   precision. Poll under shared per-user limits, handle 429 and failure, and
   feed real M04/M05 history and alerts. If account/source/field cannot be
   verified, show its exact unavailable/unsupported state rather than a zero.
9. **Implement process evidence and association (ST-OLL-005).** Discover real
   Ollama-related processes with the Linux metadata boundary, distinguish
   loaded model from executing client, preserve hierarchy only where proven,
   show path when safely available, and require owner confirmation for
   ambiguous account links. Do not read prompts, responses, arbitrary
   environment values or source files; do not control agent processes.
10. **Finish UI and failure isolation (ST-OLL-005).** Add Ollama to account
    CRUD and provider filters, Overview, detail, history, alerts and operations
    through the versioned API. Show model/runtime and cloud capacity as
    separate resources, owner names, freshness and source. Test responsive
    layout, keyboard access, partial/unavailable/recovery states and continued
    Claude/Codex/dashboard operation when Ollama is unavailable.
11. **Verify real end-to-end behavior.** Record meaningful red/green evidence,
    run pure, real SQLite, HTTP, built browser and live adapter tests. Compare
    cloud values with the owner-visible source within measured lag/precision;
    validate two identities or their actual relationship and representative
    2–4 natural process/model cases where available. Empty local state can
    prove the empty case, not loaded-model coverage. Missing natural cases stay
    explicitly Blocked/Not Run; never simulate provider or telemetry data.
12. **Deliver and close.** Run the canonical M6 gate, static/quality/security/
    mutation/docs and privacy checks, update operating and recovery guidance,
    record scope, results, unavailable scenarios and owner review. Commit the
    work, preserve the previous service and account data, and hand off M7/M8
    work separately. Do not claim M6 passed unless its actual gate passes.

## Sequencing and dependencies

`1 → 2 + 3 → 4 → 5 → 6 + 7 → 8 + 9 → 10 → 11 → 12`. Local discovery can
progress while cloud access is unavailable; cloud availability must not stall
unrelated local capabilities. The current empty local model inventory blocks a
real loaded-model scenario until a naturally available model exists; do not
start/download one without an explicit owner decision. For cloud we need an
owner-selected account or documented account relationship, authorized key
setup inside the existing secure flow, and a way to compare against the
provider UI. Do not request credentials in chat.

**No schedule is promised.** Size, endpoint permissions, available accounts,
loaded-model coverage, source drift and branch reconciliation must be measured
before giving an ETA. First deliverable is the evidence/capability matrix and a
reviewable implementation plan, not repeated plan-version churn.

## Risks requiring explicit resolution

- The current plan's initial `two identities` wording can conflict with
  provider one-account-per-person terms; document the real organization/team
  relationship rather than demanding duplicate accounts.
- Balance and usage are distinct fields: credits are not a concurrency limit,
  usage is delayed, model groups can have a remainder, and legacy usage may
  lack cost fields. Currency must not pass through binary floating point.
- Ollama's API is [not strictly versioned](https://docs.ollama.com/api/introduction);
  record exact local/provider/schema versions and fail closed on breaking drift.
- Local `/api/ps` shows loaded models, not proven agent activity or total GPU
  utilization. Never infer a per-user account link from process proximity.
- Distinguish documented capability from live verified access. A naturally
  unavailable auth/throttle/recovery case is not a passed scenario.
- Existing accepted M5 belongs to a divergent branch; the live dashboard uses
  a separate worktree and a locally overlaid frontend. Reconciliation and a
  non-destructive, repeatable deployment/rollback are required before delivery.
