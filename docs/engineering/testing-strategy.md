# Testing strategy

## Non-negotiable rule

Tests must exercise the real production behavior they claim to verify. AgentMonitor prohibits mocks, fakes, stubs, emulators, simulated provider servers, replayed network recordings, invented accounts, seeded/demo telemetry, and placeholder provider responses.

Constructed values are allowed only for pure deterministic domain functions with no I/O—for example, verifying that 14.9% remaining maps to Critical under a defined threshold policy. Constructed values cannot be used to claim a provider, database, HTTP, browser, filesystem, subprocess, email, or authentication integration works.

## Test status vocabulary

- **Passed:** executed against the required real boundary and met assertions.
- **Failed:** executed and violated an assertion or required setup invariant.
- **Blocked:** could not execute because required real state, credentials, provider condition, platform, or owner action was unavailable.
- **Not Run:** not attempted for this revision/release.

Skipped/xfail tests are not counted as Passed. The pipeline reports each category separately.

## Test classes

### T1 — Pure domain tests

Allowed scope:

- threshold precedence and health classification;
- exact money/ratio arithmetic;
- forecast calculations and uncertainty rules;
- alert state transitions/fingerprints;
- retention cutoff calculations;
- version compatibility and provenance policies;
- parsing of AgentMonitor-owned typed values, not provider compatibility.

Rules:

- no filesystem, network, database, clock patching, environment mutation, or mocks;
- pass time as an explicit `as_of` value;
- use tables/property generation for meaningful boundaries;
- expected results are domain facts, not duplicated implementation algorithms.

### T2 — Real persistence and migration tests

- Create an actual temporary SQLite database file.
- Apply the real Alembic chain.
- Use production repositories and transaction configuration.
- Assert constraints, concurrency, idempotency, retention deletion, and query plans where material.
- Test upgrade from supported prior schema artifacts when versions exist.
- Verify backup/restore with SQLite's real backup and integrity mechanisms.

An in-memory substitute is insufficient for file/WAL/backup behavior.

### T3 — Real service/API tests

- Start the production FastAPI application through its real server on an ephemeral loopback port.
- Use real configuration validation and a real SQLite database.
- Send real HTTP requests with production authentication, cookies, CSRF, API tokens, and generated client where relevant.
- Assert OpenAPI conformance, authorization, idempotency, pagination, errors, and security headers.

Calling route functions directly or replacing repositories is not API integration testing.

### T4 — Real built-UI/browser tests

- Build the production frontend.
- Serve it with the running backend.
- Drive a real supported browser with Playwright.
- Use the real login, API, database, and UI rendering.
- Validate responsive breakpoints, accessibility, error/empty/stale states arising from real application state, and key workflows.

DOM-only simulators do not count as end-to-end evidence. Pure component calculations may be tested separately, but provider/dashboard truth is verified in browser tests.

### T5 — Real platform tests

- Execute against actual Linux process/filesystem/service behavior.
- Verify process discovery with real running agent processes.
- Verify PID/start-time handling, parent hierarchy, permissions, paths, systemd, and backups.
- Execute macOS compatibility tests on real macOS when available; absence is Blocked, not simulated.

### T6 — Live provider tests

- Use real owner-controlled Claude, Codex, Ollama, Anthropic API, OpenAI API, and Ollama API accounts as applicable.
- Use current provider CLIs/services and official authentication.
- Owner performs browser/email/MFA/OTP interaction directly.
- Compare data to provider authoritative UI/command at the same observation time.
- Record only sanitized account alias, provider/adapter/CLI version, timestamps, capabilities, result, and evidence references.
- Account secrets and content never enter reports.

Provider failure states that cannot safely/naturally be produced remain Blocked. Do not exhaust credits, revoke credentials, or disrupt work solely to manufacture a passing scenario unless the owner explicitly approves the controlled action.

### T7 — Operational tests

- Native install/upgrade/start/stop/restart/status.
- Browser closed while collection continues.
- Backup rotation, checksum, integrity, restore, and recovery.
- Disk-full/permission/corruption cases only with safe isolated real resources and an approved destructive-test plan.
- Diagnostic/export secret scan.

## TDD evidence

For every changed behavior, retain in the merge request or local change record:

- test identifier and requirement/acceptance ID;
- red command, timestamp, and expected failure summary;
- production change reference;
- green command, timestamp, and result;
- refactor verification command/result;
- live verification reference where required.

The red failure must demonstrate missing/incorrect behavior. Syntax errors, missing dependencies, unavailable credentials, or unrelated setup failures do not satisfy Red.

## Prohibited patterns

- `unittest.mock`, pytest mock plugins, runtime monkeypatching of collaborators, or equivalent JS mocking libraries for production boundaries.
- Fake repositories, fake clocks, fake HTTP clients, fake keyrings, fake subprocesses, or fake provider adapters.
- MSW/WireMock/VCR/cassette/replay servers used as proof of provider integration.
- Hardcoded tests that merely mirror implementation branches or assert constants returned by test-only code.
- `assert true`, snapshot-only behavior claims, tests with no meaningful failure mode, and tests that never execute production code.
- Test-only branches or endpoints in production code.
- Reclassifying missing/unknown as zero to make assertions easy.
- Silently catching a test failure, retrying until green, or excluding a failing test from the default gate.
- Seeding the dashboard with invented telemetry for screenshots or E2E.

## Dynamic live values

Do not hardcode quota, spend, token, or reset values that change over time. Live tests assert:

- identity and units are correct;
- required fields are present/nullable according to the real source;
- mathematical relationships and ranges hold;
- provenance/source/version are correct;
- freshness is within a documented window;
- AgentMonitor value reconciles with provider authoritative value at the recorded time/precision.

## Coverage and mutation quality

Coverage is a diagnostic, not proof. Module plans set targets according to risk, with these baseline expectations:

- critical security/authorization and quota/alert/retention decision logic: every documented branch covered by meaningful pure or real-stack tests;
- domain modules: high branch coverage with no exclusions hiding business behavior;
- adapters: live scenario/capability coverage is primary; line coverage cannot replace it;
- mutation testing targets critical pure logic. Surviving meaningful mutants block completion until explained or killed.

Never add low-value tests solely to raise a percentage.

## CI and local live gates

GitLab-hosted CI can run T1–T4 and migration parts of T2 using real local processes within the job. It cannot claim T5 workstation behavior or T6 provider behavior without the required real environment.

Pipeline summary must display:

- deterministic/local-stack result;
- live-provider evidence state for each adapter/capability;
- platform evidence state;
- schema/API compatibility;
- security/license/secret scans;
- blocked/not-run scenarios.

## Test data handling

- Real operational data remains on the owner's machine.
- CI artifacts contain no account data or secrets.
- Sanitization is allowlist-based.
- If a real provider artifact is retained for incident analysis, it is not committed and cannot be used as a simulated provider test. Retention and deletion are documented.
- Pure domain values must be visibly domain examples, never labeled as provider observations.

## Flaky test policy

A flaky test is a defect. Do not auto-retry it into a pass. Capture evidence, classify environmental vs product cause, fix or mark Blocked with owner-visible impact. Live provider variability is modeled with documented tolerances, not broad assertions that cannot fail.

## Test review checklist

- Does it execute the claimed production boundary?
- Would it fail if the behavior broke?
- Is the expected result independent of implementation structure?
- Does it avoid prohibited substitutes?
- Are dynamic provider values reconciled rather than hardcoded?
- Are secrets/content absent from output/artifacts?
- Is cleanup safe and real?
- Is status truthful?
