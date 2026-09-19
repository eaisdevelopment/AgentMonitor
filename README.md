# AgentMonitor

AgentMonitor is a local-first, API-first operations dashboard for observing AI coding-agent accounts, subscription quotas, API budgets, authentication health, and running local sessions across multiple providers.

The project is currently in its specification phase. No production application has been implemented. The first delivery milestone is a read-only discovery exercise against real Claude, Codex, and Ollama installations and accounts.

## Approved direction

- FastAPI backend with an OpenAPI 3.x contract and Swagger UI.
- React, TypeScript, Vite, and Apache ECharts frontend.
- Native Linux deployment first; macOS-compatible design.
- Responsive mission-control dashboard backed only by real data.
- Modular-monolith architecture with independently owned modules and versioned contracts.
- Strict TDD. No mocks, fakes, emulators, demo telemetry, or simulated provider responses.
- Single-user authenticated dashboard and token-authenticated API.
- SQLite for the local deployment, with migration discipline and PostgreSQL portability.
- One year of operational history and automated local backups.
- Claude first, followed by Codex, Ollama, and API-budget integrations.

## Documentation

Start with [the documentation index](docs/README.md). Contributors and coding agents must also follow [AGENTS.md](AGENTS.md).

The controlling documents are:

- [Project charter](docs/product/project-charter.md)
- [Product requirements](docs/product/requirements.md)
- [V1 acceptance criteria](docs/product/v1-acceptance-criteria.md)
- [Architecture](docs/architecture/system-architecture.md)
- [Module boundaries](docs/architecture/modules.md)
- [Contracts and versioning](docs/architecture/contracts-and-versioning.md)
- [Testing strategy](docs/engineering/testing-strategy.md)
- [SDLC](docs/engineering/sdlc.md)
- [Sub-agent runbook](docs/engineering/subagent-runbook.md)
- [Module planning registry](docs/plans/README.md)
- [Operations runbook](docs/operations/runbook.md)
- [Roadmap](docs/roadmap.md)

See [CONTRIBUTING.md](CONTRIBUTING.md) for the governed change process and [SECURITY.md](SECURITY.md) for private vulnerability reporting.

## Ownership

Copyright (c) 2026 Pavlo Sidelov <pavlo@sidelov.com>. All rights reserved. See [LICENSE](LICENSE).
