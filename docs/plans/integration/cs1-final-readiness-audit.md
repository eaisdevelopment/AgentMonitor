# CS-1 independent readiness audit — corrected-corpus pass

- Audit ID: `CS1-READINESS-2026-09-18-02`
- Status: **PASS-CONDITIONAL**
- Review boundary: corrected 20-plan Draft corpus and shared CS-1 controls
- Reviewer role: independent skeptical readiness reviewer
- Authority: read-only finding report; no owner approval or implementation authority
- Test/live status: repository governance checks only; no production, provider,
  platform, browser, migration, or other T1–T7 behavior was executed
- Plan snapshot SHA-256: `9e6dbc0aa91a0dff7eb81689ff631dfc38bea98308e1e609f73b16b2e0eccc0e`

## 2026-09-20 scoped catalog/snapshot addendum

An independent bounded review compared the current synchronized snapshot
`ce910d73165ed9db8229c79abaa03129e8ba0f16e391908cc7a142067edcff0f`
with the 2026-09-19 reviewed snapshot above. Its result is
**PASS-CONDITIONAL on catalog/snapshot coherence only**: the changed automation
catalog and current snapshot agree, while all 20 plans and the other eight
controls are unchanged. This addendum does not revise the historical audit
date, scope, result, approval authority, release status, or live-verification
status.

Plan snapshot SHA-256: `ce910d73165ed9db8229c79abaa03129e8ba0f16e391908cc7a142067edcff0f`

## 2026-09-20 independent local-commit catalog review

The independent M1 reacceptance reviewer examined only the new
`AUTO-GIT-PREFLIGHT` catalog wording, its local-commit/push behavior, and the
resulting synchronized snapshot. The bounded result was **PASS for
catalog/snapshot coherence**: the snapshot renderer matches the current bytes,
only the `automation-routines` digest/size changed, local commit preflight
passes without claiming remote readiness, and explicit push preflight blocks
without a remote/upstream. This is not a renewed review of the 20 plan bodies
or the other eight controls, nor owner approval, implementation authorization,
hosted CI evidence, or a revision of the historical audit above.

Plan snapshot SHA-256: `793531850151ad12ad4210edbeadb2326c2f4bcf8844ac4a6f8b10e2f94ad875`

## 2026-09-20 M2-scoped contract rebind

The owner approved only the authenticated-shell M2 milestone and its referenced
module-plan slices through `/goal`; this does not approve the all-V1 Draft
corpus. M2 entry review and a separate migration/security review identified
and corrected four cross-plan discrepancies: IAM's unallocated outbox, bearer
Origin/Swagger behavior, cookie-plus-bearer error naming, and conditional
session-version exposure. Root also froze the Linux Argon2 work policy,
password-change token effect, logout mapping, and local port default in the
[M2 decision overlay](../../evidence/m2-contract-freeze.md). The changed M01
and P01 plans, contract/configuration/adoption baselines, and ownership digest
are rebound in the current exact snapshot. Historical CS-1 findings and their
original bytes remain historical evidence, not a claim that all V1 is newly
approved. M2 production and live-boundary tests remain Not Run at this rebind.

Plan snapshot SHA-256: `331a81a84c4362e079628bdb2c173bfdce0b76f9b664f59a9cb8b91de2c86423`

## 2026-09-20 M2 conditional-response rebind

The M2 scoped M01/P01 text now distinguishes stale active conditional targets
(`412 precondition_failed`) from terminal-state conflicts (`409`), records the
two one-time token issue responses' temporary no-`Location` exception within
the approved 13-route shell, and bounds the malformed-wire SafeProblem
exception to requests Uvicorn/h11 rejects before ASGI. Contract adoption,
parallel ownership, and the exact rendered snapshot agree with those plan
bytes. This is a bounded M2 reconciliation, not a renewed independent review
of the historical all-V1 Draft corpus or a claim that Story 4/M2 passed.
An independent bounded specification review confirmed the frozen semantics,
current session/token contracts, exact snapshot, and historical-attestation
boundary; it did not certify Story 4 or live milestone completion.

Plan snapshot SHA-256: `a3f306a540b7aa39d7af1c990de849d77878b9fc6e06ee706fb5463acd615ea8`

## 2026-09-20 M2 receipt-order and problem-type rebind

The current M2-only snapshot rebinds M01's optional typed rotation ETag
subject and P01's completed-receipt-before-stale-conditional rule, plus the
same-origin relative, authenticated, allowlisted local problem-document type.
Only M01/P01 plan bodies and their dependent adoption/ownership/baseline
digests changed. This is a scoped semantic reconciliation found by real HTTP
Red tests and independent review, not a new all-V1 approval or Story 4/M2
acceptance claim. Earlier CS-1 review bytes and dispositions remain intact.
An independent bounded specification review confirmed the final target-state
precision, M01/P01 contracts, and exact synchronized snapshot only.

Plan snapshot SHA-256: `b61ece314353d314e145a8bc384ec58e0949ec220fe172e8c73a6cf99437bbdb`

## 2026-09-20 M2 IAM list-query scope binding

Root's current M2-only query decision responds to the independent Story 4
specification finding without expanding M01: fixed existing list orders,
per-route sort/filter allowlists, and a P01 query/principal-bound cursor
envelope. The changed P01 plan, adoption and ownership digests are bound to
the exact rendered snapshot. `API-PURE-003/004/008` and browser/documentation
gates remain unaccepted until real tests and independent reviews pass; the
all-V1 Draft baseline and historical CS-1 audit are not newly approved.
Independent specification and QA reviewers accepted this bounded rebind; the
specification reviewer independently confirmed the synchronized plan and
documentation gates. No Story 4 source, browser, or dependency gate was
accepted.

Plan snapshot SHA-256: `f29c60c58ddc688235992ed2b654a0a310aab72c107c871bc70f133504475f93`

## 1. Decision

The corrected corpus closes the eighteen findings recorded in the
[first-pass audit](cs1-readiness-audit.md) and the later CS1-F01 event-topology
finding. The Draft planning gate is green, and this review found no remaining
semantic contradiction that prevents root from creating the immutable plan
snapshot and the separate full-plan synchronization record.

This is a conditional planning-readiness result only. The exact snapshot and
full synchronization record have now been regenerated and bound after the
2026-09-19 correction pass. The corpus remains Draft, owner-unapproved,
implementation-unauthorized, unimplemented, and unverified on live systems.

## 2. CS1-F01 closure — exact event topology

CS1-F01 is closed in the exact corrected files:

1. The [contract baseline](../contract-baseline.toml) now contains the exact
   `[event_topology]` record `CTR-EVT-TOPOLOGY-001`. It selects
   `module_owned_transactional_outboxes`, assigns PLAN-INT semantic governance
   and PLAN-DB reusable persistence mechanics, assigns producer rows to the
   producing module and receipts/checkpoints to the consuming module, requires
   published event-storage ports, and sets both `central_event_table` and
   `cross_module_table_access` to `false`.
2. The record allocates exactly one unique producer outbox to each M02–M08:
   `reg_event_outbox`, `provider_system_event_outbox`,
   `collection_event_outbox`, `capacity_event_outbox`,
   `runtime_event_outbox`, `alert_event_outbox`, and `ops_event_outbox`.
3. M02–M08 each adopt `CTR-EVT-TOPOLOGY-001`, their exact table, atomic
   producer append, consumer-owned processing receipt/checkpoint, and
   published-port dispatcher boundary. A central event table/journal and
   cross-module SQL are no longer implementation alternatives.
4. PLAN-DB repeats all seven allocations in its migration matrix, limits
   shared mechanics to producer-published ports, and prohibits shared event
   tables and direct cross-module table access.
5. PLAN-INT and the contract register distinguish PLAN-INT governance,
   PLAN-DB mechanics, module-owned rows, and consumer-owned processing state.
   The parallel manifest adds one dedicated shared-writer record for registry,
   dispatcher composition, and event-storage port registration while leaving
   row semantics with the producing/consuming modules.
6. Searches found none of the former central-versus-module conditional
   alternatives, and the dedicated real-checkout topology test passed.

The topology record deliberately retains `owner_approved = false` and
`implementation_authorized = false`. Approval of exact port/schema details and
real implementation evidence remain later gates; they do not reopen the
selected physical ownership model.

## 3. First-pass correction verification

| First-pass ID | Final re-audit result | Evidence |
|---|---|---|
| CS1-R01 | Corrected | P01 consistently distinguishes replay policy `one_time_secret_non_replayable` from HTTP 409 problem code `one_time_secret_not_replayable`; M01, P01, PLAN-INT, and the baseline agree. |
| CS1-R02 | Corrected | No legacy `AM_*` configuration token was found in the 20-plan corpus; namespaces use `AGENTMONITOR_*`. |
| CS1-R03 | Corrected | `configuration-baseline.toml` declares 57 unique, complete key records: 21 `proposed_exact` and 36 truthfully `decision_required`. Every exact registered name starts with `AGENTMONITOR_`. |
| CS1-R04 | Corrected | M05 sections 0, 4.9, 13.4, and 15 preserve one-way M05-to-M07 semantics and state that M07 threshold policy is not delivered to M05. |
| CS1-R05 | Corrected | A04-LINUX, A04-MAC, M06, and P01 use the one-file `contracts/<family>_v<major>.py` convention; the P01 scan found no positive package-per-version import. |
| CS1-R06 | Corrected | A01/A02/A03 and the parallel manifest use the exact `backend/src/agentmonitor/contracts/providers/<provider>/<capability>/v1/**` namespace. The manifest separates semantic ownership from the allocated wave-writer role. |
| CS1-R07 | Corrected | P01 section 6 publishes exactly the baseline's five P01-produced contracts and positively enumerates exactly the baseline's 60 P01-consumed contracts. No missing or extra positive ID remained. |
| CS1-R08 | Corrected | All 147 requirement records include each cited contract's producer among the primary/supporting parties. |
| CS1-R09 | Corrected | Every one of the 140 non-deferred requirements cites at least one scenario owned by its primary catalog plan. |
| CS1-R10 | Corrected | Parallel ownership and plan/schema text agree on `iam_`, `reg_`, `provider_system_`, `collection_`, `capacity_`, `runtime_`, `alert_`, and `ops_`. |
| CS1-R11 | Corrected | All 87 `depends_on` values and all 38 `parallel_after_approval` values resolve to exact catalog IDs; the `depends_on` graph is acyclic. |
| CS1-R12 | Corrected | P01 consumes only `CTR-PROV-002` from the provider family and reaches provider reauthentication through M02 application projections. No P01 `Sync gap` row remains. |
| CS1-R13 | Corrected | Normalized plans use `reauthentication_required`; provider-native `reauthorization_required` is explicitly mapped at the adapter boundary. M02 owns workflow/persistence and M03 owns provider protocol semantics. |
| CS1-R14 | Corrected | M07 maps NFR-PERF-001 to 100 registered accounts and 200 simultaneously discovered real processes; session-only load is explicitly supplemental. |
| CS1-R15 | Corrected | A02 ownership of the OpenAI API lane is unconditional; M0 controls capability maturity/support, not ownership. |
| CS1-R16 | Corrected | The baseline includes A04-LINUX/A04-MAC as `CTR-COMMON-004` consumers, excludes them from `CTR-DB-003`, and includes M06 for `CTR-REG-004` and `CTR-PROV-002`, matching the affected plan bodies. |
| CS1-R17 | Corrected | A04-MAC describes the present Linux peer; M08/DB/DEP no longer say registered Draft contracts are absent additions. |
| CS1-R18 | Corrected | P01 has no `Sync gap`/`synchronization gap` occurrence, uses the frozen contract layout, and its published/consumed ID sets match the baseline. |

These closures remained intact during the bounded CS1-F01 regression pass.

## 4. CAA-C01 through CAA-C17 body review

| Resolution | Result of corrected-body review |
|---|---|
| CAA-C01 | Lifecycle direction is aligned: full synchronization and owner approval precede W0. The synchronized gate remains red and no implementation is authorized. |
| CAA-C02 | Dashboard authentication and provider reauthentication retain distinct code, HTTP, session, and recovery meanings across M01/M02/adapters/P01. |
| CAA-C03 | Canonical normalized state is `reauthentication_required`; native/legacy spellings are boundary inputs only. |
| CAA-C04 | Replay policy and HTTP problem code are distinct and consistent. |
| CAA-C05 | M06 is the sole semantic producer of `ProcessInspectionPortV1`; Linux/macOS implement it. |
| CAA-C06 | FND owns portable platform semantics; Linux/macOS implement platform-specific mechanics. |
| CAA-C07 | P01 owns API semantics, FND generator mechanics, PLAN-INT generated-artifact writing, and P02 wrapper consumption. |
| CAA-C08 | M08 workflow, PLAN-DB database activation, and PLAN-DEP artifact/unit activation remain separately typed; stale registration wording was removed. |
| CAA-C09 | M08 owns maintenance intent/state; DEP owns fenced service execution. |
| CAA-C10 | M08 consumes narrow DEP service facts, DEP may consume M08 readiness, and liveness remains independent. |
| CAA-C11 | Capacity classification and alert policy are one-way M05 to M07. |
| CAA-C12 | P01's exact contract set and symbol restrictions enforce the thin provider boundary. |
| CAA-C13 | The two exact performance subjects and real-boundary restrictions are restored. |
| CAA-C14 | SQLite implementation paths consistently use `adapters/persistence/<module>/sqlite/**`. |
| CAA-C15 | Public V1 contract families consistently use `<family>_v<major>.py`. |
| CAA-C16 | Provider extension paths use the full backend namespace and remain adapter-owned/M03-governed. |
| CAA-C17 | A01/A02/A03 own Anthropic/OpenAI/Ollama API lanes respectively; M0 decides capability maturity. |

The CAA resolutions remain reflected after the CS1-F01 edits; no regression was
found in their affected plan bodies.

## 5. Machine-readable inventory results

- Planning catalog: 20 records, 20 unique IDs, 20 unique paths.
- Scenario corpus: 2,337 unique plan-scoped scenario IDs; no cross-plan
  duplicate and no requirement reference to an undefined scenario was found.
- Requirement ownership: 147 unique records: 137 `approved`, three
  `discovery`, and seven `deferred`.
- Requirement semantics: all 140 non-deferred records have a catalog primary,
  a primary-owned scenario, valid scenario parties, and all contract producers
  represented in the requirement parties.
- Deferred scope: all seven records use `POST-V1`, have an explicit V1 guard,
  and have no V1 supporting-plan, contract, scenario, or evidence assignment.
- Contract baseline: 97 unique records: 63 `proposed_aligned` and 34
  `evidence_blocked`; its approval, synchronization, implementation, and live
  flags remain false.
- Configuration baseline: 57 unique complete keys, all under
  `AGENTMONITOR_*`; 36 unresolved value/policy decisions remain honestly
  `decision_required` and therefore do not authorize implementation.
- Parallel manifest: 20 unique SHA-bound units; exact catalog-ID references;
  acyclic dependency graph; complete nonshared code/test/documentation write
  sets; corrected table prefixes; exact provider-extension paths; public
  contract writer coverage; and 16 unique shared-writer records. Unit/unit,
  unit/shared, and shared/shared collisions are rejected. Concrete
  agent/resource assignment is still required before each implementation/live
  wave.

## 6. Claims and scope guards

The reviewed current baselines retain `owner_approved = false`,
`implementation_authorized = false`, `synchronized = false`,
`approved = false`, and `live_verified = false` where applicable. Plan statuses
remain Draft/pending, and scenario text preserves Passed/Failed/Blocked/Not Run
distinctions. Searches found future/precondition/evidence-status uses of
“Passed,” not a current production or live pass claim.

No production code, dependency admission, migration, build, deployment,
provider interaction, profile change, production-behavior TDD evidence, M0 observation,
or live verification was performed by this audit. The seven deferred guards
remain fail-closed for email/native/messenger delivery, routing/switching,
cross-account checkpoint recovery, content capture, remote/multi-user use, and
additional providers.

## 7. Commands and observed results

| Command | Exit | Observed result |
|---|---:|---|
| `python3 tools/planning/validate_plans.py --stage draft-complete` | 0 | `PLANNING GATE: PASSED (draft-complete)` |
| `python3 tools/docs/check.py` | 0 | `DOCUMENTATION CHECK: PASSED (96 Markdown files)` |
| `python3 tools/planning/validate_plans.py --stage synchronized` | 0 | Exact 20-plan, nine-control snapshot and both review bindings passed |
| `python3 -m unittest tools.planning.test_validate_plans` | 0 | 12 real-checkout planning tests passed |
| `python3 tools/automation/run.py AUTO-PLAN-CHECK` | 0 | Canonical synchronized planning routine passed |
| `python3 tools/automation/run.py AUTO-DOCS-CHECK` | 0 | Canonical documentation routine passed |
| `python3 tools/automation/run.py AUTO-M0-G0` | 0 | Restricted plan-only M0 G0 approval remains exact; no provider authority granted |
| `python3 tools/automation/run.py AUTO-TEST` | 0 | 31 repository-governance tests passed; application T1–T7 remain out of scope/Blocked |
| `python3 tools/automation/run.py AUTO-GIT-PREFLIGHT` | 3 | Truthful Blocked result because the checkout is not a Git worktree |

Additional read-only Python `tomllib`/regular-expression checks parsed the
catalog, all catalog plan bodies, contract/configuration/requirement/parallel
manifests, scenario IDs, requirement parties, and P01 section 6. They produced
the exact counts and zero-delta results in sections 3 and 5. Targeted `rg`
searches checked legacy configuration prefixes, replay spellings, auth-state
spellings, contract layouts, provider paths, table prefixes, stale Sync-gap and
registration wording, performance subjects, API-lane ownership, and current
approval/live claims. The bounded follow-up searches verified the exact
CS1-F01 closure and absence of the former conditional alternatives.

## 8. Gate disposition

Status is **PASS-CONDITIONAL**. The integration steward has created the exact
`docs/plans/plan-baseline.toml` bytes and bound this audit plus
`docs/plans/integration/cs1-full-plan-synchronization.md` to their digest. The
executable synchronized gate is the authority for whether those artifacts
remain coherent. This audit does not grant owner approval or implementation
authority.

Owner approval, implementation authorization, Milestone 0 and other live
evidence, dependency admission, production code, and application tests remain
absent. A green future CS-1 synchronization gate records the Draft planning
baseline only and grants none of those later authorities or evidence claims.

## 9. 2026-09-19 independent correction re-audit

The follow-up audit rejected the earlier parallel-ownership claim because its
manifest covered selected source roots but omitted module tests,
documentation, and producer contract files. That finding is closed as
`CS1-F02`:

1. `parallel-ownership.toml` schema 1.1 now binds every unit to the exact SHA-256
   of its current plan and declares its complete nonshared repository write
   surface in `write_paths`.
2. All 20 units allocate their code, tests, documentation, and optional
   sanitized evidence paths. Unlisted repository paths remain locked.
3. Sixteen shared-writer records allocate the central contract files,
   provider-extension namespace, contract-test registration, composition,
   migrations, OpenAPI/client artifacts, frontend shell/shared paths,
   automation, CI, release artifacts, and planning controls.
4. The real-checkout validator rejects stale plan hashes, missing test or
   documentation allocation, uncovered literal public contract files, and any
   unit/unit, unit/shared, or shared/shared path collision.
5. The ownership test was observed Red against the prior manifest because
   PLAN-M0 had no plan digest/write set. It passed after the complete allocation.
6. The independent read-only re-audit returned PASS: 20 SHA-bound units, 16
   shared writers, zero ownership violations, complete public-contract writer
   coverage, corrected maturity wording, and correct M08/P01 API direction.

No production implementation, dependency, provider access, live verification,
or authority expansion occurred during this correction pass.

## 10. 2026-09-20 M2 contract-clarification rebind

Plan snapshot SHA-256: `f5daafacb7d30c27454c53b017ea89b2e44a2ed6ee940ece718df60d7c255bf1`

The M2-approved auth-first password-change replay clarification changed only
PLAN-M01 and PLAN-P01 text, their two manifest digests, and this mechanical
snapshot binding. Independent M2 specification review accepted the 401/409
ordering and bearer receipt isolation. This rebind preserves the historical
CS-1 PASS-CONDITIONAL finding; it does not claim M2 implementation or live tests.

## 11. 2026-09-20 M2 security-event consumer addendum

Plan snapshot SHA-256: `06bf3617a1b08f8e3949e839bd686e7bc332751ecfe331f7b1ec3d5490e55729`

Independent M2 QA reviewed the exact PLAN-P01 adoption of `CTR-IAM-008`, the
M01/P01 plan wording, 20-plan snapshot/ownership hashes, and the closed
same-owner M01 import allowance. The bounded review found no route, schema,
provider, or M3 scope expansion; the 174-test import-boundary suite passed.
The historical CS-1 PASS-CONDITIONAL result remains a Draft planning finding,
not a claim that M2 HTTP, generated-client, browser, live-owner, or elapsed-time
tests have passed. This addendum rebinds the reviewed M2 slice only.

## 12. 2026-09-21 M2 local-test catalog addendum

Plan snapshot SHA-256: `9960b745704e6b80c69da1e5f99f9cedc85fa49e1d5c616c871ef1d07e22ae6e`

The M2 local-test catalog and exact snapshot now agree after the first
canonical M2 run found a stale `automation-routines` control digest and byte
count. This bounded rebind changes no plan body, other control, historical
CS-1 finding, owner authority, provider verification, or milestone acceptance.
The full M2 gate must be rerun against the corrected checkout.

## 13. 2026-09-22 M3 additive consumer binding

Plan snapshot SHA-256: `bba633ea238b9fbaa874b529de68c3c65d4d7769cb6c17dc3d52e2ffe199b59d`

The current M3 snapshot records only additive, non-breaking consumer adoption
for the Claude capacity path: PLAN-A01 consumes `CTR-COL-002` and
`CTR-COMMON-003`, and PLAN-M05 consumes `CTR-COL-004`. The contract schemas and
versions are unchanged. This root integration binding preserves the historical
independent `PASS-CONDITIONAL`; it is not a renewed all-V1 audit, owner
approval, M3 acceptance, or live-provider result.

## 14. 2026-09-22 M3 runtime consumer binding

Plan snapshot SHA-256: `0ce75e14b6618fd5c2b2a77cd328772481173256e1d9be707d3768272c870704`

The M3 runtime slice adds only the implemented PLAN-M06 use of `CTR-DB-001`,
the PLAN-A04-LINUX use of `CTR-RUN-001`, and existing Foundation composition
consumers. Contract versions are unchanged. This preserves the historical
`PASS-CONDITIONAL` result and does not claim live same-account acceptance.

## 15. 2026-09-23 M3 Claude runtime binding

Plan snapshot SHA-256: `0f01bfd52b719c4de20b76024a0aeb6531edf1acc36c0d1410a439069ed3a129`

The synchronized snapshot records the already implemented Foundation and
Claude adapter consumption of registry, provenance, and runtime contracts used
by the transparent Claude telemetry composition. It also binds the additive
M02 provider-fingerprint operations. Contract versions are unchanged. This is
a mechanical M3 consumer/snapshot rebind, not owner approval or live acceptance.

## 16. 2026-09-24 M3 live-gate binding

Plan snapshot SHA-256: `4e34a1bff2d81307e422ac105aae1927358e6176ccc23e490af9637e59cfdbdc`

The automation catalog and standard now define the canonical M3 real-owner
browser gate. The synchronized snapshot changes no module plan, public contract,
owner authority, provider state, or M4 scope. This is a mechanical control
binding, not a renewed all-V1 approval or an M3 acceptance claim.

## 17. 2026-09-24 M3 exit and mutation gate binding

Plan snapshot SHA-256: `6c0687cc5dbcf9c0f6a8319415e4bcfc928a186273a2510dc91758c291158aab`

The automation catalog and completion standard now register the fail-closed
`AUTO-M3-EXIT` and real critical-policy `AUTO-MUTATION` routines. No module
plan, public contract, owner authority, provider state, or M4 scope changed.

## 18. 2026-09-25 local milestone gate-policy rebind

Plan snapshot SHA-256: `b1cb24799d8c692f13bb5abab84159de44e94a595dba5430500c2d1c35da1eb6`

The local execution policy treats detached M0 reviewer records as advisory and
gates milestone execution on current technical evidence and real boundary
checks. M03/M04/M05/A01/A02/A03 plan hashes, contract adoption, ownership,
automation catalog, and snapshot were rebound together. This changes no
provider claim or global V1 acceptance status.

## 2026-09-28 bounded Claude polling consumer/catalog binding

Plan snapshot SHA-256: `6ad4c8d41beea6bcc4ca6c5423a021a2a325d6390acd6edb5d9cd2da175cad13`

The exact current controls add Foundation's read-only consumption of
`CTR-REG-003` and `CTR-REG-005` at `1.0.0`, and register `AUTO-CLAUDE-POLL`
for the approved one-profile dashboard increment. No producer meaning, payload,
contract version, module plan, or broad milestone acceptance changes. This is
a mechanical adoption/catalog binding; it does not claim a new independent
CS-1 audit. Historical review statements remain historical. Current scope and
real evidence are recorded in
[the polling delivery](../../evidence/claude-dashboard-polling.md).

## 2026-09-28 account workspace identity adoption

Plan snapshot SHA-256: `d70615d4d51f0d0ff9d90ab9b22d8bc42516c9c9c7bf73122316f195bec71611`

The exact controls declare Foundation and P01 consumption of M03
`CTR-PROV-005` for the owner-directed account workspace increment. The
existing Draft statuses and historical audit conclusions are preserved;
this mechanical binding is not a new independent audit or broad milestone
approval. See [the bounded change plan](account-workspace-ui-change.md).

## 2026-09-28 managed Claude connection automation binding

Plan snapshot SHA-256: `1742d12b035aea5d74022ea4f68246522d860c1768ea0bffc4daaffd0adb8a4e`

The approved additional-account connection registers `AUTO-CLAUDE-MANAGED`
and documents its bounded real native/SQLite/shared-browser verification.
The exact automation controls and snapshot are rebound together. The twenty
module-plan bytes, global Draft flags, and historical audit conclusions are
preserved. This mechanical control binding does not claim a new independent
planning audit or full M4 acceptance. See the
[connection change](claude-managed-account-connection-change.md) and
[connection evidence](../../evidence/claude-managed-account-connection.md).

## 2026-09-28 dashboard Claude connection control binding

Plan snapshot SHA-256: `7ab4d65d30e7c75cbbc3c7b97eea619b95c6200a3ed9037d3a48c4129a27c4b2`

The owner-directed dashboard connection adopts M03 `CTR-PROV-007` V1
in Foundation and P01, and registers the bounded `AUTO-CLAUDE-CONNECT`
routine. Existing operation shapes, contract producers, module plan
hashes, and historical Draft flags are preserved. This is a mechanical
control binding, not an independent planning audit or M4 acceptance.
See the [approved change](claude-managed-account-connection-change.md)
and [current evidence](../../evidence/claude-dashboard-connection.md).

## 2026-09-29 trusted LAN routine control binding

Plan snapshot SHA-256: `e500c5392c3dd25a2b1acd5073a779e7e4e4efa9b98a4fe3cec700553c5e5fb8`

The owner-directed [trusted LAN change](trusted-lan-dashboard-change.md) adds
`AUTO-LAN-DASHBOARD` and its completion-standard entry. Only the two changed
automation control digests and byte counts were rebound. All twenty module
plan hashes and historical Draft/approval flags remain unchanged. This is a
mechanical control binding, not a new independent planning audit or full M4
acceptance. The bounded implementation review and real boundary evidence are
recorded separately in the LAN change evidence.

## 2026-09-29 owner process association control binding

Plan snapshot SHA-256: `8812c3786f9a5222a1a91e69aca703d84f10514ee4f7f5e78979ae7cfbc2c35c`

Root reviewed the bounded M06 settings allocation and canonical
AUTO-ACCOUNT-AGENTS catalog/standard addition. All twenty Draft module plans
remain unchanged; historical conditional planning conclusions and broader
approval state remain unchanged. Independent bounded backend/UI implementation
review findings were corrected and are recorded in the live-account-agents
evidence. Owner-completed persistence acceptance remains pending; this binding
is synchronization of the changed controls, not full M4/M06 release approval.


## Focused M4 adoption binding — 2026-09-29

Plan snapshot SHA-256: `2b51fcaca4358b1a619b33b4ea7c4c4211ad59c6b982985ccefda6f084f22a49`

Independent read-only review: `/root/m4_capacity_plan` inspected the actual
M05/M08 plan and contract-baseline/adoption diffs and reported Passed. The
changes add REG-009 consumption by M05, FND-002 lifecycle consumption by M08,
and the approved M05 metadata revision 0703 after the three M07 revisions.
Root rebound the two master-plan digests and made the allocation disjoint
(M07 owns 0700..0702 and 0704..0799; M05 explicitly owns 0703).
Versions and maturity remain unchanged. Full master plans remain Draft and
their owner approval and implementation authorization flags remain false;
implementation authority is confined to the approved focused M4 packets.
This review binds planning synchronization only. It does not report a product,
live acceptance, migration, or full M4 completion result.

Plan snapshot SHA-256: `9109f19353e317d2a7656653ab68cb8764e9e29acb1dd543c6a8fb24c6e37e1a`

## M4 alert delivery composition binding — 2026-09-29

Plan snapshot SHA-256: `9ca1d5840aa88fdcd4cf4cbb68602f38de813a82e190cf4e99bc3f283fefdfbf`

The contract baseline now records PLAN-FND composition's consumption of the
existing `CTR-ALERT-002` alert receipt and `CTR-EVT-001` durable event types.
This is an exact adoption correction for the implemented M4 delivery seam; it
does not change contract versions, plan approval, or wider readiness status.

## 2026-10-02 M3 scope-ownership addendum

The owner-approved M3 scope correction adds `AC-M3-001..007` as seven
one-account Claude milestone gates. Exact ownership now contains 154 source
IDs: 144 approved, three discovery, and seven deferred. PLAN-INT owns their
milestone evidence closure, with the producing module, adapter, API, UI, and
persistence plans named explicitly. Full provider-fleet and release criteria
retain their existing owners. This addendum changes no module contract or
implementation authority.

Plan snapshot SHA-256: `6350ad1239c4826e993f826ef682e23f312ff14cd539614f22e376b852c42b03`

## 2026-10-03 safe current M3 gate control rebind

The current snapshot binds the canonical read-only `AUTO-M3-EXIT` successor in
the automation catalog and the corresponding bounded completion standard.
Only the `automation-routines` and `automation-standard` control digests and
byte counts changed; historical CS-1 conclusions remain historical. This
rebind makes no plan, contract, provider, or acceptance expansion and does not
claim a current M3 gate result or milestone acceptance.

Plan snapshot SHA-256: `c3be3c580dd9f9e77b97f712b25588d9168904950d4d0cdf8bdb87c20a5fa9c5`

## 2026-10-03 safe current M4 gate control rebind

The current snapshot binds the canonical `AUTO-M4-EXIT` successor to a clean
revision, the selected AgentMonitor service, six distinct Claude identities
whose reported addresses match their administrator records, fresh post-restart
quota/history lineage and a private
receipt. Only the `automation-routines` and `automation-standard` control
digests and byte counts changed. Historical CS-1 conclusions remain
historical; this rebind makes no provider, product-contract or schema expansion
and does not claim that the live M4 gate or milestone acceptance has passed.

Plan snapshot SHA-256: `da2e36813484ceb16e5724cd18e77463d896d681c53e162ee2bcaa198b233761`

## 2026-10-03 current M3 technical-suite scope correction

The [focused PLAN-INT packet](m3-current-technical-suite-scope-change.md)
binds the owner-directed one-account technical test scope while leaving the
reviewed M0 handoff and all nine snapshot controls then unchanged. At that
point the canonical renderer produced the historical baseline SHA below. This is no new CS-1
approval, plan, contract, provider, or acceptance expansion and does not claim
the clean current-revision M3 exit passed.

Plan snapshot SHA-256: `c3be3c580dd9f9e77b97f712b25588d9168904950d4d0cdf8bdb87c20a5fa9c5`

## 2026-10-05 M4 Overview presentation gate extension

The current snapshot binds the real authenticated account-quota Overview
verifier into the existing `fleet_browser` lane of `AUTO-M4-EXIT`. It covers
the owner-approved interactive sorting and separate Collection / History page
after the fresh six-account witness. Only the `automation-routines` and
`automation-standard` control digests and byte counts changed. Historical CS-1
conclusions remain historical; this extension changes no canonical module
plan, public contract, provider behavior, schema, dependency, or M4 acceptance
state.

Plan snapshot SHA-256: `559468c158d5b3727faf547026cdd18a8c25b59e82025375c7e2384f262611b0`

## 2026-10-07 M5 Codex capacity contract adoption

The current snapshot binds the approved focused M5 packet's use of existing
`CTR-COL-002` collection admission and `CTR-COMMON-003` exact quantities to
PLAN-A02. Only the two consumer registrations, their generated adoption
projection, and the snapshot control digests changed. Contract versions,
producers, maturity, and all canonical plan bodies remain unchanged. This is a
bounded mechanical registry rebind; it does not renew the historical all-V1
readiness audit or claim M5 implementation, live verification, or completion.

Plan snapshot SHA-256: `26c8f1b5be85121408184005e647a20fc4eb9e69dea128862b7d515a96c67be6`

## 2026-10-07 M5 completion-automation control rebind

The current snapshot binds the canonical `AUTO-M5-ALERT-WITNESS` prerequisite
and `AUTO-M5-EXIT` completion command in the automation catalog and completion
standard. Only the `automation-routines` and `automation-standard` control
digests and byte counts changed. This mechanical rebind makes no plan,
contract, provider, schema, implementation, live-verification, or milestone
acceptance claim; the approved focused M5 packet and its executable gates
remain the authority for those results.

Plan snapshot SHA-256: `221ed2d0202a77ad4d107685fc1867d03658fed51534cc2b3b71c92657f9e47d`

## 2026-10-07 M5 implementation gate reconciliation

The current snapshot binds the completed M5 automation definitions, including
managed-profile syscall containment and the final local gate lanes, to the
canonical automation catalog and completion standard. The provider deadline
widening, service drain, pagination implementation, test inventory, and any
later live results remain evidence outside this synchronized planning snapshot.
This mechanical rebind changes no canonical module plan, public
contract version, approval flag, or milestone acceptance state.

Plan snapshot SHA-256: `2c37537514d50a8abf1890fdff9fc53af442b6e627cc13e91fb60f14b2ecae2b`

## 2026-10-08 M5 stale-prerequisite recovery control rebind

The current snapshot binds `AUTO-M5-ARCHIVE-PREREQUISITES` in the automation
catalog and completion standard. The routine has the approved narrow purpose
of preserving stale private M5 prerequisite evidence before a new create-once
run. Only the two automation controls changed. This mechanical rebind changes
no canonical module plan, public contract version, approval flag, live result,
or milestone acceptance state.

Plan snapshot SHA-256: `451deff945dcb532dcbd134e6f9e4eec138d87083b4940bc76ee10a29306e603`

## 2026-10-08 M5 archive race-safety control correction

The current snapshot records the reviewed correction that makes archive moves
and rollback atomic without replacement and serializes archive with final M5
receipt creation. Only the completion automation standard changed. This
mechanical correction changes no module plan, public contract, approval flag,
live result, or milestone acceptance state.

Plan snapshot SHA-256: `22e312a4f907bde4f17026b6f97a9c933b22e89ee3a4c348df2b31d1f42e0780`

## 2026-10-08 M5 receipt-scope lock correction

The current snapshot records the reviewed correction that serializes archive
and final receipt creation across every owner data root using the one shared
checkout receipt scope and a nonreplaceable Linux kernel guard. Only the
completion automation standard changed. This mechanical correction changes no
module plan, public contract, approval flag, live result, or milestone
acceptance state.

Plan snapshot SHA-256: `6b1ea0fd2117dc1d5a173df69bf5f59122ef9a42ec736a473ea71c61bd294215`

## 2026-10-09 dashboard 24-hour session policy rebind

The current snapshot binds the owner-approved focused
[dashboard session change](dashboard-session-24h-change.md) to the exact M01
draft overlay, its generated contract-adoption projection, the M01 ownership
digest, the fixed 86,400-second configuration allocations, and the automation
catalog wording that keeps literal 24-hour elapsed expiry separate. Existing
contract IDs and versions, the all-V1 M01 Draft status, migration and dependency
state, and the absence of a literal 24-hour elapsed observation remain
unchanged. Historical snapshot bindings above remain historical. This bounded
mechanical rebind does not approve the full M01 plan or claim the Not Run
elapsed observation passed.

Plan snapshot SHA-256: `fb47bd4d18853398c21a6d5f0029a4c30578311a7d4703156efc9429f9a250f7`

## 2026-10-09 existing-session wording correction rebind

The current snapshot binds the reviewed M01 clarification that an existing
session preserves both its issued absolute deadline and its issued idle window;
accepted activity continues under that old window. Deployment does not replace
either value with the new 86,400-second policy and performs no row rewrite.
Only the M01 plan bytes and their generated adoption, ownership, and snapshot
bindings changed. Historical bindings remain historical, and this correction
adds no contract version, migration, dependency, or elapsed-live claim.

Plan snapshot SHA-256: `7fe722823aa660845d10d006228032ad3d168c9db26958e4902db06e04d9c7c7`

## 2026-10-11 Overview provider-filter automation control rebind

The current snapshot binds `AUTO-DASHBOARD-PROVIDER-FILTER` in the automation
catalog and completion standard. The focused P02 routine builds the production
frontend and verifies the authenticated real mixed-provider Overview across
provider and organization selection, manual and scheduled refresh, responsive
layouts, and zero API mutations. Only the `automation-routines` and
`automation-standard` control digests and byte counts changed. This mechanical
rebind changes no canonical module plan, public contract, provider behavior,
schema, dependency, approval flag, live result, or milestone acceptance state.

Plan snapshot SHA-256: `a59395be92d354692182a6e8c290029a474ce71a4a15c876f71df27680d963b6`

## 2026-10-16 M5 exact-revision service-activation control rebind

The current snapshot binds the approved `AUTO-M5-SERVICE-ACTIVATE`
prerequisite in the automation catalog and completion standard. The control is
limited to selecting one detached, clean, committed M5 worktree under the
existing dashboard user service; revalidating that HEAD and the service/source
binding at every M5 evidence boundary; preserving the existing
data/config/network/provider-tool selections; applying the approved 45-second
candidate drain bound; and restoring the exact retained trusted
`77a3bad12a096a81587b94b8981ceee812b6445b` unit/runtime automatically on
failure.

PLAN-DEP/D01 `0.2.0-draft` now cross-references the active owner's exact M5
exception while preserving all broader Draft restrictions, pending approvals,
proposed contract meaning, and blocked `AUTO-DEPLOY` state. Its plan digest,
generated contract-adoption binding, reviewed parallel-ownership binding, and
the two automation controls changed. Historical CS-1 conclusions and the other
19 canonical module-plan hashes remain unchanged. This rebind records no live
transition, M5 evidence, completion, PLAN-DEP approval, or acceptance result.

Plan snapshot SHA-256: `50e786deadb666da6ca21ef21a310f4d3c8b1d9ad344ee83a1ff3db4597cded5`

## 2026-10-16 M5 transition serialization and receipt-binding control rebind

The current snapshot binds the reviewed M5 correction that serializes the
bounded service transition with `AUTO-M5-EXIT`, requires the exact successful
activation and rollback-drill receipt before final completion, and records its
digest and lane in the private M5 receipt. The automation catalog and
completion standard now state that bounded behavior. Only the
`automation-routines` and `automation-standard` control digests and byte counts
changed. The 20 canonical plan bodies, public contracts, approval flags, and
milestone state remain unchanged. This mechanical rebind records no live
activation, rollback drill, M5 exit pass, or owner acceptance.

Plan snapshot SHA-256: `f04fecc5d69ec19f10f02b078992885cabd90720386f92073cf6dcb71b9670c5`

## 2026-10-16 M5 corrective-rollover and receipt-custody rebind

The current snapshot binds approved M5 focused plan 1.4.0 and the bounded
PLAN-DEP/D01 exception to the one exact correction for the completed
`6bfa69dc13cc9e1ded9c6baa6e803cb99bc8c20b` service transition. It preserves
the complete old transition evidence through an atomic owner-only archive,
requires a typed rerun after restoring and proving the trusted service, and
revalidates the sole completed archive before selecting the corrected detached
revision.

The same snapshot binds safe first-use creation of only the exact private M5
receipt directory and the final descriptor-relative canonical-entry check for
the retained receipt inode. The PLAN-DEP plan digest, its contract-adoption and
parallel-ownership bindings, and the two automation controls changed. The
other 19 canonical plan bodies, public contracts, approval flags, and milestone
states remain unchanged. The historical `6bfa69d` rollback drill and activation
passed; corrected rollover/reactivation and `AUTO-M5-EXIT` remain Not Run, so
M5 remains Intermediate and its canonical gate state remains `not_run`.

Plan snapshot SHA-256: `1716271928ec730f646bb2602b128cd99ba7e92ba7c5c8d4c470892f840cdac6`

## 2026-10-16 approved M5 complete-scope lifecycle and second-rollover rebind

The current snapshot records the owner-approved M5 focused plan 1.5.0
correction and the corresponding PLAN-DEP/D01 planning exception. Real service
evidence shows that a latest complete one-window Codex collection left one
stale prior-run window in the public current set. The approved correction
applies the existing
`FR-QUOTA-001` / `M05-PURE-005` complete-scope lifecycle rule and limits the
required deployment step to one exact evidence-preserving rollover into a
separate fixed singleton archive namespace from
`063445154bca0bf5ec43db94ba57c17fd193fd99`.

Bounded implementation readiness is granted only for the exact correction and
second rollover through the focused plan's Red/Green/refactor, review,
clean-candidate, and fail-closed preconditions. The behavioral Red remains
unresolved, production implementation and the second rollover are Not Run, and
`AUTO-M5-QUOTA-WITNESS` would still block
`m5_quota_current_lineage_required`. No public contract, schema, migration,
dependency, automation command, canonical module approval flag, gate result,
or milestone state changes through this documentation-only rebind.

Among synchronized baseline inputs, the PLAN-DEP body, generated
contract-adoption binding, reviewed parallel-ownership binding, and plan
snapshot changed. The other 19 canonical plan bodies and canonical module
approval flags remain unchanged. The completed first corrective rollover and
activation of `0634451` are the real premise for this approved correction. Any
separate sanitized checkpoint reconciliation remains independently controlled
and must keep M5 Intermediate, acceptance unrecorded, and its canonical
completion gate `not_run` until the gate and owner acceptance actually pass.

Plan snapshot SHA-256: `6711bef89419d379fb77695154749c20b211bca22a9c48a7281046243604f628`

## 2026-10-16 M5 1.5.0 postimplementation control rebind

The current snapshot now binds the owner-approved M5 focused plan 1.5.0 to the
implemented complete-scope native-window lifecycle policy and the bounded exact
second-rollover control. The existing Capacity suite passed 71 tests, the
service-activation suite passed 43 tests, and the module boundary check is
clean. These are deterministic development-checkout Greens after the retained
real stale-lineage Red; they do not constitute fresh provider, database,
service, browser, or milestone evidence.

The rebind records the second fixed archive singleton and the requirement to
retain and revalidate every earlier archive before each service or filesystem
mutation. The approved correction reuses existing lifecycle values and changes
no public contract version, schema, migration, dependency, provider write
authority, or V1 read-mostly boundary. The live second rollover and activation,
fresh corrected-service collection, prerequisite recollection, and canonical
`AUTO-M5-EXIT` remain Not Run. M5 therefore remains Intermediate, its
acceptance remains unrecorded, and its canonical gate remains `not_run`.

Plan snapshot SHA-256: `567510d4eeb9790b7614b4aeff971944e55cdae023efb6f69490c9ac976096ed`

## 2026-10-16 approved M5 1.6.0 closeout rebind

The current snapshot records the owner-approved M5 focused plan 1.6.0
amendment and corresponding bounded PLAN-DEP/D01 proposal. Real corrected
service evidence proves the current native-window lifecycle behavior, while a
later live Red proves that its verification read only page one of a valid
nine-page immutable history. The approved test correction follows every
bounded opaque cursor, rejects missing or repeated progress, preserves exact
ascending ordering, and proves both the newest lineage and prior history.

Because committing that test changes the revision required by the canonical
exit gate, the approval permits one exact evidence-preserving rollover from
completed clean revision
`6d6e1aa9d9b64d50e3f83d0f1686e6cff04b7c17` into one eventual reviewed commit.
It requires a closed ordered three-archive chain and the same fail-closed real
Git, filesystem, systemd, HTTP, browser, Registry, database, and rollback
proofs. It changes no public contract, schema, migration, dependency, provider
behavior, or read-mostly product boundary.

The owner's 2026-10-16 approval grants implementation readiness only for that
exact test correction and rollover. Approved plan 1.5.0 and every retained
evidence artifact remain authoritative. No gate, service, acceptance, or
milestone state changes through this planning rebind. The synchronized control
set also binds the bounded three-rollover routine and automation-standard
descriptions. M5 remains Intermediate and `AUTO-M5-EXIT` remains Not Run.

Plan snapshot SHA-256: `4ecf1c391799cc14ddb39e8f33e3ac4620f5732b92a777c2841913514d745177`

## 2026-10-20 approved M5 1.7.0 browser-proof termination rebind

The current snapshot records the owner-approved M5 focused plan 1.7.0
amendment and corresponding bounded PLAN-DEP/D01 scope. The third canonical
rollover preserved the completed `6d6e1aa` transition and activated exact
clean revision `e066d7e1ba0124f0454c07002ea7b2ad0817d6b9`. Refreshed owner
outcomes and genuine collection/history lineage passed for that service.

A later real alert lifecycle completed opening or reopening, repeat, owner
action, recovery, API and built-browser presentation. The verifier emitted one
valid browser-proof document but retained its owned Playwright CDP connection,
so the Python writer reached its 180-second timeout, reported
`m5_alert_witness_browser_unavailable`, and created no alert witness. The
approved correction releases only that owned client connection after closing
its temporary page; it must preserve the owner's Chrome process, authenticated
session, pre-existing page, selected service tuple, zero-mutation result, and
complete Registry digest. Forced process exit and Chrome closure are outside
scope.

Because the correction creates a new exact revision, the approval permits one
fourth evidence-preserving rollover from completed `e066d7e` into one eventual
reviewed clean commit. It requires the fixed
`m5-service-activation-corrective-archive-e066d7e` singleton and the existing
fail-closed ordered four-archive, Git, filesystem, systemd, HTTP, browser,
Registry, database, and rollback proofs. No public contract, schema, migration,
dependency, provider authority, product behavior, or general deployment scope
changes.

This planning/control rebind does not claim the browser correction, its Green,
the clean candidate, the fourth live rollover, prerequisite archival and
recollection, `AUTO-M5-ALERT-WITNESS`, `AUTO-M5-QUOTA-WITNESS`, or
`AUTO-M5-EXIT` has passed. The synchronized control set binds the authorized
four-rollover routine and automation-standard description. M5 remains
Intermediate, acceptance remains unrecorded, and its canonical gate remains
`not_run`.

Plan snapshot SHA-256: `5bf56c21ef5c05ba7539bdd7fdd0a908231672e13ed762ab8e8365f3c0873b38`

## 2026-10-20 approved M5 1.8.0 P02 canonical-browser rebind

The current snapshot records the owner-approved M5 focused plan 1.8.0 and its
bounded P02 exception. The 1.7 browser-client teardown itself is focused Green,
but its required canonical browser lane exposed a real 390-pixel overflow, a
revocation assertion racing secure automatic logout, and a confirmed
password-flow race. In that password Red the real mutation returned 204 and the
single renewed-session read returned 200 within one second, yet a stale
previous-cookie Overview response left `/login` paired with protected content
and removed the success panel through 120 seconds.

The approved correction has a closed file and behavior boundary: contained
mobile header controls with nav-only internal scroll; revocation proof accepting
only visibly authenticated denial through automatic or one-click recovery; an
acknowledged Overview cleanup/generation fence before the password form becomes
interactive; inert controls and exactly one mutation during submission; typed
success, denial, proof-renewal, and unknown-result outcomes; secret-local data;
closed diagnostics; and a fail-first repeat runner with pure negative policy
tests. It changes no public API/IAM/UI contract version, backend, database,
provider adapter, configuration, dependency, license, migration, or ADR.

The 1.8 approval retains the same not-yet-run fourth rollover from exact
`e066d7e1ba0124f0454c07002ea7b2ad0817d6b9` and supersedes only 1.7's
candidate-content restriction. Every archive, rollback, systemd, HTTP, browser,
Registry, database, evidence-preservation, and stop condition remains binding;
no fifth transition or general deployment authority is introduced. Planning is
ready for this bounded implementation, while implementation Green, live
transition, refreshed prerequisites, canonical exit, and owner acceptance
remain Not Run. M5 therefore remains Intermediate with gate state `not_run`.

Plan snapshot SHA-256: `51945b23d1906200e29627580ac37eaec0c6b15f47ce812fcb15d9a0f4ee6a8a`

## 2026-10-21 approved M5 1.9.0 quota-projection readiness rebind

The current snapshot records the owner-approved M5 focused plan 1.9.0 and its
bounded PLAN-DEP/D01 fifth-rollover exception. The fourth canonical rollover
already preserved `e066d7e` and activated exact clean detached `d81afab`.
Current owner outcomes and the source-proven alert witness passed for that
service. The real quota-witness attempt passed its authenticated API, DOM,
history, Registry, identity, lineage, and zero-mutation boundaries, then
failed closed as `m5_quota_witness_input_invalid` and created no witness.

The defect was a private record-shape boundary: required opaque
`current_observation_id` had completed browser/history binding but was still
present when strict five-field quota policy ran. The approved implementation
projects the already verified record only after independent history-digest
validation. Focused Red/Green evidence and the complete 27-test quota-witness
file are recorded. No quota values, freshness, owner confirmation, Registry,
DOM, history, permission, or create-once condition was relaxed.

The correction requires a new exact revision, so the approval permits one
fifth evidence-preserving rollover from completed `d81afab` into fixed parent
`m5-service-activation-corrective-archive-d81afab`, with the existing four
archives retained as an unchanged ordered prefix. Four focused cases, all 43
activation tests, dispatcher/catalog checks, static checks, and exhaustive
73,728 transition plus 448 decision comparisons passed. This is local policy
and custody evidence; neither live fifth invocation has run. No sixth
rollover, public contract/schema, dependency, provider/scheduler operation,
UI/API change, or general deployment authority is introduced.

The synchronized controls also use the installed Codex 0.160 `/status` view
for authoritative rate-limit readings while retaining the historical
discovery statement and exact attestation phrase `I CONFIRM CODEX USAGE`.
Planning is ready for the bounded correction. The aggregate preactivation
gates, clean corrected candidate, fifth live transition, refreshed
prerequisites, authoritative quota witness, canonical exit, and owner
acceptance remain Not Run. M5 remains Intermediate with canonical gate state
`not_run`.

Plan snapshot SHA-256: `7e2540baa631414a0aa6647ce6d3b26385c0a00e52faa30d4739245e0bcd51a6`

## 2026-10-21 approved M5 1.10.0 containment-readiness rebind

The current snapshot records the owner-approved M5 focused plan 1.10.0 and its
bounded PLAN-DEP/D01 relationship. The correction changes only how the private
M5 verifier evaluates provider-created descendants below an exact pinned
owner-only root chain. It retains descendant metadata in evidence and preserves
the separate credential rule, link/type/ownership/device/special-bit/traversal/
bound checks, zero default-profile access, selected-profile write confinement,
and unchanged private receipt schema. It folds into the same not-yet-run fifth
rollover and authorizes no sixth transition or general deployment behavior.

Commit `d71b79c` completes both required real-filesystem bounds cases. The
focused non-live suite passes `30/30`, current-exit passes `66/66`, and the
exact Story inventory is `480` tests with digest
`e90485d6866065f3149cf1285b5c18c665d26068de2da5c4c61862830bb56bf9`.
The canonical preactivation aggregate remains pending. A subsequent real
attempt against current `d81afab` passed
safe metadata and driver stages, then failed closed as
`m5_codex_containment_path_mutator_unverifiable`; two successful provider
`chmod` calls were classified inside the selected profile and none under
default roots, but their closed path-argument proof did not pass. Owner-approved
plan 1.11 adds the exact inode-bound proof and safe channel diagnostics;
implementation is pending. This is a Failed containment result, not completion
evidence.

The synchronized controls bind the updated PLAN-DEP body, generated contract
adoption, reviewed ownership digest, M5 exit routine, and completion standard.
All other canonical approval flags remain unchanged. The aggregate
preactivation gates, an approved and passing authenticated containment
correction, the fifth live transition, refreshed prerequisites, authoritative
quota witness, `AUTO-M5-EXIT`, and owner acceptance remain Not Run. M5 remains
Intermediate with canonical gate state `not_run`.

Plan snapshot SHA-256: `4214633ff01b6b8276b1c9bc34475e37b75c3e724162c35863e845cb72bc6ff7`

## 2026-10-23 approved M5 1.16.0 alert-witness scale readiness rebind

The current synchronized Draft snapshot records the owner-approved M5 focused
plan 1.16.0 correction in the bounded automation catalog. Local implementation
is Green for the exact-ID acknowledged-event query, complete Alerts history
pagination, browser witness policy, and exact sixth-rollover policy.
Independent backend, UI, and activation reviews are CLEAN. The exact Python
Story inventory is `557` identifiers with SHA-256
`f9bf5d58f37032239377741a8ab74f96c220348cf5cad46323c47e6c71682035`;
the exact Node inventory is `21` identifiers with SHA-256
`ac6afb5a290f5bf5940581ef13db21acccce947f3d40f97b498b57189f2db7e7`.

Only the `automation-routines` control changed among synchronized baseline
inputs. All 20 canonical plan bodies, public contract versions and meanings,
the other eight controls, and canonical approval flags remain unchanged. This
control rebind records local implementation evidence; it does not advance a
live scenario, milestone gate, acceptance decision, or release state.

The active service remains exact clean revision
`8cc683d946b58f5eb72955e08a520195582e1a28`. Authenticated
`M5-CDX-UI-014`, live `M5-SVC-ACT-021`, refreshed service-bound prerequisites,
alert and quota witnesses, `AUTO-M5-EXIT`, and owner acceptance remain absent
or Not Run. M5 remains Intermediate with canonical gate state `not_run`.

Plan snapshot SHA-256: `d56f6e27de1bf918a2b27d99fe2287900312dbd63036ea3418c5a40d9216fe09`

## 2026-10-23 approved M5 1.17.0 artifact-selector readiness rebind

The synchronized Draft snapshot now binds the automation catalog to the
owner-approved focused M5 plan 1.17.0 correction. The static Story artifact
check, exact seventh-rollover policy, and their focused tests are locally
Green and independently reviewed CLEAN. The exact Python Story inventory is
`562` identifiers with SHA-256
`4ca56497a7fdaa1e80c7c01a3ee1e41c2029288966b1fe969790606fad0cbb7b`.

Only the `automation-routines` control changed among canonical synchronized
inputs. The 20 canonical plan bodies, public contract versions and meanings,
the other eight controls, and canonical approval flags remain unchanged. The
active service remains exact revision
`35f50d8c4865505a9112d8aef7ea788f425ae658`; its failed exit created no
completion receipt. Clean-candidate preactivation, the seventh rollover,
refreshed prerequisites, corrected `AUTO-M5-EXIT`, and owner acceptance remain
Not Run. M5 remains Intermediate: the latest canonical gate state is `failed`
on `35f50d8`, while the corrected candidate is `not_run`.

Plan snapshot SHA-256: `abdcd4baaca4a5bb080ff0d536c729cea8a3ce6ed96473fd7741300a7b9ecbaa`

## 2026-10-24 approved M5 1.18.0 rolling-reset readiness rebind

The current synchronized Draft snapshot records the owner-approved focused M5
plan 1.18.0 correction. The private quota-witness policy retains exact window
membership, semantic roles, whole percentages, fixed-reset matching, source
precision, and the 300-second bound. It adds only the fail-closed full-unused
rolling relation proven by real Codex 0.160.0 history; missing five-hour or
other windows remain absent. Focused Red/Green evidence and the complete
50-test quota-witness file are Green.

The same approval adds the exact eighth evidence-preserving rollover from
completed revision `1ada84f71e827bb4f7ea966462a6cf51d050e9af` into fixed
singleton `m5-service-activation-corrective-archive-1ada84f`. The focused
eighth-rollover cases are Green and the seven retained archives remain the
required unchanged prefix. This is local implementation evidence; neither live
eighth invocation has run.

Only the `automation-routines` and `automation-standard` controls changed
among synchronized baseline inputs. The 20 canonical plan bodies, public
contract versions and meanings, the other seven controls, and canonical
approval flags remain unchanged. The active service remains exact clean
revision `1ada84f`; its current owner and alert prerequisites do not provide a
quota witness or completion receipt for a future corrected revision. Complete
preactivation, the eighth rollover, refreshed prerequisites,
`AUTO-M5-QUOTA-WITNESS`, `AUTO-M5-EXIT`, and owner acceptance remain Not Run.
M5 remains Intermediate.

Plan snapshot SHA-256: `37409cd3a15d25d211cffcac55183a2d1f765656fc7cd5070e749a22f0366a8d`
