# Module boundaries

## Boundary rules

1. Each module owns its invariants, use cases, persistence tables, migrations, and public contracts.
2. A module may import another module only through that module's published contract package.
3. No module queries or writes another module's database tables directly.
4. Cross-module workflows use application orchestration or versioned events, not hidden callbacks.
5. Shared code is limited to stable technical primitives. A `utils` dumping ground is prohibited.
6. Provider- and OS-specific code is always an adapter.
7. Import-boundary rules are machine checked in CI.
8. A module plan must name allowed directories and imports before implementation begins.

## Proposed source topology

The final plan may refine names, but not erase the boundaries.

```text
backend/
  src/agentmonitor/
    contracts/                 # versioned cross-module DTOs/events only
    modules/
      identity_access/
      registry/
      provider_system/
      collection_control/
      capacity/
      runtime_observation/
      alerting/
      operations/
    adapters/
      providers/
        claude/
        codex/
        ollama/
      platform/
        linux/
        macos/
      persistence/
      notifications/
    api/
    composition/
frontend/
  src/
    app/
    features/
    shared/
```

Within each backend domain module, separate domain objects/policies, application use cases, inbound contracts, outbound ports, and repository interfaces. Infrastructure implementations live outside the module.

## M01 — Identity and access

**Owns**

- single dashboard administrator identity;
- password-verification material;
- browser sessions and CSRF state;
- API-token metadata, scopes, hashes, rotation, and revocation;
- authentication/security audit events for AgentMonitor itself.

**Publishes**

- `Principal`, `SessionSummary`, `ApiTokenSummary`, `Permission`, `AuthorizationDecision`;
- authenticate/logout/token-management use cases;
- request-authorization port for the API boundary.

**Must not**

- know provider OAuth tokens or provider account login mechanics;
- own organizations, provider accounts, alerts, or application configuration;
- expose password hashes, session secrets, or API-token hashes.

**Primary consumers:** API boundary, audit/operations.

## M02 — Registry

**Owns**

- organizations/groups;
- provider definitions and installed-provider instances;
- accounts, friendly names, provider identities, and lifecycle;
- account-to-organization assignment;
- subscription/API/profile/project relationships;
- opaque provider credential/profile references and default-profile protection flag;
- account-specific configuration references.

**Publishes**

- `OrganizationView`, `AccountView`, `MonitoringProfileView`, `ProviderInstallationView`;
- account lookup by stable internal ID;
- identity-correlation confirmation use cases;
- registry change events.

**Must not**

- collect quota or process data;
- read credential contents;
- decide health based on usage;
- persist provider-specific secret fields.

**Primary consumers:** collection control, capacity, runtime observation, alerting, API.

## M03 — Provider system

**Owns**

- provider-adapter protocol and capability vocabulary;
- adapter registration and compatibility negotiation;
- capability manifests and stability classifications;
- adapter version and provider-version compatibility records;
- discovery result contracts.

**Publishes**

- `ProviderAdapterV1` and capability-specific ports;
- `CapabilityManifest`, `ProviderSource`, `CollectionOutcome`;
- adapter availability/compatibility events.

**Must not**

- contain Claude/Codex/Ollama implementation logic in its core;
- store account quotas, budgets, processes, or alerts;
- downgrade an unsupported capability to an inferred value silently.

**Primary consumers:** provider adapters, collection control, diagnostics.

## M04 — Collection control

**Owns**

- polling policy, due schedules, manual refresh requests, job leases, deadlines, retries, and backoff;
- collection run state and sanitized collection diagnostics;
- concurrency limits per provider/account/capability;
- idempotent dispatch to provider/platform ports.

**Publishes**

- `CollectionRunView`, `CollectionRequest`, `CollectionCompletedV1`, `CollectionFailedV1`;
- manual refresh and run-query use cases;
- collector health projections.

**Must not**

- interpret quota/business meaning;
- own current capacity or session state;
- implement provider calls;
- retry authentication failures without user action.

**Primary consumers:** capacity, runtime observation, alerting, diagnostics, API.

## M05 — Capacity

**Owns**

- subscription quota observations and windows;
- API spend, budget, credit, token, model, and project observations;
- provenance, freshness, precision, and confidence for capacity values;
- current capacity projection, normalized health, burn rate, and forecast policies;
- capacity history and retention behavior.

**Publishes**

- `QuotaWindowView`, `BudgetView`, `CapacityHealthView`, `CapacityObservationRecordedV1`, `CapacityHealthChangedV1`;
- current/history/forecast query use cases.

**Must not**

- fetch provider data directly;
- combine incompatible limits into a fabricated total;
- own alert lifecycle or account identity;
- return a derived value without derivation metadata.

**Primary consumers:** alerting, API, exports, dashboard.

## M06 — Runtime observation

**Owns**

- discovered process snapshots and safe process metadata;
- local provider session metadata;
- process/session/account correlation evidence;
- parent/subagent relationships;
- operational session state and possible-stall policy;
- runtime history and retention behavior.

**Publishes**

- `AgentProcessView`, `AgentSessionView`, `SessionTreeView`, `RuntimeStateChangedV1`, `PossibleStallDetectedV1`;
- current tree/history/manual-correlation use cases.

**Must not**

- control or inject input into processes;
- persist prompts, responses, tool arguments, source content, arbitrary terminal output, or arbitrary environment values;
- invent account ownership;
- interpret subscription quota.

**Primary consumers:** alerting, API, dashboard, future supervisor through a new versioned contract.

## M07 — Alerting

**Owns**

- threshold definitions and specificity resolution;
- alert rules, fingerprints, severity, state machine, deduplication, acknowledgement, snoozing, and recovery;
- dashboard notification projection and alert history.

**Publishes**

- `AlertView`, `AlertRuleView`, `AlertOpenedV1`, `AlertStateChangedV1`;
- configure/acknowledge/snooze/query use cases.

**Must not**

- send email in V1;
- recollect provider data;
- modify source observations;
- hide stale or unknown inputs.

**Primary consumers:** API, dashboard, future notification-delivery adapters.

## M08 — Operations

**Owns**

- health/readiness projections;
- configuration validation without secret values;
- application/version diagnostics;
- backup catalog, integrity verification, restore orchestration, and retention scheduling;
- sanitized diagnostics bundles and data exports;
- product audit trail not owned by IAM.

**Publishes**

- `HealthView`, `ReadinessView`, `BackupView`, `DiagnosticSummary`, `ExportJobView`;
- backup/restore/export/diagnostic use cases.

**Must not**

- bypass module query ports to construct exports;
- include secrets or content in artifacts;
- implement provider business rules;
- silently repair corrupt data.

**Primary consumers:** API, operator runbooks.

## A01–A03 — Provider adapters

Claude, Codex, and Ollama are separate adapters with separate module plans, versions, live scenario matrices, and failure boundaries.

Each adapter:

- implements only declared provider capabilities;
- invokes documented APIs/CLIs first;
- reads only approved paths and allowlisted fields;
- validates identity and output;
- maps provider data into published contracts;
- exposes provider-specific extension fields through a versioned allowlist;
- never imports another provider adapter.

## A04 — Platform adapters

Linux and macOS adapters will implement process inspection, path resolution, permissions, service integration, filesystem-safe reads, and platform diagnostics. Linux is planned and verified first. Platform logic cannot leak into domain modules.

## P01 — FastAPI boundary

The API boundary handles transport validation, authentication/authorization, idempotency headers, request correlation, version routing, and problem responses. It invokes application use cases and maps published views. It owns no business rules and does not query persistence directly.

## P02 — React web application

Frontend feature modules consume only the generated API client and documented event stream. Server state is not duplicated into a global client store without a documented UI-only need.

## Physical database, logical ownership

SQLite is physically shared, but tables are owned by exactly one module and use a module prefix. Cross-module foreign identifiers are stored as scalar IDs and validated through contracts; database-level foreign keys across modules require an explicit ADR because they couple migrations. Read models spanning modules are composed through query ports or dedicated projections owned by the consuming use case.

## Change ownership

A future sub-agent receives one primary module. It may change another module's public surface only after a contract-change proposal is approved. Parallel agents may not edit the same module or migration chain concurrently.
