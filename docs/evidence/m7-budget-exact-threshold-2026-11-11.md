# M7 exact low-remaining threshold

Status: scoped pure-policy implementation and verification; API/UI consumption
and real financial verification remain Not Run. Recorded 11 November 2026;
Green completed before the recorded clock check at 20:35:29 UTC.

## Authority and scope

- Approved focused execution plan 1.1.0, calculation-rule clarification at
  `e40b23f`; existing T004/T012, FR-BUDGET-004, M7-A02/A08 and M7-MATH-14.
- Owner: M05 Capacity. This adds only the internal
  `MoneyPercentage.is_low_remaining` property; no published contract changes.
  Existing CTR-COMMON-003 1.0.0 exact-money representation and bounds are unchanged.
- The fixed warning uses exact remaining/positive-limit inputs, comparing
  scaled integers before percentage formatting. It does not infer a provider
  service stop, change funds or clip signed/greater-than-100% ratios.
- Existing `remaining_percentage` returns no result for missing remaining,
  missing/nonpositive limit or incompatible basis, and rejects mixed currencies.
  An absent ratio must remain unavailable in its future API/UI consumer.

## Red, Green and regression evidence

Command, from the M7 worktree, with the existing admitted Python environment:

```sh
PYTHONPATH=backend/src:. /home/dev/Nextcloud/Code/AI/AgentMonitor/backend/.venv/bin/python -m pytest backend/tests/capacity/pure/test_budget_money.py -q
```

Red: **9 failed, 44 passed in 0.17s** before the production property existed.
Each new case failed with
`AttributeError: 'MoneyPercentage' object has no attribute 'is_low_remaining'`.
These tests exercise actual ratio classification, not only attribute presence.

Green after the small integer-comparison implementation: **53 passed in 0.07s**.
New cases distinguish 20.004% from 19.996% even though both display 20.00%,
include exactly 20%, differing decimal scales, zero/negative/over-100% ratios,
and values one monetary unit above/below the threshold at the 78-digit limit.
Tests execute under a deliberately low Decimal precision to ensure the result
does not depend on that context. Existing missing/nonpositive denominator,
unknown remaining, incompatible basis and mixed-currency tests remain green.

Additional verification:

```sh
PYTHONPATH=backend/src:. /home/dev/Nextcloud/Code/AI/AgentMonitor/backend/.venv/bin/python -m pytest backend/tests/capacity/pure -q
MYPYPATH=backend/src /home/dev/Nextcloud/Code/AI/AgentMonitor/backend/.venv/bin/mypy --config-file backend/pyproject.toml --explicit-package-bases backend/src/agentmonitor/modules/capacity/domain/budget_money.py backend/tests/capacity/pure/test_budget_money.py
/home/dev/Nextcloud/Code/AI/AgentMonitor/backend/.venv/bin/ruff check --config backend/pyproject.toml backend/src/agentmonitor/modules/capacity/domain/budget_money.py backend/tests/capacity/pure/test_budget_money.py
/home/dev/Nextcloud/Code/AI/AgentMonitor/backend/.venv/bin/ruff format --check --config backend/pyproject.toml backend/src/agentmonitor/modules/capacity/domain/budget_money.py backend/tests/capacity/pure/test_budget_money.py
```

Results: **193 capacity pure tests passed in 1.28s**; mypy passed for both files;
Ruff check and formatting passed; scoped `git diff --check` passed. No additional
refactor was necessary for this small property.

All constructed numbers are pure no-I/O inputs. No provider response, database
or browser telemetry was fabricated; no provider, account or service action ran.

## Integration handoff and impact

T010/T012 must obtain a compatible ratio through the M05 policy and project the
exact `is_low_remaining` result into the typed financial state. P02 must render
that state rather than compare `percentage_text` or a floating-point value.
The ratio inputs remain available for truthful raw values and display. This
handoff does not claim that API fields, Overview warnings or installed browser
behavior are connected or verified, and does not close T004/T012 or M7.

Changed files: `budget_money.py`, its existing pure `test_budget_money.py`, and
this evidence record. No migration, dependency, license, credential, privacy,
network or deployment changes. No new canonical gate was added; root integration
includes these tests in the existing M7 checks.
