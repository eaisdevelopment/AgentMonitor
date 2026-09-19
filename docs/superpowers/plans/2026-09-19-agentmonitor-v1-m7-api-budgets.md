# AgentMonitor V1-M7 API Budgets Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver real Anthropic, OpenAI, and supported Ollama API usage, cost, credit, limit, budget, breakdown, and forecast views with exact arithmetic and authoritative reconciliation.

**Architecture:** A01, A02, and A03 collect provider-specific facts and emit only M05-owned `CTR-CAP-002` inputs through M03/M04. M05 owns exact arithmetic, immutable history, projections, and forecasts; P01 exposes those ports under `/api/v1`, and P02 renders only the generated client.

**Tech Stack:** Python, FastAPI/OpenAPI 3, real file-backed SQLite/Alembic, approved provider HTTPS interfaces or official tools, React/TypeScript, generated API client, and a real supported browser.

**Spec:** `docs/product/v1-specification.md`

## Global Constraints

- Milestone `V1-M7`; Epic `EPIC-BUDGET-01`; requirements `FR-BUDGET-001..006`; acceptance contributions `AC-LIVE-004/005/007`, `AC-UI-002..006`, `AC-HIST-001`, `AC-OPS-003/006`, and `AC-TEST-001..006`.
- Before any Red test, require Approved `PLAN-M05`, applicable A01/A02/A03, P01/P02 plans and contracts, admitted dependencies, `PG-FULL`, a collision-free start packet, and reserved owner-controlled live accounts. `AUTO-PLAN-CHECK` alone is not implementation authority.
- Follow the detailed designs and scenarios in `docs/plans/modules/m05-capacity/plan-v1.md`, `docs/plans/adapters/claude/plan-v1.md`, `docs/plans/adapters/codex/plan-v1.md`, `docs/plans/adapters/ollama/plan-v1.md`, `docs/plans/api/fastapi-boundary/plan-v1.md`, `docs/plans/ui/react-dashboard/plan-v1.md`, and `docs/plans/integration/v1-plan.md`; this execution plan does not redefine them.
- Real external boundaries permit no mocks, fakes, stubs, emulators, recordings, demo accounts, inserted/seeded telemetry, sample values, or constructed I/O inputs. Constructed values are limited to pure no-I/O domain tests.
- Money uses `CTR-COMMON-003` exact decimal strings or approved integer minor units plus currency. Reject Python `float`, JSON/JavaScript coercion, and SQLite floating storage.
- Preserve exact distinctions among zero, missing, Unknown, Unsupported, Unavailable, Withheld, Stale, and authentication-required. Subscription and API resource pools, mixed currencies, periods, scopes, and overlapping rollups never merge.
- Never read or retain credential values, reversible API-key identifiers, raw provider bodies, prompts, responses, source content, or arbitrary environments. Provider capabilities are enabled only for the exact M0-approved provider/product/role/version/source tuple.
- The UI imports `frontend/src/generated/api/index.ts` only through `frontend/src/shared/api/client.ts`; domain modules remain free of FastAPI, SQLAlchemy, provider, OS, and UI imports.
- Shared contracts, migration head, composition, OpenAPI, generated client, locks, and central evidence files have one allocated writer. M3 has already created and shared the complete frozen `v1_0500` through `v1_0504` M05 chain, including budget/usage tables. M7 verifies and uses those migrations without editing them or creating a competing revision.
- Each Story retains behavioral Red, minimum Green, refactor evidence, exact files, and every Failed/Blocked/Not Run row. Missing credentials or setup is Blocked, not Red.

---

## File map and public seams

| Unit | Exact paths | Published/consumed interface |
|---|---|---|
| M05 budget core | `backend/src/agentmonitor/contracts/capacity_v1.py`, `backend/src/agentmonitor/modules/capacity/domain/budgets.py`, `backend/src/agentmonitor/modules/capacity/application/budgets.py`, `backend/src/agentmonitor/modules/capacity/ports/budgets.py`, `backend/src/agentmonitor/adapters/persistence/capacity/sqlite/budgets.py` | Produces `ProviderUsageInputV1`, `ProviderCostInputV1`, `ProviderBudgetInputV1`, `CTR-CAP-002/004/006/007` ports; uses the immutable M3-created `v1_0500` budget/usage and `v1_0501` receipt/projection tables |
| Provider lanes | `backend/src/agentmonitor/adapters/providers/claude/anthropic_api/client.py`, `backend/src/agentmonitor/adapters/providers/claude/anthropic_api/mapping.py`, `backend/src/agentmonitor/adapters/providers/codex/openai_api/client.py`, `backend/src/agentmonitor/adapters/providers/codex/openai_api/mapping.py`, `backend/src/agentmonitor/adapters/providers/ollama/api/client.py`, `backend/src/agentmonitor/adapters/providers/ollama/api/mapping.py` | Consume approved M03/M04 boundary contracts and M05 input DTOs |
| HTTP/client | `backend/src/agentmonitor/api/v1/schemas/capacity.py`, `backend/src/agentmonitor/api/v1/routers/capacity.py`, `contracts/openapi/agentmonitor-v1.json`, `frontend/src/generated/api/index.ts` | `capacity_list_budgets_v1`, `capacity_get_budget_v1`, `capacity_list_usage_breakdowns_v1`, `capacity_get_account_api_budget_v1` |
| UI | `frontend/src/features/accounts/BudgetPanel.tsx`, `frontend/src/features/accounts/useBudgets.ts`, `frontend/src/features/history/BudgetHistory.tsx` | Generated operations only; no client-side domain calculations |
| Integration | `backend/tests/integration/release/test_api_budget_verticals_live.py`, `docs/test-evidence/capacity/v1-m7-api-budget-handoff.md` | Candidate-bound `INT-BUD-001..012` and live status matrix |

M05's query surface is exactly `GetBudgetV1`, `ListBudgetsV1`, `ListUsageBreakdownsV1`, and `GetAccountApiCapacityV1`. Collection commits use `CommitCapacityCollectionOutcomeV1(command) -> CapacityCommitReceiptV1`; adapters never write M05 tables, and HTTP handlers never call adapters or repositories.

### Task 1: ST-BUDGET-001 — Build the exact M05 budget core

**Epic:** `EPIC-BUDGET-01`

**Files:**
- Modify: `backend/src/agentmonitor/contracts/capacity_v1.py`
- Create: `backend/src/agentmonitor/modules/capacity/domain/budgets.py`
- Create: `backend/src/agentmonitor/modules/capacity/application/budgets.py`
- Create: `backend/src/agentmonitor/modules/capacity/ports/budgets.py`
- Create: `backend/src/agentmonitor/adapters/persistence/capacity/sqlite/budgets.py`
- Create: `backend/src/agentmonitor/adapters/providers/claude/anthropic_api/client.py`
- Create: `backend/src/agentmonitor/adapters/providers/claude/anthropic_api/mapping.py`
- Create: `backend/tests/live/claude/test_anthropic_api_budget_live.py`
- Create: `backend/tests/capacity/test_budget_values.py`
- Create: `backend/tests/integration/capacity/test_budget_repository_live.py`

**Interfaces:** Consumes `ExactQuantityV1`, `FieldAvailabilityV1`, `ObservationProvenanceV1`, M02 resource/scope IDs, M04 run/fencing metadata, PLAN-DB UoW, and one M0-approved Anthropic billing source. Produces the `CTR-CAP-002/004/006/007` types, four budget query ports, and the first real provider-to-SQLite budget slice.

**Contracts:** Produces `CTR-CAP-002/004/006/007`; consumes `CTR-COL-002/003/006/007`, `CTR-COMMON-001..004/006/007`, `CTR-DB-001/002`, `CTR-EVT-001`, `CTR-PROV-002/003/004/008`, and `CTR-REG-001/002/005/007/010`, all at V1.

**Traceability:** `FR-BUDGET-001..005`; `M05-PURE-043..058`; `M05-DB-001/008..016/022/023/030..036`; `CLA-NET-001..010`, `CLA-LIVE-006/007`; `AC-HIST-001`, `AC-LIVE-004/005/007`, `AC-V1-004`, `AC-TEST-005`.

- [ ] **Step 1: Write failing pure tests** proving absent limits do not derive spend, soft/hard limits and credits remain distinct, reset is never inferred, unsupported dimensions create no rows, safe key IDs are closed, floats/overflow/mixed currency are rejected, and subscription/API pools do not merge.

```python
def test_float_money_is_rejected() -> None:
    with pytest.raises(InvalidExactMoney):
        ExactMoneyV1.from_contract(currency="USD", value=12.5)

def test_absent_limit_keeps_available_spend_unknown() -> None:
    result = classify_budget_fields(
        spend=ExactField.known("12.50", unit="USD"),
        hard_limit=ExactField.unknown(),
        provider_available=ExactField.unknown(),
    )
    assert result.available_spend.state is FieldAvailabilityV1.UNKNOWN
```

- [ ] **Step 2: Run Red:** `python3 -m pytest backend/tests/capacity/test_budget_values.py -q`

Expected: FAIL on missing/incorrect M05 behavior, not dependency or syntax setup.

- [ ] **Step 3: Implement the minimum immutable domain/types** with exact string/minor-unit arithmetic, closed dimensions, explicit field states, value-kind/derivation metadata, interval compatibility, pool separation, and `insufficient_input` forecasts. Update `capacity_v1.py` only through its allocated writer.

- [ ] **Step 4: Run Green/refactor:** `python3 -m pytest backend/tests/capacity/test_budget_values.py -q && python3 tools/automation/run.py AUTO-QUALITY`

Expected: pure scenarios pass and meaningful exact-money/pool/dimension mutants are killed; unavailable mutation automation remains Blocked and prevents Story completion.

- [ ] **Step 5: Write the real provider-to-SQLite Red test** that applies the full Alembic chain to a temporary file, invokes the production Anthropic budget lane with the reserved real owner-controlled packet, sends that real typed outcome through `CommitCapacityCollectionOutcomeV1` twice, closes/reopens SQLite, and asserts one immutable observation/receipt plus exact `GetBudgetV1` and `GetAccountApiCapacityV1` results. Direct row insertion and constructed I/O inputs are forbidden.

```python
def test_real_anthropic_budget_survives_sqlite_reopen(real_anthropic_packet, real_budget_stack) -> None:
    outcome = real_budget_stack.anthropic.collect_api_budget(real_anthropic_packet)
    receipt = real_budget_stack.capacity.commit(outcome)
    replay = real_budget_stack.capacity.commit(outcome)
    reopened = real_budget_stack.reopen()
    assert receipt.observation_ids == replay.observation_ids
    assert reopened.budgets.get(receipt.budget_ids[0]).provenance.source_id == outcome.provenance.source_id
    assert_authoritative_reconciliation(reopened.budgets.for_account(outcome.account_id), owner_comparison(real_anthropic_packet))
```

- [ ] **Step 6: Run Red:** `python3 -m pytest backend/tests/live/claude/test_anthropic_api_budget_live.py backend/tests/integration/capacity/test_budget_repository_live.py -q`

Expected: FAIL because the Anthropic client/mapper and repository/application-commit path are missing. Missing credentials, provider access, or owner comparison is Blocked and prevents this Story from reaching Green.

- [ ] **Step 7: Implement the minimum Anthropic lane and persistence against the immutable allocated schema.** Use only the M0-approved host/operation/role with bounded pages/body/deadline and discard raw bodies. Map budget definitions/observations/measures and usage dimensions to the already-shared `v1_0500` tables and receipts/current projections to the already-shared `v1_0501` tables. Assert `backend/migrations/catalog.toml` digests match the M3 handoff before repository use; never edit those migrations or create another revision. Same run/schema/generation/digest returns the original receipt; a different digest conflicts; failed/unsupported collection never writes or freshens a fact.

- [ ] **Step 8: Run Green:** `python3 -m pytest backend/tests/live/claude/test_anthropic_api_budget_live.py backend/tests/integration/capacity/test_budget_repository_live.py -q && python3 tools/automation/run.py AUTO-MIGRATE`

Expected: real file SQLite and supported schema paths pass; unavailable migration automation is reported Blocked.

- [ ] **Step 9: Commit:**

```bash
git add backend/src/agentmonitor/contracts/capacity_v1.py backend/src/agentmonitor/modules/capacity/domain/budgets.py backend/src/agentmonitor/modules/capacity/application/budgets.py backend/src/agentmonitor/modules/capacity/ports/budgets.py backend/src/agentmonitor/adapters/persistence/capacity/sqlite/budgets.py backend/src/agentmonitor/adapters/providers/claude/anthropic_api backend/tests/live/claude/test_anthropic_api_budget_live.py backend/tests/capacity/test_budget_values.py backend/tests/integration/capacity/test_budget_repository_live.py
git commit -m "feat(capacity): add real Anthropic API budget slice"
```

### Task 2: ST-BUDGET-002 — Complete OpenAI and Ollama provider API lanes

**Epic:** `EPIC-BUDGET-01`

**Files:**
- Create: `backend/src/agentmonitor/adapters/providers/codex/openai_api/client.py`
- Create: `backend/src/agentmonitor/adapters/providers/codex/openai_api/mapping.py`
- Create: `backend/tests/adapters/providers/codex/test_openai_api_live.py`
- Create: `backend/src/agentmonitor/adapters/providers/ollama/api/client.py`
- Create: `backend/src/agentmonitor/adapters/providers/ollama/api/mapping.py`
- Create: `backend/tests/live/ollama/test_ollama_api_budget_live.py`

**Interfaces:** The OpenAI and Ollama lanes consume their exact M0 capability/role/source rows, M03 outcomes/provenance, M04 deadline/request budgets, and M05 input DTOs. Each produces evidenced typed inputs or explicit Unsupported/Unavailable outcomes and does not alter the already-proven Anthropic lane.

**Contracts:** Consumes `CTR-BOUNDARY-001/002`, `CTR-COL-002/003/006`, `CTR-COMMON-001/002/004/006/007`, `CTR-PROV-001..008`, and the M05 `CTR-CAP-002` input DTOs, all at V1.

**Traceability:** `FR-BUDGET-001..006`, `FR-COL-003..008`; `CDX-OAI-001..010`; `OLL-NET-001..010`, `OLL-LIVE-007/008`; `M05-LIVE-007..013`; `AC-LIVE-004/005/007`, `AC-OPS-003/006`.

- [ ] **Step 1: Reserve separate OpenAI and Ollama live packets** containing only safe aliases, role/source/version tuples, request limits, comparison method, evidence destination, and owner checkpoint. Stop any lane missing M0 evidence, an official safe mechanism, least-privilege role, or a real account.

- [ ] **Step 2: Write failing live tests** invoking each production adapter and asserting exact scope/interval/currency, pagination completeness, provenance, request bounds, authoritative comparison, no raw/secret fields, and explicit Unsupported where applicable.

```python
def test_openai_cost_reconciles_without_float(real_openai_packet) -> None:
    observed = production_codex_adapter().collect_openai_api_budget(real_openai_packet)
    assert not isinstance(observed.cost.amount, float)
    assert_authoritative_reconciliation(observed, owner_comparison(real_openai_packet))
    assert_no_raw_or_secret_fields(observed)
```

- [ ] **Step 3: Run Red at T6:**

```bash
python3 -m pytest backend/tests/adapters/providers/codex/test_openai_api_live.py -q
python3 -m pytest backend/tests/live/ollama/test_ollama_api_budget_live.py -q
```

Expected: each authorized lane FAILS for missing behavior. Credentials/provider/owner unavailability is Blocked, never a substitute Red.

- [ ] **Step 4: Implement the minimum clients/mappers** using approved hosts/operations, minimal credential scope, bounded pages/body/deadline/request count, field allowlists, and typed auth/authorization/rate/schema outcomes. Discard raw bodies; do not retry inside adapters; do not infer credits/limits/budgets or estimate spend. Ollama per-response metadata never becomes an account total.

- [ ] **Step 5: Run Green and source-isolation checks:**

```bash
python3 -m pytest backend/tests/adapters/providers/codex/test_openai_api_live.py -q
python3 -m pytest backend/tests/live/ollama/test_ollama_api_budget_live.py -q
python3 tools/automation/run.py AUTO-QUALITY
```

Expected: supported facts reconcile within approved tolerance; unsupported facts remain explicit; no credential/content/raw body crosses its adapter.

- [ ] **Step 6: Commit each lane separately:**

```bash
git add backend/src/agentmonitor/adapters/providers/codex/openai_api backend/tests/adapters/providers/codex/test_openai_api_live.py
git commit -m "feat(codex): collect OpenAI API budgets"
git add backend/src/agentmonitor/adapters/providers/ollama/api backend/tests/live/ollama/test_ollama_api_budget_live.py
git commit -m "feat(ollama): expose evidenced API budget capability"
```

### Task 3: ST-BUDGET-003 — Publish budget HTTP resources and generated client

**Epic:** `EPIC-BUDGET-01`

**Files:**
- Modify: `backend/src/agentmonitor/api/v1/schemas/capacity.py`
- Modify: `backend/src/agentmonitor/api/v1/routers/capacity.py`
- Create: `backend/tests/integration/api/test_capacity_budgets_http.py`
- Regenerate: `contracts/openapi/agentmonitor-v1.json`
- Regenerate: `frontend/src/generated/api/index.ts`

**Interfaces:** Consumes M05 `ListBudgetsV1`, `GetBudgetV1`, `ListUsageBreakdownsV1`, and `GetAccountApiCapacityV1` plus M01 `read:telemetry`; produces `capacity_list_budgets_v1`, `capacity_get_budget_v1`, `capacity_list_usage_breakdowns_v1`, and `capacity_get_account_api_budget_v1` with cursor bounds, exact schemas, RFC 9457 problems, and generated TypeScript operations. `capacity_get_account_api_budget_v1` is exactly `GET /api/v1/accounts/{account_id}/api-capacity`.

**Contracts:** Consumes `CTR-CAP-001/002/003/006/007`, `CTR-COMMON-001..005/007`, and `CTR-IAM-001..007`; produces `CTR-API-001..003` and `CTR-UI-001`, all at V1.

**Traceability:** `NFR-API-001/002`; `M05-HTTP-001/003/004/006..010`; `API-I08/I12`; `AC-V1-003`, `AC-UI-005/006`.

- [ ] **Step 1: Write failing real-HTTP tests** starting the production app on loopback with real IAM, migrated SQLite, and a provider-collected budget. Assert 401/403, exact string/minor-unit JSON, explicit unsupported dimensions, stable cursors, schema conformance, and no ingestion/provider-control route.

```python
def test_budget_response_preserves_exact_money(running_app, real_budget_id) -> None:
    response = running_app.http.get(
        f"/api/v1/budgets/{real_budget_id}", headers=telemetry_bearer_headers()
    )
    assert response.status_code == 200
    assert isinstance(response.json()["current_spend"]["amount"], str)
    assert_response_matches_running_openapi(response)

def test_account_api_capacity_delegates_to_m05_query(
    running_app, real_budget_account_id, capacity_application
) -> None:
    response = running_app.http.get(
        f"/api/v1/accounts/{real_budget_account_id}/api-capacity",
        headers=telemetry_bearer_headers(),
    )
    assert response.status_code == 200
    expected = capacity_application.get_account_api_capacity(real_budget_account_id)
    assert response.json() == contract_json(expected)
    assert_response_matches_running_openapi(response)
```

- [ ] **Step 2: Run Red:** `python3 -m pytest backend/tests/integration/api/test_capacity_budgets_http.py -q`

Expected: FAIL on absent schemas/routes. No provider-derived row means Blocked.

- [ ] **Step 3: Implement transport-only mappings** for account budgets, budget detail, usage breakdowns, and `GET /api/v1/accounts/{account_id}/api-capacity` backed only by `GetAccountApiCapacityV1`. Preserve union discriminators, field states, exact amounts, provenance, interval, completeness, and forecast state; never call repositories/providers directly.

- [ ] **Step 4: Run Green:** `python3 -m pytest backend/tests/integration/api/test_capacity_budgets_http.py -q`

Expected: PASS at the real T3 boundary.

- [ ] **Step 5: Regenerate through the sole writer:** `python3 tools/automation/run.py AUTO-BUILD`

Expected: running-app OpenAPI validates, compatibility passes, generated client compiles strictly, and source/client digests agree. Blocked build automation keeps the Story incomplete.

- [ ] **Step 6: Commit:**

```bash
git add backend/src/agentmonitor/api/v1/schemas/capacity.py backend/src/agentmonitor/api/v1/routers/capacity.py backend/tests/integration/api/test_capacity_budgets_http.py contracts/openapi/agentmonitor-v1.json frontend/src/generated/api
git commit -m "feat(api): publish API budget resources"
```

### Task 4: ST-BUDGET-004 — Render truthful budget and history views

**Epic:** `EPIC-BUDGET-01`

**Files:**
- Create: `frontend/src/features/accounts/BudgetPanel.tsx`
- Create: `frontend/src/features/accounts/useBudgets.ts`
- Create: `frontend/src/features/history/BudgetHistory.tsx`
- Modify: `frontend/src/shared/api/client.ts`
- Create: `frontend/tests/browser/p02/budgets.spec.ts`
- Create: `docs/user/dashboard.md`

**Interfaces:** Consumes only generated budget/history/forecast operations via `frontend/src/shared/api/client.ts`, including generated `capacity_get_account_api_budget_v1` for `GetAccountApiCapacityV1`; produces accessible exact-value panels, supported breakdowns, forecast/insufficient-state explanations, and separate subscription/API sections.

**Contracts:** Consumes `CTR-API-001..003`, `CTR-CAP-001/002/003/006/007`, `CTR-COMMON-003/005`, and `CTR-UI-001`, all at V1.

**Traceability:** `FR-BUDGET-001..006`, `FR-UI-002..007`; `UI-BUD-001..008`, `UI-HIST-001..008`, `M05-BROWSER-003/005`; `AC-UI-002..006`.

- [ ] **Step 1: Write failing built-browser workflows** against the real production app. Assert currency/period/source/freshness, explicit unsupported fields, separate pools, exact chart/table agreement, no raw key, truthful empty/partial/stale states, keyboard access, non-color cues, and responsive layouts.

```typescript
test("shows only real supported API budget facts", async ({ page }) => {
  await loginThroughProductionFlow(page);
  await page.goto(realBudgetAccountUrl());
  await expect(page.getByRole("heading", { name: "API budget" })).toBeVisible();
  await expectAccountApiCapacityRequest(page, "capacity_get_account_api_budget_v1");
  await expectExactBudgetToMatchApi(page);
  await expectNoInventedBreakdownOrRawKey(page);
});
```

- [ ] **Step 2: Run Red:** `npm --prefix frontend run test:browser -- --grep "API budget"`

Expected: FAIL because the feature is absent. Missing real browser/backend/provider data is Blocked.

- [ ] **Step 3: Implement the generated-client feature** by exposing generated `capacity_get_account_api_budget_v1` through `frontend/src/shared/api/client.ts` and consuming it from `useBudgets.ts`; do not add parallel DTOs, direct fetch, totals, forecasts, or fallback values. Expose source, observed/data-through time, freshness, precision, confidence, method/input IDs, completeness, and omitted reasons; render exact tables before charts.

- [ ] **Step 4: Run Green/refactor:**

```bash
npm --prefix frontend run test:browser -- --grep "API budget"
npm --prefix frontend run test:accessibility -- --grep "API budget"
```

Expected: PASS in a real built browser, including keyboard, names, chart/table equivalence, zoom, and breakpoints.

- [ ] **Step 5: Commit:**

```bash
git add frontend/src/features/accounts/BudgetPanel.tsx frontend/src/features/accounts/useBudgets.ts frontend/src/features/history/BudgetHistory.tsx frontend/src/shared/api/client.ts frontend/tests/browser/p02/budgets.spec.ts docs/user/dashboard.md
git commit -m "feat(ui): show real API budgets and usage"
```

### Task 5: ST-BUDGET-005 — Reconcile verticals and close V1-M7

**Epic:** `EPIC-BUDGET-01`

**Files:**
- Modify: `backend/src/agentmonitor/composition/providers.py`
- Create: `backend/tests/integration/release/test_api_budget_verticals_live.py`
- Modify: `docs/modules/capacity.md`
- Modify: `docs/adapters/claude.md`
- Modify: `docs/adapters/codex.md`
- Modify: `docs/adapters/ollama.md`
- Create: `docs/test-evidence/capacity/v1-m7-api-budget-handoff.md`

**Interfaces:** Consumes production provider lanes, M04, M05, running P01, generated client, built P02, and owner comparisons. The allocated shared composition writer modifies `backend/src/agentmonitor/composition/providers.py` to register those adapters. Produces the candidate-bound `INT-BUD-001..012` matrix and no new domain behavior.

**Contracts:** Verifies `CTR-CAP-001..009`, `CTR-COL-001/002/005/006`, `CTR-API-001..003`, `CTR-UI-001`, and `CTR-INT-001..006` at their approved V1 versions; it publishes no new product contract.

**Traceability:** `FR-BUDGET-001..006`; `M05-LIVE-007..014`; `INT-BUD-001..012`; `AC-LIVE-004/005/007`, `AC-HIST-001`, `AC-OPS-003/006`, `AC-TEST-001..006`.

- [ ] **Step 1: Write the failing end-to-end test** triggering each reserved source, waiting for commit, querying the running API/client, inspecting the built browser, comparing the same scope/interval to provider authority, and scanning artifacts/default profiles for prohibited changes.

```python
def test_enabled_budget_capabilities_reconcile_end_to_end() -> None:
    for reservation in approved_budget_reservations():
        receipt = trigger_real_collection_and_wait(reservation)
        assert_vertical_reconciles(
            receipt,
            query_running_api(receipt),
            inspect_built_browser(receipt),
            owner_authoritative_comparison(reservation),
        )
        assert_no_secret_content_or_profile_mutation(receipt)
```

- [ ] **Step 2: Run Red:** `python3 -m pytest backend/tests/integration/release/test_api_budget_verticals_live.py -q`

Expected: FAIL on the first missing production link. Unavailable provider/source/owner comparison is per-capability Blocked.

- [ ] **Step 3: Obtain the serialized shared-writer handoff receipt for `backend/src/agentmonitor/composition/providers.py`, then wire only approved registrations in that exact file.** The receipt must identify the prior writer's clean handoff, current candidate/plan hash, collision-free write set, and this Story as the active writer before any edit. Register adapters with M03/M04 and the M05 sink; do not add provider branches to M05, table access to P01, or UI-local joins. A missing or conflicting handoff is Blocked.

- [ ] **Step 4: Run Green and milestone gates:**

```bash
python3 -m pytest backend/tests/integration/release/test_api_budget_verticals_live.py -q
python3 tools/automation/run.py AUTO-TEST
python3 tools/automation/run.py AUTO-QUALITY
python3 tools/automation/run.py AUTO-BUILD
python3 tools/automation/run.py AUTO-DOCS-CHECK
```

Expected: real supported capabilities reconcile end to end; values remain exact; one failed source is isolated; all gates enumerate every non-Passed T6 row.

- [ ] **Step 5: Write the handoff** with `ST-BUDGET-001..005`, requirements/ACs, approved versions, exact files, R/G/R commands/timestamps, safe aliases and owner acknowledgements, tolerances, non-Passed rows, and security/privacy/migration/license/docs impact.

- [ ] **Step 6: Commit:**

```bash
git add backend/src/agentmonitor/composition/providers.py backend/tests/integration/release/test_api_budget_verticals_live.py docs/modules/capacity.md docs/adapters/claude.md docs/adapters/codex.md docs/adapters/ollama.md docs/test-evidence/capacity/v1-m7-api-budget-handoff.md
git commit -m "test(v1-m7): verify API budget verticals"
```

## V1-M7 exit gate

- [ ] `ST-BUDGET-001..005` have specification-compliance and quality approval.
- [ ] `CTR-CAP-002/004/006/007`, capability rows, OpenAPI, and client versions agree.
- [ ] Anthropic/OpenAI and supported Ollama facts reconcile; Unsupported is evidenced and not called an integration.
- [ ] Exact money survives provider mapping, SQLite, API, export, and browser; subscription/API pools remain separate.
- [ ] Rate limits, failure isolation, privacy, default-profile immutability, and canonical test/quality/build/docs gates pass for their claimed boundaries, with all non-Passed live rows visible.

## Execution handoff

Plan complete and saved to `docs/superpowers/plans/2026-09-19-agentmonitor-v1-m7-api-budgets.md`. Execute one Story per approved write set with `superpowers:subagent-driven-development`, or inline with `superpowers:executing-plans` and a review checkpoint after every Story.
