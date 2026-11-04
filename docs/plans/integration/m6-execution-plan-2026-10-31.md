# M6 execution plan: Ollama monitoring

**State:** Execution in progress under the owner-approved
[local](m6-ollama-local-vertical-change.md),
[cloud](m6-ollama-cloud-implementation-change.md) and
[process](m6-ollama-process-implementation-change.md) implementation plans.
Those scoped approvals authorize implementation; they do not establish live
acceptance or approve every historical discovery proposal.
**Date:** 31 October 2026. **Owner:** A03 Ollama adapter; the integration
steward owns cross-module contracts, deployment and the M6 completion command.
**Prerequisite:** M3 accepted; M5 accepted. This plan uses the real evidence in
[M6 research](m6-research-delivery-plan-2026-10-31.md), the existing
[A03 plan](../adapters/ollama/plan-v1.md), [M6 stories](../../superpowers/plans/2026-09-19-agentmonitor-v1-m6-ollama-slice.md),
[SDLC](../../engineering/sdlc.md), [completion gates](../../engineering/completion-and-automation-gates.md)
and [sub-agent runbook](../../engineering/subagent-runbook.md).

## 1. The outcome

From the existing dashboard an operator can register and organize Ollama
accounts, identify the local service and its available/loaded models, and see
verified cloud subscription balance or legacy limits for SDK and EAIS where
the official provider source and account roles allow it. The UI shows source,
observation time, uncertainty and freshness. It shows the actual relationship
between a process, model and account when evidence supports one; otherwise it
says unknown and allows existing owner-confirmed association mechanisms where
appropriate. Historical observations and real alerts use existing platform
capabilities. A provider failure does not bring down the dashboard or other
providers.

**Out of M6:** full API-budget/accounting dashboards and forecasts (M7), the
full V1 release, installation/backup/restore release program (M8), support
for macOS, synthetic monitoring data, and control of running processes. This
is a scope boundary, not permission to remove M6's original subscription,
identity, process, history, alert, or validation requirements.

## 2. Known live prerequisites and assumptions

| Item | Current evidence / assumption | Required action |
|---|---|---|
| Local server | This workstation: Ollama CLI/server 0.24.0; version, tags and ps respond; tags and ps returned zero models. | Preserve daemon. Verify empty-state. Owner subsequently identified this local machine as the model host; reconcile its actual endpoint and record real version and installed/loaded state. The earlier second-machine assumption is superseded. Never install, load or stop a model as a test. |
| Cloud accounts | Owner states SDK and EAIS cloud accounts are available. Account role, identity relationship, plan type and key permissions are unverified. | Arrange one owner-guided official authorization or approved key setup per required account; no passwords or keys in chat. Record aliases/scope privately and sanitized outcomes once. |
| Balance | Ollama documents `GET /api/balance` for included/purchased credits; legacy plan fields can be session/weekly limits. | Verify both real account types and authoritative UI; report actual variants, precision and sharing. No guessed ratios or resets. |
| Usage | Ollama documents `GET /api/usage`, self/team scope, 24h/7d/30d and model grouping. | Discover role, latency, precision and extent; M7 owns comprehensive cost/budget workflows. Do not silently count shared team usage twice. |
| Source limits | Both cloud endpoints document 10 requests/minute per user across keys/devices and `Retry-After`; local version is not assumed compatible forever. | One-minute or slower cloud cadence, per-user shared limiter and backoff; freeze exact bounds after live review. |
| Existing M5 | Accepted gate and dashboard promotion changes have different branches/worktrees; active dashboard serves a frontend overlay. | Reconcile histories into a clean integration branch before M6 code, preserving the accepted receipt and promotion. Do not assert the clean branch already exists. |

References: [Ollama local models](https://docs.ollama.com/api/tags),
[loaded models](https://docs.ollama.com/api/ps),
[cloud balance](https://docs.ollama.com/api/balance),
[cloud usage](https://docs.ollama.com/api/cloud-usage),
[authentication](https://docs.ollama.com/api/authentication), and
[plan changes](https://ollama.com/blog/transparent-pricing). Documentation is
not proof that a specific credential/account exposes the data.

## 3. Fixed acceptance catalog

These items form the M6 closure checklist used by `AUTO-M6-EXIT`. Each is assessed with the
real system; Failed, Blocked, Skipped, Unknown and Not Run are never marked
Passed. Existing V1 criteria are contributions, not universal release claims.

| ID | Observable acceptance | Evidence |
|---|---|---|
| M6-A01 | Ollama appears as a provider and can be added to existing organization/account administration without hardcoded account names. | Built dashboard, versioned API and real SQLite; `FR-ACC-001..005`, `AC-UI-002`. |
| M6-A02 | The local service shows version, installed models and loaded models separately; a zero list is not an error, and loaded does not imply working. | Real local Ollama on the owner-identified machine, including a genuine model-present observation and all registered host coverage, with sanitized version/time and read-only side-effect proof; `FR-DISC-001/003`, `AC-PROC-001/004`. |
| M6-A03 | SDK and EAIS accounts or their actual team/shared relationship are identified with owner-confirmed, non-secret aliases; unavailable/ambiguous roles stay explicit. | Real owner-guided source check, per-account outcome, `AC-LIVE-003`; no need to enumerate every agent. |
| M6-A04 | For each accessible account/scope, the native `balance` variant and timestamp are displayed and reconciled with the provider's authoritative view. Included and purchased balances and legacy windows remain distinct; team balance is not duplicated. | Real account/provider UI comparison with documented precision/lag; `AC-LIVE-005`, `FR-QUOTA-001/002/004/006`. No data or no documented access is explicitly unavailable/unsupported with evidence, not zero. |
| M6-A05 | New real observations reach capacity history and appropriate configured alerts; no duplicate event or silent stale-as-current display. | Real source → M04 → M05 → API → built UI and real alert lifecycle as naturally available; `AC-HIST-001`, `AC-ALERT-002`. |
| M6-A06 | Representative real Ollama-related processes/model relationships are shown where proven, with unresolved account links explicit. | Real platform/process evidence and sample model/processes on available hosts; `AC-PROC-001..004`. Process coverage is sampled and partial scanning must be disclosed. |
| M6-A07 | Provider offline/auth failure and recovery are truthful and do not interrupt the dashboard or Claude/Codex collection. | Natural real failure/recovery when available; otherwise Blocked/Not Run; `AC-LIVE-007`, `AC-OPS-003`. No deliberate daemon/agent stop. |
| M6-A08 | Existing dashboard remains responsive; product links and account features work, including mobile and keyboard. | Real built-browser tests; `AC-UI-003..006`. |
| M6-A09 | Local and cloud collection respects approved host/method/field scope, limits, privacy, profile integrity and exact source/version. | Privacy/security review and real read-only evidence, `FR-COL-003..008`, `FR-SAFE-002`, `AC-OPS-006`, `AC-TEST-001..006`. |
| M6-A10 | The exact implementation has one passing canonical M6 completion result, a reproducible operator runbook, explicit unsupported/blocked results, and the owner's review. | Canonical command and receipt, full-scope checks, documentation and owner decision. |

A missing live source or required natural state is not quietly waived. If a
source truly cannot provide a field, the capability decision and visible UI
must show that outcome. If a required scenario cannot be observed, record it as
Blocked and bring the exact impact to the owner once; do not invent data or
repeatedly ask for unrelated confirmations. Any scope change to this catalog
requires the owner's explicit decision.

## 4. Work packages and estimates

**Superseded package estimate:** this table was a first rough estimate. The
18-ticket [register](m6-ticket-register-2026-10-31.md) is authoritative for
the current **73–118 hour** estimate.

Estimates are **active engineering hours**, not guarantees. Range assumes one
engineer familiar with this repository, access to the two accounts and remote
model, no new dependency, and no breaking API or schema migration. Cloud
permissions, natural live conditions, external review, and owner availability
can add elapsed waiting time. The ranges are preliminary until packages 1–2
are complete; update the forecast at that checkpoint rather than promising a
calendar date now.

| # | Work package and evidence | Stories | Hours |
|---|---|---|---:|
| 1 | Reconcile current branches/worktrees; inspect real API/UI, freeze one integration baseline and preserve M5 receipt/promotion. | all | 3–5 |
| 2 | Safe local and cloud discovery: version/source matrix, SDK/EAIS identity and team scope, authenticated balance sample, real-model machine access, rate limits and privacy. | 001–004 | 6–10 |
| 3 | Update A03 module plan, contract impact, capability decisions, scenario/test map, gate/rollback plan and obtain owner approval of final bounded scope. | all | 6–10 |
| 4 | Implement versioned adapter admission and local service/catalog/runtime, real empty and model-present tests. | 001–002 | 8–12 |
| 5 | Implement owner-managed account/identity/auth and independently gated cloud balance/legacy windows with history/alerts. | 003–004 | 10–16 |
| 6 | Implement safe real process/model observation and explicit account correlation. | 005 | 6–10 |
| 7 | Integrate API/generated client only where needed, Overview/detail/history/health and responsive UI. | 005 | 8–12 |
| 8 | Execute real SQLite/HTTP/browser/provider tests, regressions, privacy/security, documented unavailable cases, and repair the known defect batch. | 001–005 | 6–10 |
| 9 | Canonical M6 gate, one bounded review, service rollout/rollback verification, runbook and owner handoff. | 005 | 4–7 |
| | **Total** | | **57–92 hours** (superseded by 73–118 ticket-level estimate) |

At six to seven focused engineering hours per workday this was roughly **9–16
working days**, plus external waiting. This is a planning range, not an ETA.
At the end of package 2, report elapsed hours, live-source findings, remaining
range and any concrete risk; if the upper bound or scope changes materially,
raise the reason and options then, instead of continuing silently for weeks.

## 5. Implementation sequence and ownership

1. **One integration owner** establishes the clean baseline and owns shared
   files, API, generated artifacts, service activation and final receipt.
2. **Discovery and planning:** local and cloud lanes can be investigated in
   parallel only with explicit independent ownership. A03 owns the adapter
   plan; Registry M02 owns identities, M03 provider protocol, M04 collection,
   M05 capacity, M06 runtime observation, P01 API and P02 dashboard. Shared
   contract decisions are synchronized before parallel implementation.
3. **One source decision per lane:** document `supported`, `unsupported`,
   `blocked`, or `experimental` with real evidence, owner, source/version,
   semantics, limits, privacy and allowed calls. No blanket approval of private
   endpoints or browser scraping. No new dependency without required review.
4. **Test-first implementation:** each changed behavior gets meaningful Red,
   Green and refactor evidence; external boundaries use real systems and
   provider data. Contract changes are versioned; breaking changes require an
   ADR and migration/rollback. No default profile changes.
5. **Deliver a visible vertical early:** local service plus real empty/loaded
   model state through API/UI, then cloud account/balance, then correlation,
   history and alert integration. Each is a working increment, not a claim of
   full M6 closure. Keep the running dashboard usable throughout.
6. **Stabilize once:** freeze acceptance catalog and known-defect batch. Run
   the existing canonical `AUTO-BUILD`, `AUTO-QUALITY`, `AUTO-DOCS-CHECK`,
   `AUTO-PLAN-CHECK` and applicable regression commands, plus a new canonical
   `AUTO-M6-EXIT` designed during package 3 and implemented before its phase is
   considered ready. One full final gate and one bounded independent review;
   rerun only after a genuine failure or relevant change. Do not create a new
   owner confirmation per deployment or pin an ever-growing list of one-off
   rollout revisions. Reuse valid evidence with truthful provenance and time.
7. **Release locally and hand off:** use a clean, reproducible source revision,
   atomic recoverable frontend/service rollout, health check and rollback. Do
   not kill/restart any user Ollama, Claude or Codex process. Verify dashboard
   is alive and the product promotion remains visible.

## 6. Test and evidence design

- **Pure domain:** balance variants, exact decimal USD, reset boundaries,
  provider precedence, scope/deduplication, 429/backoff, mapping and malformed
  input rejection. Constructed inputs allowed only without I/O.
- **Real boundaries:** real Ollama local servers and natural model states;
  official cloud endpoints with approved actual credentials; real file-backed
  SQLite, HTTP service and built browser. No mock/fake/recorded provider
  responses or seeded telemetry. Separate a test setup failure from a behavioral
  Red; record actual command, revision, result, timing and no skipped tests in
  the claimed gate.
- **Identity/security:** confirm the two real outcomes or documented shared
  relationship, verify protected default profiles stay intact, no secrets,
  prompts, responses, raw provider payloads or arbitrary process environment
  values in storage/logs/artifacts. Verify no hidden frontend third-party calls.
- **Dashboard acceptance:** demonstrate owner-visible account/organization,
  current balance/window and reset, freshness, model loaded/installed distinction,
  linked/unknown agent state and path where safe, history, alerts and a
  meaningful unavailable state. New evidence is checked where it is collected;
  values are not required to remain identical across naturally changing polls.
- **Completion automation:** machine-readable catalog of M6-A01..A10 and the
  five ST-OLL stories, exact versions/selection and live prerequisite results;
  fail on absent, failed, skipped, stale or narrower evidence. The receipt
  includes safe counts/digests and honest limitations, not identity/secret data.
  Owner outcomes are collected once and reused if still valid; no mechanical
  copy/paste of opaque IDs is required in normal user flows.

## 7. Owner participation and decision checkpoints

- **Now:** Owner has confirmed both SDK and EAIS cloud accounts and a real
  local model, subsequently identified as being on this machine. We will not ask for credentials in chat or require a
  list of every agent. The next practical need is reconciling the identified local model
  with the actual Ollama endpoint; verify without
  interrupting the host.
- **Once during discovery:** owner uses official account UI/auth where
  necessary and confirms which organization/account is shown. Store no secret
  or raw screenshot. Existing confirmed evidence is reused instead of asking
  again after each code change.
- **After discovery:** present endpoint/identity findings, any genuine scope
  choice, fixed M6 acceptance and revised estimate for approval. The existing
  A03 plan is Draft and must be approved before production code. Do not ask
  the owner to approve routine minor edits or repeated plan versions.
- **At delivery:** demonstrate the dashboard and summarize pass/fail and
  genuine unavailability; request formal acceptance once the actual M6 gate
  passes. This does not accept M7/M8.

## 8. Risk controls and escalation

| Risk | Trigger and decision |
|---|---|
| Cross-branch work lost | Baseline merge conflicts or promotion absent: stop before implementation, prepare a reviewable reconciliation, preserve both histories and the live service. |
| Cloud API access differs from docs | Missing permission/plan/identity: show the real response class without secrets, continue independent local work, ask once only for the missing owner action or scope decision. |
| Shared team funds counted twice | Relationship uncertain: retain unknown scope; require source-backed shared pool before aggregation. |
| Remote model unreachable | No safe read-only route or unknown trust boundary: local empty state remains valid; model-present check remains Blocked until access is supplied. Do not expose an unauthenticated Ollama API to a LAN. |
| Security/privacy or provider mutation | Suspected secret/content leak, default-profile write, unapproved route or process mutation: stop that lane and investigate; preserve dashboard. |
| Schedule drift | At package-2 checkpoint, compare actual hours and evidence against the current 73–118 hour ticket-level range; revise with specific reason and show alternatives. |
| New gate churn | Only block on a failed agreed M6 acceptance criterion or mandatory safety/contract rule, with reproducible evidence. Enhancements become follow-up, not new surprise blockers. |

## 9. Planning completion and approval

This execution plan and research document are **proposed**. The complete A03
module plan, concrete capability matrix, contract-impact decisions, live
selectors and canonical gate implementation remain to be finalized from actual
account/model evidence before production implementation begins. Existing
`AUTO-PLAN-CHECK` validates the synchronized planning baseline; it is not an
M6 readiness or acceptance gate. No estimate or proposed checklist is presented
as evidence that M6 has been implemented.

## 10. Ticket-level estimate correction and traceability

The original package estimate of 57–92 hours was superseded after the work
was decomposed into the [18-ticket catalog](m6-ticket-catalog-v1.json). The
sum of the ticket estimates is **73–118 active engineering hours**, approximately
**11–20 working days** at six to seven focused hours per day, plus external
waiting. This is an estimate, not an assurance or a justification for hidden
work. Ticket overlap and discovery results may reduce or increase it; update
the forecast at the discovery checkpoint with actual evidence.

Each catalog entry records a stable ID, existing `ST-OLL` story, owner,
dependencies, requirement IDs, V1 and M6 acceptance IDs, estimate, scope,
done condition, verification and evidence list. Current ticket status is
maintained in the catalog; proposed commands and files are clearly identified as not yet
implemented. Run `python3 tools/planning/validate_m6_tickets.py --stage plan` to validate
ticket identities, references, dependency acyclicity and M6 acceptance
coverage. This is a **planning traceability check only**. It cannot mark a
ticket done or replace the future real `AUTO-M6-EXIT`.

**Scope control:** after owner approval of the final capability decisions and
acceptance catalog, no extra feature, new gate, repeated account confirmation
or expanded work is added as a blocker unless it directly fails an agreed
criterion or a mandatory security/contract invariant, with reproducible
evidence and the smallest fix. Other findings go into a separate follow-up
list. At each checkpoint report completed ticket IDs, blocked IDs, hours used,
forecast and the next deliverable; do not ask the owner to operate internal
gates.

## 11. Host clarification reconciled on 3 November 2026

The owner answered the model-host question with **“this local machine”**, then
confirmed **“Ollama and model already available”**. The approved local-service
plan records that correction and permits the loopback source. This supersedes
the earlier planning assumption that a second machine must exist. M6-A02
therefore requires the identified local host and real model-present evidence,
not an additional computer invented by planning. Every registered host still
needs its own actual observations; one host cannot stand in for two registered
hosts. Empty inventory remains valid operational data but does not establish
the separate model-present scenario. Cloud scopes, process safety, recovery,
history and all other M6 acceptance requirements are unchanged.

This reconciliation uses existing owner direction, not a new approval or a
waiver based on current empty data. The current source reports no models, so
A02 remains unproven. See the [checkpoint](../../evidence/m6-delivery-checkpoint-2026-11-03.md)
for the failing/passing pure-policy checks and real live limitations.
