# CS-1 independent readiness audit — first pass

- Audit ID: `CS1-READINESS-2026-09-18-01`
- Status: **BLOCK**
- Review boundary: the 20-plan Draft corpus and shared planning controls before
  the final immutable snapshot
- Reviewer role: independent contract/traceability/readiness reviewer
- Authority: finding report only; no plan approval or implementation authority
- Test/live status: no production or live-provider tests were run

## 1. Decision

The first-pass corpus must not receive a CS-1 Complete record. Structural gates
and document counts were insufficient: the review found semantic contradictions
between plan bodies, the contract baseline, traceability, configuration naming,
and parallel ownership. Corrections require a second independent pass against
the exact post-correction files before a plan snapshot may be frozen.

This report is deliberately preserved as the red review evidence. A later pass
must not rewrite these findings into a retroactive pass.

## 2. Scope inspected

- all 20 artifacts in `planning-catalog.toml`;
- `contract-baseline.toml`, `requirement-ownership.toml`, and
  `parallel-ownership.toml`;
- the earlier contract-alignment and requirement-coverage audits;
- product requirements and V1 acceptance criteria;
- completion/automation, configuration, SDLC, and sub-agent standards;
- the planning validator and its real-checkout tests.

## 3. Blocking findings

| ID | Area | First-pass evidence and contradiction | Required correction / re-audit state |
|---|---|---|---|
| CS1-R01 | CAA-C04 | P01 used `one_time_secret_non_replayable` as both replay policy and HTTP 409 problem code, while M01, PLAN-INT, and the baseline distinguish policy `one_time_secret_non_replayable` from code `one_time_secret_not_replayable`. | Correct P01 and re-scan every occurrence. Applied after finding; re-audit required. |
| CS1-R02 | Configuration naming | Parallel ownership allocated `AM_*` namespaces while the mandatory standard and plan keys require `AGENTMONITOR_*`. | Use only `AGENTMONITOR_*`. Applied after finding; re-audit required. |
| CS1-R03 | Configuration collisions | No exact machine-readable key register existed; prose namespaces could not prevent collision or validate owner/type/default/bounds/sensitivity/reload state. | Enumerate every exact planned key and add executable comparison with the plan corpus. Applied after finding; re-audit required. |
| CS1-R04 | CAA-C11 | M05's addendum prohibited consuming M07 policy, but later M05 readiness/decision wording sent M07 threshold policy back to M05. | Preserve one-way M05 capacity health/signals to M07 alert policy. Applied after finding; re-audit required. |
| CS1-R05 | CAA-C15 | A04-LINUX and P01 retained package-per-version imports such as `agentmonitor.contracts.platform.v1`, contradicting the frozen one-file `<family>_v<major>.py` convention. | Reconcile every import/path and remove stale layout blockers. Assigned; re-audit required. |
| CS1-R06 | CAA-C16 | A01/A02/A03 and parallel ownership used `contracts/providers/...` while PLAN-INT froze `backend/src/agentmonitor/contracts/providers/<provider>/<capability>/v1/**`; semantic ownership and shared wave-writer authority were also conflated. | Use one exact namespace and separate semantic owner from allocated writer. Shared manifest corrected; plan re-audit required. |
| CS1-R07 | P01 contract parties | P01 declared broad family ranges that included event/inspection/provider-flow contracts it must not consume, omitted other baseline parties, and conflicted with its thin application-port boundary. | Replace ranges with the exact baseline IDs and remove provider invocation/auth-flow/extension-registry consumption. Assigned; re-audit required. |
| CS1-R08 | Requirement parties | Nine requirement records (covering ten producer obligations) cited contracts without including the contract producer in primary/supporting ownership. | Add the producer party and make the gate enforce it. Applied after finding; re-audit required. |
| CS1-R09 | Primary evidence | `NFR-PLAT-001` was primary-owned by A04-MAC but cited only Linux scenarios; `AC-UI-002` was primary-owned by P02 but cited only integration evidence. | Add an exact primary-owned scenario and enforce this invariant. Applied after finding; re-audit required. |
| CS1-R10 | Table ownership | Parallel/addendum prefixes `registry_`, `alerting_`, and `operations_` conflicted with detailed schemas/migrations using `reg_`, `alert_`, and `ops_`. | Freeze the detailed prefixes consistently. Applied after finding; re-audit required. |
| CS1-R11 | Dependency DAG | `depends_on` and `parallel_after_approval` contained prose, ranges, contract names, and environmental conditions instead of resolvable plan IDs. | Use exact catalog IDs and validate an acyclic graph; keep live conditions outside dependency IDs. Applied after finding; re-audit required. |
| CS1-R12 | CAA-C12 | The baseline listed P01 as consumer of provider auth-flow/health/extension contracts despite CAA-C12; P01 also retained seven explicit Sync-gap rows. | P01 consumes safe capability/compatibility plus M02 workflow/application ports only; align baseline and plan. Baseline corrected; plan re-audit required. |
| CS1-R13 | CAA-C03 | A01/A03 normalized lists used `reauthorization_required`; M03 still described CTR-REG-008 coordinator/persistence ownership as unresolved. | Use canonical `reauthentication_required`; assign orchestration/persistence to M02 and protocol semantics to M03. M03 corrected; adapter re-audit required. |
| CS1-R14 | CAA-C13 | M07 mapped NFR-PERF-001 to “200 sessions,” substituting for the frozen subject of 100 registered accounts plus 200 simultaneously discovered real processes. | Restore exact subjects; optional session benchmarks are supplemental only. Applied after finding; re-audit required. |
| CS1-R15 | CAA-C17 | A02 made ownership of the OpenAI API lane conditional even though ownership is frozen; only capability maturity/support may depend on M0. | State A02 ownership unconditionally and gate actual capability support on M0. Assigned; re-audit required. |
| CS1-R16 | Exact consumers | Baseline omitted A04 Linux/macOS from provenance they explicitly consume, included them in database activation they do not consume, and omitted M06 from REG-004/PROV-002 it explicitly consumes. | Reconcile the exact baseline parties to the architectural use. Applied after finding; re-audit required. |
| CS1-R17 | Currentness | A04-MAC said the Linux peer plan was absent although it is cataloged; M08/DB/DEP described already registered CTR-DB-003/CTR-DEP-001 as missing additions. | Replace stale history with current Draft-aligned/approval-pending state. M08 corrected; remaining assigned; re-audit required. |
| CS1-R18 | P01 readiness | P01 retained seven `Sync gap` route rows and layout/registration blockers that its own section required to be resolved before synchronization. | Reconcile rows to current baseline or retain a BLOCK result; do not hide them in CS-1 prose. Assigned; re-audit required. |

## 4. Controls that were structurally sound in the first pass

- The catalog enumerated exactly 20 distinct plan IDs and paths.
- The requirement manifest enumerated 147 distinct source IDs with 140 V1 and
  seven post-V1 records; the first pass found semantic party/evidence issues
  listed above rather than missing IDs.
- Deferred records had no V1 scenario assignment and carried explicit guards.
- The contract baseline enumerated 97 distinct proposed contracts with one
  producer each and did not claim owner approval or implementation.
- Plans continued to label scenarios `Not Run`/Blocked and did not claim live
  provider evidence.
- No production dependency, application code, provider mutation, or default
  profile change was part of this audit.

These facts do not offset any blocking semantic finding.

## 5. Mandatory second pass

The second reviewer must inspect the actual corrected files, not this findings
table, and must at minimum:

1. re-run the draft and synchronized validators plus repository governance tests;
2. compare all CAA-C01..CAA-C17 resolutions to the affected plan bodies;
3. validate exact requirement producers and primary-owned scenarios;
4. validate all 57 configuration keys and `AGENTMONITOR_*` namespaces;
5. validate the exact plan-ID dependency DAG, table prefixes, migration slots,
   provider-extension paths, and shared writers;
6. compare P01's exact consumed contracts with the baseline;
7. run targeted stale-spelling/path/gap/currentness searches;
8. report any remaining failure as BLOCK without allowing a snapshot or CS-1
   Complete record.

Only after that pass is green may root generate the SHA-256 snapshot and the
separate CS-1 synchronization record. Owner approval, Milestone 0 evidence,
dependency admission, implementation authority, production tests, and live
verification remain later gates.
