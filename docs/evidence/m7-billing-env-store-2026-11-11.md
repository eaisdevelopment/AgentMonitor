# M7 managed credential namespace evidence

- Evidence ID: M7-ENV-2026-11-11; delegated M02 credential-file implementation.
- Authority: approved T002 under focused execution plan 1.1.0;
  [implementation authority](m7-implementation-authority-2026-11-11.md).
- Requirements: FR-BUDGET-001, FR-AUTH-004, NFR-SEC-001; acceptance contributions
  M7-A01, AC-V1-007, AC-TEST-001/002. Full criterion acceptance is not asserted.
- Base: `f21e367506f7de54dcf1432b827162ee7fab089c`, `m7-api-budgets` worktree.
- Contracts: unchanged CTR-REG-011 bindings/locks and unchanged Ollama
  `ENV_AUTHORIZATION_POLICY_V1`; no published contract or migration edits.

## Bounded implementation

New `adapters/credential_env/format.py` holds pure canonical encoding, exact-name
read/edit, provider namespace selection and managed-name classification. The
closed registry provider keys map to the frozen prefixes:

| Registry provider | Managed prefix |
|---|---|
| claude | AGENTMONITOR_ANTHROPIC_API_KEY_AMCB_ |
| codex | AGENTMONITOR_OPENAI_API_KEY_AMCB_ |
| ollama | AGENTMONITOR_OLLAMA_API_KEY_AMCB_ |

Each prefix is followed by the uppercase 32-character hexadecimal component of
the existing generated `amcb_` binding ID. Unknown providers and malformed binding
IDs fail closed. Existing value limits and canonical Base64 behavior are retained.

`composition/ollama_env_store.py` exposes the frozen `update_managed_env` and
`import_managed_env_variable` interfaces, each requiring explicit `provider_key`.
Both delegate to the existing guarded writer body. Legacy `update_ollama_env`
and `import_ollama_env_variable` remain wrappers with their existing signatures,
including private held-guard/import arguments and sanitized legacy error codes.
The old Ollama format API still rejects Anthropic/OpenAI names.

Literal imports reject reserved entries from all three namespaces. The existing
name-only orphan scanner now returns provider plus binding ID and cleanup removes
each entry using that provider's namespace. Location-release checks recognize all
three namespaces. No provider gets a separate file lock, account lock, staging
guard or location record: `.ollama-env.lock` and existing staging/location names
are intentionally retained as compatibility artifacts. The safe-parent helper
remains reused from the existing capability module, as agreed for this increment.

## Red and pure Green

Before production changes:

```text
/home/dev/Nextcloud/Code/AI/AgentMonitor/backend/.venv/bin/pytest -q backend/tests/registry/test_billing_env_format.py
```

**3 failed, 1 passed**, exit 1. Two behavioral Reds were
`DID NOT RAISE ValueError`: the existing literal-import guard accepted Anthropic
and OpenAI managed names. The third was a separate new-capability assertion,
`provider-neutral credential format is missing`. This missing-seam assertion is
not presented as an individual existing writer-behavior regression. No empty
production shell or intentionally broken implementation was used.

After implementation, new tests plus existing Ollama format/stream/import tests
produced **45 passed in 0.36s**. The historical availability probe was then removed
in favor of ordinary static imports; formatting and strict typing were checked.

Post-refactor regression command:

```text
/home/dev/Nextcloud/Code/AI/AgentMonitor/backend/.venv/bin/pytest -q backend/tests/registry/test_billing_env_format.py backend/tests/registry/test_billing_env_store_empty.py backend/tests/contracts/test_ollama_env_format.py backend/tests/contracts/test_ollama_env_stream.py backend/tests/contracts/test_ollama_env_import_policy.py backend/tests/contracts/test_ollama_env_selection.py backend/tests/adapters/providers/ollama/test_env_authorization_policy.py backend/tests/adapters/providers/ollama/test_env_capability_policy.py backend/tests/adapters/providers/ollama/test_env_helper_process_policy.py backend/tests/registry/test_credential_staging_guard.py
```

**68 passed in 1.80s**, exit 0, no skips. Coverage includes namespace identity,
canonical codec bounds, exact replacement/deletion preserving other namespaces,
legacy Ollama rejection of foreign names, malformed reserved entries, all-provider
import reservations, existing selection/descriptor policy, and real staging-guard
exclusion/replacement checks. Constructed byte strings remain exclusively in pure
no-I/O tests; they are never written to a credential file.

The seven new real empty-file verification cases first passed independently
(**7 passed in 0.31s**) and are included in the final 68. These were added after
the writer implementation as bounded verification, not claimed as a separate
pre-implementation behavioral Red. They create only empty 0600 files in isolated
0700 directories, use internally generated binding handles, and verify:

- all three providers can remove an absent entry without changing the empty file;
- the generic and legacy writer retain the same persistent file-lock inode;
- a missing literal import source fails without writing any entry;
- a held real kernel file lock excludes both new and legacy entry points.

No key-shaped value is written or stored. All files remain empty; no owner file
is involved. Nonempty-file storage and cleanup remain outside this evidence.

Strict mypy passed for six source/test files:

```text
MYPYPATH=src /home/dev/Nextcloud/Code/AI/AgentMonitor/backend/.venv/bin/mypy --strict --explicit-package-bases src/agentmonitor/composition/ollama_env_store.py src/agentmonitor/adapters/credential_env src/agentmonitor/adapters/providers/ollama/cloud_balance/env_format.py tests/registry/test_billing_env_format.py tests/registry/test_billing_env_store_empty.py
```

Ruff check/format and scoped `git diff --check` passed.

## Compatibility and remaining boundaries

Before and after the changes, the actual pure Ollama probe fingerprint was:
`047d2bf64f70eae87a54223cb6f1aa3bec240c84ae99c0cc2155db8342a5110f`.
The unchanged authorization-policy source SHA256 was:
`b483b865b3cc760cb8f1a631647de0db8a1af34502a8142ad386b06c79bf96c9`.
No changed policy was smuggled into existing admission lineage.

Files owned here: new credential-env package initializer and formatter, existing
Ollama format compatibility module, existing environment store composition,
`test_billing_env_format.py`, the additionally authorized
`test_billing_env_store_empty.py`, and this evidence record. Enrollment/operator,
shared contracts, live verification and deployment are root-owned later work.
No dependencies, licenses, migrations, provider profile changes or service changes.
No real credential, owner environment file, account data or provider payload was
read. No mocked I/O, seeded credential file, simulated store proof or activation
was used. Successful credential storage/import/rotation, nonempty-file cleanup
and provider access require owner-entered actual credentials and remain **Not Run**.
This evidence does not close T002 or the full M7 gate.
