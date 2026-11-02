# M6 capacity constraint API projection

The M05 `CTR-CAP-001` 1.0.0 domain already carries persisted `is_constraining`. The versioned capacity API now exposes this existing value as an optional nullable additive field; OpenAPI and the generated client were regenerated. It does not change the domain, database schema, existing provider semantics or UI.

For Red and Green, an owner-private SQLite backup of the actual installed database was used; no account identities, metric values or credentials were printed. Against baseline `84b0f64`, the real repository and actual API serializer failed because the known persisted constraint state was missing from the wire object. With the change, the same real backup passed because the serializer preserved that state. This is a direct application serializer check, not an authenticated HTTP or browser test. The actual backup contained no USD or explicitly non-constraining quota windows, so their UI behavior remains unverified and is outside this slice.

To repeat using an already-created owner-private backup directory containing `agentmonitor.db`, run from the selected checkout:

```sh
PYTHONPATH=backend/src backend/.venv/bin/python \
  tools/automation/implementations/m6_constraint_projection_check.py \
  --backup-root <private-backup-root>
```

The checker opens its initial SQLite query read-only; the application repository uses its normal read-write database connection against the private backup. It inspects real current windows and prints a closed outcome only. It returns Blocked when there is no eligible real window or the backup cannot be queried. It never logs account IDs, values, paths or provider data; do not point it at a live database. OpenAPI/client compatibility and Ruff passed; authenticated HTTP and live browser verification remain Not Run. No live database or service was modified and no dependency or migration was added.
