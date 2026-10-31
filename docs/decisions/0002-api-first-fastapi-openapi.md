# ADR 0002: API-first FastAPI/OpenAPI backend

- Status: Accepted
- Date: 2026-09-18
- Owner: Pavlo Sidelov

## Context

The local UI must later move to a remote server without rewriting business logic. Other clients and future automation need a stable contract. The owner selected FastAPI, OpenAPI v3, and Swagger.

## Decision

FastAPI is the public boundary. All UI data/actions flow through versioned `/api/v1` contracts described by generated OpenAPI. Swagger UI/ReDoc are provided. The React/TypeScript UI uses a generated client and never reads database/provider state directly.

## Consequences

- Backend contract design precedes UI coupling.
- OpenAPI validation/compatibility and generated-client checks are release gates.
- Streaming schemas need separate care because OpenAPI coverage is limited.
- Same API can support later remote and automation clients.

## Rejected alternatives

- Server-rendered framework as primary backend: duplicates FastAPI boundary.
- UI reading local files/database: destroys security and portability.
- Handwritten duplicate TypeScript DTOs: contract drift.
