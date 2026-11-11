# M7 stored funds projection: bounded implementation evidence

Status: local implementation under approved focused plan 1.1.0 and M05
increment 0.3.0. Installed source-to-HTTP-to-DOM verification is still required
at this checkpoint. This is partial T010/T011 delivery, not M7 completion.

## Scope and ownership

- Requirements: FR-BUDGET-001..006; M7-A01/A06; M7-MATH-07/08;
  M7-HTTP-001..006 and M7-UI-001..006 (partial funds coverage only).
- M05/root owns additive CTR-CAP-006 2.3.0: exact fund components, independent
  account funds result/port, compatible optional field on account current view.
- Root composition consumes published M02 cloud membership and M05 quota-window
  reads. A03 owns monetary window interpretation. P01 maps typed HTTP fields;
  P02 renders them through the generated client.
- Existing cloud resources need no separate billing binding to display funds.
  Included/purchased components stay separate and non-constraining. Scope is
  unresolved, not inferred from the account label. Each value retains its own
  source time, exact coefficient/scale, availability, precision and provenance.
- No new database table/migration, dependency/license change, provider request,
  key/profile access, owner configuration or process mutation.

## Test evidence

1. Pure contract Red: after correcting an invalid test helper, three tests
   failed because the new fund DTOs did not exist. Green with the existing
   account contract: four passed. Test-helper errors are not behavior Red.
2. A03 mapper Red: module absent. Green: seventeen pure mapper tests; combined
   mapper and existing Ollama balance contract suite: twenty-nine passed.
   Wrong-provider/source/unit, unsupported target, future evidence, exact small
   money, stale deadlines, unavailable values and non-constraining zero covered.
3. Actual HTTP Red: funds assertion failed against the previous application
   response (one failed, two passed). Green: three passed, zero skips, using
   actual isolated IAM/SQLite/uvicorn. Existing 401/403/404/no-store guards and
   no-collection checks retained. This proves unavailable funds, not populated
   provider reports.
4. Combined scoped suite: thirty-three passed, zero skips. Exact command:

   ```sh
   PYTHONPATH=backend/src:. backend/.venv/bin/python -m pytest -c backend/pyproject.toml backend/tests/contracts/test_budget_funds_query.py backend/tests/contracts/test_budget_account_query.py backend/tests/providers/ollama/pure/test_funds_projection.py backend/tests/contracts/pure/test_ollama_cloud_balance_v1.py backend/tests/integration/api/test_budget_http.py -q -p tools.automation.pytest_no_skip
   ```

5. Read-only actual stored-data probe: both existing Ollama cloud accounts
   returned genuine components through public query ports and wire mapping.
   This was not HTTP or browser proof and did not collect again.
6. Built installed browser Red at `437a232866658ca38446d3c57a4cd7ce98c2e156`:
   `budget_funds_projection_missing`; authenticated access and genuine source
   checks passed, zero mutation requests. Canonical scoped probe:
   `node frontend/tests/browser/m7/verify_funds.mjs`.

The existing M7 pure lane now includes both new pure suites. Full quality first
identified import ordering and strict test-helper typing errors, subsequently
corrected; these static failures are not behavioral Red.

Final pre-install checks on this increment: `AUTO-QUALITY` passed lint, format,
strict Python/TypeScript types, module boundaries, compatible 85-operation
generated API/client, locked inputs and production build. The existing M7
`--lane pure` passed 268 tests. `AUTO-DOCS-CHECK` passed 378 Markdown files;
`AUTO-PLAN-CHECK`, local `AUTO-GIT-PREFLIGHT` and `git diff --check` passed.
The strengthened browser probe reproduced `budget_funds_projection_missing`
against installed `437a232` at 21:26 UTC, with genuine source evidence and zero
mutation requests. Full M7 acceptance is not implied by these scoped results.

## Review and completion boundaries

Independent review found no additional production defect within its inspected
scope. It identified two browser-verifier weaknesses: label-only row selection
and checking only returned components. The verifier must match resource/component
identity and compare the whole eligible source set, with concurrent source
replacement reported explicitly rather than accepted. Root added matching DOM
identity attributes. No provider response is fabricated or replayed.

Financial totals, billing reports, full history/Overview, other providers,
retention/forecast and full M7 exit remain unfinished. Deployment and populated
built-browser Green must be recorded after execution, not inferred from these
tests. The supported-funds increment does not close T010 or T011.
