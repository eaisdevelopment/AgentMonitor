# M3 local release-gate decision — 2026-09-25

> Reconciled through 2026-10-02: this document remains genuine historical technical
> gate evidence. The older active
> [historical M3 acceptance record](v1-m3-acceptance-status-v1.json) is
> superseded by the scope-corrected
> [active M3 acceptance record](v1-m3-acceptance-status-v2.json), which remains
> Blocked. See the [closure audit](m3-closure-audit-2026-10-01.md) for the safe
> current-revision rerun work that remains.

The owner explicitly directed that the repeated detached M0 approval blocker be
removed from milestone execution. This record applies to local Linux
development milestones, beginning with V1-M3 and carrying forward to M4–M8.

## Decision

The executable gate validates current technical artifacts and then runs the
real milestone boundary checks. Detached `owner`, `security_privacy`,
`test_integrity`, and `root_integration` records remain available for optional
governance review, but pending decisions do not stop local execution. No
approval record is changed to `approved` by this decision.

Natural unavailable provider/account/process/time-window scenarios and missing
historical Red chronology remain `Blocked` or `Not Run`; they are not reported
as passes. This scoped decision does not complete M0 G9, add Codex/Ollama/API
support, authorize remote hosting, or permit secrets, raw provider content,
profile mutation, or process control.

## Canonical technical preflight

```text
./.venv-m0-g1/bin/python tools/discovery/m3_handoff_validate.py --require-technical-live
```

It must report `M3 technical handoff: AUTHORIZED (local owner release policy)`.
The strict `--require-adapter-live` command remains an advisory governance
audit and is deliberately not called by any local milestone release routine.

## M3 release evidence

The technical preflight and contract tests passed after this decision. The
complete M3 result is recorded only after the real quota, owner-terminal OTLP,
authenticated visible-browser, quality, build, mutation, documentation, and
Git gates finish:

```text
python3 tools/automation/run.py AUTO-M3-EXIT
```

Any non-zero result remains a failed or blocked gate and must be fixed or
reported; it is never relabeled as success.

## Final local run — passed

On 2026-09-25, the canonical command returned zero. The run used the real
installed Claude Code `2.1.282`, the owner-confirmed account and file-backed
SQLite database, a loopback FastAPI server, and a visible Chrome window. The
dashboard password was read from the owner-managed `.env` key in memory only;
it was not printed, committed, or passed on a command line.

Observed gate results:

- fresh Claude quota and owner-terminal OTLP/runtime same-account lineage: **Passed**;
- populated authenticated browser: **Passed** (visible, not headless);
- `AUTO-M3-TEST`: **Passed** — 354 passed, 10 skipped;
- `AUTO-QUALITY`, `AUTO-BUILD`, `AUTO-MUTATION`: **Passed** (541 total policy mutants, 534 killed, 7 equivalent accepted);
- `AUTO-DOCS-CHECK` and local `AUTO-GIT-PREFLIGHT`: **Passed**.

The local toolchain gate used CPython `3.12.3`, Node `22.23.3`, npm `10.9.9`,
and uv `0.11.16`; the pinned project metadata and CI bootstrap were updated to
the actually installed Node/npm patch releases.

The real first capacity-history page exposed no continuation cursor, so the
second-page pagination scenario remains **Not Run**. Multi-provider,
multi-account, and natural ten-minute-stall scenarios remain **Blocked/Not
Run** because those real conditions are unavailable on this workstation.
Detached approval JSON remains `pending` and advisory; no approval was
fabricated. The strict governance validator still fails closed by design.
