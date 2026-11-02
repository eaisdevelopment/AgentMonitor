# M6 Ollama cloud balance contract — development evidence

Scope: M6-T011/M6-A04/A09, A03 contract version `OLLAMA-CLOUD-BALANCE-V1`
1.0.0 and existing M05 `CTR-CAP-001` projection. The new pure contract keeps
included and purchased USD balances, legacy percentages, UTC resets and source
period separate. Unknown values remain unknown. The period accompanies the
projection because the current capacity-window contract does not retain its
start; durable period fidelity is still unfinished.

Red: pure contract tests failed because the contract module did not exist.
After the first implementation, two tests exposed a false-exhaustion risk:
credit pools were independently marked constraining. They were corrected and
both monetary pools now remain non-constraining until their combined semantics
are supported. Legacy session/week windows remain constraining. The Ollama
[balance API](https://docs.ollama.com/api/balance) describes period endpoints
and provider variants; no example response was replayed or used as a fixture.

Green after formatting: 63 pure contract, capacity and collection-control tests
passed; Ruff passed for the new contract and test. No dependency, schema
migration, key, provider profile, live account or provider request was added.
This is not cloud collection or M6 completion. Live provider comparison,
credit exhaustion semantics, period persistence, history, alerts, API/UI and
sharing provenance remain open.
