# AgentMonitor

AgentMonitor is a local-first dashboard for monitoring AI coding-agent accounts, subscription capacity, quota history, alerts, and representative running processes. It is read-mostly and uses an authenticated versioned API.

Claude monitoring and the bounded Codex milestone have been implemented and accepted. Ollama, API cost and budget monitoring, and final release hardening remain planned; see [the roadmap](docs/roadmap.md) and [implementation status](docs/evidence/v1-implementation-status-v1.json). Process discovery can be partial, and account associations are shown only when supported by evidence.

## Getting started

This is a source snapshot, not a packaged V1 release. Read the [documentation index](docs/README.md) and [operations runbook](docs/operations/runbook.md) for prerequisites, local setup, and the limits of the current implementation. Do not put credentials or provider profiles into the repository.

The reusable [product-family promotion](frontend/adv/index.html) is a standalone HTML file; its [README](frontend/adv/README.md) explains embedding and rotation options.

## License

Copyright (c) 2026 Pavlo Sidelov. All rights reserved. Public access to this source does not grant rights to use, copy, modify, or redistribute it; see [LICENSE](LICENSE).
