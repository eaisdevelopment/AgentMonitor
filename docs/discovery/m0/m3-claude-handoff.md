# M3 Claude discovery handoff

Status: Accepted for the single-account V1-M3 slice only  
Mapping: `M0-M03-CLAUDE-001` V1  
Observed: 2026-09-22 on Linux x86_64 with Claude Code `2.1.278`

This handoff authorizes no login, logout, profile mutation, running-agent
control, or generalization to another Claude Code version. Account identity is
an opaque local reference; no email, credential, token, or profile path enters
the API, database, evidence, or logs.

## Subscription usage lane

- Decision: **Supported for the exact observed tuple**.
- Official source: Claude Code `/usage`, documented by Anthropic as showing the
  plan's usage limits and current rate-limit status.
- Safe invocation: the installed executable, `--safe-mode`, `--no-chrome`, and
  `--ax-screen-reader`, inside a read-only Linux filesystem boundary. The
  provider-owned profile is mounted read-only; only private temporary storage
  is writable.
- Allowed input: the literal slash command `/usage` followed by explicit exit.
- Allowed output fields: window label, integer percent used, provider-rendered
  reset text/time, model scope, usage-credit enabled state, provider/tool
  version, observed time, collected time, and field availability.
- Forbidden output: identity, email, credentials, raw terminal transcript,
  prompts, responses, tool/source content, detailed local-session attribution,
  or unknown fields.
- Proven behavior: one real invocation returned rolling-window, weekly, and
  model-specific usage plus reset information. It reported zero input/output
  tokens and zero session cost. A network-disabled repeat failed closed instead
  of inventing values. Attempted transcript persistence failed with `EROFS`.
- Initial budget: one invocation at a time, 30-second deadline, no automatic
  retry, and no more than one invocation per account per five minutes. Provider
  request count is not exposed and remains Unknown; therefore tighter polling
  is not authorized.
- Drift rule: any executable version other than `2.1.278`, missing label,
  duplicate window, malformed percentage/reset, login prompt, or new output
  shape returns `unsupported` or `unavailable` before persistence.

## Linux runtime lane

- Decision: **Supported for safe process facts; account correlation is limited
  to an explicitly targeted profile probe or owner-confirmed association**.
- Real observation: twelve naturally running `claude` processes were visible
  without signaling, attaching to, or reading content from them.
- Allowed `/proc` facts: executable identity, PID, parent PID, UID equality,
  kernel state, start-time ticks, user/system CPU ticks, resident pages,
  thread count, and observation time. PID plus start time is the identity tuple.
- Forbidden sources: process environment, command line, memory, file
  descriptors, terminal data, prompts, responses, tool activity, and source
  content.
- Existing processes without strong profile evidence remain `unresolved`; OS
  ancestry alone never proves provider session hierarchy or account identity.

## M3 mapping and residual limits

The quota source maps to `subscription.quota`; Linux facts map to
`local.process.correlation` and safe runtime observation. Every persisted field
must include source ID, exact tool version, collection time, availability,
freshness, precision, confidence, and opaque account/profile references.

This handoff is sufficient for one real M3 vertical slice. Multi-account
discovery, other Claude versions/plans, Codex, Ollama, macOS, native isolation
without the current Linux boundary, automatic existing-process account
correlation, and rare exhaustion/authentication states remain outside this
acceptance and must stay visibly unavailable or unresolved.

Official references:

- https://support.claude.com/en/articles/14553413-claude-code-cheatsheet
- https://support.claude.com/en/articles/14552983-models-usage-and-limits-in-claude-code
