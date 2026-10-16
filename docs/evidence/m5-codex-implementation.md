# Test evidence: V1-M5 Codex implementation

- Evidence ID: `M5-CDX-IMPLEMENTATION-2026-10-08`
- Module/plan/increment: A02 Codex provider adapter and root-owned V1-M5
  integration, approved focused plan version `1.4.0`, Stories
  `ST-CDX-001..005`.
- Requirements/acceptance IDs:
  `FR-ACC-001/004..006`, `FR-AUTH-001/002/004..006`,
  `FR-QUOTA-001..006`, `FR-COL-003..008`, `FR-HIST-001/002`,
  `FR-DISC-001/003/004/006/008`, `FR-STATE-001/002`, `FR-SAFE-002`,
  `FR-ALERT-002..006`, `FR-UI-001..006`, `NFR-API-001/002`,
  `NFR-TEST-001/002`, `NFR-SEC-001`, `NFR-PRIV-001/002`,
  `NFR-RES-001`, `NFR-OBS-001`, `NFR-COMP-001`, `NFR-DOC-001`;
  M5 contributions to `AC-LIVE-002/004/005/007`, `AC-UI-002/005/006`,
  `AC-PROC-001..004`, `AC-HIST-001`, `AC-ALERT-002`,
  `AC-OPS-003/006`, and `AC-TEST-001..006`.
- Contract versions: compatible V1 use of `CTR-PROV-001..008`,
  `CTR-REG-001/002/004/005/006/009/010`,
  `CTR-COL-002/004/006/007`, `CTR-CAP-001/003/004/007/008/009`,
  `CTR-RUN-001/002/003/006/007`, `CTR-PLAT-001`,
  `CTR-OPS-004/006`, `CTR-ALERT-001..005`, `CTR-EVT-001`,
  `CTR-API-001`, and `CTR-UI-001`; `ProviderAdapterV1`
  `1.0.0-draft.2`; `codex-adapter.v1` adapter `1.0.2`; Codex
  subscription capability schema `1.0`; REST `/api/v1`; database head
  `v1_0707` unchanged.
- Commit/worktree reference: retained quota-history pagination is committed at
  `d7b8b9b6af9eabd584257919947d341f6df5fa93`; the alert occurrence retry is
  carried by the revision containing this record. No clean revision has passed
  the canonical M5 gate.
- Recorder/date: Codex integration record, 2026-10-08; retained-history retry
  update, 2026-10-09; exact-revision transition and concurrency update,
  2026-10-16.
- Overall status: **Intermediate**. The canonical `AUTO-M5-EXIT` has not passed;
  its preflight was **Blocked** and no completion receipt exists. Final owner
  review is **Not Run**. This record is not milestone acceptance.

The primary production owner is A02 for provider behavior under
`backend/src/agentmonitor/adapters/providers/codex/**`. Root integration owns
composition, Registry/Collection/Capacity/Runtime/Alerting coordination, API,
UI, automation, and live closure. The focused approved plan is
[the executable V1-M5 Codex slice](../plans/integration/m5-codex-slice-change.md).

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
| `M5-CDX-GATE-001` admission/containment policy | Linux/platform/provider | Real installed executable and schema; real OS pipes, file descriptors and process tracing | Passed | `28` unittest cases: `27` passed and one live-selector skip | The skipped authenticated containment scenario is Blocked, not Passed. |
| `M5-CDX-UI` account beyond first page | DB/API/browser | Real migrated file SQLite, production HTTP/API, generated client path, production frontend, Chrome | Passed | `account_beyond_page` browser scenario | This focused UI behavior passed: it creates 201 real account records, uses the visible **Load more accounts** control, and opens the last account through a generated detail GET. Other UI scenarios remain subject to the canonical gate. |
| `M5-CDX-UI` mixed-provider Overview filter | API/built browser | Authenticated real owner service, genuine Claude and Codex Registry rows, production frontend, shared Chrome | Passed for the focused increment | `AUTO-DASHBOARD-PROVIDER-FILTER` and [Overview evidence](dashboard-density-and-quota-overview.md#mixed-provider-selection--2026-10-11) | Claude-only, Codex-only, all-provider reset, organization composition, keyboard use, manual/periodic refresh retention, 1920/1280/390 reflow, filtered counts, and zero mutations passed. This does not close the canonical M5 gate. |
| `M5-CDX-ALERT-001` complete Registry scope | Pure policy and DB integration | Real migrated file SQLite, production Registry commands, exact Codex installation reconciliation, 201 accounts | Passed | Three focused tests; full file `8 passed, 3 skipped` | Cursor progress and duplicate IDs fail closed; the target after page 200 resolves. Three owner-live selectors remain skipped. |
| `M5-CDX-ALERT-002` retained-history occurrence selection | Pure alert-witness policy | Production selector with constructed closed lifecycle values and no I/O | Passed | Meaningful Red and focused Green below | The latest `opened` or `reopened` occurrence must contain a distinct repeat, exactly one owner action, and exactly one later recovery. The combined focused run returned `19 passed, 3 skipped`; the owner-live skips are not credited as passes. |
| M5 Node story inventory | Pure UI/gate policy and source wiring | Production policy modules and browser entrypoint sources | Passed | `19 passed`, zero skipped | Includes configurable capacity-alert presentation and the alert and quota browser verifiers' use of shared complete page readers. This is a development-checkout result, not a live browser witness. |
| `AUTO-M3-TEST` dependency checkpoint | M3 contract and technical backend suites | Canonical routine on the development checkout | Passed | Two routine tests and `307` technical tests passed, zero skipped | Satisfies the local M3 dependency checkpoint; it does not establish an exact clean M5 revision. |
| `AUTO-MUTATION` checkpoint | Critical pure-policy mutation | Canonical routine on the development checkout | Passed | `1708` mutants: `1698` killed, `10` independently accepted equivalent, `0` skipped | No non-equivalent survivor was admitted. This remains subject to the final clean-revision M5 gate. |
| Quality, build, planning, documentation, and Git checkpoints | Static quality, generated artifacts/frontend build, repository validation, and local Git preflight | Canonical local routines on the development checkout | Passed | `AUTO-QUALITY`, `AUTO-BUILD`, `AUTO-PLAN-CHECK`, `AUTO-DOCS-CHECK`, and `AUTO-GIT-PREFLIGHT` exited zero | These individual checkpoints do not replace the unrun exact-revision `AUTO-M5-EXIT`. |
| Full M5 Python story selection before live setup | Backend and automation Story scope | Real local boundaries plus explicit owner/provider selectors | Blocked | The prior 386-case development-checkout run returned `379 passed, 6 skipped, 1 failed`; the real-filesystem archive race file separately returned `15 passed`. The current pinned inventory is 467 cases with digest `9945fa963f0f003aa2732614d9266ae22268ac3d6b67c8f4c08233fc3df6756a`. | The exact current JUnit inventory validator accepted all 467 unique IDs and this digest, then returned the expected `m5_current_story_suite_skipped` because the local inventory run lacked the required owner/live selectors. The expanded inventory includes service activation and receipt binding, corrective rollover and retry, archive-parent singleton custody, first-use completion locking, detached Git preflight, prerequisite service/source binding, transition serialization, interruption-safe cleanup, and the exact Git test path. No full 467-case zero-skip live execution is credited yet. |
| Full backend regression checkpoint | Backend regression | Real local test boundaries selected by the backend suite | Blocked | Historical pre-correction rerun: `10 failed, 1374 passed, 39 skipped` | Every reported failure was an explicit M4/LAN/M5 real-owner selector requirement. This historical result does not describe the corrected checkout. |
| `AC-LIVE-002/004` four selected Codex outcomes and live identities | Provider/account | Four real owner-selected Codex accounts or explicit owner-unavailable outcomes | Blocked | A four-row owner outcome file passed operationally for base revision `d7b8b9b`; it cannot bind a later alert-correction revision. | The exact outcomes need revision/service rebinding after the correction is committed; this row does not claim provider verification for the future revision. |
| `AC-LIVE-005`, `M5-CDX-COL/CAP` authoritative quota/history | Provider/DB/API/browser | Official Codex `/usage`, fresh scheduled observations, current and retained history | Blocked | One authenticated provider outcome normalized one primary window, but its capacity commit failed before persistence | Provenance admission and full-cadence interrupted-commit recovery are pure Green. A real retry must still prove commit, current/history lineage, exact whole percentages, reset precision, and at most 300-second skew. |
| `AC-PROC-001..004`, `M5-CDX-RUN-001..008` representative processes | Linux/platform/browser | Five to six real Codex processes outside the managed-profile subtree | Blocked | No current process witness | PID/start/executable reread, hierarchy/location, and unresolved or owner-confirmed association remain required. |
| `AC-ALERT-002`, `M5-CDX-ALERT-001..006` live lifecycle | DB/API/browser/provider | Genuine Codex capacity condition, fresh opening, repeated delivery, owner action, later source-proven recovery | Blocked | No current alert witness | Local DB pagination and retained-history selection policy passed; the fresh `opened` or `reopened` occurrence has not completed the real browser/provider witness. |
| Authenticated managed-profile syscall containment | Linux/provider/security | Real authenticated managed Codex profile and `strace` | Blocked | One truthful live-selector skip in the containment suite | Identity and quota operations must show provider access inside the selected root and zero default-profile access/write. |
| `M5-SVC-ACT-001..012`, `AUTO-M5-SERVICE-ACTIVATE` | Operations/service transition | Real user systemd manager, trusted persistent runtime, clean stable Git worktree, real HTTP and authenticated browser | Local correction Green; historical `6bfa69d` live Passed; corrected rollover/reactivation Not Run | Initial Red: `16 failed, 1 passed`; later targeted Reds covered inactive interruption, partial-journal recovery, detached Git, Operations binding, rollback-runtime checkpoint order, concurrent activation, activation-receipt consumption, final-lock rollback, and receipt cleanup. The first real rollback drill and activation passed at `6bfa69dc13cc9e1ded9c6baa6e803cb99bc8c20b`; the subsequent archive attempt and final-receipt review exposed the corrective gaps described below. | The bounded command is cataloged as `operational_limited`. The corrected detached revision must complete the typed corrective rollover and a second successful activation before new M5 prerequisites are collected. |
| `M5-CDX-GATE-001..014`, canonical `AUTO-M5-EXIT` | Full local/live gate | Clean exact revision, selected running service, prerequisite receipts, all local gates with zero skips | Not Run | Exit receipt binding, transition locking, interruption-safe exact-inode receipt invalidation, cleanup-result handling, and the combined 175-test focused selection are local Green. No canonical `AUTO-M5-EXIT` execution or M5 completion receipt exists. | Must run after every corrected prerequisite is current, then pass as the last technical gate before owner review. |
| macOS compatibility | Platform | Real macOS host | Blocked | No real Mac available | Outside Linux-first M5 acceptance; remains visible for V1. |

## Red evidence

No timestamp was retained for the recovered development runs below. Their
commands, failure outputs, and worktree context are preserved where available;
no time is inferred.

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
main M5 verifier and the official `/usage` reconciliation witness use this
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

  Result: `Ran 28`, `OK`, comprising 27 passes and one truthful authenticated
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
- `AUTO-BUILD` and `AUTO-PLAN-CHECK` exited zero at their
  development-checkout checkpoints. The latest `AUTO-DOCS-CHECK`, run after
  this reconciliation, passed all `305` Markdown files.
- `AUTO-QUALITY` passed formatting, Ruff, mypy across `370` source files,
  module boundaries, provider-schema generation, OpenAPI/client generation,
  frontend type checking, locked inputs, and the production frontend build.
- `AUTO-GIT-PREFLIGHT` passed its documented local-commit scope. Remote and
  upstream release readiness were not run and are not required for this local
  implementation commit.
- Before the retained-occurrence regression, the full M5 Python Story
  selection returned `379 passed`, six truthful live-selector skips, and one
  explicit `BLOCKED: m5_owner_installation_required` result across 386 cases.
  The archive race file separately returned `15 passed` against real files and
  forked processes. Its later 387-ID inventory is historical; the current
  pinned count and digest are recorded in the status table above and the latest
  transition finding below. An inventory update is not a full-suite pass; the
  final gate must execute the exact current inventory with live selectors and
  zero skips.

These were individual intermediate runs. They do not assert that the worktree
was committed and clean, that one unchanged exact revision supplied every
result, or that the live selectors required by `AUTO-M5-EXIT` were available.

## Refactor evidence

- Registry traversal uses stable snapshots, complete terminal pages, advancing
  cursors, and duplicate guards for owner/quota digests and alert delivery.
- The UI loads later account pages through the generated API client and fetches
  an explicitly selected account through the versioned detail endpoint.
- Private owner/quota prerequisite readers pin and revalidate parent and file
  identities, enforce owner-only modes, and reject link substitution.
- The syscall containment verifier moved selector, result, and trace transport
  to bounded inherited anonymous pipes, drains selector input after child
  launch, pins the managed-profile working directory by descriptor, evaluates
  pre-exec default-profile access globally, and closes provider attribution
  when a PID exits.
- Provider-schema generation, frontend type checking, Ruff, formatting, mypy,
  byte compilation, Node syntax checks, and scoped `git diff --check` have
  passed in the cited focused handoffs. The canonical build, mutation,
  documentation, planning, and M3 dependency routines also passed as
  development-checkout checkpoints. `AUTO-QUALITY` and the local-commit scope
  of `AUTO-GIT-PREFLIGHT` also passed. The complete required routine set has
  not run on one clean M5 revision, and `AUTO-M5-EXIT` remains outside the
  evidence recorded here.

## Real-system evidence

| Boundary | Status | Evidence and limit |
|---|---|---|
| Exact installed provider | Passed for installation/admission and empty-root safety | Exact Codex CLI `0.160.0`, installed schema, and local executable were used. The committed config-schema digest is recorded in the discovery/correction evidence. No authenticated quota claim is made. |
| File-backed SQLite/migration | Passed for focused persistence and pagination | Fresh databases used the real migration chain and production repositories/commands. No M5 migration was needed. |
| Production HTTP/generated client | Passed for focused account pagination and Codex API composition | Real loopback service, IAM/CSRF, versioned API, and generated client paths were exercised. `AUTO-BUILD` passed as an intermediate generated-artifact/build checkpoint; `AUTO-M5-EXIT` remains Not Run. |
| Built Chrome UI | Passed for focused 201-account navigation | The production frontend and Chrome displayed and opened the account beyond page 200. Four-account identity/quota and alert-lifecycle browser witnesses remain Blocked. |
| Linux process/filesystem | Passed for non-authenticated admission and containment policies | Real processes, file descriptors, pipes, files, links, and tracer admission were exercised. Five to six external Codex process observations and authenticated containment remain Blocked. |
| Four live accounts | Blocked | A four-row owner outcome artifact passed operationally for base revision `d7b8b9b`, but its revision/service binding cannot satisfy the later alert-correction revision. |
| Authoritative live quota/history | Blocked | One authenticated provider outcome normalized one primary window, then the Capacity commit failed on the now-corrected provenance grammar. The recovered interruption is now eligible only after full cadence. A fresh successful commit, official `/usage` reconciliation, and post-restart lineage witness remain required. |
| Genuine capacity alert lifecycle | Blocked | Retained-history policy accepts a fresh `opened` or `reopened` occurrence without deleting older generations, but no current natural repeat, owner action, source-proven recovery, built-browser proof, and create-once alert witness has completed. |
| Clean exact running revision | Historical `6bfa69d` activation Passed; corrected revision Not Run | The first activation produced its private service receipt, but no corrected exact revision has completed rollover/reactivation or produced the separate create-once `AUTO-M5-EXIT` receipt. |

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
- The approved plan, Codex adapter documentation, operations runbook,
  completion-gate documentation, generated contracts, and this evidence are
  the documentation surfaces affected. README, traceability/status, and formal
  acceptance must change only after their claims become true.

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
- Tests:
  Codex adapter, Registry, Collection, Capacity, Alerting, API, Operations,
  Linux runtime, release, client, pure UI, and built-browser suites under
  `backend/tests/**` and `frontend/tests/**`.
- Automation:
  `tools/automation/implementations/m5_*`,
  `tools/automation/implementations/auto_m5_current_exit.py`,
  `tools/automation/test_m5_*`, `tools/automation/routines.toml`,
  `tools/automation/run.py`, and shared M5 browser Registry-page helpers.
- Documentation: the approved M5 plan, Codex discovery/correction evidence,
  Codex adapter guide, operations/completion-gate documentation, and this file.

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
467 cases with digest
`9945fa963f0f003aa2732614d9266ae22268ac3d6b67c8f4c08233fc3df6756a`.
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
revision only. The corrective rollover, its required status-5 rerun, and the
corrected revision's activation are **Not Run** at this preactivation
checkpoint. `AUTO-M5-EXIT` also remains **Not Run**.

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
confirmed 467 unique identifiers and the pinned digest above; the production
inventory validator accepted both before returning the expected
`m5_current_story_suite_skipped` for the no-selector local run. This is
inventory evidence, not a live Story-suite pass. The inventory-producing run
reported `460 passed, 6 skipped, 1 failed` with the admitted Claude and Codex
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

## Data and secret review

This document contains no secret, provider response, account identity, private
profile path, process identifier, prompt, response, source-code content from a
provider session, or arbitrary environment value. Private outcome, quota,
alert, profile, and completion artifacts remain outside the repository and are
represented here only by sanitized result counts or public digests.

## Conclusion and residual gaps

The cited evidence proves substantial M5 implementation progress: the exact
installed Codex version is admitted; empty managed roots fail before provider
startup; provider write semantics are declared honestly; the ten-minute login
and service-drain bounds align; real SQLite/API/browser account pagination and
real SQLite alert Registry pagination work beyond 200 records; and the local
completion-prerequisite policies fail closed at their tested boundaries.
One authenticated quota operation also reached a normalized primary window
before exposing the corrected Capacity provenance grammar; its failed commit
is not a live quota pass. The recovered interruption can now become eligible
for a distinct run after full cadence, but that live retry has not passed.

It does not prove V1-M5 complete. Before any completion or acceptance claim,
the integration owner must:

1. run the exact corrective `AUTO-M5-SERVICE-ACTIVATE` rollover from the
   completed `6bfa69d` transition, refresh the selected trusted PID after its
   typed status-5 result, and rerun the command successfully from the corrected
   committed detached revision while retaining both the archive and trusted
   rollback runtime;
2. create the four-account owner outcome record using real accounts or explicit
   owner-unavailable outcomes;
3. reconcile every verified account with official `/usage`, fresh collection,
   current API/DOM values, and retained history;
4. verify five to six representative external Codex processes without account
   guessing or process control;
5. record one genuine Codex capacity alert through a fresh `opened` occurrence,
   or a `reopened` occurrence for a retained recovered fingerprint, followed by
   repeat/deduplication, owner action, and source-proven recovery without
   deleting earlier history;
6. run authenticated syscall containment for identity and quota with zero
   default-profile access/write; and
7. run `python3 tools/automation/run.py AUTO-M5-EXIT`, which reruns every
   required local routine with zero skips, obtain its private
   create-once exact-revision receipt, and present that exact result for owner
   review.

Until those steps pass, M5 remains **Intermediate**, its unavailable live
scenarios remain **Blocked**, and its canonical completion gate remains
**Not Run**.
