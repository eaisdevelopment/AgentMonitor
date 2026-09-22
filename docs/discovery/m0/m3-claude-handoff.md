# M3 Claude discovery handoff

Status: **Structural prerequisite authorized; adapter/live handoff Blocked**
Mapping: `M0-M03-CLAUDE-001` V1  
Scope: one `REF-M0-CLAUDE-PROFILE-001` tuple for Claude Code `2.1.278`,
Claude Max, Linux x86_64

This is a narrow input to `M0-M3-CLAUDE-SCOPED-ENTRY-001`; it is not M0 G9
completion. The authoritative sanitized scenario statuses and side-effect
reconciliation are in `m3-claude-evidence-v1.json`. Changing quota values,
process counts, PIDs, timestamps, byte totals, request totals, or session cost
are not repository evidence.

## Capability decisions

- `subscription.quota` is **Supported** only through
  `claude.usage.ax-screen-reader.v1` under the accepted exact-host boundary:
  `api.anthropic.com:443`, redirects denied, one CLI invocation, at most 32 TLS
  connections, 4 MiB total upstream and 4 MiB total downstream, a 30-second
  deadline, no retry, a 300-second minimum interval, and no model prompt or
  inference authorized. HTTP requests inside TLS are not observable and are not
  claimed as bounded. M3 must implement and live-verify an admitted equivalent
  boundary; this handoff does not approve a production proxy implementation.
- The screen-reader output refreshes incrementally. Parsing accepts only the
  latest complete window set immediately before the terminal `Usage credits`
  marker. Repeated windows across refreshes are valid; conflicting duplicates
  within that final render, an incomplete final render, a missing marker, or a
  deadline fail closed.
- `local.process.observation` is **Supported** for the allowlisted Linux process
  facts in the mapping. It excludes environment, command line, memory, file
  descriptors, terminal data, prompts, responses, tools, and source content.
- `local.process.account_correlation` is **Deferred** and its outcome is
  `unresolved`. No targeted-profile probe evidence exists. Safe process facts,
  OS ancestry, or owner recollection do not establish same-account correlation.

Version drift and authentication use the normalized outcomes in the mapping:
compatibility resolution returns `provider_version_unverified`; an invoked
operation encountering drift returns `unverified_provider_version`; provider
authentication and authorization signals return `reauthentication_required`
and `authorization_insufficient`. Identity mismatch is outer `success` with
typed result `wrong_account_detected`.

## Gate state

`M0HandoffAcceptanceV1` binds the exact mapping, this handoff, the sanitized
evidence index, the M0 schema bundle, the current CTR-PROV-002 contract bundle,
and the scoped M3 entry amendment. `structural_prerequisite_authorized` permits
only ST-PROV-001 pure provider-neutral work required to create the missing
CTR-PROV-002 normative schema. No provider I/O or later M3 task is authorized.

Adapter/live handoff remains fail-closed because the CTR-PROV-002
machine-readable normative schema does not exist, same-account targeted-profile
evidence is Not Run, and security/privacy, test-integrity, and root-integration
detached approvals are pending independent re-review.

The active owner goal authorizes this correction and structural prerequisite
scope only. It does not replace independent approvals or authorize provider
access, production adapter behavior, login/logout, profile mutation, or
running-agent control.
