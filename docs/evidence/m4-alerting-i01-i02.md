# M4 M07 alerting evidence — contracts, pure policy and rule persistence

- Evidence ID: `M4-M07-I01-I02-2026-09-29`.
- Status: **Intermediate implementation evidence**; full M07/M4 acceptance is not claimed.
- Approved packet: [M4 alerting change](../plans/integration/m4-alerting-change.md), version `0.2.0`, I01/I02 and the recorded §17/§18 I03/I04 increments; root additionally approved the forward configuration guards below on 2026-09-29.
- Requirements: `FR-ALERT-001..006`, `FR-HIST-001..003`; supporting `NFR-DATA-001`.
- Acceptance criteria: `AC-ALERT-001..003`, `AC-HIST-002`; evidence here covers their pure policy and real rule-storage portions only.
- Contracts: additive `CTR-ALERT-001..005` V1; consumes published `CTR-REG-005/009`, `CTR-CAP-004/005` and `CTR-EVT-001` V1. Later addenda record the actual I03 producer read and I04 alert actions.
- Worktree: current uncommitted checkout. Recorder: delegated M07 implementation agent, 2026-09-29.

## Delivered scope and real boundaries

Published immutable rule, alert, lifecycle, history, notification, command and query DTOs have closed enumerations, aware UTC validation and explicit owning-contract metadata. Pure policies cover whole-rule precedence, disabled overrides, inclusive exact 3000/1500 basis-point defaults, stable condition identity, ordered source generations, explicit recovery, acknowledgement/read/snooze distinctions, notification ordering and the strict 365-day terminal-history cutoff.

Real file-backed SQLite rule commands use the actual production Alembic chain, actual local administrator bootstrap and actual organization CRUD. Transactions atomically commit the rule, immutable revision, command receipt, reevaluation jobs and owned outbox. Reopen returns the original receipt revision even after later edits. Concurrent identical commands commit once. Moving a rule schedules both its former and new scope. Rule storage contains administrator configuration; these tests do not insert provider observations or alerts.

At the I01/I02 handoff, actual alert consumption, alert projection persistence/query, durable user alert commands, deadline execution, history deletion, HTTP/UI and provider-condition acceptance were **Not Run**. The later I03/I04 addenda below supersede that implementation status only for their explicitly tested paths. Account/provider resolution uses published registry queries; a provider with no eligible member remains unavailable until a provider-definition confirmation port exists.

## Red/Green ledger

| Increment | Actual sanitized Red | Green / limit |
|---|---|---|
| Contract declaration | Collection error: `ModuleNotFoundError` for `alerting_v1` | 11 passed; declaration absence evidence, not a behavioral assertion Red |
| Pure policy declaration | Collection error: `ModuleNotFoundError` for `modules.alerting` | Combined pure suite: 38 passed; pure constructed inputs establish policy only |
| Three alert migrations | 1 failed: `A-DB01: three production alert revisions are absent` | Root admitted the catalog; actual fresh chain plus capacity schema checks: 5 passed |
| Rule repository declaration | Collection error: repository module absent | Declaration absence evidence only |
| Actual rule mutation | 2 failed, 2 passed: generated opaque identifiers beginning with `-`/`_` were rejected; duplicate active scope returned the generic unavailable error | Corrections followed by full owned suite: 43 passed in 2.59 s |
| Moving an override | 1 failed, 4 deselected: the former global scope was missing from actual reevaluation jobs | Corrected one atomic transaction; full owned suite: 44 passed in 3.06 s |
| Mandatory stored configuration fields | 1 failed, 5 deselected in 0.75 s: `DID NOT RAISE IntegrityError` on incomplete actual rule configuration | Admitted forward `v1_0705`; six actual current/history/schema/threshold rejection cases pass |
| Configuration upgrade preservation/preflight | New tests target real administrator-created rules and immutable revisions at prior head `v1_0704` | Actual upgrade preserves exact prior revisions and command receipts; invalid existing current/history rows prevent guard installation and preserve head/data |

A transient syntax error, wrong type-check import path and concurrent unregistered migration-catalog state were setup failures and are excluded from behavioral Red evidence. The effective-rule application query was added after the registry seam became available without a separate recorded behavioral Red; universal TDD completion is not claimed.

Commands from repository root:

```bash
backend/.venv/bin/python -m pytest -q --tb=short backend/tests/alerting
backend/.venv/bin/python -m pytest -q --tb=short backend/tests/alerting/persistence/test_rule_crud.py -k moving_override
backend/.venv/bin/python -m pytest -q --tb=short backend/tests/alerting/persistence/test_rule_crud.py -k incomplete_threshold
backend/.venv/bin/ruff check --config backend/pyproject.toml backend/src/agentmonitor/contracts/alerting_v1.py backend/src/agentmonitor/modules/alerting backend/src/agentmonitor/adapters/persistence/alerting backend/tests/alerting
MYPYPATH=backend/src backend/.venv/bin/mypy --config-file backend/pyproject.toml --explicit-package-bases backend/src/agentmonitor/contracts/alerting_v1.py backend/src/agentmonitor/modules/alerting backend/src/agentmonitor/adapters/persistence/alerting backend/tests/alerting
```

After root admitted catalog `1.7.5`/head `v1_0705`, the full owned suite passed: **53 passed in 8.55 s**, including actual prior-head upgrades and NULL-field constraints. Strict owned mypy passed for 14 source files. Ruff uses the canonical explicit backend configuration. These module commands do not replace root-owned `AUTO-TEST`, `AUTO-QUALITY`, `AUTO-DOCS-CHECK` or `AUTO-M4-EXIT`.

## Migration and compatibility

The pinned `v1_0700` through `v1_0702` allocate twelve M07 tables, local foreign keys, bounded indexes and atomic-workflow storage without builtin rule rows or telemetry. Root integrates these with M05 `v1_0703/0704` and owns catalog digests, head, exact schema fingerprints and installation upgrades.

The actual incomplete-document Red exposed SQLite CHECK/NULL acceptance. Root approved additive `v1_0705`, parent `v1_0704`, with four owned BEFORE INSERT/UPDATE guards on current rules and rule revisions. `CASE` protects malformed JSON evaluation and explicit `COALESCE(...,0)=1` rejects absent schema/threshold fields. Closed configuration keys, integer types and threshold bounds are validated. Existing invalid data is rejected before installing guards, using a fixed safe code; there is no repair or backfill. Existing installations require offline migration and a verified backup. Pinned older revisions remain unchanged. This agent does not upgrade the owner installation or claim backup/restore acceptance.

## Security, privacy, licensing and documentation

No dependency, provider authentication operation, provider file write, process-control operation or external delivery surface was added. Existing approved SQLAlchemy/Alembic/Argon2 packages are reused. M07 SQL is restricted to its owned `alert_*` tables. Provider/OS/framework code is absent from the pure domain. Root owns browser authorization (`read:alerts` queries, `write:alerts` commands), API bindings and generated client integration.

Public evidence contains only technical opaque references, bounded reason codes, configuration versions, canonical quantities and UTC times. No account email, project path, provider content, arbitrary environment, credential or raw provider output is included. Test administrator passwords are generated in memory and never displayed. No mock, fake, stub, emulator, provider-response replay, seeded telemetry, fabricated alert or hardcoded pass was used. Constructed signal inputs occur only in pure tests without I/O.

Changed paths: `contracts/alerting_v1.py`, `modules/alerting/{domain,application}/`, `adapters/persistence/alerting/sqlite/`, `tests/alerting/{pure,persistence}/`, allocated M07 migrations, and this record. Root synchronizes the contract catalog, module routing, API/OpenAPI/client, operational runbook and canonical gates.

## Remaining integration

1. Root published reviewed `v1_0705` with the matching exact trigger inventory/catalog; actual configuration Red, upgrade preservation/preflight and full owned suite are Green. Installation migration/backup remains root-owned and unexecuted by this agent.
2. Freeze producer condition-stream identity and consumer receipt/checkpoint seams before durable consumption. Use actual producer current facts and their committed generations; a commit notice or collection success cannot prove recovery.
3. Execute real source-to-alert persistence, HTTP and built-browser workflows, including exact receipt acknowledgement after consumer commit. Naturally rare recovery/auth/stall conditions and aged retention stay Not Run until genuinely observed.
4. Pass the complete canonical M4 gate before any full milestone claim.

## I03 capacity condition consumer addendum

Root approved the exact I03 packet in [§17 of the focused plan](../plans/integration/m4-alerting-change.md). `CTR-ALERT-002` adds the typed `ConsumeCapacityAlertEventV1` port; M07 consumes `CTR-CAP-004/005`, `CTR-REG-005/009` and `CTR-EVT-001` through published DTO/call signatures. No new dependency or migration was added by I03. Root's separately allocated M04 `v1_0706` now follows M07 `v1_0705`; old-head rule tests remain genuine.

Red: `backend/.venv/bin/python -m pytest -q --tb=short backend/tests/alerting/pure/test_capacity_mapper.py` gave 15 expected missing-mapper assertion failures (0.30 s) after test input precision was corrected to a valid source enum. Green: 53 pure cases passed (0.32 s), proving exact fraction thresholds, explicit exhaustion/inverse, non-current non-evaluation, account/provider/eligibility guards, source generation, observation IDs, precision and closed producer reason preservation. Constructed pure facts do not claim a real provider state.

Genuine boundary Red: with `AGENTMONITOR_TEST_DATA_ROOT` selecting the owner's existing AgentMonitor database, the read-only integration test found an actual M05 committed event, active M02 resource/account and current quota fact through published ports, then failed only `A-LIVE01: approved capacity-alert consumer is absent` (1 failed, 0.42 s). No owner data was written. Green: the same actual selected event/current facts produced two source-derived open alerts in a private real migrated SQLite installation after a local admin created an allowed 10000/10000 basis-point global rule. The test verified exact source event and observation lineage, typed outbox payload, immutable transition rows, independent checkpoints, FK integrity and identical receipt replay after reopening; **2 passed in 1.51 s**. The initial outbox count assertion omitted the legitimate rule-change row and was corrected; it is not a behavioral Red.

The I03 transaction writes receipt, per-condition generation checkpoints, alert projections, immutable history/evidence and `AlertOpenedV1`/`AlertStateChangedV1` outbox payloads under `BEGIN IMMEDIATE`. Admission rechecks actual current facts, account/resource membership and effective rule before writing. Same event/digest replays its receipt; a mismatched digest is rejected by the code path. Producer acknowledgement occurs in `DeliverCapacityAlertEventV1` only after commit, but an actual installation acknowledgement is **Not Run** in this packet. The isolated test uses a separate M07 database for derived alerts while reading the owner source database, so it cannot prove the same-file cross-module writer lock; root composition must verify that boundary against the actual installation. Naturally observed newer recovery, source conflict and deadline expiry remain Not Run. No fabricated telemetry, event, generation, provider output or account was inserted.

After the I03 files, the full owned suite under root's reviewed head `v1_0706` passed: **68 passed in 8.01 s**. It includes the prior `v1_0704 → v1_0705` guard upgrade and current 0706 fresh-chain path. API, UI, installation backup/migration/ack and canonical `AUTO-M4-EXIT` remain root-owned and unpassed.

## I04 durable alert action and read addendum

Root approved I04 in [§18 of the focused plan](../plans/integration/m4-alerting-change.md). The actual I03 source-derived alert in an isolated migrated SQLite file was the input to the I04 action and query test. No alert projection or provider telemetry was seeded. The actual owner AgentMonitor database was queried through published M02/M05 read ports only.

Red: the real integration test reached its new read query after the prior action assertions and failed `AttributeError: 'SqliteAlertActionRepositoryV1' object has no attribute 'list_alerts'` (1 failed, 2 deselected, 2.04 s). Earlier module-absence Reds for the command and action repository are recorded in the implementation log; module absence alone does not prove behavioral TDD. Green: real integration **3 passed in 3.23 s** at root's pinned `v1_0707` catalog; pure M07 **68 passed in 9.53 s**. Ruff passed all owned code/tests and strict mypy passed **23 source files**. The real I04 test verifies acknowledgement CAS and replay, conflicting command rejection, snooze and durable deadline cancellation, unsnooze, mark-read, immutable transition rows, alert and notification keyset pagination, history sequence pagination, account-scope filtering, whole-set counts independent of page limit and SQLite foreign-key integrity.

`SqliteAlertActionRepositoryV1` opens an actual SQLite connection per command; one `BEGIN IMMEDIATE` transaction commits the projection, immutable history, typed outbox, deadline and command receipt. Identical command-ID/digest replay returns the original result, while changed digest and stale projection/notification versions fail closed. The read ports use read-only connections, bounded `limit+1` pages and bound SQL values; GET does not mark read. The public immutable ports remain `GetAlertV1`, `ListAlertsV1`, `ListAlertHistoryV1`, `ListDashboardNotificationsV1`, `GetDashboardNotificationCountsV1`, `AcknowledgeAlertV1`, `SnoozeAlertV1`, `UnsnoozeAlertV1` and `MarkAlertReadV1` on `CTR-ALERT-002/005` V1. Root owns browser IAM and P01/P02 binding.

These tests do not demonstrate actual same-installation producer acknowledgement, owner dashboard HTTP/browser use, naturally occurring recovery or due snooze execution, 365-day deletion, owner installation migration or backup/restore. Those and `AUTO-M4-EXIT` remain required. No dependency/license change, provider profile write or external alert delivery was introduced. No emails, paths, content or credentials enter M07 alert evidence.

## Installed owner alert verification — 2026-09-29

Following root's successful `v1_0603→v1_0707` owner installation upgrade and final service restart, `tools/ui/verify_m4_alerts.mjs` passed against the real owner dashboard. It verified **1 genuine source-derived alert and its history**. This later result supersedes the earlier owner-browser Not Run status for that bounded display check. It does not establish naturally occurring recovery, due snooze execution, aged retention or full `AUTO-M4-EXIT` acceptance.
