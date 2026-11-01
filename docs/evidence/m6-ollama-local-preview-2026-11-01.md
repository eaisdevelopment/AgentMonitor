# M6 Ollama local catalog — intermediate evidence

**Status: intermediate; full M6 is not complete.** The owner approved the
[local change plan](../plans/integration/m6-ollama-local-vertical-change.md)
on 1 November 2026. Scope: M6-T008/T009/T014 and contributions to
M6-A02/A08/A09; no cloud identity, capacity, history, alert or process
correlation completion is claimed.

## Behavior and contracts

A03 observes the fixed local Ollama 0.24.0 daemon using bounded read-only
`GET /api/version`, `/api/tags`, `/api/ps`, and a final version recheck.
Requests use no proxy or redirects, 256 KiB body and 16 KiB header bounds,
three-second per-request and twelve-second overall deadlines, and a
process-local nonblocking single-flight lock. The authenticated versioned
API requires `read:telemetry` and rejects unknown parameters. M03 catalog
contract `CTR-PROV-OLLAMA-LOCAL-CATALOG-001` version `1.0.0` distinguishes
available empty results from unavailable sources. P02 consumes the generated
API, renders both catalogs, records source/timestamps, and auto-refreshes with
explicit current/stale/unknown state. No user process, model or provider
profile is modified; no new dependency or database migration is introduced.

The local catalog is independent of provider registry installation records.
The Ollama provider manifest remains unregistered and pending broader
capability admission: account CRUD, cloud access and M6-A01 are not claimed.
The only current daemon snapshot has zero installed/loaded models. The owner
showed a desktop app with a model selected; its connection to this daemon has
not been established. The UI does not treat the empty service list as proof
that other applications have no models.

## Verification

- Red: real local adapter test failed on missing Ollama adapter; authenticated
  HTTP test returned 404; browser test could not find the catalog. Green: the
  actual adapter, file-backed SQLite/API and built-browser checks pass against
  the real 0.24.0 daemon's empty state.
- Real adapter checks include a concurrent-read Red before the lock and Green
  with a real service; pure tests verify name, route, deadline, version,
  contract, freshness and status policies. A real browser caught a duplicate
  initial request and passed after the component was kept mounted.
- `AUTO-M6-LOCAL-ADMIT` passed the narrow real-service/API/browser scope and
  observed a real 30-second refresh. Its selected source/test digest was
  `5d306b5cf52a70f26c262e1033f3aa7b0fbadfe849279d77a412963d3fc3fa2d`
  before and after the run. This is not the complete revision digest or the
  M6 exit receipt. Separate responsive, TypeScript and API schema
  compatibility checks passed for their tested revisions.
- **Not Run:** real populated-model catalog, a natural source failure and
  recovery, a daemon replacement with the same version, provider account
  identity/balance, cloud rate limiting, process correlation and the full
  M6 gate. The HTTP reader currently rejects chunked bodies, so a populated
  catalog using that transfer mode will show unavailable. No synthetic
  provider data was used to claim otherwise.

## Security, operations and rollback

The fixed loopback source has no user-supplied target; redirects, proxy use,
unbounded bodies and raw provider payload output are rejected. Only bounded
model identifiers cross the adapter boundary. Endpoint failures do not affect
the dashboard's other providers. Client and daemon versions remain distinct;
CLI installation discovery is not wired to the registry pending executable
path/TOCTOU review. The lock is per process and does not coordinate multiple
service processes. No dependency/license change or migration is introduced.
An installed rollout requires a separately verified recoverable service
transition, preservation of the existing configuration and data, and live
dashboard/rollback checks. `AUTO-M6-LOCAL-ACTIVATE` remains blocked because the
draft transition does not yet provide a race-free child-process guard and
verified authenticated/LAN readiness and rollback. Until then the running
dashboard is unchanged.

A read-only process/cgroup snapshot found 30 Claude/Codex-named processes
outside the dashboard service cgroup and none inside at that instant. This
supports separation of those currently observed processes, but is not a
guarantee about later children or all possible agent names. Process arguments,
environment and content were not inspected.
