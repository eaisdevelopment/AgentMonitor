# ADR 0007: Secret and provider-profile model

- Status: Accepted
- Date: 2026-09-18
- Owner: Pavlo Sidelov

## Context

The owner wants AgentMonitor-managed secrets in `.env`. Provider OAuth credentials have official refresh/storage behavior and should not be copied. Multiple accounts require isolated monitored profiles without disturbing the owner's mutable default login workflow.

## Decision

Store AgentMonitor-managed secrets in a protected gitignored `.env`. Keep provider OAuth credentials in official provider-managed storage referenced opaquely. Store dashboard password/API token verification material as hashes. AgentMonitor never modifies default profiles; managed profiles use official interactive login/reauth flows.

## Consequences

- `.env` requires strong file permissions, redaction, and rotation runbook.
- Provider profile isolation must be live verified per provider/version.
- Backups/exports exclude `.env` and provider profiles.
- Future remote deployments may replace `.env` with a secret-manager adapter.

## Rejected alternatives

- Copy provider OAuth tokens into `.env` or SQLite.
- Store app secrets in plaintext database settings.
- Repeatedly log the default CLI profile in/out for monitoring.
