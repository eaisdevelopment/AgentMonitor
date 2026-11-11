# M7 bounded managed-entry stream evidence

- Evidence ID: M7-STREAM-2026-11-11; delegated credential adapter implementer.
- Authority: approved M7 T002/T006, M7-A01; focused execution plan 1.1.0 and
  [implementation authority](m7-implementation-authority-2026-11-11.md).
- Requirements: FR-BUDGET-001, FR-AUTH-004, NFR-SEC-001; acceptance contributions
  AC-V1-007, AC-TEST-001/002. No full criterion or milestone acceptance claim.
- Base: `032a43f188d0c044f4e67f3adadea5d5e5a39707`, `m7-api-budgets` worktree.
- Contracts: no published DTO/port, migration, policy or capability change.

## Interface and behavior

`adapters/credential_env/stream.py` exports the existing function shape:

```python
ENV_STREAM_CHUNK_BYTES = 256

def read_credential_value_stream(
    chunks: Iterable[bytes | bytearray], name: bytes
) -> bytearray: ...
```

Names are validated by the shared formatter's `parse_managed_entry_name`, which
recognizes only the three managed provider namespaces. Runtime callers derive the
name from the persisted provider/binding via `credential_variable_name`; arbitrary
owner-selected environment names are not accepted by the parser.

The existing parser state machine now has neutral ownership. It reads at most
256 bytes per supplied chunk and 65,536 bytes overall, including bytes after the
selected entry. Encoded target values are bounded at 5,464 bytes and use the
existing canonical decoder with a 4,096-byte decoded limit. Only the exact named
entry is selected; unrelated values and long unrelated names are skipped without
assembling their lines or decoding their contents. Duplicates, malformed selected
lines, noncanonical encoding, missing targets and oversized input fail closed.
LF, CRLF and a final line without newline retain existing behavior.

The parser's owned encoded/selected bytearrays are cleared in `finally` on success
and failure. Caller-owned input chunks are not modified. The returned bytearray
belongs to the authorization caller, which must clear it after use; this is not
a claim of complete Python heap erasure or immutable-temporary erasure.

The existing Ollama module is a strict wrapper: it validates the original Ollama
name regex before consuming input, delegates to the shared parser and preserves
the `ollama_env_*` error vocabulary and chunk constant. It still rejects both
Anthropic and OpenAI names. No file authority, inherited lock/file capability,
provider source admission, transport, runtime reader or provider capability was
broadened by this increment.

## Red, Green and refactor

Before production edits:

```text
/home/dev/Nextcloud/Code/AI/AgentMonitor/backend/.venv/bin/pytest -q backend/tests/registry/test_billing_env_stream.py
```

**1 failed, 2 passed**, with
`AssertionError: provider-neutral bounded credential stream is missing`.
This is explicitly a missing owned-capability Red. The two legacy namespace
rejection cases already passed; existing rejection was correct and was retained.
No fake baseline, empty implementation shell or deliberate production defect was
introduced. Behavioral stream cases were then written before the implementation.

Initial new/legacy stream Green: **60 passed in 0.09s**. Refactored the historical
availability assertion into ordinary static production imports. Final regression:

```text
/home/dev/Nextcloud/Code/AI/AgentMonitor/backend/.venv/bin/pytest -q backend/tests/registry/test_billing_env_stream.py backend/tests/registry/test_billing_env_format.py backend/tests/contracts/test_ollama_env_stream.py backend/tests/contracts/test_ollama_env_format.py backend/tests/contracts/test_ollama_env_import_policy.py backend/tests/adapters/providers/ollama/test_env_authorization_policy.py backend/tests/adapters/providers/ollama/test_env_capability_policy.py backend/tests/adapters/providers/ollama/test_env_helper_process_policy.py
```

**113 passed in 0.33s**, exit 0, no skips. New tests cover all three namespaces;
one/seven/256-byte chunks; LF/CRLF/EOF boundaries; canonical and maximum-length
values; unrelated malformed foreign values; duplicate/missing/noncanonical target
lines; exact/oversized file bounds; invalid chunk types; malformed names; mutable
caller ownership; and iterator failure after a selected value without partial
success. Buffer clearing was also reviewed in the unchanged `finally` structure;
no live memory/secret-erasure experiment was performed.

Ruff check/format and scoped diff checks passed. From `backend/`, strict typing:

```text
MYPYPATH=src /home/dev/Nextcloud/Code/AI/AgentMonitor/backend/.venv/bin/mypy --strict --explicit-package-bases src/agentmonitor/adapters/credential_env/stream.py src/agentmonitor/adapters/providers/ollama/cloud_balance/env_stream.py tests/registry/test_billing_env_stream.py
```

Result: `Success: no issues found in 3 source files`, exit 0.

## Compatibility and limitations

Before and after extraction, the actual Ollama probe fingerprint remained
`047d2bf64f70eae87a54223cb6f1aa3bec240c84ae99c0cc2155db8342a5110f`.
The unchanged authorization policy file SHA256 remained
`b483b865b3cc760cb8f1a631647de0db8a1af34502a8142ad386b06c79bf96c9`.

Files in this handoff:

- `backend/src/agentmonitor/adapters/credential_env/stream.py`
- `backend/src/agentmonitor/adapters/providers/ollama/cloud_balance/env_stream.py`
- `backend/tests/registry/test_billing_env_stream.py`
- `docs/evidence/m7-billing-env-stream-2026-11-11.md`

No dependencies/license changes, credentials, owner files, accounts, profiles,
services, network or provider operations were involved. Constructed byte inputs
are pure and never cross I/O. No mock, fake boundary, seeded credential file or
provider recording was used.

Actual inherited-file/runtime authorization and the first provider billing read
remain composition/provider work and **Not Run** here. Runtime composition must
retain existing account/file guard checks, source-specific authorization admission,
read deadlines and caller buffer clearing. This parser increment is not evidence
of stored credentials, verified access, T002/T006 completion or M7 completion.
