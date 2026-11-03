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

## Installed supersession verification

On 3 November 2026, the canonical retained cutover and candidate finalizer
deployed `22d572c` with schema `v1_0718`. The real signed-in browser then
submitted one new connection check through the versioned API; ordinary service
dispatch and its rate gate performed the provider request. The new explicit
live test passed in 6.26 seconds:

```text
backend/tests/live/ollama/test_repeated_verification.py
1 passed
```

The test reads the real current receipt before initiation and verifies a newer
receipt afterward, unchanged binding/source/target lineage, exact retrieval of
both prior and current receipts by run/admission, and an unchanged monitoring
target. No receipt or provider response was fabricated. Browser session/CSRF
credentials remain inside the existing browser and are never returned or
recorded. The helper is an explicit operator test, not an automatic provider
request in a generic unit-test suite. It requires exactly one active target
and an already signed-in local dashboard browser.

The earlier isolated candidate had not exercised real supersession or the
installed dispatcher. The installed run above now covers those boundaries;
it does not establish the separate natural failure/recovery acceptance case.

## Impact and deployment boundary

The migration is additive and preserves the deployed `v1_0717` current table.
The new binary continues to validate the old exact schema as upgrade-required;
the retained prior binary does not admit the newer revision. `AUTO-MIGRATE` now
supports the bounded offline `v1_0717` to `v1_0718` path with its verified
pre-migration backup. The ordinary same-schema current updater cannot deploy
this schema change. The reviewed retained-release cutover and recovery evidence
is recorded in `m6-v0718-retained-cutover-2026-11-03.md`.

Before rollout, the operator must also prove that no interrupted older
cutover/migration journal is active or extend its exact recovery classifier for
the new target. This change does not reinterpret an older journal.

No credential value, provider payload, account identifier or process content is
logged or retained. There is no API, dependency, license, provider-profile or
secret-storage change.
