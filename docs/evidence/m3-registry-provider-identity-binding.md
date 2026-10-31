# M3 M02 provider identity binding evidence

Scope: the additive CTR-REG-006 prerequisite for FR-ACC-006 and FR-DISC-004.
M02 owns the contracts, application ports, and SQLite transaction. No M03 OTLP,
M06 runtime, API, UI, generated artifact, or migration is changed.

## Red

Before production code, this command failed during collection because the new
command contract did not exist:

```text
backend/.venv/bin/pytest -q backend/tests/integration/registry/test_provider_identity_fingerprint.py
ImportError: cannot import name 'ConfirmProviderIdentityFingerprintCommandV1'
1 error in 0.14s
```

The contract tests were moved to the pure M02 suite during refactor so no
constructed provider identity crosses an I/O boundary. The live test is the only
positive persistence test and consumes the actual opaque fingerprint returned by
the Claude OTEL production composition.

## Green and quality

```text
backend/.venv/bin/pytest -q \
  backend/tests/registry/test_provider_identity_fingerprint_contract.py \
  backend/tests/integration/registry/test_registry_persistence.py
14 passed in 1.22s
```

The ordered live binding scenario is **Not Run**, not passed. The earlier
direct-launch fixture was removed because the approved owner-run OTEL receiver
must preserve the terminal and must not read input or control Claude. The sibling
composition owns that owner-command integration and must cover actual fingerprint
binding, immutable M06 observation evidence, repository reopen/read-only
resolution, idempotent replay, changed-request conflict, and the same session
committing as `automatic_matched`. Binding the same real fingerprint to a
genuinely distinct second Claude account is also Not Run because no second
eligible real account was available.

One live attempt while the dashboard service was running failed before M02 with
the bounded error
`claude_otel_runtime_claude_otel_collection_failed`; zero Claude OTEL identity
claims were written. The exact cause was not established and no rerun was made.
Independently, the sibling lane verified that the strict production OTLP receiver
parsed a real Claude `2.1.278` metric.

Focused Ruff and Mypy pass for all M02 production and pure-test files. The full
registry suite is `54 passed, 3 skipped`; those three existing real-Claude tests
are Not Run. The repository-wide boundary checker is blocked by the unrelated
`backend/src/agentmonitor/contracts/capacity_v1.py:13` unresolved contract symbol;
it reports no M02 violation.

## Contract and data impact

- Additive contracts: `ConfirmProviderIdentityFingerprintCommandV1`,
  `ResolveProviderIdentityFingerprintQueryV1`,
  `ProviderIdentityResolutionV1`, and their application ports under CTR-REG-006.
- Existing tables only: `reg_provider_identity_claim`, `reg_identity_decision`,
  `reg_command_receipt`, and `reg_event_outbox`; no migration.
- The write requires an explicit account ID, its current record version, owner
  principal, UTC time, idempotency key, immutable source/parser tuple, exact M06
  observation ID, and expected evidence digest. There is no sole-account fallback.
- M02 accepts only the lower-case 64-character fingerprint; the provider
  composition verifies that it is the domain-separated Claude OTEL SHA-256 value.
  Raw provider account IDs and emails have no contract or SQL field.
- The claim persists the exact M06 observation ID; the decision persists its
  supplied immutable evidence digest; the receipt fingerprint binds the complete
  command including source/parser versions.
- Resolution returns an account only for one exact, active, owner-confirmed claim;
  its active owner-confirmed decision must agree. Absence is unresolved and
  inconsistent/version-mismatched state is conflict. Resolution opens SQLite in
  `runtime_read_only` mode.
- Residual schema constraint: the existing M02 tables cannot foreign-key an M06
  observation or separately constrain its provider source tuple, and the existing
  unique claim key omits scheme version. A cross-module FK/read is prohibited, so
  no migration was added: composition validates the exact source tuple, M02 stores
  the opaque reference/digest, and version/source inconsistency fails closed.
- No new dependency, license, configuration, process control, provider write, or
  secret handling is introduced.
