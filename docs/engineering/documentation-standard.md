# Documentation standard

## Documentation is part of the product

A behavior is incomplete if another developer or agent cannot understand, test, operate, diagnose, and safely change it from maintained documentation. Documentation changes in the same lifecycle as code.

## Required document types

### Product

- charter, requirements, acceptance criteria, roadmap, known limitations;
- requirement IDs remain stable after use; retired IDs are not reused.

### Architecture

- context/container flows, module ownership, dependencies, contracts, data, security, deployment;
- ADRs for consequential decisions and reversals.

### Module

Each implemented module has:

- purpose and owned invariants;
- public contracts and versions;
- allowed/forbidden dependencies;
- data/table ownership and migrations;
- use cases and error/outcome model;
- security/privacy considerations;
- test and live-verification matrix;
- operational health/diagnostics;
- known limitations and extension points.

### API

- generated OpenAPI plus human guidance for auth, errors, pagination, idempotency, units, provenance, and workflows.

### Operations

- install/config/start/stop/upgrade/backup/restore/reauth/diagnose/incident procedures;
- commands are added only after they exist and are verified. Until then procedures are marked Planned/TBD rather than invented.

### Test evidence

- red/green record, real environment/version, sanitized live report, blocked scenarios, and release matrix.

## Writing rules

- Lead with outcome and invariants.
- Distinguish Approved, Discovery, Planned, Experimental, Deferred, Unsupported, and Implemented.
- Use precise domain vocabulary from the glossary.
- Include units, timezones, null/unknown meaning, side effects, permissions, and recovery.
- Never paste secrets, tokens, raw provider responses, prompts/responses, source content, or real personal data.
- Examples are structural and labeled. They are not live evidence or demo telemetry.
- Link to the owning source document rather than duplicate policy.
- Keep diagrams text-based where possible so they are reviewable and versioned.

## Change synchronization

A change updates all affected items in one review:

- requirements/acceptance and traceability;
- module docs and contracts;
- OpenAPI/generated client;
- ADR if decision/compatibility changes;
- tests/evidence;
- operations/runbooks;
- dependency/license and threat model if applicable;
- release notes/known limitations.

## ADR discipline

- Sequential immutable number and descriptive title.
- Status: Proposed, Accepted, Superseded, or Rejected.
- Context, decision, alternatives, consequences, security/test/operation effects, and supersession link.
- Do not rewrite accepted history to hide a changed decision; add a superseding ADR.

## Review cadence

- Every merge request checks documentation impact.
- Every milestone reviews links, stale status, and requirement traceability.
- Every release exercises runbooks and verifies commands.
- Provider version changes trigger capability/document review.

## Generated documentation

Generated OpenAPI, client, SBOM, notices, schema diagrams, and coverage/evidence summaries identify their generator/source and are reproducible. Generated output is never manually patched.

## Documentation validation

CI should eventually check Markdown formatting, links, duplicate requirement IDs, ADR metadata, OpenAPI references, and prohibited secret patterns. These checks support human review; tests that merely assert exact prose are not useful.
