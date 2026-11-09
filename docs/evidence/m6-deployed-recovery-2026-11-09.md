# M6 deployed compatibility and recovery evidence — 9 November 2026

- Status: recovery and installed Claude compatibility passed; M6 remains open.
- Authority: [approved provider-display correction](../plans/integration/m6-provider-display-compatibility-2026-11-09.md).
- Requirements: FR-COL-004/006/007/008, NFR-COMP-001, M6-A04/A07/A09,
  AC-LIVE-004/007.
- Owning modules: A01 Claude compatibility; integration verification of M04,
  M05 and the installed P02 dashboard.
- Implementation, public GitHub and deployed revision:
  `e9c146b34331ecfdfc8823a33e56eaf12cd31e05`.
- Contracts: A01 adapter/parser `1.0.4`, admission
  `A01-M03-CLAUDE-2-1-289-002`; unchanged
  `CLAUDE-SUBSCRIPTION-QUOTA-V1@1.0` and public API shapes. Installed schema
  remains `v1_0720`. Official comparison evidence is `1.1.0`.

## Installed behavior

Canonical `AUTO-M6-CURRENT-UPDATE` completed successfully after a retry of
local candidate readiness. The service is active, serves HTTP 200 and retains
its normal restart policy. A genuine scheduled Claude read completed at
16:30:29 UTC with a partial result, adapter `1.0.4`, real weekly capacity and
unknown session capacity. No error code was recorded.

The authenticated built browser showed **Unknown** for the session, no session
progress meter, a weekly progress meter and fresh observations for both cards.
The read-only real persistence test confirms that the new unknown session
observation replaces the current projection while the previous numeric
observation remains in history.

The first persistence-test run failed with `StopIteration`: it searched only
the first 200 ascending history points across 30 days. A read-only bounded
query confirmed the old observation still existed. The test now starts at the
captured baseline run's request time minus one minute. It passed against the
same real installed database, with no production or data modification. The
original source behavior Red/Green evidence remains in the separate
[hash-bound admission record](claude-weekly-only-admission-2026-11-09.md).

## Canonical M6 result

`AUTO-M6-EXIT` ran against the clean deployed revision above and wrote its
direct evidence at 16:33:54 UTC. It did **not** pass the complete milestone.
Private artifact name:
`direct-e9c146b34331ecfdfc8823a33e56eaf12cd31e05-89e74a7d9a030a00.json`.

| Check | Result |
|---|---|
| Build, quality, documentation and planning | Passed |
| Source/security selection | Passed, 201 tests, zero skips |
| Real account administration and current cloud capacity | Passed, two active targets |
| Current history lineage | Passed, both targets |
| Controlled failure and scheduled recovery | Passed |
| Claude and Codex collection during recovery | Passed, actual committed run for each |
| Dashboard availability during recovery | Passed, 31 samples |
| M6-A01, M6-A03, M6-A07 and M6-A08 | Passed |
| Combined official balance comparison | Not Run for complete scope; only one target compared |
| M6-A04, M6-A05 and M6-A09 | Not Run: `official_usage_current_lineage_not_reconciled` |

The isolated collector failed at 16:27:40 UTC and ordinary scheduled recovery
completed at 16:33:10 UTC. Cleanup was confirmed. No running user agent,
default provider profile, account configuration or host networking was changed.
Natural provider failure was absent; the separately approved controlled path
supplied recovery evidence. Actual provider-side 401/403/429 conditions remain
unobserved, and dashboard continuity is sampled rather than continuous.

The SDK official comparison passed at 16:33:49 UTC with explicit unavailable
reset comparison. The EAIS official page was still at sign-in. Historical EAIS
success is not substituted for a current combined comparison. Local Ollama
remains deferred and is not included in the required completion scope.

## Handoff and residual work

The only additional change after the deployed implementation is the history
test's query range and this documentation. The selected real history test
passed (one test, zero skips), and canonical quality, documentation, planning
and local Git preflight checks passed again for this follow-up. No dependency, license, secret
storage, API or database migration change is introduced. No provider payload,
credential, conversation, personal identifier, fake boundary or seeded data is
included in this evidence.

The owner has an open official EAIS sign-in tab. After that session is
authenticated, repeat the combined official comparison and canonical M6 exit
on one clean deployed revision. Present the resulting scope and limitations
for milestone acceptance; this record does not accept M6.
