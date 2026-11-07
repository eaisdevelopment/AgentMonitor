# M6 official Ollama percentage comparison — 7 November 2026

- Scope: M6-A04, M6-A09, ST-OLL-004; integration verification tooling.
- Authority: [approved cloud implementation plan](../plans/integration/m6-ollama-cloud-implementation-change.md).
- Status: verifier implementation; full M6 completion is not claimed.

The SDK official Usage page exposes session/weekly percentages and purchased
credits. The existing comparison producer supported only monthly USD credits.
The product API already retained the percentage windows correctly. This change
extends verification, not provider collection or account configuration.

The pure comparison complements remaining ratios to used percentages with
integer decimal arithmetic, compares at the displayed percentage precision,
and checks exact provider reset instants. Purchased credits retain USD semantics.
Mixed representations, invalid ratios and missing reset metadata fail closed.
Two different plan representations may be compared in the same execution.

The delegated pure Red run found the expected unavailable percentage comparison
and acceptance of mixed representation fields. Green passes all 20 cases,
including the 13 existing monetary and account-pairing tests. The browser
producer now reads only principal, credit balance, percentage labels and reset
`data-time` metadata; it does not read model/request history or credentials.
Its selectors were checked against the real signed-in SDK page on 7 November.

The first current live comparison is Not Run: `official_usage_connection_unavailable`.
Both actual accounts have stale readings from 5 November and their connection
API reports `worker_unavailable`. A fresh read-only supervisor availability
check passes; the worker lock is empty, owner-only and not held, and no worker
unit remains. Recovery of the running supervisor and final comparison remain
in progress. These observations do not constitute a provider or completion pass.

No product contract, API schema, migration, dependency, licence or credential
storage change. The comparison envelope remains version 1.0.0. Local Ollama
remains deferred. Source changes are limited to the comparison producer,
pure comparison policy and its tests. Live results will be appended after
runtime recovery.
