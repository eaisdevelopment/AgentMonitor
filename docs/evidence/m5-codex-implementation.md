# Test evidence: V1-M5 Codex implementation

- Evidence ID: `M5-CDX-IMPLEMENTATION-2026-10-08`
- Module/plan/increment: A02 Codex provider adapter, root-owned V1-M5
  integration, and managed-profile effective-containment correction under
  approved focused plan versions `1.10.0` through `1.15.0`, Stories
  `ST-CDX-001..005`.
- Requirements/acceptance IDs:
  `FR-ACC-001/004..006`, `FR-AUTH-001/002/004..006`,
  `FR-QUOTA-001..006`, `FR-COL-003..008`, `FR-HIST-001/002`,
  `FR-DISC-001/003/004/006/008`, `FR-STATE-001/002`, `FR-SAFE-002`,
  `FR-ALERT-002..006`, `FR-UI-001..006`, `FR-IAM-001/003`,
  `UI-RESP-006`, `UI-AUTH-008/009`, `NFR-API-001/002`,
  `NFR-TEST-001/002`, `NFR-SEC-001`, `NFR-PRIV-001/002`,
  `NFR-RES-001`, `NFR-OBS-001`, `NFR-COMP-001`, `NFR-DOC-001`;
  M5 contributions to `AC-LIVE-002/004/005/007`, `AC-UI-001..006`,
  `AC-V1-005/007`,
  `AC-PROC-001..004`, `AC-HIST-001`, `AC-ALERT-002`,
  `AC-OPS-003/006`, and `AC-TEST-001..006`.
- Contract versions: compatible V1 use of `CTR-PROV-001..008`,
  `CTR-REG-001/002/004/005/006/009/010`,
  `CTR-COL-002/004/006/007`, `CTR-CAP-001/003/004/007/008/009`,
  `CTR-RUN-001/002/003/006/007`, `CTR-PLAT-001`,
  `CTR-OPS-004/006`, `CTR-ALERT-001..005`, `CTR-EVT-001`,
  `CTR-API-001/002`, `CTR-IAM-003/004/005`, and `CTR-UI-001`;
  `ProviderAdapterV1`
  `1.0.0-draft.2`; `codex-adapter.v1` adapter `1.0.2`; Codex
  subscription capability schema `1.0`; REST `/api/v1`; database head
  `v1_0707` unchanged.
- Commit/worktree reference: approved plan 1.15 implementation commit
  `8cc683d946b58f5eb72955e08a520195582e1a28` passed the complete
  preactivation set and zero-skip authenticated Codex `0.160.0` containment
  rerun. Its two-stage fifth corrective activation passed and made that clean
  detached revision the receipt-bound live service. No clean revision has yet
  passed the canonical M5 completion gate.
- Recorder/date: Codex integration record, 2026-10-08; retained-history retry
  update, 2026-10-09; exact-revision transition and concurrency update,
  2026-10-16; alert browser-proof termination and P02 canonical-browser
  updates, 2026-10-20; quota projection, fifth-rollover, and effective-
  containment updates, 2026-10-21; descriptor metadata, mount topology,
  descriptor-bound truncation, numeric-dirfd trace representation, process
  cleanup, Arg0 alias and lock-child lifecycles, and authenticated Arg0
  follow-up updates, 2026-10-22; exact 1.15 preactivation, activation, fresh
  owner/alert prerequisites, and alert-witness failure update, 2026-10-23.
- Overall status: **Intermediate**. Clean revision `8cc683d` passed the full
  preactivation set, including `104` automation tests, two Argon2 tests,
  `1361` backend passes with only `37` gate-declared skips, the browser suites,
  and every required canonical preactivation routine. The standalone
  authenticated containment rerun then passed `1 passed in 4.03s` with zero
  skips against pinned Codex `0.160.0`. The two-stage fifth activation passed
  with real service, HTTP, authenticated browser, Registry, database,
  rollback, and receipt proof.

  Fresh revision/service-bound owner outcomes then passed with four total
  records: three verified and one owner-unavailable. A genuine
  post-confirmation Codex alert opening, distinct repeat, owner
  acknowledgement, and recovery also passed. `AUTO-M5-ALERT-WITNESS` created
  no witness. Its first read-only run exposed a quadratic complete-outbox
  acknowledgement lookup over more than `36,000` real capacity events. The
  unchanged canonical rerun completed the database proof, then failed closed
  as `selected_alert_history_not_rendered`, surfaced as
  `m5_alert_witness_browser_unavailable`: the versioned API returned all `192`
  selected-alert history entries while the built Alerts page rendered `100`.

  Owner-approved plan 1.16.0 is limited to a bounded
  exact-ID acknowledged-event query, complete cursor-paginated Alerts history
  and browser proof, and one exact sixth evidence-preserving rollover from
  `8cc683d`. No current alert witness, quota witness, or M5 completion receipt
  exists. `AUTO-M5-QUOTA-WITNESS`, `AUTO-M5-EXIT`, and final owner acceptance
  are **Not Run**. This record is not milestone acceptance.

The primary production owner is A02 for provider behavior under
`backend/src/agentmonitor/adapters/providers/codex/**`. Root integration owns
composition, Registry/Collection/Capacity/Runtime/Alerting coordination, API,
UI, automation, and live closure. P02 owns the React shell, styles, and browser
runner correction. The current approved scope is plan `1.16.0`; its
[V1-M5 Codex slice](../plans/integration/m5-codex-slice-change.md) retains all
earlier corrections and the completed fifth rollover. The owner's explicit
2026-10-23 approval adds only the enumerated bounded 1.16 correction.

## Contract-impact assessment

- Codex installation, identity, authentication health, managed connection,
  subscription quota, and process observation remain behind the provider and
  platform adapter contracts. Provider-specific response shapes do not enter
  domain modules.
- The shared provider-operation deadline ceiling is relaxed from 300,000 to
  600,000 milliseconds so the declared `codex login` operation matches the
  approved ten-minute owner interaction. Existing values keep their meaning;
  values above 600,000 remain invalid. The generated capability-manifest
  schema and consumers were regenerated. This is a compatible V1 validation
  widening, so no major-version migration or ADR is required.
- The Codex adapter is `1.0.2` and its parser is `1.0.1`. Its exact `0.160.0` identity,
  authentication-health, and quota sources are classified
  `managed_profile_write`, because the provider can perform automatic
  credential refresh and runtime maintenance inside the selected managed
  profile. Installation discovery remains read-only. Mapping ID
  `M5-CDX-0-160-0-002` is unchanged; its canonical evidence digest rotated to
  `417c46ba301f9c4217c606beed52be93c9bf497da9ca5b99ca4b1993167688d3`
  because the canonical mapping artifact now binds the corrected authenticated
  identity semantics as well as the corrected read-side effects.
- Operations V1 gains the optional `source_revision` inventory field. An
  unavailable clean startup revision remains explicit rather than inferred.
- Registry, Collection, Capacity, Runtime, Alerting, event, API, and UI shapes
  are reused compatibly. Account and alert traversal now consumes complete
  cursor-paginated Registry views. The M5 quota and completion witnesses also
  consume every page in their fixed 30-day capacity-history query, so retained
  observations beyond the first 200 cannot hide the current lineage. No API
  contract or response shape changed.
- The M5 alert-witness selector now binds the latest complete alert occurrence.
  A never-before-seen fingerprint begins with `opened`; a recovered retained
  fingerprint begins its next occurrence with the existing provider-neutral
  `reopened` transition. Earlier occurrences remain in immutable history and
  cannot satisfy the fresh service-bound witness. The private
  `agentmonitor.m5-alert-witness.v2` schema remains unchanged: `opened_at` and
  the opening proof bind the selected occurrence start. No public API, event,
  database, or persistence schema changed, so no migration, contract-version
  change, or ADR is required.
- `CTR-CAP-001` capacity provenance now admits `+` in its existing bounded
  token grammar so an admitted SemVer mechanism version can retain build
  metadata such as a schema digest. This is a compatible character-set
  widening: existing values keep their meaning, and the contract major,
  REST/OpenAPI schemas, persistence schema, and consumers remain unchanged.
- The Codex collection action policy now treats exactly the bounded local
  `collection_commit_interrupted` outcome as transient. Recovery permits a
  distinct durable run only after the full configured quota cadence; it does
  not perform an immediate retry or reclassify other internal failures. No
  collection, capacity, API, event, or persistence contract changes.
- Live current-projection evidence exposed a missing implementation of the
  existing `FR-QUOTA-001` / `M05-PURE-005` complete-scope window lifecycle
  rule. The approved and locally implemented correction reuses the existing
  `complete_scope`/`partial_scope` and
  `active`/`not_observed_currently` meanings. It passed the 71-test Capacity
  suite without a public contract or schema change. The existing definition
  `last_observed_at` field carries the latest accepted presence or
  complete-scope absence lifecycle observation time across definition versions;
  immutable quota observations remain presence-only history. Pure tests cover
  strict ordering, repeated newer absence, stale and newer reappearance,
  retired no-op, out-of-order semantic changes, and exact scope isolation. A
  fresh live collection against the corrected service subsequently passed.
- That corrected-service regression exposed a test-only verification defect:
  current windows already bound only the newest run, but the history assertion
  searched only the first 200 rows of the existing ascending cursor-paginated
  30-day query. The approved 1.6.0 test follows the unchanged public ordering
  through at most 128 pages, requires progressing unique cursors, a null
  terminal cursor, and unique observation IDs, and retains an explicit prior-run
  history assertion. It changes no production module, contract, API, schema,
  migration, provider operation, dependency, generated client, or ADR.
- Plan 1.8.0 changes only P02 shell/style behavior and its browser runner. The
  mobile header reflow, closed revocation oracle, password lifecycle and
  generation fence consume existing `CTR-API-002`, `CTR-IAM-003/004/005`, and
  `CTR-UI-001` V1 behavior. The runner retains the existing direct child
  invocation and changes only bounded repetition and closed output handling;
  it adds no service or process-management mechanism. No API, OpenAPI,
  generated client, backend, database, provider adapter, configuration,
  dependency, license, migration, or ADR contract changed.
- Plan 1.9.0 changes only the private quota-witness record projection and the
  revision-pinned fifth service-rollover policy. It retains the browser/history
  digest input and every existing quota acceptance rule. No public contract,
  API, OpenAPI, generated client, UI, database, migration, provider adapter,
  configuration, dependency, license, or ADR changed.
- Plan 1.10.0 changes only the private M5 containment verifier. Four exact
  owner-owned `0700` enclosing roots are pinned and revalidated; ordinary modes
  on nested provider-created files and directories are retained in the evidence
  digest while links, nonregular objects, foreign owner/device entries, regular-
  file hard links, special bits, unsearchable directories, traversal errors,
  and bounded-count/path violations still fail closed. The separate private
  `auth.json` metadata rule, syscall tracing, default-profile exclusion, write
  confinement, receipt schema, and public behavior remain unchanged. No public
  contract, API, UI, database, migration, provider adapter, configuration,
  dependency, license, or ADR changed.
- Approved plans 1.11.0 through 1.15.0 change only private
  containment-verifier policy and diagnostics. They add inode-bound
  `chmod(..., 0700)` proof, complete descriptor metadata tracing, strict mount
  topology and traced-process identity proof, descriptor-bound `ftruncate`
  classification, pidfd-owned process-group cleanup, and the exact temporary
  Arg0 session, regular `.lock` child, four-alias creation, and five-child
  cleanup lifecycle. The earlier narrow follow-up correction accepts only a
  same-operation descendant's failed `mkdir` with exact `EEXIST` during that
  lifecycle; a failed `rename` remains rejected because a reported failure
  does not prove absence of a filesystem effect. The 1.15 feedback correction
  leaves official pre-session Arg0-root setup under ordinary confinement and
  starts both broad lifecycle guards only at exact session-`mkdir` invocation.
  These changes affect no public contract, API, UI, database, migration,
  dependency, license, or provider operation.
- No database table or migration was added. Real tests migrate fresh
  file-backed SQLite databases through the existing `v1_0707` head.
- No production or development dependency was added.
- The approved M5 plan 1.4.0 and PLAN-DEP/D01 Draft now record one explicit
  owner-authorized exception for `AUTO-M5-SERVICE-ACTIVATE`. The exception
  changes no public contract: `CTR-DEP-001` remains proposed and solely
  PLAN-DEP-owned, `AUTO-DEPLOY` remains Blocked, and broader native deployment
  implementation remains unauthorized.

## Test inventory and status

Statuses apply only to the cited development worktree run. They do not replace
the clean-revision milestone gate.

| Test/scenario ID | Layer | Real dependencies | Status | Evidence reference | Notes |
|---|---|---|---|---|---|
| `M5-CDX-SOURCE` empty-root safety correction | Provider/filesystem/subprocess | Exact installed Codex `0.160.0`, real private managed root | Passed | [read-side-effect correction](m5-codex-read-side-effect-blocker.md) | This focused correction passed: real Red observed provider writes; Green rejects an uninitialized managed root before provider startup. The remaining source scenarios and authenticated behavior remain separate below. |
| `CTR-CAP-001` SemVer build-metadata provenance | Pure capacity contract | Production `CapacityObservationProvenanceViewV1` with an admitted Codex mechanism-version shape | Passed | Focused Red plus complete `test_quantity_and_health.py` Green below | The compatible grammar correction passed its pure contract suite. The authenticated live commit that exposed it must still be retried and is not credited as a quota pass. |
| `M5-CDX-COL-004` interrupted local commit recovery | Pure composition policy | Production Codex collection action policy | Passed | Focused Red and combined collection-policy/Capacity Green below | Exactly `collection_commit_interrupted` becomes eligible for a distinct durable run after the full cadence. No live retry is credited. |
| `CTR-PROV-002/004`, Codex managed-login deadline | Pure contract/generated schema | Production contract and generated provider schema | Passed | Four focused tests, broader provider suite, mutation suite, schema check | Ten minutes accepted; 600,001 ms rejected. |
| `M5-CDX-COL-013` shutdown drain | Real application lifecycle/process | Production application lifecycle and a real owned child | Passed | Focused shutdown and lifecycle runs | Service drain is 45 seconds, strictly above the 30-second operation plus four-second owned-child cleanup bound. |
| Owner, quota, alert, and receipt prerequisite policies | Real filesystem plus pure closed-schema policy | Real files, modes, hard links, symlinks, inode substitution, kernel process behavior | Passed | Focused automation results below | These are prerequisite-policy Greens, not owner-authenticated live receipts. |
| `M5-CDX-GATE-001` admission/containment policy | Linux/platform/provider | Real installed executable and schema; real OS pipes, file descriptors, `/proc`, mount namespaces, and process tracing | Intermediate; plan 1.15 working implementation Green | Complete containment file: `97` passed and one authenticated live-selector skip across `558` subtests; current-exit: `66/66` | The exact session, `.lock`, four-alias, and five-child cleanup lifecycle passes locally. The two broad guards now cover exact session-`mkdir` invocation through final cleanup completion, while valid official pre-session root setup remains ordinarily confined. The skipped authenticated case is not counted as Passed. |
| `M5-CDX-UI` account beyond first page | DB/API/browser | Real migrated file SQLite, production HTTP/API, generated client path, production frontend, Chrome | Passed | `account_beyond_page` browser scenario | This focused UI behavior passed: it creates 201 real account records, uses the visible **Load more accounts** control, and opens the last account through a generated detail GET. Other UI scenarios remain subject to the canonical gate. |
| `M5-CDX-UI` mixed-provider Overview filter | API/built browser | Authenticated real owner service, genuine Claude and Codex Registry rows, production frontend, shared Chrome | Passed for the focused increment | `AUTO-DASHBOARD-PROVIDER-FILTER` and [Overview evidence](dashboard-density-and-quota-overview.md#mixed-provider-selection--2026-10-11) | Claude-only, Codex-only, all-provider reset, organization composition, keyboard use, manual/periodic refresh retention, 1920/1280/390 reflow, filtered counts, and zero mutations passed. This does not close the canonical M5 gate. |
| `UI-RESP-006` contained mobile header | DB/API/built browser | Thirty fresh migrated SQLite databases, production HTTP and frontend, installed Chrome at 390 by 844 | Passed for the focused correction | `run_browser.py responsive --repeat 30 --no-build`: 30/30 first-attempt passes | Both header controls remained inside the viewport and keyboard reachable, with navigation-only internal scroll and no document overflow. |
| `UI-AUTH-008` revoked secondary session | IAM/API/built browser | Thirty isolated real servers, databases, and two-context Chrome sessions | Passed for the focused correction | `run_browser.py revocation --repeat 30 --no-build`: 30/30 first-attempt passes | Only visible automatic Sign in or one Check session followed by Sign in was accepted; protected navigation remained absent after reload and the primary session stayed active. |
| `UI-AUTH-009` exclusive password lifecycle | IAM/API/built browser | Thirty isolated production password mutations over real HTTP, SQLite, session cookies, CSRF and Chrome | Passed for the focused correction | `run_browser.py password_change --repeat 30 --no-build`: 30/30 first-attempt passes | Cleanup acknowledgement preceded form use; controls stayed inert; one preflight, one PATCH and one reconciliation GET were observed; success, route, focus and rotated credentials remained coherent without late expiry. |
| P02 bounded repeat/output policy | Pure policy | Constructed closed strings and return codes only; no I/O behavior | Passed for the focused correction | `test_run_browser_policy.py`: 65 passed; final blobs `8afd41102d0168ac4a0a5934a591ede69804cc60` and `96083d23627c015a26bbfd154bb7ca37e5de5496` | Counts outside 1..30, raw or conflicting output, spawn/timeout/encoding failures, and process-level exit 2, 127 or -9 reduce to `browser_output_invalid`; one allowlisted failure line is admitted only at exact script exit 1. |
| Complete P02 follow-up lanes | DB/API/built browser/security | Fresh real stack, production build and installed Chrome | Passed for the focused correction | `run_browser.py all --no-build`, `security_boundary --no-build`, and `hostile_resource --no-build` passed | The complete lane and both separately named security/resource scenarios passed after the 30-run proofs. Focused M5 automation passed 55 tests, M5 UI policy passed 16 tests, and independent reviews were CLEAN. |
| `M5-CDX-ALERT-001` complete Registry scope | Pure policy and DB integration | Real migrated file SQLite, production Registry commands, exact Codex installation reconciliation, 201 accounts | Passed | Three focused tests; full file `8 passed, 3 skipped` | Cursor progress and duplicate IDs fail closed; the target after page 200 resolves. Three owner-live selectors remain skipped. |
| `M5-CDX-ALERT-002` retained-history occurrence selection | Pure alert-witness policy | Production selector with constructed closed lifecycle values and no I/O | Passed | Meaningful Red and focused Green below | The latest `opened` or `reopened` occurrence must contain a distinct repeat, exactly one owner action, and exactly one later recovery. The combined focused run returned `19 passed, 3 skipped`; the owner-live skips are not credited as passes. |
| M5 Node story inventory | Pure UI/gate policy and source wiring | Production policy modules and browser entrypoint sources | Passed | `19 passed`, zero skipped | Includes configurable capacity-alert presentation and the alert and quota browser verifiers' use of shared complete page readers. This is a development-checkout result, not a live browser witness. |
| `AUTO-M3-TEST` dependency checkpoint | M3 contract and technical backend suites | Canonical routine on the development checkout | Passed | Two routine tests and `307` technical tests passed, zero skipped | Satisfies the local M3 dependency checkpoint; it does not establish an exact clean M5 revision. |
| `AUTO-MUTATION` checkpoint | Critical pure-policy mutation | Canonical routine on the development checkout | Passed | `1708` mutants: `1698` killed, `10` independently accepted equivalent, `0` skipped | No non-equivalent survivor was admitted. This remains subject to the final clean-revision M5 gate. |
| Quality, build, planning, documentation, and Git checkpoints | Static quality, generated artifacts/frontend build, repository validation, and local Git preflight | Canonical local routines on the exact candidate | Passed on clean `8cc683d` | Planning, documentation, build, quality, mutation, M3 regression, full local test, and Git preflight all passed on the exact clean candidate; focused independent reviews were CLEAN. | Exact-revision `AUTO-M5-EXIT` remains Not Run. |
| Full M5 Python story selection before live setup | Backend and automation Story scope | Real local boundaries plus explicit owner/provider selectors | Inventory rebound; zero-skip Story run pending | The exact inventory is `547` unique test identifiers with digest `3a97e0103ae4ba3390d10567c9130821abaa7a5a7e9640cf0091bc56a49b6a0c`. | Collection proves scope only. The complete selected suite with live selectors and zero skips remains Not Run. |
| Canonical local regression checkpoint | Backend, API, browser, process and generated-client boundaries selected by `AUTO-TEST` | Real local processes, migrated SQLite, production HTTP, built frontend and installed Chrome | Passed operationally on final attempt | Final `AUTO-TEST`: 104 command tests; 2 Argon2 tests; backend `1361 passed, 37 skipped, 1 warning`; OpenAPI compatible with 67 operations; production build; 2 foundation browser tests; complete P02, security and hostile-resource lanes | Attempt 1 retained the real loaded Argon2 failure. Attempt 2 passed all 1361 backend tests but failed revocation as `browser_output_invalid` because an out-of-scope systemd wrapper could not access the user bus in the gate's PATH/PYTHONPATH-only environment. The approved direct-child runner was restored and the complete final attempt passed. Skipped owner/live selectors remain non-passing outside this local routine's declared scope. |
| `AC-LIVE-002/004` four selected Codex outcomes and live identities | Provider/account | Four real owner-selected Codex accounts or explicit owner-unavailable outcomes | Passed for the current `8cc683d` prerequisite | `AUTO-M5-OWNER-OUTCOMES` passed with four outcomes: three verified and one owner-unavailable. | This sanitized availability result contains no quota or acceptance claim and becomes stale after any sixth rollover. |
| `AC-LIVE-005`, `M5-CDX-COL/CAP` authoritative quota/history | Provider/DB/API/browser | Official Codex `/status`, fresh scheduled observations, current and retained history | Current witness Not Run | The earlier d81 witness failure and its projection correction remain historical Green evidence. No revision-bound `8cc683d` quota witness was created. | Fresh authoritative `/status`, collection, API/DOM, and retained-history reconciliation remains required after the proposed sixth rollover. |
| `AC-PROC-001..004`, `M5-CDX-RUN-001..008` representative processes | Linux/platform/browser | Five to six real Codex processes outside the managed-profile subtree | Historical availability; current canonical witness unrecorded | Six exact-version baseline Codex processes were alive during earlier d81 live work. | Current PID/start/executable reread, hierarchy/location, managed-child exclusion, and unresolved or owner-confirmed association remain required. |
| `AC-ALERT-002`, `M5-CDX-ALERT-001..007` live lifecycle | DB/API/browser/provider | Genuine Codex capacity condition, fresh opening, repeated delivery, owner action, later source-proven recovery | Lifecycle Passed; canonical witness Failed | A current `8cc683d` opening, repeat, owner acknowledgement, and recovery passed. `AUTO-M5-ALERT-WITNESS` created no file: the first run exposed quadratic source-event proof and the unchanged rerun failed as `selected_alert_history_not_rendered`, surfaced as `m5_alert_witness_browser_unavailable`, with API `192` versus DOM `100`. | Approved 1.16 corrects only the targeted lookup and complete UI history pagination; a fresh witness remains required after activation. |
| Authenticated managed-profile syscall containment | Linux/provider/security | Real authenticated managed Codex profile and `strace` | Passed on exact clean revision | After complete preactivation, the standalone rerun against exact `8cc683d` and pinned Codex `0.160.0` returned `1 passed in 4.03s` with zero skips. | This is required live evidence but does not replace `AUTO-M5-EXIT`. |
| `M5-SVC-ACT-001..012`, `AUTO-M5-SERVICE-ACTIVATE` | Operations/service transition | Real user systemd manager, trusted persistent runtime, clean stable Git worktree, real HTTP and authenticated browser | First five corrective rollover/activations Passed | The fifth two-invocation transition preserved the prior archive chain and activated exact `8cc683d` with service, browser, Registry, database, rollback, and receipt proof. | Owner-approved 1.16 authorizes exactly one sixth transition; no seventh rollover is approved. |
| `M5-CDX-GATE-001..014`, canonical `AUTO-M5-EXIT` | Full local/live gate | Clean exact revision, selected running service, prerequisite receipts, all local gates with zero skips | Not Run | Exact `8cc683d` preactivation, authenticated containment, fifth activation, owner outcomes, and alert lifecycle passed, but no alert witness, quota witness, or final receipt exists. | Must pass every remaining lane before M5 completion can be claimed. |
| macOS compatibility | Platform | Real macOS host | Blocked | No real Mac available | Outside Linux-first M5 acceptance; remains visible for V1. |

## Red evidence

No timestamp was retained for the recovered development runs below. Their
commands, failure outputs, and worktree context are preserved where available;
no time is inferred.

### P02 canonical-browser Reds under plan 1.8.0

The required plan 1.7.0 browser lane exposed three real P02 failures. At the
390 by 844 viewport, both `documentElement.clientWidth` and
`window.innerWidth` were 390 while `documentElement.scrollWidth` and the right
edge of the visible header actions were 392. In the real two-session revocation
scenario, an already-running protected request could receive 401 and reach the
secure **Sign in** state before the unconditional **Check session** click, so
the test timed out after the valid control had disappeared. In repeated real
password-change runs, PATCH returned 204 and the single renewed-session GET
returned 200 within one second, yet a previous-cookie Overview expiry callback
left `/login` paired with the protected shell and removed the success state for
the full 120-second observation.

### Canonical local gate and runner-scope Reds

The first complete plan 1.8.0 `AUTO-TEST` attempt reached the real Argon2
performance check and Failed with elapsed p95 `0.27936251898063347` seconds at
the `0.25`-second ceiling. The observed workstation load average was `32.08`
while another project's Vitest and `vue-tsc` workers were active. This was kept
as a real Failed result rather than reclassified; a later low-contention focused
Argon2 run returned `2 passed`.

The second complete attempt passed all 1361 backend tests, then the P02
revocation scenario returned only `browser_output_invalid`. Investigation found
that a proposed systemd containment wrapper, which was outside plan 1.8.0's
approved repeat-and-closed-grammar boundary, could not reach the user bus in
`AUTO-TEST`'s intentionally narrow PATH/PYTHONPATH-only environment. The
failure remained Failed and triggered a scope audit instead of an environment
exception or a widened gate.

The audit restored the approved existing direct child invocation. It also found
that the proposed closed grammar could accept an allowlisted script failure
line with process-level return codes 2, 127, and -9. Three pure policy cases
went Red. The minimal Green requires exact return code 1 for an allowlisted
failure line; every other nonzero return code produces only
`browser_output_invalid`.

### Authenticated identity was confused with provider authentication policy

After the owner completed the official browser login in an isolated
AgentMonitor-managed profile, a bounded `account/read` structural check
reported a ChatGPT account, a valid workspace account identifier, and
`requiresOpenaiAuth=true`. The former parser treated that boolean as current
login state, rejected the authenticated response with
`CodexIdentityFailure`, and the dashboard truthfully ended the connection as
`connection_failed`.

The exact OpenAI Codex `rust-v0.160.0` source establishes that
`requiresOpenaiAuth` comes from the active model provider while account
presence independently determines login state. The regression test changed
first:

```bash
PYTHONPATH=backend/src backend/.venv/bin/pytest -q \
  backend/tests/adapters/providers/codex/test_identity_parser.py::test_chatgpt_identity_is_allowlisted_and_fingerprinted
```

It failed with the expected `codex_identity_invalid` exception (`1 failed in
0.09s`). No raw provider response, identity value, credential, URL, prompt,
response, source content, or arbitrary environment value was retained.

The canonical mapping artifact was then extended with the corrected identity
semantics before its admission digest was rotated. The exact real-installation
admission test failed closed against the prior digest:

```bash
PYTHONPATH=backend/src backend/.venv/bin/pytest -q \
  tools/automation/test_m5_codex_admission.py::M5CodexAdmissionTests::test_real_installed_codex_matches_exact_discovery_and_mapping_evidence
```

It reported `m5_codex_mapping_evidence_invalid` (`1 failed in 0.04s`).

### Capacity provenance rejected admitted SemVer build metadata

A real authenticated Codex quota operation completed its provider read and
normalized one primary window. The subsequent Capacity commit failed closed in
`CapacityObservationProvenanceViewV1` with
`capacity_provenance_invalid`. The admitted mechanism version has the form
`codex-app-server-v2@0.160.0+schema.<digest>`, while the Capacity token grammar
did not admit the SemVer `+` build-metadata separator.

The pure contract regression test was added first:

```bash
PYTHONPATH=backend/src backend/.venv/bin/pytest -q \
  backend/tests/capacity/test_quantity_and_health.py::test_provenance_accepts_semver_build_metadata_in_mechanism_version
```

It failed for the expected bounded rejection (`1 failed in 0.29s`). This live
observation proves the provider read and normalization reached one primary
window; it does not prove a successful Capacity commit, persisted quota,
history, API value, or dashboard value. No raw provider data, credential,
identity, or private provider response was retained.

### Recovered commit interruption permanently blocked later collection

After the failed local Capacity commit was recovered as
`collection_commit_interrupted`, the Codex action policy classified that code
as an internal permanent failure. The account could therefore remain
ineligible for every later scheduled collection even after the full quota
cadence elapsed.

The focused regression test was added first:

```bash
PYTHONPATH=backend/src backend/.venv/bin/pytest -q \
  backend/tests/adapters/providers/codex/unit/test_collection_action_policy.py::test_interrupted_local_commit_allows_a_new_run_after_full_cadence
```

It failed for the expected permanent classification (`1 failed in 0.51s`).
The test is a closed pure policy check; it does not claim a provider call,
durable run, Capacity commit, or quota result.

### Managed-root side effects were classified incorrectly

Command:

```bash
PYTHONPATH=backend/src backend/.venv/bin/python -m pytest -q \
  backend/tests/adapters/providers/codex/live/test_managed_identity.py
```

The real exact-version app server was invoked against an empty selected
managed root. A first run created 18 descendants and a repeat created 94. This
disproved both the former read-only declaration and an unchanged-empty-root
expectation. A matching source review established that installation identity
and proactive authentication maintenance can write. No file content, provider
response, identity, credential, or private path was retained.

### Account UI stopped at the first 200 records

Command:

```bash
backend/.venv/bin/python frontend/tests/browser/p02/run_browser.py account_beyond_page
```

The production browser scenario timed out waiting for the visible
`Load more accounts` control. The Red used a real migrated file SQLite
database, production loopback service, production frontend, Chrome, and 201
records created through the authenticated API.

### Alert delivery could not resolve a subject after page 200

Command:

```bash
backend/.venv/bin/pytest -c backend/pyproject.toml --rootdir=. -q \
  --tb=short --import-mode=importlib \
  backend/tests/integration/alerting/test_codex_capacity_lifecycle.py::test_alert_delivery_resolves_event_subject_after_first_200_real_accounts
```

Result:

```text
AttributeError: 'CapacityAlertDeliveryV1' object has no attribute '_account_for_subject'
1 failed in 4.80s
```

The test used a newly migrated real SQLite file, 201 accounts created through
production Registry commands, real exact-installed-Codex installation
reconciliation, production identity confirmation/enrollment, and a generated
Registry resource placed beyond the first page. The cursor and duplicate-ID
tests separately failed to import their absent policy helpers.

A post-review extension resolved the target once, archived that account through
the production Registry, and then required the same resource subject to become
unresolved. Before the lifecycle filter was added, the real test reported:

```text
DID NOT RAISE capacity_alert_subject_unresolved
1 failed in 5.70s
```

This showed that complete pagination alone could still associate an archived
account or inactive resource.

### The provider contract could not declare the approved login duration

Four focused tests changed first: the provider-protocol ten-minute bound, the
generated manifest-schema maximum, the Codex reauthentication declaration,
and its critical manifest tuple. Before production changes they returned:

```text
4 failed in 0.25s
```

The former 300,000 ms maximum could not represent the approved 600,000 ms
owner login deadline.

### Service shutdown was narrower than one bounded Codex operation

Command:

```bash
backend/.venv/bin/python -m pytest -q -c backend/pyproject.toml \
  --rootdir=. --import-mode=importlib \
  backend/tests/integration/api/test_codex_dashboard_composition.py::test_codex_service_shutdown_deadline_covers_provider_operation_and_cleanup
```

Result:

```text
assert 30 > 34
1 failed in 1.47s
```

This exposed a real lifecycle contract mismatch: a 30-second provider
operation plus two bounded owned-child cleanup waits could outlive the former
30-second application drain.

### Completion automation failed closed during implementation

The following Reds were retained from the recovered session:

- The first receipt test failed with
  `TypeError: build_passed_receipt_v1() got unexpected keyword containment_evidence_digest`
  before containment evidence entered the closed receipt schema.
- Expiry and complete-pagination changes produced six focused failures, and
  the browser verifier initially failed because its shared Registry-page
  helper module did not exist.
- `AUTO-QUALITY` rejected runtime `monkeypatch` use in the new witness tests.
  The tests were rewritten to exercise real filesystem and process behavior.
- Containment tests exposed, in sequence, a missing typed
  admission/containment import, unreported pre-exec default-root access, a PID
  reuse write escape, absent anonymous private channels, an accepted unresolved
  path mutator, and a reduced pipe-capacity deadlock that surfaced as a
  `TypeError`. Each was a behavioral Red against the affected safety rule.
- A correct full backend run using `--import-mode=importlib` returned
  `16 failed, 1363 passed, 39 skipped`. Ten failures were explicit missing
  owner/live selectors. Six were stale exact operation-count or migration-head
  expectations and were treated as regressions rather than waived.
- Independent real-filesystem review reproduced two archive races: pathname
  checks followed by POSIX rename could replace a destination created in the
  gap, including during rollback, and a final receipt created after archive's
  one-time check did not stop evidence movement. The new race suite first
  failed collection because `_acquire_m5_current_completion_lock_v1` did not
  exist. No compatibility fallback was accepted.
- Final integration review then reproduced two lock-design Reds. Distinct
  owner data roots could acquire distinct locks while targeting the same
  checkout-global final receipt, and renaming the held lock pathname allowed a
  second process to lock a replacement inode. These results invalidated the
  first owner-root-scoped lock design before commit.

The exact shell spelling for the recovered six-test pagination run, the
receipt test invocation, and the 77-test witness-policy run was not retained.
Their result counts are recorded below without reconstructing commands.

### The alert browser verifier had a separate Registry-page loop

A Node source-wiring assertion was added before the browser verifier change.
It failed because `verify_m5_codex_alert_lifecycle.mjs` still defined its own
bounded cursor loop instead of using the shared fail-closed Registry-page
reader. That Red prevented the alert browser proof from having weaker
pagination checks than the main and quota verifiers. The exact failure timing
was not retained.

### The M5 witnesses stopped at the first 200 history points

The canonical preflight ran against three verified accounts with current
successful provider collections, but reported
`current_codex_quota_lineage_required`. The verifier requested a 30-day
capacity-history range and consumed only its first 200 ascending rows. Real
retained histories contained 247, 488, and 364 rows, so their current
observation IDs were on later pages. The separate authoritative quota
reconciliation entrypoint had the same one-page defect and was included in the
correction. During the fail-closed refactor, the pure page-policy regression
also failed with `Missing expected exception` because a control-character
cursor was accepted; that cursor case was rejected before Green.

### Retained alert history made a fresh literal `opened` impossible

Every eligible real Codex capacity fingerprint already had retained alert
history. The alert domain correctly emits `reopened` when a recovered
fingerprint becomes active again, but the M5 witness selector required exactly
one `opened` transition across the alert's complete history. A clean retry could
therefore pass only by deleting valid history, which the retention contract and
runbook forbid.

The pure regression changed first. It supplies one completed historical
occurrence followed by a complete fresh `reopened`, repeated, owner-action, and
recovery occurrence:

```bash
PYTHONPATH=backend/src:. backend/.venv/bin/pytest -q --tb=short \
  backend/tests/integration/alerting/test_codex_capacity_lifecycle.py::test_alert_witness_policy_selects_the_latest_reopened_generation
```

Before the selector change it failed for the expected reason:

```text
M5CodexAlertWitnessErrorV1: m5_alert_witness_lifecycle_incomplete
1 failed
```

This Red proves the retained-history selection defect only. It does not claim a
provider delivery, owner browser action, recovery, or private alert witness.

## Green evidence

### P02 canonical-browser correction under plan 1.8.0

The mobile header returns to two rows at 400 pixels and below. The revocation
oracle now branches only on visible secure state. Password change uses a parent
`closed`/`draining`/`ready`/`submitting` lifecycle, an acknowledged feature
cleanup barrier, generation-fenced feature and header-session callbacks, inert
navigation and session controls, one mutation, one bounded reconciliation, and
coherent route/session/focus restoration. Known noncommitted outcomes return to
the ready form, while an unknown mutation outcome keeps protected content
locked for explicit owner verification.

The runner accepts only repeat counts 1 through 30, stops on the first failure,
and admits only closed scenario output. It retains the existing direct Node
invocation and reduces spawn, timeout, encoding, unexpected text, channel/status
conflicts, and every nonzero return code other than the exact allowlisted script
failure code 1 to `browser_output_invalid`. The three return-code regressions
for 2, 127, and -9 went from Red to Green. The pure policy suite returned
`65 passed`; final Git blob identities are
`8afd41102d0168ac4a0a5934a591ede69804cc60` for `run_browser.py` and
`96083d23627c015a26bbfd154bb7ca37e5de5496` for its policy tests. Independent
review was **CLEAN**, with no P0, P1, or P2 finding.

Ruff, format, strict mypy, and diff checks passed. Both revocation and the
complete P02 `all` lane passed in the same PATH/PYTHONPATH-only environment used
by `AUTO-TEST`. With one successful production build already present,
responsive, revocation, and password change then each passed 30 consecutive
isolated first-attempt real-server/real-Chrome repetitions. The complete P02
`all` lane, `security_boundary`, and `hostile_resource` passed again. Focused M5
automation returned `55 passed`, M5 UI policy returned `16 passed`, and both
`AUTO-QUALITY` and `AUTO-BUILD` passed.

The final complete `AUTO-TEST` returned **PASSED (operational)**. It passed 104
automation command tests, both focused Argon2 tests, and the backend with
`1361 passed, 37 skipped, 1 warning`; verified OpenAPI compatibility with 67
operations; built the production frontend; passed 2 foundation browser tests;
and passed the complete P02, security-boundary, and hostile-resource browser
lanes. The temporary exact Claude process and private test root used by the
declared real-process test were safely stopped and removed after the pass. The
37 explicit owner/live/environment skips retain their existing non-passing
meaning outside this local routine; this result is not `AUTO-M5-EXIT`.

### Exact authenticated identity semantics

The parser now treats `true` as the admitted default provider's authentication
policy, returns absent identity only for `true` with no account or workspace,
accepts a complete ChatGPT account and workspace with `true`, and rejects
inconsistent `false` plus account shapes. The adapter version advanced to
`1.0.2` and the parser version to `1.0.1`; the provider wire schema, normalized
output schema, mapping ID, database, and public API remain unchanged.

Focused Green:

```bash
PYTHONPATH=backend/src backend/.venv/bin/pytest -q \
  backend/tests/adapters/providers/codex/test_identity_parser.py \
  backend/tests/adapters/providers/codex/test_manifest.py \
  backend/tests/adapters/providers/codex/test_critical_mutation_policies.py
```

```text
74 passed in 0.25s
```

This covered the identity parser, exact manifest policy, and critical Codex
mutation policies. Live dashboard retry and quota collection remain required
before M5 acceptance.

After every admission consumer was bound to the canonical mapping artifact's
new SHA-256 digest
`417c46ba301f9c4217c606beed52be93c9bf497da9ca5b99ca4b1993167688d3`,
the same exact real-installation admission test passed (`1 passed in 0.18s`).
The mapping ID remains `M5-CDX-0-160-0-002`.

The first mutation rerun failed closed because changing the ChatGPT type check
from `or` to `and` survived. The API-key case lacked otherwise-valid identity
fields, so a later validation rejected both implementations. The test input was
tightened to an otherwise-complete API-key shape. The final canonical mutation
run evaluated `1708` mutants: `1698` killed, `10` exact hash-pinned equivalent,
and zero skipped, suspicious, timed out, or non-equivalent survivors.

### Capacity provenance admits SemVer build metadata

The existing bounded Capacity token grammar now also accepts `+`, allowing the
admitted Codex mechanism version to retain its SemVer build metadata and schema
digest without changing the interpretation of any previously accepted value.
The complete focused Capacity contract file passed:

```bash
PYTHONPATH=backend/src backend/.venv/bin/pytest -q \
  backend/tests/capacity/test_quantity_and_health.py
```

```text
13 passed in 0.22s
```

This Green establishes the compatible `CTR-CAP-001` validation widening only.
The authenticated provider operation must be repeated through a successful
Capacity commit before any live quota, history, API, UI, or acceptance claim.

### Interrupted local commit recovers after full cadence

The collection action policy now classifies exactly
`collection_commit_interrupted` as transient. A different durable collection
run can become eligible after the complete configured quota cadence; the
change does not create an immediate retry and leaves every other internal
failure classification unchanged.

The collection policy and Capacity contract suites passed together:

```bash
PYTHONPATH=backend/src backend/.venv/bin/pytest -q \
  backend/tests/adapters/providers/codex/unit/test_collection_action_policy.py \
  backend/tests/capacity/test_quantity_and_health.py
```

```text
16 passed in 0.53s
```

This Green proves the local scheduling and provenance policies. A real
post-cadence provider run and successful Capacity commit remain required.

### Managed-profile safety correction

```bash
PYTHONPATH=backend/src backend/.venv/bin/python -m pytest -q \
  backend/tests/adapters/providers/codex/test_manifest.py \
  backend/tests/adapters/providers/codex/live/test_managed_identity.py \
  backend/tests/adapters/providers/codex/test_security_policy.py
```

Result: `22 passed`. Production now checks safe `auth.json` metadata without
opening its content and rejects an uninitialized, linked, public, nonregular,
wrong-owner, or unbounded credential store before starting app-server.

### Complete account and alert pagination

The same browser command that timed out at Red passed after the visible
pagination and direct account query were implemented:

```bash
backend/.venv/bin/python frontend/tests/browser/p02/run_browser.py account_beyond_page
# P02 ACCOUNT BEYOND PAGE: PASSED

backend/.venv/bin/python frontend/tests/browser/p02/run_browser.py \
  account_beyond_page --no-build
# P02 ACCOUNT BEYOND PAGE: PASSED

backend/.venv/bin/python frontend/tests/browser/p02/run_browser.py \
  accounts_admin --no-build
# PASSED
```

The alert cursor, duplicate-ID, and initial 201-account tests returned
`3 passed in 6.94s`. The whole alert lifecycle file returned
`8 passed, 3 skipped in 6.92s`; the three skips are existing owner-live
selectors and are not counted as Passed. After the archived-account Red, its
same real test returned `1 passed in 5.70s`, and the three focused pagination
tests returned `3 passed in 5.75s`. Production alert delivery holds one
Registry revision and one `as_of` across pages, requires a terminal page,
rejects missing, repeated, or nonadvancing cursors and duplicate account IDs,
compares nonarchived account and active-resource IDs with the stable global
Registry snapshot, and resolves exactly one eligible resource subject.

The related owner/quota/alert Registry pagination and expiry work also
returned `7` focused tests passed and `100` broader tests passed. The complete
current Node story inventory then passed all `18` tests with zero failures or
skips:

```bash
node --experimental-strip-types --test \
  tools/ui/test_m5_codex_policy.mjs \
  frontend/tests/pure/alert-presentation.mjs \
  frontend/tests/pure/provider-account-presentation.mjs \
  frontend/tests/pure/quota-reset-presentation.mjs
```

The alert browser verifier now imports `readAllRegistryItemsV1`; the source
wiring test rejects restoration of its former private 64-page loop. The real
201-account SQLite/loopback/Chrome scenario also passed.

### Complete M5 quota-history pagination

The shared browser reader now follows the versioned API's opaque capacity
history cursor until a terminal page. It requires an available bounded page,
stable subject/metric/series identity, the exact page limit, a progressing
unseen cursor, a null terminal cursor, and unique observation IDs. Both the
main M5 verifier and the official `/status` reconciliation witness use this
reader without narrowing the approved 30-day history range.

The focused Node policy file passed all 16 tests; the exact M5 Node inventory
passed all 19 tests. A real authenticated shared-browser/API Green traversed
the same three histories and found exactly 1/1, 2/2, and 2/2 current
observations respectively after collecting all 247, 488, and 364 retained
rows. The read made no Registry, provider, or database mutation. The exact
clean-revision canonical preflight remains required after commit and service
restart.

The later authoritative quota witness exposed a separate browser-presentation
Red. Its API proof had already consumed every history page, but its DOM check
inspected only the initially rendered page. A real account had 502 retained
rows across three pages; the built account view truthfully rendered its first
200 rows and the visible **Load next history page** control, while neither
current quota observation was in that first ascending page. The canonical
witness therefore blocked with
`m5_quota_current_history_point_not_charted`. A source-wiring test also failed
before the verifier change because it did not import
`advanceCapacityHistoryPageV1` or drive the visible pagination control.

The corrected witness keeps the production UI's bounded, owner-visible paging
behavior. It now clicks that generated-client control until the UI reports a
terminal page. For every real GET it requires the stable account/metric/series/
range selector, including byte-for-byte equal `from` and `before` values from
the initial request through every continuation, exact 200-row bound, a new
opaque cursor, an available and contract-valid response page, at least one row
from every nonterminal page, unique observation IDs, exact append order,
chart/table lineage equality, a progressing visible page count, and terminal
UI state. Any HTTP, cursor, page, DOM, or lineage mismatch blocks the witness;
partial rows cannot satisfy the current-point assertion.

Focused Green:

```bash
node --experimental-strip-types --test tools/ui/test_m5_codex_policy.mjs
```

Result: `16 passed, 0 failed, 0 skipped`. The real authenticated shared-Chrome
verifier then traversed `2`, `3`, and `2` visible pages for the three verified
accounts and returned:

```text
M5 CODEX QUOTA BROWSER: PASSED — 3 account(s), 5 window(s), exact API/history/DOM values
```

That run used only versioned same-origin GETs and made zero Registry or provider
mutations. It is focused Green evidence for `AC-LIVE-005`, `AC-HIST-001`, and
the M5 quota browser witness; the revision-bound canonical prerequisite and
`AUTO-M5-EXIT` still must pass after integration. This correction changes no
product UI, API, generated contract, database, migration, dependency, secret,
or provider boundary.

A follow-up source-policy Red failed because the first correction required one
`from` and `before` parameter per request but did not compare their values
across pages. The final policy binds both decoded values from the initial real
request and rejects drift on every continuation. Its focused test and exact
19-test Node inventory passed. The first post-hardening live attempt blocked at
`m5_quota_current_lineage_required` before reaching the UI. A subsequent
read-only complete-history inspection proved current matches of `1/1`, `2/2`,
and `2/2` with successful identity collection runs; the next full browser run
then passed for all three accounts and five windows. The blocked attempt is not
credited as Green.

### A complete collection left an omitted prior-run window current

After the first corrective rollover and activation, the existing real-system
scenario ran against exact service revision
`063445154bca0bf5ec43db94ba57c17fd193fd99`:

```bash
PYTHONPATH=backend/src backend/.venv/bin/pytest -q --tb=short \
  backend/tests/integration/capacity/test_codex_capacity_history.py::test_running_service_persisted_native_codex_windows_and_history
```

It failed at the current-lineage assertion. The latest successful
`complete_scope` collection contained one current native window, while the
versioned public current API retained two windows whose collection-run set
included exactly one prior run. The immutable prior observation remains valid
history; its continued presence in the current projection is the defect.
`AUTO-M5-QUOTA-WITNESS` would therefore fail closed with
`m5_quota_current_lineage_required`.

This Red exposed missing implementation of the existing `FR-QUOTA-001` /
`M05-PURE-005` rule: a strictly newer complete collection can establish that a
previously current native window is not currently observed, while a partial or
failed collection cannot. The owner approved plan 1.5.0 and the production
correction is now local Green as recorded below. The second exact live service
rollover, fresh collection, data correction through genuine observation, quota
witness, and M5 completion are Not Run. No provider response, account
identifier, quota value, credential, prompt, response, source content, or
arbitrary environment value was retained in this public evidence.

### Complete-scope lifecycle and second-rollover local Green

The complete-scope implementation retires an omitted active native-window
definition only when the incoming collection has proven identity, exact scope,
and strictly newer semantic time. A later strictly newer complete absence
advances an inactive definition's lifecycle watermark without inventing an
observation, so a delayed older presence cannot reactivate it. Partial, failed,
older, equal-time, retired, and unproven-identity inputs cannot change it; a
later qualifying presence can reactivate it. Current account, window,
forecast, availability, refresh, and compare-and-set reads require an active
definition, while immutable history remains available. The frozen-node Red
failed because the lifecycle-aware omission argument was absent; the corrected
existing Capacity suite passed `71` tests.

The bounded service-activation implementation adds only the approved exact
second rollover from `063445154bca0bf5ec43db94ba57c17fd193fd99`. It preserves
the first archive, uses the separate fixed
`m5-service-activation-corrective-archive-0634451` singleton, revalidates every
retained archive before each mutation, and admits only the enumerated fresh-root
retry states. Its pre-mutation policy also rejects the trusted revision and
both completed corrective revisions as a new rollover target; the frozen-node
Red showed the pinned revision had incorrectly returned `rollback_candidate`.
The first live second-rollover attempt then blocked safely with
`m5_service_receipt_invalid`: after the workstation reboot, the immutable
`0634451` receipt retained the original activation PID/start identity while
systemd had restarted the exact same clean revision under a new process
generation. Independent read-only post-block checks passed the unit, revision,
journal, rollback, browser, Registry, and stable-database proofs. The existing
frozen policy node went Red because no
completed-rollover restart-generation policy existed. The correction preserves
the original receipt, independently validates the current exact same-revision
service, accepts either its original or a later positive PID/start generation,
and rejects any revision or process-shape mismatch before mutation.
The activation suite then passed `43` tests with the same node inventory, and
the module boundary check is clean. `AUTO-QUALITY` and `AUTO-BUILD` pass. The generated OpenAPI
client update changed source metadata only after the Capacity repository hash
changed: compatibility remained compatible, the schema SHA stayed unchanged,
and the surface remains 67 operations. These deterministic Greens do not claim
a live rollover, service activation, fresh provider collection, quota witness,
or milestone gate pass.

That earlier corrected checkout's canonical `AUTO-TEST` rerun also passed its
declared local boundary: `1361` backend tests passed, `37` explicit owner/live or
environment selectors remained skipped, generated API/client compatibility
passed, and every required production browser scenario passed. Its first run
had one real-process precondition failure because the running workstation
Claude sessions used 2.1.301 rather than admitted 2.1.289. The exact failed
test passed with one temporary real 2.1.289 MCP-server process confined to a
private temporary configuration root; the complete gate was then rerun once
and passed. The test-owned process and root were stopped and removed after the
gate. No provider call or default-profile change was used.

### Second corrective rollover and corrected live lineage

The approved second corrective rollover later completed both canonical
invocations. Stage one restored and proved the pinned trusted runtime,
preserved the complete `0634451` transition in the fixed
`m5-service-activation-corrective-archive-0634451` singleton while retaining
the first archive, created the fresh owner-only transition root, and returned
the typed status `5` rerun result. Stage two revalidated both archive
singletons, performed the real rollback drill, and activated exact clean
detached revision `6d6e1aa9d9b64d50e3f83d0f1686e6cff04b7c17`. Its systemd,
HTTP, authenticated-browser, Operations revision, Registry, database,
rollback-runtime, and activation-receipt checks passed. This is a bounded
activation prerequisite result, not `AUTO-M5-EXIT`.

New genuine complete Codex collections then exercised the lifecycle correction
on that service. The named real-system regression proved that the public
current window set contains one window and that its observation and collection
lineage belong only to the newest complete run. Immutable earlier observations
remain available in history.

### The corrected live regression read only the first history page

The production current assertions above passed before the unchanged history
assertion failed. That assertion queried the existing 30-day history in
ascending order with limit `200`, read only its first page, and then expected to
find the newest run there. The real database contained 1,606 retained rows over
nine pages, so the first page correctly contained older history and the test
failed at `assert current_lineage`. This Red identified a verification defect;
it did not contradict the already-passing current projection, persistence, or
`CTR-CAP-006` ordering.

The owner-approved 1.6.0 correction keeps the same query, ordering, and page
limit. It traverses at most 128 pages, requires a new opaque cursor for every
nonterminal page, a null cursor on the terminal page, the combined
`(observed_at, observation_id)` sequence in exact ascending order, unique
observation IDs, the exact newest-run current-window set, and at least one
retained prior-run observation. The same live command then passed across nine
pages with all 1,606 unique rows. A later rerun after newer genuine collection
passed across nine pages with 1,608 unique rows. The explicit combined-order
assertion also passed against the later growing real history. No retained row
was deleted or reordered, and no production module, public contract, API,
schema, migration, provider behavior, dependency, generated client, or ADR
changed.

### Approved third corrective rollover local Red/Green

The pagination and evidence commit will differ from the running `6d6e1aa`
revision, so approved plan 1.6.0 permits one exact evidence-preserving rollover
from that completed revision into fixed owner-only parent
`m5-service-activation-corrective-archive-6d6e1aa`. Before implementation, the
four extended existing activation nodes for atomic inode move, exact policy,
archive selection, and partial/multiple rejection returned `4 failed in
0.65s`. Each failure was the expected `AttributeError` for absent
`THIRD_CORRECTIVE_*` constants. The frozen activation inventory remains 43
nodes.

```bash
backend/.venv/bin/python -m pytest -q \
  tools/automation/test_m5_service_activation.py::test_corrective_rollover_archives_complete_transition_by_atomic_inode_move \
  tools/automation/test_m5_service_activation.py::test_corrective_rollover_policy_is_exact_and_returns_typed_rerun \
  tools/automation/test_m5_service_activation.py::test_corrective_rollover_retry_selects_one_complete_schema_bound_archive \
  tools/automation/test_m5_service_activation.py::test_corrective_rollover_retry_rejects_multiple_or_partial_archives
# 4 failed in 0.65s
```

After adding the exact constants and archive mapping, the extended state matrix
in
`test_corrective_rollover_policy_is_exact_and_returns_typed_rerun` returned
`1 failed in 0.21s` with `corrective rollover state policy is absent`. The
minimal production policy now accepts only the closed ordered archive prefix,
the exact next reserved candidate for the first two transitions, and one new
candidate after `6d6e1aa`; skipped, partial, collided, invalid, or reserved
states block before mutation.

Green and review evidence:

```bash
test "$(rg -c '^def test_' tools/automation/test_m5_service_activation.py)" = 43 \
  && backend/.venv/bin/python -m pytest -q \
    tools/automation/test_m5_service_activation.py
# 43 passed in 1.11s
```

Ruff and format checks passed, strict mypy passed for the implementation
source, and the frozen M5 gate-inventory selector passed `1` test in `0.31s`.
Independent review found no blocking issue. These local results prove the
approved policy and custody implementation only. The later live result is
recorded separately below.

### Third corrective rollover and exact `e066d7e` service

The third corrective rollover completed both canonical invocations. Stage one
restored and proved the pinned trusted runtime, preserved the complete
`6d6e1aa` transition below the fixed owner-only
`m5-service-activation-corrective-archive-6d6e1aa` parent, created the fresh
transition root, and returned the required status `5` rerun result. Stage two
revalidated the ordered archive chain, completed the real rollback drill, and
activated exact clean revision
`e066d7e1ba0124f0454c07002ea7b2ad0817d6b9`. The selected user service,
loopback and LAN HTTP, authenticated browser, Operations source revision,
unchanged Registry and database, trusted rollback runtime, journal, unit, and
activation receipt agreed. `AUTO-M5-SERVICE-ACTIVATE --status` returned
receipt-bound **YES** for `e066d7e`.

The stale predecessor prerequisite set was archived through the canonical
no-replace routine. `AUTO-M5-OWNER-OUTCOMES` then passed for `e066d7e` with
four total outcomes: three verified and one owner-unavailable. Three fresh
genuine post-start Codex collections succeeded for the verified accounts, and
the paginated current/history integration test passed both cases against the
new service. These are current prerequisite and lineage results. They do not
include official `/status` reconciliation, the process witness, containment,
an alert-witness file, or an M5 completion receipt.

### Alert browser-child termination Red and approved 1.7.0 scope

A genuine Codex capacity alert on the exact `e066d7e` service completed a fresh
opening or reopening, a distinct repeated delivery, one authenticated owner
action, and a later source-proven recovery. The read-only browser verifier
rendered the recovered card and complete history, proved the exact service
revision and freshness, observed zero mutations and an unchanged complete
Registry digest, and emitted exactly one valid
`agentmonitor.m5-alert-browser-proof.v2` JSON document. It then closed its
temporary page but retained its Playwright CDP client connection. The Node
child did not exit, so Python `_browser_proof` reached its 180-second timeout,
reported `m5_alert_witness_browser_unavailable`, and
`AUTO-M5-ALERT-WITNESS` wrote no witness.

This is the meaningful real-system Red for approved focused plan 1.7.0. The
direct bounded invocation emitted the valid proof and then timed out with
status `124`; the canonical writer separately reached its 180-second bound.
The minimal implementation now retains the browser handle and closes the
verifier-owned Playwright connection after closing its temporary page. It does
not force process exit or close the owner's browser.

The direct real-browser Green exited `0` in `2.1s`. Before/after proof retained
the same Chrome PID/start identity, the same pre-existing authenticated target,
dashboard authentication, selected service PID/start/revision, and complete
Registry digest. The UI policy suite passed `16/16`, the alert-witness
automation suite passed `12/12`, and independent review was **CLEAN**. This
proves the bounded verifier resource-lifecycle correction. The active service
still runs the prior exact revision, and no new create-once alert witness or M5
completion receipt is claimed.

### Fourth corrective rollover local Red/Green

The four focused existing activation cases first returned four expected
failures because the exact fourth-rollover constants were absent. The minimal
implementation added only the fixed `e066d7e` revision/archive mapping and
extended the closed ordered policy and custody chain. The focused four cases
then passed, and the complete frozen activation suite passed `43/43`.
Ruff check and format and strict mypy passed. Independent exhaustive review
covered 14,336 transition-policy combinations and 294 activation-decision
combinations with zero mismatches; the review result was **CLEAN**.

These results prove local fourth-rollover policy and artifact custody only.
They do not prove either real service-transition invocation, archive creation
on the owner data root, candidate activation, refreshed prerequisites,
`AUTO-M5-ALERT-WITNESS`, or `AUTO-M5-EXIT`; all remain **Not Run**.

### Fourth live rollover, quota policy Red, and approved 1.9 Green

The fourth canonical rollover later preserved the complete `e066d7e`
transition below fixed singleton parent
`m5-service-activation-corrective-archive-e066d7e`, restored and verified the
trusted runtime, and returned the required typed rerun result. Its second
invocation activated exact clean detached revision
`d81afab9e5b1c1dbdb690f390e77cee66eba5437`. Real systemd, HTTP,
authenticated-browser, Operations source revision, complete Registry,
database, immutable rollback runtime, transition receipt, and all four prior
archives passed. Owner outcomes were recollected for that service, scheduled
collection lineage became current, and a fresh genuine alert occurrence
completed reopen, repeat, owner acknowledgement, and source-proven recovery.
`AUTO-M5-ALERT-WITNESS` passed and created the current private prerequisite.

The subsequent real `AUTO-M5-QUOTA-WITNESS` run completed authenticated API,
DOM, retained-history, Registry, identity, collection-lineage, and zero-
mutation proof and accepted all four owner-entered window observations from
the installed Codex `/status` view. Final reconciliation failed closed as
`m5_quota_witness_input_invalid`; no private quota witness was created. A
read-only diagnostic located the exact boundary: the verified browser/history
row contained required opaque `current_observation_id`, while the closed quota
policy accepts exactly the five provider-neutral quota facts. The same
function had already built and digest-verified that five-field projection but
returned the six-field browser row.

The focused Red failed at `_agent_records` with that exact error. Commit
`1e4b9cd3fcaa68ad091480af365694eef9c40722` retains
`current_observation_id` through independent history verification, then
returns only the already validated five-field policy projection. The focused
case passed, its two strict rejection variants passed, the complete quota-
witness file returned `27 passed`, and Ruff, format, and strict mypy passed.
The private browser-proof schema, history digest, input values, freshness,
owner confirmation, Registry/DOM checks, and create-once behavior are
unchanged.

Because the corrected source revision requires a new service-bound evidence
set, commit `d4f4743a319ad740ab683a53e9e8afa7cc467059` adds only the approved
fifth fixed rollover from `d81afab` into
`m5-service-activation-corrective-archive-d81afab`. Four focused cases first
failed because the fifth constants were absent, then passed. The complete
activation file returned `43 passed`; dispatcher/catalog checks returned
`3 passed`; Ruff, format, strict mypy, and diff checks passed. Exhaustive review
covered 73,728 transition combinations and 448 activation decisions with zero
mismatches. These are local policy results. The fifth live two-stage rollover,
fresh prerequisites, authoritative quota witness, containment, canonical
process witness, `AUTO-M5-EXIT`, and owner acceptance remain **Not Run**.

### Effective-containment Red, focused 1.10 local Green, and live mutator failure

The required zero-skip Story run reached the real managed-profile verifier and
failed before provider execution as
`m5_codex_containment_profile_tree_invalid`. Read-only metadata checks found
the expected owner-owned `0700` root chain and private `0600` credential stores,
while ordinary Codex-created nested files and directories carried modes from
`0444` through `0775`. The prior verifier rejected those unreachable nested
entries solely for group or other ordinary permission bits.

Commit `1143d964e72628f0b9060849098d60da213634f9` changes the tree digest to
effective enclosing-root containment while retaining every nested mode in the
evidence. It rejects links, nonregular objects, foreign UID/device entries,
regular-file hard links, special bits, owner-unsearchable directories,
traversal errors, and size/count/path bounds. Commit
`f4d4bf734e935ce6503b1aa8c81e950e4e875af2` adds the missing exact `0700`
validation and inode pin for the intermediate `profiles` root. Its focused Red
failed because a `0755` intermediate root was admitted; the two focused cases
then passed. Commit `d71b79c396ce9ad524bc1430425a0b788d93e08a` adds real-
filesystem cases that exceed the 10,000-entry bound and use a 4,113-byte
descriptor-relative path above the 4,096-byte bound. All three non-live
containment classes passed `30/30`; the full file passed those same `30` and
skipped the single owner-selected authenticated case. Current-exit passed
`66/66`. The skipped case is
not credited as live evidence. Ruff, format, strict mypy, and diff checks passed
for the focused correction.

The same commit rebinds the exact M5 Story inventory from the interim `478` to
`480` Python tests with digest
`e90485d6866065f3149cf1285b5c18c665d26068de2da5c4c61862830bb56bf9`.
The separate test-only enrollment correction compares stable aggregate fields
without the expected global Registry watermark advance; it changes no
production Registry behavior.

A later real containment attempt against the unchanged `d81afab` service
passed its safe metadata and driver work, then failed closed as
`m5_codex_containment_path_mutator_unverifiable`. Privacy-safe trace
classification found exactly two successful provider app-server `chmod` calls,
both inside the selected managed profile and none below a default root. Their
path arguments did not yet satisfy the verifier's closed mutator-path proof, so
the attempt is **Failed**, creates no completion evidence, and cannot be
treated as a containment pass. The first two attempts had already failed as
`m5_codex_containment_private_channel_invalid` after an empty result channel;
neither result is credited. At that checkpoint the fifth service rollover was
**Not Run**.
Approved plan 1.11.0 limits the follow-up to inode-bound verification of
the observed idempotent directory `chmod(..., 0700)` calls and distinct,
sanitized private-channel failure classification. At that checkpoint its
implementation was pending; the completed 1.11 through 1.13 local work is
recorded below.

### Latest complete alert occurrence on retained history

The alert-witness selector now validates the complete retained sequence and
lifecycle/severity continuity, requires its single literal `opened` at sequence
one, then selects the latest activation (`opened` or `reopened`). That selected
occurrence must contain a distinct genuine repeat before exactly one owner
action and exactly one later recovery. Missing recovery, an extra recovery,
nested activation, absent initial `opened`, duplicate active source lineage, or
an incomplete occurrence fails closed. Older complete occurrences remain
retained but cannot supply any stage of the selected witness.

The combined selector and witness-policy Green ran with the admitted retained
Codex CLI `0.160.0` first on `PATH`:

```bash
PYTHONPATH=backend/src:. backend/.venv/bin/pytest -q --tb=short \
  backend/tests/integration/alerting/test_codex_capacity_lifecycle.py \
  tools/automation/test_m5_codex_alert_witness.py
```

Result: `19 passed, 3 skipped in 5.89s`. The three skips are explicit
owner-live selectors and are **Blocked**, not Passed. The browser verifier now
recognizes either `opened` or `reopened` as an opening transition while still
requiring repeated condition, owner action, and recovery history. That is a
source-level compatibility correction; a fresh production Chrome lifecycle and
the create-once `AUTO-M5-ALERT-WITNESS` remain required.

### Configured capacity thresholds use truthful alert copy

Requirements `FR-ALERT-001/002`, `FR-UI-003/006`, and scenarios
`UI-ALERT-007/010` require configured threshold context without relying on
color or implying a different capacity state. The alert card previously used
the fixed title `Capacity running low` for every `capacity_remaining` alert.
A genuine 94% remaining observation therefore appeared low when the temporary
account rule deliberately used a 100% critical threshold.

The Red command was:

```bash
node --experimental-strip-types --test \
  frontend/tests/pure/alert-presentation.mjs
```

It failed with `a configured capacity threshold must not label 94% remaining
as low`. The Green policy uses **Capacity threshold reached**, preserves the
exact `94% remaining` value, and renders `Critical threshold: 100% or less`
from the V1 alert fields. The same focused command then returned `1 passed`.
The exact Node story inventory returned `18 passed`,
`tools/automation/test_m5_current_exit.py` returned `50 passed`, TypeScript
typechecking exited zero, and the production Vite build completed. No backend,
API, database, provider, migration, dependency, security, or privacy contract
changed. A fresh built-browser check remains required after the corrected
revision replaces the current revision-bound live evidence.

Independent review then found that the first Green still described a recovered
record as having reached the threshold. A lifecycle regression was added and
failed with actual `Capacity threshold reached` / `Configured capacity
threshold reached` where `Capacity threshold cleared` / `Warning threshold:
0% or less` was required. The refactored policy now distinguishes open,
recovered, and configuration-closed capacity records. The focused pure test is
Green for all three lifecycles, while the exact inventory count and digest stay
unchanged because the strengthened assertions remain one Node subtest.

### Current dashboard views survive direct open and refresh

`FR-UI-002` and deployment scenario `DEP-NET-007` require each published
dashboard view to open at its own URL. The React route allowlist already
published Organizations, Operations, Alerts, and Alert rules, but the P01 HTML
transport omitted those four exact paths. A real migrated file SQLite and
production Uvicorn regression failed on `GET /organizations` with `404` before
the transport correction:

```text
backend/.venv/bin/python -m pytest \
  backend/tests/integration/api/test_dashboard_html_routes.py -q --tb=short
```

After adding the four exact routes, the same command passed all three tests.
It requests every fixed P02 route plus an opaque account detail over a real
loopback socket and checks that each returns the production dashboard HTML. It
also proves an unknown page and an unknown `/api/v1` resource still return the
safe `resource_not_found` JSON problem, so the correction does not introduce a
catch-all that could mask API errors. The public API operation set and schema
digest are unchanged; the canonical generator refreshed only the source and
artifact provenance in the committed OpenAPI/client pair.

Independent review found the same four paths missing from the trusted-LAN
public-shell allowlist. A real migrated SQLite service on the selected loopback
and private-LAN sockets failed at `/organizations` with `403`; after the closed
allowlist was synchronized, the same real HTTP regression passed. The
production Chrome `monitoring_dashboard` scenario then directly opened and
reloaded every fixed P02 feature route plus the dynamic account route. Every
document returned `200`, React selected the expected view before and after
reload, and the scenario passed without external requests, browser storage, or
browser exceptions. The isolated database contained no registered account, so
the dynamic account route truthfully rendered **Account unavailable** rather
than invented account data.

### Deadline contract and application drain

After the compatible provider-contract widening, the four focused tests
returned `4 passed in 0.18s`; the broader provider suite returned
`149 passed in 0.64s`; the relevant mutation suite returned
`40 passed in 0.21s`; and composition/compatibility returned
`21 passed in 10.17s`. The generated provider-schema check passed with digest:

```text
a6e32ced602043b0ef4376a28ce068d17abfe0ba0adf2d10475f9ce5cc3ad30b
```

The focused shutdown assertion plus the real owned-child lifecycle tests then
returned `3 passed in 3.37s` with a 45-second service drain.

### Completion prerequisite policies

- The receipt schema test passed once containment fields were required; the
  complete then-current `tools/automation/test_m5_current_exit.py` run returned
  `50 passed`.
- Rewritten real-I/O witness policy tests returned `77 passed`; minimum quality
  controls reported source, backend, frontend, and aggregate minimum coverage
  true.
- Owner-outcome private-file tests returned `12 passed`; quota witness tests
  returned `22 passed`.
- The archive file now returns `15 passed` against real temporary filesystems.
  Two forked processes racing to one destination prove exactly one Linux
  `renameat2(RENAME_NOREPLACE)` move succeeds and the losing source remains.
  A separate pipe-coordinated child holds the checkout receipt-scoped guard
  while archives for two distinct owner roots and the M5-exit adapter all
  refuse contention. Another forked child cannot enter after the first process
  has had its entire receipt directory renamed and replaced: the Linux abstract
  socket name remains kernel-bound, and the first holder detects the directory
  identity change. Nonprivate or symlinked receipt directories are rejected,
  and a real rollback keeps both the archived inode and a newly created
  fixed-name destination without replacing either. No mock or injected
  filesystem collaborator is used.
- The containment and admission command was:

  ```bash
  python3 -m unittest \
    tools.automation.test_m5_codex_admission \
    tools.automation.test_m5_codex_containment
  ```

  Historical pre-1.10 result: `Ran 28`, `OK`, comprising 27 passes and one truthful authenticated
  live-selector skip. Ruff, mypy, byte compilation, and scoped diff checks
  passed after the refactor.
- The six stale backend regression expectations passed focused reruns: five in
  the first batch and the corrected remaining case in a one-test run. A
  historical pre-identity-correction complete backend rerun returned
  `10 failed, 1374 passed, 39 skipped`; all ten failures were explicit real M4
  fleet, LAN, or M5 owner-selection prerequisites. That historical result is
  retained for provenance and is not a current corrected-checkout result.

### Canonical local routine checkpoints

- `AUTO-M3-TEST` passed its two routine tests and `307` selected technical
  tests with zero skips.
- `AUTO-MUTATION` evaluated `1708` mutants: `1698` were killed, `10` were
  independently bound as equivalent, and none were skipped, suspicious, or
  timed out.
- Plan 1.8.0 `AUTO-QUALITY` and `AUTO-BUILD` exited zero after the 65-test
  runner-policy suite, three 30-run browser proofs, complete P02 lane, two
  named security lanes, 55-test focused M5 automation selection, 16-test UI
  policy selection, and CLEAN independent reviews. `AUTO-PLAN-CHECK` and the
  documentation check passed again after this reconciliation.
- The first plan 1.8.0 `AUTO-TEST` attempt Failed only at the real Argon2 p95
  bound: `0.27936251898063347` seconds was above `0.250` seconds during an
  observed workstation load average of `32.08` with unrelated Vitest and
  `vue-tsc` workers. The low-contention focused Argon2 rerun returned `2
  passed`; the original failure remains recorded.
- The second complete attempt passed 1361 backend tests before the out-of-scope
  systemd wrapper made revocation return `browser_output_invalid` in the
  PATH/PYTHONPATH-only browser environment. After the scope audit restored the
  approved direct child and exact return-code grammar, the final complete
  `AUTO-TEST` passed every declared operational lane: 104 command tests, 2
  Argon2 tests, `1361 passed, 37 skipped, 1 warning` backend, compatible
  67-operation OpenAPI, production build, 2 foundation browser tests, and the
  complete P02/security/hostile-resource scenarios.
- The earlier `AUTO-GIT-PREFLIGHT` result belongs to an earlier local commit
  scope. The plan 1.8.0 clean candidate preflight, remote, and upstream release
  readiness are Not Run.
- Before the retained-occurrence regression, the full M5 Python Story
  selection returned `379 passed`, six truthful live-selector skips, and one
  explicit `BLOCKED: m5_owner_installation_required` result across 386 cases.
  The archive race file separately returned `15 passed` against real files and
  forked processes. Its later 387-ID inventory is historical; the current
  pinned count and digest are recorded in the status table above and the latest
  transition finding below. An inventory update is not a full-suite pass; the
  final gate must execute the exact current inventory with live selectors and
  zero skips.

These are individual intermediate runs. They do not assert that the worktree
was committed and clean, that one unchanged exact revision supplied every
result, or that the live selectors required by `AUTO-M5-EXIT` were available.

## Refactor evidence

- Registry traversal uses stable snapshots, complete terminal pages, advancing
  cursors, and duplicate guards for owner/quota digests and alert delivery.
- The UI loads later account pages through the generated API client and fetches
  an explicitly selected account through the versioned detail endpoint.
- P02 centralizes the password transition in the shell, waits for removed
  feature effects to acknowledge cleanup, and fences obsolete feature and
  header-session callbacks by generation. The password component retains only
  its ready/submitting mutation state and secret-local fields.
- The closed browser runner retains the existing direct Node child, bounds
  repetition, clears raw captured output, and exposes only the exact pass line,
  an allowlisted failure stage at return code 1, or `browser_output_invalid`.
- Private owner/quota prerequisite readers pin and revalidate parent and file
  identities, enforce owner-only modes, and reject link substitution.
- The syscall containment verifier moved selector, result, and trace transport
  to bounded inherited anonymous pipes, drains selector input after child
  launch, pins the managed-profile working directory by descriptor, evaluates
  pre-exec default-profile access globally, and closes provider attribution
  when a PID exits. It now also validates complete mount topology across the
  current and start-bound traced-process `/proc` views, confines exact
  descriptor-bound `ftruncate`, and holds a pidfd-bound group leader until the
  whole new session is signalled before reap under one settlement deadline.
- Provider-schema generation, frontend type checking, Ruff, formatting, mypy,
  byte compilation, Node syntax checks, and scoped `git diff --check` have
  passed in the cited focused handoffs. The canonical build, mutation,
  documentation, planning, and M3 dependency routines also passed as
  development-checkout checkpoints. Plan 1.8.0 `AUTO-QUALITY`, `AUTO-BUILD`,
  and the final complete `AUTO-TEST` passed. The complete preactivation routine
  set later passed on exact clean revision `8cc683d`; `AUTO-M5-EXIT` remains
  outside the evidence recorded here.

## Real-system evidence

| Boundary | Status | Evidence and limit |
|---|---|---|
| Exact installed provider | Passed for installation/admission and empty-root safety | Exact Codex CLI `0.160.0`, installed schema, and local executable were used. The committed config-schema digest is recorded in the discovery/correction evidence. No authenticated quota claim is made. |
| File-backed SQLite/migration | Passed for focused persistence and pagination | Fresh databases used the real migration chain and production repositories/commands. No M5 migration was needed. |
| Production HTTP/generated client | Passed for focused account pagination and Codex API composition | Real loopback service, IAM/CSRF, versioned API, and generated client paths were exercised. `AUTO-BUILD` passed as an intermediate generated-artifact/build checkpoint; `AUTO-M5-EXIT` remains Not Run. |
| Built Chrome UI | Current service Passed; complete alert-history proof Failed | The production frontend and authenticated shared Chrome remain healthy on exact `8cc683d`. The alert witness API oracle returned `192` retained entries while the built Alerts page rendered `100`, so the proof failed closed and wrote no witness. |
| Linux process/filesystem | Five service rollovers and exact authenticated containment Passed | Real systemd, worktrees, guards, archive custody, browser, rollback, mount, `/proc`, descriptor, and process-group boundaries were exercised. The standalone exact-revision Codex `0.160.0` containment rerun passed with zero skips. |
| Four live accounts | Passed for the current `8cc683d` prerequisite | `AUTO-M5-OWNER-OUTCOMES` passed with four outcomes: three verified and one owner-unavailable. It becomes stale after any approved sixth rollover. |
| Authoritative live quota/history | Current witness Not Run | The earlier d81 quota-policy failure and its Green correction remain historical. A revision-bound `8cc683d` quota witness does not exist and must be refreshed after the proposed sixth activation. |
| Genuine capacity alert lifecycle | Current lifecycle Passed; alert witness Failed | Opening, distinct repeat, owner acknowledgement, and source-proven recovery passed on `8cc683d`. The writer then exposed quadratic source lookup; its unchanged rerun reached the browser and failed with API `192` versus DOM `100`. No alert witness exists. |
| Clean exact running revision | Exact `8cc683d` activation Passed | Five corrective rollovers are preserved in fixed private archives, and the fifth rerun activated exact `8cc683d`. Owner-approved 1.16 permits one exact sixth rollover; `AUTO-M5-EXIT` remains Not Run. |

The provider discovery basis is
[Codex 0.160.0 discovery](m5-codex-0.160.0-discovery.md). The later
[read-side-effect correction](m5-codex-read-side-effect-blocker.md) supersedes
its read-only assumption for authenticated app-server operations.

## Security, privacy, migration, license, and documentation impact

- Provider credentials remain Codex-owned under an explicitly selected,
  owner-only AgentMonitor-managed root. AgentMonitor does not accept or persist
  passwords, MFA/OTP values, OAuth tokens, cookies, or raw provider payloads.
- The default Codex profile was not opened, copied, modified, relocated, or
  logged out. Empty-root experiments used isolated managed roots. The
  authenticated syscall proof must still demonstrate zero default-profile
  access and zero writes.
- The adapter allowlists `account/read` with refresh disabled and
  `account/rateLimits/read` with reset-credit details excluded. It does not read
  threads, rollout files, prompts, responses, tool activity, source content,
  arbitrary logs, or arbitrary process environments.
- Identity email may be used transiently for owner-visible verification, but
  this evidence contains no account identity, opaque account ID, credential,
  provider/profile path, process ID, provider payload, prompt, response,
  source content, or arbitrary environment value.
- Linux process observation remains metadata-only and read-only. M5 adds no
  ability to signal, stop, restart, route, switch, or inject input into an
  agent.
- P02 keeps password values, cookies, CSRF headers, request bodies, and error
  objects out of shell state, browser storage, diagnostics, and evidence. Its
  runner clears captured raw output before returning the closed safe line and
  adds no service manager, general process control, or persistent test state.
- The existing database head remains `v1_0707`; no table, destructive
  migration, backfill, or rollback procedure was added.
- Selecting the latest retained alert occurrence changes only the private M5
  witness policy and browser verifier. It reuses the existing provider-neutral
  `reopened` transition, preserves all history, and does not change alert API,
  event, database, or witness-document schemas.
- The `CTR-CAP-001` provenance token change only admits `+` in a bounded safe
  technical version. It changes no stored field, API schema, secret handling,
  or provider operation.
- No dependency, lockfile, SBOM, notice, or license inventory changed.
- The approved plan, React dashboard module, Codex adapter documentation,
  operations runbook, completion-gate documentation, implementation-status
  overlay, README, generated contracts, and this evidence are the affected
  documentation surfaces. Formal acceptance must change only after its claim
  becomes true.

### Residual same-UID pathname race

The containment verifier itself now avoids named selector, result, and trace
artifacts by using inherited anonymous kernel channels and a pinned working
directory descriptor. Separate private owner/quota/alert/receipt cleanup
helpers still validate a named file and then unlink it by pathname. A process
running as the same UID and able to alter the private directory could replace
that name between the final metadata check and unlink. Existing parent, inode,
mode, symlink, and hard-link checks reduce exposure and prevent a false success,
but they do not prove absolute same-UID race freedom for cleanup. This evidence
does not represent that residual as a passing adversarial test.

Root integration/security review accepts this disclosed residual for the
existing local single-user deployment profile. The create-once writers fail
closed, retain no secret or provider payload, and never treat cleanup as proof
of success; a process already running as the owner UID can otherwise alter the
same owner-controlled data root. This disposition does not relax the threat
model or claim malicious same-UID atomic isolation. Eliminating the race would
require a separately reviewed kernel-mediated publication/cleanup design and
belongs with broader local-process isolation work.

## Files and change categories

This is the implementation worktree inventory by owned area, not a final clean
revision manifest:

- A02 adapter and provider schemas:
  `backend/src/agentmonitor/adapters/providers/codex/**` and
  `backend/src/agentmonitor/contracts/providers/codex/**`.
- Shared compatible contracts and generators:
  `backend/src/agentmonitor/contracts/provider_system_v1.py`,
  `backend/src/agentmonitor/contracts/operations_v1.py`,
  `tooling/provider_system/manifest_schema.py`,
  `tooling/foundation/openapi_client.py`,
  `contracts/provider-system/capability-manifest-v1.schema.json`, and
  `contracts/openapi/agentmonitor-v1.json`.
- Root composition and API:
  `backend/src/agentmonitor/composition/codex_*`,
  `backend/src/agentmonitor/composition/providers.py`,
  `backend/src/agentmonitor/composition/alert_delivery.py`,
  `backend/src/agentmonitor/composition/bootstrap.py`,
  `backend/src/agentmonitor/composition/operations_health.py`, and affected
  `backend/src/agentmonitor/api/v1/**` surfaces.
- Platform/runtime:
  `backend/src/agentmonitor/adapters/platform/linux/processes.py` and
  `backend/src/agentmonitor/composition/linux_process_locations.py`.
- UI/generated client:
  `frontend/src/features/accounts/**`, affected quota/overview presentation,
  `frontend/src/features/alerts/AlertsPage.tsx`,
  `frontend/src/features/alerts/alertPresentation.ts`,
  `frontend/src/shared/api/client.ts`, and `frontend/src/generated/api/index.ts`.
- Plan 1.8.0 P02 correction:
  `frontend/src/app/DashboardApp.tsx`, `frontend/src/app/dashboard.css`,
  `frontend/src/features/auth/PasswordChangePanel.tsx`,
  `frontend/tests/browser/p02/password_change.mjs`,
  `frontend/tests/browser/p02/responsive.mjs`,
  `frontend/tests/browser/p02/revocation.mjs`,
  `frontend/tests/browser/p02/run_browser.py`, and
  `frontend/tests/browser/p02/test_run_browser_policy.py`.
- Plan 1.9.0 focused correction:
  `tools/automation/implementations/m5_codex_quota_witness.py`,
  `tools/automation/test_m5_codex_quota_witness.py`,
  `tools/automation/implementations/m5_service_activation.py`,
  `tools/automation/test_m5_service_activation.py`, and
  `tools/automation/routines.toml`.
- Plan 1.10.0 through 1.13.0 focused corrections:
  `tools/automation/implementations/m5_codex_containment.py`,
  `tools/automation/test_m5_codex_containment.py`,
  `tools/automation/implementations/auto_m5_current_exit.py`, and
  `tools/automation/test_m5_current_exit.py`. Effective-root, inode-bound
  metadata, complete trace, mount topology, descriptor-bound `ftruncate`,
  numeric-dirfd `unlinkat`, and process-group cleanup coverage are local Green.
  The exact Story inventory is `526` identifiers with SHA-256
  `5b3c8dcbdcdff7303e7364417b6d7d5c6bd4efd3286fba48ba885bcf0bdd968e`.
- Tests:
  Codex adapter, Registry, Collection, Capacity, Alerting, API, Operations,
  Linux runtime, release, client, pure UI, and built-browser suites under
  `backend/tests/**` and `frontend/tests/**`.
- Automation:
  `tools/automation/implementations/m5_*`,
  `tools/automation/implementations/auto_m5_current_exit.py`,
  `tools/automation/test_m5_*`, `tools/automation/routines.toml`,
  `tools/automation/run.py`, and shared M5 browser Registry-page helpers.
- Documentation: the approved M5 plan, React dashboard module, Codex
  discovery/correction evidence, Codex adapter guide,
  operations/completion-gate documentation, implementation-status overlay,
  README, and this file.

## Integrity declaration

No mock, fake, stub, emulator, response recording/replay, demo account, seeded
telemetry, placeholder UI value, hardcoded test pass, disabled assertion,
test-only production branch, or swallowed failure is credited as evidence.
Constructed values appear only in closed pure policy tests. SQLite, HTTP,
browser, filesystem, subprocess, Linux, and provider claims above use their
real stated boundary. Skipped owner-live selectors remain Blocked.

## 2026-10-16 historical preactivation service-transition finding

Before the first M5 activation, the working persistent dashboard was served
from the extracted runtime for revision
`77a3bad12a096a81587b94b8981ceee812b6445b`, which remains the trusted rollback
baseline. That extracted tree does not carry the Git metadata used by startup's
clean-source check, so its versioned Operations inventory truthfully exposed
`source_revision` as unknown. At that checkpoint it could not satisfy the
revision/service binding required by
`AUTO-M5-OWNER-OUTCOMES`, the quota and alert witnesses, or `AUTO-M5-EXIT`,
even though ordinary dashboard availability is healthy.

The approved focused plan 1.4.0 now authorizes the narrow
`AUTO-M5-SERVICE-ACTIVATE` prerequisite coordinator under an explicit bounded
PLAN-DEP/D01 ownership exception. PLAN-DEP remains `0.2.0-draft`, its proposed
public contract is unchanged, and the exception supplies no general deployment
authority. The intended result is a real user-service process running from the
same detached, clean, committed Git worktree that will execute the M5 gate,
with Operations reporting that exact revision. Every prerequisite and exit
write boundary must revalidate the detached clean HEAD and selected
service/source binding. The transition preserves the existing data,
configuration, network and provider tool selections, changes the candidate
stop timeout from 30 to the already approved 45-second drain bound, and keeps
the trusted extracted runtime and exact old unit available for verified
automatic rollback.

The coordinator is now implemented and cataloged as `operational_limited`.
Its initial suite was Red with `16 failed, 1 passed`. Subsequent focused Reds
proved missing inactive-transition recovery, partial-journal recovery,
detached-worktree enforcement, prerequisite and exit service/source binding,
the M5-only detached Git preflight, and rollback-runtime checkpoint ordering.
The activation behavior suite initially returned `19 passed`. Before final
review, the combined activation, prerequisite, preflight, exit, and mandatory
no-selector behavior returned `151 passed in 15.53s`. After the corrections
described below, the same combined selection returned `162 passed in 16.33s`.
The later final-lock and receipt-custody corrections brought that selection to
`170 passed in 49.19s`; the interruption-safe finalization corrections brought
that focused checkpoint to 175 cases. The exact M5 story inventory is now
468 cases with digest
`0a11e798f8811b51d59bcd2babdabc1e0f6a738b5428d5fb1a04b699bea9b9c9`.
Strict targeted mypy, Ruff, JavaScript syntax, documentation validation, and
the read-only trusted-service status check passed. Those were the preactivation
results at that checkpoint; no prerequisite was archived or recollected, no
provider/profile operation was performed for that local Green, and no M5 gate
or acceptance state changed.

The first real `AUTO-M5-SERVICE-ACTIVATE` execution then completed its rollback
drill and selected the detached candidate revision
`6bfa69dc13cc9e1ded9c6baa6e803cb99bc8c20b`. Real HTTP, authenticated browser,
unchanged Registry, current Operations source revision, systemd process
identity, and retained trusted rollback material passed for that transition.
The following canonical prerequisite-archive attempt returned
`m5_prerequisite_archive_lock_unavailable` because the ignored
`.agentmonitor-local` receipt directory did not yet exist. Independent review
also found that final exit validation retained the receipt inode but did not
recheck that its canonical directory entry still named that inode after the
last service and lock checks.

Plan 1.4.0 and the correction implement one exact evidence-preserving rollover
for that completed `6bfa69d` transition, safe first-use creation of only the
approved private receipt directory, and the final descriptor-relative receipt
entry check. The historical activation pass remains evidence of that exact
revision only. At that preactivation checkpoint the corrective rollover, its
required status-5 rerun, and the corrected revision's activation were **Not
Run**. `AUTO-M5-EXIT` remains **Not Run**.

The corrective-rollover Red first returned four failures for the absent
rollover behavior and one failure for the absent completed-material validator.
Its initial Green brought the activation file to 37 passing cases. Retry review
then found that a process interruption after the corrected journal was written
would leave a nonempty fresh transition root that the next invocation rejected
before the existing recovery policy could run. Two real-filesystem regressions
failed because the retry-state validator did not exist. The narrow Green accepts
only an empty root or the exact owner-only journal/rollback subsets, binds any
partial material to the trusted unit, and lets an unreceipted candidate enter
the existing verified rollback path; unexpected content still blocks. The full
activation file returned `41 passed`. A further real-filesystem Red showed that
a different preexisting archive entry was not rejected before the source move.
The Green requires the archive parent to be empty before mutation, rechecks it
immediately before the atomic rename, and requires the exact singleton after
the move while leaving any preexisting entry and source unchanged. The full
activation file then returned `42 passed`; targeted Ruff/format and strict
production mypy passed, and no live service state was touched by these local
checks.

The first corrective-rollover invocation from clean revision `272e9e4`
validated the completed prior transition and restored the pinned `77a3bad`
runtime, then blocked with `m5_service_browser_unavailable` before archiving
the old evidence. The dashboard remained active with loopback HTTP `200`, all
three original private transition artifacts remained in place, and no
corrective archive existed. Direct authenticated browser proof showed the
cause: the extracted trusted runtime correctly exposes `source_revision` as
unknown, while the correction had mistakenly requested candidate-mode exact
revision proof after rollback. The proof-mode Red failed because the policy
boundary did not exist. The Green selects exact revision proof for the prior
Git candidate and baseline authenticated Registry proof for only the pinned
extracted rollback runtime; exact rollback trust continues to come from the
unit bytes, systemd process identity, and retained runtime digest. The full
activation file returned `43 passed`, with targeted Ruff/format and strict
production mypy Green. The restored state is safe for the canonical retry; no
rollover archive or corrected activation pass is claimed at this checkpoint.

Final review then exposed a same-service concurrency gap: once the private
journal and rollback unit both existed, a second activation process could reuse
them and enter the same stop/install/rollback sequence. The real-process lock
test first failed with one expected failure because
`acquire_m5_service_activation_lock_v1` did not exist. The minimal Green uses a
fixed owner-only transition directory, an abstract Unix-socket guard, and a
nonblocking directory `flock`; it detects competing processes and directory
identity or mode replacement. `_activate` acquires that cross-checkout guard
before any transition/recovery inspection and releases it only after success or
rollback. The focused contention case returned `1 passed in 0.11s`; the full
activation file returned `21 passed in 0.71s` at that checkpoint, and targeted
Ruff and strict mypy passed. These local results do not claim the live service
transition ran.

Final gate review then found that `AUTO-M5-EXIT` did not consume the successful
activation and rollback-drill receipt. The receipt-binding Red failed because
`validate_current_activation_receipt_v1` did not exist. The Green validates
the current candidate unit and systemd ownership, canonical activation
receipt, journal, exact rollback unit, pinned rollback-runtime tree, and their
content digests. The exit command now holds the same fixed service-transition
lock from before live selection through receipt creation, records the
activation-receipt digest and required `service_activation` lane, and
revalidates that receipt plus the service-transition and completion locks
before writing the final receipt. Six focused receipt cases passed; the final
activation file returned `27 passed`.

The exit cleanup review produced a separate Red when the typed result selector
was absent. The Green converts transition-lock release failure to one sanitized
failure, preserves an already selected Blocked or Failed body result, reports
the first cleanup failure only when the body otherwise succeeded, and still
attempts both lock releases. The focused service/exit files returned
`83 passed`; targeted Ruff and strict mypy passed.

A final fail-closed review exposed two later-boundary defects. In service
activation, a final transition-lock custody failure bypassed rollback and lock
cleanup could obscure the distinct rollback-failed result. The focused Red was
`2 failed in 1.16s`; the Green was `2 passed in 0.13s`. A second activation Red
showed that a short create-once write left its receipt and cleanup failure was
not visible (`2 failed in 0.17s`); the Green was `2 passed in 0.24s`. Final lock
failure now enters the same verified rollback policy, rollback failure retains
priority, every partial receipt write attempts exact-inode cleanup, and cleanup
failure is typed. The complete activation file returned `31 passed`.

The final-exit review separately proved that a parent-directory swap could
leave the exact newly created pass receipt after the command reported failure.
The first Red could not import the absent cleanup helper; after its initial
implementation, the real parent-swap Red still failed because the displaced
receipt remained. The Green creates, validates, invalidates, and conditionally
unlinks through one retained directory descriptor, retains an open descriptor
to the created receipt through both lock releases, truncates that exact inode
before cleanup, and unlinks only an unchanged regular owner file with mode
`0600`, one link, and the expected device and inode. Replacements remain
untouched and body or rollback failures retain priority over cleanup failures.
Five focused custody cases returned `5 passed in 2.77s`; the complete exit file
returned `60 passed in 2.98s`. The final combined focused selection returned
`170 passed in 49.19s`; targeted Ruff and strict mypy passed.

The last bounded control-flow review found that an interruption after receipt
creation could bypass main-level invalidation, the original guards were
released before a known-failed receipt was removed, and the writer ignored a
failed exact-inode invalidation. The first three-case Red returned `3 failed in
0.35s`; the explicit interruption-policy Red and post-write interruption Red
each failed because their cleanup helpers were absent. The Green captures every
post-write `BaseException`, invalidates before releasing the original guards,
retains duplicate abstract-socket guard descriptors through any release-failure
retry, reports failed invalidation explicitly, and then preserves the primary
interruption or typed body result. All fault injection uses real owner-only
directories, files, descriptors, processes, signals, and kernel guards. The
five new cases independently returned `5 passed in 0.56s`; the complete exit
file returned `65 passed in 4.51s`; and the exact final focused selection
returned `175 passed in 15.00s`. The bounded independent re-review found no
remaining blocker.

The exact JUnit inventory exposed a path-normalization Red: all selected
`tools/git/test_preflight.py` cases were rejected even though the canonical
story selection required them. The focused regression first failed with
`m5_current_story_report_invalid`; the narrow Green admits only that exact Git
test path while continuing to reject neighboring `tools/git` files. The same
test then passed. Independent parsing of the final canonical JUnit report
confirmed 468 unique identifiers and the pinned digest above; the production
inventory validator accepted both before returning the expected
`m5_current_story_suite_skipped` for the no-selector local run. This is
inventory evidence, not a live Story-suite pass. The inventory-producing run
reported `461 passed, 6 skipped, 1 failed` with the admitted Claude and Codex
tool paths selected. The one failure was the intentionally absent M5 owner
installation selector. None of the six owner-live skips is credited as a pass.

That inventory run also exposed eight archive-policy failures because a fixed
test-only owner-confirmation date had aged beyond the unchanged eight-day
production validity bound. The Green captures current UTC once per archive
test module and expresses all freshness cases relative to it; it does not
widen production validity. The complete archive file returned `17 passed in
0.43s`, and that checkpoint's combined focused selection returned `162 passed
in 16.33s`.

The detached-service requirement exposed a separate deterministic gate Red:
`AUTO-M5-EXIT` requires the checkout to remain detached, but its generic
`AUTO-GIT-PREFLIGHT` lane required an attached branch. The new real-worktree
tests first returned `2 failed, 3 passed in 0.28s`: the generic command accepted
an attached checkout despite the M5 selector and ignored an invalid selector.
The minimal Green adds the M5-only
`AGENTMONITOR_M5_DETACHED_GIT_PREFLIGHT=1` commit-preflight path. It requires
the exact root, a detached `HEAD`, one unchanged lowercase 40-hex commit, and
empty tracked and untracked status; it rejects attached/dirty state, invalid
selector values, push, and release. Ordinary Git preflight behavior retains
its branch requirement. The focused real-Git suite returned `5 passed in
0.45s`; Ruff passed and mypy reported no issues in the two changed Git
preflight files. This local Green does not claim the M5 live gate passed.

The later canonical retry completed both required invocations. The first
restored and proved the pinned trusted runtime, atomically moved the complete
`6bfa69d` transition into the owner-only corrective archive, created the fresh
transition root, and returned the typed rerun-required result. The second
completed the real rollback drill and activated exact clean detached revision
`063445154bca0bf5ec43db94ba57c17fd193fd99`. The selected systemd process,
loopback and LAN HTTP, authenticated browser, exact Operations source revision,
unchanged complete Registry, retained rollback runtime, archive singleton, and
new owner-only transition artifacts all passed their stated checks. The
separate prerequisite archive also passed for its stale predecessor artifact.

`AUTO-M5-OWNER-OUTCOMES` subsequently passed against the same revision and
service in sanitized aggregate form: four total outcomes, three verified and
one owner-unavailable. The private artifact records the owner facts; this
public evidence retains no aliases, opaque account IDs, private values, or
artifact digest. It is not quota evidence or milestone acceptance.

The approved second rollover then completed both required invocations. It
preserved the complete `0634451` transition below the fixed
`m5-service-activation-corrective-archive-0634451` parent without changing the
first archive, and the rerun activated exact clean detached revision
`6d6e1aa9d9b64d50e3f83d0f1686e6cff04b7c17`. Its bounded activation proof and
the later current-window/history lineage results are recorded above. The stale
owner prerequisite was preserved canonically, and `AUTO-M5-OWNER-OUTCOMES`
passed again against `6d6e1aa` with four total outcomes: three verified and one
owner-unavailable.

The approved third rollover subsequently preserved that transition and
activated exact `e066d7e`. Its stale prerequisite was archived canonically,
and `AUTO-M5-OWNER-OUTCOMES` passed again for the new service with four total
outcomes: three verified and one owner-unavailable. At that checkpoint, the
approved fourth rollover would make the revision/service-bound prerequisite
stale and require the same canonical preservation and recollection workflow;
the later completed d81 transition and refreshed evidence are recorded above.

## Plan 1.11–1.12 local containment checkpoint

The approved 1.11 implementation began with real and pure Reds for inode-bound
provider `chmod`, child PID parsing, lexical and shared working directories,
quoted-dirfd spoofing, `CLONE_UNTRACED`, global link and mutator attribution,
private-channel outcomes, and duplicate JSON members. The approved 1.12 review
then reproduced successful fd xattr, inode-flag ioctl, and io_uring mutations
that the prior exact selector did not expose. All real probes used temporary
owner-controlled files and restored or removed their changes.

The Green uses the exact expanded root-owned strace selector and raw qualifier.
It rejects all successful raw calls globally, treats only exact negative errno
results as no effect, keeps those failed records in process chronology, and
rejects malformed results. Real trace proof exposes neither the private xattr
name/value nor decoded ioctl buffers. The complete containment file passed
`64` cases and `202` subtests with one authenticated live case explicitly
skipped because live selectors were absent. The current-exit file passed `66`
cases. Ruff lint/format, strict production mypy, and diff checks passed.
Independent review found and the implementation corrected the final raw-result
grammar and post-exit chronology gaps.

The canonical M5 Story inventory was collected without executing provider
operations: `514/514` unique normalized identifiers, digest
`fd9c6c87d07e1ab759a2a2db23c8d6cd3997d416687784e4c13525ac8e2cf1bd`,
and no collection errors. This is inventory evidence, not a full live Story
suite pass. No service, browser, provider profile, account, or running agent
was changed during this local checkpoint. Canonical preactivation and the
standalone authenticated containment case against the unchanged d81 service
remain required before the fifth rollover.

## Plan 1.13 local containment checkpoint

Focused Reds exposed malformed or missing descriptor-result precedence,
noncanonical and control-bearing mount rows, missing traced-process start
binding, and an exited group leader with a live descendant. Green now parses
and counts only exact descriptor-bound `ftruncate`; validates every mountinfo
row with bounded pseudo roots only for `nsfs`; binds current and traced-driver
`/proc` snapshots to PID/start identity; and owns the new-session leader by
pidfd so its process group is signalled before reaping under the single shared
settlement deadline. Real inherited-descriptor, temporary-file, `/proc`, bind-
mount, and exited-leader/live-descendant cases cover those Linux boundaries.

The complete containment file reports `Ran 76`, `OK (skipped=1)`; the sole
skip is the authenticated live-selector case. Current-exit passes `66`; Ruff
lint and format, strict production mypy, and `git diff --check` pass. Two
independent final reviews are clean. The exact Story inventory is `525` unique
identifiers with SHA-256
`99c3b5f579aac5091939209c8f3603f88a283bb3a4444dbdfa10f8f1d91de15f`.
No service, browser, provider profile, account, or running agent changed during
this local checkpoint. At that checkpoint authenticated containment, canonical
preactivation, fifth activation, refreshed witnesses, and `AUTO-M5-EXIT` were
Not Run.

## Plan 1.13 authenticated dirfd trace Red and local correction

Clean revision `87eb40dc3975766955091c398075093aafe5f6a9` passed planning,
documentation, build, quality, mutation, M3 regression, full local test, and
Git preflight routines. The standalone authenticated containment run against
the unchanged `d81afab` service then completed the real production identity and
quota operations before trace policy returned
`m5_codex_containment_trace_invalid`. No containment receipt was written.

Sanitized in-memory diagnosis retained no path or provider value. It identified
one successful write-class `unlinkat`, one quoted relative target, one required
numeric annotated directory descriptor, and zero `AT_FDCWD` tokens. A separate
real owner-temporary-file probe reproduced strace 6.8's exact structural form
as `unlinkat(3<ABS>, "REL", 0) = 0`. No service, browser, Registry row, default
provider profile, or ordinary running agent was manually changed.

The Red pure policy and real temporary-filesystem tests both failed with the
same invalid-trace code. Green at
`f1c2c2e9a7f4434c49014646bff220273282603b` parses only exact `unlinkat`
signatures and resolves relative targets from tracked `AT_FDCWD` or a canonical
absolute numeric-dirfd annotation. Missing, deleted, relative, noncanonical,
control-bearing, escaped, traversal, malformed-result, default-profile,
outside-profile, and protected-target cases remain closed with their specific
sanitized failures. Unrelated numeric-dirfd syscall shapes remain unresolved.

The complete containment file now reports `Ran 77`, `OK (skipped=1)`: `76`
local passes and the one authenticated selector skip. Current-exit passes
`66/66`. Ruff and formatting for the changed containment files, strict
production mypy, and `git diff --check` pass. Two independent final reviews are
clean. Exact provider-free collection reports `526` unique Story identifiers
with SHA-256
`5b3c8dcbdcdff7303e7364417b6d7d5c6bd4efd3286fba48ba885bcf0bdd968e`;
removing only the new real-strace test reproduces the previous `525` count and
digest. These local results do not pass authenticated containment. The full
preactivation set and standalone authenticated run must execute again on the
current clean candidate before activation.

## Plan 1.14 Arg0 lifecycle Reds and local implementation checkpoints

Clean revision `a0f2dc16e2330c048d652845f20b2585bcf64c5e` passed the
complete preactivation set. Its standalone authenticated containment run then
completed real identity and quota operations against the unchanged `d81afab`
service and failed closed as
`m5_codex_containment_link_operation_rejected`. Privacy-safe classification
proved that each operation's root PID created the same exact ordered aliases:

1. `apply_patch`;
2. `applypatch`;
3. `codex-linux-sandbox`; and
4. `codex-execve-wrapper`.

Every link payload was the retained, inode-validated pinned Codex executable;
each created path was below one canonical managed
`tmp/arg0/codex-arg0XXXXXX` session; and every alias had a later matching
successful cleanup. Identity and quota therefore produced four links each.
The post-run managed tree contained no symlink, and the observation retained
no path, payload, provider response, identity, credential, prompt, response,
or source content. The authenticated failure and the first exact four-plus-four
policy test supplied Red evidence for the approved 1.14 behavior.

The local Green parses plain `symlink` direction exactly, records physical
invocation and completion chronology for complete and unfinished/resumed
syscalls, and admits only that four-alias lifecycle in each operation root.
Every admitted link requires one same-operation cleanup before actual operation
closure. Namespace movement or exchange remains forbidden from first creation
invocation through closure, including while descendants remain live. Optional
ordinary removal of an empty symlink-free session directory follows all four
cleanups; every other link operation and every retained final-tree symlink
still fails closed. The evidence schema and sanitized aggregate output are
unchanged.

Focused regression coverage includes grammar and cardinality, source and
destination confinement including double-leading-slash rejection in syscall
arguments and successful-open descriptor annotations, root and descendant
lineage, operation overlap and reuse, cleanup matching and descriptor
resolution, physical completion across
exit and following-provider boundaries, namespace movement before the first
creation completes and after a root exits, a cwd-dependent relative movement
overlapping an unfinished `chdir` in the same tracked `CLONE_FS` group,
unambiguous absolute and post-completion path use, optional directory removal,
unowned overlapping writes through `/proc/*/root` lexical aliases, and a real
owner-temporary-filesystem `strace -yy` direction/cleanup case. At clean
checkpoint `842a4d4`, the complete containment file reported `Ran 88`,
`OK (skipped=1)`: `87` local passes and the one authenticated live-selector
skip. Current-exit passed `66/66`; Ruff lint and format and strict production
mypy were Green. Exact provider-free inventory reported `537` unique Story
identifiers with SHA-256
`19d4244cfd50335839776af9b847af134eba0451c3dee2ad66d0daa9e321ec2d`.
That was inventory evidence and did not claim a full Story-suite pass.

Clean revision `842a4d4da20b1286d4d68b03b46f88a9cd66504e` passed the complete
preactivation set: planning, documentation, build, quality, mutation, M3
regression, full local test, and Git preflight. Its authenticated containment
run against unchanged service `d81afab` then completed real identity and quota
operations and failed closed as
`m5_codex_containment_path_mutator_unverifiable`. No receipt was written.

Privacy-safe diagnosis found one same-operation descendant's exact
`mkdir(...)= -1 EEXIST` against the already-existing Arg0 session ancestry.
It occurred after an alias creation had completed and before any alias cleanup,
operation-root exit, or actor exit. The pure policy case first failed at the
validator. The narrow Green accepts only that well-formed failed directory
create within the protected interval. A paired failed-`rename` regression
remains rejected because a reported rename failure does not prove that no
filesystem effect occurred. The complete containment file now reports
`Ran 89`, `OK (skipped=1)`: `88` provider-free passes and the one authenticated
selector skip. Current-exit remains `66/66`. Exact provider-free inventory now
reports `538` unique Story identifiers with SHA-256
`3dcf68e402a40e7e48f46494d4e35778f9e4bb85a7a6cb0cb00183495bd64223`.

A second authenticated feedback run completed both real provider operations
and still failed closed as
`m5_codex_containment_path_mutator_unverifiable`. No receipt was written. Safe
diagnosis matched the official Codex `0.160.0` Arg0 regular `.lock` child. The
[official `rust-v0.160.0` Arg0 source](https://github.com/openai/codex/blob/rust-v0.160.0/codex-rs/arg0/src/lib.rs#L22-L45)
defines that literal child. A bounded sanitized rerun verified the same exact
shape and cardinality for identity and quota: each operation root successfully
opened literal `session/.lock` exactly once before the first alias with flags
`O_RDWR|O_CREAT|O_LARGEFILE|O_CLOEXEC`, mode `0666`, and a successful
annotated descriptor. A same-operation descendant later completed exactly one
matching `unlinkat` through the annotated session directory descriptor, with
literal `.lock`, flags `0`, and result `0`. In each operation, that cleanup was
interleaved after three alias cleanups and before the fourth, and preceded
process and operation exits. The diagnostic trace was discarded. No selected
`flock` or `fcntl` call was observed, so this record makes no advisory-lock
proof claim.

The regular `.lock` lifecycle is outside approved plan 1.14 and is not
implemented or admitted by this checkpoint. No service, browser, Registry row,
provider profile, default profile, account, or ordinary running agent changed
during the local corrections and safe diagnosis. They change no public API or
provider contract, database schema or migration, dependency or license
surface, service configuration, or UI. Authenticated containment has no pass;
no fifth activation or M5 completion follows from these results.

## Plan 1.15 lock lifecycle implementation and authenticated feedback

The owner approved focused plan `1.15.0` on 2026-10-22. The first focused
policy test reproduced the prior real
`m5_codex_containment_path_mutator_unverifiable` result for the exact successful
`.lock` cleanup before production policy changed. Implementation and review then
closed the exact plan boundary: one successful root session `mkdir`, one root
regular `.lock` open, four ordered aliases, five same-operation child cleanups
in any valid child order, and optional empty-session removal for identity and
quota independently. The validator retains physical invocation and completion
chronology, descriptor/path alias controls, managed-root confinement,
default-profile prohibition, and the closed digest-only evidence schema.

The first frozen offline result was:

- containment: `96 passed, 1 skipped`, with `552` subtests; the skipped case
  required authenticated live selectors and received no pass credit;
- current-exit: `66 passed`;
- exact Story inventory: `546` identifiers with SHA-256
  `49178f121728490692228d2b0c83e0f4ed99b7da42f7c43d39191a227dfa41ba`;
- Ruff lint/format, strict production mypy, and `git diff --check`: Green; and
- two independent pre-live reviews: CLEAN after every review finding had first
  been reproduced as a focused Red and corrected.

The first authenticated 1.15 feedback run used the unchanged d81 service and
pinned Codex `0.160.0`. Identity and quota reached the line guard, which failed
closed because two broad guards still began at app-server execution. A bounded
privacy-safe in-memory classification retained only structural cardinality,
call, mode, result, and chronology. It found that before the exact session
`mkdir`, the official Arg0 implementation attempted
`mkdir(arg0_root, 0777)`, received `EEXIST`, and then performed the already
approved `chmod(arg0_root, 0700)`. No path, PID, account identity, profile,
provider payload, credential, prompt, response, source content, arbitrary
environment value, or raw trace was retained.

A focused test for that exact pre-session shape failed before the correction.
The production correction does not exempt the two calls from ordinary
confinement. It moves the two broad Arg0 guards to their planned closed
interval: exact session-`mkdir` invocation through completion of the final
fifth-child cleanup. Negative calls invoked within or crossing that interval
remain rejected. The official root setup completes before the interval and
does not satisfy or replace any session, lock, alias, cleanup, or final-tree
requirement.

The corrected local result is `97 passed, 1 skipped` across `558` subtests;
the live-selector skip remains uncredited. Current-exit remains `66/66`, and
Ruff lint/format, strict production mypy, and `git diff --check` are Green. The
exact Story inventory is now `547` identifiers with SHA-256
`3a97e0103ae4ba3390d10567c9130821abaa7a5a7e9640cf0091bc56a49b6a0c`.
Removing only the new focused case reproduces the initial `546`-identifier
inventory and digest. The focused post-correction official-source and code
reviews were CLEAN.

The authenticated feedback rerun passed with zero skips: `1 passed in 3.79s`
against the unchanged d81 service and pinned Codex `0.160.0`. The run proves
the complete approved lifecycle for the real identity and quota operations at
this feedback boundary. It does not bind a committed clean candidate, activate
the fifth service revision, refresh service-bound prerequisites, create the
quota or final completion receipt, or accept M5.

## Plan 1.15 exact-revision activation and alert-witness failure

The final plan 1.15 implementation was committed as exact clean revision
`8cc683d946b58f5eb72955e08a520195582e1a28`. Its complete preactivation set
passed, and the standalone authenticated containment rerun returned
`1 passed in 4.03s` with zero skips against pinned Codex `0.160.0`. The
two-stage fifth corrective activation then passed and made that revision the
receipt-bound live service. The dashboard returned HTTP 200.

Fresh service-bound `AUTO-M5-OWNER-OUTCOMES` passed with three verified records
and one owner-unavailable record. A genuine post-confirmation alert opening,
distinct repeat, owner acknowledgement, and recovery also passed.

The first read-only `AUTO-M5-ALERT-WITNESS` run exposed a quadratic source-event
proof: the complete capacity outbox exceeded `36,000` events, and receipt JSON
was scanned for every decoded event. It remained CPU-active for more than
eleven minutes and was interrupted before create-once output; no witness file
existed afterward. The unchanged canonical rerun completed the database proof
and reached the browser, then failed closed as
`selected_alert_history_not_rendered`, surfaced as
`m5_alert_witness_browser_unavailable`. The versioned API returned all `192`
selected-alert history entries while the built page rendered only `100`. No
alert witness or completion receipt was created.

Owner-approved plan 1.16.0 contains only the bounded exact-ID acknowledged-event
lookup, complete cursor-paginated Alerts history and browser proof, and one
exact sixth evidence-preserving rollover.

## Data and secret review

This document contains no secret, provider response, account identity, private
profile path, process identifier, prompt, response, source-code content from a
provider session, or arbitrary environment value. Private outcome, quota,
alert, profile, and completion artifacts remain outside the repository and are
represented here only by sanitized result counts or public digests.

## Conclusion and residual gaps

The approved plan 1.15 implementation is active at exact clean revision
`8cc683d946b58f5eb72955e08a520195582e1a28`. Complete preactivation,
zero-skip authenticated containment, the fifth evidence-preserving rollover,
fresh four-account owner outcomes, and a genuine current alert lifecycle all
passed. This establishes substantial implementation and operational progress;
it does not establish M5 completion.

No current alert witness, quota witness, or M5 completion receipt exists. The
alert-witness attempt exposed two bounded implementation defects: quadratic
whole-outbox acknowledgement lookup and single-page Alerts rendering. Owner-
approved plan 1.16.0 addresses only those defects and the exact rollover needed
to bind new evidence to the corrected revision. It remains unimplemented.

Before any completion or acceptance claim, the integration owner must:

1. implement plan 1.16.0's exact bounded lookup, paginated UI/browser proof,
   and sixth
   activation policy through Red, Green, refactor, full canonical preactivation,
   and independent review on one clean candidate;
2. perform exactly one two-stage sixth rollover from `8cc683d`, preserving and
   revalidating all five existing archives;
3. archive the stale service-bound prerequisites and recreate current owner
   outcomes and one genuine alert opening or reopening, repeat, owner action,
   and source-proven recovery;
4. pass `AUTO-M5-ALERT-WITNESS` and create its private revision-bound witness;
5. reconcile every verified account with fresh official Codex `/status`,
   current collection, API/DOM values, and retained history through corrected
   `AUTO-M5-QUOTA-WITNESS`;
6. verify five to six representative external Codex processes without account
   guessing or process control;
7. run authenticated syscall containment for identity and quota with zero
   default-profile access or write; and
8. run `python3 tools/automation/run.py AUTO-M5-EXIT` with zero skips, retain
   its private create-once exact-revision receipt, and present that exact result
   for owner review.

Until those steps pass, M5 remains **Intermediate**, unavailable live scenarios
remain **Blocked** or **Not Run**, and the canonical completion gate remains
**Not Run**.
