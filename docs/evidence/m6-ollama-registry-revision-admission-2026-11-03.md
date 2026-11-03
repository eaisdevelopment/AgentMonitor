# M6 Ollama collection admission after registry freshness changes

- Evidence ID: `M6-OLLAMA-REGISTRY-REVISION-ADMISSION-2026-11-03`
- Requirements: `FR-COL-003..008`, `M6-A07`, `M6-A09`
- Owner: M04 collection control under the approved M6 Ollama cloud plan
- Contract impact: `CTR-COL-002` unchanged; no schema or API change

## Failure and correction

The real Ollama cloud schedule retained one completed run while ordinary local
installation reconciliation advanced the global registry revision. M04 treated
that global snapshot revision as immutable source-policy identity within the
schedule generation and rejected the next otherwise identical run with
`collection_generation_conflict`.

Registry revision remains an exact per-run snapshot and is still checked by
the current-target eligibility and commit fences. It is not a source-policy
version. M04 now keeps the same-generation checks for source ID, manifest
fingerprint and collection-policy version, while allowing a later run to carry
the current registry snapshot.

## Real Red and Green

The focused test uses SQLite's backup API to copy the actual installed
database, invokes the production real Ollama installation reconciler on only
that private copy, and builds the next run from the resulting real registry
and graph records. It performs no provider request, credential read, seeded
row, fake response or live-database write.

Red before the correction:

```text
backend/tests/live/ollama/test_cloud_registry_revision_admission.py
CollectionRepositoryErrorV1: collection_generation_conflict
1 failed
```

Green and focused repository regression:

```text
backend/tests/live/ollama/test_cloud_registry_revision_admission.py
backend/tests/integration/collection_control/test_collection_repository.py
14 passed
```

The existing source-ID, manifest-fingerprint and collection-policy conflict
cases remain Green and fail closed. Actual scheduled provider dispatch is not
performed by this test and is not claimed by this evidence.

## Impact

No credential, provider payload, account identifier or process content is
logged or retained. No dependency, license, schema, migration, API, source
fingerprint, rate policy or provider-profile behavior changes. The separate
one-current-receipt limitation and future semantic source-policy epoch design
remain outside this correction.
