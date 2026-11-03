# M6 explicit scope evidence integration

Status: Intermediate. Scope: PLAN-INT consuming CTR-REG-013 1.0.0 through M02,
FR-ACC-006, AC-LIVE-003, M6-A03/A04/A05/A09 and ST-OLL-003/004. Authority:
[reviewed coverage plan](../plans/integration/m6-cloud-scope-outcomes-contract-impact.md).

The prior count-only test could pass scope without a selected declaration and
rejected two declared scopes using one actual target. Both pure behaviors failed
before correction. The projection now preserves explicit ordered organization
selection, current declaration state and exact hashed account/target references.
Own plus shared use of one selected account requires one target, not two keys.
Unavailable, missing, invalidated and incomplete scope never count as successful
live quota evidence. Every actual active target remains in the live denominator;
an unavailable declaration cannot hide an available target. Distinct accounts
cannot be merged into one target because labels or balances happen to match.

AUTO-M6-EXIT loads the owner-only non-secret
`/home/dev/.local/share/agentmonitor/m6-required-organizations.json` selection.
Its closed shape is schema_version 1.0.0, provider_key ollama and ordered distinct
organization_ids. Names are resolved once during authorized setup and are never
used to rediscover scope during a gate. The loader refuses links, hard links,
wrong owner/mode, oversized/invalid JSON, unknown fields and malformed selection.
Missing selection leaves cloud scope NotRun; it does not manufacture IDs or
prevent other real facts from being observed. A changed selection during the
query is rejected. The artifact binds the selected IDs as ordered typed hashes,
not account emails, organization names or credential references.

The snapshot executes as a module with explicit repeated organization-ID
arguments, using the M02 read port. Its result carries cloud_scope_evidence
alongside existing counts/digests. The consumer validates exact fields, selection
binding, consistency and the producer observation time. Existing record
confirmation times are not required to be re-attested after deployments.

## Evidence

Before integration, the real current-schema snapshot consumer returned Failed
with `coverage_snapshot_envelope_not_consumed`: it did not accept the new typed
envelope. After wiring, the same actual read passed and preserved two intended
scopes with one active target, initially both explicitly missing declarations.
The separate normal dashboard action subsequently saved the already-confirmed
EAIS own-account declaration. SDK remains unresolved pending an actual answer.

The focused combined policy/parser/projection/catalog suite passed 66 tests.
A new selection parser initially failed import because the capability was absent;
that setup failure is not counted as behavioral Red. The meaningful scope
behavior Reds are the two prior false classifications and the real envelope
rejection above. Closed-parser regression tests cover duplicate/dropped/wrong
selection, malformed facts, hidden extra targets and distinct-account aliasing.

The canonical command remains AUTO-M6-EXIT. Its internal scope-policy check
runs the focused pure tests before consuming actual scope; no new owner
attestation routine or separate milestone gate is introduced. Catalog hashes
are synchronized with the exact executable selectors and CTR-REG-013 adoption.
Other acceptance criteria and required checks remain unchanged.

No dependency, runtime secret store, provider action, schema or financial
aggregation behavior is changed by this evidence increment. Full gate and
installed-current-revision results must be recorded after execution; this
document does not convert unavailable live scenarios into Passed.

## Integration verification at 15:22 UTC

The actual current-schema snapshot passed after the EAIS declaration was saved.
It preserved the exact SDK/EAIS selection and returned `missing`, `account` in
that order. This proves selection and declaration consumption, not SDK coverage.

The actual retained owner declaration exposed two test assumptions: the SQLite
test expected no prior declaration, and the HTTP test failed
`private_copy_not_fresh`. The tests now derive their initial version from the
actual private database copy, preserve prior immutable history and other scope
declarations, and reject a different owner outcome. Set/replay/revoke/reassert
checks remain exact relative to that baseline. The combined real registry and
ephemeral HTTP/built-browser run passed eight tests in 43.77 seconds. It neither
altered the live declaration nor invented shared/unavailable outcomes.

AUTO-QUALITY passed local static/boundary/generated/locked-input checks;
AUTO-DOCS-CHECK passed 298 Markdown files; AUTO-PLAN-CHECK passed synchronized
planning; AUTO-GIT-PREFLIGHT passed its local-commit scope. Independent scope
review found no weakened acceptance criterion or blocking integration defect.
Hosted/release checks and the full current-revision M6 gate remain separate.
