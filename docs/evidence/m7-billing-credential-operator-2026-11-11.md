# M7 owner-local billing credential entry evidence

- Evidence ID: M7-ENROLL-2026-11-11; delegated M02/composition implementer.
- Authority: approved focused M7 implementation, T002 / M7-A01; see
  [implementation authority](m7-implementation-authority-2026-11-11.md).
- Requirements: FR-BUDGET-001, FR-AUTH-004, NFR-SEC-001; acceptance contributions
  M7-A01, AC-V1-007, AC-TEST-001/002. This does not close those full criteria.
- Contracts: consumes CTR-REG-014 1.0.0 billing metadata and existing CTR-REG-011
  binding/lock types; no shared contract, API, UI or migration changes.
- Base: `e544f8cfa7ff7c1910b4c6cbaa6ff0efc0fb2fdc`, `m7-api-budgets` worktree;
  changes uncommitted during verification, 2026-11-11.

## Implemented slice

`billing_credential_operator` is a candidate owner-local entry point with
`--data-root`, `--account-id` and `--resource-id`; it accepts no key argument.
The eventual installed copy command must use `--account-id=<opaque-id>` and
`--resource-id=<opaque-id>` because generated opaque IDs can begin with `-`.
Terminal refusal occurs before database access. With a terminal, actual M02
account/resource/provider eligibility is checked before service configuration
lookup or any secret prompt. The existing nonsecret deployment-selected file
helper and retained location metadata establish the selected credential file.
The command's `enroll_selected_billing_credential` wrapper shows safe provider,
organization and owner-account labels before hidden entry, using existing
`safe_label` and only selected registry lookups. `Ungrouped` is used solely when
no organization is assigned; a missing/failed organization lookup displays
`Organization unavailable`. The displayed target remains in the selection guard,
so metadata changes after display invalidate the flow. No extra confirmation
prompt was added. No account, scope, identity or monitoring configuration is
changed by the command.

`enroll_billing_credential` reuses the existing account lock, prepare/retry,
hidden prompt, store, activation and pending-cleanup sequence through one private
shared implementation. Claude maps to the Anthropic prompt/namespace and Codex
to OpenAI. Existing Ollama public and private entry signatures remain available.
The captured account version, exact resource, connection version, scope ID and
scope generation are checked before prepare/prompt, before storage and immediately
before activation; provider/lifecycle/monitoring metadata is checked as well.
Derived credential-status fields do not form part of this identity comparison.
The existing record-version fence, selected-file checks, lock lease validation,
core-dump protection and token-buffer clearing remain in the flow.

The legacy Ollama enrollment, disconnect and cleanup paths explicitly verify the
actual account provider. This retains their effective Ollama-only restriction
after the registry loader gained billing-account support. No duplicate lock,
credential store, provider profile or credential table was added.

## Red evidence

The initial operator subprocess test lacked an explicit import root and failed
with `No module named 'agentmonitor'`; this was setup failure, not behavioral Red.
After supplying the worktree source path and before creating production code:

```text
/home/dev/Nextcloud/Code/AI/AgentMonitor/backend/.venv/bin/pytest -q backend/tests/registry/test_billing_credential_operator.py
```

**2 failed**, with the real subprocess reporting
`No module named agentmonitor.composition.billing_credential_operator`.
The assertions required operator help and non-terminal refusal. This records
missing executable capability, not a regression in an existing key-storage flow.
No empty shell or deliberately broken implementation was used.

Review then found a legacy provider-boundary gap. Actual isolated billing metadata
and an empty protected file allowed `cleanup_ollama_credential` to return normally
for a Claude/Codex account. Before adding the provider fence, the integration
suite produced **2 failed, 2 passed in 4.99s**, with
`AssertionError: legacy Ollama helper must reject billing provider`.
After the correction, both legacy cleanup and disconnect calls reject those
accounts before changing state or file contents.

A subsequent actual PTY check for owner context produced **2 failed, 2 passed
in 13.30s** before the display wrapper was implemented: the hidden prompt lacked
the actual account label. The same real terminal scenario now verifies provider,
account and assigned-organization labels (or actual Ungrouped) before sending EOF.

## Green and real boundaries

The focused operator/guard suite passes six tests, including these scenarios:

- M7-ENROLL-001/002: real process help and non-terminal refusal; no database created.
- M7-ENROLL-003: production account/billing creation in isolated real SQLite;
  wrong or absent resource/provider rejected; actual account rename invalidates
  the captured target; archived account rejected; no provider profile created.
- Real PTY invalid-target checks reject before service lookup and secret prompt.
- Both real provider-specific hidden-terminal prompts show the selected owner
  context and run with terminal echo off.
  The test sends only EOF, never a credential. The actual protected file stays
  empty, the pending reference survives with binding generation zero, and later
  archive moves that reference to cleanup pending. The selected-location callback
  performs real location validation; it is not a substituted result.
- M7-ENROLL-004: pure constructed DTOs verify changed scope generation, scope ID,
  resource and connection version are rejected without I/O.
- Real subprocess legacy cleanup/disconnect rejection preserves billing references.

The hidden-terminal and metadata guard tests do not establish successful key
storage or activation. No fake key, simulated store proof or cleanup-complete
claim was introduced. The subprocesses use an explicit nonsecret import path;
they do not inherit arbitrary credential-bearing environment values.

Final regression command, after the provider fence and formatting refactor:

```text
PYTHONPATH=backend/src /home/dev/Nextcloud/Code/AI/AgentMonitor/backend/.venv/bin/pytest -q backend/tests/registry/test_billing_credential_operator.py backend/tests/integration/registry/test_billing_enrollment_guards.py backend/tests/registry/test_ollama_enrollment_terminal.py backend/tests/registry/test_ollama_operator_labels.py backend/tests/registry/test_credential_binding_policy.py backend/tests/registry/test_credential_lock_process.py backend/tests/registry/test_credential_staging_guard.py backend/tests/registry/test_billing_env_format.py backend/tests/registry/test_billing_env_store_empty.py backend/tests/contracts/test_ollama_env_format.py backend/tests/contracts/test_ollama_env_stream.py backend/tests/contracts/test_ollama_env_import_policy.py backend/tests/contracts/test_ollama_env_selection.py
```

**78 passed in 28.38s**, exit 0, no skips. This includes legacy terminal/import,
binding, real process/staging locks, generic namespace, empty-file and Ollama
format/stream/selection regressions. Ruff check/format and scoped diff checks
passed. Strict mypy passed for four files:

```text
MYPYPATH=src /home/dev/Nextcloud/Code/AI/AgentMonitor/backend/.venv/bin/mypy --strict --explicit-package-bases src/agentmonitor/composition/ollama_credential_enrollment.py src/agentmonitor/composition/billing_credential_operator.py tests/registry/test_billing_credential_operator.py tests/integration/registry/test_billing_enrollment_guards.py
```

## Files and limitations

Changed files in this handoff:

- `backend/src/agentmonitor/composition/ollama_credential_enrollment.py`
- `backend/src/agentmonitor/composition/billing_credential_operator.py`
- `backend/tests/registry/test_billing_credential_operator.py`
- `backend/tests/integration/registry/test_billing_enrollment_guards.py`
- `docs/evidence/m7-billing-credential-operator-2026-11-11.md`

No dependency/license/migration changes. No real owner account, credential,
provider profile, service or configuration was read or modified by this work.
All registry/file/process tests use isolated metadata, empty files and real local
OS behavior; constructed byte/DTO tests have no I/O. No mocks, fakes, provider
recordings, seeded telemetry or test-only production paths were used.

The candidate CLI is not a claim that an installed copy command or current
service deployment is ready. Actual deployed service-selection success, owner key
entry, successful physical storage/import, activation, rotation/deletion and
provider/API permission verification are **Not Run** here. Billing UI/status and
copy-command wiring remain root work. T002 and the full M7 gate remain in progress.
