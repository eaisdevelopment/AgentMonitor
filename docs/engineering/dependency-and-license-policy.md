# Dependency and license policy

## Goal

AgentMonitor is published under the [AgentMonitor Personal Use License 1.0](../../LICENSE) ([ADR 0016](../decisions/0016-eais-copyright-and-personal-use-license.md)), and Essential AI Solutions Ltd licenses other use. Dependencies must permit lawful local use and future distribution, have acceptable security/maintenance risk, and justify their operational cost.

## Admission gate

No direct dependency enters a manifest until its module plan documents:

- exact purpose and why standard-library/existing code is insufficient;
- upstream project and canonical package identity;
- current license from the upstream license file;
- transitive dependency/license inventory;
- maintenance activity, release cadence, security policy, and ownership;
- supported platforms/runtimes;
- binary/native components and supply-chain implications;
- network/telemetry behavior;
- size/performance impact;
- pinning/update/removal strategy;
- alternatives considered;
- approving reviewer/date.

## License classes

### Normally admissible after verification

- MIT
- BSD-2-Clause / BSD-3-Clause
- ISC
- Apache-2.0, with NOTICE/attribution obligations preserved

### Explicit owner approval required

- GPL, LGPL, AGPL, MPL, EPL, or other copyleft licenses;
- dual/commercial licenses;
- source-available/non-compete/field-of-use licenses;
- packages with unclear, missing, custom, or conflicting metadata;
- dependencies that impose branding, hosted-service, or redistribution constraints.

License compatibility is reviewed for the actual distribution method. This document is engineering policy, not legal advice.

## Initially shortlisted components

Verified from canonical upstream sources on 2026-09-18, subject to recheck at pinning time:

| Component | Role | Upstream license |
|---|---|---|
| FastAPI | HTTP/OpenAPI backend | MIT |
| SQLAlchemy | persistence | MIT |
| React | UI | MIT |
| Vite | frontend build | MIT; bundled notices apply |
| TanStack Query | server-state client | MIT |
| Radix Primitives | accessible primitives | MIT |
| Tailwind CSS | styling candidate | MIT |
| Apache ECharts | charts | Apache-2.0 |
| Pydantic | validation/settings | MIT |
| Vitest | frontend pure tests | MIT |
| Playwright | real browser tests | Apache-2.0 |

This table approves no version and omits transitive review. Each package still passes the admission gate before installation.

## Locking and provenance

- Commit lockfiles for Python and JavaScript environments.
- Pin direct dependencies and resolve reproducibly.
- Prefer official package registries and verified release provenance.
- Avoid git-branch dependencies, unreviewed forks, install scripts, and opaque binaries.
- Review lockfile changes as code changes.
- Produce an SPDX or CycloneDX SBOM for releases.
- Generate third-party notices, including bundled frontend notices.
- Retain dependency/license scan output as release evidence.

## Continuous controls

- Automated vulnerability and license scanning in GitLab CI.
- Scheduled dependency review, not blind auto-merge.
- Security updates use the SDLC with proportional urgency.
- Detect upstream license changes before upgrade.
- Remove unused dependencies promptly.
- Document accepted vulnerabilities with owner, rationale, containment, and expiry; indefinite silent ignores are prohibited.

## Dependency budget

Prefer a small stable dependency graph. A convenience package is not justified when a clear, safe implementation is trivial. Conversely, do not implement cryptography, password hashing, complex standards, or security parsers in-house to avoid a sound dependency.

Frontend component collections are imported selectively. Charting is tree-shaken where supported. Provider SDKs are adapter-local and optional when direct documented HTTP contracts are safer/smaller.

## External services and SaaS

Adding Sentry, analytics, hosted databases, feature flags, email, or other external services is both a dependency and data-flow change. It requires owner approval, privacy/security review, ADR, and updated runbook. AgentMonitor has no external analytics/crash-reporting service in V1.

## Public-release preparation

Before public distribution:

- owner chooses AgentMonitor's project license/terms;
- legal/engineering review confirms dependency compatibility;
- LICENSE, NOTICE, SBOM, and third-party notices are complete;
- trademarks/package names are reviewed;
- binary/source bundles are scanned for secrets and excluded provider artifacts;
- contribution and copyright-assignment policy is established before accepting external contributions.
