# M7 account resource layout and organization selection

Status: bounded T002/T011 increment installed and published at `edbe2fc`.
M7 remains open. Owning producer M02,
API P01, UI P02; root integrates the approved focused plan 1.1.0.

Requirements: FR-ACC-001/002/004, FR-ORG-001/002, FR-BUDGET-001;
acceptance AC-UI-002/003/006, AC-TEST-001/003, M7-A01/A07.
Existing scenario families: M7-REG-DB/HTTP, M7-UI owner setup and account detail.

## Behavior and contract

- CTR-REG-002 AccountViewV1 1.1.0 adds nullable
  `has_active_subscription_resource`. M02 uses an indexed EXISTS in the same
  account read, including list and mutation responses. It is not truncated by
  the separate resource-list bound. True describes membership, not identity,
  authentication, effective monitoring or current quota.
- P01 adds the optional field to the existing account response and regenerates
  OpenAPI/client artifacts. Unknown/omitted remains compatible. No new endpoint,
  table, database migration, dependency or license change.
- P02 shows subscription sections when an active subscription resource exists,
  even for API-origin accounts; absent/unknown retains creation-intent fallback.
  Both detail and account-list product labels use this policy. Existing Ollama
  cloud controls and API billing sections remain independent.
- An assigned organization with an unloaded name is Organization unavailable,
  never Ungrouped. The current assignment remains selectable as a disabled
  placeholder. Both create and assignment forms expose bounded Load more
  organizations through the existing cursor API. Failed/inconsistent pages
  retain choices; old requests cannot append after a new account load.
- The assignment select retains explicit owner selection across option changes.
  Loading its previously missing organization cannot silently select Ungrouped.

No provider/profile access, provider mutation or live owner configuration is
performed. Browser metadata mutations use an isolated actual IAM/SQLite service;
they do not create provider identities or telemetry. Retained-resource checking
uses a protected private copy of genuine registry data. No keys or provider
response bodies are read into test output.

## Meaningful Red and Green

- Recorded backend Red: the real pending-account HTTP response lacked the field
  (`None is False`), and the private genuine registry subscription read lacked
  it (`None is True`). Green: 286 registry/domain and focused real integration
  tests passed, including actual retained-resource presence and no-resource
  registration/reopen/HTTP.
- Pure UI Red: API origin plus an active subscription still returned API-only
  (`true !== false`); missing assigned organization returned Ungrouped rather
  than Organization unavailable. Green: `account-resource-layout.mjs` passed.
  This suite is included in the existing canonical M7 presentation selection.
- Actual built-browser Red: `account_organization_pages` failed because no
  continuation control existed. First Green loaded all actual isolated groups.
  Strengthened Red assigned an isolated account to a later-page group and
  failed specifically at `account_organization_retention` after pagination.
  The controlled selector addresses that observed failure.
- Installed read-only Red at `cd4f566`: `verify_setup.mjs` failed with
  `account_resource_classification_missing`; authentication, revision, Overview
  and setup-form checks passed, with zero mutation requests. Its extended
  post-install check requires the real field and actual subscription sections.

Independent P02 review identified the selection-reset defect; the test reproduced
it before correction. Independent M02 review found no blocking query/contract
regression. These reviews do not replace executable checks.

The exact API-origin-to-subscription owner transition has not been induced on
live accounts. Pure policy proves that combination, real metadata proves the
producer, isolated API-only pages and real installed subscription pages prove
their respective boundaries. Do not describe this as a newly observed provider
login/transition or close all T002/T011 lifecycle acceptance from it. Remaining
source lifecycle, history and monetary evidence stay in the ticket catalog.

## Commands and handoff

- Focused real integration/registry: shared admitted pytest, configuration
  `backend/pyproject.toml`, no-skip plugin, `backend/tests/registry`,
  `backend/tests/integration/registry/test_billing_account_intent.py`,
  `backend/tests/integration/api/test_billing_enrollment_http.py`,
  `backend/tests/integration/capacity/test_budget_overview_real_metadata.py`.
- Pure presentation: `node --experimental-strip-types frontend/tests/pure/account-resource-layout.mjs`.
- Built owner controls: existing M7 runner `--lane browser --check owner_pool_controls`.
- Installed setup/subscription evidence: `node frontend/tests/browser/m7/verify_setup.mjs <installed-revision>`;
  concurrent regression: existing M7 runner `--lane browser --check overview --expected-revision=<installed-revision>`.

Files: M02 contract/SQLite account reads; P01 account schema/router and generated
OpenAPI/client; AccountPage/provider presentation; focused backend, pure UI and
existing browser tests; M7 runner presentation inventory and module handoff.
The accompanying planning reconciliation changes delivery instructions only.
Schema remains v1_0734. Rollback uses the existing same-schema selected updater;
older clients ignore the optional field. No historical reports are rewritten.


## Local verification result

The strengthened real built-browser `owner_pool_controls` selection passed after
fixing selection retention. It covers more than 200 real isolated organization
records, the later-page assignment before/after loading and saving, API-only
layout, existing pool controls, responsive layout and full-list sorting. It
uses the existing runner and real IAM/HTTP/SQLite, with no provider telemetry.

`AUTO-QUALITY` passed at 05:41 UTC: formatting/lint, type checks, module boundaries,
compatible generated OpenAPI/client (98 operations), locked frontend inputs and
production build. Planning, documentation and synchronized baseline checks also
passed. These results do not cover full monetary M7 acceptance or publication.

Canonical M7 pure selection also passed: 737 backend policy tests and twelve
presentation suites, including the new resource-layout policy.


## Installed and public result

Implementation revision `edbe2fc96a6c561d81a5a5c04f9695aa22e75959` was installed
through the existing selected current-schema updater. It passed readiness and
restored the original restart policy. The user service was active and the
dashboard returned HTTP 200. Schema remains v1_0734.

The exact-revision canonical Overview selection ran four actual metadata checks
and concurrent authenticated Overview/setup/cloud probes. All three probes
passed at 05:45:43 UTC, including the new resource field and actual subscription
page in setup. They performed no configuration mutations. The broader selection
correctly exited 3: full monetary Overview remained Not Run with
`m7_monetary_overview_required`. No claim of full M7 completion is made.

Push preflight passed. `git push github HEAD:main` succeeded and `git ls-remote
github refs/heads/main` returned the exact implementation revision above.
The staged scan had two generic-key findings; both were exact old/new generated
OpenAPI artifact checksums verified against Git artifact bytes, with no unresolved
finding or suppression. A documentation-only successor records this verification;
it does not change the installed implementation.

Next independent work is T002/T010/T011 source-scope/lifecycle controls and
original-scope history discovery. T002/T011 remain in progress. The fixed full
M7 provider, monetary, analysis, recovery and release scope is unchanged.
