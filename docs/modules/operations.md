# M08 operations — M4 typed core

- Status: **M4 operations delivery implemented and its standalone milestone
  gate Passed**; this guide begins with the earlier focused pure-core increment.
- Module/contracts: M08, `operations.v1` `1.0.0`; CTR-OPS-001..007 and CTR-APP-001
- Approved increment: [focused M4 plan](../plans/integration/m4-operations-change.md), `0.2.0` I01
- Requirements: FR-OPS-002/005/006, NFR-RES-001, NFR-OBS-001; ST-OPS-001
- Evidence: [focused M4 operations record](../evidence/m4-operations.md) and
  [later canonical M4 completion](../evidence/m4-completion.md)

## Purpose and boundary

M08 classifies service health and readiness from immutable leaf receipts and
projects allowlisted versions/configuration presence. It owns no provider
facts, authentication credentials, database connection or process control.
Liveness reads only foundation's current in-process lifecycle phase.

Application facade:
`agentmonitor.modules.operations.application.service.OperationsServiceV1`.
Composition supplies the approved component manifest, registered real leaf
ports, foundation lifecycle reader, actual BuildMetadataV1/configuration
receipts and registry, and a published GetSchemaVersionV1 implementation.

Facade methods are `get_liveness(as_of, correlation_id)` and async
`get_health(request)`, `get_readiness(request)`, `get_versions(request)`,
`get_diagnostic_summary(request)`. Detailed queries require administrator
disclosure; P01 additionally owns actual IAM authorization and origin proofs.
Readiness may use service disclosure. No public route is implemented by M08.

## Meaning of states

Every required component must be fresh and healthy for readiness `ready`.
Missing required leaves remain visible and block readiness. Optional failure
degrades health without blocking healthy required components. A safely
uninitialized IAM leaf yields `setup_required` only when other required
components do not introduce blockers. Required maintenance is explicit.

Expiry is inclusive: `valid_until <= as_of` becomes unknown and retains the
original validity deadline. Future-dated evidence becomes unknown. These
components carry stale/future reason codes rather than a healthy explanation.
There is no average health score, cached-as-current fallback or missing-as-zero
count. Every manifest slot remains in the projection.

Limits are 32 components, 16 indicators per component, 8 reason codes per
sample, and a shared 2-second deadline. Component, reason and indicator keys
have closed code-owned allowlists. Only actual due/running/blocked counts and
registered health duration are permitted indicators. Underlying producers
must enforce actual I/O deadlines; the application cancellation guard does not
make a blocking SQLite call safe.

## Data and privacy

The increment is stateless: no M08 tables, migrations, health history, audit
outbox or persisted configuration. Build and schema versions come through
published receipts. Missing artifact digests keep API/client/frontend version
availability unknown. A declared build target never substitutes for the
actual database revision.

Configuration projections contain registered key/owner and presence only.
No values, provider credential presence, account identity/ID, process/path,
quota/cost/token value, raw error, log dump, environment or secret enters a
diagnostic summary. The domain does not read clocks, files or environments.
Asyncio is isolated to application/health.py; all runtime leaves are injected
published ports. Raw leaf exceptions are discarded and mapped to safe codes.

## Deferred contract families

CTR-OPS-003/005/007 publish typed backup/restore/export/participant declarations
only. No placeholder implementation, route, artifact, maintenance action,
retention job or process/provider mutation is exposed. CTR-APP-001 declares
the exact typed registry/capacity/runtime/alert/collector/operations sections
and their availability. Its implementation still requires genuine producer
queries and root wiring. A missing section stays null, not an invented count.

Full backup/restore/rotation/retention/install/macOS acceptance belongs to the
wider [M08 plan](../plans/modules/m08-operations/plan-v1.md), not this core.

## Verification and operation

Focused pure verification:

```bash
backend/.venv/bin/python -m pytest backend/tests/operations/pure -q
```

This executes no I/O collaborators or provider data. It is not an HTTP,
database, browser, scheduler or failure-isolation acceptance test. The later
[M4 completion evidence](../evidence/m4-completion.md) records the real
leaf/SQLite/HTTP/built-browser/live cadence scenarios and canonical full-M4
gate. This focused command alone does not claim wider-M08 or V1 completion.
