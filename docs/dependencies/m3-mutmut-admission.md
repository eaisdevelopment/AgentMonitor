# M3 mutmut dependency admission

- Record: `M3-FIX-006-DEP-001`, researched and approved 2026-09-24.
- Status: **Approved for the M3 audit-repair development dependency and
  `AUTO-MUTATION` gate** by the root integration/test instruction for M3-006.
- Scope: `V1-M3`, M05 capacity health and M06 runtime state/correlation pure
  policies; `AC-TEST-005`, `NFR-TEST-001`, `NFR-TEST-002`.
- Contract impact: none. This is foundation-owned test tooling and does not
  alter a product, provider, API, event, database, or configuration contract.

## Need and selected tool

The audit requires actual mutation execution, a score, and a survivor report.
Ordinary branch coverage and handwritten source edits cannot satisfy that gate.
Python's standard library has no mutation runner. The selected direct development
dependency is [`mutmut==3.8.0`](https://pypi.org/project/mutmut/3.8.0/), from
the canonical [`boxed/mutmut`](https://github.com/boxed/mutmut) project.

Version 3.8.0 was published on 2026-09-12, supports Python 3.10 and later, and
uses BSD-3-Clause. Its universal wheel is 81,469 bytes with published SHA-256
`4c0abcef6b8d1116f2adfaad19df12e1c621e4a402d4367ef15bf8cba497b91d`.
The upstream repository was active on 2026-09-12 and was not archived. No
upstream `SECURITY.md` was found, so vulnerability disclosure depends on the
public issue/advisory channels and AgentMonitor's scheduled review.

Mutmut requires `fork`; the gate is admitted for Linux and macOS and must return
Blocked on a platform without `os.fork`. It performs local source transformation
and pytest execution. No documented analytics or outbound runtime behavior was
found. The gate neither opens a network connection nor invokes a provider,
database, HTTP service, browser, or operator account.

## Exact Python 3.12 graph

`uv pip install --dry-run --python backend/.venv/bin/python mutmut==3.8.0`
resolved the following exact graph on 2026-09-24. Existing locked packages used
by the graph are marked as such; all other rows are new development-only
transitives.

| Package | Version | Role | License |
|---|---:|---|---|
| `mutmut` | `3.8.0` | Direct mutation runner | BSD-3-Clause |
| `click` | `8.5.0` | CLI; already locked | BSD-3-Clause |
| `coverage` | `7.16.1` | Execution/coverage instrumentation | Apache-2.0 |
| `iniconfig` | `2.3.0` | Pytest configuration parser | MIT |
| `libcst` | `1.9.0` | Concrete-syntax mutation engine | MIT with PSF-2.0 and Apache-2.0 notices for identified derived files |
| `packaging` | `26.3` | Pytest version/specifier support | Apache-2.0 OR BSD-2-Clause |
| `pluggy` | `1.6.0` | Pytest plugin dispatch | MIT |
| `pytest` | `9.1.1` | Existing admitted test runner | MIT |
| `setproctitle` | `1.3.7` | Worker process labels | BSD-3-Clause |
| `textual` | `8.2.8` | Upstream result browser dependency; canonical gate is non-interactive | MIT |
| `linkify-it-py` | `2.2.0` | Textual link parser | MIT |
| `markdown-it-py` | `4.2.0` | Textual Markdown rendering | MIT |
| `mdit-py-plugins` | `0.6.1` | Textual Markdown plugins | MIT |
| `mdurl` | `0.1.2` | Markdown URL parser | MIT |
| `platformdirs` | `4.11.12` | Textual platform paths | MIT |
| `pygments` | `2.21.0` | Text rendering; already locked | BSD-2-Clause |
| `PyYAML` | `6.0.3` | LibCST Python 3.12 dependency | MIT |
| `rich` | `15.0.0` | Textual terminal rendering | MIT |
| `typing-extensions` | `4.16.0` | Backported typing primitives used by the graph | PSF-2.0 |

The 19-package closure includes mutmut's complete resolved dependency path,
including pytest and its `iniconfig`, `packaging`, and `pluggy` dependencies,
plus the shared `typing-extensions` dependency. The resolver selected no
optional syntax-tree extras, test extras, or `toml`
backport on Python 3.12. Coverage, LibCST, PyYAML, and setproctitle may use
platform-specific native wheels; the gate uses only registry-resolved locked
artifacts and does not authorize source builds for a release bundle. Mutmut,
Textual, Rich, and the Markdown stack increase only the development environment,
not the shipped backend runtime dependency list.

OSV `querybatch` requests covering all 19 exact PyPI name/version tuples returned HTTP 200
with zero listed vulnerabilities on 2026-09-24. This is a point-in-time lookup,
not proof of absence. Release SBOM/notices, clean frozen installation, macOS
wheel verification, and full dependency/license scanning remain separate release
gates.

## Exact mutation policy

The admitted M3 gate targets only these production pure-policy files:

- `src/agentmonitor/modules/capacity/domain/health.py`;
- `src/agentmonitor/modules/runtime_observation/application/correlation.py`;
- `src/agentmonitor/modules/runtime_observation/application/state.py`.

It selects only their existing pure tests:

- `tests/capacity/test_quantity_and_health.py`;
- `tests/runtime_observation/test_contracts.py`;
- `tests/runtime_observation/test_runtime_state_policy.py`.

The gate additionally copies
`tools/automation/test_m3_critical_mutation_policies.py` into its isolated
workspace. That focused pure suite enumerates the published capacity-health,
stall, and policy-precedence decisions and asserts complete returned values; it
uses only constructed typed inputs and performs no I/O or test substitution.
That selected suite explicitly proves the two contract invariants on which the
equivalent-mutant classifications depend: runtime state and certainty become
unknown together, and Strong correlation evidence carries an account exactly
when its evidence class is Strong.

The automation copies the exact checkout source and selected tests to an
OS-created private temporary directory because mutation necessarily rewrites a
source copy. It never applies a mutant to the checkout. The clean selected tests
must pass before mutants execute. At least one mutant must exist, and every
non-equivalent generated mutant must be killed. A non-classified survivor,
no-test, skipped, suspicious, timeout, interrupted, segfaulted, unclassified,
or unchecked result fails the gate. Timeouts are not counted as kills.

There is no blanket equivalent-mutant exclusion. Seven exact surviving diffs
are admitted by name and SHA-256 after review of the frozen source and locked
mutmut version:

- five mutations of `state == "unknown" or certainty == "unknown"` are
  equivalent because `RuntimeStateEvidenceSummaryV1` rejects either value being
  unknown without the other;
- changing the correlation conflict guard from `> 1` to `>= 1` is equivalent
  because the immediately preceding `== 1` branch returns;
- changing the strong-evidence/account-present conjunction to a disjunction is
  equivalent because `CorrelationEvidenceInputV1` enforces their equivalence.

Any survivor outside that exact set or with a changed diff hash fails closed
and requires new review; killing a listed equivalent remains acceptable. The
entire supporting `runtime_observation_v1.py` contract source is independently
SHA-256 pinned by the gate, and any contract change blocks equivalence approval
until review updates both the invariant tests and digest. The gate also parses
the copied `pyproject.toml` and requires its source targets, selected tests,
pytest arguments, process isolation, change detection, and dependency-change
policy to match the runner's exact declarations before mutation starts. The
target is 100% killed among non-equivalent mutants. The admitted run's raw kill
score is reported separately and cannot conceal a survivor. Any other survivor
requires its exact mutant diff, an independent written equivalence
classification, and a narrowly reviewed gate change, or a meaningful test that
kills it. Percentage alone can never override a non-killed result.

## Alternatives, pinning, and removal

- `cosmic-ray` was rejected for this first gate because it adds a broader
  orchestration/configuration surface without improving the selected pure-policy
  claim.
- `mutatest` was rejected because its maintenance/version suitability was less
  compelling than the current mutmut release.
- A handwritten mutation script was rejected as circular and incomplete.
- Coverage-only acceptance was rejected by `AC-TEST-005` and the audit.

The direct dependency is exactly pinned and every resolved version is locked.
Updates repeat license, advisory, CLI/config, mutant-semantics, and platform
review. Removal is safe after replacing the canonical mutation routine with an
equivalent admitted fail-closed tool and updating its evidence; no product data
or migration is involved.

## Execution status

The graph, policy, license classes, maintenance, platform limitation, security
lookup, necessity, alternatives, and removal path were approved before
installation. The manifest/lock and installed metadata now match the admitted
versions. The canonical Linux run generated 541 mutants, killed 534, admitted
seven exact hash-pinned equivalents, and had no other result class. The raw kill
score is 98.71% and the non-equivalent kill target is 100%. Full commands and
residual Not Run items are recorded in
`docs/evidence/m3-fix-006-mutation-gate.md`.
