# Coding standards

## General principles

- Make module boundaries visible in directory structure, imports, types, migrations, and tests.
- Prefer explicit domain language over generic manager/helper/service names.
- Keep side effects at adapters and composition roots.
- Represent absence and uncertainty deliberately.
- Validate untrusted external data before it enters domain logic.
- Optimize for maintainability and diagnosis; avoid speculative abstraction.
- Do not add production behavior without requirement and test traceability.

## Naming

- Use domain terms from the glossary consistently.
- Python modules/functions/variables: `snake_case`; classes/types: `PascalCase`; constants: `UPPER_SNAKE_CASE`.
- TypeScript variables/functions: `camelCase`; types/components: `PascalCase`; true constants: `UPPER_SNAKE_CASE`.
- Boolean names begin with `is`, `has`, `can`, `should`, or an unambiguous predicate.
- IDs end in `_id`/`Id`; timestamps name the event (`observed_at`, `reset_at`), not generic `date`.
- Units appear in names when the type does not enforce them (`duration_ms`).
- Never name a mutable credential `password`/`token` in logs or views; use opaque `credential_ref`, safe prefix, or fingerprint.

## Python

- A single supported Python version baseline is pinned after dependency review; CI states it explicitly.
- Full type annotations for public and cross-module code.
- Strict static type checking; `Any`, unchecked casts, and ignore comments require written justification.
- Domain entities/value objects are independent of ORM and transport models.
- Pydantic models validate external/config/API boundaries, not every internal object by default.
- SQLAlchemy models stay in persistence adapters.
- Prefer immutable value objects for observations, money, units, provenance, IDs, and events.
- Use timezone-aware UTC datetimes only.
- Use `Decimal`/minor units for exact values; no float money.
- Async functions only for genuine async I/O; do not make the domain async.
- Cancellation and timeouts are explicit at I/O boundaries.
- Broad exception catches are allowed only at a boundary that converts them to a typed sanitized failure and preserves diagnostic causality locally.
- Never use `eval`, unsafe deserialization, shell execution, or dynamically imported untrusted provider code.

## TypeScript and React

- TypeScript strict mode and additional no-implicit/unchecked-index discipline.
- Avoid `any`; `unknown` must be narrowed through generated/runtime schema contracts.
- Backend DTOs come from the generated client, not manually duplicated types.
- React components are functional and focused on rendering/composition.
- Server state is handled through the query layer; do not mirror it into unrelated global state.
- UI-only state remains near its owner.
- Side effects live in hooks/application adapters, not render functions.
- Charts have accessible summaries and exact table alternatives.
- No raw HTML injection without a security-reviewed sanitizer and requirement.
- No direct `fetch` in feature modules.
- No secret/config values embedded at build time.

## Functions and complexity

- One clear responsibility per function/class/module.
- Prefer early validation and typed outcomes to deeply nested control flow.
- Complexity warnings require refactor or documented reason; thresholds are enforced by chosen tools after dependency admission.
- Public functions document contract, units, error/outcome behavior, and side effects where names/types are insufficient.
- Comments explain why/invariant/risk, not line-by-line syntax.
- TODOs require an issue/reference, owner, and consequence; permanent anonymous TODOs are prohibited.

## Errors and outcomes

- Expected domain/external states use typed outcomes, not generic exceptions.
- Programmer invariant violations fail clearly and are not converted to provider failure.
- User-facing errors use stable safe codes and correlation IDs.
- Preserve cause chains in local diagnostics without exposing sensitive details.
- Never conflate unavailable, unsupported, unauthenticated, unauthorized, exhausted, rate-limited, stale, malformed, and internal-error states.

## Logging

- Structured events with timestamp, severity, component/module, event name, correlation ID, and safe subject IDs.
- No string-concatenated unstructured dumps of external objects.
- No secrets, auth headers, cookies, `.env`, raw CLI output, raw provider responses, prompts, responses, tool arguments, source, or arbitrary environment values.
- Errors use safe classification plus exception type/stack only in protected local logs after redaction review.
- Account emails/display labels are avoided in logs; use internal ID and owner-friendly UI mapping.
- Log volume is bounded and rotation configured.

## Configuration and variables

- Typed settings with explicit required/optional/default status.
- AgentMonitor secret variable names use the `AGENTMONITOR_` prefix.
- Provider SDK/CLI-standard variable names remain provider-defined when required but are passed only to the owning adapter.
- Never repurpose common environment variables such as `HOME` for task data.
- Do not mutate global process environment at runtime.
- Configuration precedence is documented and deterministic.
- `.env.example` lists names and safe explanations only.

## Database

- Repository/unit-of-work boundaries are explicit.
- Transactions are short and owned by application use cases.
- Parameterized SQL only.
- Migrations own all DDL; application startup does not call implicit create-all in installed mode.
- One module owns each table and migration changes.
- Store enum/value meanings in version-compatible form.
- Enforce constraints in both domain and database when practical.
- Queries over history are bounded/paginated and indexed from real plans.
- Avoid SQLite-specific behavior in domain/repository contracts unless an ADR accepts it.

## API

- Transport models do not leak ORM entities.
- Every operation has stable `operationId`, permission, documented outcomes, and response schema.
- Use problem details for errors.
- Validate IDs, page limits, filters, and action idempotency.
- Do not start provider calls directly in request handlers.

## Security-sensitive code

- Prefer reviewed library primitives for password hashing, token generation, cryptography, and parsing.
- Compare secret verification material with safe library operations.
- Use `secrets`/OS cryptographic randomness, never non-cryptographic PRNGs.
- Path handling resolves and verifies approved roots.
- Subprocesses use argument vectors and minimal environments.
- New secret handling requires threat-model review.

## Formatting and automated checks

Tool selection is finalized through dependency admission. The baseline expects one deterministic formatter/linter per language, strict types, import-boundary enforcement, migration/schema checks, secret scanning, security static analysis, and dependency/license scanning. Developers do not hand-format around the tools or suppress checks without a documented local reason.

## Review expectations

Review behavior, invariants, security, data meaning, contracts, tests, operations, and docs—not just style. Generated files are reviewed through their source and diff summary. Large mechanical changes are separated from behavior changes.
