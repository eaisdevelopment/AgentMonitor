# ADR 0006: Read-only operational metadata first

- Status: Accepted
- Date: 2026-09-18
- Owner: Pavlo Sidelov

## Context

The dashboard runs beside up to 25 active agents. The owner wants local-process/session insight without changing launch workflow, but V1 privacy excludes full prompts/responses/tool content and V1 safety excludes process control.

## Decision

V1 performs read-only process and allowlisted provider metadata inspection, stores operational metadata only, and never injects input/signals or controls processes. Default profiles are immutable. Full content capture and routing/supervision are separate future architectures.

## Consequences

- Some task/model/account data may remain Unknown when providers do not store safe metadata.
- Account correlation requires evidence or owner confirmation.
- Parsers need strict field allowlists and versioning.
- Future supervisor work cannot be smuggled into V1 adapters.

## Rejected alternatives

- Terminal injection or process attachment.
- Reading process memory/environment broadly.
- Storing complete local transcripts for convenience.
- Requiring a launcher before the dashboard is usable.
