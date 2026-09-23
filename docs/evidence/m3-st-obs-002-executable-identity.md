# M3 Task 5 real Claude executable-identity evidence

- Evidence ID: `M3-ST-OBS-002-EXE-2026-09-23`
- Scope: A04-LINUX executable attribution and the A01 correlation handoff gap
- Requirements/scenarios: `FR-DISC-001/002/004/007/008`,
  `AC-PROC-001/003/004`, `LNX-PROC-001..007/015`, `LNX-LIVE-001/007`,
  `LNX-SEC-001/002/007..009`, `CLA-FS-002/003/004/009`, and
  `CLA-LIVE-008..010`
- Contracts: consumes corrected V1 `CTR-RUN-001/006` executable-identity
  semantics; this A04 packet makes no shared-contract, provider-manifest, API,
  database, or migration edit
- Result: **A04 executable/installation attribution Passed; same-account A01
  correlation remains Blocked**

## Real boundary and result

The target workstation exposed ten naturally running, same-UID processes whose
bounded procfs `comm` was `claude`. Two of them used the exact reviewed Claude
Code `2.1.278` executable. The production Linux adapter selected those two by
matching only regular-file metadata from `/proc/<pid>/exe` against the
composition-approved executable identity. It did not read or retain the
executable path or bytes.

For both returned observations, an independent bounded oracle revalidated:

- same owner UID;
- PID plus unchanged procfs start ticks;
- exact executable device/inode equality with the reviewed executable;
- expected lowercase SHA-256 safe executable fingerprint, independently
  derived from the approved real file identity;
- provider `claude` and opaque installation attribution;
- public adapter/source versions;
- continued process presence after observation.

Processes that merely shared the `claude` kernel label but used another
executable were not attributed. An attributed request without an exact
registered selector continues to fail closed before procfs enumeration.

## Red / Green / refactor

```text
2026-09-23T09:12:44Z
PYTHONPATH=backend/src backend/.venv/bin/pytest \
  backend/tests/live/claude/test_runtime_observation.py::test_real_reviewed_executable_proves_claude_installation_attribution \
  -q --tb=short
# exit 1: ImportError — ApprovedLinuxExecutableSelectorV1 did not exist

2026-09-23T09:15:10Z
# same command
# exit 0: 1 passed in 0.14s

2026-09-23T09:18:19Z
# same command after requiring public production version constants
# exit 1: ImportError — LINUX_PROCESS_ADAPTER_VERSION did not exist

2026-09-23T09:18:45Z
# same command
# exit 0: 1 passed in 0.12s

2026-09-23T09:30:51Z
PYTHONPATH=backend/src backend/.venv/bin/pytest \
  backend/tests/live/claude/test_runtime_observation.py -q --tb=short
# exit 1: 2 failed — ProcessSnapshotInputV1 had no executable_identity field

2026-09-23T09:34:31Z
# same command after the synchronized CTR-RUN field and A04 mapping landed
# exit 0: 2 passed in 0.19s
```

The implementation then separated pre/post executable identity reads, kept
candidate failures as typed partial omission codes, and revalidated the
registered executable after enumeration. Ruff and strict mypy passed for the
two owning files.

## Privacy and safety review

The implementation reads only the already approved same-UID procfs directory
metadata, bounded `/proc/<pid>/stat`, and regular-file metadata reached through
`/proc/<pid>/exe`. It does not read command line, environment, memory, maps,
file descriptors, terminal data, working directory, prompts, responses, tools,
source content, credentials, or executable bytes. It performs no signal,
attach, input, restart, login, logout, profile read, or provider-state write.
Raw executable paths and raw device/inode/stat identities remain inside A04.
Only their versioned, one-way lowercase SHA-256 fingerprint enters the closed
DTO. Raw identity values remain absent from logs, evidence output, persistence,
API, and UI.

No dependency, license, persistence, migration, configuration, or secret
handling changed.

## Exact correlation blocker

The observed executable proves the provider installation, not which Claude
profile/account launched a process. Automatic same-account correlation cannot
be implemented truthfully in this packet because all of the following remain
authoritative:

1. `docs/discovery/m0/m0-to-m03-claude-v1.json` marks
   `local.process.account_correlation` as `deferred` / `unavailable`, with the
   targeted-profile probe `Not Run`.
2. The approved evidence explicitly says current-login, process timing, OS
   ancestry, and owner recollection are not Strong account evidence.
3. `CTR-PROV-004` `ProviderOperationRequestHeaderV1` carries no safe process or
   provider-session reference into `LocalProcessCorrelationPortV1`; accepting
   its nullable `account_ref` as proof would trust the caller's assertion.
4. The A01 manifest publishes only the approved subscription-quota capability;
   no approved local-session or process-correlation source tuple exists.
5. The existing owner-confirmed account and real quota observation do not prove
   that any one of the simultaneously running Claude processes used that
   account. Inspecting command line, environment, terminal, memory, or content
   to infer it is prohibited.

Therefore the A01 local-session and correlation ports remain explicit
`unsupported`, with retry `never`, rather than emitting invented Strong
evidence. Closing the gap requires a separately approved safe targeted-profile
source plus a versioned request/evidence contract carrying the proven process
and session references. No broader M3 completion claim is made here.
