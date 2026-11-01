# M6 local Ollama chunked transport — candidate evidence

Requirements: M6-T004, M6-A08/A09; approved local Ollama implementation plan.
Owner: M03 Ollama adapter; existing local-catalog v1 contract unchanged.

The previous HTTP reader rejected chunked transfer encoding, which can occur
when a provider response grows. The candidate decodes bounded chunked bodies,
retaining the deadline and response size limits and rejecting ambiguous
framing. No provider profile, model, dependency, migration, or secret changes.

Red: the real-provider transport test failed with ImportError for the missing
decoder before implementation. Green: 23 Ollama adapter tests passed,
including a chunked HTTP response from the real Ollama documentation server.
`AUTO-M6-LOCAL-ADMIT` passed with source/test digest
`6fe6fd232181d2ff6cbbd2d368fa649c6b41aec31e6ab125b8744cdb9efce89f`;
its real local API and built-browser checks include automatic refresh.

The documentation response verifies HTTP framing, not a populated Ollama
catalog JSON response. Model-present and natural source failure/recovery tests
remain unexecuted. This is a candidate, not the currently running dashboard or
full M6 completion. See the earlier local preview evidence for rollout and
security boundaries. No new dependency or license impact was identified.

Deployment review: `AUTO-M6-LOCAL-ACTIVATE` is written for the original M5
unit with no drop-in; the live service now has its M6 drop-in and therefore
fails that routine's preflight. `AUTO-DEPLOY` is catalogued as blocked and has
no implementation command. Neither routine is currently an update path for
this candidate. Do not remove the existing drop-in or restart the service to
force either preflight. An update-capable, reviewed transition with real
rollback verification is still required before this candidate is installed.

Update-path work has started in the candidate branch: the pure preflight
policy refuses changed or identical baseline/candidate trees and requires an
exclusive, quiescent transition. Its test failed before implementation because
the policy did not exist, then passed. This policy alone performs no system
checks and is not a deployment command or evidence that rollback works.

Independent update review found a check-to-restart race: the service uses
`KillMode=control-group`, and the dashboard could create a child after the
empty-cgroup check. The code also had a window where a successful file replace
followed by a directory fsync error could be mistaken for no mutation. The
latter bookkeeping was corrected, but rollback has not been live-verified and
can still require operator attention if systemd or filesystem inspection fails.
`--apply` is deliberately disabled pending resolution and review of the
restart race; passing preflight is not authorization or proof of safe restart.

A read-only snapshot observed 14 Claude, 16 Codex and 2 Ollama processes outside
the dashboard service cgroup and none with those names inside it. This is one
instant, not a guarantee about later child creation or process ownership. No
command lines, process environments, prompts, or credentials were inspected.

Shutdown review: the application has lifecycle cancellation and a bounded
collector drain, but no independently callable collector-pause operation was
found in the checked composition/lifecycle paths. The live unit uses
`KillMode=control-group` with SIGTERM, so application cleanup alone does not
prove a child created after the pre-restart check will be spared the initial
service-stop signal. Do not treat the lifecycle hook as closing the race.
