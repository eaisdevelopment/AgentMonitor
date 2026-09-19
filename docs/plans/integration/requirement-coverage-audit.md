# V1 requirement and acceptance coverage audit

- Audit ID: `REQ-COV-2026-09-18-01`
- Status: **Complete as a read-only planning audit; findings are open**
- Audit scope: the 20 artifacts in `planning-catalog.toml`, the current contract
  register, all Approved/Discovery/Deferred requirement IDs, and every V1
  acceptance criterion
- Evidence date: 2026-09-18
- Evidence state: plans are Draft; contracts are Concept/Proposed; implementation
  and all planned test/live scenarios are `Not Run`
- Artifact owner: integration steward

## 1. Outcome

All 140 non-deferred specification IDs have at least one row in a planning
artifact, but the planning set is **not synchronized and must not be called
complete or implementation-ready**. The exact-primary assignments below resolve
the current many-owner shorthand for audit purposes only; they must be adopted
or corrected in the canonical traceability and CS-1 review.

The release-blocking findings are:

1. `AUTO-PLAN-CHECK` is red because
   `docs/plans/integration/cs1-full-plan-synchronization.md` is absent.
2. PLAN-INT references 61 scenario IDs that it never defines and also uses the
   undefined wildcard `INT-E2E-*`.
3. PLAN-INT and the baseline traceability document still assign several families
   to multiple primary owners (`M02 + adapters`, `M05/M06/M07/M08`, `all`) rather
   than exactly one accountable plan per exact ID.
4. PLAN-P01 puts deferred `FR-ALERT-007` and `FR-ALERT-008` inside its V1 supported
   workflow and test ranges, contradicting its own out-of-scope statement and
   PLAN-INT's deferred guard.
5. `FR-SAFE-001` lacks the promised defined `INT-SAFE-*` positive allowed-action
   inventory. P01 has real route tests, but its current trace row emphasizes
   privacy/absent-control checks rather than an exact allowed-action proof.
6. `AC-V1-006` cites undefined `INT-DOC-001..008`; `AC-V1-008` cites undefined
   `INT-TEST-001..008`. Other defined scenarios partly cover the intent, but the
   canonical references are invalid.
7. All 76 registered contracts are unapproved: 16 are `Proposed`, 38 are
   `Concept`, 21 are `Concept; blocked by M0`, and one is blocked by isolated-
   profile discovery. Zero are `Synchronized` or `Approved`.

No plan claims a live scenario Passed. The reviewed plans consistently prohibit
mocks, fakes, stubs, emulators, recordings/replays, demo accounts, seeded
telemetry, and placeholder provider values. This is a document audit, not proof
that future code or tests comply.

## 2. Audit method and status vocabulary

Sources of authority, in precedence order, are the repository `AGENTS.md`,
approved requirements and acceptance criteria, accepted ADRs, architecture and
engineering standards, and then Draft plans.

The audit enumerated 147 stable IDs:

- 94 Approved requirements, including all non-functional requirements;
- three Discovery-status V1 requirements;
- 43 mandatory V1 acceptance criteria;
- seven Deferred requirements.

Every non-deferred ID was checked for exactly one proposed primary plan, explicit
supporting plans, contract references, named planned scenarios, and a real
boundary suitable for the claim. Ranges were expanded during the audit; a family
heading or backlog entry alone did not count.

Status codes used below:

| Code | Meaning |
|---|---|
| `D-NR` | Draft exact planning chain exists; contracts are not approved and scenarios are Not Run. |
| `D0-NR` | Discovery-gated Draft chain exists; M0 and dependent scenarios are Not Run. |
| `B-NR` | Draft chain exists but its required real platform/provider condition is currently Blocked/Not Run. |
| `R-NR` | Planning reference or coverage defect must be repaired before synchronization. |
| `GATE-RED` | Exact plan exists, but its canonical executable lifecycle gate is red. |
| `X` | Deferred and guarded from V1. |
| `X-LEAK` | Deferred, but a V1 plan currently includes it in a supported/test range. |

`Primary` means accountable for planning and evidence closure. It does not move a
domain invariant or table away from the owner defined in `modules.md`.

## 3. Approved functional requirements

| ID | Primary | Supporting plans | Contracts | Planned scenarios and required evidence | Status |
|---|---|---|---|---|---|
| FR-ORG-001 | PLAN-M02 | P01, P02, DB, INT | CTR-REG-001, CTR-API-001, CTR-DB-002 | M02-PURE-001..004, M02-DB-001..006, M02-HTTP-001..003, M02-BROWSER-001; pure plus real SQLite/HTTP/browser | D-NR |
| FR-ORG-002 | PLAN-M02 | P01, P02, DB, INT | CTR-REG-001/002 | M02-PURE-005, M02-DB-007/008, M02-HTTP-004, M02-BROWSER-002; real constraint/workflow | D-NR |
| FR-ORG-003 | PLAN-M02 | M05, M06, M07, P01, P02, INT | CTR-REG-001/002/005/007, CTR-CAP-003 | M02-PURE-006, M02-DB-009, M02-HTTP-005, M02-ARCH-001 plus downstream aggregate scenarios | D-NR |
| FR-ACC-001 | PLAN-M02 | M0, M03, A01-A03, P01, P02, DB, INT | CTR-REG-002/006, CTR-PROV-005 | M02-PURE-007/008, M02-DB-010/011, M02-LIVE-001..003; real owner-confirmed accounts | D-NR |
| FR-ACC-002 | PLAN-M02 | P01, P02, DB, INT | CTR-REG-002/007 | M02-PURE-009, M02-DB-012/013, M02-HTTP-006, M02-BROWSER-003 | D-NR |
| FR-ACC-003 | PLAN-M02 | M04, M05, M06, P01, P02, DB | CTR-REG-002/007 | M02-PURE-010/011, M02-DB-014, M02-HTTP-007; history-preserving real DB/API | D-NR |
| FR-ACC-004 | PLAN-M02 | M0, M03, M05, A01-A03, P01, P02 | CTR-REG-002/003/005 | M02-PURE-012..014, M02-DB-015..018, M02-LIVE-004 | D-NR |
| FR-ACC-005 | PLAN-M02 | M0, M03, A01-A03, P01, P02 | CTR-REG-004/006, CTR-PROV-005 | M02-PURE-015/016, M02-DB-019/020, M02-HTTP-008, M02-LIVE-005; M0-approved real discovery | D-NR |
| FR-ACC-006 | PLAN-M02 | M0, M06, A01-A03, P01, P02 | CTR-REG-006, CTR-RUN-007 | M02-PURE-017..020, M02-DB-021/022, M02-HTTP-009, M02-BROWSER-004/005, M02-LIVE-006 | D-NR |
| FR-AUTH-001 | PLAN-M03 | M02, M04, M07, A01-A03, P01, P02, INT | CTR-PROV-006 | M03-PURE-021..024, M03-LIVE-006; pure vocabulary plus real provider observation | D-NR |
| FR-AUTH-002 | PLAN-M02 | M03, A01-A03, P01, P02, M01, INT | CTR-REG-003/006, CTR-PROV-007 | M02-PURE-021/022, M02-DB-023, M02-HTTP-010, M02-BROWSER-006, M02-LIVE-007 | D-NR |
| FR-AUTH-003 | PLAN-M02 | M03, A01-A03, DB, P01, P02, INT | CTR-REG-002/003/006/007, CTR-PROV-007 | M02-PURE-023, M02-DB-024, M02-LIVE-008; real transaction and live re-auth continuity | D-NR |
| FR-AUTH-004 | PLAN-M02 | M03, A01-A03, P01, security, INT | registry surface, CTR-PROV-001/007 | M02-ARCH-002, M02-SEC-001/002; schema/source/artifact scans | D-NR |
| FR-AUTH-005 | PLAN-M02 | M03, A01-A03, P01, security, INT | CTR-REG-003, CTR-PROV-007 | M02-PURE-021, M02-DB-023, M02-HTTP-010, M02-LIVE-009 plus INT-SEC-006 | D-NR |
| FR-QUOTA-001 | PLAN-M05 | M0, M03, M04, A01-A03, P01, P02, DB, INT | CTR-CAP-001 | M05-PURE-001..005, M05-DB-002..006, M05-LIVE-001..003; live authoritative reconciliation | D-NR |
| FR-QUOTA-002 | PLAN-M05 | M03, A01-A03, P01, P02, INT | CTR-CAP-001, CTR-PROV-008 | M05-PURE-006/007, M05-DB-007, M05-SEC-003, M05-LIVE-004 | D-NR |
| FR-QUOTA-003 | PLAN-M05 | M04, M07, P01, P02, INT | CTR-CAP-003 | M05-PURE-014..021, M05-DB-017..019, M05-LIVE-005 | D-NR |
| FR-QUOTA-004 | PLAN-M05 | M03, A01-A03, P01, P02, INT | CTR-COMMON-004, CTR-CAP-001/003 | M05-PURE-008..013, M05-DB-008/016, M05-HTTP-002, M05-BROWSER-001 | D-NR |
| FR-QUOTA-005 | PLAN-M05 | M07, P01, P02, INT | CTR-CAP-007 | M05-PURE-031..042, M05-DB-024..026, M05-HTTP-006, M05-LIVE-006 plus INT-BUD-010 | D-NR |
| FR-BUDGET-001 | PLAN-M05 | M0, M03, M04, A01-A03, P01, P02, DB, INT | CTR-CAP-002 | M05-DB-009..015, M05-LIVE-007..010; real configured billing accounts | D-NR |
| FR-BUDGET-002 | PLAN-M05 | A01-A03, P01, P02, INT | CTR-CAP-002/007 | M05-PURE-043..048, M05-DB-011/012, M05-HTTP-003, M05-LIVE-008/009 | D-NR |
| FR-BUDGET-003 | PLAN-M05 | M02, A01-A03, P01, P02, INT | CTR-CAP-002/006 | M05-PURE-049..052, M05-DB-013..015, M05-HTTP-004, M05-LIVE-010/011 | D-NR |
| FR-BUDGET-004 | PLAN-M05 | DB, P01, P02, M08, INT | CTR-COMMON-003, CTR-CAP-002 | M05-PURE-053..058, M05-DB-016, M05-HTTP-007, M05-SEC-004 plus INT-BUD-007 | D-NR |
| FR-BUDGET-005 | PLAN-M05 | M02, A01-A03, P01, P02, INT | CTR-CAP-001/002/003 | M05-PURE-027..030, M05-DB-022/023, M05-BROWSER-003 plus INT-BUD-009 | D-NR |
| FR-DISC-001 | PLAN-M06 | M0, A01-A04-LINUX, A04-MAC, P01, P02, INT | CTR-RUN-001/006 | M06-LNX-001, M06-LIVE-001..003; real Linux/provider processes | D-NR |
| FR-DISC-002 | PLAN-M06 | A04-LINUX, A04-MAC, P01, P02 | CTR-RUN-001/006 | M06-PURE-001..003, M06-LNX-002..006; real OS units/permissions | D-NR |
| FR-DISC-003 | PLAN-M06 | M0, A01-A04, P01, P02, security | CTR-RUN-002, CTR-PLAT-001 | M06-PURE-026/027, M06-SEC-001..004, M06-LIVE-004 | D-NR |
| FR-DISC-004 | PLAN-M06 | M0, M02, A01-A04, P01, P02 | CTR-RUN-007, CTR-REG-006 | M06-PURE-018..021, M06-DB-009, M06-UI-002, M06-LIVE-005 | D-NR |
| FR-DISC-005 | PLAN-M06 | M0, A01-A04, P01, P02, INT | CTR-RUN-003/006 | M06-PURE-004/005/014..017, M06-LNX-007, M06-LIVE-006 | D-NR |
| FR-DISC-006 | PLAN-M06 | M0, A01-A03, P01, P02 | CTR-RUN-002 | M06-PURE-016/024..027, M06-LIVE-004/007; field-by-field live capability evidence | D-NR |
| FR-DISC-007 | PLAN-M06 | A04-LINUX, A04-MAC, security, INT | CTR-RUN-006 | M06-SEC-001/002, M06-LNX-008; static and real negative proof | D-NR |
| FR-DISC-008 | PLAN-M06 | M03, A01-A04, P01 | CTR-RUN-002, CTR-COMMON-004 | M06-PURE-024, M06-DB-003, M06-LIVE-004 | D-NR |
| FR-STATE-001 | PLAN-M06 | A01-A03, M07, P01, P02 | CTR-RUN-002/004 | M06-PURE-006/007, M06-LIVE-008 | D-NR |
| FR-STATE-002 | PLAN-M06 | M0, A01-A03, P01, P02 | CTR-RUN-004 | M06-PURE-006..008, M06-API-003; real evidence completes claim | D-NR |
| FR-STATE-003 | PLAN-M06 | M07, P01, P02, DB, INT | CTR-RUN-005 | M06-PURE-009..013, M06-DB-010, M06-API-004; real observation window | D-NR |
| FR-STATE-004 | PLAN-M06 | A01-A03, M07, P01, P02, INT | CTR-RUN-005 | M06-PURE-010/011, M06-LIVE-008; natural real waiting state or Blocked | D-NR |
| FR-COL-001 | PLAN-M04 | M02, M03, A01-A03, DB, P01, P02, INT | collection policy/schedule, CTR-COL-001 | M04-PURE-001..005, M04-DB-002/003, M04-LIVE-001/002 | D-NR |
| FR-COL-002 | PLAN-M04 | M03, P01, P02, INT | CTR-COL-001 | M04-PURE-006/007, M04-DB-007..010, M04-HTTP-001..004, M04-LIVE-003/004 | D-NR |
| FR-COL-003 | PLAN-M04 | M03, A01-A03, M07, INT | CTR-COL-004, CTR-PROV-004 | M04-PURE-008..014, M04-DB-013/014, M04-LIVE-005..008 | D-NR |
| FR-COL-004 | PLAN-M04 | M03, M05, M06, M07, A01-A03, INT | CTR-COL-002/003, CTR-COMMON-004 | M04-PURE-015, M04-DB-015/016, M04-LIVE-009 | D-NR |
| FR-COL-005 | PLAN-M04 | M07, M08, P01, P02 | CTR-COL-002/004 | M04-PURE-016/017, M04-DB-011/012/017, M04-HTTP-005 | D-NR |
| FR-COL-006 | PLAN-M04 | M03, M05, M07, P01, P02 | CTR-COL-002/004/005 | M04-PURE-010..013/018, M04-DB-018, M04-HTTP-006, M04-LIVE-006/010 | D-NR |
| FR-COL-007 | PLAN-M04 | M0, M03, A01-A03, INT | CTR-PROV-002/003, dispatch admission | M04-PURE-019, M04-LIVE-011, M04-ARCH-002 | D-NR |
| FR-COL-008 | PLAN-M04 | M05, M07, P01, P02, INT | CTR-COL-002/004/005 | M04-PURE-020, M04-DB-019, M04-HTTP-007 | D-NR |
| FR-HIST-001 | PLAN-M08 | M01, M04-M07, DB, P01, P02, INT | retention coordinator ports, CTR-OPS-005 | M08-PURE-008, M08-DB-009, M08-LIFE-012 plus each data owner's retention scenarios | D-NR |
| FR-HIST-002 | PLAN-M05 | M06, M07, P01, P02, INT | CTR-CAP-006/007, CTR-RUN-001..003, CTR-ALERT-005 | M05-PURE-060..064, M05-DB-030..032, M05-HTTP-009, M05-BROWSER-002 | D-NR |
| FR-HIST-003 | PLAN-M08 | M01, M04-M07, DB, INT | retention coordinator ports | M08-PURE-008/009, M08-DB-009/011, M08-LIFE-009/012 plus owner purge scenarios | D-NR |
| FR-HIST-004 | PLAN-M08 | M05-M07, P01, P02, DB, INT | CTR-OPS-005 and module query ports | M08-PURE-012, M08-DB-009/010, M08-FS-011, M08-HTTP-007/008, M08-BROWSER-004 plus INT-HIST-003 | D-NR |
| FR-HIST-005 | PLAN-INT | M01, M02, M04-M08, P01, P02, DB | CTR-COMMON-002 and versioned views | INT-HIST-004 plus owner UTC round trips and real browser timezone rendering | D-NR |
| FR-ALERT-001 | PLAN-M07 | M02, M05, P01, P02, DB, INT | CTR-ALERT-001, CTR-REG-001/002/007 | M07-PURE-001..006, M07-DB-001..004, M07-HTTP-001/002 | D-NR |
| FR-ALERT-002 | PLAN-M07 | P01, P02, DB, INT | CTR-ALERT-001 | M07-PURE-007..011, M07-DB-005, M07-HTTP-003, M07-BROWSER-001 | D-NR |
| FR-ALERT-003 | PLAN-M07 | M03-M06, A01-A03, P01, P02, INT | CTR-ALERT-002..004 and consumed signals | M07-PURE-012..021, M07-LIVE-001..009 | D-NR |
| FR-ALERT-004 | PLAN-M07 | M04-M06, P01, P02, DB, INT | CTR-ALERT-002..004 | M07-PURE-022..033, M07-DB-006..012, M07-LIVE-010 | D-NR |
| FR-ALERT-005 | PLAN-M07 | P01, P02, DB, INT | CTR-ALERT-002/004/005 | M07-PURE-034..044, M07-DB-013..018, M07-HTTP-004..009, M07-BROWSER-002..006, M07-LIVE-011 | D-NR |
| FR-ALERT-006 | PLAN-M07 | P01, P02, security, INT | CTR-ALERT-003/004/005 | M07-ARCH-001/002, M07-SEC-001/002, M07-BROWSER-007 plus INT-ALERT-004 | D-NR |
| FR-UI-001 | PLAN-P02 | P01, all data producers, DEP, INT | CTR-UI-001, CTR-API-001 | UI-RESP-001..008, UI-VIS-001..005; built real-browser viewport matrix | D-NR |
| FR-UI-002 | PLAN-P02 | P01, M01-M08, INT | CTR-UI-001, CTR-API-001 | UI-NAV-001..008 plus named feature scenario families | D-NR |
| FR-UI-003 | PLAN-P02 | P01, M04-M08, INT | CTR-API-001 projections | UI-CMD-001..010; real populated or truthful empty state | D-NR |
| FR-UI-004 | PLAN-P02 | P01, INT | CTR-UI-001 | UI-A11Y-001..010; automated/manual real-browser checks | D-NR |
| FR-UI-005 | PLAN-P02 | M05, P01, INT | CTR-API-001 | UI-CAP-006, UI-VIS-003; source review and real rendering | D-NR |
| FR-UI-006 | PLAN-P02 | M03, M05, M06, P01, INT | CTR-API-001 capacity/provenance schemas | UI-CAP-004..010; real observation explanation | D-NR |
| FR-UI-007 | PLAN-P02 | P01, all producers, FND, INT | CTR-UI-001, CTR-FND-008 | UI-DATA-001..006; source/artifact/browser provenance gate | D-NR |
| FR-IAM-001 | PLAN-M01 | P01, P02, DB, DEP, INT | CTR-IAM-004 | M01-DB-001/002, M01-HTTP-001, M01-OPS-001 | D-NR |
| FR-IAM-002 | PLAN-M01 | DB, security, FND, INT | CTR-IAM-004, password policy | M01-CRYPTO-001..004, M01-HTTP-002; real admitted Argon2 implementation | D-NR |
| FR-IAM-003 | PLAN-M01 | P01, P02, DB, DEP, INT | CTR-IAM-003/005, CTR-API-002 | M01-DB-003..006, M01-HTTP-003..010, M01-BROWSER-001..004 plus INT-IAM-002 | D-NR |
| FR-IAM-004 | PLAN-M01 | P01, P02, DB, INT | CTR-IAM-006/007, CTR-API-003 | M01-DB-007..011, M01-HTTP-011..016, M01-BROWSER-005 | D-NR |
| FR-IAM-005 | PLAN-M01 | DB, M08, security, INT | CTR-IAM-006/007 | M01-DB-008, M01-SEC-001/002; DB/backup/secret inspection | D-NR |
| FR-IAM-006 | PLAN-M01 | P01, P02, FND, INT | CTR-IAM-006/007, CTR-API-003 | M01-HTTP-017, M01-BROWSER-006; generated OpenAPI and real Swagger | D-NR |
| FR-IAM-007 | PLAN-M01 | P01, FND, DEP, P02, INT | CTR-IAM-003, CTR-API-002, CTR-DEP-001 | M01-HTTP-018..021, M01-OPS-002 plus INT-IAM-005 | D-NR |
| FR-OPS-001 | PLAN-DEP | FND, A04-LINUX, M04, M08, P01, P02, INT | CTR-DEP-001, CTR-PLAT-001 | DEP-INSTALL-001..008, DEP-SVC-001..014; real target Linux T5/T7 | D-NR |
| FR-OPS-002 | PLAN-M08 | M03-M07, DB, DEP, P01, P02, INT | CTR-OPS-001/002/004/006 | M08-PURE-001..004, M08-DB-012, M08-HTTP-001..003, M08-LIFE-001/013 | D-NR |
| FR-OPS-003 | PLAN-M08 | DB, DEP, P01, P02, INT | CTR-OPS-003, CTR-DB-003 | M08-PURE-005..007, M08-DB-007/008, M08-FS-001..009, M08-LIFE-002 | D-NR |
| FR-OPS-004 | PLAN-M08 | DB, DEP, P01, P02, INT | CTR-OPS-003, CTR-DB-003 | M08-HTTP-004/005, M08-BROWSER-002, M08-LIFE-003..008 | D-NR |
| FR-OPS-005 | PLAN-M08 | every module, DB, DEP, P01, P02, INT | CTR-OPS-003..005 | M08-PURE-011/012, M08-FS-004/010..013, M08-HTTP-005/006/009, M08-SEC-001..006 | D-NR |
| FR-OPS-006 | PLAN-M08 | FND, M03-M07, DB, DEP, P01, P02, INT | CTR-OPS-001/004, CTR-FND-007, CTR-DB-001 | M08-PURE-014, M08-DB-012, M08-HTTP-003, M08-BROWSER-001 | D-NR |
| FR-SAFE-001 | PLAN-P01 | M01-M08, A01-A04, P02, DEP, INT | CTR-API-001 and every allowed command port | API-HTTP-010..036 and route/permission inventory are real-boundary candidates, but promised INT-SAFE-001..008 are undefined and the current P01 trace row is not an exact positive allowed-action inventory | R-NR |
| FR-SAFE-002 | PLAN-P01 | every module/adapter, P02, DEP, INT | CTR-API-001 plus absence across all published surfaces | API-HTTP-036, API-SEC-015, INT-SEC-009 and module negative surface scans | D-NR |

## 4. Discovery-status V1 requirements

| ID | Primary | Supporting plans | Contracts | Planned scenarios and required evidence | Status |
|---|---|---|---|---|---|
| FR-AUTH-006 | PLAN-M0-DISCOVERY | M02, M03, A01-A03, M04, P01, P02, INT | future CTR-REG-003/006 and CTR-PROV-002/005/007; currently blocked | M0-CLA-001/007..010, M0-CDX-001/007..010, M0-OLL-001/007/009/010; real installed versions/accounts, no auth mutation in M0 | D0-NR |
| FR-QUOTA-006 | PLAN-M0-DISCOVERY | M03, M05, A01-A03, M04, P01, P02, INT | future CTR-PROV-002/004 and CTR-CAP-001; currently blocked | M0-CLA-001..004/010, M0-CDX-001..004/010, M0-OLL-001/004/010; authoritative real surfaces | D0-NR |
| FR-BUDGET-006 | PLAN-M0-DISCOVERY | M03-M05, A01-A03, P01, P02, INT | future CTR-PROV-002/004 and CTR-CAP-002; currently blocked | M0-ANT-001..008, M0-OAI-001..009, M0-OAPI-001..007; real approved billing roles/accounts | D0-NR |

## 5. Non-functional requirements

| ID | Primary | Supporting plans | Contracts | Planned scenarios and required evidence | Status |
|---|---|---|---|---|---|
| NFR-ARCH-001 | PLAN-FND | every catalog plan, INT | CTR-FND-001, ownership/import policy | FND-BND-001/002 plus INT-CONTRACT-002; real source/import graph | D-NR |
| NFR-ARCH-002 | PLAN-FND | every module, DB, INT | CTR-FND-001, typed producer contracts | FND-BND-003, FND-MIG-003 plus INT-PLAN-003/CONTRACT-006 | D-NR |
| NFR-API-001 | PLAN-P01 | FND, M01-M08, P02, DEP, INT | CTR-API-001, CTR-FND-002/005 | API-OAPI-001..012, API-HTTP-001..038 plus INT-API-004; real FastAPI HTTP | D-NR |
| NFR-API-002 | PLAN-P01 | FND, P02, INT | CTR-UI-001, CTR-FND-005 | API-CLIENT-001..008, API-OAPI-001..012 plus INT-API-003/005 | D-NR |
| NFR-DATA-001 | PLAN-DB | M01-M08, FND, DEP, INT | CTR-DB-001/002/003, CTR-FND-006 | DB-FILE-001..010, DB-TXN-001..012, DB-PORT-001..006 plus INT-MIG-008; real file SQLite | D-NR |
| NFR-TEST-001 | PLAN-FND | every plan, INT | CTR-FND-008 | FND-EVID-001 plus every behavioral scenario's retained Red/Green/refactor record | D-NR |
| NFR-TEST-002 | PLAN-FND | every plan, INT | test-integrity policy, CTR-FND-008 | FND-TEST-001, FND-UI-002 plus module prohibited-pattern gates | D-NR |
| NFR-SEC-001 | PLAN-INT | every plan and security reviewers | all boundary contracts, CTR-FND-003/004/008 | INT-SEC-001..012, INT-API-007, module security matrices; real source/runtime/artifact boundaries | D-NR |
| NFR-PRIV-001 | PLAN-INT | M03-M08, A01-A04, P01, P02, DB | data allowlists and every public DTO/artifact contract | INT-EVID-003, INT-SEC-004/005/008/010 plus module persistence/log/export scans | D-NR |
| NFR-PRIV-002 | PLAN-INT | FND, every runtime/boundary/dependency owner | dependency/network policies | INT-SEC-007, INT-LIC-006 plus module network/artifact reviews | D-NR |
| NFR-DOC-001 | PLAN-FND | every plan, INT | documentation/command registry, CTR-FND-008 | FND-DOC-001..003 and INT-AUTO-002; real checkout docs validation | D-NR |
| NFR-LIC-001 | PLAN-INT | FND and every dependency owner | dependency admission records, SBOM/notices | INT-LIC-001..007 plus FND-DEP-001..004; real locked graph | D-NR |
| NFR-PLAT-001 | PLAN-A04-MAC | A04-LINUX, DEP, FND, DB, M06, INT | CTR-PLAT-001, CTR-RUN-006, CTR-DEP-001 | all MAC-PROC/FS/SVC/DIAG scenarios on a real Mac plus LNX-COMP-001..006 on real Linux; macOS T5 currently Blocked | B-NR |
| NFR-PERF-001 | PLAN-INT | M02-M08, A01-A04, P01, P02, DB, DEP | bounded query/inspection/API contracts | INT-PERF-001..004; 100 production-created registry records and 200 real owned processes without provider claims | D-NR |
| NFR-RES-001 | PLAN-INT | M03-M08, A01-A04, P01, P02, DB, DEP | typed failure/health contracts | INT-PERF-005..007 plus INT-OPS-003; real owned-component/provider failure where safe | D-NR |
| NFR-OBS-001 | PLAN-FND | every plan, M08, INT | CTR-FND-004, CTR-OPS-004/006 | FND-LOG-001..004 plus module log/diagnostic scans | D-NR |
| NFR-COMP-001 | PLAN-INT | FND, M01-M08, adapters, P01, P02, DB, DEP | every versioned contract class | INT-CONTRACT-001..005, INT-API-006, INT-MIG-001..008 | D-NR |

## 6. V1 acceptance criteria

### 6.1 Release-wide

| ID | Primary | Supporting plans | Contracts | Planned scenarios and required evidence | Status |
|---|---|---|---|---|---|
| AC-V1-001 | PLAN-INT | all other 19 catalog plans | CTR-FND-008 and all requirement contracts | INT-TRACE-001..006; exact current requirement-to-evidence chain | D-NR |
| AC-V1-002 | PLAN-INT | all other 19 catalog plans | planning catalog, contract register, approval records | INT-PLAN-001..006; canonical synchronized planning gate currently exits 1 because CS-1 is absent | GATE-RED |
| AC-V1-003 | PLAN-INT | FND, P01, P02, DEP | CTR-FND-005, CTR-API-001, CTR-UI-001 | INT-API-001..008; running API, generated OpenAPI/client, built browser | D-NR |
| AC-V1-004 | PLAN-INT | DB, M01-M08, DEP | CTR-DB-001..003, CTR-FND-006 | INT-MIG-001..008; real fresh and supported prior-release SQLite artifacts | D-NR |
| AC-V1-005 | PLAN-INT | all plans and independent reviewers | security/dependency/evidence contracts | INT-SEC-001..012, INT-LIC-001..007 | D-NR |
| AC-V1-006 | PLAN-INT | FND, every module, DEP, M08 | documentation and command registry | primary row cites undefined INT-DOC-001..008; defined INT-TRACE-004/INT-AUTO-002 and module DOC scenarios only partly replace it | R-NR |
| AC-V1-007 | PLAN-INT | FND, M01-M08, P01, P02, DB, DEP | artifact/evidence allowlists | INT-SEC-003..010; real repo/build/log/diagnostic/export/backup scans | D-NR |
| AC-V1-008 | PLAN-INT | every producer, P01, P02, test steward | provenance/test evidence contracts | primary row cites undefined INT-TEST-001..008; INT-TRACE-005/INT-AUTO-011 and module scans partly cover intent | R-NR |

### 6.2 Live accounts and providers

| ID | Primary | Supporting plans | Contracts | Planned scenarios and required evidence | Status |
|---|---|---|---|---|---|
| AC-LIVE-001 | PLAN-A01 | M0, M02-M05, P01, P02, INT | CTR-REG-002/003/005/006, CTR-PROV-001..008 | CLA-LIVE-002 plus INT-CLA-001; six owner-confirmed aliases/unavailable declarations | D0-NR |
| AC-LIVE-002 | PLAN-A02 | M0, M02-M05, P01, P02, INT | CTR-REG-002/003/005/006, CTR-PROV-001..008 | CDX-LIVE-001/002/015..019 plus INT-CDX-001; four real accounts | D0-NR |
| AC-LIVE-003 | PLAN-A03 | M0, M02-M05, P01, P02, INT | CTR-REG, CTR-PROV | OLL-LIVE-002/003 plus INT-OLL-001; two real identity/workspace relationships | D0-NR |
| AC-LIVE-004 | PLAN-M03 | A01-A03, M0, M02, M04-M06, INT | CTR-PROV-001..008 | M03-LIVE-001..010 plus provider conformance matrices | D0-NR |
| AC-LIVE-005 | PLAN-M05 | A01-A03, M03, M04, P01, P02, INT | CTR-PROV-004, CTR-CAP-001/002, CTR-COMMON-004 | M05-LIVE-001..013 plus INT-CLA/CDX/OLL/BUD reconciliation scenarios | D0-NR |
| AC-LIVE-006 | PLAN-M02 | M03, A01-A03, M04, P01, P02, INT | CTR-REG-003/006, CTR-PROV-007 | M02-LIVE-005/007..010 plus provider re-auth scenarios; owner-controlled official flows | D0-NR |
| AC-LIVE-007 | PLAN-M03 | A01-A03, M04, M05, M07, P02, INT | CTR-PROV-004/006/007 | M03-LIVE-006..008/010 plus natural provider states; unavailable remains Blocked | D0-NR |

### 6.3 Dashboard and workflow

| ID | Primary | Supporting plans | Contracts | Planned scenarios and required evidence | Status |
|---|---|---|---|---|---|
| AC-UI-001 | PLAN-P02 | M01, P01, DB, INT | CTR-IAM-003..007, CTR-API-001..003, CTR-UI-001 | UI-AUTH-001..010, UI-TOKEN-001..010 plus M01-BROWSER-001..006 | D-NR |
| AC-UI-002 | PLAN-P02 | every data producer, P01, DB, INT | CTR-API-001, CTR-UI-001 | UI-CMD/ORG/ACC/CAP/BUD/RUN/ALERT scenario sets plus INT-UI-001; real data only | D-NR |
| AC-UI-003 | PLAN-P02 | P01, DEP, INT | CTR-UI-001 | UI-RESP-001..008 plus INT-UI-002/003; real viewport/zoom matrix | D-NR |
| AC-UI-004 | PLAN-P02 | P01, INT | CTR-UI-001 | UI-A11Y-001..010 plus INT-UI-004/005; real browser/manual AT | D-NR |
| AC-UI-005 | PLAN-P02 | all producers, P01, INT | CTR-API-001 problem/state schemas | UI-STATE-001..012 plus INT-API-008/INT-UI-006 | D-NR |
| AC-UI-006 | PLAN-P02 | M03, M05, M06, P01, INT | CTR-API-001 capacity/runtime/provenance | UI-CAP-004..010 plus INT-UI-007 and provider vertical slices | D-NR |

### 6.4 Process and session

| ID | Primary | Supporting plans | Contracts | Planned scenarios and required evidence | Status |
|---|---|---|---|---|---|
| AC-PROC-001 | PLAN-M06 | M0, A01-A04-LINUX, P01, P02, INT | CTR-RUN-001/006 | M06-LNX-001/009 plus INT-PROC-001; real target Linux processes | D0-NR |
| AC-PROC-002 | PLAN-M06 | M0, A01-A04, P01, P02, INT | CTR-RUN-003/006 | M06-LNX-007, M06-LIVE-006 plus INT-PROC-002 | D0-NR |
| AC-PROC-003 | PLAN-M06 | M02, A01-A04, P01, P02, INT | CTR-RUN-007, CTR-REG-006 | M06-LIVE-005, M06-API-005, M06-UI-002 plus INT-PROC-003 | D0-NR |
| AC-PROC-004 | PLAN-M06 | A01-A04, DB, M08, P01, P02, INT | runtime storage allowlists | M06-SEC-001..004, M06-LNX-008 plus INT-PROC-004/INT-SEC-005 | D0-NR |
| AC-PROC-005 | PLAN-M06 | A01-A04, M07, P01, P02, INT | CTR-RUN-005 | M06-LIVE-008, M06-PURE-009..012 plus INT-PROC-005/006 | D0-NR |

### 6.5 Alerts and history

| ID | Primary | Supporting plans | Contracts | Planned scenarios and required evidence | Status |
|---|---|---|---|---|---|
| AC-ALERT-001 | PLAN-M07 | M02, M05, P01, P02, DB, INT | CTR-ALERT-001 | M07-PURE-001..011, M07-DB-001..005, M07-HTTP-001..003 plus INT-ALERT-001 | D-NR |
| AC-ALERT-002 | PLAN-M07 | M04-M06, P01, P02, DB, INT | CTR-ALERT-002..005 | M07-DB-006..022, M07-HTTP-004..010, M07-BROWSER-002..006, M07-LIVE-011 plus INT-ALERT-002 | D-NR |
| AC-ALERT-003 | PLAN-M07 | M03-M06, A01-A03, P01, P02, INT | consumed signal contracts, CTR-ALERT-002..005 | M07-LIVE-004..007 plus INT-ALERT-003; natural real stale/auth conditions | D0-NR |
| AC-HIST-001 | PLAN-INT | M04-M08, A01-A03, P01, P02, DB | CTR-COL-003/006, CTR-CAP-006, CTR-RUN-002, CTR-ALERT-005 | INT-HIST-001; real collection-to-SQLite-to-API-to-built-chart | D0-NR |
| AC-HIST-002 | PLAN-INT | M01, M04-M08, DB | retention ports | INT-HIST-002; pure explicit `as_of` plus real database deletion without clock change | D-NR |

### 6.6 Reliability and operations

| ID | Primary | Supporting plans | Contracts | Planned scenarios and required evidence | Status |
|---|---|---|---|---|---|
| AC-OPS-001 | PLAN-DEP | FND, A04-LINUX, M08, DB, P01, P02, INT | CTR-DEP-001, CTR-PLAT-001 | DEP-INSTALL-001..008, DEP-SVC-001..009 plus INT-OPS-001 | D-NR |
| AC-OPS-002 | PLAN-DEP | M04, M08, A04-LINUX, P02, INT | CTR-DEP-001, CTR-OPS-003 | DEP-SVC-007 plus M04-OPS-008/M08-LIFE-002/INT-OPS-002 | D-NR |
| AC-OPS-003 | PLAN-INT | M03-M08, A01-A04, P01, P02, DEP | health/failure contracts | INT-OPS-003 and INT-PERF-006; real naturally failing component/provider path | D0-NR |
| AC-OPS-004 | PLAN-M08 | DB, DEP, P01, P02, INT | CTR-OPS-003, CTR-DB-003 | M08-FS-001..009, M08-LIFE-003..008 plus INT-OPS-004/009 | D-NR |
| AC-OPS-005 | PLAN-DEP | DB, M01, M04-M08, INT | CTR-DEP-001, CTR-DB-001..003 | DEP-UPG-001..012, DEP-REC-001..010 plus INT-OPS-005/010 | D-NR |
| AC-OPS-006 | PLAN-M04 | M0, M03, A01-A03, INT | CTR-PROV-002/004, collection admission/budget contracts | M04-PURE-024/025, M04-DB-005/006, M04-LIVE-015 plus INT-OPS-006/INT-BUD-012 | D0-NR |

### 6.7 Test integrity

| ID | Primary | Supporting plans | Contracts | Planned scenarios and required evidence | Status |
|---|---|---|---|---|---|
| AC-TEST-001 | PLAN-FND | every implementation plan, INT | CTR-FND-008 | FND-EVID-001 plus behavior-specific Red/Green/refactor records | D-NR |
| AC-TEST-002 | PLAN-FND | every implementation plan, INT | test-integrity policy, CTR-FND-008 | FND-TEST-001/FND-UI-002 plus module repository scans | D-NR |
| AC-TEST-003 | PLAN-INT | FND, M01-M08, P01, P02, DB | AUTO-TEST selectors and CTR-FND-008 | FND-DB-001/FND-HTTP-001/FND-UI-001 plus all module T1-T4 matrices and INT-AUTO-003/011 | D-NR |
| AC-TEST-004 | PLAN-INT | M0, A01-A04, M03-M06, owner | live-report/evidence contract | INT-EVID-004 plus M0-COM-008 and provider/platform live matrices | D0-NR |
| AC-TEST-005 | PLAN-INT | M01, M04-M07 and other critical-policy owners | mutation evidence in CTR-FND-008 | module critical `PURE`/`DB` mutation matrices; exact admitted tool and per-module target remain approval blockers | D-NR |
| AC-TEST-006 | PLAN-INT | every plan | CTR-FND-008 and four-state gate tree | INT-TRACE-006, INT-EVID-001, INT-AUTO-003/011 | D-NR |

## 7. Deferred requirements and leakage check

| ID | V1 guard | Observed plan treatment | Status |
|---|---|---|---|
| FR-ALERT-007 | No email in V1; future credentials and approval required | PLAN-INT excludes it, but PLAN-P01 includes `FR-ALERT-001 through FR-ALERT-008` and `FR-ALERT-001..008` in V1 workflow/test coverage | X-LEAK |
| FR-ALERT-008 | No messengers; no native Linux notification requirement | Same contradictory PLAN-P01 ranges as FR-ALERT-007 | X-LEAK |
| FR-ROUTE-001 | No account recommendation/selection in V1 | Explicitly excluded by P01 and guarded by PLAN-INT | X |
| FR-ROUTE-002 | No checkpoint/recovery under another account/provider in V1 | Explicitly excluded by P01 and guarded by PLAN-INT | X |
| FR-CONTENT-001 | No prompt/response/tool-content storage in V1 | Explicitly excluded by P01 and guarded by PLAN-INT | X |
| FR-REMOTE-001 | No remote/multi-user deployment in V1 | Explicitly excluded by P01 and guarded by PLAN-INT | X |
| FR-PROVIDER-EXT-001 | No Gemini/Grok/Muse/additional-provider implementation in V1 | Guarded by PLAN-INT; absent from P01's deferred summary but not present in its endpoint plan | X |

## 8. Cross-plan defects

### 8.1 Undefined PLAN-INT scenario references

The following referenced IDs have no scenario definition in PLAN-INT:

- `INT-ALERT-005..009`
- `INT-COL-007..010`
- `INT-DOC-001..008`
- `INT-HIST-005..008`
- `INT-IAM-006..010`
- `INT-LIVE-004..010`
- `INT-OPS-011..014`
- `INT-PROC-007..010`
- `INT-SAFE-001..008`
- `INT-TEST-001..008`
- `INT-UI-009..012`

Total: 61 undefined exact references. `INT-E2E-*` is additionally a vague,
undefined wildcard and cannot be an evidence identifier.

This defect is not detected by the present validator because the validator checks
minimum distinct scenario inventory rather than referential integrity of every
scenario expression.

### 8.2 Multiple-primary shorthand

These canonical rows do not yet meet the exactly-one-primary rule:

- PLAN-INT assigns `FR-ACC-*` to `M02 + adapters`, `FR-AUTH-*` to
  `M02/M03/adapters`, `FR-HIST-*` to `M05/M06/M07/M08`, `FR-OPS-*` to
  `M08/DEP/DB/A04`, and `FR-SAFE-*` to `all`.
- PLAN-INT assigns non-functional and acceptance families to lists of owners
  rather than one accountable evidence closer.
- `docs/traceability.md` similarly uses `Registry + provider adapters`,
  `Capacity/runtime/alerting`, `All modules`, and family-level rows.

The exact-primary tables in this audit are a proposed resolution. CS-1 must
approve or amend them and update the canonical traceability source; this audit
cannot silently change ownership.

### 8.3 Contract maturity mismatch

Detailed producer plans now define proposed schemas and semantics for M02-M08,
provider/platform adapters, P01/P02, DB, and DEP, while the contract register
still labels all non-foundation/non-IAM contracts `Concept`. CS-1 must reconcile
plan text with one canonical version/status and record every consumer review.
No contract may jump from this mismatch directly to Approved.

### 8.4 Real-boundary and test-integrity result

- Every external-boundary claim reviewed names a real SQLite, real HTTP, built
  browser, real OS/service, or real provider/account boundary as applicable.
- Naturally unavailable provider states remain Blocked rather than simulated.
- macOS verification is explicitly Blocked until a real Mac is available.
- Provider-dependent requirements remain gated by M0 and no M0 observation has
  been executed.
- No test result exists yet. Structural plan review cannot count as Red, Green,
  Passed, live verification, or implementation evidence.

## 9. Executed audit commands and results

| Command | Exit | Result |
|---|---:|---|
| `python3 tools/planning/validate_plans.py --stage draft-complete` | 0 | Draft artifact/count/structure gate Passed. This is not synchronization or approval. |
| `python3 tools/planning/validate_plans.py --stage synchronized` | 1 | Failed: missing `docs/plans/integration/cs1-full-plan-synchronization.md`. |
| `python3 -m unittest tools/planning/test_validate_plans.py` | 1 | One of two tests failed for the same missing CS-1 artifact. |

The initially attempted unsupported selector `--stage draft` exited 2 and was
corrected to the documented `--stage draft-complete`; it is not evidence for or
against plan completeness.

## 10. Required root fixes before CS-1 can pass

1. Repair PLAN-INT's 61 undefined references: either define substantive scenarios
   with real boundaries or replace each range with already defined exact IDs.
   Remove `INT-E2E-*` and use exact stable IDs.
2. Remove deferred FR-ALERT-007/008 from P01's V1 workflow and test ranges; add
   explicit negative route/config/dependency checks for all seven deferred IDs.
3. Add an exact positive allowed-action inventory for FR-SAFE-001 and retain the
   negative no-control proof for FR-SAFE-002.
4. Resolve exactly one primary plan for every ID through CS-1. Update
   `docs/traceability.md`, PLAN-INT, and plan rows without erasing supporting
   responsibilities.
5. Reconcile all 76 contract register entries with producer-plan definitions,
   consumers, schema/version, compatibility promise, discovery blocker, and
   review status. No implementation approval until required contracts are
   Synchronized and owner-approved.
6. Create the substantive CS-1 review only after its inputs are corrected. It
   must record every exact ID, all 20 plan digests/versions, contract decisions,
   table/config/generated/shared-file ownership, unresolved blockers, and the
   real validator result.
7. Extend `AUTO-PLAN-CHECK` and its real tests to fail closed on:
   - undefined or wildcard scenario references;
   - a non-deferred requirement/AC without exactly one primary plan;
   - deferred IDs in V1 supported/test/API/config/permission surfaces;
   - contract producer/status/version disagreement;
   - requirement rows without a contract, named scenario, and matching real
     boundary;
   - any live/provider/platform scenario represented as Passed without a valid
     sanitized evidence record.
8. Rerun both validator tests and the synchronized gate. A green planning gate
   will mean only that the Draft plan set is complete and synchronized; approval,
   implementation, dependency admission, M0 execution, and live verification
   remain separate gates.

## 11. Final audit disposition

The exact coverage inventory exists, but synchronization is **Failed** and all
behavioral evidence remains **Not Run**. The next legitimate state is correction
of the findings above followed by a real CS-1 review and rerun of the canonical
gate. Production implementation remains unauthorized.
