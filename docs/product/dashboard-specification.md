# Dashboard specification

## Experience goal

The dashboard should feel like a serious spacecraft mission-control console: information-rich, calm under normal conditions, unmistakable under failure, and driven entirely by meaningful real telemetry. The theme is a design language, not decoration.

## Primary viewport and responsiveness

- Optimize primary composition for 1920x1080.
- Use a fluid grid rather than fixed pixel positioning.
- Large desktop/ultrawide: dense multi-column layout and simultaneous comparison.
- Standard desktop/laptop: prioritized panels with fewer columns.
- Tablet width: stacked operational cards and collapsible secondary detail.
- Mobile width: authentication, critical status, account availability, and alerts only; mobile operation is not a V1 deployment target.
- Do not rely on a no-scroll guarantee. Preserve critical summary and alert visibility while allowing detailed content to scroll.

## Information hierarchy

### Global command view

1. System/collector health and last global refresh.
2. Critical alert strip.
3. Capacity summary by normalized account health.
4. Provider and organization capacity matrix.
5. Active parent-agent/session tree with aggregates.
6. Near-term quota/budget exhaustion forecast.
7. Recent incidents, recoveries, and authentication actions.

### Organization view

- Aggregate capacity and spend.
- Accounts by provider and health.
- Active agents and session ownership.
- Organization-specific alert thresholds and history.

### Account view

- Identity, provider, group, plan/workspace/project relationships.
- Authentication state and re-authentication action.
- Every raw quota/budget window.
- Normalized health explanation.
- Active/historical sessions.
- Usage and forecast timelines.
- Collector source, version, precision, and failures.

### Agent/session view

- Parent/child hierarchy.
- Provider/account correlation and confidence.
- PID, parent PID, project path label, start/duration, CPU/memory.
- Observable task label, model, tokens/context, last activity, and status.
- No prompt, response, tool argument, environment-secret, or source-content display in V1.

### Alert console

- Active, acknowledged, snoozed, recovered, and historical filters.
- Severity, condition, affected resources, first/last occurrence, count, and evidence.
- Acknowledge and snooze actions.
- Link to exact source metric or collector failure.

### Authentication center

- Accounts requiring attention.
- Profile location label without credential contents.
- Last successful verification and refresh.
- Guided official re-authentication.
- Wrong-account and identity-mismatch protection.

### Diagnostics

- Application, schema, provider adapter, provider CLI, and frontend versions.
- Collector run durations, freshness, errors, and backoff state.
- Database and backup health.
- Sanitized export action.

## Visual system

- Dark mission-control theme is the initial theme.
- Use restrained neutral surfaces with semantic accent colors.
- Critical red and warning amber are reserved for state, not decoration.
- Every state has a text label and icon; never use color alone.
- Use tabular numerals for quotas, money, countdowns, and time series.
- Use gauges only for bounded values with a real denominator.
- Use line/area charts for time, stacked bars for composition, heatmaps for density, and tables for exact comparisons.
- Animate only state transitions that benefit comprehension. Respect reduced-motion preferences.
- Display `Unavailable`, `Unsupported`, `Unknown`, `Stale`, or `Experimental` explicitly instead of blank or zero.

## Real-data-only behavior

- No sample accounts or seeded metric cards.
- A new installation uses a truthful onboarding/empty state.
- Loading skeletons may represent layout but cannot display numeric placeholders resembling telemetry.
- Design and browser tests use the running backend and its real persisted state. Static visual examples, if ever needed for documentation, must be clearly watermarked as design-only and cannot serve as acceptance evidence.

## Accessibility baseline

- WCAG 2.2 AA target for the web UI.
- Full keyboard operation and visible focus.
- Semantic landmarks, headings, tables, and accessible chart summaries.
- Text alternatives for chart conclusions and exact data tables.
- Minimum target sizes and no hover-only actions.
- User-facing time uses configured timezone while exposing UTC in detail.

## UI module boundaries

- `app-shell`: routing, session bootstrap, error boundaries.
- `auth`: dashboard login/logout and session state.
- `command`: global mission-control composition.
- `organizations`: group views and settings.
- `accounts`: account identity, quota, budget, and auth detail.
- `sessions`: process/session hierarchy and detail.
- `alerts`: notification lifecycle.
- `history`: trends and exact tables.
- `diagnostics`: collectors, versions, backups, and exports.
- `settings`: configuration and API tokens.
- `shared`: generated API client, design tokens, accessible primitives, formatting, and error presentation only.

Feature modules cannot call `fetch` directly. All server state flows through the generated API client and a documented query layer.
