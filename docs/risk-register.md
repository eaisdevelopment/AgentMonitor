# Project risk register

## Scales and governance

- Likelihood: Low, Medium, High.
- Impact: Moderate, Major, Critical.
- State: Open, Monitoring, Mitigated, Accepted, Closed.

Risk owners are roles until individual module owners are assigned. Every module plan adds or links its specific risks. A risk is closed only with evidence; a design intention is not evidence.

| ID | Risk | Likelihood | Impact | Mitigation and prevention | Trigger/indicator | Owner | State |
|---|---|---|---|---|---|---|---|
| R-001 | Provider subscription quotas lack stable machine-readable interfaces. | High | Critical | Official-interface-first discovery; capability manifests; explicit unsupported/experimental states; no fake precision. | No documented output/API or incompatible plan results. | Provider system | Open |
| R-002 | Provider CLI/local schemas change without notice. | High | Major | Versioned parsers, provider-version recording, allowlists, safe unknown-version failure, live compatibility matrix. | New version or parse failure increase. | Adapter owners | Open |
| R-003 | A process/session cannot be reliably mapped to its launch account. | High | Critical | Evidence-based correlation, unresolved state, owner confirmation, no guessing; research isolated profiles separately. | Ambiguous/conflicting identity signals. | Runtime/registry | Open |
| R-004 | Monitoring modifies or corrupts a default provider profile. | Low | Critical | Read-only default-profile invariant, path/permission controls, owner-reviewed live tests, no write-capable discovery. | File mutation, login prompt, session disruption. | Security/adapters | Open |
| R-005 | Secret or prompt/response/tool/source/environment content leaks. | Medium | Critical | Data allowlists, minimization, redaction, artifact scans, bounded output, no raw-payload retention, incident stop rule. | Scanner finding or unexpected content field. | Security/all owners | Open |
| R-006 | Concurrent collectors exceed rate limits or contaminate observations. | Medium | Major | Leases, per-scope concurrency limits, idempotency, deadlines, adaptive polling/backoff. | Throttle, duplicate run, inconsistent timestamps. | Collection control | Open |
| R-007 | Stale/partial/unknown data appears as current available capacity. | Medium | Critical | Mandatory provenance/freshness/confidence, stale/unknown states, no cached-as-current fallback, UI disclosure. | Missing timestamp/source or provider disagreement. | Capacity/UI | Open |
| R-008 | Normalization hides incompatible windows or implies false forecast accuracy. | Medium | Major | Preserve native windows; derivation metadata; uncertainty; boundary/property tests; explanation UI. | Combined total or unlabeled forecast. | Capacity | Open |
| R-009 | Rare provider failure states are unavailable under the no-simulation policy. | High | Major | Separate pure policy from live integration; retain Blocked state; use incident evidence; only owner-approved safe scenarios. | Required live state cannot safely be produced. | Test/integration | Accepted |
| R-010 | Live tests consume credits or interrupt development. | Medium | Major | Owner coordination, read-only/low-cost scenarios, collection-cost limits, stop conditions, opaque aliases. | Unexpected spend, throttle, agent behavior change. | Live verification | Open |
| R-011 | SQLite locking, corruption, or growth becomes unsafe under retention. | Medium | Major | Transaction/WAL design, real measurement, integrity/backup/restore tests, bounded retention. | Busy errors, latency/storage limit, integrity failure. | Persistence/operations | Open |
| R-012 | PostgreSQL/remote migration is blocked by local/SQLite coupling. | Medium | Major | Repository/transport seams, portable types/SQL, API-only UI, portability review. | SQLite logic outside adapter or UI DB access. | Architecture | Monitoring |
| R-013 | Local authentication provides false security if exposed beyond loopback. | Medium | Critical | Loopback bind, strict host/origin, no default password, secure sessions/CSRF/scoped tokens; new threat model before remote use. | Non-loopback bind or proxy/public-host request. | IAM/deployment | Open |
| R-014 | Group/account aggregation leaks or double-counts resources. | Medium | Major | Stable IDs, one primary group, distinct resource pools, deduplication/aggregation invariants. | Totals differ from children or duplicate pool. | Registry/capacity | Open |
| R-015 | PID reuse/hierarchy ambiguity reports the wrong agent. | Medium | Major | PID plus start identity, bounded ancestry, executable verification, unknown on conflict, real process tests. | PID reuse, missing parent, wrapper ambiguity. | Runtime/platform | Open |
| R-016 | Stall detection creates noisy false positives. | High | Moderate | Evidence-aware exclusions, configurable ten-minute default, inferred label, dedup/snooze, live tuning. | Waiting sessions flagged or high dismissal rate. | Runtime/alerting | Open |
| R-017 | Dense mission-control UI is inaccessible or fails on smaller screens. | Medium | Major | Responsive priority, accessibility requirements, real-browser viewport/zoom tests. | Overflow, hidden critical status, a11y failure. | UI | Open |
| R-018 | A dependency introduces license, telemetry, vulnerability, or supply-chain risk. | Medium | Critical | Admission gate, permissive preference, lockfiles, SBOM/notices, scans and periodic review. | License/vulnerability/provenance alert. | Dependency reviewer | Open |
| R-019 | Hosted CI is mistaken for workstation/provider evidence. | Medium | Major | Separate evidence gates; owner-controlled T5/T6 reports; explicit Blocked/Not Run status. | Release lacks live matrix. | Integration steward | Open |
| R-020 | Backups contain secrets or cannot restore. | Medium | Critical | Minimized database, secret exclusion, future encryption decision, real integrity/restore exercises. | Restore failure or sensitive field found. | Operations/security | Open |
| R-021 | Reauthentication changes identity or loses history. | Medium | Critical | Stable identity, pre/post verification, wrong-account state, transactional relink, real owner-driven tests. | Identity mismatch or duplicate account. | Registry/adapters | Open |
| R-022 | Future routing relies on monitor-only contracts that cannot guarantee continuity. | Medium | Critical | Keep V1 read-only; require supervisor architecture, checkpoint semantics, consent/threat model, provider support and ADRs. | Attempt to inject/switch/restart via V1 paths. | Future architecture | Monitoring |
| R-023 | macOS support silently degrades during Linux-first delivery. | Medium | Major | Platform contract, no Linux logic in domain, real macOS gate, visible Blocked state. | Linux-specific dependency crosses adapter boundary. | Platform owner | Open |
| R-024 | Provider terms or policy constrain a proposed data source. | Medium | Critical | Use official mechanisms; policy/legal review before experimental/private sources; defer unsafe methods. | Scraping, cookie extraction, interception, private endpoint required. | Product/security | Open |

## Review cadence

- At module-plan approval, add module-specific risks and update linked project risks.
- At each observed provider/CLI release, review R-001 through R-006 and R-024.
- At every milestone exit, review likelihood, impact, state, triggers, and evidence.
- Before V1, no Critical risk may be silently open: mitigate it with evidence, obtain explicit owner acceptance with limitation, or block release.
- After incidents, update this register and link the post-incident record, ADR, or change plan.

