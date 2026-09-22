# Milestone 0 G1 control specification

- Control ID: `M0-G1-CONTROLS`
- Version: `0.3.0-draft`
- Status: **Draft — G1 not approved; no discovery operation authorized**
- Owner: `PLAN-M0-DISCOVERY`
- Governing plan: [Milestone 0 execution plan](m0-execution-plan.md)
- Record schema: [M0 G1 JSON Schema](m0-g1-record.schema.json)
- Requirements: `NFR-TEST-001`, `NFR-TEST-002`, `NFR-SEC-001`,
  `NFR-PRIV-001`, `NFR-DOC-001`
- Acceptance criteria: `AC-TEST-001`, `AC-TEST-002`, `AC-TEST-006`

## Goal

G1 establishes the minimum safety controls required before G2. It answers:

1. Where may sensitive discovery evidence be kept?
2. How is one read-only operation reviewed and approved?
3. How are results and side effects recorded truthfully?
4. When must work stop and an incident be recorded?
5. Which local/no-telemetry scanner may guard repository publication?
6. How is every M0 scenario accounted for?

This specification does not authorize provider, account, process, profile, or
evidence-root access. It does not approve installation, login, logout, network
requests, scanner execution, or any discovery command.

## Scope

G1 owns seven records in `m0-g1-record.schema.json`:

| Record | Purpose |
|---|---|
| `ApprovalRecordV1` | Detached decision over exact subject bytes |
| `CustodyDecisionV1` | Owner-selected external evidence custody |
| `E1ScannerAdmissionV1` | Local scanner dependency decision |
| `IncidentRecordV1` | Stop and escalation facts |
| `OperationPacketV1` | One exact proposed read-only operation |
| `RunResultV1` | Immutable result and side-effect reconciliation |
| `ScenarioLedgerV1` | Complete M0 scenario accounting |

No execution scheduler, lease, crash-recovery protocol, publication engine,
provider capability model, or downstream module handoff belongs to G1.

## Authority rules

- Records are proposals until the required detached approvals exist.
- Approval binds the exact subject ID and SHA-256; changing the subject requires
  new approval.
- Missing, expired, conflicting, or rejected approval means `Blocked`.
- A successful repository contract test proves structure only. It grants no
  live-operation authority.
- Provider-owned state and the user's default profiles remain read-only.
- V1 discovery never controls a running agent.

## Evidence custody

The owner selects the external custody root at OCP-02. AgentMonitor records only
an opaque `external_root_ref` in repository-safe material, never the real path.
The completed custody decision remains outside Git and must state:

- owner selection;
- repository storage prohibition;
- permissions verification result;
- sync/backup disposition;
- retention deadline;
- approval over the exact decision.

The disposition records the owner's factual custody choice. It may be
`excluded`, `owner_accepted_encrypted`, or `owner_accepted_synced`; it is
`blocked` when none is truthfully owner-attested. Encryption is not inferred
from a synced location.

Real identities, paths, aliases, provider values, and unsanitized evidence stay
in the external root. Credentials, prompts, responses, source/tool content,
arbitrary environment values, OTP/MFA values, and raw secret-bearing files are
never collected as evidence.

## Operation review

Every observation starts with one exact operation packet. The packet binds:

- one scenario and one custody decision;
- exact operation type, executable/arguments or procedure reference;
- exact opaque targets;
- expected results and assertions;
- timeout and resource limits;
- zero or explicitly bounded network/request/cost/write effects;
- mandatory stop conditions;
- expiry and detached approvals.

The packet must not contain a shell command string. Execution uses an argument
array and rejects redirects, expansions, implicit installers/updaters, unknown
hosts, unresolved targets, and any operation outside the approved packet.

`AUTO-M0-PREFLIGHT` must fail closed until its real validator is implemented and
the exact packet, custody decision, and approvals are valid. G1 approval alone
does not make a packet executable.

## Result and scenario status

After an authorized operation, one immutable run result records timestamps,
termination, per-assertion outcomes, actual side effects, prohibited-data
observation, sanitized evidence references, and incident linkage.

`AUTO-M0-POSTFLIGHT` derives the scenario outcome. Allowed outcomes are exactly
`Passed`, `Failed`, `Blocked`, or `Not Run`. Missing evidence never becomes a
pass. `AUTO-M0-LEDGER` requires one unique entry for every scenario in the
approved M0 plan.

## Stop and incident handling

Stop immediately on any condition in the approved M0 plan, including unexpected
authentication, mutation, network, billing, provider response, secret/content,
path, permission, process, or scope behavior.

After stopping:

1. do not retry or broaden access;
2. preserve provider and running-agent state;
3. quarantine accidental sensitive material outside Git without copying it;
4. create a sanitized incident record;
5. notify the owner and required reviewers;
6. require a new packet or plan amendment before resuming.

An incident record reports facts; it never authorizes cleanup or recovery.

## E1 scanner admission

The E1 scanner admission records one candidate binary/version/digest, license
review, maintenance/security review, configuration digest, no-telemetry and
network requirements, output policy, real verification status, and decision.

Admission requires a local scanner that can run without telemetry, without
network access, and without retaining prohibited output. Until the dependency
review and real local verification pass, scanner admission is `Blocked`.

## Sequence

G1 defines and approves controls; it does not execute an M0 scenario.
M0-COM-001 is the first ordinary scenario after G1 and requires its own approved
operation packet plus `AUTO-M0-PREFLIGHT`. G2 begins only after G1 approval.

## G1 exit

G1 exits only when:

- this specification and the exact schema pass repository review;
- the owner has selected and approved real external custody;
- the E1 scanner admission is approved with real local evidence;
- the six authoring templates match the schema;
- owner, security/privacy, test-integrity, provider-system, and root-integration
  reviewers approve the exact G1 bundle;
- all remaining live operations are still visibly `Blocked` pending their own
  packet and preflight.

Until then, G1 remains `Blocked` and G2 must not start.

## Contract verification

`python3 tools/automation/run.py AUTO-M0-G1-CONTRACT` checks the real checkout's
bounded G1 bundle. It performs no provider, process, profile, account, network,
scanner, or external-custody access.

Live custody, scanner, preflight, postflight, and ledger verification require
separate approved implementations and owner checkpoints. Their absence is
`Blocked`, never `Passed`.
