# Change plan: current M3 technical-suite scope

- Status: **Approved for this bounded integration correction** under the owner's explicit direction to correct M3 to one real Claude vertical, keep later milestone work with its owners, and continue the current M3 gate.
- Version: `1.0.0`; date: 2026-10-03; owner: PLAN-INT.
- Scope: `AC-M3-001..007`, chiefly `AC-M3-006/007` and `INT-M3-006/007`; one owner-selected real Claude account.
- Contracts: existing A01/M02/M03/M04/M05/M06/P01/P02 V1 surfaces. A01's published manifest must bind the exact already-approved OTEL mapping bytes; no public contract shape, mapping content, provider operation, API, database schema, or migration change.

## Decision

`AUTO-M3-TEST` selects a guarded, exact set of current one-account M3 tests. It checks the real A01 Claude manifest, M03 production protocol and manifest, registry identity policy, collection, capacity/history, runtime, persistence, and authenticated API boundaries. Its first command checks the target list itself; its second command runs only those targets. Zero skips are required for acceptance, with a fail-closed runner check. `AUTO-M3-EXIT` separately supplies the current installed-service quota, identity, runtime, and built-browser witness before it accepts the technical lane and the other canonical local gates.

The historical `m3_handoff_validate.py --require-technical-live` result belongs to the reviewed 2026-09-25 M0-to-M3 subject. It is historical evidence, not a current-byte gate. The approved `M0ToM03CapabilityMappingV1`, acceptance record, and four pending detached approval records remain untouched. PLAN-M03 §4.2 still requires a versioned successor, review, and approvals for a changed mapping; this correction does not rebind its digest in place or promote pending approvals.

M4 owns six-account Claude fleet, organizations, alerting, and operations. LAN and global M2 routines retain their own gates. M5, M6, M7, and M8 retain their provider and release-wide scopes. An excluded test is not marked passed by M3; the owning milestone must run it.

## Implementation boundary

PLAN-INT owns `tools/automation/implementations/auto_m3_test.py`, the new `tools/automation/test_m3_test.py` and `tools/automation/pytest_no_skip.py`, and sanitized evidence in `docs/evidence/m3-current-gate-implementation.md`. The root integration steward coordinates a sole-writer A01 correction of only `CLAUDE_OTEL_MAPPING_DIGEST` in `backend/src/agentmonitor/adapters/providers/claude/manifest.py`, with the existing `backend/tests/adapters/providers/claude/test_manifest.py` selected as an exact test target. That test must compare the digest to the actual checked-in mapping bytes. The target list must be closed and duplicate-free, each selected path must exist, the guard must reject later-milestone targets, and the runner must fail if pytest reports a skip. The canonical generator may refresh only the OpenAPI/client source-provenance hashes required by the backend source change; its API schema digest and operations must remain unchanged. No provider profile, owner database, service, registry, M0 handoff record, mapping content, or historical evidence is edited by this change. No new dependency is admitted.

## Red, Green, and completion evidence

| Boundary | Evidence | Required result |
|---|---|---|
| Prior broad technical selection | Focused Red: **16 failed, 470 passed, 26 skipped**; later M4/LAN/M2-global and changed migration-head cases entered the M3 lane | Fail; no M3 receipt or acceptance claim |
| Exact target guard | `tools/automation/test_m3_test.py` | **2 passed**, confirming required M3 paths, uniqueness, presence, closed exclusions, command binding, and a real skipped-test negative probe |
| Current technical suites before A01 selection | `python3 tools/automation/run.py AUTO-M3-TEST` | **285 passed, 0 skipped** after the initial scope correction; selected failures block the runner, and skip detection must fail closed before final M3 acceptance |
| A01 mapping provenance | `test_manifest_declares_official_otel_session_lane_separately` | Red: production `CLAUDE_OTEL_MAPPING_DIGEST` began `88f558e1`, while the approved unchanged OTEL mapping file hashes to `b04e8098`; Green binds the exact file digest in the manifest and selected test |
| Expanded guarded technical suite | `python3 tools/automation/run.py AUTO-M3-TEST` | **295 passed, 0 skipped**; the guard separately reports **2 passed**, including proof that one real pytest skip returns exit 1 |
| Canonical current exit | `python3 tools/automation/run.py AUTO-M3-EXIT` on a clean exact revision and selected real account | Still required independently, including fresh provider/browser lineage, mutation, quality, build, docs, Git, owner countersignature, and historical TDD disposition |

The numbers above describe the focused observed Red and Green; they do not substitute for a clean-revision `AUTO-M3-EXIT` receipt. The runner loads a pytest plugin that changes an otherwise successful session to exit 1 when any selected test skips or xfails. Its negative test executes a real temporary pytest case marked skipped and verifies that failure. The A01 digest correction changes only the manifest's bound provenance value, not the historical mapping. Pure no-I/O mapping and runtime-policy tests use constructed typed values; persistence and API tests use their real local boundaries, while the separate gate supplies the real browser/provider witness. No constructed value is used as provider-boundary evidence. Run `AUTO-PLAN-CHECK`, `AUTO-DOCS-CHECK`, and the guarded technical command on the final checkout; report each exit code and any Blocked or Not Run lane separately.

## Impact and handoff

The correction has no data migration, license, service, provider-state, API-shape, or UI behavior change. The generated OpenAPI/client pair changes only its source-provenance hashes and retains the same schema digest and 66 operations. Output remains bounded test status and sanitized gate results; no account identity, profile path, credential, prompt, response, or raw provider payload is included. The main risks are accidentally omitting a current M3 behavior while narrowing a directory target, allowing a hidden skip, or binding A01 to stale provenance. The exact target guard, skip negative test, A01 mapping-file digest test, and `AUTO-M3-EXIT` real account/browser checks are the review boundary; any new M3 criterion must be added by an explicit scoped decision, not by silently widening a directory. Root owns the final clean-revision run, receipt review, owner decisions, and acceptance status. Until that gate passes, M3 remains an intermediate result.
