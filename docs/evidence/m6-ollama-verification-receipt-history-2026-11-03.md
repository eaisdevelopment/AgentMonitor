# M6 Ollama verification receipt history

- Evidence ID: `M6-OLLAMA-VERIFICATION-RECEIPT-HISTORY-2026-11-03`
- Requirements: `FR-ACC-001`, `FR-COL-004`, `FR-SAFE-001`, `M6-A03`,
  `M6-A04`, `M6-A07`, `M6-A09`, `NFR-DATA-001`
- Owner: M02 registry persistence under the approved M6 Ollama cloud plan
- Contract impact: `CTR-REG-012` 1.1.0 wire shape unchanged; additive database
  revision `v1_0718`

## Failure and correction

M02 previously kept exactly one verification receipt for each credential binding
generation. A later successful owner verification under the same current source
policy could not install a new current receipt without colliding with that row,
and replacing it would have removed the exact run/admission receipt required for
crash recovery.

`v1_0718` adds an immutable technical-history table. The M02 transaction moves
the prior current receipt to history by a full-row compare-and-swap, then installs
the strictly newer receipt. Supersession requires the exact same binding, access
target, source ID, adapter version and manifest fingerprint. Semantic source
upgrades therefore remain fail closed and are not claimed by this change.

The current-receipt read remains current-only for scheduled admission. Exact
recovery lookup by `(run_id, admission_id)` reads current and history and fails
closed on any duplicate lineage.

## Red and Green

The pure policy Red was recorded before the transition function existed:

```text
ImportError: cannot import name 'verification_receipt_transition'
1 error during collection
```

Green:

```text
backend/tests/contracts/test_cloud_binding_verification.py
7 passed
```

The real migration test uses SQLite's online backup API to copy the installed
`v1_0717` database, which contains the real successful Ollama verification
receipt. The production `AUTO-MIGRATE` implementation is then invoked directly
only against that owner-only private copy. It verifies the new exact schema,
preserves every current receipt field,
adds an empty history table, and proves the exact current and run/admission read
paths. It performs no provider request, key read, seeded row, fabricated receipt
or live-database write.

```text
backend/tests/live/ollama/test_verification_receipt_history_migration.py
1 passed
```

A natural second successful owner verification is still required to exercise
the SQLite supersession branch with two real receipts. That provider boundary is
Not Run in this change; no provider response or account data was fabricated.
The canonical dispatcher form remains Not Run until the change is integrated
into a checkout with its reviewed local runtime.

## Impact and deployment boundary

The migration is additive and preserves the deployed `v1_0717` current table.
The new binary continues to validate the old exact schema as upgrade-required;
the retained prior binary does not admit the newer revision. `AUTO-MIGRATE` now
supports the bounded offline `v1_0717` to `v1_0718` path with its verified
pre-migration backup. The ordinary same-schema current updater cannot deploy
this schema change; reviewed offline migration/cutover sequencing remains an
integration requirement.

Before rollout, the operator must also prove that no interrupted older
cutover/migration journal is active or extend its exact recovery classifier for
the new target. This change does not reinterpret an older journal.

No credential value, provider payload, account identifier or process content is
logged or retained. There is no API, dependency, license, provider-profile or
secret-storage change.
