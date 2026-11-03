# Test evidence: sealed release source revision

- Evidence ID: `M6-SEALED-SOURCE-REVISION-2026-11-03`
- Module/plan/increment: Foundation composition build metadata; approved M6 exact-revision correction
- Requirements/acceptance IDs: `FR-OPS-006`, `NFR-SEC-001`, `NFR-TEST-001/002`, `NFR-COMP-001`; `M6-A10`; supporting `FND-META-001`
- Contract versions: `CTR-FND-007 BuildMetadataV1` remains compatible and unchanged
- Commit/worktree reference: isolated worktree based on `4d189ca19f18ca8dd435d4ffbd8861e913e6eca4`
- Recorder/date: Codex / 2026-11-03

## Test inventory and status

| Test/scenario ID | Layer | Real dependencies | Status | Evidence reference | Notes |
|---|---|---|---|---|---|
| `M6-SOURCE-REV-RED` | Real Git/filesystem | Real clone of the tracked candidate checkout, `/usr/bin/git`, retained-release permission seal | Failed as expected | Focused Red below | Unchanged sealed bytes were rejected as dirty by `diff-index` |
| `M6-SOURCE-REV-GREEN` | Real Git/filesystem | Same real clone and seal | Passed | Focused Green below | Exact 40-character HEAD returned; Git index identity unchanged |
| `M6-SOURCE-REV-DIRTY` | Real Git/filesystem | Real temporary Git repository | Passed | Full owning test module | Tracked, staged and untracked changes still yield unknown revision |
| `M6-SOURCE-REV-DEPLOYED-DIAGNOSTIC` | Read-only deployed filesystem | Deployed retained release at `4d189ca` | Passed diagnostic | Read-only command result below | Corrected isolated reader returned exact HEAD; index identity unchanged |
| Authenticated version API and browser after corrected deployment | Real HTTP/browser | Integrated, reviewed, deployed successor revision and signed-in browser | Not Run | Root integration follow-up | This isolated correction does not deploy itself |

## Red evidence

Before production code changed:

```text
PYTHONDONTWRITEBYTECODE=1 python -B -m pytest -q \
  -p tools.automation.pytest_no_skip \
  backend/tests/integration/foundation/test_source_revision.py::test_real_sealed_tracked_checkout_reports_clean_revision_without_index_write

1 failed
AssertionError: assert None == '4d189ca19f18ca8dd435d4ffbd8861e913e6eca4'
```

The test cloned the actual tracked checkout with `--no-hardlinks`, waited for a
distinct filesystem ctime interval, and applied the same permission policy as
the retained release: remove all file write bits and make directories `0500`.
The setup proved raw `diff-index --quiet` returned 1 while porcelain
`diff --quiet` returned 0 for the same unchanged tracked bytes. This was a
behavioral Red, not a setup or dependency failure.

## Green evidence

The reader now uses read-only porcelain
`git diff --no-ext-diff --no-textconv --quiet HEAD --` under the existing fixed
executable, minimal environment, disabled filesystem monitor, disabled
untracked cache and `GIT_OPTIONAL_LOCKS=0`. It retains the separate
untracked-file check and before/after HEAD equality check.

```text
PYTHONDONTWRITEBYTECODE=1 python -B -m pytest -q \
  -p tools.automation.pytest_no_skip \
  backend/tests/integration/foundation/test_source_revision.py

3 passed
```

The sealed-clone test records the Git index device, inode, mode, link count,
owner, group, size, mtime and ctime before the reader and requires the same
identity afterward. The tracked/staged/untracked regression test remains green,
so the correction does not reinterpret a genuinely dirty checkout as clean.

## Refactor evidence

No architecture expansion or refactor was needed. The production correction is
one Git subcommand replacement. Ruff passed for the changed test, Ruff format
passed for both changed Python files, strict mypy passed for both, and
`AUTO-DOCS-CHECK` plus `git diff --check` passed. A direct whole-file Ruff
check of `bootstrap.py` still reports the pre-existing import-order finding
present at base `4d189ca`; this focused correction neither changes nor
suppresses that unrelated baseline finding.

## Real-system evidence

A read-only diagnostic against the deployed retained release at revision
`4d189ca19f18ca8dd435d4ffbd8861e913e6eca4` reproduced the exact condition:

```text
diff-index=1
diff=0
index-unchanged=yes
```

The corrected isolated reader was then invoked read-only against that same
retained release and returned the exact `4d189ca19f18ca8dd435d4ffbd8861e913e6eca4`
HEAD with `index-unchanged=yes`. All commands used `GIT_OPTIONAL_LOCKS=0`; no
release file, index, service, database, browser session or provider state was
changed. The corrected code has not been deployed in this isolated increment,
so a real authenticated
`/api/v1/operations/versions` and browser witness remain Not Run here.

## Integrity declaration

No mock, fake, stub, emulator, response recording/replay, demo account, seeded
telemetry, placeholder value, test-only production branch, patched subprocess
or swallowed failure was used. The tests use the actual Git executable, actual
tracked repository bytes and actual filesystem permission changes in a private
temporary clone.

## Data and secret review

No credential, `.env`, provider profile, provider payload, prompt/response,
account identifier, database row or arbitrary process environment was read or
recorded. Evidence contains only the safe technical source revision and closed
command outcomes.

## Conclusion and residual gaps

The evidence proves that an unchanged retained release can report its exact
HEAD after permission sealing without writing its Git index, while real
tracked, staged and untracked changes still fail closed. There is no public
API, schema, migration, configuration, dependency, license or source-hash
change. Independent review, integration into the current M6 candidate,
deployment through the existing reviewed update path, and the authenticated
version API/browser witness remain required before `M6-A10` or M6 completion
can be claimed.
