# Live verification runbook

## Purpose

Verify provider, platform, authentication, and end-to-end behavior against real owner-controlled systems. This is mandatory evidence, not an exploratory replacement for requirements or automated deterministic tests.

## Roles

- Agent/developer: prepares exact scenario, commands, expected invariants, redaction, cleanup, and records sanitized result.
- Owner: controls browser login, email code, MFA, provider/dashboard comparison, and approval of any state-changing action.
- Neither party sends credentials through chat or stores them in test artifacts.

## Preconditions

- Requirement, contract, implementation, and deterministic real-stack tests are complete.
- Scenario is listed in the provider/module live matrix.
- Exact target account alias/profile and default-profile protection are confirmed.
- Provider adapter and CLI/service versions are recorded.
- Expected side effects, quota/cost, duration, and cleanup are understood.
- `.env` and provider credentials are protected.
- Test output path is excluded from version control and secret-scanned.

## Scenario record

Each scenario has:

- unique ID;
- requirement/acceptance IDs;
- provider/account alias/plan class, not secret identity;
- capability and source;
- application/adapter/provider versions;
- start/end UTC timestamps;
- preconditions and permitted side effects;
- steps and observable assertions;
- provider authoritative comparison method;
- result: Passed, Failed, Blocked, Not Run;
- sanitized evidence reference;
- cleanup and post-state;
- owner acknowledgement when interactive.

Use [the live-test report template](../templates/live-test-report-template.md).

## Authentication scenario

1. Confirm target is an AgentMonitor-managed profile.
2. Start official login/reauth flow without secret capture.
3. Owner completes browser/device/email/MFA steps.
4. Verify stable returned identity against expected account.
5. Verify auth health and a safe read-only provider operation.
6. Verify default profile checksum/identity/state is unchanged using an approved non-secret method.
7. Verify no secret appears in logs/database/API/UI/artifacts.

## Quota/budget reconciliation scenario

1. Trigger/await a real collection.
2. Record observation timestamp, source, unit, scope, precision, and freshness.
3. Owner opens provider authoritative usage/billing view/command.
4. Compare same account/project/window and nearest time.
5. Apply only documented provider latency/rounding tolerance.
6. Confirm reset timezone/precision and used-vs-remaining interpretation.
7. Record pass or exact mismatch. Do not manually edit data.

## Local process/session scenario

1. Owner identifies a real running parent agent and any subagents.
2. Record safe PIDs/start times/provider/project labels.
3. Run read-only discovery.
4. Verify hierarchy, activity/status, and account evidence.
5. Confirm no process input/signal/restart and no provider file change.
6. Confirm no content/environment/secrets persisted.

## Re-authentication-expiry and exhausted states

Use naturally occurring states where possible. Do not intentionally revoke a credential, exhaust paid quota, change a budget, or interrupt active work merely for a test unless the owner explicitly approves a controlled scenario after cost/impact review.

If the state is unavailable, report Blocked. Domain state-machine logic may still have pure tests with constructed values, but that does not convert the live scenario to Passed.

## Failure handling

- Stop if wrong account appears, default profile could be modified, secret/content enters output, unexpected purchase/limit/state change is offered, or active agents are affected.
- Sanitize evidence at source; if contamination occurs, quarantine and rotate/revoke as needed.
- A provider outage is recorded as Blocked/Failed according to whether product behavior was still testable.
- Never retry repeatedly against rate limiting.

## Completion

- Owner confirms observed identity/comparison where required.
- Agent records result and follow-up.
- Traceability/live matrix is updated.
- Failed behavior returns to discovery/design/TDD.
- Blocked behavior remains a visible release item according to acceptance requirements.
