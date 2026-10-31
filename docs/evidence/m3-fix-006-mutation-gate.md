# Test evidence: M3-FIX-006 critical-policy mutation gate

- Evidence ID: `M3-FIX-006`
- Module/plan/increment: foundation test automation consuming M05/M06 V1 pure policies
- Requirements/acceptance IDs: `AC-TEST-005`, `NFR-TEST-001`, `NFR-TEST-002`; M3 Task 6; audit finding `M3-006`
- Contract versions: consumes `CTR-CAP-003`, `CTR-RUN-004`, `CTR-RUN-005`, and `CTR-RUN-007` V1; no contract change
- Commit/worktree reference: uncommitted M3 audit-repair worktree
- Recorder/date: Codex sub-agent / 2026-09-24

## Test inventory and status

| Test/scenario ID | Layer | Real dependencies | Status | Evidence reference | Notes |
|---|---|---|---|---|---|
| M3-FIX-006-AUTO-001 | Automation pure | Production catalog, configuration, exit routine, dependency graph, invariant digest, and mutation summary policy | Passed | Eight focused unit tests below | Rejects absent routine, selector drift, contract drift, zero mutants, unclassified results, and unapproved survivors. |
| M3-FIX-006-PURE-001 | Pure | Production M05/M06 policy and supporting runtime-contract modules | Passed | 73 selected tests | Constructed typed inputs only; no I/O or test double. |
| M3-FIX-006-MUT-001 | Mutation | Locked `mutmut==3.8.0`, forked workers, exact checkout source copied to a private temporary directory | Passed | `AUTO-MUTATION` | 541 generated: 534 killed and seven exact hash-pinned equivalent survivors; 100% of non-equivalent mutants killed. |
| M3-FIX-006-LOCK-001 | Dependency | Actual `backend/uv.lock` and installed `.venv` | Passed | `uv lock --directory backend --check`; frozen sync check | 47 packages resolve; installed environment requires no change. |
| M3-FIX-006-STATIC-001 | Static | Ruff and strict mypy from locked backend environment | Passed | Commands below | Scoped automation and mutation-policy test files passed. |
| M3-FIX-006-EXIT-001 | Automation integration | Production M3 exit routine list and source | Passed | Focused automation test | `AUTO-M3-EXIT` actively iterates `AUTO-MUTATION`; it cannot omit the mutation gate while retaining the tested tuple. |
| M3-FIX-006-QUALITY-001 | Repository quality | Canonical automation unit suite | Passed | `python3 -m unittest tools.automation.test_run` | 44 tests passed after integration regenerated the client and corrected concurrent formatting/type/boundary drift. |
| M3-FIX-006-LIVE-001 | DB/API/browser/provider | None required by this pure-policy gate | Not Run | Not applicable to mutation claim | No live/provider acceptance is inferred from pure mutation results. |

## Red evidence

The automation behavior tests were added before `AUTO-MUTATION`, its catalog
entry, or its fail-closed summary policy existed:

```text
python3 -m unittest \
  tools.automation.test_run.AutomationRoutineTests.test_m3_mutation_gate_is_cataloged_fail_closed \
  tools.automation.test_run.AutomationRoutineTests.test_mutation_summary_policy_rejects_every_non_killed_result \
  tools.automation.test_run.AutomationRoutineTests.test_real_catalog_defines_every_mandatory_routine

exit 1; 3 errors/failures
KeyError: 'AUTO-MUTATION'
ModuleNotFoundError: No module named 'auto_mutation'
mandatory routine set missing 'AUTO-MUTATION'
```

After the runner existed, its first genuine mutation execution failed rather
than accepting the existing tests:

```text
python3 tools/automation/run.py AUTO-MUTATION
exit 1
{"killed":308,"survived":233,"total":541,...all other result classes zero}
M3 MUTATION: FAILED — non_killed_or_unclassified_mutant
```

Strengthening complete returned-value assertions reduced the next run to 31
survivors. Boundary, exact safe-code, policy-match, conflict, and unresolved
correlation assertions killed 24 more. The remaining seven diffs were reviewed
as equivalent and then admitted individually by exact mutant name and SHA-256;
any unlisted survivor or changed surviving diff fails closed.

The independent review rejected that first Green because equivalence approval
was not bound to its supporting contract, the mutmut selectors could drift from
the runner declarations, M3 exit did not invoke the mutation gate, and the
admission listed only 15 of 19 locked packages. Four new tests were added before
their corrections. The combined Red exited `1` with three import errors and one
assertion failure:

```text
ImportError: cannot import name 'equivalence_invariants_match'
ImportError: cannot import name 'mutation_config_matches'
ImportError: cannot import name 'M3_LOCAL_EXIT_ROUTINES'
AssertionError: M3_MUTMUT_GRAPH omitted iniconfig, packaging, pluggy,
typing-extensions
```

The review repairs bind equivalent approval to the exact SHA-256 of
`runtime_observation_v1.py` and explicit invalid-input contract tests; parse and
compare the complete copied mutmut configuration; add `AUTO-MUTATION` to the
actively iterated M3 exit tuple; and verify/document the full 19-package graph.

## Green evidence

The same focused automation command exited `0` after the minimum gate and
catalog implementation. The final focused checks were:

```text
backend/.venv/bin/pytest -q \
  backend/tests/capacity/test_quantity_and_health.py \
  backend/tests/runtime_observation/test_contracts.py \
  backend/tests/runtime_observation/test_runtime_state_policy.py \
  tools/automation/test_m3_critical_mutation_policies.py
# 73 passed in 0.23s

python3 -m unittest \
  tools.automation.test_run.AutomationRoutineTests.test_m3_mutation_gate_is_cataloged_fail_closed \
  tools.automation.test_run.AutomationRoutineTests.test_mutation_summary_policy_rejects_every_non_killed_result \
  tools.automation.test_run.AutomationRoutineTests.test_mutation_equivalence_is_bound_to_contract_invariants \
  tools.automation.test_run.AutomationRoutineTests.test_mutation_config_exactly_matches_runner_targets_and_tests \
  tools.automation.test_run.AutomationRoutineTests.test_m3_exit_actively_runs_the_mutation_gate \
  tools.automation.test_run.AutomationRoutineTests.test_m3_mutmut_dependency_graph_names_the_full_locked_closure \
  tools.automation.test_run.AutomationRoutineTests.test_real_catalog_defines_every_mandatory_routine \
  tools.automation.test_run.AutomationRoutineTests.test_m2_admitted_argon2_graph_matches_real_locked_install
# Ran 8 tests; OK

python3 tools/automation/run.py AUTO-MUTATION
# exit 0
# killed=534, accepted_equivalent=7, total=541
# no_tests/skipped/suspicious/timeout/interrupted/segfault=0
# AUTO-MUTATION: PASSED (operational)
```

The raw mutation kill score is `534 / 541 = 98.71%`. The admitted target is
100% killed among non-equivalent mutants, and it passed. The seven equivalents
remain visible in the output rather than being counted as killed.

## Refactor evidence

```text
backend/.venv/bin/ruff check \
  --config backend/pyproject.toml \
  tools/automation/implementations/auto_mutation.py \
  tools/automation/implementations/auto_m3_exit.py \
  tools/automation/implementations/auto_quality.py \
  tools/automation/test_m3_critical_mutation_policies.py \
  tools/automation/test_run.py
# All checks passed

MYPYPATH=backend/src:tools/automation/implementations backend/.venv/bin/mypy \
  --config-file backend/pyproject.toml \
  tools/automation/implementations/auto_mutation.py \
  tools/automation/implementations/auto_m3_exit.py \
  tools/automation/implementations/auto_quality.py \
  tools/automation/test_m3_critical_mutation_policies.py
# Success: no issues found in 4 source files

uv lock --directory backend --check
# Resolved 47 packages

uv sync --directory backend --all-groups --frozen --check
# Checked 45 packages; would make no changes

git diff --check -- <M3-FIX-006 owned files>
# exit 0
```

The first broader `python3 -m unittest tools.automation.test_run` run remained
Red: `auto_quality.py` encountered concurrent formatting/type/boundary findings
and `auto_build.py` reported generated-client drift. Integration corrected
those actual checkout failures and regenerated the client. The same canonical
suite then passed all 44 tests. The independent mutation re-review separately
returned `APPROVE` after rerunning 73 selected pure tests, eight automation
tests, the real 541-mutant gate, Ruff, strict mypy, lock, frozen-sync, and diff
checks.

## Real-system evidence

The real admitted mutation engine transformed and executed the actual checkout
policy source in forked worker processes. It was not a handwritten mutation,
coverage proxy, or simulated result. The source copy lived in an OS-created
private temporary directory and was deleted afterward. This gate intentionally
performs no database, HTTP, browser, OS-process observation, provider, or owner
account operation; those boundaries remain governed by their separate M3 gates.

## Integrity declaration

No mock, fake, stub, emulator, response recording/replay, demo account, seeded
telemetry, placeholder value, hardcoded pass, disabled assertion, test-only
production branch, or swallowed mutation result was used. Constructed values
appear only in the no-I/O pure policy tests. A non-killed result passes only if
its exact name and rendered diff hash match the seven reviewed equivalent
mutants; every other result class fails.

## Data and secret review

The mutation targets contain only pure policy code. The routine supplies a
minimal environment (`PATH` and `PYTHONHASHSEED`) to workers and neither reads
nor copies `.env`, provider state, telemetry databases, prompts, responses,
source content outside the three named policy files, account identifiers, or
arbitrary process environment values. Output contains safe file/module names,
counts, and mutant IDs only.

## Contract, migration, dependency, and operations impact

- Contracts: no public contract, OpenAPI, generated-client, event, or schema change.
- Compatibility: nonbreaking development-tool addition; production runtime dependencies are unchanged.
- Migration/data: none; no SQLite access or persistence.
- Dependencies: admitted and locked `mutmut==3.8.0` plus its exact 19-package development-only closure in `docs/dependencies/m3-mutmut-admission.md`.
- Licenses/security: direct/transitive licenses and the 2026-09-24 zero-result OSV query are recorded in the admission; release SBOM/notices and future advisory checks remain separate gates.
- Platforms: Linux passed. macOS is supported by upstream's fork model but was Not Run. Native Windows is Blocked by the admitted tool and returns Blocked when `os.fork` is absent.
- Operations: repeatable command is `python3 tools/automation/run.py AUTO-MUTATION`; no provider/profile/process mutation occurs.

## Conclusion and residual gaps

M3-006's critical quota/runtime pure-policy mutation gate is implemented and
passes locally: all 534 non-equivalent mutants are killed and all seven exact
equivalents are independently visible, hash-pinned, and bound to the supporting
contract digest and explicit invariant tests. The exact mutmut configuration is
verified before execution, and M3 exit now actively invokes this gate. This closes only the
mutation-gate finding; it does not close other M3 audit findings or the broader
repository quality/build failures recorded above. macOS execution, native
Windows replacement, release SBOM/notices, and clean release installation are
Not Run.
