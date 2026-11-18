# Security architecture

AgentMonitor handles sensitive operational metadata: account identities, usage,
costs, project paths and connection state. The authenticated dashboard is the
boundary for viewing that data. A public source repository or a reachable static
login page does not make account data public.

## Credentials

Provider OAuth credentials remain in provider-managed storage. Official,
user-visible sign-in flows may write to separate AgentMonitor-managed profiles;
the user's default profiles are not modified.

Owner-entered Anthropic/OpenAI administrative billing keys and Ollama cloud keys
use the selected protected AgentMonitor `.env`. Only the runtime receives the
selected binding transiently for its admitted provider operation. Coding agents
must not view these values. Keys do not belong in browser forms, command
arguments, database records, logs, tests, screenshots, exports or backups.

Local setup commands use hidden terminal input. A stored key, verified access
and enabled monitoring are distinct states. Rotation, scope changes and
disconnection invalidate stale collection authority while preserving history.
Removing a local key does not revoke it at its provider.

Passwords and session/API-token verification use their configured hashing
mechanisms. Token plaintext is not a recoverable account property. Sign-out and
revocation remain explicit operations.

## Browser and API

The local service validates hosts, origins, authorization and request bounds.
Cookie-authenticated mutations require CSRF protection. The UI uses the
versioned API and generated client; it does not inspect the database or provider
files. Authenticated API documentation does not bypass authorization.

Trusted-LAN mode is opt-in and restricted to its selected private interface and
subnet. It retains application authentication. Its HTTP transport does not
protect against observers on that network, and it is not an Internet-hosting
configuration. Forwarded headers do not establish trusted peer identity.

## Provider and local inspection

Adapters admit specific provider interfaces, versions, fields and operations.
Requests and subprocesses have bounded output and deadlines. Secrets go only to
the owning provider operation. Provider failures, missing fields and unsupported
schemas remain explicit rather than becoming invented successful readings.

Process inspection is limited to permitted operational metadata. AgentMonitor
does not collect prompts, responses, source-code content or arbitrary process
environment values. Process identity checks account for PID reuse. Monitoring
does not stop, switch or restart user agents.

## Storage and operation

Normalized reports retain provenance and immutable history; no raw provider
response is used as a replayed live reading. Failed collections do not refresh
the age of old observations. Storage, migration, retention and recovery use
explicit boundaries and preserve original report/receipt identity.

Keep configuration and data under the intended service user's control. Avoid
broad debug logging and unredacted diagnostic uploads. Treat a credential
exposure as an incident: revoke or rotate the affected credential at its owner,
preserve a minimal sanitized account of what happened, and follow
[the reporting policy](../../SECURITY.md).

These controls describe the application boundary, not a security certification
or a guarantee against a compromised host.
