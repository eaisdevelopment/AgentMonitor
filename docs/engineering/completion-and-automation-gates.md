# Completion and automation gates

- Status: **Mandatory engineering standard**
- Version: 1.1.0
- Owner: integration steward
- Approved direction: explicit owner instruction, 2026-09-18

## 1. Purpose

This standard prevents an intermediate artifact, framework, backlog, or partial
implementation from being reported as completed work. It also requires every
repeatable engineering and operational routine to have a canonical automated
entry point before the lifecycle phase that depends on it may be called ready.

An agent's narrative assessment is not a completion gate. The applicable
machine-executable gate and its truthful evidence are the gate.

## 2. Completion claim rule

Before using `complete`, `done`, `ready`, `implemented`, `validated`, or an
equivalent phrase in a handoff, the responsible agent must:

1. resolve the requested deliverable into a versioned completeness catalog;
2. run the catalog's canonical gate against the real checkout/environment;
3. report the exact command, exit status, and bounded result summary;
4. report every Failed, Blocked, and Not Run item separately;
5. verify that no required artifact was replaced by a backlog entry, placeholder,
   example, proposed future step, or prose promise;
6. avoid a completion claim when the gate is absent, red, skipped, or narrower
   than the claim.

If work is intentionally presented before the gate passes, it must be called an
`intermediate update`, name what remains, and continue without asking the owner
to discover the omissions.

### 2.1 Review convergence rule

A completion review is bounded by the approved scope and completeness catalog;
it is not an open-ended invitation to improve the design. Before a final review,
the responsible agent records the exact known-defect batch and enters
stabilization. During stabilization:

1. repair only known defects and their necessary consistency consequences;
2. perform one fresh full-gate run and one bounded independent review;
3. permit a new blocking finding only when it proves that a stated V1 behavior
   is impossible, violates a non-negotiable safety/privacy invariant, or
   directly contradicts another normative contract;
4. require every blocking finding to cite the affected requirement or invariant,
   exact conflicting artifacts, reproducible evidence, and smallest sufficient
   closure;
5. record enhancements, defense-in-depth ideas, stylistic improvements, and
   implementation details that do not meet item 3 as non-blocking follow-up;
6. prohibit broadening the acceptance catalog, adding a feature, or restarting
   exploratory review without explicit owner direction.

If the bounded review finds a qualifying blocker, only that blocker and its
necessary consistency consequences are repaired before the same full gate is
rerun. A handoff must state the number and class of any such reopenings. This
rule limits scope; it never permits a known correctness or safety failure to be
called complete.

## 3. Planning completion gate

The source of truth is
[`docs/plans/planning-catalog.toml`](../plans/planning-catalog.toml). The canonical
command is:

```bash
python3 tools/planning/validate_plans.py --stage synchronized
```

The synchronized planning gate is green only when:

- all 20 required V1 planning workstreams have substantive artifacts;
- each applicable plan contains all module-plan sections;
- each plan meets its declared minimum scenario inventory;
- all exact scenario references resolve to definitions;
- the 147 requirement/acceptance records have one primary plan, explicit
  contract producers, and primary-owned evidence;
- the 97-contract, 57-key configuration, and parallel-ownership baselines pass
  semantic validation without claiming approval or implementation;
- the planning registry links every artifact;
- the automation standard defines every mandatory routine;
- the exact plan/control SHA-256 snapshot matches the checkout;
- the cross-plan synchronization review is Complete and accounts for every plan.

Passing this gate means the draft planning set is complete and synchronized. It
does **not** approve a plan, dependency, provider mechanism, implementation, live
test, deployment, or release.

The gate itself is tested against the real checkout:

```bash
python3 -m unittest tools/planning/test_validate_plans.py
```

## 4. Routine automation contract

The machine-readable registry is
[`tools/automation/routines.toml`](../../tools/automation/routines.toml). Every
routine, including one whose implementation is not yet authorized or available,
has the same canonical invocation:

```bash
python3 tools/automation/run.py <AUTO-ROUTINE-ID>
```

An unavailable routine exits with status 3 and prints `BLOCKED` plus its exact
prerequisites. This fail-closed command is codified automation state, not an
implementation or readiness claim. `python3 tools/automation/run.py --list`
shows the current operational, limited, and blocked states.

Every routine below must ultimately have one documented, non-interactive,
fail-closed command. The owning plan selects the implementation and dependency
only after admission review. Until that command exists and has real evidence,
the lifecycle stage that needs it remains Not Ready.

| Routine ID | Required canonical behavior | Owner | Required before |
|---|---|---|---|
| `AUTO-PLAN-CHECK` | Validate the complete catalog, module-plan structure, registry, scenarios, and synchronization record | Integration | planning-complete claim |
| `AUTO-M0-G0` | Verify that the exact M0 plan and all required reviewer decisions are approved without authorizing execution | M0/integration | M0 G0 exit |
| `AUTO-M0-G1-CONTRACT` | Validate the real checkout's bounded Draft G1 specification, schema, templates, and indexes without claiming approval or live evidence | M0/security/test | G1 contract review and every proposed G1 bundle change |
| `AUTO-M0-G1-FINALIZE` | Obtain the explicit owner checkpoint and atomically record approval of the fixed custody control record, verified scanner admission, and exact current G1 bundle | M0/owner/security/test | final `AUTO-M0-G1-EXIT` execution |
| `AUTO-M0-G1-EXIT` | Sole G1 approval gate over the exact minimal controls, real custody, scanner admission, and reviewer decisions | M0/integration/security/test | G1 completion |
| `AUTO-M0-PREFLIGHT` | Validate one exact-digest, detached role-approved, versioned M0 run packet, exact operation/assertion scope, custody, and side-effect budget | M0/security/test | every M0 observation |
| `AUTO-M0-POSTFLIGHT` | Validate immutable run results and per-assertion real evidence, reconcile side effects, and derive scenario status | M0/security/test | accepting an M0 run result |
| `AUTO-M0-LEDGER` | Generate/validate unique complete scenario accounting from approved packet/result digests | M0/integration/test | M0 synthesis and exit |
| `AUTO-DOCS-CHECK` | Validate local links, identifiers, required metadata, generated references, and documentation routing | Foundation/integration | any implementation handoff |
| `AUTO-TEST` | Run the selected real-boundary test suites with explicit Passed/Failed/Blocked/Not Run reporting | Foundation/test steward | implementation handoff |
| `AUTO-M3-TEST` | Run the bounded M3 contract and technical backend suites; keep the long M2 elapsed-time browser scenario separate | Integration | V1-M3 technical completion |
| `AUTO-QUALITY` | Run formatting, linting, typing, import-boundary, security, secret, dependency, license, and compatibility gates | Foundation/security | merge/release candidate |
| `AUTO-GIT-PREFLIGHT` | Verify repository identity, expected branch/upstream, clean/declared changes, no secrets, and commit policy without mutating history | Foundation/release | commit/push/release |
| `AUTO-BUILD` | Reproducibly build locked backend/frontend artifacts and emit build metadata/SBOM/notices | Foundation/release | install/deploy |
| `AUTO-M3-LIVE` | Verify the M3 Claude vertical slice against real owner SQLite through the authenticated loopback production build and browser; keep the native password memory-only and report unavailable prerequisites as Blocked | Integration/P02 | V1-M3 handoff |
| `AUTO-M3-EXIT` | Perform fresh authorized Claude quota and owner-terminal runtime collection, prove same-account lineage and current identity evidence, exercise the authenticated production browser, then run every local M3 gate | Integration | V1-M3 completion claim |
| `AUTO-MUTATION` | Mutate the exact admitted critical M05/M06 pure-policy surface and fail on every survivor or result not covered by an exact independently reviewed equivalence binding | Foundation/test steward | V1-M3 completion claim |
| `AUTO-MIGRATE` | Preflight schema range, lock migration, take required backup, apply explicit revisions, verify integrity, and fail safely | Persistence/operations | upgrade/start on new schema |
| `AUTO-DEPLOY` | Install or upgrade the native user service and frontend/backend artifacts using the approved paths, permissions, preflight, and rollback | Deployment | installed release |
| `AUTO-BACKUP` | Create checksum-verified, integrity-checked, retention-classified backups without secrets | Operations | production-like local data |
| `AUTO-RESTORE` | Restore only to an isolated/approved target, verify integrity/schema, rotate invalidated security state, and produce evidence | Operations | recovery readiness |
| `AUTO-RELEASE` | Run all release gates, assemble signed/versioned artifacts where approved, SBOM/notices/evidence/release notes, and rollback instructions | Integration/release | V1 release claim |

## 5. Automation implementation rules

- Canonical commands live in repository-owned scripts or an approved task runner;
  personal shell history is not automation.
- The same command is used by developers, agents, and CI where the real boundary
  exists. CI must not report local/provider/platform-only gates as Passed.
- Scripts are non-interactive unless the runbook explicitly defines an owner
  checkpoint for secrets, MFA, live provider state, destructive effects, or
  external publication.
- Scripts validate resolved targets before writes and never use broad destructive
  paths, unresolved globs, or secret-bearing command arguments.
- A routine must be idempotent where its semantics permit. Non-idempotent actions
  require preflight, confirmation authority, evidence, and rollback.
- Outputs are structured or deterministically parseable, redacted, bounded, and
  return nonzero on violations.
- Automation must preserve the distinction between Passed, Failed, Blocked, and
  Not Run. Absence of a runner, credential, platform, or account is never Passed.
- No automation may install dependencies, initialize/push Git, create GitLab
  resources, deploy, migrate, restore, or publish unless that action is explicitly
  authorized at the applicable gate.
- `AUTO-M0-G0` reads repository governance artifacts only. Its success does not
  authorize provider/account/process/profile access, select an evidence root, or
  satisfy `AUTO-M0-PREFLIGHT`.
- `AUTO-M0-G1-CONTRACT` is repository-only and structurally limited. Its success
  does not approve G1, replace detached human decisions, prove a behavioral
  validator, select custody, admit a scanner, or authorize any live operation.
- `AUTO-M0-G1-FINALIZE` is the named interactive owner checkpoint. It authorizes
  only one fixed custody control-record write/read and binds the current G1
  bundle; it grants no provider, account, process, profile, or G2 authority.
- `AUTO-M0-G1-EXIT` remains Blocked until real custody, scanner admission, and
  exact reviewer decisions exist. G1 executes no M0 scenario.
- `AUTO-M0-PREFLIGHT` remains the per-operation authority after G1. A G1
  contract or exit result cannot substitute for an approved scenario packet.
- Each script has real tests at its actual boundary. Pure parsing/policy may use
  constructed values; filesystem, Git, database, HTTP, browser, service, and
  provider behavior uses the real respective system.

## 6. Git and GitLab routine

Git/GitLab readiness is separate from planning completeness. Before source-control
automation is approved, PLAN-FND and PLAN-INT must define:

- initialization/import authority and repository identity;
- default/protected branch, signed/unsigned commit policy, and merge workflow;
- token scope/storage and prohibited secret outputs;
- pre-commit versus CI responsibility;
- canonical preflight, commit, push, tag, and release commands;
- recovery from rejected push, wrong remote, detached head, and partial release;
- hosted GitLab jobs and the boundaries they can truthfully exercise without a
  local runner.

The current checkout not being a Git repository is a visible Blocked condition,
not an invitation for an agent to initialize or publish it.

## 7. Test routine

The future `AUTO-TEST` command must select explicit suites for T1 pure, T2 real
SQLite, T3 real loopback HTTP, T4 real built browser, T5 real platform, T6 real
provider/account, and T7 native lifecycle. It must emit the environment and
boundary actually exercised and attach Red/Green/refactor evidence identifiers.

No aggregate green status may conceal a Blocked or Not Run T5/T6/T7 scenario.

## 8. Deployment and recovery routines

`AUTO-DEPLOY`, `AUTO-MIGRATE`, `AUTO-BACKUP`, and `AUTO-RESTORE` are designed in
PLAN-DEP, PLAN-DB, and PLAN-M08 and synchronized in PLAN-INT. They remain
unavailable until those plans are approved and implementation follows TDD.
Their absence keeps deployment/recovery readiness red; prose procedures alone
cannot make the gate green.

## 9. Handoff evidence

Every handoff records:

- catalog/gate version;
- exact canonical commands executed;
- exit codes and sanitized evidence references;
- scope and boundary actually covered;
- Failed, Blocked, and Not Run items;
- changed automation and compatibility impact;
- remaining gates and the authority required to execute them.

Reviewers rerun the gate rather than trusting the author's completion statement.
