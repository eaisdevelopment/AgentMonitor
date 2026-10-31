# V1-M3 acceptance-scope correction — 2026-10-02

- Decision: **Approved** by the owner on 2026-10-02.
- Scope: V1-M3 exits on one owner-confirmed real Claude vertical.
- Runtime impact: none. No provider, profile, account, database, API, UI, or
  running-process state was read or changed for this correction.
- Contracts: runtime contracts remain V1. The milestone acceptance record moves
  from documentation schema `1.0.0` to `2.0.0` because its criterion set changes.

## Corrected M3 gates

| Gate | M3 outcome |
|---|---|
| `AC-M3-001` | Approved Claude/Linux/source tuple implements the M03 provider boundary. |
| `AC-M3-002` | One owner-confirmed Claude identity has a durable M02 account/profile/resource graph. |
| `AC-M3-003` | That account produces a genuine read-only Claude subscription quota observation. |
| `AC-M3-004` | Its real quota run commits idempotently through M04 into M05 history and provenance. |
| `AC-M3-005` | A real Linux Claude process/session is linked to its M04 run and persisted through the M06 durable receipt/observation path for the same account using metadata only. |
| `AC-M3-006` | A revision-bound M3 technical run proves the authenticated API, generated client, and built browser rendered that account's real quota, runtime, history, and provenance. |
| `AC-M3-007` | A safe current-revision canonical gate passes every required lane, retains unavailable states, records owner interaction, and disposes historical Red-first gaps explicitly. |

The existing M3 evidence supports gates 1–6. Gate 7 remains Blocked because
the post-M4 owner database cannot safely run the historical M3 command, the
current dashboard needs a successor browser witness, and the historical M3
Red-first gap still needs the owner's explicit disposition.

## Later milestone ownership

| Outcome | Owner |
|---|---|
| Six intended Claude accounts, organizations, fleet, alerts, and Claude operations | V1-M4 |
| Codex identities, subscription capacity, and process trees | V1-M5 |
| Ollama local/cloud identities, resources, and process trees | V1-M6 |
| Anthropic, OpenAI, and supported Ollama API budgets | V1-M7 |
| Complete cross-provider matrices, dashboard, deployment/recovery, natural-time scenarios, universal controls, and final release | V1-M8 |

The release-wide `AC-V1-*`, `AC-LIVE-*`, `AC-UI-*`, `AC-PROC-*`,
`AC-HIST-*`, `AC-OPS-*`, and `AC-TEST-*` definitions remain unchanged. M3
evidence may contribute to them but does not mark a complete release row Passed.

## Red / Green evidence

The focused documentation-validator test was first run against the old
schema. It failed because schema `2.0.0`, the new keys, and the seven scoped
criteria were rejected. After the versioned validator was implemented:

```text
python3 -m unittest tools.docs.test_check
Ran 16 tests in 0.992s
OK

backend/.venv/bin/ruff check tools/docs/check.py tools/docs/test_check.py
All checks passed!
```

The added tests accept the exact approved V2 criterion set and predecessor
chain, reject a later-provider criterion in M3, and reject a changed historical
predecessor. The old `1.0.0` record keeps its original criteria and results and
is retained with lifecycle `superseded`.

The hardened transition also pins the approved scope bytes, canonical
predecessor path/ID/bytes, and active overlay path independently of fields in
the new record. Schema `2.0.0` is deliberately unable to claim Passed; the safe
gate step must introduce a successor schema that binds a current-revision gate
receipt before M3 can close.

```text
python3 -m unittest tools.docs.test_check
Ran 22 tests
OK
```

In the acceptance JSON, a command's `skips` array records required top-level
gate lanes. The historical `AUTO-M3-EXIT` had no omitted required lane under
the corrected M3 scope, so its command row has an empty array. Its nested test
suite still reported ten optional skipped tests, and natural multi-provider,
multi-account, pagination, and stall scenarios remained Blocked or Not Run;
those outcomes stay visible in the cited historical evidence and cannot satisfy
`AC-M3-007`.

The first synchronized planning run then failed closed with the seven new IDs
missing from exact ownership. After assigning their milestone closure to
PLAN-INT, retaining every contract producer as a supporting plan, and rebinding
the snapshot and reviews, seven bounded `INT-M3-001..007` scenarios replace
broader fleet/release scenarios. The canonical gates reported:

```text
AUTO-DOCS-CHECK: PASSED (operational)
AUTO-PLAN-CHECK: PASSED (operational)
AUTO-QUALITY: PASSED (operational)
```

## Impact

- Security/privacy: documentation metadata only; no account identity, secret,
  prompt, response, source content, provider payload, or environment value.
- Migration: acceptance-record documentation schema only; no data migration.
- Dependencies/licenses: none.
- Follow-up: implement and run the read-only successor M3 gate, then record the
  owner countersignature and historical TDD disposition before accepting M3.
