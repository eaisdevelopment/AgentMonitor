# AgentMonitor

AgentMonitor is a local-first dashboard for monitoring AI agent accounts,
subscription capacity, quota history, alerts and representative running
processes. It uses an authenticated, versioned API and is designed to observe
running agents without interrupting them.

## Dashboard demo

![AgentMonitor dashboard overview](docs/images/dashboard-demo.png)

The screenshot is a point-in-time example of the dashboard.

## Project status

Claude monitoring and the bounded Codex milestone have been implemented and
accepted. Ollama local discovery and process monitoring are in development;
Ollama cloud accounts, full M6 verification and deployment are not complete.
Observations that cannot be verified are shown as unknown or unavailable.

This repository contains the current project source, including work in
progress. It is not yet a packaged V1 release. A verified one-command
installation is not yet available; see the [roadmap](docs/roadmap.md),
[implementation status](docs/evidence/v1-implementation-status-v1.json) and
[operations runbook](docs/operations/runbook.md) for current capabilities and
limitations. Do not commit credentials or provider profiles.

## Repository

- [Backend](backend/) — API, provider adapters, domain modules and tests.
- [Frontend](frontend/) — dashboard and product-family promotion.
- [Contracts](contracts/) — versioned API specifications.
- [Documentation](docs/README.md) — architecture, requirements and runbooks.
- [Tools](tools/) — development and verification commands.

The frontend uses Node.js 22.23.3 and npm 10.9.9; the Python project requires
Python 3.12.3 or later. See [CONTRIBUTING.md](CONTRIBUTING.md) and
[AGENTS.md](AGENTS.md) for the development process.

## License

Copyright (c) 2026 Pavlo Sidelov. All rights reserved. Public access to this
source does not grant rights to use, copy, modify or redistribute it; see
[LICENSE](LICENSE).
