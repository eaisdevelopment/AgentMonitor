# ADR 0001: Modular monolith with enforced module boundaries

- Status: Accepted
- Date: 2026-09-18
- Owner: Pavlo Sidelov

## Context

AgentMonitor needs independent provider, collection, capacity, runtime, alerting, identity, and operations development. It initially runs on one workstation and must become useful before a distributed supervisor exists. Microservices would add deployment, network, security, consistency, and test cost without a current scaling need. An unstructured monolith would prevent safe independent sub-agent work.

## Decision

Use one native deployable organized as a modular monolith. Enforce one-way dependencies, table ownership, published typed contracts, versioned events, provider/platform adapters, and CI import-boundary checks. Plan and assign future work one primary module per sub-agent.

## Consequences

- Local installation and transactions remain simple.
- Modules can be planned/tested/reviewed independently.
- Physical database/process sharing must not justify direct table/import coupling.
- Some infrastructure (outbox, composition) is shared and centrally governed.
- A module may be extracted later if operational evidence requires it.

## Rejected alternatives

- Microservices in V1: excessive operational and testing complexity.
- Layered monolith with shared models/repositories: weak ownership and high coupling.
- Provider-specific applications: duplicates core identity/history/alert behavior.
