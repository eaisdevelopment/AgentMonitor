# Installed M7 financial storage and collection increment

Status: Intermediate T014/T003; operational activation passed, full financial
acceptance remains open. Approved focused plan 1.1.0; FR-BUDGET-001/004,
AC-OPS-003, AC-TEST-001/006, M7-A10. No owner account or credential was configured.

## Exact candidate and execution

- Committed/installed revision: `437a232866658ca38446d3c57a4cd7ce98c2e156`.
- Previous installed revision: `7e252b869e28d62582b675f9e3cecc1612d6c5c4`.
- Frontend build digest: `206c6c502259e740177fd42d8bea8e062a5fa767f01de3e1204cf6f265964dea`.
- Schema: `v1_0731 → v1_0733`.
- Migration catalog digest: `06f74722b3d533f111248c986886735d923faa23ef308b11ce1e4f4dc3e93046`.
- Isolated preparation passed with no blockers, including real migration/build
  and backup checks; its backup digest is isolated rehearsal evidence, not the
  installed backup receipt.
- Candidate was retained under the existing fixed release directory while
  holding the production transition locks, then verified by its retained controller.

Executed from that retained release using the existing fixed runtime:

```text
PYTHONPATH=backend/src:. /home/dev/.local/share/agentmonitor/releases/m6-runtime-2fedf0809fc9/bin/python -B -m tools.automation.implementations.auto_m7 --lane deploy --check financial_activation --expected-revision=437a232866658ca38446d3c57a4cd7ce98c2e156
```

Actual terminal result:

```text
M7 CHECK controller_preflight: PASSED
M7 CHECK candidate_started: PASSED
M7 CHECK installed_revision_loopback: PASSED
M7 CHECK restart_finalized: PASSED
M7 CHECK operator_command: PASSED
M7 CHECK billing_worker_command: PASSED
M7 CHECK lan_readiness: PASSED
M7 CHECK installed_postcheck: PASSED
M7 CHECK authenticated_financial: NOT_RUN (m7_separate_real_evidence_required)
M7 CHECK collector_continuity: NOT_RUN (m7_separate_real_evidence_required)
M7 CHECK backup_recovery: NOT_RUN (m7_separate_real_evidence_required)
```

The command exited 3, intentionally an intermediate operational slice. It did
not pass AUTO-M7-DEPLOY or the full M7 exit. The earlier b69d96a failure did not
reproduce; its original cause remains unknown. The diagnostic change did not
alter transition safety decisions, and this success does not retrospectively
prove what caused that prior failure.

## Read-only installed verification

After terminal completion:

- Service active/running; WorkingDirectory matches the retained revision above.
- Restart policy restored to `on-failure`; no active cutover journal remains.
- Read-only SQLite schema observation: `v1_0733`.
- Loopback `http://127.0.0.1:43110/`: HTTP 200.
- LAN `http://192.168.1.18:43110/`: HTTP 200.

Executed existing built-browser probe:

```text
node frontend/tests/browser/m7/verify_setup.mjs 437a232866658ca38446d3c57a4cd7ce98c2e156
```

At `2026-11-11T20:46:03.621Z` the actual shared browser passed authentication,
API build-manifest revision, Overview, Add API billing account form, retained
promotion/support/footer and read-only checks. It observed 35 requests and zero
unsafe mutation requests. This closes the earlier authenticated setup-surface
check for this installed revision; it is not a populated financial DOM pass.
Existing tabs were preserved.

A subsequent authenticated read-only paged account/billing-connection inventory
was complete for 15 registry records. No Anthropic/OpenAI billing connection
existed; two active Ollama accounts use their existing cloud connection path.
No credential values, environment values or provider profiles were read. Absence
of a configured billing connection does not prove the owner lacks admin access.

Root opened a new shared browser tab on Accounts and expanded Add API billing
account without submitting it. The owner was asked once to use the actual local
setup flow for an Anthropic Console administrative credential, or identify absent
access. This affects that first-provider live lane only. Independent Overview,
funds projection, other-provider integration and full verification remain work.

## Remaining acceptance and impact

Positive provider billing report, atomic monetary commit/reopen, exact API/DOM
comparison, enabled browser-closed billing refresh, complete existing-collector
continuity and installed financial recovery evidence remain Not Run. Existing
isolated restoration tests are narrower than a full installed recovery claim.
No subscription profile or running user agent was restarted/modified; only the
AgentMonitor service underwent the authorized transition. Protected managed
configuration remained under the existing deployment procedure. No new package,
license, secret custody or publication effect. Code is committed and installed;
this record makes no GitHub publication claim. M7 remains open.

### Post-activation collection observation

At `2026-11-11T20:52:12.838Z`, authenticated read-only collection-run queries
observed completions after `20:46:03Z`: Claude one Partial, Codex three Succeeded
across two accounts, Ollama three Partial. This proves continued execution for
those observed runs; Partial is not reclassified as Succeeded, and this is not
full inventory/financial continuity acceptance. No provider retry was triggered.
