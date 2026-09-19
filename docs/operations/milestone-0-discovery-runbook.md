# Milestone 0: read-only telemetry discovery runbook

## Objective

Determine exactly what real Claude, Codex, Ollama, Anthropic API, OpenAI API, and Ollama API environments expose before finalizing schemas or collectors. Produce evidence-backed capability matrices without modifying default profiles, accounts, running agents, or provider state.

## Exit artifacts

- environment/version inventory;
- provider-by-capability matrix;
- safe local source inventory;
- field semantics/units/precision/freshness notes;
- authentication/permission requirements;
- rate-limit and collection-cost notes;
- source stability classification;
- sanitized evidence references;
- supported/experimental/deferred/unsupported decisions;
- architecture/requirements/contract updates;
- follow-up isolated-profile experiments requiring separate approval.

## Strict safety boundary

Allowed:

- read installed executable paths and versions;
- run documented read-only status/help/version commands after review;
- enumerate running process metadata through approved OS APIs;
- list approved provider directory/file names, metadata, ownership, permissions, size, and modification time;
- read specifically approved metadata files/fields under owner supervision;
- view provider dashboards/CLI status interactively with owner;
- query documented provider API usage/cost endpoints with owner-provided real credentials when separately approved.

Not allowed in this milestone without a new explicit approval:

- logout/login or creation/modification of any profile;
- copying/moving OAuth files;
- writing provider settings/state;
- attaching to process memory, injecting terminal input, signaling or restarting agents;
- reading arbitrary process environments;
- network interception/MITM/browser cookie extraction;
- undocumented/private endpoint calls or browser automation;
- exhausting quota, changing budgets, revoking keys, purchasing credits, or triggering side effects;
- intentionally opening, reading, requesting, parsing, or loading prompts,
  responses, source/tool content, arbitrary process environments, credentials,
  or raw secret-bearing files; a source with inseparable safe and prohibited
  fields remains Blocked/Deferred/Unsupported.

## Preflight

G1 artifacts and exact validation rules are defined in the
[M0 G1 control specification](../plans/discovery/m0-g1-control-specification.md).
Blank custody, operation/assertion, ledger, E1-admission, and incident forms are
under [the template index](../templates/README.md). A blank or completed form is
not approval. `AUTO-M0-G1-CONTRACT` checks repository structure only.
`AUTO-M0-G1-EXIT` remains Blocked until real custody, scanner admission, and
exact bundle approvals exist. After G1, `AUTO-M0-PREFLIGHT` is the mandatory
machine gate for every exact scenario packet. No gate may be bypassed or
substituted for another. `M0-COM-001` is the first ordinary post-G1 scenario;
G1 itself executes no M0 scenario.

1. Confirm owner is present for sensitive/live observations.
2. Capture current time/timezone and AgentMonitor workspace revision state.
3. Confirm no command will update/install automatically.
4. List intended commands/paths and classify read-only behavior.
5. Define redaction and evidence destination outside version control if account data may appear.
6. Ensure commands do not echo environment or credentials.
7. Confirm running agents will not be interrupted.

## Common inventory

- OS/distribution/kernel/architecture.
- Python/Node/browser availability for later tooling, without installation.
- Claude, Codex, Ollama executable paths and exact versions.
- Running process count/tree, start times, executable identities, and working directories where permitted.
- Standard provider state roots and permissions.
- Existing use of alternate profile/config directories.
- Current account-switching workflow and possible effects on already-running
  processes, from official documentation and owner description only. Do not
  execute login, logout, `/login`, profile changes, or account switching in M0.

## Claude questions

- What does documented `/usage` expose for each subscription plan/account?
- Is there a non-interactive documented structured equivalent?
- Which local files contain safe usage totals, session index, model, token/context, activity, and parent/subagent metadata?
- Which fields contain content or secrets and must be excluded?
- Can running sessions be correlated to an account without process memory/environment/injection?
- What official documentation says may survive `/login` changes while older
  agents run; any live change is a separately approved future experiment.
- What exact paths honor `CLAUDE_CONFIG_DIR`, and does credential isolation work? This last question may require a later approved write/auth experiment, not read-only discovery.
- What reset times/units/precision are visible and how do they match provider UI?

## Codex questions

- What does `/status` expose for five-hour/weekly/credit limits and reset?
- Does current Codex offer a documented structured/app-server representation?
- What local state under `CODEX_HOME` safely exposes sessions, model, tokens/context, activity, or account identity?
- Which auth store mode is active, without reading secret values?
- Can a running process/session be correlated to the account used at launch?
- What is the separation behavior of `CODEX_HOME` versus configuration `--profile`? A write/auth experiment is deferred until approved.

## Ollama questions

- Is each reported identity a personal account, team, organization, or workspace under current plan rules?
- Is the account on current monthly-credit pricing or a legacy plan?
- What usage, included/purchased credit, reset, concurrency, queue, model, and per-request token/cost data is exposed officially?
- Does local Ollama daemon/API/log metadata expose cloud request usage without content?
- What CPU/RAM/GPU/model-load/process metrics are available through supported local endpoints/tools?
- Is there a documented billing/usage API? If not, record the gap; do not access private endpoints in read-only supported discovery.

## API billing questions

### Anthropic

- Admin API credential roles and scopes.
- Usage/cost endpoints, bucket limits, grouping, pagination, latency, currency, workspace/key/model fields.
- Credit/budget/limit endpoints or explicit absences.

### OpenAI

- Admin credential roles and scopes.
- Organization/project usage, costs, spend limits/alerts, credits, pagination, and data latency.
- Distinction between ChatGPT/Codex subscription pools and API billing.

### Ollama

- Official API usage/cost/budget availability and account/team semantics.
- Per-response token/cost fields and whether they can cover already-running tools without proxying.

## Local metadata review procedure

For every candidate file:

1. Record path pattern, owner/mode, size bound, modification behavior, and provider version.
2. Decide whether path/file access is supported, undocumented, or unsafe.
3. Establish schema/field names from documentation or a selective approved
   interface. Do not open a candidate merely to inspect its schema when doing so
   would read co-resident prohibited bytes.
4. Classify fields: required metadata, personal identifier, content, credential, unknown.
5. Do not persist credential/content/unknown values.
6. Define allowlist, parser-version signal, and failure behavior.
7. Confirm symlink/path boundary behavior.
8. Record read side effects. Atime must remain unchanged unless its exact paths,
   bound, measurement, and reconciliation are predeclared and owner-approved;
   all other writes are prohibited.

## Capability matrix template

Use [provider capability matrix template](../templates/provider-capability-matrix-template.md). One row represents one provider/account type/capability/source combination. Do not generalize from one account/plan without marking scope.

## Evidence rules

- Use account aliases, not secrets or full personal identifiers.
- Prefer schema/field lists and redacted summaries to screenshots/raw output.
- Record observation time because quota values change.
- Evidence location is access-controlled and excluded from Git.
- Before any sanitized live E1 artifact enters Git or a handoff, run the
  security-approved local no-telemetry fail-closed secret/content scanner and a
  human allowlist review. The scanner must not echo matches; without an admitted
  scanner, publication is Blocked.
- Documentation contains conclusions and safe shapes, not raw account data.

## Decision rules

- **Supported:** documented/safe source, semantics understood, live verified.
- **Experimental:** explicit opt-in, brittle/undocumented source, isolated adapter, visible status.
- **Deferred:** useful but needs separate risk/architecture work.
- **Unsupported:** no safe/authorized source or semantics cannot be trusted.

An unsupported metric is a successful discovery outcome and must be displayed honestly later.

## Stop conditions

Stop immediately if a command prompts to update/login/write, output contains a
secret/content, provider state changes, a running agent reacts, account identity
is uncertain, certificate/hostname verification fails or would be bypassed, a
host or redirect is not exactly approved, credentials could cross to a
non-owning host, or the source appears to require private endpoint/cookie
extraction. Preserve sanitized notes and seek owner direction.
