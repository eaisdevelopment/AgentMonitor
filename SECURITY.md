# Security policy

## Current project status

AgentMonitor is in specification phase and has no released production version. Security reports about documentation, planned architecture, repository exposure, or future implementation are still welcome.

## Reporting

Report a suspected vulnerability privately to Essential AI Solutions Ltd at `support@essentialai.uk` with a minimal, sanitized description. Do not send passwords, API/OAuth tokens, session cookies, OTP/MFA/recovery codes, provider auth files, `.env`, raw prompts/responses/tool data, source content from monitored projects, process environments, or complete database/log/diagnostic files.

If proof requires sensitive evidence, first describe the evidence category and arrange a safe transfer method. Do not open a public issue or merge request containing exploitation details or affected-account identifiers before coordinated disclosure.

## Include safely

- affected AgentMonitor revision/version and module;
- platform and provider/CLI version without personal account identity;
- impact and prerequisites;
- minimal reproduction using only data/systems you are authorized to test;
- sanitized error codes/correlation references;
- whether active credentials, provider accounts, default profiles, running agents, or stored metadata may be affected.

## Research boundaries

- Test only systems/accounts you own or have explicit authorization to test.
- Do not extract credentials/content, intercept provider traffic, access private provider endpoints, exhaust credits, change budgets, or disrupt running agents.
- Do not use a vulnerability to access another user's data or persist access.
- Stop when a secret/content exposure or unintended side effect is demonstrated; retain only the minimum sanitized evidence.

## Response expectations

The owner will acknowledge receipt when practical, assess severity and affected scope, coordinate safe reproduction/mitigation, and agree disclosure timing. Exact response-time commitments will be established before public release.

## Security architecture

The normative controls and threat model are in [the security architecture](docs/architecture/security.md). The operational response for accidental secret exposure is in [the operations runbook](docs/operations/runbook.md).

