# Test evidence: Milestone 0 G0 approval gate

- Evidence ID: `EVID-M0-G0-2026-09-18`
- Module/plan/increment: `PLAN-M0-DISCOVERY` / G0
- Requirements/acceptance IDs: FR-SAFE-001/002, NFR-ARCH-001/002,
  NFR-TEST-001/002, NFR-SEC-001, NFR-PRIV-001/002, NFR-DOC-001
- Contract versions: PLAN-M0-DISCOVERY `0.2.0`; `ProviderAdapterV1`
  `1.0.0-draft.2`; automation catalog `0.2.0-draft`
- Commit/worktree reference: unavailable — checkout is not a Git worktree
- Recorder/date: root integration steward / 2026-09-18

## Decision

G0 is **Passed** for the exact PLAN-M0-DISCOVERY file with SHA-256
`6db9f5c048c6b3bf74c86b39e0388222766937f907a47a14e51a323cd3719192`
and byte count `78412`. The owner, root/integration, security/privacy,
test-integrity, and provider-system roles approved that exact scope.

This decision approves the discovery plan only. It grants no implementation,
provider operation, account access, credential use, process/profile/file read,
evidence-root selection, or scenario-execution authority. G1 is incomplete and
`AUTO-M0-PREFLIGHT` is intentionally `Blocked`.

## Review findings and closure

| Review | Initial status | Required correction | Final status |
|---|---|---|---|
| Security/privacy | Conditional | Prohibit intentional reads of prohibited data; enforce TLS/host/redirect controls; require admitted local no-telemetry E1 scan | Approved and exact-digest attested |
| Test integrity | Conditional | Make auth switching documentation-only; reconcile atime; gate G5 through G3/preflight; bind assertion/evidence schema | Approved and exact-digest attested |
| Provider system | Conditional | Freeze capability/auth vocabulary; restore A01 Anthropic and A02 OpenAI API handoff ownership | Approved and exact-digest attested |
| Root/integration | Conditional while findings open | Resolve all findings, codify the gate, preserve zero execution authority | Approved after closure |
| Owner | Awaiting OCP-01 | Continue from the explicitly stated M0 plan-approval checkpoint | Approved for G0 only |

## Test inventory and status

| Test/gate | Real boundary | Status | Evidence |
|---|---|---|---|
| Automation catalog registration | Real checkout/catalog/dispatcher | Passed | `python3 -m unittest tools/automation/test_run.py` |
| Exact plan/approval digest gate | Real plan and TOML bytes | Passed | `python3 -m unittest tools/discovery/test_m0_gate.py` |
| Canonical G0 command | Real checkout | Passed | `python3 tools/automation/run.py AUTO-M0-G0` |
| Per-run discovery preflight | Real checkout | Blocked | `python3 tools/automation/run.py AUTO-M0-PREFLIGHT`, exit 3; G1 custody and approved packet schema absent |
| Provider/account/platform operations | Provider/platform | Not Run | G0 grants no such authority |

## Red evidence

1. Before the automation catalog and commands existed,
   `python3 -m unittest tools/automation/test_run.py` exited 1 with three
   behavioral failures: both M0 routine IDs were absent and the dispatcher
   rejected them.
2. After the gate implementation existed but before approval, the same suite
   exited 1 because `m0-g0-approval.toml` was absent. The gate emitted
   `M0 G0 APPROVAL: FAILED`; this is the behavioral Red for missing approval.
3. `python3 -m unittest tools/discovery/test_m0_gate.py` likewise exited 1
   against the real checkout because the approval record did not exist. The
   missing-file error is retained as setup evidence; the validator's explicit
   approval violation is the behavioral evidence.
4. Independent reviews were Conditional before plan changes. No conditional
   review was recorded as Passed.

## Green and refactor evidence

After the minimum plan, contract, runbook, approval-record, and gate changes,
the six focused discovery/automation tests passed. `AUTO-M0-G0` exited 0 and
reported the restricted scope. `AUTO-M0-PREFLIGHT` continued to exit 3 and
report its real prerequisites, proving that G0 success does not bypass G1.

The M0 gate is isolated in `tools/discovery/m0_gate.py`; the generic dispatcher
only owns catalog validation and command execution. The approval record carries
the exact plan digest and explicit false authority flags. No provider-specific
behavior was added to the gate.

## Integrity, security, privacy, dependency, and migration impact

- Tests and gates read the real checkout; no mock, fake, stub, emulator,
  recording, demo account, seeded telemetry, placeholder, or hardcoded pass was
  used.
- No provider/account/profile/process/evidence-root or `.env` data was read.
- No secret or personal identity was added to source, evidence, logs, or chat.
- No dependency was added; all automation uses the Python standard library.
- No database/API migration or production-code change exists.
- The unpublished provider Draft was clarified from inconsistent
  `authentication.reauthorize`/`authentication_required` spellings to
  `authentication.reauthenticate`/`reauthentication_required` and versioned as
  `1.0.0-draft.2`; there is no implemented consumer to migrate.

## Residual gates

- G1/OCP-02: owner selects and protects the external evidence root without
  disclosing its path in Git or chat.
- G1: approve the local no-telemetry scanner and freeze the operation/assertion
  packet schema.
- `AUTO-M0-PREFLIGHT`: implement through real-checkout TDD, then approve each
  exact observation separately.
- All application T1–T7 suites, implementation plans, dependency admission,
  Git/GitLab setup, deployment, and release remain Blocked or Not Run.
