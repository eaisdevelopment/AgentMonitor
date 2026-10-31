# Change plan: typed durable M4 event delivery

- Status: **Approved for shared V1 contracts and module-owned delivery adapters**.
- Version: `1.0.0`; root integration review: 2026-09-29.
- Authority: existing owner-authorized full M4 implementation objective.
- Requirements: `FR-ALERT-001..005`, `NFR-DATA-001`, `NFR-RES-001`.
- Acceptance: `AC-ALERT-001/002`, `AC-HIST-002`, `AC-TEST-001/002`.
- Contracts: `CTR-EVT-001`, supporting `CTR-COMMON-006` and the existing
  `CTR-EVT-TOPOLOGY-001` module-owned outbox convention.

## Scope and ownership

Publish the exact typed event, batch and read/ack protocols proposed in section
4 of the approved M4 alerting packet. Root owns the shared contracts and
composition dispatcher. Each producer owns its SQL, payload decoder and
acknowledgement adapter. M07 owns its atomic receipt, checkpoint, alert,
history and outbox transaction. No central business tables or cross-module
SQL is authorized. Existing commit notices retain their original meaning;
they trigger typed current queries and never independently prove recovery.

## Guarantees and verification

Events carry immutable typed payloads, a positive schema major/stream sequence,
a bounded stream key and canonical SHA-256 payload digest. Batches contain at
most 200 actual events. Consumer delivery acknowledgements require the committed
receipt identity and matching payload digest. Crash before acknowledgement
redelivers to an idempotent consumer receipt. Producer generation and explicit
current inverse evidence govern lifecycle ordering, never run target generation.

Pure contract tests fail before publication and then verify bounded immutable
records. Real module SQLite tests and real event dispatch/restart tests remain
required for delivery claims. Constructed pure records are not provider data.
There is no new dependency, default-profile write, credential access, running
agent mutation or public API break. Existing producer schemas already own
outbox/delivery tables; any extra state requires an approved additive migration.
Rollback stops the new dispatcher while preserving durable rows and receipts.
