# Security architecture

## Security objectives

1. Do not compromise provider accounts or local source code.
2. Do not let a browser or unrelated local program mutate AgentMonitor without authorization.
3. Do not leak secrets or content through storage, logs, tests, diagnostics, backups, or exports.
4. Do not disturb running agents or default provider profiles.
5. Contain provider parser/process failures.
6. Preserve a safe path from local single-user deployment to later remote hosting.

## Protected assets

- provider OAuth tokens and refresh state;
- API/admin keys and GitLab/SMTP credentials;
- dashboard password and sessions;
- AgentMonitor API tokens;
- provider account identity, usage, cost, and budget data;
- local project paths and operational metadata;
- SQLite history and backups;
- integrity of process/session correlation and alerts.

## Trust boundaries

- Browser ↔ local FastAPI service.
- API boundary ↔ application modules.
- AgentMonitor ↔ provider network APIs.
- AgentMonitor ↔ provider CLIs/subprocesses.
- AgentMonitor ↔ provider-owned local files.
- AgentMonitor ↔ `/proc`/platform process APIs.
- Service ↔ `.env`, SQLite, backups, and exports.
- GitLab CI ↔ repository and build artifacts.

Local-only does not mean trusted. A malicious web page, local process, repository hook, provider file, or dependency may attack the service.

## Secret model

### AgentMonitor-managed secrets

Examples: session-signing secret, GitLab token used by development automation, and post-V1 SMTP credentials.

- Stored in `.env` with owner-only permissions.
- Development path may be repository-local and gitignored; installed path follows the user's protected configuration directory.
- Loaded once through typed configuration and never returned by configuration APIs.
- Error messages name missing variables, never values.
- Not inherited by provider subprocesses unless a specific allowlisted variable is required.
- Rotation has a runbook and invalidates affected sessions/tokens where applicable.

### Provider-managed credentials

- Remain in official provider profile storage.
- Referred to by opaque profile reference.
- Never copied into `.env`, SQLite, exports, tests, or logs.
- Default profiles are immutable from AgentMonitor.
- AgentMonitor-managed profiles are changed only through official user-visible authentication flows.

### Stored verification material

- Passwords use an approved memory-hard hash with per-record salt and current parameter metadata.
- API tokens and browser-session tokens are stored only as keyed/cryptographic hashes or equivalent verification material.
- Token plaintext is shown once at creation and cannot be recovered.

## Local web security

- Bind to `127.0.0.1`/`::1` only in local mode.
- Validate `Host` and `Origin`; deny unexpected origins and avoid wildcard CORS.
- Same-origin UI and API are preferred.
- Browser authentication uses HTTP-only, SameSite cookies; enable Secure whenever TLS is present.
- State-changing browser requests require CSRF protection.
- Login endpoints use rate limiting and constant-time verification behavior.
- Sessions have idle/absolute expiry, logout, rotation after login, and server-side revocation.
- API bearer tokens are not stored in browser localStorage.
- Security headers include CSP, frame denial, content-type protection, and conservative referrer policy.
- Swagger is authenticated; mutating calls require appropriate token scopes.

## Authorization

V1 has one administrator role but still checks explicit permissions. Proposed token scopes include:

- `read:status`
- `read:accounts`
- `read:telemetry`
- `read:diagnostics`
- `write:configuration`
- `write:accounts`
- `write:alerts`
- `write:reauth`
- `write:tokens`
- `write:backup`

The single-user shortcut must not bypass the authorization service, preserving a future multi-user seam.

## Safe local inspection

- Standard roots and filenames are allowlisted per provider/version.
- All reads are non-mutating, bounded in size/time, and checked against symlink/path traversal.
- Parsers discard content-bearing and secret-bearing fields before returning contracts.
- Arbitrary process environment reads are prohibited.
- Process working directories are operational metadata but may reveal names; expose them only to the authenticated owner.
- `/proc` race conditions and PID reuse require process start-time validation.
- Never attach/debug or read process memory.

## Safe subprocess execution

- No shell strings; use executable plus arguments.
- Fixed/validated executable paths and supported versions.
- Minimal clean environment.
- No secret command-line arguments.
- Output size limits, deadlines, cancellation, and process-group cleanup.
- Sanitized logging with command category, duration, exit code, and correlation ID—not sensitive output.
- Commands used for read-only collection are reviewed for side effects.

## Provider network policy

- HTTPS certificate verification enabled; no global insecure override.
- Hostnames allowlisted per provider adapter.
- Bounded timeouts, connection pools, response sizes, and redirects.
- Credentials sent only to their owning provider host.
- Private/browser endpoints disabled by default and clearly experimental when explicitly enabled.
- Rate limits respected; re-auth/auth failures are not blindly retried.

## Data protection

- Operational metadata only in V1.
- Database/backups/files use owner-only permissions.
- Backups and exports exclude `.env` and provider profiles.
- Diagnostic bundles use an allowlist and automated secret scan before creation.
- Logs are structured, local, rotated, and redacted at source.
- Sensitive values are represented by safe identifiers or masked labels.
- No external product analytics or automatic crash reports.

## Threats and required controls

| Threat | Required controls |
|---|---|
| Malicious website calls localhost | password/session auth, CSRF, strict origin/host, no wildcard CORS |
| Local process reads `.env` | owner-only permissions, least privilege, no unnecessary long-lived tokens |
| Provider file includes malicious/huge content | allowlisted paths/fields, bounded reads, safe parser, no eval/deserialization |
| CLI output leaks token/content | bounded capture, redaction, discard raw output, no debug logging |
| Wrong account enrolled | stable identity check and explicit owner confirmation |
| Default profile modified | protected flag and adapter precondition; live regression test |
| PID reused/misattributed | validate process start time and evidence; unresolved rather than guess |
| Dependency compromise | lockfiles, hashes where supported, SBOM, license/security scanning, minimal dependencies |
| SQLite corruption | WAL/transaction discipline, integrity checks, rotating verified backups |
| API token theft | scoped token, hash at rest, one-time reveal, rotation/revocation, audit |
| Secret committed | `.gitignore`, secret scanning, review gate, incident rotation runbook |

## Security review triggers

An explicit threat-model update and ADR are required before:

- remote network binding;
- multi-user access;
- transcript/prompt/tool storage;
- process control or routing;
- arbitrary plugin execution;
- browser automation/private endpoints;
- reading any process environment field;
- moving secrets out of the agreed stores;
- adding telemetry/crash reporting;
- accepting community code or distributing binaries.

## Incident baseline

If a secret may have leaked: stop affected integration, preserve sanitized evidence, revoke/rotate at the provider, rotate AgentMonitor sessions/tokens if implicated, scan history/artifacts, document scope, and only resume after a verified clean test. Never paste the secret into an issue or chat during investigation.
