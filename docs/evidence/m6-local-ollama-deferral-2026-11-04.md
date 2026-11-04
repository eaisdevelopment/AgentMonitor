# Local Ollama deferral record

On 4 November 2026 the owner instructed: **“defer all local ollama tasks to the next versions to backlog”**.

The [approved scope amendment](../plans/integration/m6-local-ollama-deferral-2026-11-04.md) records the decision and its contract/gate impact. The [future backlog](../plans/integration/future-local-ollama-backlog-v1.json) retains the deferred work under FUT-OLL-LOCAL-001..004. Local installation, model-present, process and local recovery verification are not prerequisites for current M6 or V1 closure.

This records an owner scope decision, not a passing provider test or milestone acceptance. Historical code, tests and live results are preserved. Cloud account coverage, balance/history/alerts, cloud recovery, security, browser checks and the current canonical technical result remain required.

## Implementation and verification

Integration automation now uses the cloud-only exit catalog schema `1.1.0`
(eight acceptance IDs, four stories). `M6-A02`, `M6-A06` and `ST-OLL-002`
are absent from active acceptance, not marked Passed. The exit runner does
not invoke local admission or inventory; its browser verifier does not inspect
Ollama processes. The private snapshot producer schema `1.1.0` removes local
installation/process queries and count fields, so their limits and failures
cannot block cloud evidence. Legacy in-memory fact slots are explicitly
Not Run/unpopulated, not observations of zero local resources.

Red/Green evidence on 4 November:

- `tools/automation/test_m6_local_deferral.py`: four expected Red failures
  against the old policy, then Green after scope selection and classification
  changed. A further regression rejects historical catalogs as current scope.
- `tools/automation/test_m6_evidence_snapshot.py::test_real_cloud_snapshot_does_not_publish_deferred_local_observations`:
  Red against the real read-only database snapshot because it still published
  local counts; Green after removal. No provider responses or telemetry were
  invented, copied, replayed or written.
- Focused exit/direct/scope/cloud/recovery/snapshot and ticket lifecycle suite:
  **106 passed**, including current real capacity/history reconciliation.
- `AUTO-QUALITY`, `AUTO-PLAN-CHECK`, `AUTO-DOCS-CHECK` and ticket planning
  validation passed. Ticket completion remains unavailable because cloud work
  is unfinished; this deferral does not close M6.
- Independent review identified the residual local database dependency; the
  correction was re-reviewed with no remaining findings.
- Real browser verification used authorized normal local sign-in. The first
  isolated nonpersistent session could not establish the verifier's revision
  request; using an isolated persistent context established the installed
  revision and reconciled one actual current/history target. The final
  stability check returned `dashboard_registry_changed_concurrently`, so the
  browser result is **Blocked**, not Passed. The local process result remains
  explicitly `not_run/local_ollama_deferred` and is not a completion dependency.

The dashboard stayed online at installed revision
`5839f05e029005d72cff89ddba571b4794d11482`. No product code, public API, database
schema, dependency, provider state, or running-agent change was made. The full
current-revision cloud `AUTO-M6-EXIT` and owner review remain separate work.
