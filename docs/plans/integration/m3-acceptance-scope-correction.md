# V1-M3 acceptance-scope correction

- Status: **Approved for implementation** by the owner's 2026-10-02 direction:
  correct M3 to one Claude vertical and move other vendors to their subsequent
  milestones.
- Owner: integration/documentation authority.
- Runtime contracts: unchanged. Registry, provider, collection, capacity,
  runtime, API, UI, and database contracts remain V1.
- Internal documentation contract: M3 acceptance record schema `2.0.0` adds the
  milestone-scoped `AC-M3-001..007` criterion set while preserving schema
  `1.0.0` records as historical evidence.

## Decision

V1-M3 accepts exactly one owner-confirmed real Claude vertical: provider and
registry identity, quota collection and persistence, same-account Linux runtime
observation, authenticated versioned API, generated client, built dashboard,
history/provenance, privacy, and the canonical current-revision gate.

The broader outcomes retain these owners:

| Scope | Owning milestone |
|---|---|
| Six intended Claude accounts, organizations, fleet, alerts, and Claude operational behavior | V1-M4 |
| Codex accounts, subscription capacity, and representative Codex processes | V1-M5 |
| Ollama local/cloud identities, resources, and representative processes | V1-M6 |
| Anthropic, OpenAI, and supported Ollama API usage/cost/budgets | V1-M7 |
| Cross-provider matrices, complete dashboard, deployment, recovery, release-wide security/docs/test criteria, and final V1 acceptance | V1-M8 |

Milestone evidence may contribute to a release-wide criterion without claiming
that the entire release criterion passed. M3 therefore stops carrying
six-account, Codex, Ollama, API-budget, cross-provider, and full-release closure
as its own exit conditions.

## Files and behavior

1. Add `AC-M3-001..007` to the acceptance-criteria catalog as milestone gates;
   they contribute to, but do not replace, mandatory V1 release criteria.
2. Replace M3 Task 6's global criterion set with the seven M3 gates and add an
   explicit ownership transfer table to M3–M8 plans.
3. Register the seven new IDs under PLAN-INT in exact requirement ownership,
   retain each producing plan as a supporting party, and rebind the synchronized
   planning snapshot.
4. Version the documentation validator so historical schema `1.0.0` records
   retain the old criterion set and active schema `2.0.0` records require only
   `AC-M3-001..007`. Schema `2.0.0` remains a Blocked transition record; a
   successor closure schema must bind the future safe current-revision receipt.
5. Preserve the 2026-09-24 record as `superseded`; create a new active Blocked
   record. Existing M3 delivery evidence can pass criteria 1–6. The safe current
   gate and explicit historical TDD disposition remain criterion 7 blockers.
6. Point the current status index and implementation overlay to the new active
   record without changing M4–M8 delivery states.

## Red / Green

Red tests must prove that the old checker rejects schema `2.0.0`, cannot accept
the scoped criterion set, and cannot supersede a JSON status authority safely.

Green requires:

```text
python3 -m unittest tools.docs.test_check
python3 tools/automation/run.py AUTO-DOCS-CHECK
python3 tools/automation/run.py AUTO-PLAN-CHECK
```

The change does not run provider collection, alter the owner database, modify
profiles, start authentication, or control running agents.

## Impact

- Security/privacy: documentation metadata only; no account alias, identity,
  credential, prompt, response, source content, or arbitrary environment data.
- Migration: no database or API migration.
- Dependencies/licenses: none.
- Rollback: revert the scope-correction commit; historical schema `1.0.0`
  evidence remains intact in Git either way.
