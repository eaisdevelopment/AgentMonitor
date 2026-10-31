# ST-API-001 — IAM HTTP boundary and generated client evidence

- Status: **Accepted for V1-M2 Story 4** after final root, specification, and QA review.
- Owner/date: Story 4 P01 worker, 2026-09-20.
- Requirements/acceptance: `NFR-API-001/002`, `FR-IAM-007`, `AC-TEST-004`;
  `API-PURE-001..010`, `API-HTTP-001..009/039/041`, `API-OAPI-001..004`,
  `API-CLIENT-004/006/007` within the approved M2 overlay.
- Contracts: publishes `CTR-API-001..003` and `CTR-COMMON-005` V1 M2 subset;
  consumes `CTR-IAM-001..008`, `CTR-DB-002`, `CTR-FND-002` V1. No DDL or IAM
  credential-policy change is owned here. OpenAPI and TypeScript client are
  generated, not hand-edited.

## Delivered and bounded scope

The M2 production composition wires the 13 frozen IAM routes to M01
application ports. The local transport enforces canonical Host/Origin,
cookie/bearer separation, CSRF for ambient-cookie mutations, size/concurrency/
deadline bounds, safe problem mapping, correlation, private security headers,
and a service-held exclusive recovery lock. M1 foundation-contract mode
remains separate with its empty operation surface. The fixed generation command
produces the 13-operation OpenAPI and strict TypeScript client. Token 201
responses omit the dead `Location` header by root-approved exception to P01
Draft §8.1; no 14th route is created. See [boundary document](../api/http-boundary.md).
Problem `type` values are closed, same-origin `/problems/{code}` references to
an authenticated local HTML documentation route outside OpenAPI. For one-time
password/token issue, M01 completed-receipt detection precedes a stale
wrong-subject precondition; a new wrong-subject request still fails 412 with
no mutation. This is the root-approved M2 contract direction recorded in the
frozen overlay and plan. The M2 IAM list-query
profile is now explicitly frozen in the overlay: P01 supplies the three fixed
stable sort orders, rejects undeclared filters/repeated singletons, and wraps
M01's raw keyset ID in a versioned, authenticated, 15-minute cursor bound to
the normalized query and exact credential authority. No M01 list-port or
repository change was made. Ordinary SafeProblem responses omit optional
`errors`; live validation problems include safe field errors; `next_cursor`
remains explicit JSON null on a final page. The published M2 list parser now
represents each fixed primary sort with its descending opaque-ID tie-breaker
as an internal two-field order before binding a cursor. `SafeProblemV1.detail`
is optional but non-null in OpenAPI and the generated TypeScript client, while
current runtime errors still emit an allowlisted string. This is a pre-release
M2 draft correction aligning P01 §11, not a silent change to a published stable
V1 guarantee; it adds no migration and relaxes client response requirements.
The seven existing IAM wire component names are now aligned to P01 §12.9,
without renaming M01 DTOs. Initialization now passes through its three safe
`CTR-IAM-004` fields (`state`, nullable `policy_version`, `schema_revision`)
instead of dropping two. This is a pre-release M2 OpenAPI/client contract
correction: regenerated client names change, but there is no database or IAM
port migration and no new dependency. M2's revoke-other-sessions operation
continues to have no request body; proposed Draft `RevokeSessionsInputV1`
does not match its approved all-others port and is not invented here. The
single 13-row generator oracle now requires the exact existing per-operation
request/success schemas and the frozen 15 SafeProblem status declarations.
An additive pre-release M2 `SafeProblemV1.committed_resource` object now
contains only API-token ID, version, and state on committed token create/rotate
one-time replay; it is optional but non-null in OpenAPI/TypeScript and omitted
on password replay/other errors. No M01 DTO, database, or migration changed.

## Real test inventory and status

| Scenario | Real boundary | Status |
|---|---|---|
| Login, cookies, current session, CSRF, logout, token create/list, one-time replay, bearer scope, OpenAPI matrix | Alembic-migrated file SQLite + production IAM bootstrap/Argon2 + live Uvicorn | Passed in focused tests |
| Foreign Origin on login/initialization even with Bearer; cookie+bearer ambiguity; pure bearer foreign Origin | Same real HTTP/DB | Passed |
| Raw TCP canonical/alias/malformed/duplicate Host; exact 64 vs excess headers, 16 KiB, non-ASCII correlation | Actual Uvicorn TCP parser and ASGI envelope | Passed denial/boundary tests; duplicate Host is a pre-ASGI plain-400 exception |
| 8 KiB body, 32 in-flight request cap, actual ten-second deadline | Actual Uvicorn socket and wall clock | Passed |
| Public M01 repository outage 503; framework 401/404/405 safe problem/private headers; validation key redaction | Real isolated file permissions and real HTTP | Passed |
| P01 `a.b:c` correlation in response and persisted safe IAM audit event | Real HTTP + file SQLite | Passed after M01 `bcce4b2` |
| Generated TS client initialization/login/current/token/list/scope-denial | Node 22 importing generated TS against same real HTTP/DB; password only via stdin pipe | Passed; no browser claim |
| Stale active token/session/target/password `If-Match` => 412 distinct from terminal 409 | Real HTTP + file SQLite | Passed after published M01 token `01fa432` and session `3cd2456` outcome splits |
| Same-key password/token one-time retry with original or wrong-subject ETag => 409 before stale precondition; fresh wrong-subject => 412/no mutation | Real HTTP + file SQLite | Passed after narrow P01 handoff and committed additive M01 rotation port `856f017` |
| Same-origin problem type and authenticated local allowlisted HTML; unknown-code safe 404 | Real HTTP + file SQLite | Passed; not a 14th OpenAPI resource operation |
| Three fixed IAM list sorts, closed filters/singletons, signed query/credential-bound cursor, restart invalidation, optional-versus-null response | Real HTTP + file SQLite + generated OpenAPI/client | Passed in available focused and full non-docs tests; no M01 query expansion |
| P01 §12.9 IAM wire names and `CTR-IAM-004` safe initialization projection | Real Uvicorn/file SQLite + actual generated OpenAPI/client | Focused `6 passed` after three genuine pre-fix failures; independent spec and QA accepted the bounded non-docs slice |
| 15-minute cursor expiry | Separate production Uvicorn + file SQLite with real elapsed clock | **Passed**: explicit 901-second opt-in run returned `1 passed in 902.12s (0:15:02)`; no patched clock or test-only service |
| 30-minute browser-session idle expiry | Separate production Uvicorn + migrated file SQLite, real elapsed wall clock | **Passed**: explicit 1801-second opt-in run returned `1 passed in 1801.99s (0:30:01)`; expired cookie received 401 `dashboard_authentication_required`, with no patched clock or seeded expired row |
| Protected local `/docs`, `/redoc`, and allowlisted assets; Swagger cookie/CSRF and entered-bearer Try-it-out | Real HTTP/local assets and built Chrome over migrated file SQLite/Uvicorn | **Passed** focused HTTP and browser tests; bearer success 200, wrong-scope 403, reload loses bearer, zero external request attempts |
| API policy + API/M1 foundation integration tests with docs transport explicitly deselected | Pure production parser/codec/schema + real HTTP/DB/process + schema generator | Independent QA observed `82 passed, 1 deselected` on frozen final non-docs source; earlier local checkpoint was 79/1 before final wire-name correction. **Not** the all-Story gate. |
| Partial full-backend regression, excluding the blocked documentation transport | All collected backend tests with only `documentation_transports` deselected | Frozen final checkout: `502 passed, 1 deselected in 262.35s (0:04:22)`; earlier checkpoints were 491/1 and 499/1. **Not** a complete Story 4 pass. |
| `AUTO-QUALITY`, `AUTO-BUILD`, and `AUTO-DOCS-CHECK` | Canonical commands | Passed on complete docs checkout: 82 formatted, 78 mypy, zero boundaries, 13 generated operations, exact asset hashes/notices, production build, 204 Markdown |
| `AUTO-TEST` local M1 regression routine | 69 local unittest cases, 324 pytest cases, generated artifact, production build, two real foundation browser cases | Final checkout operational command exit 0; separately reported M0-G1 approval Failed/outside M1, T5/T6/T7/hosted CI Not Run; **not** M2 docs/browser acceptance |
| Full backend, M2 milestone gate | Canonical commands | Final frozen-source backend **Passed**: `505 passed in 272.37s (0:04:32)`; milestone gate outside Story 4/Not Run |
| Naturally occurring unexpected-500 HTTP response | Real HTTP + production handler | **Not Run**; no test-only endpoint, override, seeded corruption, or manufactured OS/DB fault was introduced. Pure mapper and live validation/framework/503 checks cover the bounded Task 4 ID. |
| Provider accounts, macOS, actual owner `.env`, remote mode | External/product layers outside this Story | **Not Run** |

## Genuine Red → Green and regression evidence

Commands below run from the repository root using `backend/.venv/bin/python`.
Failure excerpts are sanitized and no secret is retained. Later acceptance
tests added to already working behavior are explicitly not called prior Reds.

| Increment | Real Red observed before production fix | Green observed |
|---|---|---|
| Initial HTTP route | `pytest -q backend/tests/integration/api/test_iam_http.py::test_login_uses_real_migrated_iam_and_sets_two_cookies` returned 405 instead of login 204. | Same test passed after M2 production route/composition registration. |
| Current session and schema protection | Real-socket tests returned 404 instead of current-session 200 and protected OpenAPI 401. | Focused tests passed after M2 routes/auth. |
| Login Bearer/Origin, media, invalid logout clear | Three live HTTP checks failed respectively 400 vs expected 403, 422 vs 415, and missing clearing cookies. | Focused 6-test suite passed after transport/problem fixes. |
| OpenAPI references/security | Generated schema had 13 operations but missing SafeProblem and security-scheme components. | Live schema and generator reference checks passed after registering components. |
| Generated artifact | Artifact contained zero operations while live M2 route matrix contained 13. | Generator produced 13 exact operations; frontend typecheck passed. M1 compatibility assertion was genuinely Red then its M1-empty/M2-13 split passed (33 M1 integration tests). |
| M01 public outage | Real chmod of isolated SQLite produced unsafe HTTP 500 instead of public 503. | Same real-socket check passed after catching only published `IamRepositoryUnavailableV1`. |
| Initialization Origin with Bearer | Real HTTP returned 200 for foreign supplied Origin instead of 403. | Same focused test passed after pre-auth Origin policy fix. |
| Service lock | Real Uvicorn test found no stable lock file during service lifetime. | Same test passed: owner-only file held exclusively through drain, released afterward. |
| Valid bearer docs auth | Real HTTP `/openapi.json` with valid `write:tokens` bearer returned 403 instead of 200. | Same test passed after documentation authentication no longer assumed `read:self` bearer scope. |
| Complete error media declaration | Live OpenAPI omitted documented 404/405/504 problems. | Same test passed after versioned declaration was expanded. |
| Required header declarations | Live OpenAPI omitted conditional/idempotency header parameters. | Same test passed after exact affected operations declared them. |
| Stale `If-Match` | Real token and active-session HTTP returned 409 rather than frozen 412. After M01 token split, P01 initially mapped the new token code to unsafe 500. | Real token HTTP and active logout/target revoke/password-change HTTP passed after narrow published `precondition_failed`→412 mappings; terminal `credential_state_conflict` remains 409. |
| Protected local docs and real browser | Real HTTP `/docs` returned 404 rather than anonymous 401. First Chrome run failed because byte-identical ReDoc unconditionally attempted `cdn.redoc.ly`; later Chrome run failed at Swagger bearer UI selectors. `AUTO-BUILD` first failed locked-input admission after exact package pinning, then generated artifact drift. | Local authenticated docs/assets HTTP test `1 passed in 1.56s`; hash-checked derived ReDoc local footer asset and passive real Chrome test `1 passed in 7.00s` with zero external attempts; exact lock/asset gate and regenerated 13-operation contract made `AUTO-BUILD` pass. No Playwright interception or secret output. |
| Strict problem CSP on docs/assets | Strengthened real-socket assertion failed: anonymous `/docs` 401 had permissive docs script/style CSP instead of strict `default-src 'none'; frame-ancestors 'none'` (`1 failed in 1.03s`). | Selecting CSP from response problem media before request path gave focused HTTP+Chrome `2 passed in 8.21s`. Successful docs HTML/assets retain docs-only CSP; denied asset 401 and unknown asset 404 are also strict. |
| Safe token replay metadata | Real create/rotate replay tests failed `KeyError: 'committed_resource'` (`2 failed, 1 passed, 33 deselected`). | Narrow typed P01 problem mapping gave `3 passed, 33 deselected in 2.99s`; password replay omits metadata. |
| Optional non-null replay schema | Generated-client and live OpenAPI assertions failed (`2 failed in 1.40s`): TS had `| null` and schema had `anyOf[ref,null]`. | `SkipJsonSchema[None]` plus removal of null default, regenerated client, and same focused real-schema command gave `2 passed in 1.23s`. |
| Password UTF-8 byte cap | Real password-change request with 1024 `é` code points (2048 UTF-8 bytes) returned 401 instead of a pre-M01 422. | Both current/new fields now return safe 422; focused real-socket test passed. |
| Invalid logout with only CSRF cookie | Real HTTP returned 401 but no cookie clear. | Focused real-socket test passed after only presented logout cookies are cleared; failed-login 401 leaves an existing valid session intact. |
| Exact OpenAPI policy oracle | Real M2 schema with a controlled per-operation auth/permission/port/replay/security alteration was accepted (`DID NOT RAISE`). | Independent frozen 13-row matrix rejects more than 60 controlled alterations; focused test passed. |
| Approved Git baseline | Isolated generator initially rejected an uncommitted generated draft source update as `breaking_drift` (after first missing `--write` CLI flag Red). | Real temp Git repo with committed M1 artifact/client: draft can regenerate, committed M2 breaking source change is refused, absent/non-Git HEAD baseline is refused; 10 generator-focused tests passed. |
| One-time password/token replay precedence | Real Uvicorn/file-SQLite focused run returned `412` versus expected `409` for both old-session ETag password retry and wrong-subject rotation retry with the same key (`2 failed, 21 deselected`). | Narrow P01 parse/handoff and additive M01 post-receipt rotation-subject check gave `2 passed, 21 deselected in 2.73s`; fresh wrong-subject/no-receipt remained 412 with no mutation. |
| Resolving problem `type` locally | Real Uvicorn/file-SQLite request emitted `https://agentmonitor.invalid/problems/...` versus expected root-relative `/problems/...` (`1 failed, 23 deselected`). | Closed-code type and authenticated local HTML transport gave `1 passed, 23 deselected in 1.07s`; unknown code is safe 404 with no requested segment reflection. |
| M2 fixed IAM list profile | Real Uvicorn/file-SQLite query with approved `sort=-issued_at` returned 400 instead of 200 (`2 failed, 1 passed, 24 deselected` across new tests). Independently, raw cursor lacked `v1.`, changed-limit cursor reuse returned 200 instead of 400, repeated singleton returned 200 instead of 400, and ordinary SafeProblem serialized `errors: []` instead of omitting it (`4 failed, 26 deselected`). | Fixed parser, per-lifespan CSPRNG HMAC envelope, query/credential binding, and optional serialization pass real HTTP; full non-docs regression `67 passed, 1 deselected in 49.71s`. No M01 list source changed. |
| List authentication precedence | Unauthenticated malformed list query returned 400 instead of generic 401 (`1 failed, 30 deselected`). | Moving authorization before query parsing gave focused `1 passed, 30 deselected`; cursor decoding remains post-auth. |
| Sort-normalization test integrity | First full non-docs run after list implementation had `66 passed, 1 failed, 1 deselected`: test incorrectly compared entire responses, including newly issued cursor expiry bytes that can differ across a second boundary. | The assertion now compares contract observables (stable ordered IDs and `has_more`); focused test passed, then full `67 passed, 1 deselected`. This was a test defect, not a product pass. |
| Pure list/parser/codec/schema policy | `backend/.venv/bin/pytest -q backend/tests/api/test_pagination_policy.py` returned `3 failed, 1 passed`: missing `id_field`/full tie-breaker order caused two `TypeError`s and `SafeProblemV1.detail` was required. | Same direct production-policy command returned `4 passed in 0.25s`; parser now represents the exact closed two-field orders and cursor binding includes them. Pure codec tamper/query binding and unknown/repeated query checks also pass, paired with live-socket tests. |
| Optional non-null problem detail contract | `backend/.venv/bin/pytest -q backend/tests/integration/api/test_iam_http.py -k 'wire_schema_preserves_absent_credentials or canonical_generated_artifacts_publish_m2_iam_operations'` returned `2 failed, 29 deselected`: live OpenAPI and generated TS still required `detail`. | After Pydantic source correction and generator `--write`, focused real-socket/schema/client check returned `4 passed, 27 deselected in 2.85s` (including adjacent list/ordinary-error checks); runtime 401 still emits allowlisted detail, while schema/client mark it optional and non-null. |
| Reopened exact `API-PURE-001/002/006/007/009`, `API-OAPI-001` | `backend/.venv/bin/pytest -q backend/tests/api/test_transport_policy.py backend/tests/integration/api/test_openapi_policy.py --tb=short` returned `5 failed, 1 passed in 0.84s`: production lacked a callable pure correlation validator, strong ETag decoder, unexpected-error mapper; the generator accepted each controlled success-schema drift and structurally invalid `termsOfService=42`. | Pure validator/codec/closed mapper, one frozen 13-row auth/permission/port/replay/security/success/error oracle, and `OpenAPI.model_validate` gave `6 passed in 1.01s`. The final refactor and added per-operation 2xx status/schema and error-schema drift checks returned `3 passed in 1.00s` for the generator policy file; every operation rejects both success-schema and success-status mutation. Paired real Uvicorn/file-SQLite correlation bounds, weak ETag/no mutation, validation redaction, and persisted audit correlation returned `4 passed, 30 deselected in 2.17s`; the first three live regressions already passed before refactor (`3 passed, 31 deselected in 1.78s`). |
| Reopened quality-gate corrections | First `AUTO-QUALITY` run failed one Ruff import-order issue. Next run failed three formatting locations; subsequent run failed six mypy errors in new/changed P01 files. | Each was corrected without outside-module edits; canonical `AUTO-QUALITY` then passed with 80 formatted, 76 mypy-checked, zero boundary violations, and 13 generated operations/client. These intermediate failures were not passing gates. |
| Required SafeProblem error-status oracle | `backend/.venv/bin/pytest -q backend/tests/integration/api/test_openapi_policy.py::test_generator_rejects_missing_safe_error_statuses_on_every_operation --tb=short` returned `1 failed in 0.53s`: deleting all 15 non-2xx responses from current-session GET was accepted. | The same test returned `1 passed in 1.29s` after each operation's single policy row carried the frozen required statuses; it also removes each status individually across all 13 rows. Existing error media/reference checks remain. |
| P01 §12.9 component names and safe initialization fields | Focused three-test command against real schema and Uvicorn returned `3 failed in 1.15s`: four success names, three request names, and actual initialization response did not match the catalog/`CTR-IAM-004`. | P01-only renames and safe field mapping gave `6 passed in 2.21s` for the policy file plus real initialization test. No M01 DTO/port change. |
| Request-schema drift guard | `backend/.venv/bin/pytest -q backend/tests/integration/api/test_openapi_policy.py::test_iam_request_component_names_match_approved_catalog --tb=short` returned `1 failed in 0.52s`: a wrong or invented requestBody was accepted. | The same test passed within the final six-test focused policy/real-init run (`6 passed in 2.30s`); every existing request schema and every no-body operation is checked against the same 13-row generator policy. |

Additional passing regression/acceptance checks (not misrepresented as prior
Reds) include real HTTP exact login cookie attributes (`API-HTTP-002`), natural
five-failure throttle 429/Retry-After/no credential disclosure
(`API-HTTP-004`, `1 passed in 1.36s`), generated-client unauthenticated
401 typed problem/correlation (`API-CLIENT-006` available dashboard half,
`1 passed in 1.02s`), actual raw-TCP Host/header/body limits, 32 concurrent sockets,
ten-second deadline, generated Node client, `a.b:c` audit propagation,
one-time replay, no dead Location, pure bearer Origin independence, app/framework
SafeProblem security headers, and exact 13 operation IDs/security/$refs.

Prior non-docs checkpoint (historical; not a complete Story 4 result):

```text
backend/.venv/bin/python tooling/foundation/openapi_client.py --write
compatible; 13 operations; SHA e89b23b810e408ff9bb9860a08e658f47044a4c55c1ae7ef4949902b62ceda15  [exit 0]
python3 tools/automation/run.py AUTO-QUALITY
PASSED: Ruff/format (80 files), mypy (76), boundaries (0 violations),
generated artifact (13 operations), frontend typecheck/build, locked inputs  [exit 0]
python3 tools/automation/run.py AUTO-DOCS-CHECK
PASSED: 204 Markdown files  [exit 0]
python3 tools/automation/run.py AUTO-TEST
PASSED (operational): 69 unittest OK, 324 pytest passed, 13 generated operations,
production build, 2 real foundation browser tests  [exit 0]
Separate M0-G1 approval: Failed (outside M1); T5/T6/T7/hosted CI: Not Run.
backend/.venv/bin/python -m pytest -q backend/tests/integration/api/cursor_expiry_live.py --tb=short
1 passed in 902.12s (0:15:02)  [exit 0; real elapsed 901-second wait]
backend/.venv/bin/python -m pytest backend/tests -q --tb=short -k 'not documentation_transports'
502 passed, 1 deselected in 262.35s (0:04:22)  [exit 0; frozen final non-docs source]
backend/.venv/bin/pytest -q backend/tests/integration/api/test_openapi_policy.py --tb=short
3 passed in 1.00s  [exit 0; final status-drift assertion]
```

Current docs increment (exact commands from repository root):

```text
backend/.venv/bin/python -m pytest -q backend/tests/integration/api/test_iam_http.py::test_documentation_transports_require_real_auth_and_use_local_assets --tb=short
RED: 1 failed; anonymous /docs returned 404, expected 401 [exit 1]
GREEN: 1 passed in 1.56s, including seven real fetched protected assets [exit 0]
backend/.venv/bin/python -m pytest -q backend/tests/integration/api/test_docs_browser.py --tb=short
RED: failed at redoc_network (cdn.redoc.ly), then bearer authorization UI selector; no pass claimed
GREEN: 1 passed in 7.00s with real Chrome and zero external request attempts [exit 0]
backend/.venv/bin/python -m pytest -q backend/tests/integration/api/test_iam_http.py::test_documentation_transports_require_real_auth_and_use_local_assets backend/tests/integration/api/test_docs_browser.py --tb=short
2 passed in 8.48s after full-header and three-anonymous-page coverage additions [exit 0]
npm ci --prefix frontend --ignore-scripts --no-audit --no-fund
added 31 packages; Scarf analytics disabled before install [exit 0]
python3 tools/automation/docs_assets.py --write
PASSED exact upstream/derived hashes and preserved notices [exit 0]
python3 tools/automation/docs_assets.py --check
PASSED, network-free [exit 0]
backend/.venv/bin/python tooling/foundation/openapi_client.py --write
compatible; 13 operations; SHA 9f2e9d7bcdc4393d116f457de69df06c7b4136d0ceee6d51a3bef4e827eae0e3 [exit 0]
python3 tools/automation/implementations/auto_build.py
PASSED locked inputs, docs-assets check, generated client, typecheck, production build [exit 0]
python3 tools/automation/run.py AUTO-QUALITY
PASSED 82 formatted, 78 mypy, 0 boundaries, 13 operations/client [exit 0]
python3 tools/automation/run.py AUTO-DOCS-CHECK
PASSED 204 Markdown files [exit 0]
backend/.venv/bin/python -m pytest backend/tests -q --tb=short
505 passed in 272.37s (0:04:32) on frozen source [exit 0]
python3 tools/automation/run.py AUTO-TEST
PASSED operational: 69 unittest, 324 pytest, 13 generated operations,
production build, 2 real foundation Chrome tests [exit 0]; M0-G1 separate
approval Failed/outside this Story; platform/provider/native/hosted CI Not Run
backend/.venv/bin/python -m pytest -q backend/tests/integration/api/session_expiry_live.py --tb=short
1 passed in 1801.99s (0:30:01) [exit 0; real elapsed 1801-second wait]
```

The final frozen-source full backend run passed: `505 passed in 272.37s
(0:04:32)` from `backend/.venv/bin/python -m pytest backend/tests -q
--tb=short`. Earlier full `505 passed in 273.39s` began before the optional
replay-schema correction and is historical only.
An independent spec review also observed one intermittent real-Chrome failure
at the bearer token-list DOM-status wait; the test now passively awaits the
actual GET response before asserting 200, with three consecutive Chrome runs
passing (7.33s, 7.42s, 7.43s). The failure is retained as a test-integrity
finding, not silently erased. The separate real 1801-second idle-expiry test
passed as recorded above. Provider re-authentication is M2-deferred/Not Run,
not inferred from dashboard 401 client coverage. Final results must be
recorded before Story 4 acceptance. The generator's `--write` baseline is the approved
`HEAD` artifact, not an uncommitted draft; `--check` compares current worktree
artifacts byte-for-byte. No new resource operation was created. P01's plan
listed an `api/security_headers.py` file; the implementation deliberately
keeps those headers in `api/transport.py`, the single ASGI envelope owner, so
there is no parallel header middleware or missing security behavior.

## Security, dependency, operations, and review

Test setup uses real Alembic migration, isolated file SQLite, OS-random
ephemeral owner credentials, production Argon2, and real Uvicorn. There are no
mocks, fakes, stubs, emulators, recorded responses, seeded telemetry, patched
clock, test-only production branch, or hardcoded passing assertion. Tests do
not read `.env`, provider profiles, process environment content, prompts,
responses, source content, or external accounts. The generated-client password
travels only through a private stdin pipe and is never logged/printed.

No migration was added. The owner approved exact local Swagger/ReDoc assets;
the two pinned Swagger package entries and Scarf opt-out were installed with
scripts disabled. Only reviewed files/notices and the root-approved single-URL
derived ReDoc bundle plus pinned same-origin SVG are vendored. Browser
Try-it-out and ReDoc passed; macOS, owner-live use, release SBOM/publication,
and hosted CI remain **Not Run**. The service lock is a consumed protocol for the
separately owned local forgotten-password command, which remains Not Run here.
Three exact upstream notice files retain their hash-checked whitespace; scoped
`.gitattributes` entries keep the staged whitespace gate active for authored files.

Independent specification and QA reviewers accepted the final Story 4 source,
contracts, real-browser evidence, and real 1801-second idle-expiry result. Root
acceptance is limited to Story 4; Story 5, Story 6, and the M2 milestone gate
remain separate and unstarted.
