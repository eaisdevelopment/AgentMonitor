# ST-PROV-001 — provider protocol evidence

- Status: **Accepted for the V1-M3 pure Task 1 scope**.
- Module/plan: M03 provider system, V1-M3 Task 1.
- Requirements/acceptance: `FR-COL-004/006..008`, `FR-AUTH-001`,
  `NFR-ARCH-001/002`, `NFR-COMP-001`; `M03-PURE-001..024/031..034`.
- Contracts: publishes the pure Python forms of `CTR-COMMON-004/007` and
  `CTR-PROV-001..008` V1. Persistence and provider conformance are excluded.
- Implementation commit: `37883ed`, based on `1cb57b6`; mapping
  `M0-M03-CLAUDE-001` V1 digest
  `5a179f872951ce7052160d8e1b568ab1ad4c6f021d60e742e9e096f2c31fd413`
  after the machine-readable schema binding was published.
- Recorder/date: root integrator, 2026-09-22.

## Delivered behavior

The provider-neutral layer now defines closed capability, version, source,
constraint, request, outcome, provenance, authentication, identity, and retry
contracts. Resolution rejects stale M0 mappings, incompatible protocol or
capability schemas, unverified opaque provider versions, unapproved source
chains, and ungranted experimental sources before invocation. Outcome
validation preserves the exact negotiated source or an explicitly approved
fallback with lineage. Catalog replay is idempotent and conflicting reuse is
isolated.

No provider adapter, profile access, network call, process read, persistence,
migration, HTTP route, generated client, or UI behavior was implemented in
this Story.

## Test inventory and status

| Test/scenario | Boundary | Status | Result |
|---|---|---|---|
| `M03-PURE-001..024/031..034` | Pure deterministic domain/contracts | Passed | 74 collected and passed |
| `CTR-PROV-002` manifest schema | Real committed artifact + deterministic checker | Passed | 6 schema tests; provider total 80 |
| Module boundary and static quality | Real checkout/toolchain | Passed | Ruff, format, strict mypy, zero boundary violations |
| Canonical `AUTO-QUALITY` | Real backend/frontend toolchain and production build | Passed | Exit 0 |
| `M03-CONF-001..006`, `AC-LIVE-004` | Real adapter/provider conformance | **Not Run** | Deferred to `ST-CLA-001`; current authorization is pure-only |
| `M03-PURE-025..030` | Reauthentication and extension governance | **Not Run** | Outside the approved Task 1 scenario slice |
| DB/API/browser/provider/platform | External/real boundaries | **Not Run** | This Story makes no claim at those boundaries |

## Red evidence

The initial whole-file run at `2026-09-22T14:36:54Z` exited 2 because
`common_provenance_v1` did not exist. This is retained as an expected missing
implementation signal, but is not claimed as behavioral Red.

Meaningful pre-fix behavioral Reds were:

| Time (UTC) | Command/test | Sanitized expected failure |
|---|---|---|
| 2026-09-22T15:22:13Z | `pytest ...::test_stale_freshness_requires_an_expired_deadline -q` | `DID NOT RAISE provenance_stale_time_invalid` |
| 2026-09-22T15:23:38Z | `pytest ...::test_mapping_digest_mismatch_is_rejected_before_resolution -q` | actual `resolved`; expected `mapping_binding_invalid` |
| 2026-09-22T15:33:17Z | `pytest ...::test_approved_fallback_accepts_exact_actual_source_and_lineage -q` | actual `invalid_provider_data`; expected approved `success` |
| 2026-09-22T15:47:28Z | `pytest ...::test_source_transition_rejects_empty_or_invalid_failure_codes -q` | three cases did not reject empty, blank, or duplicate failure-code sets |
| 2026-09-22T15:48:19Z | `pytest ...::test_fallback_without_prior_failure_code_is_rejected -q` | source-only lineage returned `success`; expected `invalid_provider_data` |

Earlier signature-drift `TypeError` failures are explicitly not behavioral
evidence. Strengthened acceptance checks for the other pure scenarios were
added after the minimum implementation or already passed when added. They are
regression evidence, not retroactively labelled Red. This disclosure is a
Story-level TDD evidence limitation; Red-first remains mandatory for later M3
changes.

## Green and refactor evidence

```text
python3 -m pytest backend/tests/provider_system/test_protocol.py --collect-only -q
74 tests collected                                  [exit 0]

python3 -m pytest backend/tests/provider_system/test_protocol.py -q
74 passed in 0.12s                                  [exit 0]

python3 -m pytest backend/tests/provider_system \
  backend/tests/foundation/test_contract_boundaries.py -q
249 passed in 3.64s                                 [exit 0]

MYPYPATH=backend/src backend/.venv/bin/mypy \
  --config-file backend/pyproject.toml --explicit-package-bases \
  backend/src/agentmonitor backend/tests/provider_system/test_protocol.py
Success: no issues found in 42 source files           [exit 0]

python3 tooling/foundation/check_boundaries.py .
boundaries: PASS (0 violations)                       [exit 0]

python3 tools/automation/run.py AUTO-QUALITY
AUTO-QUALITY: PASSED (operational)                    [exit 0]
```

The first canonical quality run failed only on import grouping. It was not
reported as passed. After the one-line correction, the final run passed Ruff,
formatting, strict mypy, boundary checks, the 13-operation generated OpenAPI
compatibility check, frontend typecheck, locked inputs, and the production
frontend build. Hosted GitLab, live provider/platform checks, full secret/SAST/
vulnerability scans, fresh frozen install, and release SBOM/notices remained
Not Run as the canonical command reports.

The machine-readable schema closure is commit `57ee900`. Its initial missing
generator import was not claimed as behavioral Red. After generator plumbing,
the focused suite produced a real `FileNotFoundError` for the absent required
committed schema artifact; generation made the same six tests pass. The
artifact at `contracts/provider-system/capability-manifest-v1.schema.json` has
SHA-256 `d86958cb4f2c3805fee5bed51a6c590810ccf33e270c50371274308d07603466`.
Independent review accepted exact reproduction, closed required fields and
properties, enums/bounds/patterns, Python semantic-authority binding, and its
canonical `AUTO-QUALITY` check.

## Integrity, security, and compatibility

The tests use constructed immutable values only in pure deterministic code.
There are no mocks, fakes, stubs, emulators, response recordings, provider
fixtures, seeded telemetry, placeholder UI values, disabled assertions, or
test-only production branches. Invocation callbacks are used only as
never-called pre-I/O sentinels and assert zero calls. Source-substitution and
fallback checks call the pure outcome validator directly.

No credential, account identity, provider payload, prompt, response, source
content, command line, process environment, profile path, or raw external data
was read or retained. No dependency, migration, public HTTP/OpenAPI shape, or
external state changed. Unknown/incompatible inputs fail closed.

## Residual work

- Complete detached security/privacy, test-integrity, and root-integration
  approval against the final bound artifacts.
- Keep real adapter/provider conformance visibly Not Run until `ST-CLA-001`.
- Preserve the disclosed Red-evidence limitation; do not use this Story as a
  precedent for post-implementation tests in later M3 work.

The first independent reacceptance rejected an unenforced fallback failure-code
policy. That finding produced the final genuine Red cases above. Independent
re-review of commit `37883ed` accepted the corrected transition validation,
typed fallback lineage, 74-test result, strict typing, formatting, and zero
boundary violations. Acceptance remains limited to the pure Task 1 scope.
