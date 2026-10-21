# Codex CLI 0.160.0 bounded M5 discovery

- Date: 2026-10-07.
- Status: **Accepted as the implementation basis for the bounded M5 change
  plan; authenticated account/quota verification remains a required live
  implementation gate.**
- Provider product: Codex CLI.
- Exact installed version: `codex-cli 0.160.0` on Linux x86_64.
- Evidence mapping ID: `M5-CDX-0-160-0-001`.
- Scope: `M0-CDX-001/002/004/005/007/008/009` evidence needed to choose the
  initial M5 mechanism. Account-specific `M0-CDX-003/006/010` claims remain
  conditional on the later owner-authenticated live run.

## Official source review

The official OpenAI documentation establishes these current facts:

- [Codex authentication](https://developers.openai.com/codex/auth) documents
  `CODEX_HOME`, file/keyring/auto/ephemeral credential stores, automatic token
  refresh, browser/device login, and the sensitivity of `auth.json`.
- [Codex app server](https://developers.openai.com/codex/app-server) documents
  newline-delimited JSON over stdio, the `initialize`/`initialized` handshake,
  `account/read`, `account/rateLimits/read`, and their closed field meanings.
  It also labels app-server experimental and unsupported for production
  workloads, so this admission is exact-version and local-only.
- [Codex developer commands](https://developers.openai.com/codex/cli/reference)
  documents `codex login status` and the interactive `/usage` view.
- [Codex configuration](https://developers.openai.com/codex/config-reference)
  documents analytics/OpenTelemetry controls and that raw prompt export is
  opt-in.

No undocumented/private endpoint, browser cookie, traffic interception, or
provider-file parser is selected.

### 2026-10-21 operator-surface correction

The dated 2026-10-07 source-review statement above is retained as historical
discovery evidence. Direct inspection of the installed admitted Codex CLI
`0.160.0` later established that its interactive `/status` view displays the
current account rate-limit windows used for authoritative M5 reconciliation;
`/usage` opens analytics or billing settings where available. Current M5
operator instructions therefore use `/status`. This presentation correction
does not change the admitted `account/rateLimits/read` app-server operation,
schema digest, normalized provider contract, or the exact owner attestation
phrase `I CONFIRM CODEX USAGE`.

## Real installed-system observations

The exact executable returned a bounded `codex-cli 0.160.0` version banner and
reported ChatGPT authentication as a category without revealing identity or
credential data. `codex app-server --help` exposed stdio, Unix-socket and
schema-generation commands. Version-specific schema generation ran in a
temporary directory outside the repository and produced the following exact
SHA-256 values:

| Schema | SHA-256 |
|---|---|
| `v2/GetAccountParams.json` | `30b545275f60975b55bd6fbaafd70f15505801d14168ee82d3931b6e93c78aab` |
| `v2/GetAccountResponse.json` | `c3092dd8e52c2933c5ba5f0bf92377174f65bed627ff4ef5d7c04a189dd34fd1` |
| `v2/NullableGetAccountRateLimitsParams.json` | `072f813ca1c696831a7f2fbd934feaa8cad228a6b3d44a4be8877547c796341b` |
| `v2/GetAccountRateLimitsResponse.json` | `cb9655e68130116f634ed9353e45b336492e6069a6628f424d1cd52e54eda0e0` |
| Ordered four-schema admission bundle | `36bd8e1d76b12b89b06446a85c45e957945eb8cb63b05061264c3dec97f625da` |

A real app-server process was then started against a new owner-only empty
temporary `CODEX_HOME` with file credential storage, analytics disabled, all
OpenTelemetry exporters disabled, and prompt logging disabled. The required
handshake and `account/read` with `refreshToken=false` succeeded and returned
the expected unauthenticated category. The process wrote only inside that
selected managed root. No default-profile file, account identity, credential,
provider payload, prompt, response, source content, or arbitrary environment
value was inspected or retained.

A bounded same-user Linux observation found five currently running Codex
processes using only PID/parent, kernel command name, exact executable name, and
start identity. The count establishes that the M5 five-to-six process boundary
is presently testable. It does not establish account ownership or expose those
private process identifiers in committed evidence.

### Authenticated identity semantic correction

On 2026-10-08 the owner completed an official login in an isolated
AgentMonitor-managed profile. A bounded structural `account/read` check found
an authenticated ChatGPT account and workspace identifier while
`requiresOpenaiAuth` remained `true`. This disproved the implementation's
earlier assumption that the flag represented current login state.

The exact tagged OpenAI source confirms the observed meaning. The
[`0.160.0` provider account implementation](https://github.com/openai/codex/blob/rust-v0.160.0/codex-rs/model-provider/src/provider.rs#L554-L594)
derives the flag from the active model provider and independently derives the
account from cached authentication. The
[`0.160.0` TUI login decision](https://github.com/openai/codex/blob/rust-v0.160.0/codex-rs/tui/src/lib.rs#L2142-L2152)
derives login state from account presence. For the admitted default-provider
tuple, `true` plus a populated ChatGPT account is authenticated, while `true`
plus a null account is unauthenticated. A populated account with `false` is
rejected as inconsistent. The stable generated response schema defines the
workspace-routing type but does not expose `workspaceRouting` as a response
property; the experimental schema and real exact-version response do. M5
therefore treats `workspaceRouting.chatgptAccountId` as a required,
allowlisted exact-version observed extension. No admitted field, operation,
source identifier, or normalized output schema changed.

## Accepted field and operation decisions

- Identity/auth: allow `account.type`, ChatGPT `email`, `planType`,
  `requiresOpenaiAuth`, and `workspaceRouting.chatgptAccountId` only as input
  to a one-way private identity fingerprint. Call `account/read` only with
  `refreshToken=false`.
- Subscription: allow `accountId` only for same-profile comparison and as
  input to that one-way private fingerprint; allow `ordinaryUsageAllowed`,
  `rateLimits`, `rateLimitsByLimitId`, and each bucket's `limitId`, bounded
  `limitName`, `planType`, `primary`, `secondary`, and
  `rateLimitReachedType`.
- Window: allow integer `usedPercent` in 0..100, nullable positive
  `windowDurationMins`, and nullable Unix-second `resetsAt`. Derive remaining
  percentage and ratio with exact decimal arithmetic.
- Reset-credit details, upsell content, spend limits, credit balances, email
  nudges, reset consumption, logout, threads, turns, items, previews, and every
  unknown method are excluded from M5.
- Source: one short-lived app-server child per managed-profile operation,
  maximum concurrency one, no application retry, and a five-minute collection
  interval until live evidence justifies a different policy.
- Version drift: any provider version other than `0.160.0` returns
  `unverified_provider_version` and is not invoked.
- Authentication: official `codex login` may write only to the explicit
  AgentMonitor-managed `CODEX_HOME`. The owner performs browser/MFA actions;
  AgentMonitor never accepts or reads the secret values.
- Runtime: use the existing Linux exact-executable/process metadata boundary
  and guarded owner association. Do not use content-bearing app-server thread
  responses.

## Remaining live conditions

The implementation must still prove, without simulated provider data:

- official login and identity verification for the remaining intended managed
  profiles and a successful enrollment retry for the first profile;
- exact real rate-limit response mapping and authoritative UI reconciliation;
- four intended account outcomes under `AC-LIVE-002`;
- five to six representative process trees and truthful correlation;
- service restart, scheduled collection, file-backed SQLite history, API,
  built browser, failure isolation, and default-profile non-modification.

Those are completion-gate requirements, not assumptions supplied by this
discovery record.
