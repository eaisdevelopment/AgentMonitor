# Configuration standard

## Purpose

Configuration is a versioned interface between AgentMonitor, its operator, its deployment, and its modules. It must be validated, documented, safe to inspect, and portable from the local V1 deployment to a future remote deployment. This document defines conventions; exact keys are allocated by approved module plans.

## Sources and precedence

Lowest to highest precedence:

1. secure production defaults in code;
2. non-secret values in an explicitly selected configuration file when introduced;
3. AgentMonitor environment variables loaded from the local `.env` deployment file;
4. explicit command-line options for documented operational commands, excluding secrets;
5. narrowly scoped runtime settings persisted through an authorized API, such as alert thresholds.

The effective value and source may be reported only for non-secret configuration. Secret presence may be reported as `configured` or `missing`; secret value, length, prefix, suffix, and hash are never exposed.

## Naming

- Environment variables use uppercase `AGENTMONITOR_` prefix and snake case: `AGENTMONITOR_<MODULE>_<SETTING>`.
- Python settings use lower snake case and map one-to-one to documented external names.
- TypeScript configuration exposed to the browser uses lower camel case only after the server explicitly publishes a non-secret value.
- Boolean names read positively: `enabled`, `required`, `allow_*`. Avoid double negatives.
- Durations include units (`*_seconds`, `*_minutes`) unless represented by an ISO-8601 duration at a public boundary.
- Sizes include units (`*_bytes`, `*_mib`). Counts use `*_count` or an exact noun.
- URL values use `*_url`; filesystem paths use `*_path` or `*_dir`; identifiers use `*_id`.
- Names do not encode a provider in a domain setting unless semantics are truly provider-specific and adapter-owned.

## Configuration ownership

Every key has exactly one owning module and a registry record with:

- external/internal name;
- description and owner;
- type, unit, allowed range/enum, and validation;
- required/optional status and safe default;
- secret classification;
- source/precedence and reload semantics;
- first version and deprecation/removal version;
- operational and security consequences;
- test and documentation reference.

The exact Draft allocation is maintained in
[`docs/plans/configuration-baseline.toml`](../plans/configuration-baseline.toml).
It becomes authoritative only after the applicable plan/contract approval; a
`decision_required` record allocates the name and owner but still blocks
implementation. A module cannot consume another module's private setting
directly.

## Secret classes

### AgentMonitor-managed secrets

Examples include the dashboard bootstrap/password inputs, session signing/encryption keys, API token bootstrap material if ever used, and post-V1 SMTP credentials. They live only in the untracked `.env` or a future approved secret store. The application stores password and API-token verification hashes, not plaintext.

### Provider-managed credentials

Claude, Codex, Anthropic, OpenAI, and future provider OAuth/API credentials remain in provider-supported stores or explicitly approved AgentMonitor-managed provider profiles. The owner separately approved Ollama cloud API keys in the protected AgentMonitor-managed `.env` on 2 November 2026. Ollama entries are binding-scoped and owner-only; credentials must not appear in logs, database rows, exports, backups, diagnostics, screenshots, arguments, or chat. The default Ollama profile remains untouched. Do not load unrelated `.env` values into the cloud worker's environment.

### Development-service credentials

GitLab tokens or similar development credentials are not application runtime configuration. If the operator places one in `.env` for local tooling, it must use a clearly development-only name, minimum scope, and must never be loaded or exposed by the AgentMonitor service.

## `.env` rules

- `.env` is local, ignored by Git, owner-readable only, and never printed wholesale.
- An `.env.example` may contain names, comments, and safe non-secret example values only. It must not contain realistic tokens, emails, passwords, account identifiers, or provider state paths copied from the workstation.
- Startup fails closed on missing required security settings, invalid values, unknown critical enum values, or incompatible key combinations.
- Error messages name the setting and safe remediation without echoing its value.
- Automated tests create their own isolated configuration and do not read the operator's `.env`.
- Rotation and restart/reload requirements are documented per secret.

## Runtime settings

User-editable settings such as thresholds, polling cadence within safe bounds, time zone, and retention policy are changed only through authorized application use cases. They receive validation, audit metadata, optimistic concurrency or idempotency where appropriate, and documented precedence. Environment configuration cannot silently overwrite persisted user choices without an explicit policy.

## Change and compatibility policy

- Adding a compatible optional setting requires documentation, validation, and tests.
- Renaming or changing semantics requires a deprecation/migration period and contract assessment.
- Removing a setting requires release notes and a safe unknown-key/error policy.
- Configuration migrations run independently from database migrations when behavior changes.
- Exported diagnostics report only allowlisted non-secret effective settings plus secret-presence booleans.

## Test requirements

Use real settings loading and application startup, not patched environments or fake settings objects, for integration claims. Verify valid, missing, malformed, boundary, conflicting, deprecated, and unknown values; file permissions where supported; secret redaction; startup failure; and diagnostics output. Pure parsing/value-policy functions may use constructed values under the testing strategy.

## Provisional categories

The following categories reserve design space but do not allocate final keys:

| Category | Likely owner | V1 status |
|---|---|---|
| Bind host/port, public origin, trusted hosts | API/deployment | Required; loopback-only |
| Database and backup paths | Operations/persistence | Required |
| Session/password/token security parameters | Identity/access | Required |
| Polling, timeouts, retries, concurrency | Collection control | Required |
| Thresholds, snooze, possible-stall interval | Alerting/runtime | Required, usually persisted settings |
| Retention and backup rotation | Operations | Required |
| Provider executable/profile/state references | Registry/adapters | Discovery then planned |
| Log level/path/rotation | Operations | Required |
| SMTP/email | Future notification module | Deferred until post-V1 |
| Remote TLS/multi-user settings | Future deployment/IAM | Deferred |

No name in this table should be treated as an implemented environment variable.
