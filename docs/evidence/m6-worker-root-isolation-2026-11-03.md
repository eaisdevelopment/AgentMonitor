# M6 worker discovery isolation by data root

- Evidence ID: `M6-WORKER-ROOT-ISOLATION-2026-11-03`
- Owner: M04 composition; approved [M6 cloud plan](../plans/integration/m6-ollama-cloud-implementation-change.md)
- Requirements: FR-COL-003..008, FR-SAFE-001/002; acceptance M6-A07/A09
- Candidate base: `eef50e7`
- Recorder/date: AgentMonitor engineering, 3 November 2026
- Status: isolated candidate; root deployment and installed-service continuity pending

## Actual defect and correction

The supervisor discovered every `agentmonitor-cloud-worker-*.service` under
the user manager. It then evaluated each against its own data root and exact
worker arguments. A genuine worker belonging to another installation therefore
caused quarantine. The installed service becoming unavailable after the local
test gate motivated this check; the private overlap reproduction below proves
the mechanism without using the installed root.

New unit names contain the full SHA256 of the selected absolute canonical data
root, followed by the existing random 32-hex-character start token. Discovery
uses only that root's prefix. The root path is not exposed in the unit name.
Noncanonical aliases are rejected rather than creating different authority
interpretations for the same path. Existing pinned directory/lock ownership,
mode, inode and no-follow checks remain in force.

The pinned own-root marker accepts either the exact current namespaced format
or the exact previous token-only format. Legacy acceptance is used only when
recovering that marker, never for global discovery. The unchanged full worker
identity check still verifies executable, root and arguments, invocation,
description, transient properties and cgroup before any stop. Foreign-root
markers and unknown/lookalike units in the current root namespace fail closed.
Unmarked global legacy units are never stopped or adopted by discovery.

The marker read and size checks use the computed maximum of the fixed supported
format: 132 bytes including newline (131 bytes for the unit name). Oversized and malformed content remains
rejected. No public contract, database schema, API, dependency or credential
format changed.

## Real Red and Green

Two supervisors used distinct real temporary roots with no database or
credentials. The test started the first real transient worker, observed its
unit loaded through systemd, and then started the second while the first task
was still active. Before production changes:

```text
test_real_supervisors_in_different_roots_do_not_quarantine_each_other
AssertionError: assert 'quarantined' == 'not_admitted'
1 failed in 2.04s
```

After namespaced discovery, the same test passed in 4.31 seconds. Both returned
`not_admitted`, remained available, and created no database. The actual systemd
boundary was exercised; no simulated manager, subprocess or provider response
was used.

Focused command used for Red and Green:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=backend/src \
  /home/dev/Nextcloud/Code/AI/AgentMonitor/backend/.venv/bin/python -B \
  -m pytest -q --tb=short \
  backend/tests/adapters/providers/ollama/test_cloud_worker_boundary.py::test_real_supervisors_in_different_roots_do_not_quarantine_each_other
```

Added checks also prove that another root leaves an actual legacy worker alone,
that its own exact persisted legacy marker recovers that worker, and that a
subsequent normal namespaced start works. Oversized/foreign-root markers and
noncanonical root aliases are rejected. The existing real lookalike-unit check
now uses the current root's namespace and confirms that the lookalike remains
active when the supervisor quarantines. Existing cancellation, parent death,
start-authority, lock replacement and same-root serialization tests remain.

## Regression checks and explicit provider-boundary disclosure

The full existing worker-boundary file was then run once:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=backend/src \
  /home/dev/Nextcloud/Code/AI/AgentMonitor/backend/.venv/bin/python -B \
  -m pytest -q --tb=short \
  backend/tests/adapters/providers/ollama/test_cloud_worker_boundary.py
```

Result: **17 passed in 34.05 seconds**. Ruff lint/format and strict mypy passed
for both changed Python files using explicit `backend/pyproject.toml` settings.

This full-file selection unintentionally included the existing
`test_real_anonymous_provider_helper_is_contained_by_transient_unit`, exceeding
this task's no-provider restriction. That test invokes the existing
`probe_cloud_balance_endpoint_v1()` in its own transient helper unit, observes
the real helper child, stops only that test-owned cgroup, and verifies it is
empty. It **passed**. The probe may contact the fixed official anonymous
endpoint; no credentials or account were supplied. It would be false to call
the entire regression run provider-free. This scope deviation was reported
immediately to the root steward, and no further provider test was run. The new
overlap and legacy-isolation tests themselves used only private no-database
workers and systemd metadata.

## Integration, privacy and rollback

Only the supervisor, its boundary tests and this evidence record changed. The
installed data root, running dashboard service, `.env`, provider profiles and
user agents were not modified. Unit cleanup targeted only exact test-owned
workers; no unmarked foreign legacy unit was stopped. No key, account identity,
provider response or private path content appears in evidence.

Root must deploy through the canonical update, observe ordinary installed
collection resume, and confirm a later local gate cannot quarantine that
service. Full M6 completion remains **Not Run** for this isolated candidate.
Legacy marker recovery still requires the exact executable/argument identity;
an old worker from a different runtime is not silently adopted.

For rollback, first complete normal owned-worker shutdown and marker cleanup.
The older supervisor cannot parse a new namespaced marker and will quarantine
if such a marker remains; do not delete an unresolved marker to bypass recovery.
No database migration or provider-state restoration is required.
