# M3 Claude OTLP targeted-profile probe

- Evidence reference: `REF-M0-CLAUDE-OTEL-TARGETED-PROBE-001`
- Date: 2026-09-24
- Scope: Claude Code `2.1.278`, Linux x86-64, one owner-selected Claude Max
  account and its protected provider-default monitoring profile
- Requirements: `ST-PROV-001`, `ST-OBS-002`, `AC-LIVE-005`,
  `AC-PROC-001`, `AC-PROC-004`
- Contracts: `CTR-PROV-002` V1, `CTR-REG-006` V1, `CTR-RUN-001/006`
  V1
- Result: Passed

## Real boundary exercised

The owner explicitly confirmed the one-shot identity-binding command on a real
controlling terminal. The production launcher then started the installed Claude
Code `2.1.278` executable under the existing provider-managed default profile,
accepted only the authenticated metrics-only OTLP request on an ephemeral IPv4
loopback listener, observed the exact Linux PID/start identity, and committed the
session through the production M04-to-M06 path in the real owner database.

The current read-only integrity test reopened that file-backed database and
proved all of the following without printing an account identifier, provider
identity, fingerprint, path, payload, or credential:

- exactly one current Claude provider-account fingerprint claim exists for the
  selected AgentMonitor account;
- the active claim and decision resolve to the same selected account;
- the claim references the exact committed M06 session observation;
- the decision evidence digest equals the durable M06 receipt digest;
- the receipt contains that observation reference;
- source, source version, parser version, and mechanism version match the
  governed OTLP mapping; and
- the resulting runtime session is `automatic_matched` to that same account.

## TDD and real-run results

The audit repair first produced the expected real failures:

```text
active Claude identity evidence does not resolve to an M06 observation
1 failed
```

After the first real owner-confirmed run exposed a collection-policy generation
collision, a pure regression assertion was changed before production code and
failed with `assert 5 == 6`. The independent collection-policy generation then
made that focused test pass.

The next real run committed the evidence and exposed two active claims. The live
integrity test failed with:

```text
expected exactly one active Claude identity claim
assert 2 == 1
```

The confirmation transaction was corrected to retire replaced claims and their
decisions atomically, while preserving history. The registry revision used by
the launch plan was also changed from an installation-local revision to the
current registry-scope revision so subsequent automatic matches cannot become
stale immediately after confirmation.

Final focused results on the repaired checkout:

```text
backend/tests/adapters/providers/claude/test_otel_runtime_static.py::
test_otlp_collection_schedule_is_bound_to_selected_account_and_profile
1 passed

backend/tests/adapters/providers/claude/test_otel_runtime_static.py
backend/tests/registry/test_identity_policy.py
backend/tests/registry/test_provider_identity_fingerprint_contract.py
backend/tests/integration/registry/test_provider_identity_operator.py
62 passed

backend/tests/live/claude/test_provider_identity_evidence.py
1 passed
```

The live command used the selected owner data root and opaque account ID through
process-local variables. Their values are intentionally absent from this
repository record.

## Boundary and privacy reconciliation

- Provider/profile state mutation by AgentMonitor: none.
- Running-agent process control by AgentMonitor: none.
- Provider payload retained: none.
- Raw provider account identity retained: none; only the governed domain-separated
  SHA-256 fingerprint is stored in the private registry table.
- Logs/traces/prompts/responses/tool activity/source content collected: none.
- Default provider profile relocated, rewritten, or logged out: no.
- New dependency or migration: none.
- Remaining natural scenarios: non-Claude trees, a naturally ambiguous mapping,
  and a naturally stalled/waiting process are not evidenced by this probe.

This record is sanitized repository evidence. Dynamic provider values and any
raw capture remain outside the repository under the owner-controlled custody
policy.
