# M6 baseline and preliminary local discovery — 1 November 2026

This is progress evidence, not M6 acceptance or an M0 exit receipt.

## M6-T001: integration baseline

- Integration branch `codex/m6-integration`, merge revision `ea37a3f`, merges
  accepted-M5 evidence branch `56f7bca` with promotion and support-link branch
  `589949f`. Both are ancestors; the merge had no conflicts.
- The accepted M5 receipt is preserved with SHA-256
  `a1c6f7c0ca90cd1f46fd87d57d383766a7aceafeae0b4e1838ab4e345dd6c929`.
- The running dashboard uses backend revision `ab1408b` with the current
  dashboard frontend overlay. Its service was active and `/login` returned
  HTTP 200. No running provider agents were interrupted.
- Prior dashboard entry rollback artifacts remain outside the repository;
  no deployment was performed as part of this baseline merge.
- This establishes a reviewable merged baseline, not proof of M6 completion.

## M6-T002: preliminary read-only local observation

At `2026-11-01T14:50:36Z`, the installed Ollama CLI and daemon each reported
version `0.24.0`. The service was active, owned by user `ollama`, and listened
on loopback port `11434`. Read-only GET requests to the documented
`/api/version`, `/api/tags`, and `/api/ps` returned HTTP 200. The latter two
reported zero installed models and zero loaded models respectively. The
daemon PID and active state remained unchanged across repeated requests.
Requests used a three-second timeout and 256 KiB response bound.

The empty lists are observations at that instant, not evidence of nonempty
model behavior or absence of historical models. An unchanged PID is not proof
that every filesystem attribute remained unchanged. No profile, credential,
prompt, response content, or arbitrary process environment was read; no model
was loaded and no service or agent was stopped.

This preliminary observation is not an M0 G1 or preflight receipt; those
runbook gates and formal capability admission have not been shown to pass.
On this integration baseline, `python3 tools/automation/run.py
AUTO-M0-PREFLIGHT` returned **BLOCKED**: the routine is registered without an
implementation and lists evidence custody, the operation/assertion packet
schema, and validator implementation as blockers. `AUTO-M0-G1-EXIT` also
returned **BLOCKED by missing or unusable local executable** in this fresh
worktree; this is an environment/tooling result, not a finding about the
substantive custody or approvals. The previously observed requests must not be
represented as authorized M0 scenario passes or capability admission.
Accepted [ADR-0013](../decisions/0013-local-milestone-release-gates.md)
supersedes detached M0 reviewer approvals as a prerequisite for owner-local
M3–M8 milestone execution. It requires current technical bindings, real
provider checks and the original privacy and safety protections; it does not
claim M0 completion. The M0 runbook now clarifies that policy for owner-local
milestones. The M6-specific technical check remains absent, so the preliminary
result is not M6 capability admission. An unavailable
M0 executable is not by itself evidence that the entire M6 milestone is blocked.
`python3 tools/automation/run.py AUTO-M6-LOCAL-INVENTORY` is now a repeatable
preliminary loopback inventory: it restricts its three GET paths, disables
proxies and redirects, bounds time and response size, and outputs only daemon
version and counts. Its real-service run observed daemon 0.24.0 and both
counts zero. Two pure policy tests check path and redirect rejection. This
inventory is narrower than a complete M6 technical admission, does not test a
model-present host or cloud, and its initial implementation did not retain an
exact-command Red-before-Green record; do not present that TDD evidence as
passed. The broader automation suite was attempted in this fresh worktree and
failed because its Node and Python tool environments are not installed there,
among other reported failures. After linking the existing local tool
environments into the new worktree, the suite ran 54 tests with one failure:
the nested Codex security-policy suite had six `codex_version_unverified`
failures because it requires Codex `0.160.0`. This is not an Ollama failure or
an M6 pass. The focused inventory catalog/policy tests and actual local
inventory passed. The temporary tool-environment links are not repository
changes and must not become deployment artifacts.

The inventory now has a real-boundary regression check: it calls the canonical
command and independently reads the same live service before and after,
requiring the installed/loaded counts to agree when the observed source state
is stable. `python3 -m unittest tools.discovery.test_m6_local_inventory -v`
passed all three live/pure checks on the local service. A changing model state
is reported as a test failure instead of being converted to a pass or skip.

For the proposed local vertical, the real-service test
`PYTHONPATH=backend/src backend/.venv/bin/python -m pytest
backend/tests/adapters/providers/ollama/live/test_local_catalog.py -q`
currently fails at collection with `ModuleNotFoundError: No module named
'agentmonitor.adapters.providers.ollama'`, as expected before an adapter
exists. This establishes a preliminary Red only; it is not a successful live
adapter check, and the test/contract may need revision during plan review.

The independently prepared authenticated loopback HTTP test
`backend/tests/integration/api/test_ollama_local_catalog_http.py` used the real
temporary application/SQLite stack and actual local Ollama state. It failed
as expected after a successful dashboard login because the proposed catalog
route returned HTTP 404 instead of 200. Assertions for authorization, rejected
unknown query parameters and source-matching counts are present but were not
reached; they are not passed checks. The route and response shape remain
subject to the requested plan/contract approval.
The owner subsequently identified this workstation as the model host. A
repeat inventory still reported zero installed and zero loaded models; one
local Ollama service/listener was identified, and no Ollama-labelled published
container was found by the bounded container listing. The expected model name
and how it is accessed remain unconfirmed (M6-T003); zero models from this
service does not prove there is no model elsewhere on the machine.
SDK and EAIS cloud identities, roles, balance variants and credentials remain
unverified (M6-T004/T005). No authenticated cloud request was made.

## Contract impact identified

The A03 Ollama plan remains Draft and there is no implemented Ollama provider
adapter on this baseline. Existing runtime provider enumeration and generic
dashboard provider filtering alone do not provide Ollama monitoring. The
capacity contract has typed quota fields and exact money, but mappings for
shared team credits and distinct included/purchased pools have not been
established. An installed/loaded model catalog and public API owner/contract
must be resolved before implementation; loaded is not proof of an active
agent or account association. A03 must not bypass M02/M04/M05/M06 ownership.

The 18-ticket catalog passes its planning traceability validator; it is still
proposed and does not validate implementation. The exact model-host and cloud
inputs must be discovered and a reviewable implementation plan approved before
production code, as required by `AGENTS.md`.
