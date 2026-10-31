# V1-M3 closure audit — 2026-10-01

- Status: **Formal acceptance remains Blocked**.
- Assessed implementation revision:
  `e2fec69dfe8fc1413521e551c106b5bead804f8f`.
- Scope: reconcile the active M3 acceptance record with later technical and M4
  evidence, and identify the exact work required for safe closure.
- Requirements / acceptance: corrected on 2026-10-02 to
  `AC-M3-001..007`. The former full-release rows remain historical facts in the
  superseded record and close under V1-M4 through V1-M8.
- Contracts: no runtime contract change. Current M02/M04/M05/P01 read
  contracts are sufficient for the proposed replacement gate.

## Reconciled facts

The [historical acceptance record](v1-m3-acceptance-status-v1.json) was recorded on
2026-09-24 against revision `6b1edfc4a1ed1ac2c64692ec0d790b34b21ae7b8`.
It records `AUTO-M3-EXIT` as `not_run`, the then-missing mutation gate, and
formal M3 status as `blocked`. The 2026-10-02 scope correction preserves those
facts and supersedes that authority with a scoped, still-Blocked record.

The later [local release-gate decision](m3-local-release-gate-decision.md)
records that `AUTO-M3-EXIT` returned zero on 2026-09-25. That run used a fresh
same-account Claude quota and owner-terminal runtime observation, the visible
authenticated browser, 354 passing technical tests, quality/build/mutation,
documentation, and Git gates. The [mutation evidence](m3-fix-006-mutation-gate.md)
records 541 policy mutants: 534 killed and seven reviewed exact-bound
equivalents.

The [M4 completion record](m4-completion.md) later proves six selected monitored
registry/profile connections in two organizations and records a passing
standalone `AUTO-M4-EXIT`. It does not bind that run to an exact commit, and the
current overview contains five distinct reported identity quota rows because
two profile connections report the same identity. Its 257-test run had zero
skips and included real fleet, alert, operations, build, mutation,
documentation, and Git checks.

The [live account-agent evidence](live-account-agents.md) also proves one real
owner-confirmed unresolved-terminal-to-account link. These results close or
substantially improve several findings in the older M3 record. The
scope-corrected record now supersedes its authority while preserving every
historical result.

## Closure blockers

### 1. Resolved — the M3 acceptance set crossed later milestone boundaries

M3 Task 6 selects release-wide criteria and scenarios including all six Claude
accounts, every provider adapter, representative Claude/Codex/Ollama process
trees, a naturally observed ten-minute stall, complete release documentation,
and full artifact/backup secret review. The same M3 plan's completion rule is a
one-account Claude vertical. The program assigns the fleet to M4, Codex to M5,
Ollama to M6, API budgets to M7, and release completion to M8.

On 2026-10-02 the owner approved the
[scope correction](m3-scope-correction-2026-10-02.md). M3 now has seven
one-account Claude criteria, the validator supports a hash-bound schema `2.0.0`
successor, and M4–M8 plans state their ownership. The historical blocked and
not-run results remain unchanged in the superseded schema `1.0.0` record. This
blocker is closed without treating any unavailable later-provider or release
scenario as Passed.

### 2. The current M3 exit command is unsafe on the post-M4 owner database

[`AUTO-M3-EXIT`](../../tools/automation/implementations/auto_m3_exit.py) reads
`AGENTMONITOR_M3_ACCOUNT_ID`, but calls the owner-confirmed quota workflow
without that account selection. It checks the returned account only after the
workflow has performed provider and registry work.

The called
[`claude_live_monitoring`](../../backend/src/agentmonitor/composition/claude_live_monitoring.py)
path repeats default-profile discovery and owner enrollment with the fixed name
`Claude owner account` and no organization. The M4 administrator legitimately
renamed that account and assigned it to an organization. The
[`owner_enrollment`](../../backend/src/agentmonitor/modules/registry/application/owner_enrollment.py)
flow reconciles discovery before confirmation, while the
[`registry repository`](../../backend/src/agentmonitor/adapters/persistence/registry/sqlite/repository.py)
correctly rejects confirmation when the existing name or organization differs.
The old gate can therefore write a discovery candidate and then fail with an
identity conflict. A managed-account selector can also cause protected-default
work before the late account mismatch is detected.

The old command must not be run against the current owner database. Its safe
successor is an automation-only change: validate the selected existing
protected-default account before provider work, witness the next genuine
scheduled service collection through published reads, require exact
run/receipt/quota/identity lineage, execute the existing owner-terminal runtime
lane, check the current authenticated browser, and prove the administrator name,
organization, and record version remain unchanged. A timeout or mismatch stays
Blocked. This design does not need a production API or database change.

### 3. The M3 browser subgate predates the current dashboard

The historical populated-dashboard verifier asserts the old page structure and
a hardcoded exact provider-version tuple. The current M4 dashboard reorganized
the overview, account details, connection state, and process association views.
A targeted M3 browser witness needs a real-browser Red/Green update against the
running current service and one selected account. It must remain read-only and
must not replace the wider M4 browser evidence.

### 4. No canonical M3 result is bound to the assessed implementation revision

The 2026-09-25 technical pass is genuine historical evidence. It does not prove
that the safe successor gate passes against implementation revision `e2fec69`.
After Blockers 2–3 are resolved, the successor command must pass against the
exact assessed implementation checkout and real owner environment before a new
acceptance record can claim current closure.

### 5. The historical M3 Red-first gap needs an explicit disposition

The historical record correctly says older M3 corrections lack captured pre-fix
Reds. That history cannot be reconstructed. Formal closure requires an explicit
owner decision that either accepts this bounded historical M3 deviation or
keeps `AC-M3-007` blocked. The decision cannot waive Red-first evidence for
the successor gate or future changes.

### 6. The scope-corrected formal status authority remains Blocked

The schema `2.0.0` record and matching Markdown marker now preserve the old
failed/not-run results and make the corrected scope authoritative. It remains
Blocked on `AC-M3-007`. After the safe current gate and historical deviation
decision are available, this active record must be updated or superseded with
their exact evidence and owner countersignature before M3 can be accepted.

## Evidence already available for the successor decision

- six selected monitored profile connections and two organizations: M4 fleet
  gate; the five distinct reported identities and genuine duplicate require an
  owner outcome before `AC-LIVE-001` can claim six intended accounts;
- one real manual terminal/account confirmation: account-agent live gate;
- M3 quota/runtime/browser technical vertical: historical M3 exit gate;
- mutation target and survivor disposition: M3 and M4 mutation gates;
- no simulated provider telemetry and explicit unavailable-state reporting:
  existing test-integrity and completion automation;
- local M0 detached reviewer approvals: advisory under the recorded local
  release policy and not an execution blocker.

## Required closure sequence

1. **Completed 2026-10-02:** approve and validate a milestone-scoped M3
   acceptance set, retaining broader criteria as contributions to their V1
   owners.
2. **Pending:** add the read-only installed-service M3 successor gate with recorded
   Red/Green evidence and current-browser coverage.
3. **Pending:** run that gate in a controlling terminal against the exact implementation
   revision and real owner environment; record every unavailable scenario
   separately.
4. **Pending:** record the owner's explicit M3 historical-TDD disposition and interactive
   live countersignature.
5. **Pending:** update or supersede the active M3 acceptance JSON with the
   current gate result and synchronized Markdown marker; run
   `AUTO-DOCS-CHECK` and `AUTO-GIT-PREFLIGHT`.
6. **Pending:** when M3 becomes accepted, update the implementation-status overlay so M4's
   dependency becomes satisfied and make the appropriate M4 acceptance
   decision explicitly.

No production code, provider state, account metadata, or running process was
changed by this audit.
