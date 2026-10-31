# Test evidence: CS-1 planning and automation gate

- Evidence ID: `EVID-CS1-PLANNING-GATE-2026-09-18`
- Module/plan/increment: PLAN-INT / CS-1 Draft synchronization
- Requirements/acceptance IDs: NFR-ARCH-001/002, NFR-TEST-001/002,
  NFR-DOC-001, NFR-LIC-001, NFR-COMP-001, AC-TEST-001..006
- Contract versions: contract baseline `0.2.0`; proposed contracts `1.0.0`;
  plan baseline `1.0.0-draft`
- Commit/worktree reference: unavailable — this checkout is not a Git worktree
- Recorder/date: root integration steward / 2026-09-19

## Test inventory and status

| Test/scenario | Layer | Real dependencies | Status | Evidence | Notes |
|---|---|---|---|---|---|
| Planning catalog/completeness | Repository governance | Real checkout and all 20 plan files | Passed | `AUTO-PLAN-CHECK`; synchronized validator | Exact paths, headings, size/scenario floors and registry links |
| Contract/config/requirement/parallel semantics | Repository governance | Real TOML controls and plan bodies | Passed | synchronized validator and independent audit | 97 contracts, 57 keys, 147 ownership rows, 20 SHA-bound units, 16 shared writers |
| Exact scenario resolution | Repository governance | Real 20-plan corpus | Passed | synchronized validator | 2,337 unique defined scenarios; exact references resolve |
| CTR-EVT physical topology | Repository governance | Real contract baseline and M02–M08/DB/INT plans | Passed | dedicated topology unittest | Module-owned outboxes; consumer-owned receipts/checkpoints |
| Immutable byte snapshot | Repository governance | Real plan/control files | Passed | snapshot validator | 20 plan and nine control digests/byte counts |
| Independent semantic audit | Independent review | Real complete Draft corpus | Passed conditionally | `cs1-final-readiness-audit.md` | Planning only; no owner approval or implementation authority |
| Documentation integrity | Documentation | Real Markdown corpus | Passed | `AUTO-DOCS-CHECK` | Links and repository references checked |
| Repository-wide AUTO-TEST | Repository governance/M0 G1 | Real checkout | Passed | `AUTO-TEST` exit 0 | 31 repository-governance tests passed; application T1–T7 remain Blocked/Not Run |
| Git preflight | SCM boundary | Real checkout | Blocked | `AUTO-GIT-PREFLIGHT` exit 3 | Checkout is not a Git worktree |
| Application T1–T4 | Pure/DB/API/browser | Production application and suites | Not Run | None exist | Governance tests do not substitute |
| Live T5 Linux/macOS | Platform | Approved real target systems | Not Run/Blocked | Linux not run; macOS unavailable | No simulation permitted |
| Live T6 providers | Provider/account | Owner-controlled real accounts/resources | Not Run | Owner coordination not yet requested | No provider boundary was touched |
| Installed T7 lifecycle | Operations | Built native service and real database | Not Run | Implementation absent | No deploy/migrate/backup/restore claim |

## Red evidence

The changed gate behavior was observed failing before its minimum implementation:

1. The first planning-gate import failed because `validate_plans` did not yet
   exist. This proved only that the gate capability was absent; it was not used
   as behavioral evidence.
2. Requirement-ownership validation initially failed because the validator and
   exact ownership manifest were absent.
3. Snapshot validation initially failed because `plan-baseline.toml` was absent.
4. Automation, documentation and Git preflight tests initially failed because
   their executable routines were absent. Git preflight then exposed an exit-code
   defect: the real non-Git checkout returned 2 while the contract required the
   truthful Blocked code 3.
5. Governance discovery initially found zero tests because package discovery was
   incomplete; adding package markers made the real suite discoverable rather
   than accepting a false green.
6. The dedicated event-topology test first failed with
   `contract baseline lacks [event_topology]` after the validator behavior
   existed but before the baseline/plans were corrected. This is the behavioral
   red for CS1-F01.
7. The synchronized planning gate failed first for snapshot, BLOCK audit and
   synchronization-record absence, then for only snapshot and record absence
   after the independent PASS-CONDITIONAL audit. Missing artifacts were never
   reported Passed.
8. The exhaustive ownership test failed against the prior manifest because the
   first unit had no plan digest or complete write set. It passed only after all
   20 plan-hash bindings, nonshared code/test/documentation paths, public
   contract writers, and collision checks were present.

No application behavior was written or claimed from these governance reds.

## Green evidence

The minimum governance implementations now provide:

- real-checkout catalog, contract, configuration, requirement, scenario,
  ownership-DAG, event-topology, audit, synchronization-record and digest checks;
- executable documentation and Git-preflight checks;
- a canonical routine catalog that distinguishes operational,
  operational-limited and Blocked routines;
- an independent PASS-CONDITIONAL audit after all semantic corrections.

The final command/result table in the
[synchronization record](cs1-full-plan-synchronization.md#final-observed-commands)
records synchronized validation, documentation, all 12 planning tests,
canonical plan/docs routines, restricted M0 G0, the truthful Git Blocked exit,
and the failed repository-wide AUTO-TEST result. A nonzero command is retained
as Blocked/Failed rather than normalized to Passed.

## Refactor evidence

Planning validation was decomposed into catalog loading, contract,
configuration, requirement, scenario, parallel ownership, event topology and
snapshot validators. Snapshot rendering is separate and deterministic.
Automation dispatch, documentation checks and Git preflight have separate
modules/tests and one machine-readable routine catalog. The broader governance
suite is rerun after finalization.

## Real-system evidence

All evidence here operates against the real repository checkout and real
filesystem state. The real Git boundary correctly reports Blocked because no
worktree exists. Real SQLite, HTTP server, browser, Linux/macOS process,
provider/account, installed-service and recovery boundaries were not executed
because the application and approvals do not yet exist.

## Integrity declaration

No mock, fake, stub, emulator, response recording/replay, demo account, seeded
telemetry, placeholder UI value, hardcoded pass, disabled assertion, test-only
production branch or swallowed failure was used. Constructed test values were
not used to claim an external-boundary result. The checks read the actual
repository files and preserve every Blocked/Not Run state.

## Data and secret review

The work read and wrote documentation and governance tooling only. It did not
read or persist secrets, `.env`, provider credentials/profiles, provider
payloads, prompts/responses, source content from monitored projects, process
environments or personal account identifiers. No external state changed.

## Conclusion and residual gaps

The evidence proves that the exact twenty-plan Draft is complete enough for
owner review, internally cross-referenced, independently audited and protected
against silent byte drift. It does not prove product implementation, provider
support, platform behavior, deployment or release readiness. Those claims
remain gated by M0, owner approval, real-system TDD and the blocked canonical
routines.
