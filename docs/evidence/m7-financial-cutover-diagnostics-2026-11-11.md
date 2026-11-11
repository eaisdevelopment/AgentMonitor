# M7 financial cutover diagnosis and bounded integration

Status: Intermediate T014/T003 under approved focused plan 1.1.0.
Requirements FR-BUDGET-001/004, AC-OPS-003, AC-TEST-001/006; M7-A10.
Root owns existing local deployment operators. No product contract/schema or
migration change, dependency, secret-custody or license change.

The b69d96a installed financial attempt reported only
`m7_setup_cutover_journal_review`. Read-only follow-up proved the old retained
7e252b8 service active, schema v1_0731 and no remaining transition journal.
Those facts did not prove an underlying cause and did not justify a database
restore. The existing catch discarded the original error and pre-stop cleanup
could remove the journal, leaving no actionable diagnostic.

## Change and safety boundary

The existing transition now retains a closed execution phase and allowlisted
reason in CutoverError while preserving its original generic exception code.
CLI/M7 output carries only that validated pair. SQLite busy/locked classification
uses driver error numbers, never raw SQL/error text. Unknown exception payloads,
paths and extra output are not emitted. Fixed phases cover preflight, locks,
journal/guard operations, barrier, stop/quiescence, migration and startup.

Lock, guard, backup, migration, stop/start and finally-cleanup decisions are
unchanged. A diagnostic is not permission to restore/retry: actual installed
revision/schema/journal still determine the recovery path. Candidate startup
never authorizes an automatic old-database restore.

## Red and Green

- Modified the existing disposable-systemd/real-SQLite writer-contention test
  to require phase `write_barrier` and reason `persistence_busy`.
- Red: one failed/23 deselected; missing CutoverError phase attribute. The
  initial safe formatter implementation then failed the reason assertion;
  the actual SQLAlchemy-wrapped driver error required numeric classification.
- Green: seven passed/23 deselected, covering the actual writer refusal plus
  pure closed-message/privacy and M7 translation checks.
- Broader selected regression: 25 passed and one failure. Real normal, child,
  writer and restoration scenarios passed. The failing isolated selector clone
  copied the operator without its newly introduced diagnostic module; its actual
  Python process returned ModuleNotFoundError rather than the expected refusal.
  Clone preparation now packages the actual current operator sources and helper,
  without replacing any implementation or adding provider fixtures.
- Independent read-only review found no safety decision changed or raw payload
  path; it confirmed the M7 final result preserves the closed diagnostic.

Actual test command (existing candidate supplies real built files; installed
service is not the disposable test target):

```text
PYTHONPATH=backend/src:. AGENTMONITOR_TEST_CANDIDATE=<retained-b69d96a-release> backend/.venv/bin/python -m pytest -q --tb=short tools/automation/tests/test_m7_cutover_diagnostics.py tools/automation/tests/test_m7_setup_selector.py tools/automation/tests/test_m6_cutover.py -k 'not disposable or normal or writer or child or restore]'
```

Root's AUTO-QUALITY passed: formatting, strict backend typing, zero boundary
violations, 85 compatible generated operations, frontend typecheck and build.
Scoped operator mypy with explicit bases and silent imported-module traversal
passed five files. An unrestricted operator traversal reports four existing
errors in m6_controlled_recovery_evidence.py, m6_direct_evidence.py and
 auto_m6_exit.py; these are not a passing result and were not suppressed in
that invocation. They are outside this diagnostic change; the normal quality
command remains a narrower backend/frontend static check.

The writer test proves diagnostic behavior, not the original installed failure's
cause. Authenticated installed financial/browser proof, successful financial
activation and full M7 acceptance are still required. No provider request,
account/key configuration or user-agent/profile mutation was performed by this
change. Follow-up: prepare the checked clean candidate, use the normal activation
path, inspect actual phase/reason and service state, and fix the observed cause.

Final selector/diagnostic/preparation regression after packaging correction:
**23 passed in 19.64 seconds**, using actual clean isolated clones and the real
financial migration/build rehearsal. No provider success or installed transition
is inferred. The earlier selected real cutover/recovery cases were already green;
the corrected selector failure was rerun in this final selection.


## Same-schema Overview follow-up

The e310b82 and b617268 Overview update attempts returned the old generic
same-schema wrapper message. The second real attempt identified a
`QuiescentStopError` in the stop phase, but the closed formatter omitted its
reason and the wrapper omitted the formatted diagnostic. The dashboard remained
on ca5f062, active/running, with no retained transition journal or restart guard;
its original on-failure restart policy was restored. Read-only release/unit/
process checks passed. No database restore was performed.

The same-schema wrapper now uses the existing safe formatter. Its fixed reason
vocabulary includes eleven existing quiescent-stop refusals; no raw exception,
PID, command line or provider detail is emitted. Stop/recovery decisions are
unchanged. Pure Red: eleven reason-preservation cases failed with
`unexpected_failure`. Green: all seventeen diagnostic cases plus twenty-one
real clean/dirty/revision controller checks passed (38 total). Scoped Ruff and
diff checks passed. Files: existing current-update wrapper, diagnostic helper,
its pure regression tests and this evidence. No contract, migration, dependency,
license, secret or owner-configuration change. The exact stop refusal and new
installed Overview/browser result still require the next checked attempt.


## Bounded stop correction for naturally completed children

With safe diagnostics installed, the e98bc80 update returned
`M6 CUTOVER: BLOCKED — phase=stop reason=unit_has_children_or_not_stopped; review service and journal state`.
The original service remained active and the transition cleaned up its journal
and guard. Read-only process metadata showed transient child creation/completion;
no process arguments, environment values or provider payloads were inspected.

A real disposable systemd regression reproduced the defect: its parent starts
an actual short-lived child and waits to reap it. Freezing the parent prevents
that wait from completing, so the previous three-second check refuses even
after the child naturally exits. Red:1 failed/5 deselected with the same closed
reason. This establishes the primitive defect, not the exact identity of every
child in earlier dashboard refusals.

The primitive now briefly resumes only the already-bound parent through its
pidfd, rechecks invocation/start/executable/cgroup identity and freezes it again
within the existing retry window. The systemd query is bounded by remaining
retry time. It never signals children, extends the retry window, skips the
final frozen/child-free proof, or changes restart/recovery policy. Long-running
children still cause refusal and the parent resumes. No user agent/default
profile is a test target.

Independent review caught a race in the new test's post-reap marker assertion;
the parent may correctly stop before writing that marker. The corrected test
requires an observed live child before stopping, its absence afterward and a
stopped parent. It also led to bounding each retry's systemd query by remaining
time. After both corrections all6 real quiescent-stop scenarios and17 pure
diagnostic cases passed (23 total). Scoped lint/type checks and disposable
full-cutover regression results are recorded with the final check below.

Files: m6_quiescent_stop.py, its existing real-system tests and this evidence.
No product contract/schema, migration, dependency/license, secret custody or
owner configuration changes. Existing T014/AC-OPS-003/AC-TEST-001/006 scope.

Final scoped verification: Ruff and mypy passed; the existing disposable real
systemd/SQLite cutover cases normal, child and writer passed (3 passed,
21 deselected). Documentation validation and diff checks passed. The installed
update and authenticated Overview rerun remain separate operational evidence.
