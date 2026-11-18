# API usage and spend monitoring

AgentMonitor adds API usage and reported spend alongside existing Claude and Codex subscription quotas and Ollama cloud balances.

- Monitor Anthropic and OpenAI API billing organizations using separately configured administrative credentials. Existing Ollama cloud connections supply their supported usage and balance reports.
- Filter subscription and financial rows by organization and provider. Financial rows show their billing scope, reporting period, freshness, reported spend and available funds when supplied by the provider.
- Open an account to inspect exact report history, daily charts and supported breakdowns. Currency, units and reporting coverage remain visible; shared billing pools count once in compatible totals.
- View an observed daily spending rate from qualifying monetary history. An exhaustion date appears only when compatible funds and sufficient history are available; otherwise the dashboard explains the missing input.
- Refresh the stored view separately from requesting a new provider reading. Scheduled collection and bounded retries continue with the browser closed.

## Setup and limitations

API billing access is separate from Claude or ChatGPT subscription sign-in. Add the connection in the dashboard, enter the provider credential using its local hidden-input command, check access and enable monitoring. Existing working connections do not require setup again.

Anthropic and OpenAI reports cover the supported last 7 or 30 completed UTC days. Ollama reports retain their native covered periods. Reported API costs are not an invoice. Missing balances do not imply unlimited funds. An empty usage category does not establish zero monetary cost; zero cost requires a complete cost report with the applicable currency and period. Unsupported dimensions and unavailable forecasts remain explicit.

This update adds no local Ollama model or process monitoring. It does not switch, stop or restart running agents. AgentMonitor remains source-available under its Personal Use License; organizational, professional and commercial use requires a separate EAIS licence.

## Upgrade and compatibility

The database schema is `v1_0736`. The migration chain adds billing connections,
financial reports and collection outcomes, shared-pool metadata, model/remainder
semantics and financial-retention markers. Existing reports retain their original
source and context; migration does not fabricate readings or infer account setup.
Use the revision-compatible deployment procedure with a verified backup. Direct
database downgrade is unsupported, and older binaries must not open the newer
schema. Preserve a failed database for diagnosis before an approved restore or
forward fix.

Financial API additions coexist with existing subscription quota endpoints.
The published OpenAPI schema and generated frontend client travel together.
Financial history uses immutable report selection, bounded pagination and exact
currency/quantity fields. Runtime-only administrative credentials remain in the
protected local `.env`, outside report storage, exports and browser payloads.
