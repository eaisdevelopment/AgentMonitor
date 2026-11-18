# AgentMonitor agent instructions

Read [docs/README.md](docs/README.md),
[CONTRIBUTING.md](CONTRIBUTING.md), and the applicable architecture, API and
operator documentation before working on this repository.

## Authority and scope

- Identify the owning module and published contracts before changing behavior.
- Production implementation requires an approved change/module plan. Existing
  applicable user approvals persist; do not request them again without cause.
- Follow direct user instructions and the applicable project rules. Establish a
  real blocker from evidence; do not treat an unsupported assumption as one.
- Continue authorized work until the requested outcome is reached. Explain
  actual limitations and outstanding work; do not call partial work complete.
- Use the full engineering runbook and private governance records when supplied
  by the maintainer. They are not published as local-development artifacts.

## Invariants

- Use real systems and real provider data at external boundaries. No mocks,
  fakes, stubs, response replays, seeded telemetry or placeholder dashboard data.
- Constructed values are limited to pure domain tests with no I/O.
- Follow red-green-refactor TDD. Blocked, skipped or unexecuted tests are not passes.
- Do not read prompts, responses, monitored source content, arbitrary process
  environments, credential values, passwords or one-time codes.
- The runtime may use owner-entered provider keys from its selected protected
  `.env` for admitted official operations. Coding agents must not view keys.
  Never put secrets in source, tests, logs, screenshots, commits or chat.
- Do not modify, log out, relocate or rewrite default Claude, Codex or Ollama
  profiles. Official user-visible authentication may write only to the selected
  AgentMonitor-managed profile.
- Provider-owned state is read-only except for a separately approved official
  authentication flow into an AgentMonitor-managed profile.
- Monitoring must not stop, restart, switch or mutate user agent processes.
- The UI consumes the versioned API. It does not read the database, backend
  internals or provider files directly.
- Keep provider/framework/OS details in adapters, outside pure domain code.
- Assess cross-module contract changes. Breaking changes require a versioned
  migration path. New dependencies require prior licence, maintenance, security
  and transitive-impact review.

## Verification and handoff

Use canonical commands for repeatable operations. Verify the installed boundary
when claiming installed behavior, and the remote repository when claiming a
push. Do not replace required work with a tracker, future task or prose promise.

Name requirement and acceptance IDs, module and contract versions, affected
files, meaningful Red/Green results, actual live verification,
security/privacy/migration/licence impact and remaining work.
Completion claims require the applicable executable checks to pass; retain
conditional unexecuted scenarios as such. Keep private live evidence and owner
account data out of the public repository.
