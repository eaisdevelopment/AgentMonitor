# ADR 0011: Copyright and dependency licensing

- Status: Accepted
- Date: 2026-09-18
- Owner: Pavlo Sidelov
- Superseded by: [ADR 0016](0016-eais-copyright-and-personal-use-license.md) for the copyright holder and project terms only; the dependency admission gate below still applies

## Context

The project is local/private first and may later be released free to the community. The owner retains all rights now and wants dependency licenses reviewed before inclusion.

## Decision

AgentMonitor is currently Copyright (c) 2026 Pavlo Sidelov <pavlo@sidelov.com>, all rights reserved. No open-source license is granted. Normally admit verified MIT/BSD/ISC/Apache-2.0 dependencies; other/unclear licenses require explicit owner approval. Generate lockfiles, SBOM, and third-party notices. Choose public project terms only before release.

## Consequences

- Public viewing would not automatically grant use/modification/distribution rights.
- External contributions should not be accepted before a contribution/copyright policy exists.
- Dependencies remain usable in proprietary distribution only when obligations are satisfied.
- Upstream licenses must be rechecked at version pin/upgrade time.

## Rejected alternatives

- Selecting Apache-2.0 or AGPL for AgentMonitor now.
- Adding libraries based only on popularity/convenience.
- Deferring license checks until release.
