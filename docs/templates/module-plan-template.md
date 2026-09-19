# Module plan: MNN — module name

- Status: Draft
- Plan version: 0.1.0
- Module contract version: proposed version
- Owner: role/name
- Reviewers: integration, security, test, operations roles
- Requirements: IDs
- Acceptance criteria: IDs
- Dependencies: module/contract versions
- Target milestone: Mx
- Approved by/date: pending

## 1. Outcome and boundaries

### Outcome

Define the user/system outcome in measurable terms.

### In scope

- Behavior owned by this module.

### Out of scope

- Adjacent or deferred behavior.

### Ownership

List owned domain concepts, tables/migrations, configuration, API routes if applicable, events, jobs, and documentation.

### Allowed and forbidden dependencies

List permitted imports/contracts and explicitly forbidden modules, tables, provider details, frameworks, and I/O.

## 2. Requirements and traceability

| Requirement/AC | Planned behavior | Contract | Test/scenario IDs | Evidence gate |
|---|---|---|---|---|
| ID | Behavior | Name/version | IDs | Gate |

Record ambiguities and approved interpretations. Do not invent behavior to fill a requirement gap.

## 3. Domain design

Define:

- entities, value objects, policies, states, and invariants;
- state machines and valid/invalid transitions;
- units, precision, time-zone and clock semantics;
- identity/correlation/deduplication rules;
- idempotency and concurrency behavior;
- degradation and recovery behavior.

Include diagrams only where they materially clarify a relationship or sequence.

## 4. Public contracts

### Published ports

For each command/query/event, specify name, version, input/output schema, preconditions, postconditions, errors, idempotency, authorization, and compatibility promise.

### Consumed ports

List exact owner, contract, version range, failure behavior, and fallback/degradation behavior.

### Contract change assessment

State whether the plan adds, changes, deprecates, or removes API/event/provider/database behavior. Link any required ADR and migration plan.

## 5. Data and persistence

Specify owned tables, keys, indexes, constraints, transaction boundaries, migrations, retention, deletion, backup/restore, and repository interfaces. Identify sensitive and prohibited fields. State PostgreSQL portability concerns.

## 6. External and platform boundaries

For each provider, OS, filesystem, process, email, or network boundary, define the adapter interface, official/public source, capability checks, timeout, retry/backoff, rate limiting, parsing confidence, provenance, safe failure, and real verification method.

## 7. Security and privacy

Document authentication/authorization, secret handling, least privilege, input/path/process validation, redaction, audit behavior, abuse cases, trust boundaries, and data-minimization proof. Update the threat model when needed.

## 8. Configuration and operations

List configuration keys without real values, defaults, validation, ownership, reload/restart behavior, and secret classification. Define health/readiness, structured logs, metrics stored locally, diagnostics, backup/recovery, and operator procedures.

## 9. Test design before implementation

### Test inventory

| Test ID | Layer | Requirement | Real dependencies | Initial failure expected | Pass condition | Owner/live coordination |
|---|---|---|---|---|---|---|
| ID | Pure/DB/API/browser/platform/provider | ID | Dependencies | Reason | Assertion | Owner |

### Integrity rules

- Pure domain tests may construct values but perform no I/O.
- Persistence uses real SQLite and real migrations.
- API uses a real running application over HTTP.
- UI uses the real built UI in a real supported browser.
- Platform/provider tests use actual target systems/accounts.
- No mocks, fakes, stubs, emulators, recorded responses, seeded telemetry, or placeholder UI values.

### Failure, migration, and recovery scenarios

Cover malformed/partial inputs, access denial, expired authentication, exhausted credits, rate limits, timeouts, concurrent collection, process exit/reuse, clock/window changes, restart, migration, backup restoration, and safe degradation as relevant.

## 10. Implementation increments

Each increment must produce one vertical, verifiable behavior and follow red-green-refactor.

| Increment | Files/area | Failing test first | Production change | Refactor/documentation | Exit evidence |
|---|---|---|---|---|---|
| I-01 | Scope | Test ID | Change | Work | Evidence |

Describe ordering, parallel-safe work, shared-file ownership, and integration points. No increment may bypass a contract through direct database or internal imports.

## 11. Documentation outputs

List module documentation, API/OpenAPI updates, ADRs, configuration reference, operator runbooks, troubleshooting, diagrams, migration notes, and traceability updates.

## 12. Dependency and license impact

List proposed packages and exact purpose. Link admission evidence for license, maintenance, security, transitive dependencies, alternatives, and approval. Prefer no new dependency where the standard library/current stack is sufficient.

## 13. Risks and unresolved decisions

| Risk/question | Likelihood/impact | Mitigation or experiment | Owner | Trigger/deadline | Status |
|---|---|---|---|---|---|
| Item | Rating | Action | Owner | Trigger | Open |

## 14. Delivery and rollback

Define deployment order, compatibility window, migration/rollback, feature exposure, data recovery, release notes, and post-deployment checks.

## 15. Definition of ready

- [ ] Requirements and non-goals are approved.
- [ ] Boundaries, owners, and allowed paths/imports are explicit.
- [ ] Published and consumed contracts are versioned.
- [ ] Test cases and expected initial failures are designed.
- [ ] Real provider/platform coordination is scheduled where required.
- [ ] Security, privacy, license, migration, and operations impacts are reviewed.
- [ ] No unresolved issue permits materially different implementations.

## 16. Approval record

Record reviewer decisions, conditions, date, and approved plan/contract versions. Implementation does not start while status is Draft or Proposed.

