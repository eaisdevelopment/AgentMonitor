# M7 fixed billing worker supervisor

Status: partial T007 composition implementation; not installed collection or M7
closure. Authority: approved M7 focused plan 1.1.0/T007, root's explicit bounded
composition ownership assignment. Requirements FR-BUDGET-001 and M7-A09. Base
revision supplied for the assignment: `ad7a04e`.

## Boundary and compatibility

`BillingWorkerSupervisorV1(data_root, *, credential_env_file=None)` reuses the
existing Ollama transient-unit supervisor lifecycle through a small fixed
subclass. It has no caller-selected executable, module, command or service name.
Its fixed entrypoint is `agentmonitor.composition.billing_worker`, implemented
separately by root. Billing uses `agentmonitor-billing-worker-<root hash>-<token>`,
`.billing-worker.lock` (also the durable unit marker), description
`AgentMonitor billing worker <token>` and `RuntimeMaxSec=120s`.

The shared supervisor now takes these identities from bounded class constants.
Original Ollama defaults remain its exact module, prefix, description, lock,
30-second runtime, and historical marker recovery. Billing refuses that legacy
generic-prefix fallback. Marker size is derived from the fixed prefix; it is
still bounded. Poll count scales with the selected fixed runtime, while systemd
enforces the hard unit lifetime. Existing start-authority pipe, exact argv/unit
checks, cgroup cleanup, quarantine and inode/lock checks are reused unchanged.

No credential values are received by the supervisor. An optional selected `.env`
path retains the existing validation and goes only to the fixed child entrypoint.
No owner key/account/default profile was opened or modified for this work. Root
owns source grants, account selection, actual one-job collection, generation
fences, result persistence and the billing CLI. This increment adds no public
versioned contract, migration, dependency, provider behavior or UI change.

## Red and verification

Initial collection failed because the new supervisor module did not yet exist;
this is feature-absence evidence, not behavioral isolation proof. After adding
the fixed subclass, the unchanged base produced a meaningful **2 failed in
0.10s**: it created the Ollama lock instead of the billing lock, and an actual
Ollama lock incorrectly made billing unavailable. Real isolated files/flocks
were used; no substituted lock or mocked OS behavior.

After the minimal constants refactor, the two billing lock cases and three real
Ollama smoke cases passed: **5 passed, 16 deselected in 1.44s**. The broader
existing supervisor suite then passed **20 passed, 1 deselected in 12.08s**:

```text
PYTHONPATH=backend/src:. /home/dev/Nextcloud/Code/AI/AgentMonitor/backend/.venv/bin/python -m pytest -q backend/tests/adapters/providers/ollama/test_cloud_worker_boundary.py backend/tests/integration/collection_control/test_billing_worker_supervisor.py -k 'not anonymous_provider_helper'
```

The deliberately excluded existing anonymous-provider probe makes a real
provider request and was outside this assignment. It is **Not Run**, not Passed.
The selected regression uses real disposable systemd units, actual empty
resources and the production Ollama entrypoint. It covers cancellation, revoked
late starts, durable recovery, same/different-root serialization, legacy marker
recovery, foreign/oversized markers, lookalike-unit refusal and replaced locks.
It does not prove billing provider collection.

Scoped backend-config Ruff passed. Strict mypy with `--explicit-package-bases
--follow-imports=silent` passed the two production files. No alternate type/test
configuration or dependency was added.

Two additional actual billing CLI/unit tests were added after that regression:
missing-database refusal and exact fixed 120-second unit identity with authority
withheld then revoked. These are awaiting root's actual billing entrypoint and
are **Not Run** at this evidence stage. No fabricated unit-property dictionaries,
fake entrypoint, credential, provider payload or alternate worker was supplied
to make them pass.

## Files and remaining evidence

- `backend/src/agentmonitor/composition/ollama_cloud_worker.py`
- `backend/src/agentmonitor/composition/billing_worker_supervisor.py`
- `backend/tests/integration/collection_control/test_billing_worker_supervisor.py`
- This evidence document.

Required next evidence: run the two real billing entrypoint cases once available;
then root integrates actual admission/grants and collection. Authenticated
provider work, hung authenticated child cutoff, recovery of a real in-flight
billing job, installed scheduling/continuity, and canonical full M7 tests remain
**Not Run** for this increment. No commit or deployment was performed.
