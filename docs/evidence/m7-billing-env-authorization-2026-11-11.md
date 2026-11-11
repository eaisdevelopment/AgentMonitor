# M7 guarded Anthropic environment authorization evidence

- Status: Intermediate composition contribution; no ticket or M7 acceptance claim.
- Authority: approved M7 T002/T006 and M7-A01; focused execution plan 1.1.0 and
  [implementation authority](m7-implementation-authority-2026-11-11.md).
- Requirements: FR-BUDGET-001, FR-AUTH-004, NFR-SEC-001; contributions to
  AC-V1-007 and AC-TEST-001/002. Real positive access remains unverified.
- Base observed: `032a43f188d0c044f4e67f3adadea5d5e5a39707`.
- Owner: composition; published contracts unchanged. Consumes existing M02
  inherited account-lock capability and A01 source authorization protocol/sink.

## Implemented boundary

`AnthropicEnvAuthorizationV1(binding_id, account_id, credential_lock,
credential_file)` derives only the Claude managed variable name. It accepts real
inherited account/file capabilities, validates them at construction and before
reading, reads bounded mutable chunks using the shared stream parser, verifies
the total against the pinned file size, and validates both capabilities again
before applying the result to the exact `AnthropicCostAuthorizationSinkV1` type.
The sink permits only `x-api-key`; this reader has no URL or provider selector.
Owned chunks and the returned token are cleared in `finally`. Ordinary failures
expose only `anthropic_cost_authorization_unavailable`; deadline `TimeoutError`
is preserved. There is no public key return or diagnostic containing contents.

Physical capability validators are reused from the existing implementation in
composition. No provider adapter gains imports of another provider's internals.
The existing policy, fingerprint, lock format and credential lifecycle are
unchanged. Python immutable temporaries and transport internals are not claimed
to provide complete heap erasure.

This object proves physical guarded access only. The dedicated worker must
resolve the actual active M02 binding and generation and retain the resource /
scope-generation fence before issuing authorization. A persisted pending binding
ID is sufficient for the negative empty-file tests; it is never converted into
a fabricated active-binding reference or presented as active access proof.

## Red and Green

Before adding the composition implementation, the real isolated SQLite metadata
and empty-file test failed at the missing-owned-capability assertion:

```text
/home/dev/Nextcloud/Code/AI/AgentMonitor/backend/.venv/bin/pytest -q backend/tests/registry/test_billing_env_authorization.py
1 failed in 1.48s
AssertionError: guarded Anthropic credential authorization is missing
```

This was a new-capability Red, not proof of a preexisting behavioral defect.
After implementation, the availability probe was replaced by static imports.
The six behavioral cases passed in 14.81s: empty selected entry, replaced file
inode, replaced account-lock inode, expired file lease, expired account-lock
lease, and rejection of the actual legacy Ollama sink type.

Each case uses ordinary production account registration, billing metadata and
pending-binding preparation in real file SQLite, a real empty mode-0600 file,
actual kernel/account locks, and an actual HTTPSConnection object which stays
unconnected. The exact A01 sink remains unapplied, its missing-authorization
check fails, its connection header buffer is empty, and no network call occurs.
The wrong-sink test uses a real legacy production sink, not a substitute sink.
No nonempty credential file, fake key, active-store proof or provider response
is supplied. The success path of key reading/header application is Not Run.

Post-implementation scoped regression:

```text
PYTHONPATH=backend/src /home/dev/Nextcloud/Code/AI/AgentMonitor/backend/.venv/bin/pytest -q backend/tests/registry/test_billing_env_authorization.py backend/tests/registry/test_billing_env_store_empty.py backend/tests/registry/test_credential_lock_process.py backend/tests/registry/test_billing_env_stream.py backend/tests/contracts/test_ollama_env_stream.py
75 passed in 15.60s
```

Ruff check passed for the new composition and test files. Strict typing from
`backend/` also passed:

```text
MYPYPATH=src /home/dev/Nextcloud/Code/AI/AgentMonitor/backend/.venv/bin/mypy --strict --explicit-package-bases src/agentmonitor/composition/billing_env_authorization.py tests/registry/test_billing_env_authorization.py
Success: no issues found in 2 source files
```

## Handoff and limits

Files: `backend/src/agentmonitor/composition/billing_env_authorization.py`,
`backend/tests/registry/test_billing_env_authorization.py`, and this evidence.
No migrations, dependencies, license changes, published contracts, owner account
configuration, profiles, services or owner credential files were changed/read.
No source policy or Ollama fingerprint changes belong to this increment.

Dedicated-worker wiring, lifecycle/generation admission, actual owner key entry,
positive authorization, real provider access, report storage, HTTP/browser
financial reconciliation and the full canonical completion gate remain outside
this evidence. They must not be inferred from these negative boundary passes.
Work is preserved while the owner-requested plan review proceeds.
