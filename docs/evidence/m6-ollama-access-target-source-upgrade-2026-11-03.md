# M6 Ollama access-target source upgrade reconciliation

- Evidence ID: `M6-OLLAMA-TARGET-SOURCE-UPGRADE-2026-11-03`
- Module/plan/increment: M02 Registry under the approved M6 Ollama cloud plan
- Requirements/acceptance IDs: `M6-A03`, `M6-A04`, `M6-A07`, `M6-A09`
- Contracts: `CTR-REG-012` 1.1.0, unchanged
- Candidate base: `3807977`
- Recorder/date: AgentMonitor engineering, 3 November 2026

## Behavior and contract impact

The existing code-owned, not-yet-verified `ollama.com` access target can advance
to the reviewed cloud source fingerprint without changing its target ID,
provider, authority, kind, lifecycle, account graph, profile, resource or
credential binding. The target record version advances exactly once. Replaying
the current fingerprint is idempotent. Immutable-identity disagreement, a
disabled target, a stale timestamp or a failed compare-and-swap remains fail
closed.

Verification receipts retain their exact historical fingerprint. Current
scheduled admission already requires the target fingerprint, receipt
fingerprint and current source policy to agree, so an earlier receipt cannot
authorize the upgraded source. The verification commit now independently
requires its fingerprint to equal the current target, fencing an old in-flight
source result after reconciliation. Because V1 permits only one receipt per
binding generation, reconciliation refuses a target that already has any
receipt; safe upgrade of that future state needs versioned receipt-history or
an explicit binding-generation transition rather than deletion of recovery
evidence.

This is a compatible persistence behavior correction. It changes no public
contract, API, schema, migration, credential generation or secret format.

## Red and Green evidence

The test copies the real installed SQLite database using SQLite's online backup
API, changes only the private copy and selects the existing code-owned Ollama
cloud target. It does not construct an account, credential, provider response
or telemetry row and does not print row values.

Red before implementation:

```text
backend/tests/live/ollama/test_access_target_source_upgrade.py
CredentialBindingRepositoryErrorV1: credential_binding_target_conflict
1 failed
```

Green after the minimum implementation:

```text
backend/tests/live/ollama/test_access_target_source_upgrade.py
1 passed
```

Focused regression:

```text
backend/tests/live/ollama/test_access_target_source_upgrade.py
backend/tests/contracts/test_cloud_binding_verification.py
backend/tests/contracts/test_ollama_target_fence.py
backend/tests/contracts/test_ollama_cloud_verification_enqueue_versions.py
14 passed
```

Ruff passed for the changed source and test. Strict mypy with explicit package
bases passed for both files. `git diff --check` remains required before handoff.

## Real-system and privacy status

The real installed database was opened read-only solely as the source of a
private SQLite backup. The live database, dashboard, service, `.env`, provider
profiles and provider network were not changed or accessed. Aggregate metadata
confirmed the natural target had no verification receipt and no pending
verification job at the test boundary; no identifiers or row contents were
printed.

The test is repeatable after live reconciliation: an already-current target
exercises the idempotent replay branch without requiring stale state. Actual
live target reconciliation, authenticated provider success, browser
capacity display, scheduled history and the canonical M6 exit remain **Not
Run** for this isolated candidate. A future source upgrade starting from an
already successful receipt requires separate real validation of the existing
one-receipt-per-binding-generation persistence policy; no such historical row
existed here, and none was fabricated.

The same V1 uniqueness also means a second successful manual verification run
for an already verified, same-fingerprint binding cannot write another receipt;
normal status policy should not offer that action while the current receipt is
valid, but the persistence path itself remains fail closed rather than
idempotent across a different run/admission. Versioned receipt history or a
generation transition is the shared M6 follow-up for both cases.

## Integrity declaration

No mock, fake, stub, emulator, recorded response, demo account, seeded row,
placeholder value, key, secret, provider payload or default-profile mutation
was used. No dependency, license, security boundary or operator command changed.
