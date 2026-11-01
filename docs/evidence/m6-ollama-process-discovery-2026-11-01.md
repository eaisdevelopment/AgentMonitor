# M6 Ollama process discovery — preliminary

Requirement M6-T013 / M6-A06: read-only process discovery and honest
correlation. A read-only process-name inventory on 1 November 2026 reported
two `ollama` processes on this Linux host. Process names alone do not establish
their executable identity, version, model, account, activity, relationship to
the daemon on port 11434, or relationship to the desktop app. No process was
started, stopped, signalled or modified; no command lines, environments,
provider profiles or conversation data were read.

The existing Linux platform adapter has a composition-approved executable
selector with executable identity checks and PID-reuse guards. Ollama
installation discovery currently exists but is not wired into runtime
composition. A provider-specific integration and real validation are still
needed; this inventory is not evidence that process correlation works or that
M6-T013 is complete.

The existing Linux adapter was also called against the actual locally
validated Ollama executable, using its normal approved-executable-selector
mechanism and a read-only bounded process request. The adapter returned
`unsupported` with zero matched processes: its static admitted-selector list
currently contains Claude and Codex only, so an Ollama selector is not yet
accepted. This is evidence of a concrete implementation gap, not proof that
no Ollama processes exist. The local test's installation reference was used
only for this ephemeral discovery call; it was not written to the registry.

A same-user Ollama process was independently confirmed to have the same
filesystem device and inode as the installed executable; a second Ollama
process runs under another user and is outside the same-user adapter scope.
A real-process test at `backend/tests/live/ollama/test_process_discovery.py`
was added and run before implementation. It failed for the expected
`linux_selector_unverified` reason (unsupported selector); this is Red, not a
pass. The installation reference used by the test is an ephemeral digest of
real executable metadata and is not persisted. This real-state test requires
an existing matching same-user process and is not part of the already-passing
local-catalog admission routine.
