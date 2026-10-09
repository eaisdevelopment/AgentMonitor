# Test evidence: V1-M5 Codex implementation

- Evidence ID: `M5-CDX-IMPLEMENTATION-2026-10-08`
- Module/plan/increment: A02 Codex provider adapter and root-owned V1-M5
  integration, approved focused plan version `1.1.0`, Stories
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
- Commit/worktree reference: integration worktree based on
  `e4ea22a815af4fc89e7899ea57cb35814a1fa6c8`. The identity correction does
  not yet have a clean revision assessed by the canonical M5 gate.
- Recorder/date: Codex integration record, 2026-10-08.
- Overall status: **Intermediate**. The canonical `AUTO-M5-EXIT` run and its
  owner review are **Not Run**. This record is not milestone acceptance.

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
| `M5-CDX-ALERT-001` complete Registry scope | Pure policy and DB integration | Real migrated file SQLite, production Registry commands, exact Codex installation reconciliation, 201 accounts | Passed | Three focused tests; full file `8 passed, 3 skipped` | Cursor progress and duplicate IDs fail closed; the target after page 200 resolves. Three owner-live selectors remain skipped. |
| M5 Node story inventory | Pure UI/gate policy and source wiring | Production policy modules and browser entrypoint sources | Passed | `19 passed`, zero skipped | Includes configurable capacity-alert presentation and the alert and quota browser verifiers' use of shared complete page readers. This is a development-checkout result, not a live browser witness. |
| `AUTO-M3-TEST` dependency checkpoint | M3 contract and technical backend suites | Canonical routine on the development checkout | Passed | Two routine tests and `307` technical tests passed, zero skipped | Satisfies the local M3 dependency checkpoint; it does not establish an exact clean M5 revision. |
| `AUTO-MUTATION` checkpoint | Critical pure-policy mutation | Canonical routine on the development checkout | Passed | `1708` mutants: `1698` killed, `10` independently accepted equivalent, `0` skipped | No non-equivalent survivor was admitted. This remains subject to the final clean-revision M5 gate. |
| Quality, build, planning, documentation, and Git checkpoints | Static quality, generated artifacts/frontend build, repository validation, and local Git preflight | Canonical local routines on the development checkout | Passed | `AUTO-QUALITY`, `AUTO-BUILD`, `AUTO-PLAN-CHECK`, `AUTO-DOCS-CHECK`, and `AUTO-GIT-PREFLIGHT` exited zero | These individual checkpoints do not replace the unrun exact-revision `AUTO-M5-EXIT`. |
| Full M5 Python story selection before live setup | Backend and automation Story scope | Real local boundaries plus explicit owner/provider selectors | Blocked | The current 386-case development-checkout run returned `379 passed, 6 skipped, 1 failed`; the real-filesystem archive race file separately returned `15 passed`. | The sole full-run failure is the explicit `BLOCKED: m5_owner_installation_required` release selector. All six skips name missing owner/live selectors; no ordinary test failed. The final gate must rerun the 386-case inventory with zero skips. |
| Full backend regression checkpoint | Backend regression | Real local test boundaries selected by the backend suite | Blocked | Historical pre-correction rerun: `10 failed, 1374 passed, 39 skipped` | Every reported failure was an explicit M4/LAN/M5 real-owner selector requirement. This historical result does not describe the corrected checkout. |
| `AC-LIVE-002/004` four selected Codex outcomes and live identities | Provider/account | Four real owner-selected Codex accounts or explicit owner-unavailable outcomes | Blocked | No current owner outcome file | Owner authentication and current identity verification are still required. |
| `AC-LIVE-005`, `M5-CDX-COL/CAP` authoritative quota/history | Provider/DB/API/browser | Official Codex `/usage`, fresh scheduled observations, current and retained history | Blocked | One authenticated provider outcome normalized one primary window, but its capacity commit failed before persistence | Provenance admission and full-cadence interrupted-commit recovery are pure Green. A real retry must still prove commit, current/history lineage, exact whole percentages, reset precision, and at most 300-second skew. |
| `AC-PROC-001..004`, `M5-CDX-RUN-001..008` representative processes | Linux/platform/browser | Five to six real Codex processes outside the managed-profile subtree | Blocked | No current process witness | PID/start/executable reread, hierarchy/location, and unresolved or owner-confirmed association remain required. |
| `AC-ALERT-002`, `M5-CDX-ALERT-001..006` live lifecycle | DB/API/browser/provider | Genuine Codex capacity condition, repeated delivery, owner action, later source-proven recovery | Blocked | No current alert witness | Local DB pagination passed; the natural live lifecycle did not run. |
| Authenticated managed-profile syscall containment | Linux/provider/security | Real authenticated managed Codex profile and `strace` | Blocked | One truthful live-selector skip in the containment suite | Identity and quota operations must show provider access inside the selected root and zero default-profile access/write. |
| `M5-CDX-GATE-001..014`, canonical `AUTO-M5-EXIT` | Full local/live gate | Clean exact revision, selected running service, prerequisite receipts, all local gates with zero skips | Not Run | No M5 completion receipt | Must be the last technical gate before owner review. |
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
- The current full M5 Python Story selection returned `379 passed`, six
  truthful live-selector skips, and one explicit
  `BLOCKED: m5_owner_installation_required` result across 386 cases. The
  archive race file separately returned `15 passed` against real files and
  forked processes. Exact JUnit reconciliation produces 386 unique test IDs
  with SHA-256
  `561d47287a62b1a4773131c043099de22324e65fcb0eb7289052076181a04547`.
  The final gate must execute that complete inventory with live selectors.

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
| Production HTTP/generated client | Passed for focused account pagination and Codex API composition | Real loopback service, IAM/CSRF, versioned API, and generated client paths were exercised. `AUTO-BUILD` passed as an intermediate generated-artifact/build checkpoint; the exact clean-revision M5 gate remains Not Run. |
| Built Chrome UI | Passed for focused 201-account navigation | The production frontend and Chrome displayed and opened the account beyond page 200. Four-account identity/quota and alert-lifecycle browser witnesses remain Blocked. |
| Linux process/filesystem | Passed for non-authenticated admission and containment policies | Real processes, file descriptors, pipes, files, links, and tracer admission were exercised. Five to six external Codex process observations and authenticated containment remain Blocked. |
| Four live accounts | Blocked | No four-row owner outcome artifact is current for this worktree/revision. |
| Authoritative live quota/history | Blocked | One authenticated provider outcome normalized one primary window, then the Capacity commit failed on the now-corrected provenance grammar. The recovered interruption is now eligible only after full cadence. A fresh successful commit, official `/usage` reconciliation, and post-restart lineage witness remain required. |
| Genuine capacity alert lifecycle | Blocked | No natural opening, repeated condition, owner action, and source-proven recovery witness exists. |
| Clean exact running revision | Not Run | The worktree is not a committed clean assessment revision, and no create-once M5 receipt exists. |

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

1. commit one clean exact implementation revision and start the selected
   service from that same revision;
2. create the four-account owner outcome record using real accounts or explicit
   owner-unavailable outcomes;
3. reconcile every verified account with official `/usage`, fresh collection,
   current API/DOM values, and retained history;
4. verify five to six representative external Codex processes without account
   guessing or process control;
5. record one genuine Codex capacity alert through open, repeat/deduplication,
   owner action, and source-proven recovery;
6. run authenticated syscall containment for identity and quota with zero
   default-profile access/write; and
7. run `python3 tools/automation/run.py AUTO-M5-EXIT`, which reruns every
   required local routine with zero skips, obtain its private
   create-once exact-revision receipt, and present that exact result for owner
   review.

Until those steps pass, M5 remains **Intermediate**, its live scenarios remain
**Blocked**, and its canonical completion gate remains **Not Run**.
