# M7 billing worker physical grants — bounded increment

Date: 2026-11-11, checked at 17:56 UTC. Baseline: `7e252b8` plus concurrent
approved M7 work. Owner: composition, delegated T007 physical custody slice.
Requirements: FR-BUDGET-001..006, M7-A02/A09. Binding and inherited descriptor
contracts: CTR-REG-011 1.0.0. No public contract or schema version changed.

## Change and boundary

`composition/billing_env_authorization.py` now provides
`OpenAIEnvAuthorizationV1` and `OllamaUsageEnvAuthorizationV1`, alongside the
unchanged Anthropic grant. Each constructor accepts the existing binding ID,
account ID, inherited account lock and inherited credential-file capability.
The provider namespace is fixed in each implementation. Authorization accepts
only its exact A02 OpenAI Costs or A03 Ollama Usage sink type. Ollama usage uses
the existing Ollama credential namespace; it creates no second credential.

Both new grants preserve the existing validation sequence: validate physical
capabilities at construction; validate again before reading; bounded stream
selection; verify consumed file size and both physical capabilities again;
apply to the exact sink; wipe the mutable token and stream buffers. Exceptions
become a provider-specific closed unavailable code, with TimeoutError preserved
for the supervised worker deadline. No caller-selected URL, provider string or
arbitrary callback is an authorization parameter. Only the existing bounded
chunk reader is shared; Anthropic authorization behavior remains unchanged.

This is physical custody, not registry authority. Root must still resolve the
current binding/generation, acquire the real lock, admit the source, and fence
binding, scope and M04 run generation at commit. Neither construction nor a
stored credential proves provider access or enables monitoring.

## Red and Green

The new test first created actual temporary registry metadata, pending binding
records and empty owner-private files through the real custody path. It then
failed because the two grant/error types were absent: **12 failed in 8.87s**.
The combined preimplementation run was **12 failed, 6 passed in 12.73s**; the six
existing Anthropic cases remained passing. This is missing-implementation Red,
not evidence of a live provider or credential-bearing behavioral failure.

After adding the two concrete implementations: **18 passed in 12.76s**. Each
new provider exercises an actual empty file, replaced file, replaced account
lock, expired file lease, expired account lease and concrete wrong-provider
sink. Every case returns its closed failure, leaves the HTTP connection
unconnected with no buffered header, leaves sink completion unavailable, and
preserves the persisted pending binding and zero-byte file. No mock, fake sink,
credential contents, provider response or seeded telemetry was used.

```sh
/home/dev/Nextcloud/Code/AI/AgentMonitor/backend/.venv/bin/python -m pytest -c backend/pyproject.toml --import-mode=importlib -q --tb=short -p no:cacheprovider backend/tests/registry/test_billing_env_authorization.py backend/tests/registry/test_billing_provider_grants.py
```

Scoped Ruff check and format check passed with `--config backend/pyproject.toml`
for the three changed Python files. Strict mypy passed the composition file with
the same backend configuration, `MYPYPATH=backend/src`,
`--explicit-package-bases --follow-imports=silent`. Scoped `git diff --check`
passed. No production refactor followed Green.

## Changed files and residual verification

- `backend/src/agentmonitor/composition/billing_env_authorization.py`
- `backend/tests/registry/test_billing_env_authorization.py`: existing isolated
  metadata/empty-file helper now supports the three providers; default remains
  Claude. Ollama uses its existing binding path without separate billing metadata.
- `backend/tests/registry/test_billing_provider_grants.py`
- This evidence file.

No owner runtime, account configuration, managed credential file, provider
profile or secret was read or modified. Only temporary empty files and isolated
administrative metadata were created. No dependency/license, migration, service,
deployment or shared-contract change; no commit by this delegate.

Successful credential application, actual A02/A03 authenticated HTTP, real
provider mapping, worker lifecycle and commit fencing remain **Not Run** here.
Empty-file refusal cannot establish successful secret delivery or distinguish
every internal rejection branch. This evidence does not close T007, M7-A02/A09,
or the M7 exit gate.
