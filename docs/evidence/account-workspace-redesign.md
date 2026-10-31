# Test evidence and handoff: account workspace redesign

- Evidence ID: `ACCOUNT-WORKSPACE-2026-09-28`.
- Increment/authority: the owner's account-page redesign and automatic-identification correction; [approved bounded plan](../plans/integration/account-workspace-ui-change.md).
- Outcome: **Passed for the bounded account-workspace increment**, including the final real-owner browser gate after service restart. Mixed-account process attribution remains Partial as listed below.
- Primary module: P02; coordinated A01, A04 Linux, M03, M05, M06, P01, and Foundation V1 changes.
- Requirements: `FR-ACC-002/005/006`, `FR-ORG-001`, `FR-DISC-001/002/004/007`, `FR-UI-001/002/004/005/006`, `FR-COL-008`.
- Bounded acceptance evidence: `AC-UI-002/003/005/006`, `AC-PROC-001/003/004`; existing `AC-HIST-001` presentation retained, without a new full history acceptance claim.
- Contracts: HTTP/OpenAPI V1; `CTR-PROV-005`, `CTR-RUN-006`, `CTR-CAP-001`, `CTR-UI-001`, `CTR-API-001/002/003`, and `CTR-FND-005/008` at `1.0.0`. Generator `2.0.4`; 41 operations, two additive reads and one optional quota-window allowance field.
- Recorder/date/worktree: root agent, 2026-09-28, `codex/v1-m2` following `498f137`.

## Delivered outcome

The account page leads with the provider-reported email, assigned dashboard
organization, and Account / State / Left / Path summary. Claude's official
read-only `auth status --json` supplies an allowlisted email and provider
organization. Identity is read before and after each successful quota run;
only matching observations attest that exact run. The browser checks both the
account ID and collection-run IDs before displaying the email. Registry names
and organization assignments remain administrator-managed. Neither previous
quota history nor other processes are relabeled from the current default
profile. The receipt is memory-only and is unresolved after service restart
until the next genuine quota collection, respecting the five-minute cadence.

M05 calculates a per-window remaining percentage from available remaining
ratio, or `100 - reported percent used`. It validates units/range, preserves
rounded precision, confidence, and stale field state, marks the value derived,
and supplies its calculation and input observation ID. Original source fields,
health decisions, persistence, and history are preserved. When M05 has no
single constraining window, the UI labels individual windows separately.

A separate live table shows same-user Claude processes matching the admitted
installation, guarded PIDs, and actual working directories. It reads procfs
stat/exe/owner/cwd metadata and guards start ticks, executable, and owner around
cwd inspection. Running means process presence; Working cannot be established.
These processes have unresolved accounts and receive no assigned quota. Partial
scans and unavailable sources are disclosed. No argv, process environment,
transcript, prompt, response, or source-code content is inspected.

Quota and process summaries refresh every 30 seconds through generated V1 API
calls. Settings, source details, exact metrics, session records, and history are
expandable. The existing rename/assign/monitor/archive/restore flows remain
available. Mobile navigation and tables are compact and keyboard accessible.

## Test inventory and status

| Scenario | Real boundary | Status / evidence |
|---|---|---|
| `ACCOUNT-WORKSPACE` | Official installed Claude, owner SQLite/service, authenticated HTTP, built Chrome | Passed, including final refactor and service-restart rerun. Email matched an independent official CLI read; receipt matched every displayed quota run; real paths and unresolved ownership were checked. |
| Percentage derivation | Pure domain only | Nine cases Passed: zero/full/fractional usage, ratio precedence, stale preservation, unavailable, incompatible unit, negative/out-of-range. Constructed values have no I/O. |
| OpenAPI policy and observation HTTP | Production schema, real SQLite/Uvicorn/auth tokens | `35 passed in 44.00s`, including percentage tests. New reads authenticate before lookup and enforce account/telemetry permissions. |
| Linux process and account/runtime regressions | Real procfs, pure policies, real SQLite/HTTP | `31 passed in 28.37s`. |
| Organization and HTML regressions | Real SQLite/HTTP and built assets | `7 passed in 9.31s`. |
| `accounts_admin` | Fresh real migrated SQLite, production service, built Chrome | Passed after the redesign; native settings/history sections are opened by the scenario. No provider login or telemetry is invented. |
| `responsive` | Production service and built Chrome | Passed: six viewports, reduced motion, focus. |
| `AUTO-QUALITY` | Real checkout/toolchain | Passed again after final refactor: lint, format, strict typing, module boundaries, generated-artifact compatibility/drift, locked inputs, and production build. |
| Documentation/planning/Git | Real indexed Markdown, exact controls, checkout | Documentation passed for 254 Markdown files; synchronized planning and local commit preflight Passed. |

## Red evidence

All failures below preceded the production implementation they drove, against
the actual running owner dashboard or production schema on 2026-09-28.

- The initial built browser timed out waiting for the `Account activity` table
  (`workspace_table`, 10 seconds), before the summary redesign.
- The identity operation returned HTTP `404`, before the new P01 read existed.
- The real browser failed at `real_process_locations: live_api_read_failed`
  before the process-location operation existed.
- The percentage browser assertion failed with
  `real_remaining_percentage_missing` against real percent-used observations,
  before M05's display calculation and P02 rendering.
- The schema policy assertion failed with
  `assert 'read:status' == 'read:accounts'`; the new email read was then tightened
  to account-read permission. The real token permission scenario also exposed
  a missing-account `500`, fixed to the existing safe `404` problem code.
- The old OpenAPI regression oracle failed with `assert 41 == 25`; its exact
  success/request catalog now includes the previously delivered registry
  operations and the two new reads. Negative drift assertions remain enabled.

No historical terminal artifact is invented. Initial syntax/static failures
are excluded from behavioral Red claims. A narrow-screen overflow during
visual refinement was followed by a passing real browser rerun.

## Canonical verification and refactor evidence

The bounded completion gate requires a running loopback owner service, its
real eligible Claude profile, real current processes, and the local dashboard
credential already available to the operator helper. Missing prerequisites
return Blocked or fail; a new collection may take the genuine source interval.
The credential and expected identity travel through private stdin and are
never command arguments. Screenshots are private local artifacts, not committed.

```bash
backend/.venv/bin/python tools/ui/verify_account_workspace.py \
  --origin http://127.0.0.1:43110 \
  --screenshots /tmp/agentmonitor-workspace-final
backend/.venv/bin/python frontend/tests/browser/p02/run_browser.py accounts_admin --no-build
backend/.venv/bin/python frontend/tests/browser/p02/run_browser.py responsive --no-build
python3 tools/automation/implementations/auto_quality.py
python3 tools/docs/check.py
python3 tools/planning/validate_plans.py --stage synchronized
python3 tools/git/preflight.py --operation commit
```

The browser checks 1440×1000, 1920×1080, and 390×844, exact Account / State /
Left / Path headings, actual identity/run lineage, the calculated remaining
values, genuine working directories, unresolved process ownership, collapsed
settings, no page errors, and no document overflow. Desktop and phone screenshots
were inspected. Eight real processes and eight paths were observed during this
session; this is a dated observation, not a configured account/process count.

The final owner command returned exit `0` with
`ACCOUNT WORKSPACE: PASSED — real owner account, organization, selected quota, responsive browser`.
The final `accounts_admin` command and local static/build controls also returned
exit `0`. Service restart preserved the real polling interval; the subsequent
new run supplied a matching identity receipt. No clock or provider limit was
changed. Responsive screenshots were visually inspected after compaction.

## Scope and changed files

- A01: `backend/src/agentmonitor/adapters/providers/claude/authentication/identity.py`.
- A04: `backend/src/agentmonitor/adapters/platform/linux/processes.py`.
- Foundation: `backend/src/agentmonitor/composition/{bootstrap,claude_dashboard_collection,linux_process_locations}.py`.
- M03/M05/M06: public `contracts/{provider_system_v1,capacity_v1,runtime_observation_v1}.py`, each owning module's `application/queries.py`, M05 `domain/allowance.py`.
- P01: `api/v1/dependencies.py`, routers and schemas for providers, runtime, capacity; real observation/OpenAPI tests.
- P02: `AccountPage.tsx`, new `AccountWorkspaceSummary.tsx` and `LiveClaudeProcesses.tsx`, `CapacityPanel.tsx`, `quotaPresentation.ts`, dashboard CSS, shared generated-client wrapper, and browser scenarios.
- Generated: `contracts/openapi/agentmonitor-v1.json`, `frontend/src/generated/api/index.ts`, generated by `tooling/foundation/openapi_client.py`.
- Verification: `backend/tests/capacity/test_display_allowance.py`, `frontend/tests/browser/p02/account_workspace.mjs`, `tools/ui/verify_account_workspace.py`.
- Documentation: this evidence, approved change plan, module guide/index, exact contract adoption/baseline/snapshot and mechanical synchronization records.

## Contract, privacy, migration, license, and operations review

Both new reads use the normal authenticated P01 authorization and safe problem
transport; email requires `read:accounts`, process locations `read:telemetry`.
OpenAPI compatibility passed. Foundation/P01 consumption of M03's identity
contract is declared in the exact catalog. Existing Draft plan statuses and
broader milestone status are preserved; the owner authorized this bounded
change. No incompatible public change or ADR migration is required.

No database migration, configuration key, dependency, license admission,
provider authentication write, default-profile mutation, or running-agent
control was introduced. Provider credentials remain provider-managed. Only
allowlisted identity metadata is retained in memory; fingerprints/raw status
JSON are not exposed. No personal account identifier, project path, credential,
or raw provider payload is written into this document or tests. Production
logs contain only safe poll event codes. Screenshots show post-login UI and
are stored locally in a private directory. No test doubles, provider recordings,
demo accounts, seeded telemetry, hardcoded pass, or test-only production branch
were used. Administrative browser records exercise real CRUD in isolated
SQLite and never simulate provider accounts or observations.

Rollback is a code/build rollback; no data transformation is required. Service
shutdown drains its own bounded reader. The permanent service remains at
the existing loopback origin; reload the account page to use the new build.

## Residual gaps and follow-up

- `ACCOUNT-CORRELATION-OPEN`: individual existing mixed-account processes are
  Unresolved. M03/M06/A01 need a provider-supported, session-specific identity
  source before assigning accounts or quota. The official agent-list command
  has no metadata-only field projection; potentially content-bearing output
  was not inspected. Manual guesses or default-profile inference are excluded.
- Working/waiting activity is not available for these native processes; no
  Working state is claimed. Cwd is a working directory, not an inferred root.
- Other Claude versions/users and macOS are outside this admitted Linux view.
- Six-account/new-managed-profile authentication, full V1/M4 acceptance,
  release/hosted verification, and renewed full history acceptance: **Not Run**
  in this increment. Existing acceptance records remain authoritative.

The evidence proves the bounded account-workspace delivery and one genuine
profile's quota identity. It does not prove complete mixed-account attribution
or completion of the entire dashboard/V1 milestone.
