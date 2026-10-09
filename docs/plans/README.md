# Module planning registry

## Purpose

This registry is the synchronization point for detailed module planning. A
substantive Draft exists for every V1 discovery, foundation, module, adapter,
platform, API, UI, persistence, deployment, and integration workstream. The
exact versions and SHA-256 digests are frozen by the plan snapshot and the
completed CS-1 synchronization review. PLAN-M0-DISCOVERY has subsequently
passed its restricted G0 and G1 safety-control gates; post-G1 provider/platform
observations have not started.
The implementation-plan set remains unapproved, and provider-dependent
implementation still requires Milestone 0 evidence. A row moves to
implementation `Approved` only after named review, executable readiness gates,
and owner approval.

## Status vocabulary

- `Waiting for discovery`: material external facts are unresolved.
- `Ready to plan`: requirements/boundaries are stable enough for an independent planning task.
- `Draft`: a planning agent is preparing the plan.
- `Contract review`: consumers/producer are synchronizing public surfaces.
- `Approved`: root steward has approved the exact plan and contract versions for implementation.
- `Approved for gated discovery`: the exact discovery plan passed its named
  planning review; it grants no implementation or live-operation authority and
  remains subject to its later gates.
- `Superseded`: a newer plan version replaces it; history remains linked.

## Planning register

| Plan ID | Scope/owner | Current status | Required predecessor/evidence | Primary contract relationships | Plan artifact |
|---|---|---|---|---|---|
| PLAN-M0-DISCOVERY | Read-only provider/platform discovery | G0 and G1 complete; post-G1 observations not started | Exact per-operation preflight and real evidence | Evidence handoffs to M02–M06/A01–A04-LINUX | [Approved 0.2.0](discovery/m0-execution-plan.md) |
| PLAN-FND | Repository, CI, tooling, composition foundation | Draft synchronized at CS-1; not implementation-ready | Resolve dependency/tool/runtime choices and consumer contracts | All modules; no business ownership | [Draft 0.2.0](foundation/plan-v1.md) |
| PLAN-M01 | Identity and access | Draft synchronized at CS-1; not implementation-ready | Resolve 16 root/security/P01/P02/M08/DB decisions | FastAPI boundary, operations audit/recovery | [Draft 0.2.0](modules/m01-identity-access/plan-v1.md) |
| PLAN-M02 | Registry | Draft synchronized at CS-1; M0/approval pending | Account/profile/resource identity findings before approval | Provider system, capacity, runtime | [Draft 0.2.0](modules/m02-registry/plan-v1.md) |
| PLAN-M03 | Provider system/protocol | Draft synchronized at CS-1; M0/approval pending | M0 capability matrices before approval | Every provider adapter, collection | [Draft 0.2.0](modules/m03-provider-system/plan-v1.md) |
| PLAN-M04 | Collection control | Draft synchronized at CS-1; M0/approval pending | Rate, cost, timeout, auth-failure evidence before approval | Provider system, capacity, runtime, alerting | [Draft 0.2.0](modules/m04-collection-control/plan-v1.md) |
| PLAN-M05 | Capacity | Draft synchronized at CS-1; M0/approval pending | Quota/budget semantics and units before approval | Registry, collection, alerting, API/UI | [Draft 0.2.0](modules/m05-capacity/plan-v1.md) |
| PLAN-M06 | Runtime observation | Draft synchronized at CS-1; M0/approval pending | Linux process/session source and identity evidence before approval | Registry, alerting, platform/provider adapters | [Draft 0.2.0](modules/m06-runtime-observation/plan-v1.md) |
| PLAN-M07 | Alerting | Draft synchronized at CS-1; approval pending | Real upstream recovery/threshold evidence before approval | API/UI, future delivery adapters | [Draft 0.2.0](modules/m07-alerting/plan-v1.md) |
| PLAN-M08 | Operations | Draft synchronized at CS-1; approval pending | Backup/service/config decisions | Every module health/query port | [Draft 0.2.0](modules/m08-operations/plan-v1.md) |
| PLAN-A01 | Claude adapter | Draft synchronized at CS-1; M0/live evidence pending | Real Claude versions/accounts/capabilities before approval | M03/M04/M05/M06/M02 | [Draft 0.2.1](adapters/claude/plan-v1.md) |
| PLAN-A02 | Codex adapter | Draft synchronized at CS-1; M0/live evidence pending | Real Codex versions/accounts/capabilities before approval | M03/M04/M05/M06/M02 | [Draft 0.2.0](adapters/codex/plan-v1.md) |
| PLAN-A03 | Ollama adapter | Draft synchronized at CS-1; M0/live evidence pending | Real Ollama versions/accounts/capabilities before approval | M03/M04/M05/M06/M02 | [Draft 0.2.1](adapters/ollama/plan-v1.md) |
| PLAN-A04-LINUX | Linux platform adapter | Draft synchronized at CS-1; M0/live evidence pending | Real process/path/service inventory before approval | M06/M08/deployment | [Draft 0.2.0](platform/linux/plan-v1.md) |
| PLAN-A04-MAC | macOS platform adapter | Draft synchronized at CS-1; real Mac evidence Blocked | Real macOS evidence before implementation/approval | Same platform contract as Linux | [Draft 0.2.0](platform/macos/plan-v1.md) |
| PLAN-P01 | FastAPI/API boundary | Draft synchronized at CS-1; approval pending | IAM and application contract decisions | All application query/command ports | [Draft 0.2.0](api/fastapi-boundary/plan-v1.md) |
| PLAN-P02 | React mission-control UI | Draft synchronized at CS-1; approval pending | Approved OpenAPI/resource and generated-client contract | P01 only | [Draft 0.2.0](ui/react-dashboard/plan-v1.md) |
| PLAN-DB | SQLite persistence/migration adapter | Draft synchronized at CS-1; approval pending | Approved table/port details and dependency admission | Repository ports; operations backup | [Draft 0.2.0](persistence/sqlite/plan-v1.md) |
| PLAN-DEP | Native Linux deployment | Draft synchronized at CS-1; target/live approval pending | Target workstation inventory before live approval | P01/P02/M08/platform | [Draft 0.2.0](deployment/linux-native/plan-v1.md) |
| PLAN-INT | Integration and V1 release | Draft synchronized at CS-1; release unauthorized | Approved module plans and full live evidence before release | All modules/adapters | [Draft 0.1.0](integration/v1-plan.md) |

## Planning control artifacts

- [V1 planning program](integration/v1-planning-program.md): dependency graph, planning/implementation waves, synchronization gates, and approval boundaries.
- [Independent planning packet catalog](planning-backlog.md): reusable task
  packets for all module/adapter/boundary plans; no plan is missing.
- [Proposed contract register](contract-register.md): producer, consumers, maturity, blockers, and synchronization rules.
- [Machine contract baseline](contract-baseline.toml): exact producer/consumer/version/checklist records for all proposed contracts.
- [Exact contract adoption](contract-adoption.toml): machine-checked
  per-plan published and consumed contract sets bound to the baseline digest.
- [Exact configuration allocation](configuration-baseline.toml): all 57 currently planned `AGENTMONITOR_*` keys with one owner, type, units, defaults/derivations, constraints, sensitivity, reload semantics, and unresolved-decision status.
- [Exact requirement ownership](requirement-ownership.toml): all 154 requirement and acceptance IDs with one primary plan and exact planned evidence.
- [Parallel ownership manifest](parallel-ownership.toml): plan-hash-bound code, test, and documentation write sets; contract families; tables; migration slots; configuration namespaces; dependencies; and shared writers.
- [Planning completeness catalog](planning-catalog.toml): the 20 required artifacts and their executable minimums.
- [Routine automation catalog](../../tools/automation/routines.toml): canonical operational, limited, and fail-closed Blocked commands.
- [CS-0 draft-integrity review](integration/cs0-draft-integrity-review.md): cross-plan findings and next allowed actions.
- [CS-1 independent final audit](integration/cs1-final-readiness-audit.md): semantic review and closure of CS1-R01..R18 plus CS1-F01.
- [Synchronized plan/control baseline](plan-baseline.toml): exact SHA-256 and
  byte length for all 20 plans and nine controls, including exact contract
  adoption and the M0 G0 approval.
- [M0 G0 gate evidence](discovery/m0-g0-gate-evidence.md): reviewer findings,
  real-checkout Red/Green evidence, exact approved digest, and the still-Blocked
  execution preflight.
- [M0 G1 control specification](discovery/m0-g1-control-specification.md):
  versioned custody, packet, assertion, ledger, E1-admission, incident, and
  future `AUTO-M0-PREFLIGHT` contracts.
- [Gitleaks E1 scanner admission](discovery/dependencies/gitleaks-admission.md):
  approved and verified for isolated local G1 use; not approved for distribution.
- [CS-1 full-plan synchronization record](integration/cs1-full-plan-synchronization.md): final scope, alignment, automation and authority disposition.
- [CS-1 planning-gate evidence](integration/planning-gate-evidence.md): real-checkout red/green/refactor evidence and residual Blocked/Not Run boundaries.

## Independent planning protocol

1. Root steward issues one mandatory task packet from the sub-agent runbook.
2. One planning agent copies the module-plan template for one row and edits only its assigned plan directory unless authorized otherwise.
3. The agent treats current contracts as proposals and submits gaps; it does not edit shared contracts during independent drafting.
4. Root compares all plans for duplicate ownership, gaps, circular dependencies, shared-file collisions, security/privacy conflicts, and incompatible assumptions.
5. Producers and consumers perform a contract synchronization review.
6. ADRs, shared contracts, requirements, traceability, risks, and plan versions are updated together.
7. Root records approval, allowed paths, implementation wave, and exact contract versions.
8. Only Approved plans can produce implementation tasks.

## Proposed plan artifact structure

```text
docs/plans/
  README.md
  discovery/
    m0-execution-plan.md
  foundation/
    plan-v1.md
  modules/
    m01-identity-access/plan-v1.md
    ...
  adapters/
    claude/plan-v1.md
    ...
  platform/
    linux/plan-v1.md
  integration/
    v1-planning-program.md
    cs0-draft-integrity-review.md
    v1-plan.md
```

Directories are created when an approved planning assignment begins. Drafts state their status clearly and are not mistaken for implementation authority.

## Root synchronization checklist

- Every approved V1 requirement/acceptance criterion has exactly one primary owner and required supporting plans.
- Every public contract has one producer, identified consumers, version, compatibility status, and verification owner.
- Every table/migration/configuration key/generated artifact/shared file has one edit owner per implementation wave.
- Provider/platform discoveries have explicit Supported/Experimental/Deferred/Unsupported results.
- Live tests requiring the owner are scheduled and cannot be substituted.
- Critical risks have mitigation/acceptance decisions.
- No plan relies on prompts/content/secrets, default-profile mutation, agent control, fake telemetry, or unapproved dependencies.
- Parallel tasks share no unresolved contracts, migration chain, or generated output.

## Bounded owner-directed account-view changes

- [Dashboard 24-hour session policy](integration/dashboard-session-24h-change.md):
  approved M01/P01 fixed 86,400-second policy for newly issued browser sessions,
  with no runtime `.env` override or schema/API change.
- [V1-M5 Codex slice](integration/m5-codex-slice-change.md): approved exact
  `0.160.0` managed-profile identity/quota, four-account fleet, five-to-six
  process, provider-neutral API/UI, and fail-closed milestone completion scope;
  OpenAI API billing remains V1-M7.
- [Live agent account association](integration/live-agent-account-association-change.md):
  explicit manual confirmation, guarded current terminal details and private
  revisioned settings; the named owner-authorized live link/persistence gate Passed.
- [Duplicate identity overview](integration/duplicate-account-overview-change.md):
  one quota row for fresh identical identities and review links for their
  separate admin connections.
