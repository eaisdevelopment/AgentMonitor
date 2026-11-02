# M6 Ollama cloud implementation contract and dependency review

**Status: engineering decision for the owner-approved cloud plan; implementation and live validation not yet complete.** Baseline: commit `3d26b69` and [cloud plan](m6-ollama-cloud-implementation-change.md). This specifies the contract/architecture handoff; it is not a claim that credentials, accounts, data, a keyring item or provider responses were accessed. Owner approval and the narrow runtime exception are recorded in `AGENTS.md`. Requirements: M6-A01/A03/A04/A05/A07/A08/A09/A10, tickets M6-T004–007/T010–012/T014–018. M6-A02/A06 and M6 closure remain governed by the full execution plan.

## ADR: narrow Linux credential and cloud source boundary

**Decision.** Linux user-session Secret Service via the `secret-tool` executable is the chosen owner-managed credential store; one generated non-secret binding identifies exactly one AgentMonitor-managed item per registry account. One local interactive `agentmonitor ollama connect`-equivalent command (actual entry point must match packaging) lets the owner select organization/account by name and uses the tool's TTY password prompt. Never pass a key to the shell, CLI arguments, API, environment, logs, test evidence, or agent. The dashboard supplies account management and instructions, not a browser credential field. `secret-tool store` prompts on a TTY; it also permits stdin input, but the recommended operator flow must use a local TTY, as documented in the [Ubuntu manual](https://manpages.ubuntu.com/manpages/noble/man1/secret-tool.1.html). AgentMonitor never captures the input in its enrollment process. For reads the private runtime subprocess captures `lookup` stdout in a bounded pipe and applies it only as the HTTPS bearer header to the official balance route. Do not echo it, include it in exceptions, export it in diagnostics or tracebacks, or use shell execution. The agent never views it. Safe subprocess stdout capture still puts the key in process memory; no secure zeroization is promised.

`secret-tool` selects items by attribute equality and `clear` removes all matching unlocked items. Reserve at least `application=agentmonitor`, `provider=ollama`, `purpose=balance`, `binding=<cryptographically-random opaque-id>`; never use an email or secret as an attribute. All four attributes are mandatory for store, lookup and clear, and the schema rejects duplicate active bindings. A random replacement binding on rotate avoids overwriting a known-good item until new enrollment succeeds. If distinct accounts have the same friendly label, show organization and a short nonsecret disambiguator; do not prompt for opaque IDs. The runtime must not invoke `search`, whose output can expose item details. Attribute matching is not an OS security boundary against other same-user processes.

**Lifecycle and crash recovery.** Create a pending registry binding first; a local owner operation stores its fresh item then atomically marks the binding active. A pending item after a crash is visible for owner cleanup; a failed store leaves the old active binding untouched. On rotation activate the new binding before scheduling deletion of the old item. Archive/delete or disconnect atomically disables scheduling and marks the dedicated binding `cleanup_pending`; local cleanup clears only that binding's item and then records completion. Locked/unavailable store or failed clear must remain visible as cleanup pending. Never silently claim provider-side key revocation; owner may revoke it through Ollama. Serialize per-account mutations and ensure an in-flight poll checks binding generation before committing results. No shared keyring item between account records in v1.

The protected default Ollama profile is never read, relocated or modified. Store/bus absence, locked state, timeout, session logout and reboot must result in sanitized `store_unavailable` or `store_locked` without plaintext fallback; retry after owner unlock, no hidden interactive prompt from an unattended scheduler. Secret Service may require user prompts and transport between processes: [specification](https://specifications.freedesktop.org/secret-service/latest/unlocking.html). Restrict noninteractive behavior based on what the real client supports; if `secret-tool lookup` causes unattended prompts or cannot distinguish timeout/locked/missing reliably, the adapter must fail closed with an honest combined unavailable state rather than invent a distinction. All local subprocesses use an exact executable path, no shell, short deadline and limited output. Avoid D-Bus address logging and do not infer that the active daemon implies an unlocked service.

**Network.** Only `GET https://ollama.com/api/balance` with TLS certificate and hostname verification; no redirects, URL overrides, retries, query/body, proxy or user-controlled destination. Prefer Python stdlib `http.client.HTTPSConnection` and `ssl.create_default_context()` to avoid implicit environment proxy settings and a new HTTP package. Set explicit connect/read and whole-operation deadline, maximum headers/body, single request and safe exception mapping. Parse JSON with `Decimal` and reject duplicate keys, nonfinite/excessive values, invalid timestamps, oversized data and unexpected combinations; do not log raw data. Documented schema and rate limits: [Ollama balance API](https://docs.ollama.com/api/balance). An authorized response confirms balance endpoint access only, never provider identity.

## Versioned contract impact

The existing `CTR-PROV-004` `ProviderOperationRequestHeaderV1` carries opaque `access_grant_refs`, not keys; the adapter can resolve a reference only at the private execution boundary. `CTR-PROV-001/003` manifest currently declares installation and model catalog as pending and has no cloud capability. Add an appropriately versioned Ollama subscription-quota capability and documented source with one request, one concurrent operation, no automatic retries and at least 60 seconds interval; technical admission requires evidence. Do not expose raw keyring references on the public API.

`CTR-REG-002` `AccountViewV1` currently requires `matched` or `owner_confirmed` for effective monitoring. Use existing **owner-confirmed** workflow for the owner's account association only if its actual workflow accepts that provenance; otherwise add a versioned owner-asserted association, never call it provider verified. `CTR-REG-003` monitoring profile supplies managed-profile identity and lifecycle; do not treat it as permission to touch a provider default profile. `CTR-REG-005` identifies account resources and requires an account owner; do not use separate account-scoped resources to claim verified team identity. Implement binding reference and generation in an internal registry-owned table with unique account-active invariant and transactional cleanup states; only approved M02 ports cross into M03 and API. Existing `AccountViewV1` need not include a binding or keyring path. All mutable endpoints require existing write authorization and CSRF/origin policy.

`CTR-CAP-001` is already exact and uses `ExactQuantityV1` with tokenized unit, `ProviderQuotaWindowInputV1` and a distinct `remaining_ratio`. Recommended mapping:

| Native source | window key | remaining | limit | remaining ratio | reset |
|---|---|---|---|---|---|
| `included.balance_usd`, `allowance_usd` | `ollama_included_credits` | exact quantity `usd` | exact quantity `usd` | derived only when a real positive allowance is present, marked derived | `period.until` only if present |
| `purchased.balance_usd` | `ollama_purchased_credits` | exact quantity `usd` | unknown | unknown | unknown |
| `included.session.remaining_percent` | `ollama_session` | unknown | unknown | exact decimal source percent divided by 100, `provider_reported` | `session.resets_at` when present |
| `included.weekly.remaining_percent` | `ollama_weekly` | unknown | unknown | exact decimal source percent divided by 100, `provider_reported` | `weekly.resets_at` when present |

No mixing native money and ratios, no guessed zero, denominator or reset. Existing contract has `reset_at` but no provider period start; add a versioned observation period with source start inclusive/end exclusive, carrying both through current/history/API if supplied, or mark the cloud scope incomplete until implemented. Exact values outside `CanonicalDecimalV1` bounds must fail safely rather than silently round. `ExactMoneyV1` exists but M05 windows use `ExactQuantityV1`; `usd` is an explicit native unit with no implicit exchange rate. Preserve decimal serialization as coefficient/scale through generated client. Do not silently reuse forecast/alert behavior without verifying it understands `usd`, unknown thresholds and purchased balances. No global sum across unknown or owner-asserted sharing. Add scope provenance `unresolved|owner_asserted|provider_verified`, and an optional shared-pool identifier only when supported by actual evidence; absent sharing evidence means separate views without aggregate totals. Changes to closed enums or required fields require a versioned contract and migration/ADR, not a silent v1 break. Existing `capacity` router maps generic windows and exact fields; overview and account UI must add readable amounts and source labels, preserve all existing consumers, and expose stale/access/unavailable states.

## Rate limiter and operational contract

Ollama documents 10 requests/minute/user shared by keys/devices; team balances are shared. Single instance: durable global `next_allowed_at` plus fair cursor, acquire transactionally before each request, >=60 seconds spacing plus jitter across all Ollama cloud accounts, with one request in flight. Persist a 429 `Retry-After` deadline, apply globally when identity equivalence is unknown, and honor it after restart. Use bounded exponential fallback when the header is absent/invalid; never truncate a provider-supplied wait to a shorter time. Wall-clock jumps require conservative handling; no data collected early after restart. Other applications may consume the provider limit; rate limiting remains possible. Multi-process/multi-host simultaneous collection is unsupported until an actual cross-process coordination mechanism exists. Manual refresh uses the same limiter; old observations stay visibly stale. Preserve existing Claude/Codex jobs and app availability during any Ollama error.

The additive M04 seam is `CTR-COL-008 OllamaCloudAdmissionV1`, traced to
`M6-A07`, `M6-A09`, `FR-COL-003`, `FR-COL-005`, `FR-COL-006`, and
`FR-COL-008`. It carries create-once admission identity, scheduler owner,
bounded UTC lease, bounded jitter, exact selected schedule/account, fencing,
closed admission decision, sanitized terminal outcome and optional parsed
`Retry-After` seconds. Only `acquired` authorizes provider dispatch; active or
terminal replay never grants a second dispatch. M04 owns the durable global
gate and fair cursor. A03 and integration composition consume the seam but do
not write M04 tables directly. CTR-COL-001 remains request intent and
CTR-COL-002 remains collection-run state; overloading either would break their
existing replay and side-effect meaning.

## Schema compatibility and rollback consequences

`v1_0708` is an additive M04 migration: it adds the global Ollama cloud gate,
create-once admission rows and their indexes without altering or rewriting
existing IAM, registry, provider, collection, capacity, runtime or alert rows.
A real `v1_0707` database remains readable by the current inspector as
`upgrade_required`; the offline `AUTO-MIGRATE` path accepts either `v1_0603` or
`v1_0707`, creates and verifies an owner-only pre-migration backup, and then
applies the immutable chain to `v1_0708`. The candidate binary requires `v1_0708`
for writes. The actual prior binary does not recognize `v1_0708` and reports
`unknown_revision`; it must not write that database. A prior-binary runtime
rollback test has not yet been performed.

There is no in-place downgrade and the migration never drops the new tables.
Binary rollback after applying `v1_0708` therefore requires stopping the
service and restoring the verified pre-migration `v1_0707` backup, or a
reviewed forward fix; merely starting an older binary against the newer file
is not a rollback. The canonical `AUTO-RESTORE` command remains blocked, and
no executable restore/prior-binary rollback has been proven, so live migration
is not yet ready. An upgrade preserving populated `v1_0707` data also remains
unverified. Disabling the Ollama cloud integration leaves the additive
technical rows in place and does not affect Claude/Codex schedules or provider
profiles. Admission rows grow by one bounded technical record per attempt, so
retention/purge policy remains follow-up work before claiming indefinite
operational storage. This implementation work uses isolated real SQLite files;
it does not migrate the live dashboard database or restart its service.

## Dependency and license review — Ubuntu-local admission recorded

The owner-approved GPL/LGPL system dependency is admitted for Ubuntu 24.04
amd64 local implementation in the
[M6 Secret Service dependency record](../../dependencies/m6-ollama-secret-service-admission.md).
It records exact installed origins, the resolved ELF closure, the conservative
150-package APT surface, all 41 legacy copyright-label gaps, current
maintenance/security evidence, alternatives and limitations. AgentMonitor
does not bundle or link the OS binaries. Unlock behavior, logout/reboot,
dynamic prompt paths, release SBOM/notices, redistribution and other platforms
remain unverified and are not admitted by that record.

## Verification and implementation order

1. Implement within the Ubuntu-local dependency admission conditions, confirm actual user-service session access without inspecting unrelated items, and resolve the exact enrollment/cleanup contract and schema migrations. Dependency admission is not runtime behavior evidence.
2. Land M02 and credential boundary, M03 source + capability, M04 durable limiter, M05 native windows/history/alerts, versioned API and generated UI as one coordinated end-to-end change. Keep provider implementation in its adapter, no direct cross-module table access. Design account identity as owner asserted unless independently proved. Preserve fallback/recovery without stopping agents.
3. Red-green-refactor meaningful no-I/O pure contract tests; use real SQLite, actual app/service/browser and real owner-provisioned source for boundary behavior; no mocks, recording, seeded telemetry or fabricated provider states. Verify rotation/crash/cleanup, no secret leak, DST/UTC and exact numbers, period fidelity, unauthorized/rate-limited/locked paths when naturally available, safe backoff/restart, history and alert deduplication, existing provider health. Record omitted scenarios accurately as blocked/not run. Verify with owner in official Ollama views, never request key in chat or screenshots.
4. Run the canonical full M6 completion gate against deployed clean revision, account for the local and cloud requirements and record sanitized evidence, not a partial success. This review supplies neither a completed executable gate nor live verification.

## Additional user-service reachability evidence

On 2 November 2026 an isolated, short-lived systemd user service successfully
queried the user bus for `org.freedesktop.secrets` and exited normally. This
is evidence of bus-name reachability from a user-service context only. It does
not prove the login collection is unlocked, that unattended lookup succeeds,
or that behavior survives logout or reboot; no secret items were created,
listed, read, or changed. The transient service was collected after exit.

The installed recursive apt dependency-candidate inventory is recorded in
[`m6-keyring-system-dependency-inventory.json`](../../evidence/m6-keyring-system-dependency-inventory.json).
It contains 150 installed packages; all 41 packages without a machine-readable
`License:` field now have a grouped manual copyright review and exact installed
file hash. The inventory still includes potential alternatives and is not a
runtime trace or release SBOM. Ubuntu's machine-readable security status at
the recorded review time had no pending update intersecting the inventory,
which is not proof of no vulnerability. No package update or reboot occurred.
