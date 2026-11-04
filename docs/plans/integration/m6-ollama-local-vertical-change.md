# M6 Ollama local-service vertical

**Current status: Deferred to future versions by the owner on 4 November 2026.** The [scope decision](m6-local-ollama-deferral-2026-11-04.md) and [future backlog](future-local-ollama-backlog-v1.json) supersede this plan's M6 delivery/acceptance assignment. Earlier approval and evidence below remain historical. Do not resume local work or require it for M6 closure without future scheduling.

- Status: Approved by the owner on 1 November 2026 for this local-service scope.
- Owners: A03 adapter, M03 provider protocol, M06 runtime, P01 API, P02 UI;
  the integration steward serializes shared contracts and composition.
- Parent: A03 plan `0.2.1-draft`; M6 ST-OLL-001/002/005, M6-T002/003/006/008/009/013/014.
- Requirements: FR-DISC-001/003/004/008, FR-COL-003/004/006/007,
  FR-SAFE-001/002; acceptance: M6-A02/A06/A08/A09, AC-UI-005,
  AC-LIVE-004, AC-PROC-001..004. This vertical contributes to but cannot close
  M6; cloud identities/balance, history and alert coverage remain required.

## Outcome and scope

The authenticated dashboard shows the real local Ollama service version,
installed-model inventory and loaded-model inventory with source, observation
time and explicit unavailable/partial states. An empty list is valid. Loaded
does not imply an active request, agent or cloud account; unverified links are
unknown. The application must remain usable when Ollama is unavailable.

This first scope is one local loopback service at `127.0.0.1:11434` and its
documented read-only `/api/version`, `/api/tags` and `/api/ps`. CLI and daemon
versions are independent. This plan does not authorize remote endpoints,
inference, model download/load/unload, default-profile access or process
mutation. M6's model-present and process-correlation acceptance remain open
until a real safe model/process state is available and its fields and
semantics have been verified. The owner identifies this machine as the host;
the currently observed loopback service reports no models.

## Ownership and intended changes

1. A03: add isolated Ollama manifest, installation/version discovery and a
   bounded local source under `backend/src/agentmonitor/adapters/providers/ollama/`.
   Enforce fixed host/path/method, no redirects or proxy, time/size bounds,
   safe field allowlisting, normalized failures and admitted exact daemon
   version. Define safe permitted model fields, length/item bounds and
   truncation before exposing them; provider-generated names may contain
   user-defined content and require privacy review. Distinguish per-source
   failure from an empty list. Do not write the database or depend on UI/domain
   internals.
2. M03/M06: publish typed catalog/capability ports and closed result objects in
   owned `backend/src/agentmonitor/contracts/` modules. The result distinguishes
   installed, loaded, empty, unavailable, stale and partial, with provenance;
   it must not fabricate active work or ownership. Freeze per-source times,
   freshness, size and item bounds, truncation, and errors from real evidence.
   The existing generic capability port does not prove a concrete catalog
   schema exists. `/api/tags` and `/api/ps` are not an atomic snapshot.
3. P01/composition: inject the port and add an authenticated read-only v1
   provider catalog route and response schemas. Never accept a caller-chosen
   network target or unknown query parameters and require `read:telemetry`.
   Define an idempotent installation reconciliation or make the local catalog
   visible independently of installation registration. Regenerate the OpenAPI contract and TypeScript client with
   the repository generator. Check additive compatibility; a breaking change
   requires a versioned migration path and ADR.
4. P02: consume only the versioned generated client in the provider/dashboard
   views, showing catalog sets, time, version and state responsively. Preserve
   account views, promotion and support link. No direct daemon calls from UI.
5. M06/A04 process evidence is a separate owned path: use only allowed
   read-only OS metadata and existing association contracts. Do not claim this
   vertical satisfies correlation before real representative checks pass.

No new third-party package is proposed. An ephemeral catalog may need no
database migration, but review the final contract and lifetime before deciding;
M6's cloud capacity history and alerts remain separate required work.

## Technical evidence and test-first sequence

The canonical local inventory uses three fixed requests with a three-second
timeout, 256 KiB limit, no proxy or redirects and count-only output. It is a
preliminary observation, not the M6 technical admission. ADR-0013 governs
owner-local milestone evidence; detached M0 paperwork is advisory but real
technical/source/security checks remain mandatory. Implement and register a
versioned M6 technical admission routine that checks actual source/version,
configured scope, bounded operation and sanitization before an enabled lane is
accepted. It must not require the old unimplemented M0 approval machine.

| Step | Red before production change | Green / refactor evidence |
|---|---|---|
| Safe source | Real local integration check fails because no Ollama adapter/source exists. | Production adapter reads actual service under fixed boundaries, returns current version and empty/real catalogs without state mutation; exact unknown version and invalid data fail closed. |
| Contract/API | Real SQLite/HTTP check fails because catalog port/route is absent. | Actual authenticated endpoint exposes typed safe results, rejects untrusted access, preserves prior v1 API and generated client. |
| UI | Built-browser check fails because the local catalog view is absent. | Real backend and actual Ollama state render on desktop/mobile, show time/version and empty/unknown accurately; existing promotion and support link remain. |
| Real model/process | Real model-present and process checks initially remain Blocked if unavailable; do not turn the absence of a prerequisite into a Red test. | When a naturally available model/process exists, verify true source fields and correlations without starting/stopping it; disclose unresolved relationships. |

Use real providers and actual process/HTTP/browser/SQLite boundaries; pure
domain rules may use constructed values. Record test command, expected Red,
actual output, Green and post-refactor result. Do not record raw provider
payloads, model prompts, completions, secrets or arbitrary process environment.

## Operations, review and rollback

User-managed Ollama and running agents remain untouched. Collection is bounded
and failure-isolated. The existing dashboard service stays available; rollout
must be atomic and reversible with a preserved previous frontend/service
revision, no forced model or agent restart. Security review covers host binding,
SSRF/redirect/proxy protection, safe fields, information exposure and failure
isolation. No new dependency or license is anticipated. Update the provider
module, API contract/client, dashboard docs, live-verification runbook and
ticket evidence in the same change.

## Stop conditions and completion

Stop the affected lane for a new source/host, profile write, missing contract,
unexpected content or credential exposure, unapproved dependency, breaking
contract or uncertain side effect. Record blocked/not-run cases honestly and
continue independent work. Completion requires the registered technical
admission, all planned local tests and available real states, security and
privacy review, actual dashboard verification and a reviewable handoff; full
M6 still requires M6-A01–A10 and the M6 completion command. The owner's approval
authorizes this local scope; it is not an implementation-completion claim.
