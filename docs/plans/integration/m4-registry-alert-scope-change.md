# Change plan: current registry alert subject scope

- Status: **Approved**; version `1.0.0`; root review 2026-09-29.
- Owner: M02; authority: existing full M4 implementation authorization.
- Requirements: `FR-ORG-003`, `FR-ACC-001/002/003`, `FR-ALERT-004`.
- Acceptance: `AC-ALERT-001/002`, `AC-TEST-001/002`.
- Contract: additive `CTR-REG-009` V1 `AlertSubjectScopeV1` and
  `ResolveAlertSubjectScopeV1(account_id) -> AlertSubjectScopeV1 | None`.

Root publishes the safe account/provider/organization/eligibility/revision
record and implements the M02 query through its existing repository port.
Read current global registry revision before and after the account projection;
reject incomplete scope or concurrent revision changes. Missing account is
None. Eligibility requires actual active lifecycle and effective monitoring.
No account names, identity, profile paths or provider data are exposed.

The genuine owner registry test first fails for the absent query and then
verifies every actual account's current membership and monitoring eligibility.
Constructed provider records are forbidden. M07 consumes only this published
query; it cannot read registry tables or accept caller-supplied membership.
No schema, dependency, authentication, default-profile or running-agent change.
Roll back the additive query coherently with its consumers, preserving data.
