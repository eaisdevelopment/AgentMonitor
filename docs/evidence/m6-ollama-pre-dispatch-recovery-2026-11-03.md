# M6 Ollama pre-dispatch recovery

Owner: M04 collection control, under the approved M6 cloud implementation plan.
Requirements: FR-COL-003..008, FR-QUOTA-006; acceptance M6-A07/A09.
CTR-COL-008 and the scheduled-source admission contracts retain their existing
versions and shapes. No source policy, provider transport, API or schema changes.

## Actual failure

After deploying `67527dd`, the account still showed stale balances from the
09:29 UTC successful verification. The exact current source signal identified
a failed run at 09:36 UTC with `dispatch_certainty=not_started`, an existing
durable pre-dispatch terminal record, and a ready global rate gate. Its
classification was nevertheless `outcome_unresolved`. The repository discarded
the terminal's `pre_dispatch_failed` reason before calling the pure classifier.
Scheduled proof therefore failed and the UI disabled another connection check.
This was a local collection failure, not evidence of a provider outage.

## Red and Green

The pure regression first failed with `ollama_cloud_source_signal_invalid`
for the newly covered pre-dispatch reason: 4 failed, 18 passed. The repository
now forwards only the existing durable terminal reason. The classifier returns
`transient_failure` only for a failed run, `not_started` certainty and no
response outcome. Running, unknown, possibly dispatched and response-received
cases remain unresolved; missing terminal reason remains unresolved.

The focused source-signal, scheduled-source admission and connection-status
suite passed **64 tests**, including the independent review's additional
contradictory-outcome negative case. Independent review found no blocking
correctness, privacy or contract issue. A read-only query against the actual unchanged
database then derived a valid scheduled proof with `transient_failure` from
that same persisted failure. No request was dispatched by this query, no
historical record was edited and no fake provider data was supplied.

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=backend/src backend/.venv/bin/python -B -m pytest -q --tb=short backend/tests/collection_control/domain/test_ollama_latest_source_signal.py backend/tests/provider_system/test_scheduled_source_admission.py backend/tests/registry/domain/test_cloud_connection_status.py
```

Deployment and a subsequent actual scheduled success remain pending. This
correction does not waive the full M6 gate or claim natural provider recovery.
It preserves account/binding/source fences, durable rate limits, and all
post-dispatch uncertainty handling. No dependency, license, credential storage,
provider profile, process-control or migration change.
