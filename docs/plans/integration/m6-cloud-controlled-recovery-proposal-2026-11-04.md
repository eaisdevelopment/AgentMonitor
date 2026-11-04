# M6 cloud recovery: bounded controlled verification proposal

- Status: Approved for implementation and bounded execution by the owner’s direction to proceed after the pending proposal, 4 November 2026. The test has not yet run.
- Owner: integration/completion automation, with M04/A03 contract review.
- Requirement: M6-A07, M6-T015/T017, AC-LIVE-007, AC-OPS-003.
- Existing authority: approved M6 cloud implementation. The
  [current execution plan](m6-execution-plan-2026-10-31.md) requires a natural
  failure/recovery; the owner has now directed proceeding with this bounded amendment.
- Local Ollama remains deferred. This concerns cloud monitoring only.

## Reason and observed state

On 4 November the real read-only recovery producer returned
`not_run/m6_recovery_current_natural_failure_absent` against installed revision
`5839f05e029005d72cff89ddba571b4794d11482`. Its current policy accepts only a
received 401/403/429 failure for the exact current account, target, binding and
source. A healthy service can therefore leave this scenario unexecuted
indefinitely. It is not an implementation failure or a reason to ask the owner
to repeat account setup.

## Approved observable test

1. Select one existing connected, owner-confirmed Ollama cloud target, without
   creating/editing an account or changing monitoring. Record only opaque
   lineage, exact installed revision and service invocation. If no eligible
   target exists, report Not Run.
2. Run one AgentMonitor-owned collector process in its own network namespace
   with no external network access, using the installed production collection
   use case and the existing managed credential boundary. No alternate URL,
   fake server, response fixture, exception injection or key substitution.
   The production shared admission/credential locks, global request spacing,
   lease rules and source timeout remain mandatory. If a normal worker wins
   admission, wait for an eligible slot within the bounded test interval;
   do not change its schedule or kill it.
3. Observe the real network failure, normal M04 terminal run/latest signal and
   dashboard unavailable/stale presentation. Keep the last genuine balance and
   history; do not synthesize a provider error response or capacity record.
4. Let the isolated test process exit. The next ordinarily scheduled collector
   has normal connectivity. Observe a successful real response, committed
   current/history lineage and restored dashboard state for the same target,
   binding generation and source. Do not force retry or shorten cooldown.
5. Throughout the interval verify dashboard availability and normal real
   Claude/Codex collection. A service revision/invocation change, account/key
   change, missing lineage, incomplete cleanup or exceeded deadline is a
   Blocked/Not Run/Failed result as appropriate, never Passed.

The expected visible effect is one temporary Ollama monitoring connection
warning and retention of its last reading until normal collection recovers.
No user agent loses network access. No local model is required.

## Isolation, implementation and cleanup

Use an already admitted namespace facility for the single test process; do
not install a dependency. Namespace creation must succeed and its isolation
must be proven before dispatch. If the platform cannot support the boundary,
report that result instead of changing host firewall, service settings or
provider credentials. Do not touch user/default Claude, Codex or Ollama
profiles, the Ollama daemon, network interfaces, routes, DNS or account setup.

The concrete integration seam is `OllamaCloudCollectionV1` in
`backend/src/agentmonitor/composition/ollama_cloud_collection.py`, with the
existing rate/admission leases and source worker. The harness must establish
exclusive ownership of its own bounded attempt without bypassing the normal
collector manager's exclusion/recovery rules. If that cannot be done through
existing production interfaces, implementation must report the specific gap;
this proposal does not authorize an ad hoc second scheduler or weakened locks.
The tool may terminate only its own identified test process after its deadline.

Total observation budget: ten minutes plus existing source cleanup deadlines.
No persistent network setting, configuration flag, account mutation or hidden
retry loop. The only application writes are genuine collection runs/signals
and subsequent normal provider observations. Coding agents do not view keys;
the approved runtime reads the existing binding transiently as normal.

## Acceptance and contract change

Allow M6-A07 to be satisfied by either its existing natural scenario or this
explicitly labelled controlled **network isolation and recovery** scenario.
This does not prove provider-side 401/403/429 recovery; those outcomes remain
separate coverage limitations when not observed.

Keep `latest_natural_failure` and the existing natural recovery evidence honest.
Add a separate versioned controlled evidence record bound to real namespace
ownership, exact account/target/binding/source/run IDs, service revision and
invocation, dashboard samples and recovery lineage. A stored generic
`provider_unavailable` error alone must never qualify as controlled evidence.
Update the gate's selector/catalog hashes and strict consumer together; old
receipts cannot satisfy the changed acceptance. No public API/database
migration or product configuration is proposed. Any newly discovered public
contract or dependency impact must be reported before implementing it.

Before execution, implement meaningful pure Red/Green rejection tests for
missing/foreign/reused isolation witness, mismatched target/binding/source,
no actual failed run, no later committed recovery, missing continuity,
cleanup failure and stale/different revision. Then execute the real scenario
once and retain only sanitized evidence. Failed setup is not behavioral Red.

## Owner direction

The owner directed continuing toward the unfinished goal immediately after the
proposal and approval question. This is treated as authorization to implement
and execute this specific bounded scenario; no repeated approval is required. No account key,
terminal command, model installation or repeated sign-in is requested by this
proposal. SDK configuration remains exclusively owner-operated.

## Non-disruptive feasibility check

On 4 November the installed `/usr/bin/bwrap` successfully started an owned
short-lived process with `--unshare-net`, a read-only filesystem view and no
provider call. Its network-namespace identity differed from the parent and
it exited with status 0. This establishes namespace availability only; it is
not the failed-request/recovery test and does not satisfy M6-A07. No credential
was accessed or network/account/service configuration changed by this check.

## Integration safety correction

Read-only inspection found that the current worker supervisor treats any lock
contention as permanent quarantine. For safe coexistence with one owned test
attempt, ordinary `BlockingIOError` must instead return transient worker-busy;
unsafe metadata and other lock errors must still quarantine. Verify with real
owner-only lock files and actual flock contention, without a provider call,
before deployment. This is a bounded M04 supervisory recovery correction, not
a new configuration option or alternate provider implementation.
