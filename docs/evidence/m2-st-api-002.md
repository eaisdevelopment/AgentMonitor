# ST-API-002 — cross-origin perimeter and M2 local gate evidence

> **Post-audit status:** The original acceptance commands below are historical. A real Chrome cross-port image later refreshed a persisted session despite an unreadable response. [ADR 0012](../decisions/0012-cookie-read-origin-proof.md) and the [M2 correction record](m2-audit-fixes.md) supersede the old hostile-no-mutation inference and record the corrected full local gate, owner-accepted historical TDD deviation, and independent post-audit QA reacceptance. The older browser oracle checks response opacity and session identity only. Its `M2-LOCAL-001` mapping to universal `AC-TEST-001` was too broad; the current evidence producer no longer makes that mapping. The other historical commands below remain genuine results for the cited checkout.

- Status: **Accepted for the V1-M2 local authenticated-shell exit gate**. The
  canonical real-stack gate and independent integration review passed; later
  provider, platform, hosted, and release boundaries remain separate.
- Owner/date: P01 Story 6 worker and integration steward, 2026-09-21.
- Requirements/acceptance: `FR-IAM-007`, `AC-UI-001`, `AC-TEST-001..004/006`;
  `M01-HTTP-019/021`, `M01-SEC-008`, `API-BROWSER-006`, `API-SEC-002/003`.
  `AC-OPS-003` is a later provider-adapter isolation criterion, not proven by
  this authentication boundary; its provider portion is **Not Run**.
- Contracts: consumes `CTR-IAM-001..007`, `CTR-UI-001`; verifies
  `CTR-API-001..003` and `CTR-COMMON-005` V1 M2 subset. No API field, route,
  status, schema, permission, database, or configuration version changed.

## Red evidence

The new Origin/bearer tests were **Green on first execution** against the
existing Story 4 transport. No perimeter defect or fictitious pre-fix Red is
claimed. The new hostile-page Chrome scenario likewise passed on its first
execution. A real automation-selection Red was recorded before changing the
canonical runner:

```text
python3 -m unittest tools.automation.test_run.AutomationRoutineTests.test_m2_local_suite_selection_covers_real_backend_and_browser_boundaries
exit 1: ImportError: cannot import name 'm2_local_suite_commands' from 'auto_test'
```

That failure demonstrated that the M1-only runner had no M2 suite selection;
it was not a browser, credential, or test-setup failure.

## Green and refactor evidence

```text
backend/.venv/bin/python -m pytest backend/tests/integration/api/test_origin_policy.py -q --tb=short
exit 0: 2 passed in 2.31s
same command after stronger exact-403 preflight assertion and formatting
exit 0: 2 passed in 1.59s
backend/.venv/bin/python frontend/tests/browser/p02/run_browser.py security_boundary --no-build
exit 0: P02 SECURITY BOUNDARY BROWSER: PASSED; P02 BROWSER: PASSED — security_boundary
python3 -m unittest tools.automation.test_run.AutomationRoutineTests.test_m2_local_suite_selection_covers_real_backend_and_browser_boundaries
exit 0: Ran 1 test; OK
env -i PATH="$PATH" PYTHONPATH="$PWD/backend/src" backend/.venv/bin/python frontend/tests/browser/p02/run_browser.py security_boundary --no-build
exit 0: P02 SECURITY BOUNDARY BROWSER: PASSED (exact AUTO-TEST environment)
env -i PATH="$PATH" PYTHONPATH="$PWD/backend/src" backend/.venv/bin/python frontend/tests/browser/p02/run_browser.py quick --no-build
exit 0: nine real Chrome P02 scenarios passed in 22.27s (exact AUTO-TEST environment)
MYPYPATH="$PWD/backend/src" backend/.venv/bin/mypy --config-file backend/pyproject.toml --explicit-package-bases backend/tests/integration/api/test_origin_policy.py
exit 0: no issues in one source file
backend/.venv/bin/ruff check --config backend/pyproject.toml backend/tests/integration/api/test_origin_policy.py tools/automation/implementations/auto_test.py tools/automation/test_run.py
exit 0: All checks passed
```

The T3 checks use a fresh Alembic-migrated file SQLite, production Argon2
bootstrap, real Uvicorn socket, and real HTTP cookie jar. The hostile logout
request includes valid session cookie, current strong ETag, and matching CSRF
proof but receives 403 `origin_not_allowed`; the same session ID remains
active. Hostile cookie GET is denied, preflight has no CORS grant, and valid
`write:tokens` bearer works with absent or hostile Origin while a wrong scope
gets 403 and invalid bearer 401. The T4 check uses production-built dashboard,
the same real IAM stack, installed Chrome, and a minimal real attacker-owned
page from another loopback port. Credentialed cross-origin GET/DELETE responses
are unreadable to the hostile page, and the original persisted session remains
active after navigation back. No AgentMonitor response is intercepted or
injected. The one-time OS-random test password travels only through private
runner-to-browser stdin; no value is retained here.

`AUTO-TEST` now selects all `backend/tests` with no deselection, the generated
OpenAPI/client check, production Vite build, real M1 browser regression, P02
`all` (including natural ≥61-second touch/logout and ≥1,800-second idle
expiry), and the separate hostile-origin Chrome scenario. `main()` executes
the returned commands fail-closed. Selector Green alone does not claim the
M2 gate Passed; canonical execution and its failures are recorded below.

The first fast build exposed an evidence-mapping error: its local-only Passed
row cited `AC-TEST-004`, which requires owner-countersigned live provider
verification. The M1 foundation test row made the same false implication.
Before correcting those mappings, the new policy test failed as expected:

```text
python3 -m unittest tools.automation.test_run.AutomationRoutineTests.test_local_evidence_cannot_claim_owner_countersigned_live_acceptance
exit 1: AssertionError: ValueError not raised
```

The local evidence builder now rejects a Passed `AC-TEST-004` row without a
supported owner countersignature path. The two local rows cite `AC-TEST-003`
instead. The same focused test passed (exit 0), followed by the complete
automation unit suite (29 tests, exit 0, 9.25s). This is an evidence-policy
correction, not live-provider verification; the subsequent canonical rerun is
recorded below.

The first canonical `AUTO-TEST` execution then exited 1 after 71 planning and
automation tests: two planning assertions reported a stale
`automation-routines` snapshot SHA-256 and byte count. It did not reach the
backend or browser suites. The exact current catalog digest/size were rebound
in `docs/plans/plan-baseline.toml`; the rendered snapshot compares byte-for-
byte, the synchronized planning validator passes, both formerly failing
planning tests pass, and `AUTO-DOCS-CHECK` passes. This correction does not
convert that failed first gate into a pass; its later rerun is recorded below.

The next committed-tree `AUTO-TEST` execution passed all 71 tooling tests,
then failed in the complete backend suite (`511 passed, 2 failed in 391.50s`),
before generated-client or browser stages. The first failure was a real
temporary-Git setup defect in
`test_generator_cli_preserves_outputs_on_refusal[breaking]`: the fixture tried
to commit generated M2 artifacts that were already identical to its committed
HEAD. The focused test reproduced Red (exit 1, empty Git commit), then passed
after a test-only correction that commits only a real staged artifact change.
The related real generator/compatibility cases passed 11/11, and independent
QA accepted that the breaking-drift refusal and byte-preservation assertions
remain effective. The second failure is the real two-worker Argon2 verification
budget: observed p95 0.4578s against the approved 0.250s limit. Separate
focused runs both passed and failed under high workstation load. That gate
attempt remains **Failed**, not retroactively converted into Green; the
low-contention measurement and full canonical rerun are recorded below.
Neither initial failure was a production API or browser pass.

After the Git-fixture correction, a backend run with only the known Argon2
timing case deselected reported an additional failure marker, but the chat
interruption terminated it before pytest produced a result or traceback. Its
status is **Interrupted**, not Failed or Passed. A fresh, non-concurrent run of
the same explicitly narrowed command exited 0: `513 passed, 1 deselected in
312.08s`. That proves the remaining backend tests on this checkout, but does
not satisfy the full `AUTO-TEST` gate or the Argon2 timing acceptance. A first
standalone built-browser `all` run was also terminated by that interruption
without a final status and cannot be counted. Its natural-time scenario has
been restarted with a protected result record; its result follows.

That fresh standalone built-browser `all` run completed with exit 0 on the
same M2 production source and build. Its nine quick real-Chrome workflows
passed; `logout_after_touch` observed at least 61 seconds, and `idle_expiry`
asserted at least 1,800,000 ms of actual elapsed time before showing the
expired-session login state. The protected runner printed only scenario
statuses, not the generated one-time credential. This is valid T4 evidence;
the separately executed canonical `AUTO-TEST` result follows.

## Final committed-source local gate and independent review

The workstation later became less contended without changing user processes:
load was about 3.9 on 16 CPUs and CPU pressure `some avg10=0.42` before a
single targeted run of the unchanged two-worker Argon2 workload (`2 passed`,
exit 0). A separate real production-adapter probe measured p95 `0.122203s`,
peak process RSS `160488 KiB`, and all 100 verifications matched. The Linux
RSS harness correction and its real Red/Green are in
[Story 1 evidence](m2-st-iam-001.md). Earlier p95 failures at `0.4578s`,
`0.2515s`, and `0.4100s` under workstation contention remain historical
Failed results. No hash parameters, limits, test exclusions, process priority,
or owner workloads were changed to obtain the low-contention pass.

On committed production/test source `55d0941`, the canonical command
`python3 tools/automation/run.py AUTO-TEST` exited **0**. Its protected local
run reported 71 tooling tests OK; **514 backend tests passed with no
deselection** on the real migration/SQLite/IAM/HTTP stack; generated OpenAPI
and client compatible with exactly 13 operations; production Vite build;
two real M1 Chrome shell cases; all nine P02 quick workflows; real browser
logout after at least 61 seconds; real idle expiry after at least 1,800
seconds; and the separate malicious-origin Chrome denial. The structured
`M2-LOCAL-001` Passed row cites `AC-UI-001`, `AC-TEST-001/003/006`, and
T2/T3/T4, without claiming owner-countersigned `AC-TEST-004`. Its separate
M0-G1 exact-digest approval is explicitly **Failed (exit 2)**, outside M2.

On the same unchanged source, `AUTO-QUALITY`, `AUTO-BUILD`,
`AUTO-DOCS-CHECK` (208 Markdown files), and `AUTO-PLAN-CHECK` each exited 0.
The production-asset Gitleaks 8.30.0 scan after the final build exited 0 on
`frontend/dist`; this bounded scan does not substitute for full SAST or
vulnerability checks. An independent integration reviewer verified the
protected canonical exit record and its sanitized scenario statuses,
independently reran those four fast gates, confirmed the six M2 Story and
recovery evidence records, and found no further M2-local product blocker.
Only evidence/status documentation changed after the passing source gate;
production, generated client, migration, frontend, and test bytes remained
unchanged.

## Security, privacy, compatibility, and residual state

No production perimeter correction, dependency, migration, provider-profile
access, process control, or remote-service behavior was introduced. The
regressions retain only status/code/session-equality booleans and do not print
cookies, CSRF, bearer, ETag, password, provider content, or raw response bodies.
An independent QA pass found that several older P01 HTTP test assertions
compared a generated credential directly against captured response/process
bytes; a failing pytest rewrite could disclose both operands. Those assertions
in `backend/tests/integration/api/test_iam_http.py` now assert only a derived
boolean with fixed safe failure text, before later assertions inspect captured
content. Equivalent one-time bearer, oversized password, and random submitted-
field/path absence checks in that file were hardened in the same bounded
change; nearby raw-body membership checks also use safe booleans. Four
`Set-Cookie` absence assertions likewise reduce unexpected secret-bearing
headers to a boolean and a fixed message before pytest can introspect them.
This is test-output privacy hardening, not a production behavior correction or
a fabricated TDD Red. The eight initially affected real Uvicorn/file-SQLite
cases passed (`8 passed, 28 deselected in 9.81s`), then the full P01 HTTP file
passed on the final hardened test source (`36 passed in 36.60s`); targeted Ruff
check and format check passed. `AUTO-DOCS-CHECK` passed across 208 Markdown
files before the final evidence wording update.
Independent Story 6 specification and QA reviewers reran the real Origin,
bearer, and hostile-browser checks and found no remaining perimeter or
test-integrity blocker. The recovery correction received its own reviews.

The installed Gitleaks 8.30.0 scanned only staged repository changes and the
current production frontend build, never `.env`. The first staged scan exited
1 on two fixed nonsecret correlation IDs adjacent to a local variable named
`secret`; line inspection confirmed false positives. Renaming that local
variable to `candidate` changed no behavior; the staged scan then exited 0,
and the five real recovery tests and targeted Ruff/format checks passed again.
The final staged command was
`.venv-m0-g1/bin/gitleaks git --staged --no-banner --redact --log-level error --report-format json --report-path /tmp/agentmonitor-m2-scan-s0hQOW/staged-report-after-refactor.json`
(exit 0). The bounded build scan used
`.venv-m0-g1/bin/gitleaks dir frontend/dist --no-banner --redact --log-level error --report-format json --report-path /tmp/agentmonitor-m2-scan-s0hQOW/dist-report.json`
(exit 0). The final production build's assets were rescanned with the same
bounded command, with exit 0. These are secret-pattern scans of the named
surfaces, not a full SAST, vulnerability, or owner-data scan.
The attacker page is test input only, not a simulated AgentMonitor service.
No fake, mock, stub, emulator, recording, seeded telemetry, placeholder metric,
or hardcoded passing test was used.

| Boundary | Current status | Required remaining evidence |
|---|---|---|
| Targeted T3 Origin/bearer, T4 hostile-page Chrome, and standalone full P02 `all` | Passed | Independent specification, QA, and final integration reviews passed |
| Canonical `AUTO-TEST` on committed M2 production/test checkout `55d0941` | Passed, exit 0: 71 tooling tests; 514 backend tests; generated client; production build; M1 and P02 real Chrome; hostile-origin Chrome | Two earlier Failed attempts and one interrupted narrower backend attempt remain documented above |
| `AUTO-QUALITY`, `AUTO-BUILD`, `AUTO-DOCS-CHECK`, `AUTO-PLAN-CHECK` | Passed local scopes, each exit 0 | Fresh install, platform, hosted, and release scopes remain Not Run as below |
| Staged-source and final built-artifact secret-pattern scans | Passed on named surfaces, exit 0 | Full SAST/vulnerability scan remains Not Run |
| Full SAST/vulnerability scan, T5 workstation, T6 provider/account, T7 installed lifecycle, owner live setup, macOS, hosted CI | Not Run | Separate tools/environments/owner evidence; cannot be inferred from local T2/T3/T4 |
| `AC-TEST-004` live provider/account aliases, versions, and owner countersignature | Not Run | Requires actual owner-controlled provider verification; local IAM test credentials do not satisfy it |
| Separate M0-G1 exact-digest approval | Failed in prior independent gate | Outside M2 authentication, still visible and not relabeled Passed |

The integration steward inspected the passing canonical committed-source gate,
the protected sanitized result record, and the independent review: the approved
V1-M2 **local authenticated-shell exit gate is accepted**. This does not accept
the full V1 release, M0 G1, any owner/provider/platform/hosted Not Run boundary,
or V1-M3. No M3 implementation has begun.
