# M3-FIX-001/002 — scoped Claude handoff and OTLP mapping

- Audit findings: `M3-001`, `M3-002`
- Requirements: M3 scoped entry gate; `ST-PROV-001`; `AC-TEST-006`
- Modules/contracts: A01 and M03; `CTR-PROV-002` V1
- Status: remediation implemented; current evidence and bindings validate, but
  live authorization remains blocked by the pending detached approval records.

## Red

The contract tests were tightened before the handoff artifacts were changed:

```text
python3 -m unittest tools.discovery.m3_handoff_contract_tests && \
  PYTHONPATH=backend/src:. backend/.venv/bin/python -m pytest \
  backend/tests/adapters/providers/claude/test_manifest.py -q --tb=short

FAILED: the governed OTLP mapping was absent, the acceptance subject did not
bind it, local process/account correlation remained Deferred, the contract
bundle digest was stale, and --require-adapter-live returned Blocked.
```

This was a real-checkout failure. It made no provider request and did not read
or change a provider profile.

## Implementation

`m0-to-m03-claude-otel-v1.json` now owns the exact Claude Code 2.1.278 Linux
metrics-only OTLP mapping. The record is limited to the authenticated IPv4
loopback receiver, exact process identity, safe hashed account identity, and
explicit owner confirmation. Logs and traces are disabled; raw provider
payload and identity values are not retained.

The source fields and transport are reconciled to the official
[Claude Code monitoring documentation](https://code.claude.com/docs/en/monitoring-usage).
The manifest test resolves the repository artifact and hashes its bytes rather
than accepting a self-declared literal.

The acceptance subject binds the exact mapping, evidence index, handoff,
contract/schema bundles, and approved M3 plan by SHA-256. The validator derives
live blockers from the current detached decisions and fails on stale artifacts,
missing roles, a non-current contract bundle, or an unapproved targeted probe.

## Green and review

The structural contract suite currently passes. The live validator is expected
to remain blocked until all four detached approval records are independently
decided:

```text
python3 -m unittest tools.discovery.m3_handoff_contract_tests -v
.venv-m0-g1/bin/python tools/discovery/m3_handoff_validate.py \
  --require-adapter-live
PYTHONPATH=backend/src:. backend/.venv/bin/python -m pytest \
  backend/tests/adapters/providers/claude/test_manifest.py -q --tb=short
```

```text
python3 -m unittest tools.discovery.m3_handoff_contract_tests -q
12 passed

.venv-m0-g1/bin/python tools/discovery/m3_handoff_validate.py
M3 adapter/live handoff: BLOCKED
- owner_approval_pending
- security_privacy_approval_pending
- test_integrity_approval_pending
- root_integration_approval_pending

.venv-m0-g1/bin/python tools/discovery/m3_handoff_validate.py \
  --require-adapter-live
exit 2
```

The exact results must remain in the final M3 acceptance record. A pending,
rejected, stale, or unavailable decision is Blocked and is never called Green.

### Security-review correction

The first schema/security review rejected the handoff because the validator did
not execute its bound schema. A schema-only test was written first and failed
with `unrecognized arguments: --schema-only`. The approved M0
`jsonschema==4.26.0` runtime now validates the closed base mapping, distinct
closed OTLP mapping, evidence index, schema/contract bundles, acceptance, and
all detached approvals before any live authorization decision.

The next review found that the OTLP parser could collapse two partially equal
but otherwise conflicting required observations. A provider-neutral pure test
was added before implementation and failed at collection with an `ImportError`
for `resolve_one_exact_observation`. The new pure policy accepts duplicates only
when the complete immutable value is equal; the Claude adapter applies it to the
complete parsed session observation. No constructed provider response was used.

```text
PYTHONPATH=backend/src:. backend/.venv/bin/python -m pytest \
  backend/tests/provider_system/test_protocol.py -q \
  -k exact_observation_resolution --tb=short
# Green: 1 passed, 74 deselected

PYTHONPATH=backend/src:. backend/.venv/bin/python -m pytest \
  backend/tests/provider_system/test_protocol.py \
  backend/tests/adapters/providers/claude/test_otel_runtime_static.py \
  -q --tb=short
# Green: 84 passed
```

## Impact

- Security/privacy: metrics only; private loopback authentication; no raw
  provider identity, payload, prompt, response, tool, source, credential,
  arbitrary environment, or command-line content is retained.
- Provider/process state: read-only; no logout, profile rewrite, process
  control, or provider mutation.
- Migration/dependency/license: none.
- Documentation: governed mapping, scoped handoff, validator, contract tests,
  and this evidence record.
