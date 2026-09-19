# CS-0 draft-integrity review

- Review ID: `CS-0-2026-09-18-01`
- Status: Complete
- Result: **Pass with approval-blocking conditions**
- Reviewer: root/integration steward
- Reviewed plan versions: M0 0.1.0, PLAN-FND 0.1.0, PLAN-M01 0.1.0, V1 planning program 0.1.0, contract register 0.1.0
- Behavioral implementation/live-test result: Not Run; this is a document/planning review only

## 1. Meaning of the result

`Pass` means the P0 artifacts are internally substantial enough to enter owner and producer/consumer review. It does not mean a module is Approved, Ready for implementation, implemented, or live verified.

All three independent plans correctly remain Draft. M0 execution and every production implementation action remain blocked until their explicit approval/entry conditions are met.

## 2. Artifacts reviewed

| Artifact | Independent owner | Scope isolation | Review outcome |
|---|---|---|---|
| `docs/plans/discovery/m0-execution-plan.md` | M0 planning agent | Sole assigned file | Pass with M0 owner/safety approvals pending |
| `docs/plans/foundation/plan-v1.md` | Foundation planning agent | Sole assigned file | Pass with dependency/technical/consumer decisions pending |
| `docs/plans/modules/m01-identity-access/plan-v1.md` | M01 planning agent | Sole assigned file | Pass with security/P01/P02/M08/persistence decisions pending |
| `docs/plans/integration/v1-planning-program.md` | Integration steward | Root-owned integration plan | Pass as gated planning strategy; owner review pending |
| `docs/plans/contract-register.md` | Integration steward | Root-owned shared register | Pass as proposed register; no contract Approved |
| `docs/plans/planning-backlog.md` | Integration steward | Root-owned task-packet catalog | Pass; provider-dependent plans correctly gated by M0 |

No planning agent edited a shared specification, another agent's plan, source code, dependency manifest, configuration, migration, `.env`, provider state, Git/GitLab resource, or production artifact.

## 3. Compliance review

| Gate | M0 | Foundation | M01 | Result/notes |
|---|---|---|---|---|
| Planning authority only | Yes | Yes | Yes | Each explicitly says implementation is unauthorized |
| Requirement/AC mapping | Yes | Yes | Yes | M0 records contribution rather than false acceptance; FND/M01 distinguish supporting gates |
| One owner/boundary | Cross-cutting evidence coordinated by root/M03 future owner | Technical foundation, no business ownership | M01 only | No hidden module/table ownership takeover found |
| Allowed/forbidden scope | Yes | Yes | Yes | Exact paths or artifact scope and stop rules are present |
| Contract impact | Handoff proposals only | Eight technical proposals | IAM port/DTO/error proposals | Central register updated to Proposed where producer plan exists |
| Data/table ownership | No product data | Tool metadata only | `iam_*` only | No cross-module direct table access proposed |
| Real-system test policy | 75 real discovery scenarios | 52 real/policy scenarios | 76 planned scenarios | No mock/fake/replay/seeded telemetry path found |
| Meaningful Red design | N/A to observational discovery; predeclared pass/safety basis | Yes | Yes | Setup/dependency failure explicitly rejected as Red |
| Secret/content safety | Yes | Yes | Yes | Allowlist, external custody, redaction/non-capture, stop/incident rules present |
| Default-profile/running-agent safety | Zero side-effect budget | No provider boundary | No provider boundary | V1 process-control prohibition preserved |
| Dependency admission | No additions | Candidate/Pending only | Candidate/Pending only | No exact package/version/install is approved |
| Operations/recovery | Discovery custody/stop | lifecycle/migration/rollback seams | credential rotation/recovery/restore invalidation | Commands remain TBD until real verification |
| Blocked/Not Run truthfulness | Explicit | Explicit | Explicit | No absent evidence counted as Passed |
| Documentation/handoff | Detailed | Detailed | Detailed | Downstream consumers and approval conditions named |

## 4. Cross-plan ownership review

### Foundation versus M01

- Foundation owns configuration loading/secret-safe wrapper; M01 owns its keys and security policy.
- Foundation owns composition mechanisms; M01 owns authentication/authorization use cases.
- Foundation owns migration environment/allocation mechanism; M01 owns only `iam_*` DDL/revisions allocated to it.
- Foundation owns OpenAPI/client generation mechanism; P01/M01 own API/auth semantics, and P02 consumes generated output.
- Foundation owns safe correlation/log primitives; M01 owns safe IAM event vocabulary.

No circular import or direct table dependency is required by either plan.

### M01 versus P01/P02/M08

- M01 owns credential/session/token/permission semantics.
- P01 will own sockets, Host/Origin/CORS, HTTP parsing/serialization, cookie headers, routing, OpenAPI security, problem mapping, and Swagger transport.
- P02 will own login/token UI, generated-client use, browser expiry recovery, storage behavior, and accessibility.
- M08 will own backup/restore orchestration, diagnostics/export boundary, and retention scheduling while invoking M01 ports.

The division is viable, but the exact cookie/CSRF/Origin, problem-code, permission/scope, audit/retention, and restore-invalidation contracts require consumer review before M01 approval.

### M0 versus provider/domain plans

M0 gathers evidence and proposes handoff needs; it does not decide production schema or adapter implementation. M02–M06 and A01–A04-LINUX correctly remain Waiting for discovery until M0's G9 exit.

## 5. Contract synchronization findings

The central register now records Foundation and M01 producer-defined proposals as `Proposed`. All other contracts remain `Concept`, especially those blocked by M0.

Approval is blocked until:

1. Foundation consumers accept lifecycle, configuration, log/correlation, OpenAPI/client, migration metadata, build metadata, evidence, and ownership contracts.
2. M01/P01/P02 agree on browser session cookie, CSRF, Origin, expiry, error, one-time-secret, and generated-client behavior.
3. Root freezes the permission/scope catalog against planned `/api/v1` operations.
4. M01/M08/DB agree on IAM audit retention, backup sensitivity, restore invalidation, migration allocation, and recovery.
5. Exact foundation/IAM dependency choices pass separate admission.
6. M0 evidence resolves provider capability/identity/provenance contracts before their producers draft schemas.

No proposed contract was promoted to `Synchronized` or `Approved` by this review.

## 6. Findings and dispositions

| Finding | Severity | Disposition | Blocking scope |
|---|---|---|---|
| CS0-F01 — P0 plans have no owner/reviewer approval records | Expected gate | Retain Draft; present for owner review | All implementation; all M0 execution |
| CS0-F02 — M0 exact operations, evidence root, aliases, request budgets, and installed versions are intentionally unknown | Critical if bypassed | Complete G0/G1/G2/G3 in order; zero request budget until approval | M0 live execution and M02–M06/A01–A04 approval |
| CS0-F03 — Foundation has 20 materially different runtime/tool/dependency/CI/config choices | Critical if delegated to implementation | Run dependency/tool decision and consumer synchronization work; retain Candidate/Pending | PLAN-FND implementation |
| CS0-F04 — M01 has 16 root synchronization decisions | Critical if delegated to implementation | Resolve through security, P01, P02, M08, DB, dependency and owner reviews | PLAN-M01 implementation |
| CS0-F05 — Technical/IAM contract proposals were drafted independently from the central register | Moderate, resolved for review | Register updated with mapping and Proposed status; consumer review still pending | Contract approval |
| CS0-F06 — Git is not initialized and GitLab has not been contacted | Informational | Preserve; those mutations require later explicit authorization | Hosted CI implementation/evidence |
| CS0-F07 — M0 rare live states may remain unavailable under real-only policy | Major, accepted project risk | Preserve Blocked status; never simulate or weaken release reporting | Relevant live gates |
| CS0-F08 — Real macOS environment is not established | Major | Keep platform evidence Blocked; prevent Linux leakage in core contracts | macOS implementation/verification |

No secret/content exposure, destructive action, provider-state access, dependency installation, test manipulation, or source implementation occurred during planning.

## 7. Review metrics

- M0 scenarios: 75 uniquely named catalog entries as reported by its planning owner.
- M0 workstreams: common governance plus Claude, Codex, Ollama product/local, Anthropic API, OpenAI API, Ollama API, Linux process/session, and synthesis.
- Foundation: 52 uniquely defined test/policy scenario IDs spanning boundaries, real SQLite, real HTTP, generated contracts/client, built browser, security, dependencies, docs, CI, and platforms.
- M01: 76 uniquely defined planned scenario IDs spanning pure rules, real Argon2 implementation, real SQLite/migrations, real HTTP server, real browser, security/artifact, operations, dependency, and documentation gates.
- Production files/manifests/migrations/configuration/dependencies added: zero.
- Live provider/platform scenarios executed: zero (`Not Run`).

Metrics describe planning coverage, not product correctness.

## 8. CS-0 exit decision

P0 exits **draft-integrity review** and may enter owner/consumer review. It does not exit planning, Definition of Ready, M0 G0, or any implementation gate.

Allowed next actions after this review:

1. owner reviews the gated V1 planning program and P0 drafts;
2. reviewers resolve Foundation and M01 contract/decision items without implementation;
3. owner explicitly approves or requests revisions to M0 G0;
4. after G0 approval, prepare the exact G1 evidence-custody packet; no provider operation yet;
5. execute M0 gates only with their individual safety/owner approvals;
6. assign P1 module planners only after accepted M0 handoffs.

Not allowed merely because CS-0 passed:

- production/test implementation;
- Git/GitLab initialization/configuration;
- dependency install/version pinning without admission;
- `.env` creation or secret request;
- provider/process/file/API inspection;
- login/logout/reauth/profile experiment;
- approval of M0-dependent schemas or provider contracts.
