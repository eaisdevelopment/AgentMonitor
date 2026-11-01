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
