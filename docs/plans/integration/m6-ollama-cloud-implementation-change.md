# M6 Ollama cloud: account connection and balance delivery plan

**Current scope amendment:** the [4 November local deferral](m6-local-ollama-deferral-2026-11-04.md) removes local model/process prerequisites from M6. The cloud account, balance, history/alert, security and recovery requirements in this plan remain active. References below to separate local acceptance are superseded by that explicit owner decision.

**Status: Approved by the owner on 2 November 2026.** The owner subsequently selected the protected AgentMonitor-managed `.env` for Ollama cloud keys instead of OS Secret Service. This explicit decision supersedes the keyring-specific provisions below; it does not waive security review or constitute evidence of implementation or completion.

## Owner-approved credential storage amendment

On 3 November 2026 the owner placed the Ollama key in the selected `.env`
and explicitly instructed AgentMonitor to use it there. This also authorizes
runtime import from an explicitly named entry in that same protected file,
bound to the explicitly selected real account, without a terminal prompt.
The operator must not print the value or place it in arguments, environment,
logs or evidence. Import uses the existing guarded account-binding lifecycle,
preserves the original entry and unrelated configuration, and rejects unsafe,
missing, empty or ambiguous entries. This is an alternative to retyping the key,
not permission to inspect other credentials or provider profiles. Real import
and subsequent provider verification still require actual evidence.

The owner selects an existing account by name in a local, non-echoing terminal
and enters the key there. The deployment explicitly selects the existing `.env`
and the file must be owner-only (`0600`); no second `.env` is created. On this
installation the selected project directory is group-writable (`0775`): pinned
identity checks detect replacement but cannot prevent malicious same-group
directory changes. The existing directory permissions are preserved and this
residual risk remains documented. Each binding has a distinct named
entry with a base64-encoded value; encoding is not encryption. The worker scans the shared file and retains only its exact current binding entry for each request, through a bounded
private boundary, with no restart after rotation. The agent never sees the key.
Atomic replacement preserves unrelated entries, with a shared writer lock and
per-account credential lock; rotation activates the new binding before cleanup
of the old one, and disconnect disables access before removal. Interrupted
cleanup remains visible and retryable. The `.env` is excluded from backups,
diagnostics, logs and exports. Never alter provider profiles. No key is placed
in arguments, environment variables passed to the worker, dashboard HTTP,
screenshots, tests, evidence or chat. Successful real-owner setup and rotation
remain Not Run until actually performed. Existing Secret Service sections below
are historical and do not authorize a keyring-only implementation.

For the existing installation the owner selected
`/home/dev/Nextcloud/Code/AI/AgentMonitor/.env`. The dashboard currently starts
with the separate `service.env` configuration path; deployment must explicitly
bind the selected `.env` to both operator and worker, without copying values or
creating a second `.env`.

The service keeps a non-secret location fence while any binding is pending,
active or awaiting cleanup. If the configured path is changed while bindings
remain, restore the previous service path, disconnect or clean up every Ollama
binding, then configure the new path. Once all bindings are clean, the location
fence is released automatically. If the dashboard is down or its configured
path has changed, the local operator can use the retained non-secret location
for disconnect and cleanup only; it cannot enroll a new key in that mode. This
recovery requires no new approval.

After restoring an older database, managed `.env` entries may outlive their
binding records. The app retains the non-secret location while such entries
exist. The local operator can remove reserved-prefix orphan entries under a
shared binding-creation and credential-writer guard after M02 reports no
unfinished bindings; it can then reconnect the account. No SQLite transaction
spans file I/O. This candidate remains subject to real concurrency/crash and
security review; no entry values or opaque identifiers are shown to the owner.

## Outcome and scope

An administrator can add any number of Ollama accounts through existing organization/account administration, connect each to an owner-provided official API key on the server, and see its actual cloud balance, freshness, history and applicable alerts. SDK and EAIS are examples of administrator-created groups, never hardcoded identities. The provider's documented balance variations and possible team sharing are preserved, not flattened into invented percentages. Local-model and process functionality remains in the approved local plan and the overall M6 plan; this plan covers the cloud work and its integration, not the whole milestone.

Traceability: `M6-T004/T005/T006/T007/T010/T011/T012/T014/T015/T016/T017/T018`; `M6-A01/A03/A04/A05/A07/A08/A09/A10`; `FR-ACC-001..005`, `FR-QUOTA-001/002/004/006`, `FR-COL-003..008`, `FR-SAFE-001/002`, `AC-LIVE-003/005/007`, `AC-HIST-001`, `AC-ALERT-002`, `AC-UI-002..006`, `AC-OPS-003/006`. The ticket catalog and execution plan retain their dependencies and full definitions; this plan does not mark any ticket passed.

## Approved credential architecture

The owner-approved protected `.env` architecture above is authoritative. The local setup command selects the registry organization/account by readable name. The dashboard never accepts a key. Runtime applies the selected binding's key only to the permitted official balance request and returns sanitized observations. Owner-only filesystem protection does not prevent access by other processes running as the same user; complete memory zeroization is not guaranteed. A missing, unsafe or unreadable file produces an actionable unavailable state. Rotation and deletion do not revoke the provider-side key.

## Boundaries, contracts and data

Primary owner: Ollama provider adapter `M03`; supporting owners: `M02` registry, `M04` collection, `M05` capacity/history/alerts, API and `P02` dashboard. Implement through published versioned contracts; no adapter database access, domain-to-provider/framework/OS imports, dashboard-to-database access, or provider profile mutation. Update the OpenAPI contract and regenerate the client for any API extension. Inventory current contract versions during implementation: use compatible additive v1 changes only where valid; incompatible meaning or required fields require a versioned contract and migration/ADR, not an unannounced change.

* Registry: existing organization and account create/read/update/delete remain authoritative; provider selection is dynamic. Maintain a nullable opaque random `credential_binding_id` and non-secret state for each Ollama account, isolated to the managed credential component. Create records without credentials; edit labels/organization without changing the provider profile; disable/re-enable monitoring; rotate and disconnect locally. Account deletion removes its managed reference and, subject to explicit deletion semantics, its dedicated item; failures are reported for local cleanup. Never destroy a shared item while another record refers to it. No account email is inferred from a key.
* Connection state: `not_configured`, `pending`, `access_valid_identity_unresolved`, `unauthorized`, `rate_limited`, `store_locked`, `unavailable`; include sanitized observation time and actionable reason. Owner-entered name and organization are **owner asserted**. A successful balance GET proves access to that endpoint, not account identity, membership, team, or scope. Do not claim identity verification without authoritative evidence.
* Capacity: retain a versioned typed representation with `observed_at`, source and exact decimal USD amounts. Included-credit variant: `balance_usd`, `allowance_usd`, source period boundaries when supplied. Purchased credits: separate `balance_usd`, no invented allowance, percent or expiry. Legacy variant: separately labeled session/weekly `remaining_percent` and `resets_at` when supplied. Optional fields represent unknown, not zero; source-provided window/reset semantics and precision are retained. Reject malformed or unexpected responses safely rather than assuming their shape. Preserve original semantics through M05, history, API and built UI; use an additive discriminated schema if compatible, otherwise version it.
* Scope: a provider-proven shared pool can be represented once and related to multiple account records. Owner-described relationships carry `owner_asserted` provenance. If relationship is unknown, show each observation with its own unresolved scope and do not aggregate or present a combined total; do not deduplicate by email or claim multiple distinct pools. Alerts require comparable supported metrics and configured thresholds; no percentage alert for a monetary value without a real denominator. Stale values retain their observation time and stale label.
* Network: allow only HTTPS `GET https://ollama.com/api/balance`; reject redirects and arbitrary targets; set finite connect/read timeouts and response-byte limits, disable sensitive request/response logging, and report only allowlisted safe fields. No requests for models, prompts, source code, cookies, OAuth tokens or other provider content. Read-only upstream; credentials are stored only in the protected `.env` under the approved amendment above, never in database, browser, diagnostic output, evidence, backups, source or shell history. Avoid ever printing raw provider payloads or authorization headers.

## Rate and failure behavior

Ollama documents 10 balance requests per minute per user **across keys and devices**, with `Retry-After` on 429 ([official balance API](https://docs.ollama.com/api/balance)). As principal equivalence is unknown, serialize all cloud reads in one deployed AgentMonitor instance globally with at least 60 seconds between starts and bounded jitter; this is deliberately below the documented limit but cannot prevent other devices using the same allowance. Rotate fairly across enabled connections. Persist scheduler `next_allowed_at` and the parsed `Retry-After` deadline across process restart; when absent or invalid, apply bounded exponential backoff and jitter. No immediate retries, busy loops or cascading dashboard failures. Retain last successful observation as stale; surface 401/403, 429, timeout, network, unsupported response and unavailable managed credential distinctly without logging secrets. A multi-instance deployment requires a shared limiter before it is supported. Natural recovery resumes fairly when allowed.

## Work and verification, delivered as one scope

1. Record the owner-approved `.env` boundary, account cleanup semantics, contract impact and any needed ADR. Validate owner-only file protections and no-echo local input without inspecting existing secrets; verify operation after restart without modifying the provider profile.
2. Deliver versioned registry/API and M03 credential/HTTP boundary, M04 scheduler, M05 capacity/history/alert support, and the dashboard account setup, provider filter and readable balance views as a cohesive change. Document local setup, reconnect, rotation, disconnect, unavailable-file recovery, operating-system scope and provider-side revocation. Do not modify the default Ollama profile or interrupt running agents. Implement migration/rollback and generated-client updates as needed.
3. Follow meaningful red-green-refactor: record a failing test for each changed behavior before production implementation, then green and post-refactor evidence. Constructed values only in pure no-I/O domain tests. Real external boundaries use actual SQLite, HTTP service, browser and Ollama service/account; no mocks, fakes, recordings, seeded telemetry or test-only production behavior. Verify account CRUD and authorization, safe local enrollment/rotation/removal, no secret leakage, clean error presentation, HTTP destination restriction, parsing and money/legacy distinctions, shared-scope nonaggregation, rate scheduling/restart, stale/history/alerts, and ordinary Claude/Codex availability. Test locked, unauthorized and rate-limited behavior only if the real conditions occur safely; otherwise mark the corresponding scenario Not Run or Blocked rather than forcing disruptive changes or claiming success.
4. With the owner operating official authentication and local secret entry, perform a bounded real comparison of each available SDK/EAIS scope against Ollama's authoritative view, noting observed time, precision, ownership provenance and actual sharing. Record only sanitized outcomes; do not ask the owner to repeat unchanged prior evidence. If a scope is unavailable, record the actual limitation without pretending it was tested. Verify built browser including keyboard/mobile, real history and naturally available alert lifecycle; then run the canonical full M6 completion command against the actual checkout and deployment. Missing requirements or unavailable tests prevent a full-pass claim. This cloud slice does not waive local model/process work or other M6 requirements.

## Dependency, cost, operations and rollback

The approved `.env` path uses the existing Python standard library and adds no keyring or package dependency. Verify local terminal echo protection, file permissions, concurrency and recovery. Operational costs include local setup for each account, key rotation and monitoring of provider/API limits. API usage or billing implications and plan eligibility must be checked against the account's current official Ollama terms; no specific price or free allowance is assumed. The balance check itself must not initiate inference or purchase credits.

Roll out first to the existing local installation with the owner present for key provisioning, keeping the dashboard available; check existing providers before and after. Back up application data through the established procedure without exporting key material. Provide version-compatible rollback for schema/API changes and keep historic non-secret observations readable. Rollback removes/disables the managed integration only; no provider key revocation or default profile changes. Treat partially deleted references or locked-store cleanup as visible follow-up, not success.

## Approval and completion boundary

The owner approved this plan and the subsequent managed `.env` credential decision on 2 November 2026. The normal documented dependency/security and contract review remains required. Approval does not substitute for actual real-system evidence. The owner supplies keys only in the approved local prompt and performs any official login; the operator/agent performs implementation, tests and reporting.

## Workstation discovery (1 November 2026)

A read-only package and service inventory found `secret-tool` installed,
`libsecret-tools` and `libsecret-1-0` version `0.21.4-1build3`, and
`gnome-keyring` version `46.1-2ubuntu0.2`. The user service was active and
`org.freedesktop.secrets` was present on the user bus. No keyring items were
listed or read. This establishes availability of a service name only: it does
not establish unlock state, enrollment, dashboard-service access, restart
behavior, or fitness of the design.

Installed package copyright manifests enumerate LGPL-2.1+, BSD-3-Clause,
GPL-2+, Apache-2.0 and other file-specific terms; the GNOME Keyring manifest
also includes MPL and custom terms. This inventory is not a completed license
or transitive-dependency review and does not approve adding a dependency.

## 5 November 2026: verification after replacing a stored key

This is a correction within the approved cloud connection/rotation behavior,
not a new credential-entry method or a request for another owner approval.
The owner stored a replacement SDK key and clicked **Check connection**. The
real HTTP action returned `503 ollama_cloud_connection_unavailable`: the active
credential binding was generation 2, while the monitoring graph still named
generation 1. Initial enrollment had succeeded, but verification initiation
reused the old graph when the account record version had not changed.

M02 owns the correction. The existing atomic M02/M04 verification transaction
must reconcile an already owner-confirmed active account's graph with its exact
current binding before admitting the new check. Preserve the account's name,
organization, enabled monitoring choice, profile/resource identifiers and all
history; the earlier verification receipt must never validate the replacement
key. Keep exact expected-account-version, active-binding, target, lifecycle,
identity, idempotency and transaction guards. Retain the separate pending-only
initial-enrollment policy. No public contract shape, schema, migration,
dependency, credential store or provider-profile change is intended.

Verify Red on an owner-private SQLite backup of the actual outstanding
rotation using production ports, without reading keys, sending a provider
request, seeding records or changing live configuration. Add pure policy
rejections where applicable; verify Green and repeat/replay behavior, then
exercise the real installed button and subsequent normal scheduled reading.
The live check repeats the owner's already-requested verification action;
it does not choose or replace credentials or account configuration.

## Existing-scope recovery correction — 7 November 2026

M6-T011/T012, M6-A07/A09 and FR-COL-003/007 require durable timeout/network
recovery. An actual abandoned request exposed an indefinite `dispatched` gate
with no durable response, after both its run deadline and owner lease expired.
This correction implements that approved recovery behavior; it adds no provider,
account, local-model scope or owner configuration step.

M04 adds schema `v1_0720` and CTR-COL-008 1.2.0. Recovery requires the exact
active gate, expired admission/run leases and deadline, matching run/owner/fences,
and a scheduler heartbeat older than the supervisor's stale-owner threshold.
The supervisor holds its existing exclusive worker lock; provider subprocess
execution has a finite deadline. These are ownership evidence, not a claim that
an arbitrary OS process was inspected. An unverified or current owner cannot be
recovered through this path.

A dedicated uncertainty receipt releases an abandoned dispatch after preserving
all known next-start deadlines and adding the existing maximum fallback (300
seconds plus bounded jitter) from recovery time. Original admission and journal response outcome/timestamps remain unchanged.
The run records retry classification `provider_unavailable` under the existing
collection failure policy; this does not assert a received provider response.
Run failure is `ollama_cloud_outcome_unknown`; its typed source signal is `transient_failure`
with `may_have_started`, never a fabricated received response or `not_started`.
No new request is dispatched by recovery itself. The receipt makes replay
idempotent and prevents recovery polling from extending the cooldown repeatedly.

A newly observed Retry-After that cannot be represented safely instead persists
a distinct unreleased hold. Recording this conservative hold retains exact
owner/gate/lease identity checks but does not require an unexpired lease; a late
response must not lose its known restriction. Such a hold never grants dispatch
or commit and is never automatically released by abandoned-request recovery.

The historical unknown outcome may include an unrecorded response or Retry-After.
No local recovery can reconstruct it. This bounded fallback implements the
approved absent-response policy; it cannot promise compliance with an unseen
provider deadline. Known deadlines are never shortened. A future authoritative
response is required before quota freshness or successful recovery can be claimed.

Verification uses the actual orphan on a private SQLite backup, the full migration
chain and composition recovery, plus pure policy/contract tests. No provider rows
are seeded, no provider response is invented, and the live database is unchanged.
Deployment, actual resumed polling and the M6 completion gate remain separate
required evidence. See [the focused evidence](../../evidence/m6-unknown-outcome-recovery-2026-11-07.md).

Representable Retry-After has the same preservation requirement: an actually
received `rate_limited` outcome may be journaled after lease expiry under the
unchanged exact active gate/owner/fence identity checks. Its response timestamp
must remain between request start and the real persistence wall clock. Existing
outcome recovery then applies its actual recorded deadline. This exception only
preserves a provider restriction; it does not admit late success or quota writes.
