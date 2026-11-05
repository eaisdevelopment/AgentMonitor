# Project charter

## Document control

- Status: Approved baseline
- Product: AgentMonitor
- Owner: Pavlo Sidelov <pavlo@sidelov.com>
- Deployment stage: local single-user
- Initial platform: Linux; macOS-compatible by design
- Public release: source published under the [AgentMonitor Personal Use License 1.0](../../LICENSE) ([ADR 0016](../decisions/0016-eais-copyright-and-personal-use-license.md)); organisational and commercial use is licensed by Essential AI Solutions Ltd

## Problem statement

The owner operates multiple Claude, Codex, and Ollama subscription accounts and multiple API billing identities. Numerous coding-agent processes may be active under different accounts at the same time. Subscription quotas, API budgets, authentication health, and local agent state are fragmented across provider interfaces and terminal sessions.

The current workflow discovers exhaustion reactively: an agent stops or becomes blocked, and the owner then checks accounts manually. This loses time, obscures available capacity, and prevents informed account selection.

## Product vision

AgentMonitor will be a local mission-control system that answers, with explicit provenance and without fabricated precision:

- Which provider accounts are available now?
- Which quota or budget window is constraining each account?
- When will capacity reset?
- Which accounts are approaching exhaustion and at what rate?
- Which agents and subagents are running, waiting, blocked, or possibly stuck?
- Which account owns each observable session?
- Is monitoring data current, authoritative, derived, experimental, or unavailable?
- Which account is the best candidate for the next task?

V1 observes and advises. Later versions may launch and route agents, but process control cannot delay the monitoring dashboard.

## Users and operating scale

V1 has one administrator on one development workstation.

Current subscription inventory:

- 6 Claude accounts
- 4 Codex accounts
- 2 Ollama accounts

Expected peak locally observed agent processes:

- 10–15 Claude processes
- 5–6 Codex processes
- 2–4 Ollama processes
- approximately 19–25 total, excluding incidental helper processes

Accounts are grouped into organizations such as Org1 and Org2. An account can expose separate subscription quota, API budget, project, authentication, and session resources.

## Outcomes

1. Detect capacity risk before an agent is blocked.
2. Replace manual multi-account checking with a single trustworthy dashboard.
3. Preserve provider-specific detail while offering normalized health states.
4. Establish real historical data for forecasting and later routing decisions.
5. Observe running agents without changing the owner's current launch workflow.
6. Create a stable API and module system that community providers can extend later.
7. Make every value explainable by source, collection time, parser/adapter version, and confidence.

## Product principles

- **Truth before completeness:** unavailable is better than invented.
- **Real data from day zero:** no demo mode, placeholder metrics, or simulated provider responses.
- **Dashboard first:** routing and supervision are later products built on trustworthy observation.
- **Read-only by default:** do not disturb running agents or default provider profiles.
- **Provider fidelity:** never compress incompatible provider windows into a false universal credit number.
- **API first:** the UI is a client of the same documented API available to other consumers.
- **Modular evolution:** provider adapters and bounded modules evolve independently through contracts.
- **Local privacy:** operational metadata only in V1; no prompt, response, or source-content storage.
- **Evidence-based delivery:** no feature is complete without meaningful tests and live verification where required.

## Constraints

- Local native deployment; no Docker requirement for V1.
- Service binds to loopback in local mode.
- Dashboard requires a single-user password login.
- API clients authenticate with scoped bearer tokens.
- AgentMonitor-managed secrets use `.env`; provider OAuth credentials remain in official provider storage.
- All provider state inspection is read-only except an explicit official login flow into an AgentMonitor-managed profile.
- No near-real-time requirement; adaptive minute-scale polling is sufficient.
- History retention is 365 days.
- Dashboard-only notifications in V1. Email follows V1 validation. Native desktop notifications are not required.
- No AgentMonitor analytics or automatic crash-report uploads in V1.

## V1 non-goals

- Automatically switch or route running agents.
- Kill, restart, pause, inject commands into, or otherwise control agent processes.
- Store full prompts, responses, tool calls, source code, or arbitrary terminal output.
- Multi-user roles, SSO, or remote internet exposure.
- Messenger or native desktop notifications.
- Windows support.
- Public plugin marketplace.
- Guarantee metrics that a provider does not expose.
- Scrape private/browser endpoints without explicit opt-in and an experimental designation.

## Future direction

- Email and messenger notifications.
- Secure remote-server deployment and multi-user authorization.
- Gemini, Grok, Muse, and other agent/provider adapters.
- Optional full transcript and tool-activity capture with separate consent, encryption, and retention controls.
- Account-aware launching, routing, checkpointing, and recovery.
- Community release under terms chosen by the owner.
