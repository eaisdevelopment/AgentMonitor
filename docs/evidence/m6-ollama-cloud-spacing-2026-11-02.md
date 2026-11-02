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
explicit timezone-aware timestamps and bounded jitter; too-large retry delays
raise an error and must not be interpreted as permission to poll early.

Persistence, atomic cross-task admission, fair selection, clock-change
handling, request execution, actual provider rate-limit behavior, and
multi-instance behavior remain unimplemented or unverified. This policy is
not wired to a live collector. A future caller must treat validation errors as
blocked admission, never as an immediately eligible poll.
