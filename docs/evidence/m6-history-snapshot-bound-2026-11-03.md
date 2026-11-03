# M6 current-history snapshot range correction

Owner: integration evidence producer. Requirements FR-COL-004/005/008,
AC-HIST-001 and M6-A05. CTR-CAP-006 remains unchanged.

Once the actual automatic Ollama reading became fresh, the real completion
snapshot returned `m6_snapshot_query_unavailable`. A sanitized exception trace
identified `capacity_history_range_too_large`: its history query used a start
365 days before `as_of` and an exclusive end one microsecond after `as_of`.
That exceeds the existing contract's maximum range by one microsecond.

The new real installed-state regression failed with that blocked result before
the correction. The exclusive upper bound is now `as_of`; it preserves the
365-day contract and includes the already committed current observations.
The actual current target and retained prior observations are queried through
existing module ports; no provider request, invented telemetry, database edit
or profile mutation is performed.

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=backend/src backend/.venv/bin/python -B -m pytest -q --tb=short tools/automation/test_m6_evidence_snapshot.py
```

Green: four tests passed against the real installed database, including the
previously failing current balance/history reconciliation. This verifies the
snapshot query, not all M6 acceptance criteria. No API, schema, dependency,
license or secret-handling change.
