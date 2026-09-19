# Test evidence: change or increment

- Evidence ID:
- Module/plan/increment:
- Requirements/acceptance IDs:
- Contract versions:
- Commit/worktree reference:
- Recorder/date:

## Test inventory and status

| Test/scenario ID | Layer | Real dependencies | Status | Evidence reference | Notes |
|---|---|---|---|---|---|
| ID | Pure/DB/API/browser/platform/provider | Dependencies | Passed/Failed/Blocked/Not Run | Reference | Notes |

## Red evidence

For each new/changed behavior, record the command/test ID, expected reason it failed before production implementation, actual sanitized failure summary, and timestamp/worktree reference. A syntax/setup failure does not prove behavioral red.

## Green evidence

Record the same tests passing after the minimum implementation, plus relevant broader suites. Include exit status and concise sanitized output/reference.

## Refactor evidence

Record tests rerun after refactoring and any static, schema, migration, build, or boundary checks.

## Real-system evidence

Summarize real SQLite, HTTP server, built browser, OS/process, and provider/account verification required by the change. Link live reports. Explicitly list unavailable layers as Blocked or Not Run.

## Integrity declaration

Confirm no mock, fake, stub, emulator, response recording/replay, demo account, seeded telemetry, placeholder UI value, hardcoded test pass, disabled assertion, test-only production branch, or swallowed failure was used.

## Data and secret review

Confirm evidence contains no secrets, provider payloads, content, personal account identifiers, or sensitive process/environment data.

## Conclusion and residual gaps

State what the evidence proves, what it does not prove, defects found, and next required gate.

