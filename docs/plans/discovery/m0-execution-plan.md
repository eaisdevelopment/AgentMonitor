# Milestone 0 execution plan: read-only telemetry discovery

- Plan ID: `PLAN-M0-DISCOVERY`
- Status: **Approved for gated discovery**
- Plan version: `0.2.0`
- Lifecycle phase: G0 approved; G1 incomplete; no scenario execution or implementation is authorized
- Primary owner: root/integration steward
- Primary owning module for future discovery contracts: M03 Provider system
- Evidence operators: provider/platform discovery agents under owner supervision
- Reviewers: owner, security/privacy reviewer, provider-system owner, test-integrity reviewer
- Governing contracts: `ProviderAdapterV1` `1.0.0-draft.2` capability/outcome vocabulary; no implementation contract is approved by this plan
- Target milestone: M0
- Approval record: `docs/plans/discovery/m0-g0-approval.toml`

## 1. Purpose and authority boundary

### Objective

Replace assumptions about Claude, Codex, Ollama, Anthropic API, OpenAI API, Ollama API, and the Linux process/session surface with scoped, sanitized, real-system evidence. The resulting evidence must be sufficient to decide, for every V1 capability and observed provider/version/plan context, whether it is `Supported`, `Experimental`, `Deferred`, or `Unsupported` and to prepare isolated implementation plans without inventing provider behavior.

M0 is successful when the owner and reviewers can answer all of the following from inspectable evidence:

1. Which official or approved read-only source exposes each capability?
2. What exact safe fields, units, windows, timestamps, precision, freshness, and identity scope does the source provide?
3. What credential role or local access is required, without recording credential values?
4. What rate-limit, collection-cost, latency, timeout, version, and failure constraints apply?
5. Which identity signals can correlate installations, profiles, accounts, resources, sessions, and processes without guessing?
6. Which files, fields, outputs, and process attributes are prohibited because they may contain credentials, prompts, responses, tool activity, source, arbitrary environment values, or unrelated personal data?
7. What contract proposals and module plans can safely proceed, and which remain blocked?

### Planning-only authority

This document authorizes planning only. It does not authorize any command, provider request, local provider-file read, account access, browser interaction, API call, installation, login, logout, profile creation, re-authentication, code creation, or modification of shared specifications. Each later observation requires the gates in this plan and explicit owner approval for its reviewed execution packet.

### Non-goals

M0 will not:

- implement production collectors, adapters, parsers, domain models, database schemas, API routes, UI views, services, or tests;
- finalize `ProviderAdapterV1` signatures before evidence and contract synchronization;
- enroll all owner accounts or satisfy V1 live-enrollment acceptance criteria;
- perform login, logout, re-authentication, account switching, profile isolation, profile creation, or credential migration;
- modify or relocate a default Claude, Codex, or Ollama profile;
- invoke an undocumented/private endpoint, browser automation, cookie extraction, traffic interception, process attachment, process memory inspection, terminal injection, or arbitrary environment inspection;
- manufacture exhaustion, revocation, provider failure, account mismatch, or rate-limit states;
- measure application performance, retention, backup, alerting, dashboard, or routing behavior;
- infer support for unobserved versions, plan classes, platforms, organizations, workspaces, projects, or credential roles;
- introduce dependencies or promote exploratory scripts into production code;
- claim that a discovery scenario satisfies a release acceptance criterion by itself.

## 2. Governing invariants

The following rules apply to every gate, workstream, command review, observation, evidence record, conclusion, and handoff:

1. Real provider accounts, current installed tools, and real Linux processes are the only acceptable external evidence. No mocks, fakes, stubs, emulators, provider recordings, demo accounts, seeded telemetry, or placeholder values are permitted.
2. Default provider profiles and running agents are read-only and must not be interrupted, signaled, restarted, controlled, or supplied input.
3. Provider-owned files are not read until their path, file class, field allowlist, size bound, version scope, and side-effect analysis are approved.
4. **`M0CTL-NOREAD`:** Prompts, responses, tool activity,
   source-code content, terminal contents, arbitrary process environments,
   credentials, cookies, passwords, OTP/MFA/recovery values, and raw
   secret-bearing payloads are never intentionally opened, read, requested,
   parsed, or loaded into memory, and are neither captured nor persisted. If a
   source cannot selectively expose allowlisted safe fields without reading
   co-resident prohibited bytes, that source is `Blocked`, `Deferred`, or
   `Unsupported`. Accidental appearance alone enters the section 19 stop and
   incident procedure.
5. Missing, unknown, unsupported, unavailable, unauthenticated, unauthorized, exhausted, stale, and zero remain distinct.
6. Observations are scoped to the exact provider product, installed/provider version, plan/account class, credential role, source, and platform actually reviewed.
7. Official source semantics take precedence over inference. Owner visual comparison confirms a source; it does not turn an undocumented interface into a supported interface.
8. A read-only label is not trusted until command/network/filesystem side effects have been reviewed.
9. No raw output is committed. Repository artifacts contain conclusions, safe shapes, opaque aliases, citations, and external evidence references only.
10. Discovery can conclude `Unsupported`; it cannot fill a gap with invented precision or a weaker source without an explicit decision.

## 3. Ownership and module isolation

M0 is cross-cutting evidence work coordinated by the root/integration steward. M03 Provider system is the single primary owner of the future capability/discovery contract; each observation remains evidence for the domain or adapter named below. This plan does not transfer production ownership:

| Concern | Future owner | M0 responsibility |
|---|---|---|
| Organizations, accounts, profiles, resources, owner-confirmed links | M02 Registry | Discover safe identity and relationship evidence only |
| Capability vocabulary, manifests, compatibility, discovery outcomes | M03 Provider system | Classify sources/capabilities and propose contract needs |
| Polling, concurrency, deadlines, retries, backoff, collection runs | M04 Collection control | Discover constraints; do not design scheduler internals |
| Quotas, budgets, costs, forecasts, provenance | M05 Capacity | Establish observable semantics and safe fields only |
| Processes, sessions, hierarchy, state, correlation | M06 Runtime observation | Establish Linux/provider evidence and prohibited fields only |
| Claude behavior | A01 Claude adapter | Produce a Claude-scoped capability dossier |
| Codex behavior | A02 Codex adapter | Produce a Codex-scoped capability dossier |
| Ollama behavior | A03 Ollama adapter | Produce Ollama local/cloud capability dossiers |
| Linux process/filesystem behavior | A04-LINUX platform adapter | Produce a Linux-scoped source and safety dossier |

Discovery operators must not edit another module's future contracts or choose database/API/UI representations. Contract changes identified by M0 are proposals for the synchronization gate.

## 4. Requirement, acceptance, and risk traceability

### Requirements and acceptance contribution

`Contribution` means M0 provides input to a later plan or acceptance gate. It does not mean the acceptance criterion passes.

| Workstream | Primary requirements | Acceptance contribution | Primary risks |
|---|---|---|---|
| Common environment and source governance | FR-ACC-005, FR-COL-004..008, FR-OPS-006; NFR-SEC-001, NFR-DOC-001, NFR-PLAT-001, NFR-OBS-001 | AC-V1-001, AC-V1-005..008, AC-LIVE-004, AC-TEST-004, AC-TEST-006 | R-002, R-004, R-005, R-010, R-018, R-019, R-024 |
| Claude subscription/local surfaces | FR-ACC-001, FR-ACC-004..006, FR-AUTH-001, FR-AUTH-005..006, FR-QUOTA-001..006, FR-DISC-003..004, FR-DISC-006..008 | AC-LIVE-001, AC-LIVE-004..007, AC-PROC-003..004 | R-001..005, R-007, R-009, R-010, R-021, R-024 |
| Codex subscription/local surfaces | FR-ACC-001, FR-ACC-004..006, FR-AUTH-001, FR-AUTH-005..006, FR-QUOTA-001..006, FR-DISC-003..004, FR-DISC-006..008 | AC-LIVE-002, AC-LIVE-004..007, AC-PROC-003..004 | R-001..005, R-007, R-009, R-010, R-021, R-024 |
| Ollama product/subscription/local surfaces | FR-ACC-001, FR-ACC-004..006, FR-AUTH-001, FR-AUTH-005..006, FR-QUOTA-001..006, FR-DISC-003..004, FR-DISC-006..008 | AC-LIVE-003..005, AC-PROC-003..004 | R-001..005, R-007, R-009, R-010, R-024 |
| Anthropic API budget surfaces | FR-BUDGET-001..006, FR-COL-003..008 | AC-LIVE-004..005, AC-OPS-006 | R-001, R-005..010, R-014, R-018, R-024 |
| OpenAI API budget surfaces | FR-BUDGET-001..006, FR-COL-003..008 | AC-LIVE-004..005, AC-OPS-006 | R-001, R-005..010, R-014, R-018, R-024 |
| Ollama API budget surfaces | FR-BUDGET-001..006, FR-COL-003..008 | AC-LIVE-003..005, AC-OPS-006 | R-001, R-005..010, R-014, R-018, R-024 |
| Linux process/session observation | FR-DISC-001..008, FR-STATE-001..004, FR-SAFE-002; NFR-PRIV-001, NFR-PLAT-001, NFR-RES-001 | AC-PROC-001..005, AC-LIVE-004, AC-TEST-004 | R-003..005, R-009, R-010, R-015, R-016, R-019, R-023 |
| Identity/correlation synthesis | FR-ACC-006, FR-DISC-004..005, FR-STATE-002 | AC-LIVE-001..003, AC-PROC-002..004 | R-003, R-014, R-015, R-021 |

All workstreams are additionally constrained by NFR-TEST-001..002, NFR-PRIV-001..002, NFR-COMP-001, and FR-SAFE-001..002.

### Risk treatment required at M0 exit

- R-001 and R-002: every capability records source class, version scope, format stability, unknown-version behavior, and whether a safe machine-readable source exists.
- R-003 and R-015: correlation evidence and PID/start-time identity are documented; ambiguity resolves to `Unresolved`, never a guess.
- R-004 and R-005: pre/post side-effect checks and evidence sanitization are completed for every executed scenario.
- R-006 and R-010: each network/CLI source has an approved request/cost/rate budget before use.
- R-007 and R-008: native windows, timestamps, units, precision, missingness, and freshness are recorded without normalization.
- R-009: unavailable live states remain visibly `Blocked`; pure future policy tests cannot convert them to live passes.
- R-014 and R-021: identity/resource multiplicity and re-auth implications are handed to Registry; re-auth is not executed in M0.
- R-019: workstation/provider evidence is kept distinct from future hosted-CI evidence.
- R-023: Linux evidence is not generalized to macOS.
- R-024: an interface requiring private/browser mechanisms is `Deferred` or `Unsupported` unless a later threat review and ADR authorize it.

## 5. Source priority and research standard

Each candidate source is evaluated in this order:

1. **Documented API** — current official provider documentation and supported API schema.
2. **Supported CLI** — official documentation or built-in help for the installed version, with structured output preferred.
3. **Approved local metadata** — owner-approved, bounded, read-only, allowlisted provider files or operating-system metadata.
4. **Experimental private/browser source** — disabled for this M0 plan. Discovery may document that it appears necessary, but it may not call, automate, or capture it without a separate threat-model update, ADR, and explicit approval.

Research citations must point to official provider documentation, provider-maintained source/release notes where appropriate, or the installed tool's approved help/version surface. Community articles, search summaries, reverse-engineering notes, and memory may suggest a question but cannot establish support or semantics. Every official source record contains URL/document identifier, title, access date, version applicability, relevant capability, and whether live behavior matched it.

Provider dashboard pages may be used by the owner as an authoritative visual comparison. They are not automated, scraped, inspected for cookies, or treated as a collector interface.

No current external-provider fact is asserted by this plan; current facts are established during execution from official sources and real observations.

## 6. Evidence and data-handling model

### Evidence classes

| Class | Contents | Repository eligibility | Custody |
|---|---|---|---|
| E0 — public source | Official URL/document/release/help reference, access date, scoped conclusion | Yes | Repository documentation |
| E1 — sanitized structural evidence | Field names, types, units, nullability, safe enum names, version, timestamps, result status, redacted summary | Only after `M0CTL-E1-ADMISSION` | Repository conclusion plus external run record |
| E2 — sensitive operational metadata | Opaque account alias mapping, local absolute paths, PIDs, working directories, file metadata, organization/project identifiers | No | Owner-controlled external evidence root |
| E3 — prohibited/secret/content | Credential values, cookies, auth headers, email/identity, raw provider payloads, prompts, responses, tools, source, arbitrary environment, OTP/MFA | Never intentionally accessed; accidental appearance only | Stop, quarantine only if accidentally exposed, then incident procedure |

### External evidence root and exact layout

Before execution, the owner selects an owner-only, non-repository, non-CI, non-shared location represented in documents as `<M0_EVIDENCE_ROOT>`. The real path is not recorded in Git or chat. Each run uses an opaque run ID:

```text
<M0_EVIDENCE_ROOT>/
  custody-register.md
  runs/<opaque-run-id>/
    run-record.md
    command-approvals.md
    observations/
    sanitized/
    quarantine/               # normally empty; incident-only
    deletion-record.md
```

Requirements:

- owner-only filesystem permissions are verified without printing sensitive contents;
- cloud synchronization and automatic backup eligibility are explicitly decided by the owner before use; default is no synchronization;
- opaque aliases are mapped to real identities only in the external custody register, never in repository files;
- raw stdout/stderr and screenshots are not captured by default;
- an operator transcribes only allowlisted structural fields into a sanitized record;
- if a tool cannot prevent reading or output of secret/content data at source,
  the operation is not run and the source is Blocked, Deferred, or Unsupported;
- accidental E3 evidence is moved to `quarantine/` without copying it into chat, then the security incident procedure determines deletion and any required credential rotation;
- E2 is retained only through the affected adapter/module plan approval and first corresponding live verification, unless an incident/legal need requires a reviewed exception;
- E1 conclusions and deletion records remain; deleted evidence keeps a non-sensitive tombstone with custodian, date, scope, and reason;
- external evidence is never used as a replay fixture or substitute for a live provider test.
- **`M0CTL-E1-ADMISSION`:** before any E1 conclusion, shape,
  deletion record, or handoff enters the repository, an approved local,
  no-telemetry, fail-closed secret/content scanner and a human allowlist review
  must both pass. The scanner must report only bounded finding categories and
  locations without echoing matched values. Dependency/license/security
  admission applies to the scanner. If no admitted scanner is available or the
  scan cannot run, repository publication remains `Blocked`.

### Sanitized observation record

Every cataloged scenario has a ledger record, including `Blocked` and `Not Run`
scenarios with an auditable reason and evidence/reference status. Every
attempted or executed scenario additionally records:

- scenario ID and opaque run ID;
- status: `Passed`, `Failed`, `Blocked`, or `Not Run`;
- operator/custodian roles and owner acknowledgement where interactive;
- UTC start/end plus local timezone used for owner comparison;
- platform, provider product, installed/provider version, plan/account class, and credential role category;
- source class and official citation;
- reviewed command identifier or owner-visual procedure identifier;
- approved assertion-set and operation-packet version/reference;
- assertion IDs, mandatory/optional classification, required real boundary,
  expected result, and actual result per attempted assertion;
- deviations from the approved operation or assertion set;
- approved side-effect budget and actual side-effect check;
- safe fields/types/units/window/precision/freshness findings;
- missing/unknown fields and uncertainties;
- sanitized warnings/errors without raw payloads;
- evidence class and external reference;
- capability decision impact and follow-up.

**`M0CTL-ASSERTIONS`:** a scenario cannot be `Passed` unless every
mandatory predeclared assertion has the required real-boundary evidence and the
record includes the approved assertion-set/version. Optional omissions remain
visible gaps. `Blocked` and `Not Run` records include the blocker/reason and do
not borrow an evidence reference from another scope.

No account identity, credential, full local path, raw payload, dynamic quota/spend amount, prompt/content, or source-code value appears in the committed record.

## 7. Side-effect budget

### Default budget for all scenarios

| Effect | Default maximum |
|---|---|
| Provider/account/profile/configuration mutations | Zero |
| Login, logout, re-authentication, account switching, profile creation | Zero |
| Default-profile or provider-state file writes/moves/copies | Zero |
| Process signals, input injection, restart, attach, debug, memory read | Zero |
| Budget, credit, subscription, key, role, or billing changes | Zero |
| Billable model generation or deliberately consumed quota | Zero |
| Package/tool installation or update | Zero |
| Private endpoint, cookie, or intercepted network access | Zero |
| Arbitrary process environment reads | Zero |
| Retained raw command/API response bodies | Zero |

Documented read-only API and status requests may consume rate-limit capacity or have a provider-defined request cost. Their maximum request count, concurrency, retry count, expected rate-limit impact, and possible monetary cost must be filled from official evidence and approved for that execution packet. Until those values are filled, the network request budget is zero.

Local filesystem reads can affect access time on some filesystems. A candidate file read must state whether atime can change and whether the mount/provider behavior makes that acceptable. No scenario may claim byte-for-byte non-modification merely from a content hash of a credential file; credential-file contents and hashes are not captured. Pre/post checks use only approved non-secret metadata and owner/provider observations.

### Permitted observational effects after approval

- bounded CPU, memory, disk-read, and process-list activity on the development machine;
- a reviewed official read-only request within its approved request/rate/cost budget;
- provider-side audit/access-log entries caused by that documented read-only request;
- owner opening an official provider dashboard for visual comparison;
- **`M0CTL-ATIME`:** an owner-approved atime change only when it cannot
  be disabled safely and it is predeclared, bounded to exact paths, measured
  with approved non-secret metadata, and reconciled after the run; all other
  filesystem writes remain prohibited.

Any other effect is unexpected and triggers the stop procedure.

## 8. Preflight safety approval gate

No scenario can move from `Not Run` to execution until `M0-GATE-PREFLIGHT` is signed for its run.

### Required preflight packet

1. **Scope:** scenario IDs, provider/product, version, plan/account class, opaque alias, and exact capability questions.
2. **Owner availability:** owner confirms the intended identity locally and remains available for dashboard/auth-sensitive observations.
3. **Version inventory:** installed binary/service/provider version is known or the scenario is explicitly limited to discovering it.
4. **Command approval:** every command/request has an approved command record; visual-only steps have a reviewed procedure.
5. **Path/field approval:** all candidate roots/files/fields are allowlisted; path escape, symlink, file type, ownership, size, and parsing bounds are specified.
6. **Evidence custody:** external root, permissions, alias mapping, sanitization method, and deletion trigger are confirmed.
7. **Side-effect budget:** zero-default categories and any non-zero read-request budget are recorded and owner-approved.
8. **Running-agent safety:** target and unrelated processes are identified by safe local aliases; no input/signal/restart is planned.
9. **Default-profile protection:** profile class is known; no mutation-capable operation targets it. Pre/post non-secret checks are defined where meaningful.
10. **Secrets/content:** output field review shows how prohibited data is prevented rather than redacted after broad capture.
11. **Timeout/output bounds:** cancellation, maximum duration, stdout/stderr handling, and no-retry behavior are explicit.
12. **Stop/incident readiness:** operator knows how to terminate the observation without affecting provider agents and how to quarantine accidental sensitive output.
13. **Repository state:** discovery conclusions target planned paths only; no evidence file or local identity will be committed.
14. **Approval:** operator, security reviewer, root steward, and owner record decision and conditions.

### Gate result

- `Approved`: only listed scenarios and exact reviewed operations may run.
- `Conditionally approved`: execution waits until named conditions are fulfilled.
- `Rejected`: scenario remains `Blocked` or is redesigned.
- Expired approval: any provider/tool version, command, path, output schema, side-effect, or credential-role change returns to review.

## 9. Command and procedure review

### Rule

This plan intentionally contains no executable provider commands. A familiar command name, `--help`, `--version`, status command, or documented endpoint is not assumed read-only. Exact operations are added only after official-source and side-effect review.

### Command identifiers and lifecycle

Candidate operations receive stable IDs:

```text
CMD-M0-COM-NNN
CMD-M0-CLA-NNN
CMD-M0-CDX-NNN
CMD-M0-OLL-NNN
CMD-M0-ANT-NNN
CMD-M0-OAI-NNN
CMD-M0-OAPI-NNN
CMD-M0-LNX-NNN
```

Lifecycle: `Proposed -> Security reviewed -> Owner approved -> Executed once -> Reconciled -> Approved for bounded reuse | Retired | Blocked`.

### Review record fields

For every command, API request, file read, or owner-visual procedure, record:

- exact executable identity/absolute path category and verified version, or exact HTTPS method/official endpoint template;
- exact argument vector or request field names; never a shell string and never a secret in arguments;
- authoritative official documentation reference and access date;
- working directory and minimal environment-variable name allowlist, with values never recorded;
- target profile/account/resource class and proof the default profile cannot be mutated;
- stdin/interactive behavior, login/update prompts, auto-update/telemetry behavior, and cancellation behavior;
- network hosts, redirects, request method, expected authentication role, and response-size bound;
- **`M0CTL-NETWORK`:** exact owning host allowlist and credential-to-host
  binding, normal certificate and hostname verification with no insecure
  override, and a default-deny redirect policy; an exact reviewed redirect
  target is a new allowlisted host and credentials are never forwarded across
  hosts;
- filesystem reads/writes, caches, logs, histories, lock files, atime effects, and provider audit effects;
- expected stdout/stderr field classes and an allowlist-based extraction plan;
- timeout, output limit, allowed exit codes, request/concurrency/retry limit, and cost budget;
- pre/post state checks and cleanup, which must not delete provider state;
- known failure modes and the stop condition;
- reviewers, approval timestamp, applicable version range, and expiry trigger.

### Execution rules

- Use direct argument vectors; no shell interpolation or output redirection into repository files.
- Use the minimum environment. Do not dump, enumerate, or inherit unrelated environment values.
- Do not accept a login/update/configuration prompt; stop instead.
- Do not retry an unknown failure, rate limit, or auth failure automatically.
- Request/read/parse only the allowlisted sanitized fields needed for the
  scenario. Do not broadly capture prohibited data and redact it afterward.
- A changed command, version, endpoint, role, output shape, or side effect is a new review, not an editorial update to a passed result.

## 10. Identity and correlation model to investigate

### Identity layers

M0 must distinguish rather than collapse:

- provider installation and executable/service instance;
- provider authentication/profile root;
- human/provider account identity;
- provider organization, team, or workspace;
- API organization/project and safe API-key identifier if officially exposed;
- subscription or billing resource pool;
- provider session/conversation/run identifier where safe;
- operating-system process identity as `(pid, process_start_time, executable_identity)`;
- parent/child process and parent/subagent session relationships;
- model and project/repository labels as metadata, not identity.

### Evidence-strength rubric

| Strength | Evidence | Allowed conclusion |
|---|---|---|
| Strong | Documented stable provider identifier or an exact documented relation shared by both sources | Automatic correlation may be proposed for the exact scoped versions |
| Corroborated | Multiple independent non-secret signals with documented collision/lifetime behavior | Correlation may be proposed only with explicit confidence and conflict rules |
| Owner confirmed | Owner manually confirms an otherwise unresolved association at a recorded time | Persistable manual association may be proposed; it is not provider proof |
| Weak | Display name, email fragment, path name, process order, timing alone, or inferred current login | Must remain `Unresolved`; cannot drive automatic mapping |
| Conflicting | Signals disagree, identifier is reused, or lifetime is unclear | `Unresolved` or `wrong-account` condition; stop automatic association |

### Cross-workstream questions

1. Which identifier is stable across rename, logout/login, re-authentication, profile relocation, provider upgrade, organization move, and billing-cycle reset?
2. Which identifiers are scoped only within an organization, project, profile, process, or device?
3. Can a provider account expose multiple subscription/API resources without double counting?
4. Can one profile authenticate a subscription surface and an API organization that are not the same resource pool?
5. Does a running process retain launch identity after the owner independently changes the default login?
6. Can a session record prove its account/profile without reading content, arbitrary environment, process memory, or terminal state?
7. Can parent/subagent relationships be proven from provider metadata, OS ancestry, or both, and how are wrappers/reparenting handled?
8. What is the lifetime/reuse behavior of provider session IDs and process IDs?
9. What owner confirmation is required when evidence is absent or conflicting?
10. What non-secret check can detect a wrong account during a future managed-profile re-authentication flow?

Questions requiring login, logout, account switching, or managed-profile creation are documented for a separately approved later experiment. They are not executed under this plan.

## 11. Scenario status semantics

Scenario status and capability decision are different dimensions.

- **Passed:** the exact approved scenario executed against the required real boundary and met its predeclared observational and safety assertions. Passing a discovery scenario does not imply the capability is supported.
- **Failed:** the scenario executed but an observational assertion, safety invariant, source-semantics check, or pre/post state check failed.
- **Blocked:** execution could not safely proceed because owner action, real account/role, provider condition, official documentation, approved source, evidence custody, or safe command was unavailable.
- **Not Run:** the scenario was not attempted for the current run/revision.
- **Unsupported:** not a test status. It is a reviewed capability decision reached when no safe/authorized/trustworthy source exists for the scoped context.
- **Partial:** not an allowed final scenario status. A scenario with incomplete mandatory assertions is `Failed` or `Blocked`; optional observations are recorded as gaps.
- `Skipped`, `assumed pass`, and `pass with no evidence` are prohibited.

A `Blocked` or `Not Run` scenario remains visible in the scenario ledger and every downstream handoff. It never becomes `Passed` because another provider, account, plan, version, pure domain test, or owner recollection behaved similarly.

## 12. Master scenario catalog

The steps below are procedural descriptions, not executable commands. Every scenario requires the preflight gate and approved operation IDs.

### 12.1 Common environment and governance (`M0-COM`)

| Scenario ID | Observation | Pass basis |
|---|---|---|
| M0-COM-001 | Establish owner consent, evidence root, alias mapping, roles, stop procedure, and zero-default side-effect budget | Custody and approvals exist without secrets/identities in repository/chat |
| M0-COM-002 | Record OS, distribution, kernel, architecture, timezone, filesystem/mount behavior relevant to reads, and permission context | Sanitized platform scope and read-side-effect notes are complete |
| M0-COM-003 | Inventory availability and versions of provider executables/services and later test prerequisites without installing/updating | Exact observed versions or explicit absence are recorded |
| M0-COM-004 | Inventory provider state-root candidates by approved root metadata only | Roots are classified without reading unapproved values or following unsafe links |
| M0-COM-005 | Establish official-source register and access dates for every candidate capability | Every candidate operation has an official citation or is marked unsupported/unapproved |
| M0-COM-006 | Validate evidence sanitization on a safe structural record before provider observations | Review finds no E2/E3 data in repository-eligible form |
| M0-COM-007 | Reconcile pre/post local/provider state after each run | No unapproved side effect; uncertainty is recorded rather than cleared |
| M0-COM-008 | Produce complete scenario ledger and custody/deletion state | Every scenario is Passed/Failed/Blocked/Not Run with an evidence reference |

**`M0CTL-AUTH-SCOPE`:** any question about login, logout, `/login`, account
switching, profile isolation, or state survival is documentation-only in M0 or
is handed to a separately approved future experiment. No operation packet
approved by this plan may perform or induce those actions.

### 12.2 Claude subscription and local surfaces (`M0-CLA`)

| Scenario ID | Observation | Pass basis |
|---|---|---|
| M0-CLA-001 | Review official Claude product/CLI documentation for installation, status/usage, auth-health, local-session, and profile-isolation surfaces | Candidate capabilities, exact version scope, and documentation gaps are recorded |
| M0-CLA-002 | Observe installed Claude executable/version and reviewed help/schema surfaces | Installed-version scope is established without update/login/write |
| M0-CLA-003 | Owner compares the official subscription usage view/command with safe field-name transcription | Native windows, units, reset semantics, scope, precision, and missing fields are recorded without dynamic account values |
| M0-CLA-004 | Determine whether an approved non-interactive structured usage/status source exists | Source is classified with auth, rate/cost, output, and stability constraints or absence |
| M0-CLA-005 | Inventory approved local state file names/metadata and classify schemas before values | File classes and excluded secret/content classes are documented |
| M0-CLA-006 | Inspect only approved local metadata fields for safe session ID, model, token/context totals, activity, errors, and parent/subagent signals | Every retained field passes allowlist/privacy/version review; unavailable fields remain unknown |
| M0-CLA-007 | Evaluate auth-health and safe provider/account identity signals without authentication changes | Observable states/IDs and wrong/unknown identity behavior are documented |
| M0-CLA-008 | Evaluate process/session/profile/account correlation for naturally running Claude agents | Evidence strength, conflicts, and unresolved mappings are recorded without guessing |
| M0-CLA-009 | Observe provider/file/process behavior across a naturally occurring owner action only if separately approved and not initiated for M0 | Otherwise Blocked; no account switching/login is requested by this plan |
| M0-CLA-010 | Decide each Claude capability for the exact versions/plan classes observed | Each matrix row has a decision, confidence, gaps, and handoff impact |

### 12.3 Codex subscription and local surfaces (`M0-CDX`)

| Scenario ID | Observation | Pass basis |
|---|---|---|
| M0-CDX-001 | Review official Codex documentation for installation, status/limits, auth health, structured/app-server, session, and profile-home surfaces | Candidate capabilities and official gaps are version-scoped |
| M0-CDX-002 | Observe installed Codex executable/version and reviewed help/schema surfaces | Installed-version scope is established without update/logout/login/write |
| M0-CDX-003 | Owner compares official subscription status/limit surfaces with safe field-name transcription | Native windows, credit/limit/reset semantics, scope, precision, and missing fields are recorded |
| M0-CDX-004 | Determine whether a documented structured/app-server status source exists and is safe for polling | Source class, protocol/version, auth, rate/cost, and failure constraints or absence are recorded |
| M0-CDX-005 | Inventory approved `CODEX_HOME`-class state names/metadata and classify schemas before values | Secret/content-bearing classes are excluded and safe roots are bounded |
| M0-CDX-006 | Inspect only approved local session fields for safe session ID, model, tokens/context, activity, status, errors, and hierarchy signals | Retained fields are allowlisted and scoped to provider version |
| M0-CDX-007 | Determine active auth-store/profile mode as a category without reading credential material | Safe observable category and limitations are documented |
| M0-CDX-008 | Evaluate process/session/profile/account correlation for naturally running Codex agents | Evidence strength, conflicts, and unresolved mappings are recorded |
| M0-CDX-009 | Document `CODEX_HOME` versus named configuration-profile questions for a later isolated write/auth experiment | Scenario passes as a documented boundary only; no experiment runs in M0 |
| M0-CDX-010 | Decide each Codex capability for the exact versions/plan classes observed | Each matrix row has a decision, confidence, gaps, and handoff impact |

### 12.4 Ollama product, subscription, and local runtime (`M0-OLL`)

| Scenario ID | Observation | Pass basis |
|---|---|---|
| M0-OLL-001 | Review official Ollama documentation for account/team/workspace, cloud subscription/credits, local service, model/runtime, and auth surfaces | Candidate capability/source inventory and gaps are scoped |
| M0-OLL-002 | Observe installed Ollama client/service versions and reviewed supported discovery surfaces | Client/service/platform versions or absence are recorded without update/write |
| M0-OLL-003 | Owner identifies each observed resource as personal/team/organization/workspace and current/legacy plan class using opaque aliases | Relationship semantics and owner-confirmation needs are recorded without identity details |
| M0-OLL-004 | Observe official subscription/credit/usage view, if present, through owner comparison | Included/purchased balance, reset, concurrency/queue, units, precision, and absent fields are described structurally |
| M0-OLL-005 | Evaluate supported local service endpoints/tools for running models, load state, CPU/RAM/GPU, queue/concurrency, and request counters | Safe fields, host scope, units, freshness, and side effects are documented |
| M0-OLL-006 | Evaluate whether local logs/state expose cloud usage without content or credentials | Only allowlisted metadata is retained; content-bearing sources are rejected |
| M0-OLL-007 | Evaluate local/cloud process/session/account/workspace correlation | Evidence strength, multiplicity, conflicts, and unresolved states are documented |
| M0-OLL-008 | Separate local compute/model metrics, cloud subscription resources, and API billing resources | No incompatible pool is combined or double counted |
| M0-OLL-009 | Record auth-health and official re-auth guidance availability without executing authentication changes | Safe observable states and future managed-profile questions are documented |
| M0-OLL-010 | Decide each Ollama product/subscription/local capability for the exact observed scope | Each matrix row has a decision, confidence, gaps, and handoff impact |

### 12.5 Anthropic API usage, cost, and budget (`M0-ANT`)

| Scenario ID | Observation | Pass basis |
|---|---|---|
| M0-ANT-001 | Review current official Admin/API usage, cost, billing, credit, budget, and authentication-role documentation | Endpoint/field/role candidates and explicit documented absences are recorded |
| M0-ANT-002 | Establish least-privilege credential-role category and organization/workspace/project scope with owner, without recording credentials | Required role/scope and unavailable lower-privilege options are documented |
| M0-ANT-003 | Execute one bounded approved read-only usage observation | Buckets, grouping, pagination, token/request/model/workspace/key-safe fields, latency, and timestamps are structurally recorded |
| M0-ANT-004 | Execute one bounded approved cost observation, if officially available | Exact money representation, currency, intervals, grouping, pagination, latency, and missingness are recorded |
| M0-ANT-005 | Determine official credit, hard/soft limit, budget, and renewal/reset availability | Each field is supported or explicitly absent/unknown; no value is inferred from spend |
| M0-ANT-006 | Observe safe auth/authorization/rate-limit failure distinctions only when naturally encountered | Natural evidence is recorded; unavailable states are Blocked and not manufactured |
| M0-ANT-007 | Reconcile an observation with owner-visible authoritative billing/usage UI at the nearest valid time | Identity/scope/unit/time/latency/precision match or the exact discrepancy is recorded |
| M0-ANT-008 | Decide each Anthropic API capability for the observed organization/role/version scope | Matrix decisions, collection constraints, and contract proposals are complete |

### 12.6 OpenAI API usage, cost, and budget (`M0-OAI`)

| Scenario ID | Observation | Pass basis |
|---|---|---|
| M0-OAI-001 | Review current official organization/project usage, cost, billing, credit, spend-limit/alert, and admin-role documentation | Endpoint/field/role candidates and documented absences are recorded |
| M0-OAI-002 | Establish least-privilege credential-role category and organization/project scope with owner, without recording credentials | Required role/scope and unavailable lower-privilege options are documented |
| M0-OAI-003 | Execute one bounded approved read-only usage observation | Buckets, grouping, pagination, token/request/model/project/key-safe fields, latency, and timestamps are structurally recorded |
| M0-OAI-004 | Execute one bounded approved cost observation, if officially available | Exact money representation, currency, intervals, grouping, pagination, latency, and missingness are recorded |
| M0-OAI-005 | Determine official credits, hard/soft limits, spend alerts, budgets, and renewal/reset availability | Each is supported or explicitly absent/unknown; no inferred remaining budget is presented as provider data |
| M0-OAI-006 | Prove subscription/Codex allowance and API billing are separate resource pools | Source/scope evidence prevents accidental merging or double counting |
| M0-OAI-007 | Observe safe auth/authorization/rate-limit failure distinctions only when naturally encountered | Natural evidence is recorded; unavailable states remain Blocked |
| M0-OAI-008 | Reconcile an observation with owner-visible authoritative billing/usage UI at the nearest valid time | Identity/scope/unit/time/latency/precision match or exact discrepancy is recorded |
| M0-OAI-009 | Decide each OpenAI API capability for the observed organization/project/role/version scope | Matrix decisions, constraints, and contract proposals are complete |

### 12.7 Ollama API usage, cost, and budget (`M0-OAPI`)

| Scenario ID | Observation | Pass basis |
|---|---|---|
| M0-OAPI-001 | Review current official Ollama API/cloud documentation for usage, token, request, cost, credits, budgets, account/team, and auth roles | Candidate official sources and explicit gaps are recorded |
| M0-OAPI-002 | Establish whether API billing identity is distinct from subscription/workspace/local-runtime identity | Resource relationships and owner-confirmation requirements are documented |
| M0-OAPI-003 | Execute one bounded approved read-only usage/cost observation only if an official source exists | Safe fields, exact units/money, scope, buckets, pagination, latency, and rate impact are structurally recorded |
| M0-OAPI-004 | Determine whether per-response token/cost metadata can account for already-running tools without proxying or content capture | Coverage and limitations are documented; proxying is not introduced |
| M0-OAPI-005 | Determine official credits, limits, budgets, reset/renewal, concurrency, and queue availability | Each capability is supported or explicitly absent/unknown |
| M0-OAPI-006 | Reconcile available official data with the owner-visible authoritative surface | Scope/unit/time/precision match or discrepancy is recorded |
| M0-OAPI-007 | Decide each Ollama API capability for the observed account/team/role/version scope | Matrix decisions, constraints, and contract proposals are complete |

### 12.8 Linux process and session observation (`M0-LNX`)

| Scenario ID | Observation | Pass basis |
|---|---|---|
| M0-LNX-001 | Review official Linux process/filesystem interfaces available under the owner's privilege | Approved OS source list, permissions, race conditions, and prohibited sources are documented |
| M0-LNX-002 | Observe real running Claude, Codex, and Ollama process identities without changing launch workflow | Provider executable, PID/start-time tuple, parent PID, state, and observation timestamp are safely captured or unavailable |
| M0-LNX-003 | Validate parent/child OS ancestry for representative naturally running main agents/subagents/wrappers | Proven relations and wrapper/reparent/orphan ambiguities are recorded |
| M0-LNX-004 | Evaluate PID reuse and process-exit race handling using naturally observed lifecycle evidence | Required validation tuple and unknown-on-conflict behavior are defined without inducing process termination |
| M0-LNX-005 | Evaluate working-directory/project-label visibility and privacy | Permission, symlink/path behavior, redaction, and UI exposure rules are documented |
| M0-LNX-006 | Evaluate CPU, memory, elapsed time, and process-state fields and units | Source, sampling semantics, precision, permissions, and freshness are documented |
| M0-LNX-007 | Evaluate provider session metadata linkage to process identities | Safe join keys/evidence or unresolved gaps are recorded; no environment/memory/terminal read is used |
| M0-LNX-008 | Evaluate parent/subagent session hierarchy using OS ancestry plus safe provider evidence | Confidence/conflict rules are documented; OS ancestry alone is not mislabeled as provider semantics |
| M0-LNX-009 | Inventory observable model, session ID, tokens/context, activity, errors, and wait-state evidence across providers | Each field is source-scoped; content-bearing fields are excluded |
| M0-LNX-010 | Evaluate state evidence for working, waiting, idle, quota/auth/error, exited/crashed, unknown, and possible-stall inputs | Definitive versus inferred signals and unavailable states are documented; no states are manufactured |
| M0-LNX-011 | Prove arbitrary environment, process memory, terminal content, prompts/responses/tools/source are outside the approved observation path | Procedure and retained evidence contain none of the prohibited sources |
| M0-LNX-012 | Reconcile that no process input/signal/restart/attach or provider-file mutation occurred | Pre/post safety checks pass or scenario fails |
| M0-LNX-013 | Decide Linux platform capabilities and limitations for the exact kernel/permissions/provider versions observed | A04-LINUX dossier, safe source allowlist, and unknown behavior are complete |

## 13. Workstream execution specifications

### WS-00 — Common environment and evidence governance

**Inputs:** approved plan, owner availability, repository revision, evidence-custody choice.

**Sequence:**

1. Complete M0-COM-001 and create the external custody register.
2. Complete the safe platform/version inventory before any provider-specific command.
3. Create an official-source register and candidate-operation register.
4. Review evidence sanitization using a non-provider structural record.
5. Issue separate preflight packets for each subsequent execution block.
6. Reconcile side effects after every block and maintain the scenario ledger.

**Owner checkpoints:** approve evidence location/retention; map opaque aliases locally; confirm installed tools are not to be updated; approve every non-zero network request budget.

**Completion:** M0-COM-001..006 Passed; M0-COM-007 is Passed for each executed run; remaining workstreams have reviewed inputs. M0-COM-008 passes only at final synthesis.

### WS-01 — Claude

**Questions:** subscription window visibility; structured source availability; auth-health states; safe local session/token/model/activity/hierarchy fields; version detection; account/session/process correlation; default-profile observability; future isolated-profile questions.

**Sequence:** official documentation -> installed version/help review -> owner visual/status comparison -> path/file schema classification -> approved field reads -> naturally running process/session correlation -> decision matrix.

**Owner checkpoints:** identify plan class and opaque alias; open authoritative UI/status surface; confirm any local profile/root target; confirm all account-switch/login observations remain out of scope unless separately approved.

**Output:** Claude capability matrix and A01/M02/M03/M04/M05/M06 handoff entries.

### WS-02 — Codex

**Questions:** subscription status windows/credits; structured/app-server source; auth-store category; safe `CODEX_HOME` session metadata; named configuration profile versus home isolation; account/process/session correlation; version behavior.

**Sequence:** official documentation -> installed version/help review -> owner status comparison -> state-root/schema classification -> approved fields -> naturally running process/session correlation -> separate later-experiment questions -> decision matrix.

**Owner checkpoints:** identify plan class/opaque alias; open authoritative status surface; approve target state root; explicitly confirm no logout, login, profile switch, or managed-home experiment is performed.

**Output:** Codex capability matrix and A02/M02/M03/M04/M05/M06 handoff entries.

### WS-03 — Ollama product/subscription/local runtime

**Questions:** personal/team/organization/workspace semantics; current/legacy plan class; included/purchased credits; reset/concurrency/queue; local/cloud separation; local service process/model/resource metrics; log/state privacy; authentication and correlation.

**Sequence:** official documentation -> installed client/service version -> owner resource classification -> official subscription comparison -> supported local endpoint/tool review -> safe local metadata review -> identity/resource separation -> decision matrix.

**Owner checkpoints:** confirm account/workspace relationships using aliases; classify current/legacy plan locally; approve any daemon/API observation and host; confirm no model generation is initiated for discovery.

**Output:** Ollama product/local capability matrix and A03/M02/M03/M04/M05/M06 handoff entries.

### WS-04 — Anthropic API

**Questions:** least-privilege role; organization/workspace/key-safe scopes; usage/cost buckets/grouping/pagination; data latency; exact currency; credits/budgets/limits; rate/cost constraints; source reconciliation.

**Sequence:** official documentation -> role/scope review -> owner authorizes bounded credential use locally -> approved read-only usage/cost requests -> owner UI reconciliation -> capability decision.

**Owner checkpoints:** supply credentials only through the approved local secret mechanism; confirm organization/workspace aliases; approve request count/cost; perform authoritative UI comparison. The operator never sees or records secret values.

**Output:** Anthropic API capability matrix and A01/M02/M03/M04/M05 handoff entries.

### WS-05 — OpenAI API

**Questions:** least-privilege admin role; organization/project/key-safe scope; usage/cost grouping and pagination; credit/limit/alert availability; data latency; subscription versus API-pool separation; reconciliation.

**Sequence:** official documentation -> role/scope review -> owner authorizes bounded local credential use -> approved read-only usage/cost requests -> explicit resource-pool separation -> owner UI reconciliation -> decision.

**Owner checkpoints:** same secret and request-budget controls as Anthropic; owner confirms organization/project aliases and authoritative comparison; no Codex subscription credential is assumed to grant API billing access.

**Output:** OpenAI API capability matrix and A02/M02/M03/M04/M05 handoff entries.

### WS-06 — Ollama API

**Questions:** existence of official usage/cost/budget interfaces; account/team scope; relationship to cloud subscription; per-response tokens/cost coverage; ability to observe existing clients without proxying; credits/limits/concurrency.

**Sequence:** official documentation -> identity/resource relationship -> official read-only request only if available -> existing-client coverage analysis -> owner comparison -> decision. Absence of an official source is recorded and does not trigger private-endpoint discovery.

**Owner checkpoints:** classify account/team/workspace aliases; approve any documented request; confirm no proxy insertion, request interception, or generated inference call.

**Output:** Ollama API capability matrix and A03/M02/M03/M04/M05 handoff entries.

### WS-07 — Linux process/session observation

**Questions:** safe OS sources; PID/start identity; hierarchy/wrappers/reparenting; working-directory privacy; CPU/RAM/state semantics; process/session join keys; provider session hierarchy; definite/inferred state signals; exclusion of environment/memory/terminal/content.

**Sequence:** official Linux interface review -> owner identifies naturally running representative agents -> approved process metadata observation -> provider-safe session linkage -> hierarchy/state comparison -> pre/post side-effect reconciliation -> platform decision.

**Owner checkpoints:** identify representative running agents locally; confirm processes may be observed; validate hierarchy at a human level; do not create/terminate agents solely for M0; approve whether working-directory labels may enter external evidence.

**Output:** Linux platform capability matrix and A04-LINUX/M06/M02/M03 handoff entries.

### WS-08 — Cross-source identity and capability synthesis

**Sequence:**

1. Compare identity layers and resource pools without copying sensitive evidence into Git.
2. Mark every proposed automatic correlation Strong/Corroborated, every manual relation Owner confirmed, and all weaker/conflicting relations Unresolved.
3. Check that subscription/API/local-compute pools remain distinct.
4. Apply the capability rubric at provider/version/plan/role/source granularity.
5. Record contract impacts and unresolved questions.
6. Conduct owner/security/test-integrity review.
7. Produce handoff packets only after scenario and custody ledgers reconcile.

## 14. Capability decision rubric

### Decision unit

One decision applies to exactly one tuple:

```text
provider product + capability + source + provider/tool version range
+ plan/account/resource class + credential role + platform
```

Never generalize one observed account, version, role, or plan into provider-wide support.

### Required dimensions

| Dimension | Required finding |
|---|---|
| Authorization | Officially permitted source and least-privilege role/access |
| Safety | Read-only behavior demonstrated; prohibited data and mutations excluded |
| Semantics | Scope, units, windows, timestamps, reset, null/missing, precision understood |
| Identity | Subject/resource can be identified or explicitly remains unresolved |
| Stability | Source class, schema/version detection, drift behavior, verified range known |
| Freshness | Source time, collection time, provider latency, staleness policy understood |
| Reliability | Timeout, rate/cost, pagination, partial/failure behavior understood |
| Provenance | Every retained field can carry source/version/confidence evidence |
| Verification | Real scenario result and owner comparison exist where required |
| Operability | Collection can fail safely without affecting other providers/agents |

### Decisions

- **Supported:** all mandatory dimensions are sufficiently understood; source is documented/safe; real scenario passed for the exact scope; no unresolved issue can materially change implementation.
- **Experimental:** source is brittle/undocumented or incompletely stable but has an approved isolation/threat model and explicit opt-in. Under this plan, private/browser sources cannot receive this decision because their execution is not authorized; they can only be proposed for later review.
- **Deferred:** value is plausible, but required separate authentication/profile experiment, threat/ADR work, role/account availability, platform, cost approval, or contract decision is not available now.
- **Unsupported:** official/safe/authorized source does not exist, source semantics cannot be trusted, or required access violates project safety/privacy. Unsupported is an acceptable M0 outcome.
- **Unknown:** temporary discovery state only. M0 cannot exit with `Unknown` for an in-scope V1 capability unless the owner explicitly changes scope or accepts a blocking gap.

Confidence (`High`, `Medium`, `Low`) is recorded separately from decision. Confidence never upgrades an unsafe source.

## 15. Planned output artifacts

Only this execution plan exists at Draft creation. The following paths are reserved for later approved execution; they are not evidence until created and reviewed:

```text
docs/discovery/m0/
  README.md
  environment-inventory.md
  official-source-register.md
  approved-command-register.md
  scenario-ledger.md
  identity-correlation.md
  capability-decisions.md
  contract-impact-report.md
  handoff-matrix.md
  capabilities/
    claude.md
    codex.md
    ollama-product-local.md
    anthropic-api.md
    openai-api.md
    ollama-api.md
  platform/
    linux-process-session.md
  reports/
    m0-summary.md
```

Repository artifacts contain only E0/E1 evidence. Detailed E2 run evidence uses the `<M0_EVIDENCE_ROOT>` layout in section 6. No raw provider payload, local account map, credential, private path, prompt/content, environment dump, or screenshot is committed.

When discovery is complete, the root steward may separately authorize synchronized updates to requirements, architecture, contracts, risks, traceability, roadmap, and the planning registry. This plan does not pre-authorize those edits.

## 16. Dependency and contract impact

### Dependencies

- M0 adds no production or development package by default.
- Installed provider tools, browser UI, provider APIs, and Linux interfaces are observed as real external dependencies; they are not installed or upgraded by M0.
- A proposed discovery helper, parser, HTTP client, scanner, or capture tool requires dependency/license/security admission before use. Standard library availability does not by itself authorize broad capture.
- Exploratory code, if separately approved, remains outside production and cannot be promoted without a module plan and TDD.

### Contract proposals expected

M0 may identify proposals for:

- M02 stable provider identity, resource multiplicity, profile protection, owner confirmation, and unresolved-correlation representations;
- M03 capability manifests, source/stability categories, verified-version ranges, discovery outcomes, and provider-extension schema boundaries;
- M04 deadlines, request budgets, pagination, rate limits, concurrency, backoff, authentication-failure handling, and partial outcomes;
- M05 quota-window, credit, cost, budget, exact money, unit, reset precision, provenance, freshness, and unsupported/null semantics;
- M06 process identity, session identity, hierarchy, evidence/confidence, runtime fields, state signals, and unknown/conflict behavior;
- A01/A02/A03 provider-specific safe extensions and parser/version-detection rules;
- A04-LINUX safe process/filesystem ports and race/permission outcomes.

These remain proposed until contract synchronization. A source-shape finding does not dictate a domain field. Provider-specific fields stay in versioned extensions unless shared semantics and an ADR justify normalization.

### Compatibility and ADR triggers

An ADR/security review is required before proposing any of the following:

- process environment access;
- private/browser endpoint or browser automation;
- credential copying or a new secret store;
- modification of default profiles;
- login/profile-isolation experiments;
- process control or request proxying;
- raw provider payload retention;
- remote collection or non-loopback exposure.

## 17. Ordered execution gates

These are dependency gates, not calendar estimates or delivery promises.

### G0 — Plan review and approval

**Entry:** specification baseline exists.  
**Work:** owner, security, provider-system, test-integrity, and integration review this plan.  
**Exit:** plan is approved or revised; execution remains prohibited while Draft.

### G1 — Evidence custody and operation-review framework

**Entry:** G0 approved.  
**Work:** execute M0-COM-001; define external evidence custody, alias rules,
side-effect record, operation template, and stop/incident procedure; admit the
local/no-telemetry E1 scanner; and freeze the scenario ledger/assertion schema
required by `M0CTL-ASSERTIONS`.  
**Exit:** custody and approval controls pass review.

### G2 — Common environment baseline

**Entry:** G1 complete.  
**Work:** M0-COM-002..006; no provider account data collection.  
**Exit:** platform/tool versions and candidate roots are scoped; evidence sanitization is proven on safe structural data.

### G3 — Official-source and command review

**Entry:** G2 complete.  
**Work:** documentation-only scenarios for all providers; prepare exact operation packets.  
**Exit:** each executable scenario has an approved operation or is Blocked/Deferred; no unreviewed command remains in an execution packet.

### G4 — Local subscription/provider surfaces

**Entry:** relevant G3 packets approved and owner present.  
**Work:** Claude, Codex, and Ollama product/local scenarios, one bounded provider block at a time.  
**Exit:** subscription/local observations, safety reconciliation, and provisional matrices complete.

### G5 — Linux process/session observation

**Entry:** G2 complete; relevant G3 Linux operation packets are approved; the
signed per-run `M0-GATE-PREFLIGHT` passes; the owner is available; and
representative naturally running processes and provider-safe linkage questions
are known.  
**Work:** M0-LNX-001..013 without changing launch workflow.  
**Exit:** Linux source/safety dossier and correlation evidence complete; unavailable providers/process patterns remain visible.

**`M0CTL-G5-OPERATIONS`:** G5 cannot bypass G3 command/procedure review. Every Linux
OS or provider-local observation is bound to the exact approved operation and
assertion packet; an unavailable packet or owner makes the scenario `Blocked`.

### G6 — API usage/cost/budget surfaces

**Entry:** relevant G3 network/role/request budgets approved; owner installs no new credentials through chat or command arguments.  
**Work:** Anthropic, OpenAI, and Ollama API workstreams sequentially, stopping after unexpected auth/rate/cost behavior.  
**Exit:** API capability matrices and authoritative comparisons complete or explicitly Blocked/Unsupported.

### G7 — Identity and capability synthesis

**Entry:** G4..G6 ledgers and side-effect reconciliations complete.  
**Work:** WS-08; resolve duplication, resource-pool boundaries, identity confidence, capability decisions, and risks.  
**Exit:** every in-scope capability has a decision; no weak correlation is presented as automatic.

### G8 — Contract-impact and handoff review

**Entry:** G7 complete.  
**Work:** create isolated handoff packets for PLAN-M02/M03/M04/M05/M06/A01/A02/A03/A04-LINUX; root checks cross-plan consistency.  
**Exit:** contract gaps, dependencies, owners, Blocked scenarios, and future experiments are explicit.

### G9 — M0 exit review

**Entry:** G8 complete and M0-COM-008 reconciled.  
**Work:** owner/security/test/root sign-off; custody retention/deletion actions recorded.  
**Exit:** all M0 exit criteria pass. Only then can dependent module plans move from Waiting for discovery to Draft/contract review.

## 18. Owner-interaction checkpoints

The owner is required at the following points; absence means `Blocked`, not delegated credential handling:

| Checkpoint | Owner action | Agent action prohibited |
|---|---|---|
| OCP-01 Plan approval | Approve scope, non-goals, and safety budget | Starting discovery while Draft |
| OCP-02 Evidence custody | Select/protect external root and hold alias mapping | Recording real identities in Git/chat |
| OCP-03 Operation approval | Review exact command/request/path and side effects | Assuming status/help/API calls are harmless |
| OCP-04 Account/resource scope | Confirm opaque alias, plan class, org/workspace/project relation | Guessing from display names or current login |
| OCP-05 Interactive provider view | Open official dashboard/status and compare locally | Browser automation, cookies, credential capture |
| OCP-06 API credentials | Place/authorize least-privilege credential locally through approved mechanism | Viewing, printing, transcribing, or passing it in arguments |
| OCP-07 Running process identity | Identify representative existing agent/process/session and expected hierarchy | Creating, interrupting, or controlling an agent for convenience |
| OCP-08 Safety reconciliation | Confirm no profile/account/budget/agent change was observed | Clearing an unexpected effect without incident review |
| OCP-09 Capability decisions | Accept scoped limitations/Unsupported decisions or request separately governed research | Replacing gaps with inference |
| OCP-10 M0 sign-off | Review matrices, blocked items, custody/deletion, and handoffs | Advancing dependent plans without evidence |

Login/MFA/OTP is not expected in read-only M0. If an official read-only API setup requires owner authentication, it is a separate owner-performed prerequisite and needs an amended, explicitly approved packet; the values never enter evidence.

## 19. Stop and incident conditions

Stop the current operation immediately when any of the following occurs:

- a login, logout, update, install, write, consent, purchase, budget, profile, or configuration prompt appears;
- an operation differs from its approved executable, arguments, endpoint, method, host, role, path, output shape, or side effects;
- secret, cookie, auth header, credential material, email/identity, OTP/MFA, prompt, response, tool activity, source, terminal content, arbitrary environment, or unknown high-risk data appears;
- a default-provider file may have been changed, copied, moved, locked, or rewritten;
- a running agent reacts, receives input/signal, restarts, exits, pauses, or changes state plausibly because of discovery;
- account/resource identity is uncertain or contradicts the owner-selected alias;
- a request consumes unexpected credits, causes billable generation, reaches an unapproved host, redirects unexpectedly, or produces a rate limit;
- certificate/hostname verification is disabled or fails, an insecure transport
  override is proposed, a target host is outside the exact allowlist, a
  redirect is not the exact separately reviewed target, or credentials might be
  forwarded to a non-owning host;
- a path escapes an approved root, follows an unapproved symlink, is not the expected file type/owner/mode, or exceeds bounds;
- the provider/tool version or schema is outside the approved range;
- output cannot be sanitized at source or evidence custody fails;
- a private endpoint, browser cookie, traffic interception, process memory, terminal injection, arbitrary environment, or elevated privilege becomes necessary;
- repeated attempts would be required to obtain a desired result.

After stopping:

1. Do not retry or broaden access.
2. Protect running agents and provider state; do not perform cleanup that mutates provider data.
3. Quarantine accidental sensitive evidence locally without copying it.
4. Record a sanitized `Failed` or `Blocked` result and actual side-effect uncertainty.
5. Notify the owner/root/security reviewer.
6. Follow credential rotation/incident procedure if exposure is possible.
7. Require a new operation review, threat update, or plan amendment before resuming.

## 20. Handoff specifications

Every packet contains scenario statuses, scoped capability rows, official sources, sanitized evidence references, identity findings, side-effect reconciliation, unresolved questions, risk changes, proposed contracts, prohibited fields/sources, and exact downstream decisions needed.

### PLAN-M02 — Registry

Deliver:

- identity-layer and relationship map per provider;
- safe stable identifiers and their scope/lifetime/reuse behavior;
- account/profile/resource multiplicity and subscription/API/local-pool separation;
- owner-confirmation requirements, wrong/conflicting identity behavior, and unresolved mappings;
- default-profile detection/protection evidence and future managed-profile questions;
- data fields that are personal, prohibited, nullable, or unavailable.

Block planning decisions that depend on unproven stable identity or profile isolation. Relevant scenarios: M0-CLA-007..009, M0-CDX-007..009, M0-OLL-003/007..009, M0-ANT-002, M0-OAI-002/006, M0-OAPI-002, M0-LNX-007..008.

### PLAN-M03 — Provider system/protocol

Deliver:

- one capability row per scoped tuple;
- source classification, stability, verified-version ranges, schema/version signals;
- outcome/failure vocabulary gaps, partial/unsupported/version-drift behavior;
- provenance/freshness/confidence requirements;
- safe provider-extension needs and command/network/file boundary constraints.

M03 cannot approve a capability absent a matrix decision and real evidence. Relevant scenarios: all provider decision scenarios and M0-LNX-013.

### PLAN-M04 — Collection control

Deliver:

- documented rate limits, request/cost budgets, pagination and provider latency;
- safe polling constraints, timeouts, concurrency, cancellation, retry/backoff, and no-retry auth behavior;
- collection outcome distinctions and freshness/staleness triggers;
- source-specific interaction/owner requirements and unsupported collection modes.

Unknown rate/cost behavior blocks automated polling for that source. Relevant scenarios: structured/network-source scenarios for every provider and all natural failure observations.

### PLAN-M05 — Capacity

Deliver:

- native quota/billing windows kept separate;
- exact used/remaining/limit/credit/cost/token/request fields, units, currency, nullability, and resource scope;
- reset/renewal timezone and precision; observed/source/collected time availability;
- provider latency, reconciliation tolerance evidence, and unavailable fields;
- provider-reported versus derived boundaries and provenance inputs.

No normalization, forecast, or combined total may be planned from Unknown semantics. Relevant scenarios: M0-CLA-003..004, M0-CDX-003..004, M0-OLL-003..005/008, all ANT/OAI/OAPI usage-cost-budget scenarios.

### PLAN-M06 — Runtime observation

Deliver:

- safe provider session and Linux process fields, sources, units, timestamps, and version scope;
- process identity tuple, hierarchy, PID-reuse/race/conflict behavior;
- session/account correlation evidence and owner-confirmation boundary;
- definitive versus inferred state/activity/wait/error signals;
- token/context/model/project metadata availability without content;
- explicit exclusion proof for environment, memory, terminal, prompt/response/tool/source data.

Unproven correlation remains `Unresolved`. Relevant scenarios: provider local-session/correlation scenarios and M0-LNX-001..013.

### PLAN-A01 — Claude adapter

Deliver the Claude product/local matrix and the A01-owned Anthropic API matrix;
safe command/path/field/HTTP allowlists; source and version evidence;
identity/authentication behavior; quota/session and API
usage/cost/budget/project sources; safe extension needs; failure cases;
request/read costs; unsupported/deferred findings; excluded sources/fields; and
all Blocked later auth/profile-isolation scenarios.

### PLAN-A02 — Codex adapter

Deliver the Codex product/local matrix and the A02-owned OpenAI API matrix;
supported CLI/app-server/state/HTTP sources; source and version evidence;
`CODEX_HOME` and profile questions; authentication behavior and auth-store
category without contents; safe extension needs; quota/session/correlation and
API usage/cost/budget/project findings; failure cases; unsupported/deferred
findings; and the Blocked isolated-home/login experiment.

**`M0CTL-API-OWNERSHIP`:** M0 controls capability maturity only. A01 retains
the Anthropic API integration lane and receives every M0-ANT handoff; A02
retains the OpenAI API integration lane and receives every M0-OAI handoff. A
missing or unsupported source does not transfer either lane.

### PLAN-A03 — Ollama adapter

Deliver separate product/subscription, local-runtime, and API matrices; account/team/workspace/resource relationships; current/legacy plan scope; daemon/local metric sources; cloud/API usage/billing support or explicit absence; version/auth/failure rules; no-proxy limitation.

### PLAN-A04-LINUX — Linux platform adapter

Deliver approved OS interface/path source list; permission/platform/version scope; process identity and ancestry algorithms as evidence requirements, not implementation; race/PID-reuse/symlink/file safety; resource metric semantics; privacy classification; no-control guarantee; real platform scenario prerequisites.

### Handoff acceptance

A downstream planning agent rejects a packet when:

- scenario results or evidence references are missing;
- a conclusion generalizes beyond observed scope;
- identity/correlation is inferred from weak evidence;
- units/windows/reset/freshness semantics are unknown but treated as decided;
- source safety, side effects, version range, or credential role is unclear;
- Blocked/Not Run scenarios are omitted;
- raw/sensitive evidence is embedded;
- the packet prescribes cross-module internals rather than contract needs.

## 21. Entry criteria

Execution may begin only when all are true:

- this plan status is Approved by the owner/root/security/test reviewers;
- the owner is available for required checkpoints;
- exact scenario scope and opaque aliases are selected locally;
- external evidence custody, permissions, retention trigger, and sanitization are approved;
- stop/incident procedure is understood;
- initial operations have approved review records;
- no installation/update/profile/auth/account mutation is required;
- representative provider versions/accounts/processes needed for the first block exist or the scenario is explicitly Blocked;
- no overlapping agent is editing the same discovery artifacts;
- no unresolved question would cause materially different safety handling for the first block.

## 22. Exit criteria

M0 exits only when:

- every scenario in the master catalog is `Passed`, `Failed`, `Blocked`, or `Not Run`, with the latter three explicitly reviewed;
- every in-scope V1 provider/capability/source tuple has a `Supported`, `Experimental`, `Deferred`, or `Unsupported` decision; any residual `Unknown` is an explicit owner-accepted milestone blocker or scope change;
- exact provider/tool/plan/role/platform scope prevents overgeneralization;
- all retained fields have source, unit, time, precision, freshness, confidence, version, and privacy classification as applicable;
- subscription, API, organization/project/workspace, and local-compute resources are not conflated;
- account/session/process correlations have evidence strength and conflicts remain Unresolved;
- no default profile, running agent, provider account/configuration, budget, or credential was intentionally modified;
- no secret/content/arbitrary-environment data entered repository, chat, reports, or test fixtures;
- every executed operation has pre/post side-effect reconciliation;
- official-source, scenario, custody, capability, risk, and contract-impact records are owner/reviewer approved;
- each required downstream plan has an accepted isolated handoff packet;
- external E2 retention/deletion action is recorded;
- requirements/architecture/contract changes are queued for separate synchronized review rather than silently applied.

M0 does not pass because many scenarios passed. A Critical safety violation, hidden Blocked scenario, invented result, unresolved cross-module identity assumption, or secret/content leak blocks exit.

## 23. Unresolved decisions at Draft approval

These are intentionally unresolved until gated research/owner input; none may be answered by assumption:

1. Exact executable commands, API endpoints, request shapes, output formats, safe paths, and field allowlists.
2. Exact installed provider/service versions and official compatibility scope.
3. Which owner account/plan/resource aliases provide necessary coverage without exposing identity.
4. Exact least-privilege Anthropic/OpenAI/Ollama API roles and whether owner credentials of those roles are available.
5. Whether Claude or Codex exposes a supported structured subscription-usage interface for current installed versions.
6. Whether provider local state exposes safe identity/session/token/hierarchy fields without content or credentials.
7. Whether process-to-session-to-account correlation is Strong, Corroborated, owner-confirmed only, or impossible.
8. Ollama personal/team/workspace/current-versus-legacy resource semantics and official billing API availability.
9. Approved non-secret method for proving default-profile non-modification for each provider.
10. Filesystem atime/mount behavior and whether relevant local reads remain within the side-effect budget.
11. Exact request/rate/cost ceilings and evidence retention/deletion dates for each execution block.
12. Which rare auth/exhaustion/rate/failure states occur naturally; absent states remain Blocked.
13. Which findings require changes to requirements, contracts, data model, risks, ADRs, or the planning registry.

### Frozen G0 contract vocabulary

**`M0CTL-CAPABILITY-VOCABULARY`:** all M0 operation, matrix, ledger, and handoff
records use the `ProviderAdapterV1` `1.0.0-draft.2` vocabulary. The capability
is `authentication.reauthenticate` and the normalized/operation outcome is
`reauthentication_required`. Provider-native or legacy `reauthorization_required`
or `authentication_required` values may be recorded only as bounded source
codes and are mapped at the adapter boundary; they never enter normalized M0
records.

## 24. Approval record

| Role | Decision | Conditions | Date |
|---|---|---|---|
| Owner | Approved | Explicit 2026-09-18 direction to continue from the stated M0 approval checkpoint; limited to G0 plan approval and not account/provider/execution authority | 2026-09-18 |
| Root/integration steward | Approved | All G0 review findings resolved; exact digest must pass `AUTO-M0-G0`; G1 remains required | 2026-09-18 |
| Security/privacy reviewer | Approved | `M0CTL-NOREAD`, `M0CTL-NETWORK`, and `M0CTL-E1-ADMISSION` remain mandatory | 2026-09-18 |
| Test-integrity reviewer | Approved | `M0CTL-AUTH-SCOPE`, `M0CTL-ATIME`, `M0CTL-G5-OPERATIONS`, and `M0CTL-ASSERTIONS` remain mandatory | 2026-09-18 |
| Provider-system reviewer | Approved | `ProviderAdapterV1` `1.0.0-draft.2`, `M0CTL-CAPABILITY-VOCABULARY`, and `M0CTL-API-OWNERSHIP` remain mandatory | 2026-09-18 |

This approval exits G0 only. It does not authorize a command, provider request,
file/process/profile read, account access, credential use, evidence-root choice,
implementation, or scenario execution. G1 and the signed per-run
`M0-GATE-PREFLIGHT` remain mandatory and incomplete.
