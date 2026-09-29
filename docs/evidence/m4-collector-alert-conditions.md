# M04 collector condition increment evidence

- Date: 2026-09-29
- Scope: ST-ALERT-001 producer contribution only; FR-COL-003/005/006/008, FR-ALERT-003/004, NFR-DATA-001, NFR-RES-001, NFR-SEC-001, NFR-PRIV-001; AC-ALERT-003 and AC-V1-003/005/007/008 contribution.
- Contracts: additive CTR-COL-007 V1 and CTR-COL-004 optional failure policy; CTR-PROV-004, CTR-COMMON-006/007 and CTR-EVT-001 consumed without a breaking change.
- Plan: `docs/plans/integration/m4-collector-alert-condition-change.md` v0.2.0, approved by root under full M4 authority.

## Red and Green

The focused pure/empty SQLite tests first failed 13 times because the M04 condition domain and repository modules were absent. Command:

```sh
backend/.venv/bin/python -m pytest backend/tests/collection_control/test_collector_alert_conditions.py backend/tests/integration/collection_control/test_alert_condition_queries.py -q
```

After implementation, the same command passed 13 tests on real file-backed migrated SQLite for the empty current/read/refresh boundary and constructed immutable inputs only for the pure classifier. The focused actual SQLite test does not seed business or provider rows. The existing M04 integration suite passed 20 tests and skipped 5; those skips are not live evidence. Ruff and mypy passed on the changed M04 source.

Root published v1_0706 from the staged candidate with SHA256 `2f5210db90076967c373f9d6b42017b198f0a986e846414be6bcdcf2a4fe5987`, catalog 1.7.6 and head v1_0706. Root's fresh actual Alembic DDL/integrity check passed and produced fingerprint `3b3bf7db294670c5ff38c7d797de46119e645c07c06224c4fa09789861c230e4`. This verifies schema creation, not nonempty condition/event behavior.

## Current boundary and remaining evidence

The producer reads actual M04 schedule, run, reference and projection tables only. A named internal refresh writes one target's current condition and typed event in one bounded SQLite transaction. The current query is read-only; missing projection, source version mismatch or expired unevaluated current data is partial, never a fabricated healthy inverse. The last fully succeeded committed run determines collection freshness. Provider retry advice is persisted as nullable run metadata; it does not by itself represent an applied schedule deferral.

Actual nonempty provider-produced history, source-version transition, expiry generation, typed event replay/ack conflict and M07 end-to-end delivery are **Not Run** by this M04 role. Root owns the eligible pipeline resource, consumer receipt, service composition and the full M4 completion gate. No claim of nonempty live correctness or full ST-ALERT-001 acceptance follows from this increment.

## Impact

Security/privacy: no prompts, provider values, identity labels, profile paths or credentials; only opaque IDs, closed condition states, timestamps and safe codes cross the contract. Direct SQLite writer is M04-private, validates file identity before/after, uses an allowlist and a two-second local lock/VM budget, and closes on every exit. The budget is not a universal OS stall bound.

Migration: additive v1_0706 M04 projection, nullable run outcome, nullable paired delivery proof with producer-owned triggers. Legacy unknowns are not backfilled. No downgrade or new dependency. Documentation: this evidence, the focused plan and M04 module guide. Full M4 exit remains red until root's real integration and canonical gate pass.
