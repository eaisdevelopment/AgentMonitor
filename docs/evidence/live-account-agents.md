# Live account agents and duplicate identity progress

Date: 2026-09-29. Owner: integration steward. Status: Passed for the bounded
owner-authorized terminal/account link, built browser and persistent read view.
Full M4 is not accepted; other unidentified processes and unexecuted live
unlink/PID-reuse/exec/account-change scenarios remain outside this result.

## Scope and authority

The owner requested account drill-down to identify currently running Claude
terminals and supplied a genuine official `/status` observation. The owner later
explicitly delegated the corresponding dashboard confirmation and browser test
to root. Provider sign-in/credentials remain owner-controlled. Plans:
[live agent association](../plans/integration/live-agent-account-association-change.md)
and [duplicate overview](../plans/integration/duplicate-account-overview-change.md).
[ADR 0015](../decisions/0015-owner-process-account-associations.md) records the
M06 settings persistence exception and backup consequence.

Requirements: FR-ACC-006, FR-DISC-001/002/004/007, FR-UI-001/002/003/004/006/007,
FR-SAFE-002, FR-IAM-003/006/007. Bounded AC-PROC-001/003/004,
AC-UI-002/004/005/006, AC-TEST-001/002/003/004/006 apply only to the named
scenarios. This is not universal coverage of those release criteria.
Primary M06, supporting M02/A01/A04/P01/P02/root; additive CTR-RUN-006/007 V1,
existing M02/M01 and generated API V1. New PUT is browser-only write:accounts,
CSRF and If-Match; old GET operation/query grammar is unchanged. The canonical
generator reports 45 operations and compatible V1 drift.

## Red and Green evidence

| Scenario | Meaningful Red | Current Green or remaining boundary |
|---|---|---|
| Real browser account drill-down | `process_account_association_contract_missing` before production changes | Built shared Chrome finds ten genuine processes; no-link state, inert confirmation form, Overview navigation, guarded details and 1920/1280/390 layouts Passed |
| Actual owner terminal/version | `owner_reported_running_terminal_missing` with the owner's actual PID | Read-only OS/native discovery includes that current terminal, actual CLI 2.1.283, reported cwd, and genuine OS metrics |
| Additive API declaration | `test_generator_rejects_success_schema_drift`: `assert 44 == 45` | Real schema policy and pure transition tests Passed; artifact generation reports compatible |
| Special-file filesystem guard | `unsafe_settings_special_file_blocks_reader` against a real FIFO | Nonblocking open rejects the special file; actual filesystem tests reject unsafe modes, symlinks, hardlinks, oversize/corrupt/unknown/duplicate-key settings without reset |
| Executable replacement guard | `owner_association_key() takes 1 positional argument but 2 were given` | Pure selector test now distinguishes images; read/set/persisted key validation binds exact executable fingerprint |
| Duplicate quota identity | `duplicate_identity_quota_displayed_twice` in actual authenticated Overview | Live post-restart shared Chrome Passed: one genuine duplicate group, one quota row, two connected profiles and review link; all six records have fresh verified quota lineage |
| Owner write/persistence/reopen | Initial association was unavailable; no attestation invented | Owner explicitly delegated the known terminal confirmation; real browser PUT 200, private settings receipt and post-service-restart guarded join/reopen Passed; canonical AUTO-ACCOUNT-AGENTS Passed |

Initial pure and OpenAPI rerun: 10 Passed in 34.96s. Canonical focused run after
refactor: 24 tests Passed in 32.10s; final import/format rerun 24 Passed in
32.24s. Read-only populated browser and genuine duplicate presentation Passed;
the historical full command exited Blocked because no owner confirmation existed.
After selector/FIFO
corrections: six pure transition and twelve real filesystem tests Passed in
0.39s. Real migrated SQLite + Uvicorn/native process HTTP denial scenario
Passed in 1.89s: anonymous 401, absent CSRF 403, absent precondition 428,
malformed precondition 400, absent owner confirmation 422; no association file
was created. Early missing-module setup failures are not meaningful Reds.

Commands: `python3 tools/automation/run.py AUTO-ACCOUNT-AGENTS` with explicit
owner CDP/origin/account/PID/private data-root selectors; the full gate requires
the owner-authorized persistent receipt and never submits a confirmation.
Optional `AGENTMONITOR_TEST_DUPLICATE_IDENTITY=1` requires the genuine duplicate
condition. `AUTO-QUALITY`, `AUTO-DOCS-CHECK`, `AUTO-PLAN-CHECK` and
`AUTO-GIT-PREFLIGHT` Passed. Documentation validates 265 Markdown files and the
planning baseline is synchronized. Thirteen canonical-catalog/planning tests
Passed in 1.231s. No skipped/live-unexecuted result is a pass. The previously
delivered organization-filter verifier was updated for distinct connected
profiles; its full manual/periodic-filter regression rerun Passed: five genuine
quota rows from six registry connections, one low red and nine normal bars,
single/multiple/empty/reset filters, refresh retention, sorting, desktop/narrow
layouts and read-only account navigation. The broad pre-existing
AUTO-MUTATION runtime fingerprint prerequisite remains stale/outside this
bounded gate; universal mutation/M4 acceptance is not claimed.

## Review and operational impact

The owner subsequently directed root to perform the corresponding browser
confirmation. The real guarded link was already saved when inspected; root
exercised **Change account**, selected that same known account, verified the
save was disabled until confirmation, checked the supplied-status attestation
and submitted through the actual generated-client UI. PUT returned 200;
identical confirmation preserved revision 1 and its original timestamp. The
linked row, actual cwd/CLI version, details and account-summary path Passed.
No other process/account was assigned and no provider login was changed.

Root gracefully restarted only AgentMonitor on the existing loopback/LAN
listeners. The actual CLI process remained present. A fresh API read and a new
settings repository instance returned the same guarded account link/revision;
settings and writer-lock files remained 0600. The canonical focused gate then
Passed, including 24 tests in 34.86s and both populated browser checks: ten real
processes, one linked and nine unlinked, responsive layout, receipt and reopen.
An earlier post-restart run with the optional duplicate prerequisite exited
Blocked while scheduled identity receipts were still unavailable; its 24 tests
Passed in 40.47s. That unavailable duplicate prerequisite was not called Passed.
The genuine duplicate/group/filter scenario had independently Passed before
restart. Missing fresh identity keeps grouping fail-closed until collection.

Local `AUTO-QUALITY` Passed: 241 Python files formatted, 228 typed sources,
zero boundary violations, 45 compatible generated operations, frontend
typecheck/build and locked-input verification. Hosted/platform/release security
scans, fresh install and SBOM/notices remain Not Run.

Independent backend review found a stale-image selector defect, corrected by
binding executable fingerprint into the selector and persisted-key validation.
Independent UI review found duplicate React sibling keys, insufficient grouping
eligibility and an accessible button-name mismatch; all three were corrected.
Both bounded read-only reviews reported no further concrete blocker.

The app was restarted on existing loopback/private-LAN listeners; dashboard
password and registry remain intact. Real quota collection continues every
300 seconds. Existing read-only quota/auth parsing remains pinned to reviewed
Claude 2.1.282; additional actual native binaries are admitted only for OS
process metadata after their official version banner is checked. Native version
directories may be owner/primary-group writable, never world writable; selected
binaries must be owner-owned regular executables with no group/world write.
This relies on the existing workstation user/primary-group trust boundary and
does not authorize changing installation/profile files.

No dependency/license/lockfile change, SQLite migration, default provider
profile write, process control, or secret/content access. Metadata settings are
0700/0600, bounded and separately versioned; manual links show Owner confirmed
with timestamp and require reconfirmation after an in-terminal account change.
Per-agent model/session/tokens and working/waiting state remain unavailable.
PID start/boot scope and executable guards prevent link inheritance after reuse.

SQLite-only backups do not capture the new settings file. Full native backup,
restore, account switching and retrospective automatic identity remain outside
this scope. Older application versions ignore these settings on rollback.

## Files and follow-up

Production: runtime V1 contracts/API/dependencies/schema, M06 application/ports,
M06 settings adapter, A04 process snapshots, A01 installation discovery,
root process composition/bootstrap, generated OpenAPI/client, API wrapper,
account page/summary/agent table, Overview and CSS. Verification: pure and real
filesystem tests, HTTP route/OpenAPI tests, browser verifiers, canonical
automation/catalog, ownership allocation and docs/ADR/plan bindings.

Follow-up: identify other terminals only from their genuine owner-provided
identity evidence or a separately approved automatic source. Live unlink,
natural PID reuse, executable replacement and in-terminal account changes were
not exercised; pure guards cover those identities/revisions. Preserve distinct
registry records when provider identity duplicates; the owner reviews/reconnects
the mismatched record through admin controls. Full M4 and automatic switching
remain separate work.
