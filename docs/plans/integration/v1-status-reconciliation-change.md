# V1 implementation-status reconciliation change

- Status: **Approved for implementation** by the owner's 2026-10-01 direction
  to reconcile version and implementation state before evaluating V1-M3 closure.
- Scope: documentation authority and documentation validation only. No provider,
  database, API, UI, process-control, or installed-service behavior changes.
- Requirements / acceptance: `AC-V1-001`, `AC-V1-002`, `AC-V1-006`,
  `AC-TEST-006`.
- Contracts: no runtime contract changes. This change adds the internal
  `agentmonitor.v1_implementation_status` evidence format at schema version
  `1.0.0`.

## Problem

The import-ready implementation backlog intentionally freezes every Story as
`Planned`, while the repository contains completed implementation through the
standalone V1-M4 exit gate. The roadmap uses an older milestone numbering, the
documentation index surfaces only the blocked M3 acceptance record, and several
module guides predate the final M4 evidence. These sources currently make a
single truthful answer about delivery state impossible.

The M3 evidence also contains two facts that must stay distinct: its canonical
technical gate passed on 2026-09-25, while its active formal acceptance record
from 2026-09-24 remains `blocked`. M4's standalone gate later passed, but its
program dependency on accepted M3 is unresolved.

## Change

1. Preserve `implementation-backlog.toml` as the immutable GitLab import
   topology and label it as planning provenance rather than current status.
2. Add one machine-readable V1 implementation-status overlay with all eight
   canonical milestones and all 44 Stories. Record delivery, canonical-gate,
   acceptance, and dependency states separately and bind every non-planned
   claim to repository evidence.
3. Extend `AUTO-DOCS-CHECK` to fail closed if the overlay is absent, structurally
   open, inconsistent with the backlog, missing evidence, or claims a complete
   program state while a dependency is unresolved.
4. Align the roadmap and current module/document indexes to the canonical
   V1-M1 through V1-M8 numbering and the overlay. Preserve historical evidence
   as historical evidence.
5. Publish an M3 closure audit that names current blockers without changing the
   active M3 acceptance result or relabeling unavailable live scenarios.

## Red / Green

Red: add documentation-check tests that require the overlay and reject a Story
whose milestone mapping differs from the frozen backlog. The existing checker
must fail those tests before implementation.

Green: implement the closed-schema validator and add the overlay, then run:

```text
python3 -m unittest tools.docs.test_check tools.planning.test_implementation_backlog
python3 tools/automation/run.py AUTO-DOCS-CHECK
python3 tools/automation/run.py AUTO-PLAN-CHECK
```

## Execution evidence

The first focused test failed as expected because the existing documentation
checker returned no violation when the import backlog existed without a current
status overlay:

```text
FAIL: test_import_backlog_requires_current_implementation_status_overlay
AssertionError: False is not true : []
```

The dependency test then failed because M4 could be marked `satisfied` while
the M3 acceptance row remained `blocked`. Two additional Reds proved that an
accepted milestone could lack distinct decision evidence and that a
`current_implementation_revision` gate binding did not verify its revision.

After implementation and review corrections:

- `python3 -m unittest tools.docs.test_check tools.planning.test_implementation_backlog`
  passed 18 tests;
- Ruff check and format verification passed for the changed Python files;
- `AUTO-DOCS-CHECK` passed 292 Markdown files;
- `AUTO-PLAN-CHECK`, `AUTO-QUALITY`, `AUTO-GIT-PREFLIGHT`, and
  `git diff --check` passed within their documented local scopes.

Independent read-only review corrected two initially overbroad claims: the M4
run has no exact tested-commit binding, and six monitored profile connections
currently resolve to five distinct reported identity quota rows. The final
overlay records the gate as historical and leaves M4 acceptance unrecorded.

## Impact

- Security/privacy: evidence paths and status metadata only; no account aliases,
  provider secrets, profile paths, prompts, responses, or runtime content.
- Migration: none.
- Dependencies/licenses: none.
- Compatibility: additive documentation schema; runtime contracts remain V1.
- Rollback: revert this documentation/validator commit.
