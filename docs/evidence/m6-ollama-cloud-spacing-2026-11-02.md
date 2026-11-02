# M6 Ollama cloud spacing policy — development evidence

Scope: M6-T011/M6-A09; collection-control domain, approved M6 cloud plan.
This is a pure calculation only; it is not a live scheduler or full M6 evidence.
It has no external I/O and introduces no contract, schema, dependency, license,
privacy, secret-storage, deployment, or migration change.

`PYTHONPATH=backend/src:. python3 -m pytest -q backend/tests/collection_control/domain/test_ollama_rate_policy.py`
failed first because the policy module did not exist, then passed. A separate
regression test failed because the first implementation measured the provider's
retry delay from request start rather than response receipt; after correction,
all five pure tests pass. Ruff formatting and lint pass. Input includes
explicit timezone-aware timestamps and bounded jitter; waits that cannot be represented by a timestamp
raise a distinct blocking error and must never be replaced by a shorter wait.

Persistence, atomic cross-task admission, fair selection, clock-change
handling, request execution, actual provider rate-limit behavior, and
multi-instance behavior remain unimplemented or unverified. This policy is
not wired to a live collector. A future caller must treat validation errors as
blocked admission, never as an immediately eligible poll.

Collection-control regression run on 2 November 2026: the complete existing
`backend/tests/collection_control` suite passed, 37 tests. This does not add
provider-boundary, scheduler persistence, or live rate-limit evidence.

Independent review identified and reproduced three failures: a backwards clock
was accepted, valid waits longer than 31 days were rejected, and timezone
offsets were not normalized. They were fixed with real red/green pure tests;
the collection-control suite now passes 41 tests. Durable clock-change
protection across restarts still requires integration-level evidence.
