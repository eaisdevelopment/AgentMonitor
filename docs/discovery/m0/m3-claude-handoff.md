# M3 Claude discovery handoff

Status: **Adapter/live handoff evidence complete; authorization remains blocked pending detached review decisions**
Mapping: `M0-M03-CLAUDE-001` and `M0-M03-CLAUDE-OTEL-001`, V1
Scope: one `REF-M0-CLAUDE-PROFILE-001` tuple for Claude Code `2.1.278`,
Claude Max, Linux x86_64

This is the narrow input to `M0-M3-CLAUDE-SCOPED-ENTRY-001`; it is not M0 G9
completion and does not authorize another provider, version, platform, account,
profile, source, or capability. The authoritative sanitized statuses and
side-effect reconciliation are in `m3-claude-evidence-v1.json`. Dynamic quota,
process, session, identity, and timestamp values are not repository evidence.

## Capability decisions

- `subscription.quota` is **Supported** only through
  `claude.usage.ax-screen-reader.v1` under the exact host, deadline, invocation,
  byte, redirect, retry, and 300-second interval bounds in
  `m0-to-m03-claude-v1.json`.
- `local.process.observation` is **Supported** only for the allowlisted Linux
  process facts in that mapping. It excludes environment, command line, memory,
  file descriptors, terminal data, prompts, responses, tools, and source
  content.
- `local.session.discovery` and `local.process.account_correlation` are
  **Supported** only through the official metrics-only OTLP HTTP/JSON lane in
  `m0-to-m03-claude-otel-v1.json`. The source is an authenticated private
  loopback receiver for `claude_code.session.count`; logs and traces are
  disabled, raw payloads and raw provider identity are discarded, and exporter
  success follows durable commit and checkpoint.
- Automatic account association requires the exact owner-confirmed registry
  fingerprint binding and exact launch/process identity. Missing, stale,
  unapproved, or conflicting evidence remains unresolved/conflict. There is no
  sole-account fallback.

The OTLP source semantics were reviewed against Anthropic's official Claude
Code monitoring documentation at
`https://code.claude.com/docs/en/monitoring-usage` on 2026-09-24. The accepted
attributes and privacy boundary are recorded in the OTLP mapping; the
repository retains only sanitized conclusions and opaque evidence references.

## Targeted same-account result

The owner-terminal targeted probe produced an authenticated session metric,
matched it to the exact AgentMonitor-launched Linux PID/start identity and the
owner-confirmed provider-account fingerprint, committed it through M04/M06,
reopened the real SQLite database, and resolved the session to the same account
used by the real quota lane. The provider profile and running process were not
modified or controlled. No credential, provider identifier, prompt, response,
tool activity, source content, arbitrary environment value, raw payload, or raw
provider output was retained.

The sanitized proof is referenced as
`REF-M0-CLAUDE-OTEL-TARGETED-PROBE-001`; operational detail is recorded in
`docs/evidence/m3-claude-otel-targeted-probe.md`. The new owner-confirmed
binding operator makes first-use setup reproducible; it is not a substitute for
the exact real probe.

## Gate state

`M0HandoffAcceptanceV1` binds both mappings, this handoff, the sanitized
evidence index, the M0 schema bundle, the current CTR-PROV-002 contract bundle,
the approved M3 plan, the targeted probe evidence, and all four detached
decision paths. The evidence and subject are current, but adapter/live
authorization remains blocked until the owner, security/privacy,
test-integrity, and root-integration decisions all approve this exact subject.
Every live execution must validate the current digests and exact version before
I/O.

Codex, Ollama, Anthropic API, OpenAI API, Ollama API, macOS, reauthentication,
agent control/routing, prompt/response/tool capture, and broader M0 G9 claims
remain outside this handoff.
