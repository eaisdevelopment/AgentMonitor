# AgentMonitor V1 implementation-plan index

Status: **Planning complete; implementation not authorized**

This is the execution layer over the approved product requirements and the 20
detailed module plans. It contains eight milestones, 19 Epics, and 44 Stories.
Every Story names exact files, module contracts, requirement/acceptance IDs,
real-boundary Red/Green commands, expected results, and a commit boundary.

## Authoritative files

- [V1 implementation program](2026-09-19-agentmonitor-v1-program.md): milestone
  outcomes, dependency graph, lifecycle, parallel-execution policy, and gates.
- [Import-ready backlog](implementation-backlog.toml): unique Milestone, Epic,
  Story, ownership, and dependency records. `gitlab_objects_created = false` is
  intentional until a GitLab project ID and protected token are configured.
- [V1-M1 Foundation](2026-09-19-agentmonitor-v1-m1-foundation.md)
- [V1-M2 Authenticated shell](2026-09-19-agentmonitor-v1-m2-authenticated-shell.md)
- [V1-M3 Claude slice](2026-09-19-agentmonitor-v1-m3-claude-slice.md)
- [V1-M4 Claude fleet, alerts, and operations](2026-09-19-agentmonitor-v1-m4-claude-fleet-alerts.md)
- [V1-M5 Codex slice](2026-09-19-agentmonitor-v1-m5-codex-slice.md)
- [V1-M6 Ollama slice](2026-09-19-agentmonitor-v1-m6-ollama-slice.md)
- [V1-M7 API budgets](2026-09-19-agentmonitor-v1-m7-api-budgets.md)
- [V1-M8 Hardening and release](2026-09-19-agentmonitor-v1-m8-hardening-release.md)

## Module and boundary coverage

The detailed plan remains the design authority; the milestone Stories are the
implementation units. Cross-module Stories list every affected plan in the
backlog and reserve shared writers through `parallel-ownership.toml`.

| Plan | Isolated owner | Implementation coverage |
|---|---|---|
| `PLAN-M0-DISCOVERY` | Real provider/platform capability evidence | Entry evidence for M3–M7; not a production-code Story |
| `PLAN-FND` | Repository, toolchain, CI, composition | M1 `ST-CONTRACT-*`, `ST-FND-*` |
| `PLAN-M01` | Identity, sessions, CSRF, API tokens | M2 `ST-IAM-*` |
| `PLAN-M02` | Organizations, accounts, resources, profiles | M3 `ST-REG-001`; M4–M6 provider identity Stories |
| `PLAN-M03` | Provider protocol and capabilities | M3 `ST-PROV-001`; M5–M7 provider-lane Stories |
| `PLAN-M04` | Collection scheduling, isolation, retries | M3–M7 collection Stories |
| `PLAN-M05` | Capacity, quota, budget, history, forecast | M3–M7 capacity/budget Stories |
| `PLAN-M06` | Processes, sessions, hierarchy, stalls | M3–M6 runtime Stories |
| `PLAN-M07` | Alert rules and lifecycle | M4 `ST-ALERT-001..002` |
| `PLAN-M08` | Health, diagnostics, backup, restore, audit | M4–M6 operations integration; M8 `ST-HARDEN-*` |
| `PLAN-A01` | Claude adapter | M3, M4, and M7 Claude/Anthropic Stories |
| `PLAN-A02` | Codex adapter | M5 and M7 Codex/OpenAI Stories |
| `PLAN-A03` | Ollama adapter | M6 and M7 Ollama Stories |
| `PLAN-A04-LINUX` | Linux observation and service boundary | M3–M6 runtime; M8 native operation |
| `PLAN-A04-MAC` | macOS-compatible platform contract | M8 compatibility review; live evidence remains Blocked without a real Mac |
| `PLAN-P01` | FastAPI, OpenAPI, authentication enforcement | API Stories in every applicable milestone |
| `PLAN-P02` | React UI and generated client | UI Stories in every applicable milestone |
| `PLAN-DB` | SQLite repositories, migrations, transactions | M1 base plus module-owned persistence Stories |
| `PLAN-DEP` | Native Linux packaging and service lifecycle | M8 `ST-DEP-001..002` |
| `PLAN-INT` | Integration, acceptance, release | Every milestone exit; M8 `ST-RELEASE-001..002` |

## Validation

Run:

```bash
python3 -m unittest tools.planning.test_implementation_backlog
python3 tools/automation/run.py AUTO-DOCS-CHECK
python3 tools/automation/run.py AUTO-PLAN-CHECK
python3 tools/automation/run.py AUTO-TEST
```

The backlog test reads the real checkout and fails when a Milestone, Epic, or
Story is missing, duplicated, assigned to the wrong milestone, detached from a
real plan heading, or lacks requirement/contract traceability. These checks
validate planning artifacts only; they do not authorize implementation or
claim that any provider/application/live test has run.

## Execution rule

Before production code, approve the affected detailed module plans and exact
contract versions. Then execute one `ST-*` Story at a time with
`superpowers:subagent-driven-development`, independent specification and code
review, isolated write ownership, and retained Red/Green/live evidence.
