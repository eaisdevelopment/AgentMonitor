# ADR-0013 — Technical evidence gates are the executable local milestone gate

**Status:** Accepted by explicit owner direction, 2026-09-25  
**Supersedes:** the use of detached M0 reviewer approvals as a prerequisite for
local milestone execution  
**Scope:** every V1 milestone executed on the owner’s Linux development machine

## Decision

Detached `owner`, `security_privacy`, `test_integrity`, and `root_integration`
approval records are advisory evidence. They must not stop an executable local
milestone gate or force the owner to repeat a review workflow before seeing the
product. `--require-technical-live` is the local release policy: it validates
current artifact digests, capability mappings, schema/contract bindings, and
then lets the milestone’s real provider, database, HTTP, and browser checks run.

The strict `--require-adapter-live` validator remains available for an optional
governance audit, but no M3–M8 execution gate may call it as its prerequisite.
The same rule applies to future provider and API-budget milestones.

This does not turn unavailable conditions into passes. Missing accounts,
providers, processes, credentials, natural stall windows, or historical Red
evidence remain explicitly `Blocked` or `Not Run`. This decision also does not
declare M0 G9 complete, authorize remote/hosted release, or permit provider
profile mutation, process control, secret access, or raw-content retention.

## Required technical checks

- exact current mapping/schema/contract/probe bindings;
- real owner/provider observations where the milestone claims them;
- real file-backed SQLite, loopback HTTP, generated client, and built browser;
- security/privacy, migration, quality, mutation, documentation, and Git gates;
- truthful reporting of every unavailable or unexecuted scenario.

## Evidence

The policy is executable through:

```text
./.venv-m0-g1/bin/python tools/discovery/m3_handoff_validate.py --require-technical-live
python3 tools/automation/run.py AUTO-M3-EXIT
```

The first command is a structural/technical preflight and performs no provider
I/O. The second command remains the real local M3 vertical gate. Later
milestone gates must use the same technical policy and retain their own real
boundary checks.

