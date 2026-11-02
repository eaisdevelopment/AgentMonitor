# Test evidence: M6 Ollama scheduled-source admission contract

- Evidence ID: `M6-OLLAMA-SCHEDULED-SOURCE-ADMISSION-2026-11-02`
- Module/plan/increment: M03 provider-system; approved M6 Ollama cloud plan
- Requirements/acceptance IDs: `M6-A03/A04/A05/A10`, `M6-T005/T006/T007/T014`
- Contract versions: additive `CTR-PROV-003` V1 (`1.0.0`)
- Commit/worktree reference: `codex/m6-scheduled-admission-proof`
- Recorder/date: Codex, 2 November 2026

## Test inventory and status

| Test/scenario ID | Layer | Real dependencies | Status | Evidence reference | Notes |
|---|---|---|---|---|---|
| M03-PURE-SCHEDULED-001 | Pure | None | Passed | `test_scheduled_source_admission.py` | Exact current binding, probe run and M05 commit derive one proof. |
| M03-PURE-SCHEDULED-002 | Pure | None | Passed | parameterized lineage test | Current binding/target, M04 and M05 mismatches fail closed. |
| M03-PURE-SCHEDULED-003 | Pure | None | Passed | request-limit test | At least 60 seconds, one request, one concurrent operation and no retry. |
| M03-PURE-SCHEDULED-004 | Pure | None | Passed | authorization-signal tests | 401/403/schema incompatibility revoke; rate/transient/store failures preserve. |
| M03-PURE-SCHEDULED-005 | Pure | None | Passed | identity-provenance test | Proof remains owner asserted and has no provider-identity field. |

## Red evidence

Before production symbols existed, the focused command failed during collection
with `ImportError: cannot import name 'ScheduledSourceAdmissionPolicyV1'`. This
was the expected structural Red for the new contract, but it is not claimed as
a behavioral Red of an already-present implementation. The integration
behavior therefore remains an intermediate candidate under the project's TDD
rules.

## Green evidence

`python -m pytest -q backend/tests/provider_system/test_scheduled_source_admission.py`
passed after the minimum contract and pure decision were added. After adding
exact M04-run projection fields, policy-digest sensitivity and
authorization-signal semantics, the focused plus existing provider-system
protocol/manifest set passed 104 tests.

## Refactor evidence

Ruff passed on the three changed Python files. `git diff --check` passed.
The 190-test foundation contract-boundary suite returned the same 188 passed,
2 failed result on both this candidate and its exact `aec840a` base. The two
pre-existing failures are the real-checkout boundary/catalog reconciliation
failures (`test_real_manifest_and_checkout_pass` and
`test_checker_cli_runs_real_checkout_and_fails_closed`); this candidate added
no boundary violation.

## Real-system evidence

Not Run: SQLite receipt projection, real worker dispatch, provider HTTP,
credential lookup, installed API/service, browser, source failure recovery and
scheduled polling. This slice intentionally performs no I/O. The actual
authenticated probe and all provider-owned states remain unavailable until the
owner completes the approved setup and the runtime gate is independently
admitted.

## Integrity declaration

No mock, fake, stub, emulator, recorded response, demo account, seeded
telemetry, placeholder, test-only production branch or swallowed failure was
used. Constructed values occur only in pure no-I/O contract tests.

## Data and secret review

The values contain opaque non-secret IDs, digests, closed status tokens and UTC
times only. No API key, keyring value, provider payload, identity, prompt,
response, source content or arbitrary environment value was read or recorded.

## Conclusion and residual gaps

This candidate supplies the M03-owned conditional admission meaning without
turning an M02 verification receipt into a global provider capability or an
identity claim. Integration still requires a narrow M04 exact-outcome read,
composition from real M02/M04/M05 records, current-state rechecks at dispatch,
real SQLite red/green, worker recovery review, live owner probe and canonical
completion gates. It is not M6 completion evidence.
