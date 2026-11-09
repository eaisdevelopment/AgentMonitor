# ADR 0016: Essential AI Solutions copyright and personal-use licence

- Status: Accepted
- Date: 2026-11-05
- Deciders: Pavlo Sidelov (owner)
- Requirements: none; project terms and copyright notice
- Supersedes: [ADR 0011](0011-copyright-and-dependency-licenses.md) for the copyright holder and project terms only
- Superseded by: none

## Context

[ADR 0011](0011-copyright-and-dependency-licenses.md) recorded AgentMonitor as
Copyright (c) 2026 Pavlo Sidelov, all rights reserved, with no licence granted.

On 2026-11-05 the repository adopted the
[AgentMonitor Personal Use License 1.0](../../LICENSE): individuals may use
AgentMonitor free for personal, non-commercial use, and any other use (by or
for an organisation, client work, resale, redistribution or a hosted service)
needs a separate written licence from Essential AI Solutions Ltd (EAIS).
EAIS also lists AgentMonitor as one of its products on essentialai.uk.

Those licences are granted by EAIS, so EAIS should hold the rights it grants.

## Decision drivers

- The party that grants commercial licences must hold the copyright or an
  express right to license it.
- Licensing and security enquiries should reach a company mailbox rather than a
  personal address.
- Free personal use must stay available.

## Considered options

### Option A: copyright stays with Pavlo Sidelov; EAIS licenses as agent

Needs a separate written licensing agreement between the owner and EAIS, and
leaves two parties named in every notice.

### Option B: Essential AI Solutions Ltd holds the copyright

One rights holder, which also grants the commercial licences. Needs a written
assignment from Pavlo Sidelov to EAIS.

### Option C: Apache-2.0

Considered and rejected on 2026-11-05: it would let anyone use, resell or host
AgentMonitor without a licence from EAIS.

## Decision

Option B. Current copyright notices name
**Essential AI Solutions Ltd <support@essentialai.uk>**, and the project terms are
the AgentMonitor Personal Use License 1.0. Vulnerability reports go to
`support@essentialai.uk` (see [SECURITY.md](../../SECURITY.md)).

The dependency admission gate in ADR 0011 is unchanged.

## Consequences

### Positive

- One rights holder grants every licence beyond personal use.
- Copyright, licensing and security enquiries reach one company mailbox,
  `support@essentialai.uk`.

### Negative and trade-offs

- A notice does not transfer copyright by itself. A written copyright
  assignment from Pavlo Sidelov to Essential AI Solutions Ltd must be signed
  before EAIS grants its first commercial licence.

### Neutral or follow-up

- Accepted ADRs, approved plans and evidence records written before this date
  keep the notice they were approved with; they are historical records. This
  ADR governs from 2026-11-05.
- Decision-owner and approver fields still name the individual who made each
  decision; they are roles, not copyright notices.
- External contributions still need a contribution and copyright policy before
  they are accepted (ADR 0011).

## Compatibility and migration

No API, event, provider, database, configuration or deployment impact. Only
`LICENSE`, `README.md`, `SECURITY.md`, the V1 specification header, the project
charter's public-release field, the dependency and license policy goal, the
roadmap's later-work list and the ADR index change.

## Verification

- `LICENSE`, `README.md` and the V1 specification name Essential AI Solutions
  Ltd as the copyright holder; `SECURITY.md` names `support@essentialai.uk`.
- `python3 tools/automation/run.py AUTO-DOCS-CHECK` passes.
- Reconsider if EAIS stops licensing AgentMonitor or the project terms change.
