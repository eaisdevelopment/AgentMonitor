# M5 representative quota increment — 2026-10-30

Status: Intermediate. The final milestone gate, deployment, evidence migration,
current official comparisons and owner acceptance have not passed.

- Requirements: `ST-CDX-003`, `ST-CDX-005`, `AC-LIVE-002`, `AC-LIVE-005`.
- Owning boundary: PLAN-INT completion automation and Codex quota verification;
  private quota witness v2 adds sample coverage beside full-fleet coverage.
  The public API, database and provider contracts are unchanged.
- Red/green: focused pure tests first failed on absent representative sample
  selection, reconciliation, v2 document validation, source-artifact inventory
  and changed Node inventory; they passed after implementation. The 134-test
  quota and exit suites passed and 22 Node policy tests passed with zero skips.
- Live: the built browser read two real monitored accounts and three windows,
  confirmed current API, rendered and retained-history values and recorded
  zero registry mutations. An earlier attempt failed on a value mismatch during
  the live check; the later attempt passed. No official owner comparison or v2
  witness was created by this check.
- Quality: `AUTO-QUALITY`, `AUTO-DOCS-CHECK` and `AUTO-PLAN-CHECK` passed on
  the candidate; hosted, release and final-gate checks were not run.
- Deployment preparation: the activation policy initially rejected the current
  source revision because it was outside the closed rollover chain. A failing
  pure policy test established that result; the exact source was added as the
  next rollover with all earlier archives still required. The activation,
  quota and exit test suites subsequently passed 187 tests. At that point,
  actual activation and evidence migration had not yet run.
- The `04f8bcd` candidate was subsequently activated and the dashboard returned
  HTTP 200. Its first M5 exit attempt blocked on the predecessor-bound owner
  evidence. Read-only validation of all ten preserved activation archives
  confirmed the predecessor receipt's process identity matches the original
  owner confirmation; the original alert witness also validates against that
  predecessor. Tracked application source and dependency inputs are unchanged.
  A live browser preflight using that original confirmation and the new service
  revision passed four outcomes, three current histories and five processes.
  The migration implementation, its deployment and the complete exit gate
  remain subject to their own verification; no new owner action is claimed.
- The migration policy now checks the original owner process and revision
  against the fully retained predecessor activation chain and rejects changed
  tracked application or dependency inputs. It preserves the original owner
  and alert bindings and validates the current service independently. The
  separate current-service and predecessor-owner browser preflight passed
  against the running `04f8bcd` service. A focused migration policy test
  failed before implementation and passed afterward. The migration has not
  been deployed or accepted by the full M5 exit gate.
- The existing 365-day account-history view required thousands of retained
  rows to be paged before reaching current observations, exceeding the
  witness's 300-second browser bound. The live pre-change browser lacked a
  range control. The updated P02 view defaults to 24 hours and retains a
  selectable 365-day range. A real-data preview confirmed the recent chart
  and full-year selection; the unchanged full history verification then
  passed for two sampled accounts (three windows) and the three-account
  selected fleet (four windows), both with zero mutations, in roughly 15 and
  30 seconds respectively. These preview checks are not a built-service or
  final-gate pass. The history view is the sole permitted application-source
  change in predecessor migration, bound to its exact reviewed SHA-256.
- The deployed `9db4c3d` dashboard showed the 24-hour chart and retained the
  selectable full-year range. Its selected-fleet and sample browser checks
  passed on genuine data after identity receipts refreshed. `AUTO-M3-TEST`
  passed 307 tests and `AUTO-MUTATION` passed. The exact current story
  inventory contains 614 parent tests and 558 subtests. One full diagnostic
  run passed all of them with no skips; two prior full runs failed in the
  real containment check with `m5_codex_containment_fd_write_unverifiable`.
  A sanitized diagnostic classified the rejected operation as `fchmod` on a
  managed-profile file. Isolated containment passed repeatedly. Its
  intermittent cause remains unresolved; no containment policy was weakened.
- A gate correction uses the alert's verified account for the alert lifecycle
  tests, independently selects the current service for the containment test,
  records sampled coverage accurately, and binds the gate to the updated exact
  test inventory. Red/green tests cover these corrections. They are not yet
  deployed, and the canonical final gate has not passed.
- Security/privacy: only safe account selectors and quota metadata are used;
  no credential, provider profile or running agent is read or changed. No new
  dependency, license, database migration or public contract is introduced.
- Follow-up: review the increment, bind existing evidence safely to any new
  deployment or repeat affected live checks, obtain current owner-sourced
  sample observations and run `AUTO-M5-EXIT`. The previous screenshot values
  are historical and cannot be asserted current without a fresh observation.
