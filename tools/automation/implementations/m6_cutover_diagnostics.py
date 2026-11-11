"""Closed cutover diagnostics: phase and reason only, never raw exception text."""

from __future__ import annotations

import sqlite3
import subprocess

from sqlalchemy.exc import DBAPIError

PHASES = frozenset(
    {
        "preflight",
        "transition_lock",
        "journal_create",
        "guard_create",
        "guard_reload",
        "guard_verify",
        "settings_lock",
        "write_barrier",
        "guarded_preflight",
        "stop",
        "quiescence",
        "migration",
        "candidate_override",
        "candidate_start",
        "candidate_verification",
    }
)
REASONS = frozenset(
    {
        "unexpected_failure",
        "unit_not_quiescent_ready",
        "unit_identity_changed",
        "unit_identity_unavailable",
        "unit_has_children_or_not_stopped",
        "unit_changed",
        "unit_invocation_changed",
        "unit_stop_unconfirmed",
        "unit_signal_unavailable",
        "unit_unavailable",
        "unit_uid_mismatch",
        "unit_cgroup_mismatch",
        "operation_timeout",
        "lock_occupied",
        "file_already_exists",
        "filesystem_unavailable",
        "persistence_busy",
        "persistence_unavailable",
        "persistence_io_failure",
        "database_identity_changed",
        "settings_lock_missing",
        "settings_lock_unsafe",
        "settings_lock_occupied",
        "settings_lock_changed",
        "service_changed",
        "candidate_changed",
        "target_unit_changed",
        "target_guard_changed",
        "release_identity_changed",
        "candidate_schema_unavailable",
        "candidate_schema_mismatch",
        "cutover_lock_changed",
        "baseline_restart_policy_changed",
        "systemd_operation_failed",
        "systemd_identity_unavailable",
        "process_identity_unavailable",
        "migration_not_applied",
        "current_schema_unverified",
        "override_changed",
        "restart_override_changed",
        "candidate_start_unverified",
        "candidate_start_block_unverified",
        "restart_override_cleanup_failed",
        "journal_changed",
        "service_transition_lock_unavailable",
    }
)
_PREFIX = "M6 CUTOVER: BLOCKED — phase="
_SUFFIX = "; review service and journal state"


def cutover_failure_reason(error: BaseException) -> str:
    """Retain exact admitted error codes; ignore all other exception payloads."""
    original = error.orig if isinstance(error, DBAPIError) else error
    sqlite_code = getattr(original, "sqlite_errorcode", None)
    if isinstance(sqlite_code, int) and sqlite_code & 0xFF in {
        sqlite3.SQLITE_BUSY,
        sqlite3.SQLITE_LOCKED,
    }:
        return "persistence_busy"
    code = error.args[0] if len(error.args) == 1 else None
    if isinstance(code, str) and code in REASONS:
        return code
    if isinstance(error, subprocess.TimeoutExpired):
        return "operation_timeout"
    if isinstance(error, BlockingIOError):
        return "lock_occupied"
    if isinstance(error, FileExistsError):
        return "file_already_exists"
    if isinstance(error, OSError):
        return "filesystem_unavailable"
    return "unexpected_failure"


def cutover_failure_message(error: BaseException) -> str:
    """Format only validated phase/reason fields, including preflight failures."""
    phase = getattr(error, "phase", "preflight")
    reason = getattr(error, "reason", None)
    if not isinstance(phase, str) or phase not in PHASES:
        phase = "preflight"
    if not isinstance(reason, str) or reason not in REASONS:
        reason = cutover_failure_reason(error)
    return f"{_PREFIX}{phase} reason={reason}{_SUFFIX}"


def parse_cutover_failure_message(output: bytes) -> tuple[str, str] | None:
    """Accept exactly one closed wrapper message; do not expose appended output."""
    try:
        value = output.decode("utf-8").removesuffix("\n")
    except UnicodeDecodeError:
        return None
    if not value.startswith(_PREFIX) or not value.endswith(_SUFFIX):
        return None
    fields = value[len(_PREFIX) : -len(_SUFFIX)].split(" reason=")
    if len(fields) != 2 or fields[0] not in PHASES or fields[1] not in REASONS:
        return None
    return fields[0], fields[1]
