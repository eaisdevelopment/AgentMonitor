"""Fail-closed predecessor binding for already recorded M5 evidence."""

import re
import subprocess
from pathlib import Path

from tools.automation.implementations import m5_service_activation as activation

PREDECESSOR_REVISION = "10a7bc0db09997d92e62fb5c5e8ea7d5b85866cb"


def validate_predecessor_binding_v1(
    *,
    old_revision: str,
    archived_revision: str,
    old_pid: int,
    archived_pid: int,
    old_start: int,
    archived_start: int,
    application_changed: bool,
) -> None:
    """Require the evidence to match its activation and unchanged app source."""
    if (
        not isinstance(old_revision, str)
        or re.fullmatch(r"[0-9a-f]{40}", old_revision) is None
        or old_revision != archived_revision
        or type(old_pid) is not int
        or old_pid <= 1
        or old_pid != archived_pid
        or type(old_start) is not int
        or old_start <= 0
        or old_start != archived_start
        or application_changed is not False
    ):
        raise ValueError("m5_evidence_predecessor_invalid")


def prove_predecessor_v1(
    *,
    root: Path,
    current_revision: str,
    old_revision: str,
    old_pid: int,
    old_start: int,
) -> None:
    """Prove retained activation, exact old process, and unchanged app sources."""
    if old_revision != PREDECESSOR_REVISION or not re.fullmatch(
        r"[0-9a-f]{40}", current_revision
    ):
        raise ValueError("m5_evidence_predecessor_invalid")
    try:
        diff = (
            subprocess.run(
                [
                    "/usr/bin/git",
                    "diff",
                    "--name-only",
                    "-z",
                    old_revision,
                    current_revision,
                    "--",
                ],
                cwd=root,
                capture_output=True,
                check=True,
                timeout=10,
            )
            .stdout.decode("utf-8")
            .split("\0")
        )
        changed = [path for path in diff if path]
        application_changed = any(
            not path.startswith(("docs/", "tools/automation/", "tools/ui/"))
            for path in changed
        )
        archives = activation._retain_activation_rollover_archive_chain_v1(
            PREDECESSOR_REVISION, activation._rollback_runtime_state()
        )
        try:
            receipt = archives[-1].completed
            validate_predecessor_binding_v1(
                old_revision=old_revision,
                archived_revision=receipt.candidate_revision,
                old_pid=old_pid,
                archived_pid=receipt.main_pid,
                old_start=old_start,
                archived_start=receipt.main_pid_start_time_ticks,
                application_changed=application_changed,
            )
            activation._require_preserved_activation_rollovers_v1(
                tuple(a.retained for a in archives)
            )
        finally:
            activation._close_activation_rollover_archive_chain_v1(archives)
    except (
        OSError,
        UnicodeError,
        subprocess.SubprocessError,
        activation.M5ServiceActivationErrorV1,
        activation.M5ServiceActivationFailedV1,
    ) as error:
        raise ValueError("m5_evidence_predecessor_invalid") from error
