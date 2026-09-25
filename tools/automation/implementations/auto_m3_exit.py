"""Fail-closed V1-M3 exit over fresh real Claude observations and browser."""

from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backend/src"))
M0_SCHEMA_PYTHON = ROOT / ".venv-m0-g1/bin/python"

if TYPE_CHECKING:
    from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
        DatabaseRefV1,
    )
    from agentmonitor.contracts.collection_control_v1 import CollectionRunViewV1
    from agentmonitor.contracts.common_v1 import OpaqueIdV1
    from agentmonitor.contracts.runtime_observation_v1 import AgentSessionRecordV1


CLAUDE_OTLP_SOURCE_ID = "claude.otel.metrics.http-json.v1"
M3_LOCAL_EXIT_ROUTINES = (
    "AUTO-M3-TEST",
    "AUTO-QUALITY",
    "AUTO-BUILD",
    "AUTO-MUTATION",
    "AUTO-DOCS-CHECK",
    "AUTO-GIT-PREFLIGHT",
)
_BACKEND_BOOTSTRAP = (
    "import runpy,sys; "
    "source=sys.argv.pop(1); sys.path.insert(0,source); "
    "sys.argv[0]='agentmonitor.composition.claude_otel_runtime'; "
    "runpy.run_module('agentmonitor.composition.claude_otel_runtime',run_name='__main__')"
)
_BROWSER_BOOTSTRAP = (
    "import os,runpy,sys; "
    "root=sys.argv.pop(1); account=sys.argv.pop(1); script=sys.argv.pop(1); "
    "os.environ['AGENTMONITOR_M3_DATA_ROOT']=root; "
    "os.environ['AGENTMONITOR_M3_ACCOUNT_ID']=account; "
    "sys.argv=[script]; runpy.run_path(script,run_name='__main__')"
)


class M3ExitErrorV1(ValueError):
    """A bounded completion failure without provider values or credentials."""


@dataclass(frozen=True, slots=True)
class M3FreshLineageV1:
    """Safe scalar lineage used by the fail-closed completion policy."""

    gate_started_at: datetime
    quota_account_id: str
    quota_run_id: str
    quota_requested_at: datetime
    quota_completed_at: datetime | None
    quota_observation_ids: tuple[str, ...]
    runtime_account_id: str | None
    runtime_run_id: str
    runtime_requested_at: datetime
    runtime_completed_at: datetime | None
    runtime_observed_at: datetime
    runtime_source_id: str
    runtime_state: str
    runtime_observation_ids: tuple[str, ...]


def verify_fresh_same_account_v1(lineage: M3FreshLineageV1) -> None:
    """Reject stale, incomplete, mismatched, or replay-only milestone evidence."""
    timestamps = (
        lineage.gate_started_at,
        lineage.quota_requested_at,
        lineage.quota_completed_at,
        lineage.runtime_requested_at,
        lineage.runtime_completed_at,
        lineage.runtime_observed_at,
    )
    if (
        any(value is None or value.utcoffset() != timedelta(0) for value in timestamps)
        or lineage.quota_requested_at < lineage.gate_started_at
        or lineage.quota_completed_at is None
        or lineage.quota_completed_at < lineage.gate_started_at
        or lineage.runtime_requested_at < lineage.gate_started_at
        or lineage.runtime_completed_at is None
        or lineage.runtime_completed_at < lineage.gate_started_at
        or lineage.runtime_observed_at < lineage.gate_started_at
    ):
        raise M3ExitErrorV1("m3_exit_fresh_observation_missing")
    if (
        lineage.runtime_account_id is None
        or lineage.runtime_account_id != lineage.quota_account_id
    ):
        raise M3ExitErrorV1("m3_exit_account_mismatch")
    if (
        not lineage.quota_run_id
        or not lineage.runtime_run_id
        or lineage.quota_run_id == lineage.runtime_run_id
        or not lineage.quota_observation_ids
        or not lineage.runtime_observation_ids
    ):
        raise M3ExitErrorV1("m3_exit_lineage_incomplete")
    if (
        lineage.runtime_source_id != CLAUDE_OTLP_SOURCE_ID
        or lineage.runtime_state != "succeeded"
    ):
        raise M3ExitErrorV1("m3_exit_runtime_outcome_invalid")


def _run_checkout_command(
    arguments: list[str],
    *,
    timeout: int,
    environment: dict[str, str] | None = None,
) -> None:
    result = subprocess.run(
        arguments,
        cwd=ROOT,
        check=False,
        timeout=timeout,
        env=environment,
    )
    if result.returncode == 3:
        raise M3ExitErrorV1("m3_exit_required_gate_blocked")
    if result.returncode != 0:
        raise M3ExitErrorV1("m3_exit_required_gate_failed")


def identity_evidence_check(
    data_root: Path, account_id: str
) -> tuple[list[str], dict[str, str]]:
    """Build the exact real-owner evidence check used by the M3 exit gate."""

    environment = os.environ.copy()
    environment["AGENTMONITOR_TEST_DATA_ROOT"] = str(data_root)
    environment["AGENTMONITOR_TEST_ACCOUNT_ID"] = account_id
    environment["PYTHONPATH"] = str(ROOT / "backend/src")
    return (
        [
            str(ROOT / "backend/.venv/bin/python"),
            "-m",
            "pytest",
            "backend/tests/live/claude/test_provider_identity_evidence.py",
            "-q",
            "--tb=short",
        ],
        environment,
    )


def _current_m0_handoff_is_technically_ready() -> None:
    """Check technical handoff evidence without detached governance approvals."""
    if not M0_SCHEMA_PYTHON.is_file():
        raise M3ExitErrorV1("m3_exit_m0_schema_runtime_unavailable")
    result = subprocess.run(
        [
            str(M0_SCHEMA_PYTHON),
            "tools/discovery/m3_handoff_validate.py",
            "--require-technical-live",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    if result.returncode != 0:
        raise M3ExitErrorV1("m3_exit_m0_handoff_technical_evidence_missing")


def _fresh_runtime_lineage(
    reference: DatabaseRefV1,
    *,
    account_id: OpaqueIdV1,
    gate_started_at: datetime,
) -> tuple[AgentSessionRecordV1, CollectionRunViewV1]:
    from agentmonitor.adapters.persistence.collection_control.sqlite.repository import (
        SqliteCollectionRepositoryV1,
    )
    from agentmonitor.adapters.persistence.runtime_observation.sqlite.repository import (  # noqa: E501
        SqliteRuntimeObservationRepositoryV1,
    )
    from agentmonitor.modules.runtime_observation.application.queries import (
        ListAgentSessionsV1,
    )

    runtime = SqliteRuntimeObservationRepositoryV1(reference)
    sessions = tuple(
        session
        for session in ListAgentSessionsV1(runtime)(
            provider_key="claude",
            account_id=account_id,
            as_of=datetime.now(UTC),
            page_size=500,
        )
        if session.last_observed_at >= gate_started_at
        and session.provenance.source_id == CLAUDE_OTLP_SOURCE_ID
        and session.correlation_state == "automatic_matched"
        and session.account_id == account_id.value
    )
    if len(sessions) != 1:
        raise M3ExitErrorV1("m3_exit_fresh_runtime_observation_missing")
    session = sessions[0]
    run = SqliteCollectionRepositoryV1(reference).get_run(
        session.provenance.operation_id
    )
    return session, run


def _run_live_browser(data_root: Path, account_id: OpaqueIdV1) -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            _BROWSER_BOOTSTRAP,
            str(data_root),
            account_id.value,
            str(ROOT / "tools/automation/implementations/auto_m3_live.py"),
        ],
        cwd=ROOT,
        check=False,
        timeout=600,
    )
    if result.returncode == 3:
        raise M3ExitErrorV1("m3_exit_browser_blocked")
    if result.returncode != 0:
        raise M3ExitErrorV1("m3_exit_browser_failed")


def main() -> int:
    try:
        from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
            DatabaseRefV1,
        )
        from agentmonitor.composition.claude_live_monitoring import (
            run_owner_confirmed_claude_collection,
        )

        from tools.automation.implementations.auto_m3_live import _owner_target

        _current_m0_handoff_is_technically_ready()
        target = _owner_target()
        if target is None:
            raise M3ExitErrorV1("m3_exit_owner_target_unavailable")
        data_root, _config, account_id = target
        if not (sys.stdin.isatty() and sys.stdout.isatty() and sys.stderr.isatty()):
            raise M3ExitErrorV1("m3_exit_controlling_tty_required")

        gate_started_at = datetime.now(UTC)
        reference = DatabaseRefV1(data_root / "agentmonitor.db", data_root)
        quota = run_owner_confirmed_claude_collection(
            reference,
            status=lambda code: print(code, flush=True),
        )
        if quota.graph.account.account_id != account_id:
            raise M3ExitErrorV1("m3_exit_quota_account_mismatch")

        print(
            "M3 EXIT: OWNER CHECKPOINT — use the opened Claude session normally, "
            "then exit it to continue verification",
            flush=True,
        )
        runtime = subprocess.run(
            [
                sys.executable,
                "-c",
                _BACKEND_BOOTSTRAP,
                str(ROOT / "backend/src"),
                "--data-root",
                str(data_root),
                "--account-id",
                account_id.value,
            ],
            cwd=ROOT,
            check=False,
        )
        if runtime.returncode != 0:
            raise M3ExitErrorV1("m3_exit_runtime_collection_failed")

        session, runtime_run = _fresh_runtime_lineage(
            reference,
            account_id=account_id,
            gate_started_at=gate_started_at,
        )
        verify_fresh_same_account_v1(
            M3FreshLineageV1(
                gate_started_at=gate_started_at,
                quota_account_id=quota.graph.account.account_id.value,
                quota_run_id=quota.completed_run.run_id.value,
                quota_requested_at=quota.completed_run.requested_at,
                quota_completed_at=quota.completed_run.completed_at,
                quota_observation_ids=tuple(
                    item.value for item in quota.capacity_receipt.observation_ids
                ),
                runtime_account_id=session.account_id,
                runtime_run_id=runtime_run.run_id.value,
                runtime_requested_at=runtime_run.requested_at,
                runtime_completed_at=runtime_run.completed_at,
                runtime_observed_at=session.last_observed_at,
                runtime_source_id=session.provenance.source_id,
                runtime_state=runtime_run.state,
                runtime_observation_ids=tuple(
                    item.value for item in runtime_run.observation_ids
                ),
            )
        )

        identity_command, identity_environment = identity_evidence_check(
            data_root, account_id.value
        )
        _run_checkout_command(
            identity_command,
            timeout=120,
            environment=identity_environment,
        )

        _run_live_browser(data_root, account_id)
        for routine in M3_LOCAL_EXIT_ROUTINES:
            _run_checkout_command(
                [sys.executable, "tools/automation/run.py", routine],
                timeout=3_600,
            )
    except (M3ExitErrorV1, OSError, RuntimeError, TypeError, ValueError) as error:
        code = str(error)
        if not code.startswith("m3_exit_"):
            code = "m3_exit_internal_failure"
        print(f"M3 EXIT: FAILED — {code}")
        return 1
    except subprocess.TimeoutExpired:
        print("M3 EXIT: FAILED — m3_exit_timeout")
        return 1

    print(
        "M3 EXIT: PASSED — fresh same-account Claude quota/runtime/browser "
        "and local gates"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
