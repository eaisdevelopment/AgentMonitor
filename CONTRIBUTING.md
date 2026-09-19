# Contributing to AgentMonitor

AgentMonitor is currently a private, all-rights-reserved specification project. Possession of the source does not grant redistribution or relicensing rights. Contribution workflow and licensing may change before a community release.

## Before proposing work

1. Read [AGENTS.md](AGENTS.md), the [documentation index](docs/README.md), and the [AgentMonitor engineering skill](.agents/skills/agentmonitor-engineering/SKILL.md).
2. Identify requirement/acceptance IDs and exactly one primary owning module.
3. Confirm the relevant discovery is complete and the module/change plan is approved.
4. Confirm public contract versions, permitted paths/imports, and live-test needs.
5. Do not begin implementation merely because a requirement or roadmap item exists.

## Development policy

- Follow the [SDLC](docs/engineering/sdlc.md), [coding standards](docs/engineering/coding-standards.md), and [review checklists](docs/engineering/review-checklists.md).
- Use strict red-green-refactor TDD and the [real-system testing policy](docs/engineering/testing-strategy.md).
- Do not introduce mocks, fakes, recorded provider responses, demo accounts, seeded telemetry, or placeholder metrics.
- Keep module ownership and dependency direction intact. Propose contract changes before crossing a boundary.
- Treat migrations, configuration, OpenAPI, internal events, and provider protocols as versioned contracts.
- Add no dependency before the [dependency and license review](docs/engineering/dependency-and-license-policy.md).
- Update requirements, traceability, contracts, runbooks, risks, and evidence with behavior changes.

## Sensitive systems and data

Never commit, paste, upload, or include in artifacts:

- `.env` or any secret/token/password/OTP/MFA value;
- provider OAuth/auth files or raw API/CLI responses;
- account email/identity unless explicitly approved and masked;
- prompts, responses, tool activity/arguments, source content, arbitrary process environments, or terminal transcripts;
- live database, logs, diagnostics, screenshots, or test evidence not explicitly sanitized.

Do not log out, rewrite, relocate, or modify a default provider profile. Do not interrupt/control running agent processes in V1. The owner performs interactive provider authentication.

## Change proposal and review

Use the templates under [docs/templates](docs/templates/README.md). A reviewable change identifies:

- requirement, acceptance, plan, module, and contract versions;
- scope/non-goals and file ownership;
- architecture/API/data/configuration/migration impact;
- security/privacy/license/operations impact;
- meaningful Red, Green, and refactor evidence;
- real database, API, built-browser, platform, and provider evidence as applicable;
- every Failed, Blocked, and Not Run scenario;
- documentation and exact integration/rollback steps.

Branch, commit-message, merge-request, and release commands will be finalized by the repository-foundation plan and documented only after they exist. Do not invent commands or bypass protected-branch/CI policy.

## Reporting security issues

Follow [SECURITY.md](SECURITY.md). Never place a credential or sensitive provider artifact in an issue, merge request, commit, chat, or email body.

