"""Activate one clean M5 checkout as the exact persistent dashboard service."""

from __future__ import annotations

import argparse
import ctypes
import errno
import hashlib
import json
import os
import re
import shlex
import sqlite3
import stat
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from tools.automation.implementations.m5_completion_lock import (
    M5CompletionLockErrorV1,
    M5CompletionLockV1,
    acquire_m5_completion_lock_v1,
    release_m5_completion_lock_v1,
    validate_m5_completion_lock_v1,
)

ROOT = Path(__file__).resolve().parents[3]
SERVICE_NAME = "agentmonitor-dashboard.service"
PINNED_ROLLBACK_REVISION = "77a3bad12a096a81587b94b8981ceee812b6445b"
DATA_ROOT = Path("/home/dev/.local/share/agentmonitor")
CONFIG_PATH = DATA_ROOT / "service.env"
DATABASE_PATH = DATA_ROOT / "agentmonitor.db"
ROLLBACK_ROOT = DATA_ROOT / "runtime" / PINNED_ROLLBACK_REVISION
UNIT_PATH = Path("/home/dev/.config/systemd/user") / SERVICE_NAME
CACHE_ROOT = DATA_ROOT / "cache/pyc"
CLAUDE_BIN_DIRECTORY = Path(
    "/home/dev/.local/share/agentmonitor/provider-tools/claude-2.1.289/"
    "node_modules/.bin"
)
CODEX_BIN_DIRECTORY = Path(
    "/home/dev/.codex/packages/standalone/releases/"
    "0.160.0-x86_64-unknown-linux-musl/bin"
)
PROVIDER_PATH = f"{CLAUDE_BIN_DIRECTORY}:{CODEX_BIN_DIRECTORY}:/usr/bin:/bin"
LOOPBACK_ORIGIN = "http://127.0.0.1:43110"
LAN_ORIGIN = "http://192.168.1.18:43110"
REQUIRED_ORIGINS = (LOOPBACK_ORIGIN, LAN_ORIGIN)
SYSTEMCTL = Path("/usr/bin/systemctl")
SYSTEMD_ANALYZE = Path("/usr/bin/systemd-analyze")
GIT = Path("/usr/bin/git")
NODE = Path("/usr/bin/node")
TRANSITION_ROOT = DATA_ROOT / "state/m5-service-activation"
CORRECTIVE_ARCHIVE_BASENAME = "m5-service-activation-corrective-archive"
CORRECTIVE_ARCHIVE_ROOT = DATA_ROOT / CORRECTIVE_ARCHIVE_BASENAME
CORRECTIVE_ROLLOVER_REVISION = "6bfa69dc13cc9e1ded9c6baa6e803cb99bc8c20b"
SECOND_CORRECTIVE_ARCHIVE_BASENAME = "m5-service-activation-corrective-archive-0634451"
SECOND_CORRECTIVE_ARCHIVE_ROOT = DATA_ROOT / SECOND_CORRECTIVE_ARCHIVE_BASENAME
SECOND_CORRECTIVE_ROLLOVER_REVISION = "063445154bca0bf5ec43db94ba57c17fd193fd99"
THIRD_CORRECTIVE_ARCHIVE_BASENAME = "m5-service-activation-corrective-archive-6d6e1aa"
THIRD_CORRECTIVE_ARCHIVE_ROOT = DATA_ROOT / THIRD_CORRECTIVE_ARCHIVE_BASENAME
THIRD_CORRECTIVE_ROLLOVER_REVISION = "6d6e1aa9d9b64d50e3f83d0f1686e6cff04b7c17"
FOURTH_CORRECTIVE_ARCHIVE_BASENAME = "m5-service-activation-corrective-archive-e066d7e"
FOURTH_CORRECTIVE_ARCHIVE_ROOT = DATA_ROOT / FOURTH_CORRECTIVE_ARCHIVE_BASENAME
FOURTH_CORRECTIVE_ROLLOVER_REVISION = "e066d7e1ba0124f0454c07002ea7b2ad0817d6b9"
FIFTH_CORRECTIVE_ARCHIVE_BASENAME = "m5-service-activation-corrective-archive-d81afab"
FIFTH_CORRECTIVE_ARCHIVE_ROOT = DATA_ROOT / FIFTH_CORRECTIVE_ARCHIVE_BASENAME
FIFTH_CORRECTIVE_ROLLOVER_REVISION = "d81afab9e5b1c1dbdb690f390e77cee66eba5437"
SIXTH_CORRECTIVE_ARCHIVE_BASENAME = "m5-service-activation-corrective-archive-8cc683d"
SIXTH_CORRECTIVE_ARCHIVE_ROOT = DATA_ROOT / SIXTH_CORRECTIVE_ARCHIVE_BASENAME
SIXTH_CORRECTIVE_ROLLOVER_REVISION = "8cc683d946b58f5eb72955e08a520195582e1a28"
SEVENTH_CORRECTIVE_ARCHIVE_BASENAME = "m5-service-activation-corrective-archive-35f50d8"
SEVENTH_CORRECTIVE_ARCHIVE_ROOT = DATA_ROOT / SEVENTH_CORRECTIVE_ARCHIVE_BASENAME
SEVENTH_CORRECTIVE_ROLLOVER_REVISION = "35f50d8c4865505a9112d8aef7ea788f425ae658"
EIGHTH_CORRECTIVE_ARCHIVE_BASENAME = "m5-service-activation-corrective-archive-1ada84f"
EIGHTH_CORRECTIVE_ARCHIVE_ROOT = DATA_ROOT / EIGHTH_CORRECTIVE_ARCHIVE_BASENAME
EIGHTH_CORRECTIVE_ROLLOVER_REVISION = "1ada84f71e827bb4f7ea966462a6cf51d050e9af"
NINTH_CORRECTIVE_ARCHIVE_BASENAME = "m5-service-activation-corrective-archive-468a937"
NINTH_CORRECTIVE_ARCHIVE_ROOT = DATA_ROOT / NINTH_CORRECTIVE_ARCHIVE_BASENAME
NINTH_CORRECTIVE_ROLLOVER_REVISION = "468a937d796efcb7ff1785a749789f07a3322abc"
TENTH_CORRECTIVE_ARCHIVE_BASENAME = "m5-service-activation-corrective-archive-10a7bc0"
TENTH_CORRECTIVE_ARCHIVE_ROOT = DATA_ROOT / TENTH_CORRECTIVE_ARCHIVE_BASENAME
TENTH_CORRECTIVE_ROLLOVER_REVISION = "10a7bc0db09997d92e62fb5c5e8ea7d5b85866cb"
ELEVENTH_CORRECTIVE_ARCHIVE_BASENAME = (
    "m5-service-activation-corrective-archive-04f8bcd"
)
ELEVENTH_CORRECTIVE_ARCHIVE_ROOT = DATA_ROOT / ELEVENTH_CORRECTIVE_ARCHIVE_BASENAME
ELEVENTH_CORRECTIVE_ROLLOVER_REVISION = "04f8bcdb1adaa4bc5352794c3bc65bcfb7137348"
TWELFTH_CORRECTIVE_ARCHIVE_BASENAME = "m5-service-activation-corrective-archive-c271d47"
TWELFTH_CORRECTIVE_ARCHIVE_ROOT = DATA_ROOT / TWELFTH_CORRECTIVE_ARCHIVE_BASENAME
TWELFTH_CORRECTIVE_ROLLOVER_REVISION = "c271d47ef6c7fe20a3ac05bca0a0c63429bc9cdb"
THIRTEENTH_CORRECTIVE_ARCHIVE_BASENAME = (
    "m5-service-activation-corrective-archive-9db4c3d"
)
THIRTEENTH_CORRECTIVE_ARCHIVE_ROOT = DATA_ROOT / THIRTEENTH_CORRECTIVE_ARCHIVE_BASENAME
THIRTEENTH_CORRECTIVE_ROLLOVER_REVISION = "9db4c3d7add4da16a46b88b6c46bb23ed7855883"
FOURTEENTH_CORRECTIVE_ARCHIVE_BASENAME = (
    "m5-service-activation-corrective-archive-b80e816"
)
FOURTEENTH_CORRECTIVE_ARCHIVE_ROOT = DATA_ROOT / FOURTEENTH_CORRECTIVE_ARCHIVE_BASENAME
FOURTEENTH_CORRECTIVE_ROLLOVER_REVISION = "b80e816f46161c106f50c14852b22b543a2a5de3"
FIFTEENTH_CORRECTIVE_ARCHIVE_BASENAME = (
    "m5-service-activation-corrective-archive-91b84b1"
)
FIFTEENTH_CORRECTIVE_ARCHIVE_ROOT = DATA_ROOT / FIFTEENTH_CORRECTIVE_ARCHIVE_BASENAME
FIFTEENTH_CORRECTIVE_ROLLOVER_REVISION = "91b84b1007337255774fe9068e806aff0a3ccdda"
CORRECTIVE_ROLLOVER_REVISIONS = (
    CORRECTIVE_ROLLOVER_REVISION,
    SECOND_CORRECTIVE_ROLLOVER_REVISION,
    THIRD_CORRECTIVE_ROLLOVER_REVISION,
    FOURTH_CORRECTIVE_ROLLOVER_REVISION,
    FIFTH_CORRECTIVE_ROLLOVER_REVISION,
    SIXTH_CORRECTIVE_ROLLOVER_REVISION,
    SEVENTH_CORRECTIVE_ROLLOVER_REVISION,
    EIGHTH_CORRECTIVE_ROLLOVER_REVISION,
    NINTH_CORRECTIVE_ROLLOVER_REVISION,
    TENTH_CORRECTIVE_ROLLOVER_REVISION,
    ELEVENTH_CORRECTIVE_ROLLOVER_REVISION,
    TWELFTH_CORRECTIVE_ROLLOVER_REVISION,
    THIRTEENTH_CORRECTIVE_ROLLOVER_REVISION,
    FOURTEENTH_CORRECTIVE_ROLLOVER_REVISION,
    FIFTEENTH_CORRECTIVE_ROLLOVER_REVISION,
)
ACTIVATION_JOURNAL_BASENAME = "activation-journal-v1.json"
ACTIVATION_LOCK_BASENAME = "activation-lock-v1"
JOURNAL_PATH = TRANSITION_ROOT / ACTIVATION_JOURNAL_BASENAME
ROLLBACK_UNIT_PATH = TRANSITION_ROOT / "rollback-unit.service"
RECEIPT_PATH = TRANSITION_ROOT / "activation-receipt.json"
BROWSER_SCRIPT = ROOT / "tools/ui/verify_m5_service_revision.mjs"
MAX_UNIT_BYTES = 32 * 1024
MAX_JSON_BYTES = 32 * 1024
MAX_ROLLBACK_RUNTIME_ENTRIES = 20_000
MAX_ROLLBACK_RUNTIME_BYTES = 512 * 1024 * 1024
MAX_ROLLBACK_RUNTIME_FILE_BYTES = 128 * 1024 * 1024
_REVISION = re.compile(r"[0-9a-f]{40}\Z")
_DIGEST = re.compile(r"[0-9a-f]{64}\Z")
_RENAME_NOREPLACE = 1
try:
    _LIBC = ctypes.CDLL(None, use_errno=True)
    _RENAMEAT2 = getattr(_LIBC, "renameat2", None)
except OSError:
    _RENAMEAT2 = None
if _RENAMEAT2 is not None:
    _RENAMEAT2.argtypes = (
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_uint,
    )
    _RENAMEAT2.restype = ctypes.c_int


class M5ServiceActivationErrorV1(ValueError):
    """A missing or ambiguous live prerequisite blocks activation."""


class M5ServiceActivationFailedV1(RuntimeError):
    """The selected implementation or activation operation failed."""


class M5ServiceActivationRollbackFailedV1(M5ServiceActivationFailedV1):
    """The trusted rollback service could not be proven restored."""


class M5ServiceActivationRerunRequiredV1(M5ServiceActivationErrorV1):
    """A corrective rollover restored trust and requires fresh live selectors."""

    def __init__(self, trusted_service_pid: int) -> None:
        if type(trusted_service_pid) is not int or trusted_service_pid <= 0:
            raise M5ServiceActivationErrorV1("m5_service_activation_rerun_invalid")
        super().__init__("m5_service_activation_rerun_required")
        self.trusted_service_pid = trusted_service_pid


class _M5ServiceRollbackDrillV1(M5ServiceActivationFailedV1):
    """Internal planned failure used to exercise the real recovery handler."""


@dataclass(frozen=True, slots=True)
class M5ServiceCandidateV1:
    unit_name: str
    unit_path: Path
    checkout_root: Path
    source_revision: str
    executable: Path
    argv: tuple[str, ...]
    config_path: Path
    data_root: Path
    environment: tuple[str, ...]
    after_units: tuple[str, ...]
    wants_units: tuple[str, ...]
    restart_policy: str
    restart_delay_seconds: int
    timeout_stop_seconds: int
    umask: str
    required_origins: tuple[str, ...]
    unit_text: str


@dataclass(frozen=True, slots=True)
class SystemdServiceObservationV1:
    unit_name: str
    fragment_path: Path
    load_state: str
    active_state: str
    sub_state: str
    unit_file_state: str
    main_pid: int
    main_pid_start_time_ticks: int
    control_group: str
    process_control_group: str
    unit_working_directory: Path
    unit_argv: tuple[str, ...]
    unit_executable: Path
    process_working_directory: Path
    process_argv: tuple[str, ...]
    process_executable: Path
    environment: tuple[str, ...]
    after_units: tuple[str, ...]
    wants_units: tuple[str, ...]
    restart_policy: str
    restart_delay_seconds: int
    timeout_stop_seconds: int
    umask: str
    source_revision: str
    ready_origins: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class UnitSnapshotV1:
    path: Path
    content: bytes
    mode: int
    digest: str
    device: int
    inode: int


@dataclass(frozen=True, slots=True)
class ActivationTransitionDecisionV1:
    """One deterministic effect or terminal result in rollback recovery."""

    phase: str
    effect: str | None
    terminal_error: str | None


@dataclass(frozen=True, slots=True)
class _DatabaseStateV1:
    device: int
    inode: int
    user_version: int
    schema_version: int
    schema_digest: str


@dataclass(frozen=True, slots=True)
class _RollbackRuntimeStateV1:
    revision: str
    root_device: int
    root_inode: int
    root_mode: int
    entry_count: int
    total_file_bytes: int
    tree_digest: str


@dataclass(frozen=True, slots=True)
class ActivationSelectorsV1:
    owner_data_root: Path
    dashboard_origin: str
    dashboard_cdp_endpoint: str
    service_pid: int


@dataclass(frozen=True, slots=True)
class M5ServiceRevisionProofV1:
    implementation_revision: str
    service_source_revision: str
    registry_digest: str


@dataclass(frozen=True, slots=True)
class ValidatedM5ServiceActivationReceiptV1:
    """Content-bound proof of the current activation and rollback material."""

    digest: str
    candidate_revision: str
    rollback_revision: str
    journal_digest: str
    rollback_unit_digest: str
    rollback_runtime_digest: str
    main_pid: int
    main_pid_start_time_ticks: int


@dataclass(frozen=True, slots=True)
class _RetainedActivationArtifactV1:
    basename: str
    descriptor: int
    identity: tuple[int, ...]
    digest: str


@dataclass(frozen=True, slots=True)
class _RetainedCompletedActivationRolloverV1:
    transition_root: Path
    archive_parent: Path
    archive_id: str
    directory_descriptor: int
    directory_device: int
    directory_inode: int
    artifacts: tuple[_RetainedActivationArtifactV1, ...]
    archive_parent_descriptor: int
    archive_parent_identity: tuple[int, ...] | None


@dataclass(frozen=True, slots=True)
class _ValidatedRetainedActivationArchiveV1:
    candidate: M5ServiceCandidateV1
    completed: ValidatedM5ServiceActivationReceiptV1
    retained: _RetainedCompletedActivationRolloverV1


def _argv(checkout_root: Path, data_root: Path = DATA_ROOT) -> tuple[str, ...]:
    return (
        str(checkout_root / "backend/.venv/bin/python"),
        "-m",
        "agentmonitor.composition.bootstrap",
        "--config",
        str(data_root / "service.env"),
        "--data-root",
        str(data_root),
        "--host",
        "127.0.0.1",
        "--port",
        "43110",
        "--authenticated-dashboard",
        "--lan-host",
        "192.168.1.18",
        "--lan-network",
        "192.168.1.0/24",
    )


def _environment(checkout_root: Path) -> tuple[str, ...]:
    return (
        f"PYTHONPATH={checkout_root}/backend/src",
        f"PYTHONPYCACHEPREFIX={CACHE_ROOT}",
        f"PATH={PROVIDER_PATH}",
    )


def _render_unit(
    checkout_root: Path,
    *,
    data_root: Path = DATA_ROOT,
    timeout_stop_seconds: int = 45,
) -> str:
    environment = _environment(checkout_root)
    return (
        "[Unit]\n"
        "Description=AgentMonitor dashboard\n"
        "After=network-online.target\n"
        "Wants=network-online.target\n\n"
        "[Service]\n"
        "Type=simple\n"
        f"WorkingDirectory={checkout_root}\n"
        f"Environment={environment[0]}\n"
        f"Environment={environment[1]}\n"
        f"Environment={environment[2]}\n"
        f"ExecStart={' '.join(_argv(checkout_root, data_root))}\n"
        "Restart=on-failure\n"
        "RestartSec=5s\n"
        f"TimeoutStopSec={timeout_stop_seconds}s\n"
        "UMask=0077\n\n"
        "[Install]\n"
        "WantedBy=default.target\n"
    )


def candidate_for_checkout_v1(
    *,
    source_revision: str,
    data_root: Path = DATA_ROOT,
    checkout_root: Path = ROOT,
    unit_path: Path = UNIT_PATH,
) -> M5ServiceCandidateV1:
    candidate = M5ServiceCandidateV1(
        unit_name=SERVICE_NAME,
        unit_path=unit_path,
        checkout_root=checkout_root,
        source_revision=source_revision,
        executable=checkout_root / "backend/.venv/bin/python",
        argv=_argv(checkout_root, data_root),
        config_path=data_root / "service.env",
        data_root=data_root,
        environment=_environment(checkout_root),
        after_units=("network-online.target",),
        wants_units=("network-online.target",),
        restart_policy="on-failure",
        restart_delay_seconds=5,
        timeout_stop_seconds=45,
        umask="0077",
        required_origins=REQUIRED_ORIGINS,
        unit_text=_render_unit(checkout_root, data_root=data_root),
    )
    validate_service_candidate_v1(candidate)
    return candidate


def validate_service_candidate_v1(candidate: M5ServiceCandidateV1) -> None:
    """Validate the closed candidate contract without touching the host service."""

    if not isinstance(candidate, M5ServiceCandidateV1):
        raise M5ServiceActivationErrorV1("m5_service_candidate_invalid")
    expected_argv = _argv(candidate.checkout_root, DATA_ROOT)
    expected_environment = _environment(candidate.checkout_root)
    expected_unit = _render_unit(candidate.checkout_root, data_root=DATA_ROOT)
    if (
        candidate.unit_name != SERVICE_NAME
        or not candidate.unit_path.is_absolute()
        or candidate.unit_path.name != SERVICE_NAME
        or not candidate.checkout_root.is_absolute()
        or _REVISION.fullmatch(candidate.source_revision) is None
        or candidate.executable != candidate.checkout_root / "backend/.venv/bin/python"
        or candidate.argv != expected_argv
        or candidate.config_path != CONFIG_PATH
        or candidate.data_root != DATA_ROOT
        or candidate.environment != expected_environment
        or candidate.after_units != ("network-online.target",)
        or candidate.wants_units != ("network-online.target",)
        or candidate.restart_policy != "on-failure"
        or candidate.restart_delay_seconds != 5
        or candidate.timeout_stop_seconds != 45
        or candidate.umask != "0077"
        or candidate.required_origins != REQUIRED_ORIGINS
        or not isinstance(candidate.unit_text, str)
        or not 1 <= len(candidate.unit_text.encode("utf-8")) <= MAX_UNIT_BYTES
        or candidate.unit_text != expected_unit
    ):
        raise M5ServiceActivationErrorV1("m5_service_candidate_invalid")


def _service_process_matches(
    candidate: M5ServiceCandidateV1,
    observation: SystemdServiceObservationV1,
) -> bool:
    expected_suffix = f"/{SERVICE_NAME}"
    return (
        observation.unit_name == candidate.unit_name
        and observation.fragment_path == candidate.unit_path
        and observation.load_state == "loaded"
        and observation.active_state == "active"
        and observation.sub_state == "running"
        and observation.unit_file_state == "enabled"
        and type(observation.main_pid) is int
        and observation.main_pid > 0
        and type(observation.main_pid_start_time_ticks) is int
        and observation.main_pid_start_time_ticks > 0
        and observation.control_group.endswith(expected_suffix)
        and observation.process_control_group == observation.control_group
        and observation.unit_working_directory == candidate.checkout_root
        and observation.process_working_directory == candidate.checkout_root
        and observation.unit_argv == candidate.argv
        and observation.process_argv == candidate.argv
        and observation.unit_executable == candidate.executable
        and observation.process_executable == candidate.executable
        and observation.environment == candidate.environment
        and observation.after_units == candidate.after_units
        and observation.wants_units == candidate.wants_units
        and observation.restart_policy == candidate.restart_policy
        and observation.restart_delay_seconds == candidate.restart_delay_seconds
        and observation.timeout_stop_seconds == candidate.timeout_stop_seconds
        and observation.umask == candidate.umask
        and observation.source_revision == candidate.source_revision
    )


def _observation_matches(
    candidate: M5ServiceCandidateV1,
    observation: SystemdServiceObservationV1,
) -> bool:
    return (
        _service_process_matches(candidate, observation)
        and observation.ready_origins == candidate.required_origins
    )


def validate_selected_systemd_service_v1(
    candidate: M5ServiceCandidateV1,
    observation: SystemdServiceObservationV1,
) -> None:
    validate_service_candidate_v1(candidate)
    if not isinstance(
        observation, SystemdServiceObservationV1
    ) or not _observation_matches(candidate, observation):
        raise M5ServiceActivationErrorV1("m5_service_selection_invalid")


def activation_decision_v1(
    candidate: M5ServiceCandidateV1,
    current: SystemdServiceObservationV1,
) -> Literal["already_active", "replace"]:
    validate_service_candidate_v1(candidate)
    if (
        current.unit_name != candidate.unit_name
        or current.fragment_path != candidate.unit_path
    ):
        raise M5ServiceActivationErrorV1("m5_service_unit_unknown")
    if _observation_matches(candidate, current):
        return "already_active"
    if (
        current.load_state == "loaded"
        and current.active_state == "active"
        and current.sub_state == "running"
        and current.unit_file_state == "enabled"
        and current.main_pid > 0
        and current.main_pid_start_time_ticks > 0
        and current.control_group.endswith(f"/{SERVICE_NAME}")
        and current.process_control_group == current.control_group
        and current.restart_policy == "on-failure"
        and current.ready_origins == candidate.required_origins
    ):
        return "replace"
    raise M5ServiceActivationErrorV1("m5_service_selection_invalid")


def activation_recovery_decision_v1(
    candidate: M5ServiceCandidateV1,
    rollback: M5ServiceCandidateV1,
    current: SystemdServiceObservationV1,
    *,
    journal_present: bool,
    receipt_present: bool,
) -> Literal["activate", "already_active", "restore_rollback", "blocked"]:
    """Classify an interrupted transition without causing an I/O effect."""

    if type(journal_present) is not bool or type(receipt_present) is not bool:
        return "blocked"
    candidate_active = _observation_matches(candidate, current)
    rollback_active = _observation_matches(rollback, current)
    if receipt_present:
        if journal_present and candidate_active:
            return "already_active"
        return "blocked"
    if journal_present:
        if candidate_active or rollback_active:
            return "restore_rollback"
        return "blocked"
    if rollback_active:
        return "activate"
    return "blocked"


def inactive_transition_recovery_decision_v1(
    candidate: M5ServiceCandidateV1,
    rollback: M5ServiceCandidateV1,
    *,
    unit_content: bytes,
    fragment_path: Path,
    active_state: str,
    main_pid: int,
    journal_present: bool,
    receipt_present: bool,
) -> Literal["restore_rollback", "blocked"]:
    """Classify an interrupted stopped unit from exact persisted unit bytes."""

    known_content = unit_content in {
        candidate.unit_text.encode("utf-8"),
        rollback.unit_text.encode("utf-8"),
    }
    if (
        journal_present
        and not receipt_present
        and known_content
        and fragment_path == candidate.unit_path == rollback.unit_path
        and active_state in {"inactive", "failed"}
        and type(main_pid) is int
        and main_pid == 0
    ):
        return "restore_rollback"
    return "blocked"


def partial_artifact_recovery_decision_v1(
    *,
    journal_present: bool,
    rollback_present: bool,
    trusted_service_active: bool,
) -> Literal["unchanged", "complete_journal", "complete_rollback_copy", "blocked"]:
    """Decide whether a pre-mutation half-write can be completed safely."""

    if not all(
        type(value) is bool
        for value in (journal_present, rollback_present, trusted_service_active)
    ):
        return "blocked"
    if journal_present == rollback_present:
        return "unchanged"
    if not trusted_service_active:
        return "blocked"
    return "complete_journal" if rollback_present else "complete_rollback_copy"


def corrective_activation_rollover_decision_v1(
    *,
    candidate_revision: str,
    completed_revision: str,
    service_revision: str,
) -> Literal["not_applicable", "rollback_candidate", "archive_restored", "blocked"]:
    """Select only the next exact approved completed-activation correction."""

    if not all(
        isinstance(value, str) and _REVISION.fullmatch(value) is not None
        for value in (candidate_revision, completed_revision, service_revision)
    ):
        return "blocked"
    if candidate_revision == completed_revision:
        return "not_applicable"
    if completed_revision not in CORRECTIVE_ROLLOVER_REVISIONS:
        return "blocked"
    completed_index = CORRECTIVE_ROLLOVER_REVISIONS.index(completed_revision)
    if completed_index < len(CORRECTIVE_ROLLOVER_REVISIONS) - 1:
        if candidate_revision != CORRECTIVE_ROLLOVER_REVISIONS[completed_index + 1]:
            return "blocked"
    elif candidate_revision == PINNED_ROLLBACK_REVISION or (
        candidate_revision in CORRECTIVE_ROLLOVER_REVISIONS
    ):
        return "blocked"
    if service_revision == completed_revision:
        return "rollback_candidate"
    if service_revision == PINNED_ROLLBACK_REVISION:
        return "archive_restored"
    return "blocked"


def completed_activation_rollover_generation_v1(
    *,
    completed_revision: str,
    service_revision: str,
    receipt_main_pid: int,
    receipt_start_time_ticks: int,
    current_main_pid: int,
    current_start_time_ticks: int,
) -> Literal["receipt_generation", "restarted_generation", "blocked"]:
    """Accept a proven same-revision systemd restart without rewriting evidence."""

    process_values = (
        receipt_main_pid,
        receipt_start_time_ticks,
        current_main_pid,
        current_start_time_ticks,
    )
    if (
        not isinstance(completed_revision, str)
        or _REVISION.fullmatch(completed_revision) is None
        or service_revision != completed_revision
        or any(type(value) is not int or value <= 0 for value in process_values)
    ):
        return "blocked"
    if (
        receipt_main_pid == current_main_pid
        and receipt_start_time_ticks == current_start_time_ticks
    ):
        return "receipt_generation"
    return "restarted_generation"


def corrective_rollover_browser_expectation_v1(
    *,
    service_revision: str,
    candidate_revision: str,
) -> tuple[str, bool]:
    """Select baseline proof only for the trusted extracted rollback runtime."""

    if not all(
        isinstance(value, str) and _REVISION.fullmatch(value) is not None
        for value in (service_revision, candidate_revision)
    ):
        raise M5ServiceActivationErrorV1("m5_service_rollover_service_invalid")
    if service_revision == PINNED_ROLLBACK_REVISION:
        return service_revision, False
    if service_revision == candidate_revision:
        return service_revision, True
    raise M5ServiceActivationErrorV1("m5_service_rollover_service_invalid")


def corrective_rollover_rerun_decision_v1(
    *,
    transition_state: str,
    candidate_revision: str,
    journal_candidate_revision: str | None,
) -> Literal["rerun", "blocked"]:
    """Allow the normal typed rerun only after persisting the exact candidate."""

    if (
        transition_state == "prepared"
        and _REVISION.fullmatch(candidate_revision) is not None
        and journal_candidate_revision == candidate_revision
    ):
        return "rerun"
    return "blocked"


def _corrective_rollover_archive_basename_v1(prior_revision: str) -> str:
    """Return the fixed archive namespace for one approved prior revision."""

    if prior_revision == CORRECTIVE_ROLLOVER_REVISION:
        return CORRECTIVE_ARCHIVE_BASENAME
    if prior_revision == SECOND_CORRECTIVE_ROLLOVER_REVISION:
        return SECOND_CORRECTIVE_ARCHIVE_BASENAME
    if prior_revision == THIRD_CORRECTIVE_ROLLOVER_REVISION:
        return THIRD_CORRECTIVE_ARCHIVE_BASENAME
    if prior_revision == FOURTH_CORRECTIVE_ROLLOVER_REVISION:
        return FOURTH_CORRECTIVE_ARCHIVE_BASENAME
    if prior_revision == FIFTH_CORRECTIVE_ROLLOVER_REVISION:
        return FIFTH_CORRECTIVE_ARCHIVE_BASENAME
    if prior_revision == SIXTH_CORRECTIVE_ROLLOVER_REVISION:
        return SIXTH_CORRECTIVE_ARCHIVE_BASENAME
    if prior_revision == SEVENTH_CORRECTIVE_ROLLOVER_REVISION:
        return SEVENTH_CORRECTIVE_ARCHIVE_BASENAME
    if prior_revision == EIGHTH_CORRECTIVE_ROLLOVER_REVISION:
        return EIGHTH_CORRECTIVE_ARCHIVE_BASENAME
    if prior_revision == NINTH_CORRECTIVE_ROLLOVER_REVISION:
        return NINTH_CORRECTIVE_ARCHIVE_BASENAME
    if prior_revision == TENTH_CORRECTIVE_ROLLOVER_REVISION:
        return TENTH_CORRECTIVE_ARCHIVE_BASENAME
    if prior_revision == ELEVENTH_CORRECTIVE_ROLLOVER_REVISION:
        return ELEVENTH_CORRECTIVE_ARCHIVE_BASENAME
    if prior_revision == TWELFTH_CORRECTIVE_ROLLOVER_REVISION:
        return TWELFTH_CORRECTIVE_ARCHIVE_BASENAME
    if prior_revision == THIRTEENTH_CORRECTIVE_ROLLOVER_REVISION:
        return THIRTEENTH_CORRECTIVE_ARCHIVE_BASENAME
    if prior_revision == FOURTEENTH_CORRECTIVE_ROLLOVER_REVISION:
        return FOURTEENTH_CORRECTIVE_ARCHIVE_BASENAME
    if prior_revision == FIFTEENTH_CORRECTIVE_ROLLOVER_REVISION:
        return FIFTEENTH_CORRECTIVE_ARCHIVE_BASENAME
    raise M5ServiceActivationErrorV1("m5_service_rollover_archive_invalid")


def _corrective_rollover_chain_revisions_v1(
    latest_revision: str,
) -> tuple[str, ...]:
    """Return the closed ordered prefix ending at one approved revision."""

    try:
        latest_index = CORRECTIVE_ROLLOVER_REVISIONS.index(latest_revision)
    except ValueError:
        raise M5ServiceActivationErrorV1(
            "m5_service_rollover_archive_invalid"
        ) from None
    return CORRECTIVE_ROLLOVER_REVISIONS[: latest_index + 1]


def corrective_rollover_transition_policy_v1(
    *,
    receipt_revision: str | None,
    candidate_revision: str,
    archive_states: tuple[str, ...],
) -> tuple[Literal["none", "retain", "archive", "retry", "blocked"], str | None]:
    """Require one exact archive prefix for the approved rollover sequence."""

    if (
        _REVISION.fullmatch(candidate_revision) is None
        or (
            receipt_revision is not None
            and _REVISION.fullmatch(receipt_revision) is None
        )
        or len(archive_states) != len(CORRECTIVE_ROLLOVER_REVISIONS)
        or any(
            state not in {"absent", "empty", "complete", "invalid"}
            for state in archive_states
        )
    ):
        return "blocked", None

    def stable_prefix(length: int) -> tuple[str, ...]:
        return ("complete",) * length + ("absent",) * (
            len(CORRECTIVE_ROLLOVER_REVISIONS) - length
        )

    def candidate_follows(index: int) -> bool:
        if index < len(CORRECTIVE_ROLLOVER_REVISIONS) - 1:
            return candidate_revision == CORRECTIVE_ROLLOVER_REVISIONS[index + 1]
        return candidate_revision != PINNED_ROLLBACK_REVISION and (
            candidate_revision not in CORRECTIVE_ROLLOVER_REVISIONS
        )

    if receipt_revision is None:
        if archive_states == stable_prefix(0):
            return "none", None
        for prefix_length in range(1, len(CORRECTIVE_ROLLOVER_REVISIONS) + 1):
            if archive_states == stable_prefix(prefix_length):
                latest_index = prefix_length - 1
                if candidate_follows(latest_index):
                    return "retry", CORRECTIVE_ROLLOVER_REVISIONS[latest_index]
                return "blocked", None
        return "blocked", None

    if receipt_revision == candidate_revision:
        if candidate_revision == PINNED_ROLLBACK_REVISION:
            return "blocked", None
        if candidate_revision in CORRECTIVE_ROLLOVER_REVISIONS:
            expected_prefix_length = CORRECTIVE_ROLLOVER_REVISIONS.index(
                candidate_revision
            )
        else:
            expected_prefix_length = len(CORRECTIVE_ROLLOVER_REVISIONS)
        if archive_states != stable_prefix(expected_prefix_length):
            return "blocked", None
        if expected_prefix_length == 0:
            return "none", None
        return (
            "retain",
            CORRECTIVE_ROLLOVER_REVISIONS[expected_prefix_length - 1],
        )

    if receipt_revision not in CORRECTIVE_ROLLOVER_REVISIONS:
        return "blocked", None
    completed_index = CORRECTIVE_ROLLOVER_REVISIONS.index(receipt_revision)
    expected_states = list(stable_prefix(completed_index))
    expected_states[completed_index] = archive_states[completed_index]
    if (
        archive_states[completed_index] not in {"absent", "empty"}
        or archive_states != tuple(expected_states)
        or not candidate_follows(completed_index)
    ):
        return "blocked", None
    return "archive", receipt_revision


def _corrective_rollover_archive_root_v1(prior_revision: str) -> Path:
    """Return the fixed production archive root for an approved revision."""

    basename = _corrective_rollover_archive_basename_v1(prior_revision)
    return DATA_ROOT / basename


def _corrective_rollover_archive_parent_state_v1(
    *,
    archive_parent: Path,
    prior_revision: str,
) -> Literal["absent", "empty", "complete", "invalid"]:
    """Classify only the fixed private archive parent and its entry count."""

    try:
        archive_basename = _corrective_rollover_archive_basename_v1(prior_revision)
        if (
            not archive_parent.is_absolute()
            or archive_parent.name != archive_basename
            or archive_parent.parent.is_symlink()
            or archive_parent.parent.resolve(strict=True) != archive_parent.parent
        ):
            raise OSError
        try:
            archive_parent.lstat()
        except FileNotFoundError:
            return "absent"
        if (
            archive_parent.is_symlink()
            or archive_parent.resolve(strict=True) != archive_parent
        ):
            raise OSError
        descriptor = os.open(
            archive_parent,
            os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
        )
        try:
            metadata = os.fstat(descriptor)
            current = archive_parent.lstat()
            entries = os.listdir(descriptor)
            if (
                not stat.S_ISDIR(metadata.st_mode)
                or metadata.st_uid != os.getuid()
                or stat.S_IMODE(metadata.st_mode) != 0o700
                or _stable_stat_identity(metadata) != _stable_stat_identity(current)
            ):
                raise OSError
            if not entries:
                return "empty"
            if len(entries) == 1 and re.fullmatch(
                rf"{re.escape(prior_revision)}-[0-9a-f]{{64}}",
                entries[0],
            ):
                return "complete"
            return "invalid"
        finally:
            os.close(descriptor)
    except (OSError, TypeError, ValueError):
        return "invalid"


def activation_transition_step_v1(
    phase: str,
    event: str,
    *,
    original_failure: str,
) -> ActivationTransitionDecisionV1:
    """Reduce one activation failure into the next ordered rollback effect."""

    if re.fullmatch(r"[a-z0-9_]{1,128}", original_failure) is None:
        raise M5ServiceActivationErrorV1("m5_service_transition_invalid")
    if phase in {"candidate_starting", "candidate_finalizing"} and event == "failed":
        return ActivationTransitionDecisionV1(
            "rollback_verifying_runtime_before_stop",
            "verify_rollback_runtime",
            None,
        )
    succeeded = {
        "rollback_verifying_runtime_before_stop": (
            "rollback_stopping_candidate",
            "stop_candidate",
        ),
        "rollback_stopping_candidate": (
            "rollback_restoring_unit",
            "restore_unit",
        ),
        "rollback_restoring_unit": (
            "rollback_reloading_unit",
            "daemon_reload",
        ),
        "rollback_reloading_unit": (
            "rollback_verifying_runtime_before_start",
            "verify_rollback_runtime",
        ),
        "rollback_verifying_runtime_before_start": (
            "rollback_starting_previous",
            "start_previous",
        ),
        "rollback_starting_previous": (
            "rollback_verifying_previous",
            "verify_previous",
        ),
        "rollback_verifying_previous": (
            "rollback_verifying_runtime_after_start",
            "verify_rollback_runtime",
        ),
    }
    if event == "succeeded" and phase in succeeded:
        next_phase, effect = succeeded[phase]
        return ActivationTransitionDecisionV1(next_phase, effect, None)
    if event == "succeeded" and phase == "rollback_verifying_runtime_after_start":
        return ActivationTransitionDecisionV1(
            "rollback_complete", None, original_failure
        )
    if event == "failed" and phase.startswith("rollback_"):
        return ActivationTransitionDecisionV1(
            "rollback_failed", None, "m5_service_activation_rollback_failed"
        )
    raise M5ServiceActivationErrorV1("m5_service_transition_invalid")


def _safe_regular_file(path: Path, *, maximum: int) -> tuple[os.stat_result, bytes]:
    descriptor = -1
    try:
        descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
        info = os.fstat(descriptor)
        current = path.lstat()
        if (
            not stat.S_ISREG(info.st_mode)
            or info.st_uid != os.getuid()
            or info.st_nlink != 1
            or stat.S_IMODE(info.st_mode) != 0o600
            or not 1 <= info.st_size <= maximum
            or (info.st_dev, info.st_ino) != (current.st_dev, current.st_ino)
        ):
            raise OSError
        content = os.read(descriptor, maximum + 1)
        if len(content) != info.st_size:
            raise OSError
        return info, content
    except OSError:
        raise M5ServiceActivationErrorV1("m5_service_unit_invalid") from None
    finally:
        if descriptor >= 0:
            os.close(descriptor)


def _stable_stat_identity(info: os.stat_result) -> tuple[int, ...]:
    return (
        info.st_dev,
        info.st_ino,
        info.st_mode,
        info.st_uid,
        info.st_gid,
        info.st_nlink,
        info.st_size,
        info.st_mtime_ns,
        info.st_ctime_ns,
    )


def _read_retained_artifact_digest_v1(
    descriptor: int,
    metadata: os.stat_result,
) -> str:
    os.lseek(descriptor, 0, os.SEEK_SET)
    remaining = metadata.st_size
    digest = hashlib.sha256()
    while remaining:
        chunk = os.read(descriptor, min(64 * 1024, remaining))
        if not chunk:
            raise OSError
        digest.update(chunk)
        remaining -= len(chunk)
    if os.read(descriptor, 1):
        raise OSError
    return digest.hexdigest()


def _validate_retained_activation_rollover_v1(
    retained: _RetainedCompletedActivationRolloverV1,
    *,
    canonical_path_required: bool,
) -> None:
    directory = os.fstat(retained.directory_descriptor)
    if (
        not stat.S_ISDIR(directory.st_mode)
        or directory.st_uid != os.getuid()
        or stat.S_IMODE(directory.st_mode) != 0o700
        or (directory.st_dev, directory.st_ino)
        != (retained.directory_device, retained.directory_inode)
        or set(os.listdir(retained.directory_descriptor))
        != {artifact.basename for artifact in retained.artifacts}
    ):
        raise OSError
    if retained.archive_parent_descriptor >= 0:
        if retained.archive_parent_identity is None:
            raise OSError
        archive_parent = os.fstat(retained.archive_parent_descriptor)
        current_archive_parent = retained.archive_parent.lstat()
        archived_entry = os.stat(
            retained.archive_id,
            dir_fd=retained.archive_parent_descriptor,
            follow_symlinks=False,
        )
        if (
            not stat.S_ISDIR(archive_parent.st_mode)
            or archive_parent.st_uid != os.getuid()
            or stat.S_IMODE(archive_parent.st_mode) != 0o700
            or _stable_stat_identity(archive_parent) != retained.archive_parent_identity
            or _stable_stat_identity(current_archive_parent)
            != retained.archive_parent_identity
            or archive_parent.st_dev != directory.st_dev
            or set(os.listdir(retained.archive_parent_descriptor))
            != {retained.archive_id}
            or (archived_entry.st_dev, archived_entry.st_ino)
            != (retained.directory_device, retained.directory_inode)
        ):
            raise OSError
    elif retained.archive_parent_identity is not None:
        raise OSError
    if canonical_path_required:
        current = retained.transition_root.lstat()
        if (current.st_dev, current.st_ino) != (
            retained.directory_device,
            retained.directory_inode,
        ):
            raise OSError
    for artifact in retained.artifacts:
        metadata = os.fstat(artifact.descriptor)
        current = os.stat(
            artifact.basename,
            dir_fd=retained.directory_descriptor,
            follow_symlinks=False,
        )
        if (
            _stable_stat_identity(metadata) != artifact.identity
            or _stable_stat_identity(current) != artifact.identity
            or _read_retained_artifact_digest_v1(artifact.descriptor, metadata)
            != artifact.digest
            or _stable_stat_identity(os.fstat(artifact.descriptor)) != artifact.identity
        ):
            raise OSError


def _require_retained_activation_rollover_v1(
    retained: _RetainedCompletedActivationRolloverV1,
    *,
    canonical_path_required: bool,
) -> None:
    try:
        _validate_retained_activation_rollover_v1(
            retained,
            canonical_path_required=canonical_path_required,
        )
    except OSError:
        raise M5ServiceActivationErrorV1(
            "m5_service_rollover_artifact_changed"
        ) from None


def _require_preserved_activation_rollovers_v1(
    preserved_rollovers: tuple[_RetainedCompletedActivationRolloverV1, ...],
) -> None:
    """Reprove and sync immutable prior archives around every mutation."""

    try:
        seen: set[tuple[int, int]] = set()
        for retained in preserved_rollovers:
            identity = (retained.directory_device, retained.directory_inode)
            if (
                identity in seen
                or retained.archive_parent_descriptor < 0
                or retained.archive_parent_identity is None
            ):
                raise OSError
            seen.add(identity)
            _validate_retained_activation_rollover_v1(
                retained,
                canonical_path_required=True,
            )
            os.fsync(retained.directory_descriptor)
            os.fsync(retained.archive_parent_descriptor)
            _validate_retained_activation_rollover_v1(
                retained,
                canonical_path_required=True,
            )
    except (OSError, TypeError, ValueError):
        raise M5ServiceActivationErrorV1(
            "m5_service_rollover_artifact_changed"
        ) from None


def _retain_completed_activation_rollover_v1(
    *,
    transition_root: Path,
    archive_parent: Path,
    prior_revision: str,
    receipt_digest: str,
    journal_digest: str,
    rollback_unit_digest: str,
) -> _RetainedCompletedActivationRolloverV1:
    """Retain the exact complete activation directory across trusted rollback."""

    directory_descriptor = -1
    archive_parent_descriptor = -1
    artifact_descriptors: list[int] = []
    try:
        archive_id = f"{prior_revision}-{receipt_digest}"
        archive_basename = _corrective_rollover_archive_basename_v1(prior_revision)
        source_location = (
            transition_root.name == TRANSITION_ROOT.name
            and transition_root.parent.name == "state"
            and archive_parent == transition_root.parent.parent / archive_basename
        )
        archived_location = (
            transition_root.name == archive_id
            and transition_root.parent == archive_parent
            and archive_parent.name == archive_basename
        )
        if (
            not transition_root.is_absolute()
            or not (source_location or archived_location)
            or _DIGEST.fullmatch(receipt_digest) is None
            or _DIGEST.fullmatch(journal_digest) is None
            or _DIGEST.fullmatch(rollback_unit_digest) is None
            or transition_root.parent.is_symlink()
            or transition_root.parent.resolve(strict=True) != transition_root.parent
            or transition_root.is_symlink()
            or transition_root.resolve(strict=True) != transition_root
        ):
            raise OSError
        archive_parent_identity: tuple[int, ...] | None = None
        if archived_location:
            archive_parent_descriptor = os.open(
                archive_parent,
                os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
            )
            archive_parent_metadata = os.fstat(archive_parent_descriptor)
            current_archive_parent = archive_parent.lstat()
            if (
                not stat.S_ISDIR(archive_parent_metadata.st_mode)
                or archive_parent_metadata.st_uid != os.getuid()
                or stat.S_IMODE(archive_parent_metadata.st_mode) != 0o700
                or _stable_stat_identity(current_archive_parent)
                != _stable_stat_identity(archive_parent_metadata)
                or set(os.listdir(archive_parent_descriptor)) != {archive_id}
            ):
                raise OSError
            archive_parent_identity = _stable_stat_identity(archive_parent_metadata)
            directory_descriptor = os.open(
                archive_id,
                os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
                dir_fd=archive_parent_descriptor,
            )
            current_directory = os.stat(
                archive_id,
                dir_fd=archive_parent_descriptor,
                follow_symlinks=False,
            )
        else:
            directory_descriptor = os.open(
                transition_root,
                os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
            )
            current_directory = transition_root.lstat()
        directory = os.fstat(directory_descriptor)
        expected_digests = {
            ACTIVATION_JOURNAL_BASENAME: (journal_digest, MAX_JSON_BYTES),
            ROLLBACK_UNIT_PATH.name: (rollback_unit_digest, MAX_UNIT_BYTES),
            RECEIPT_PATH.name: (receipt_digest, MAX_JSON_BYTES),
        }
        if (
            not stat.S_ISDIR(directory.st_mode)
            or directory.st_uid != os.getuid()
            or stat.S_IMODE(directory.st_mode) != 0o700
            or (directory.st_dev, directory.st_ino)
            != (current_directory.st_dev, current_directory.st_ino)
            or set(os.listdir(directory_descriptor)) != set(expected_digests)
        ):
            raise OSError
        artifacts: list[_RetainedActivationArtifactV1] = []
        for basename in sorted(expected_digests):
            expected_digest, maximum = expected_digests[basename]
            descriptor = os.open(
                basename,
                os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC,
                dir_fd=directory_descriptor,
            )
            artifact_descriptors.append(descriptor)
            metadata = os.fstat(descriptor)
            current = os.stat(
                basename,
                dir_fd=directory_descriptor,
                follow_symlinks=False,
            )
            identity = _stable_stat_identity(metadata)
            if (
                not stat.S_ISREG(metadata.st_mode)
                or metadata.st_uid != os.getuid()
                or stat.S_IMODE(metadata.st_mode) != 0o600
                or metadata.st_nlink != 1
                or metadata.st_dev != directory.st_dev
                or not 1 <= metadata.st_size <= maximum
                or _stable_stat_identity(current) != identity
                or _read_retained_artifact_digest_v1(descriptor, metadata)
                != expected_digest
                or _stable_stat_identity(os.fstat(descriptor)) != identity
            ):
                raise OSError
            artifacts.append(
                _RetainedActivationArtifactV1(
                    basename,
                    descriptor,
                    identity,
                    expected_digest,
                )
            )
        result = _RetainedCompletedActivationRolloverV1(
            transition_root,
            archive_parent,
            archive_id,
            directory_descriptor,
            directory.st_dev,
            directory.st_ino,
            tuple(artifacts),
            archive_parent_descriptor,
            archive_parent_identity,
        )
        _validate_retained_activation_rollover_v1(
            result,
            canonical_path_required=True,
        )
        directory_descriptor = -1
        archive_parent_descriptor = -1
        artifact_descriptors.clear()
        return result
    except (OSError, TypeError, ValueError):
        raise M5ServiceActivationErrorV1(
            "m5_service_rollover_artifact_invalid"
        ) from None
    finally:
        for descriptor in artifact_descriptors:
            try:
                os.close(descriptor)
            except OSError:
                pass
        if directory_descriptor >= 0:
            os.close(directory_descriptor)
        if archive_parent_descriptor >= 0:
            os.close(archive_parent_descriptor)


def _retain_archived_activation_rollover_after_commit_v1(
    retained: _RetainedCompletedActivationRolloverV1,
) -> _RetainedCompletedActivationRolloverV1:
    """Reopen and retain the committed archive through its fixed parent."""

    try:
        prior_revision, separator, receipt_digest = retained.archive_id.partition("-")
        artifact_digests = {
            artifact.basename: artifact.digest for artifact in retained.artifacts
        }
        if (
            separator != "-"
            or prior_revision not in CORRECTIVE_ROLLOVER_REVISIONS
            or _DIGEST.fullmatch(receipt_digest) is None
            or artifact_digests.get(RECEIPT_PATH.name) != receipt_digest
            or set(artifact_digests)
            != {
                ACTIVATION_JOURNAL_BASENAME,
                ROLLBACK_UNIT_PATH.name,
                RECEIPT_PATH.name,
            }
        ):
            raise M5ServiceActivationErrorV1("m5_service_rollover_archive_invalid")
        return _retain_completed_activation_rollover_v1(
            transition_root=retained.archive_parent / retained.archive_id,
            archive_parent=retained.archive_parent,
            prior_revision=prior_revision,
            receipt_digest=receipt_digest,
            journal_digest=artifact_digests[ACTIVATION_JOURNAL_BASENAME],
            rollback_unit_digest=artifact_digests[ROLLBACK_UNIT_PATH.name],
        )
    except (KeyError, TypeError, ValueError):
        raise M5ServiceActivationErrorV1(
            "m5_service_rollover_archive_invalid"
        ) from None


def _select_completed_activation_rollover_archive_v1(
    *,
    archive_parent: Path = CORRECTIVE_ARCHIVE_ROOT,
    prior_revision: str = CORRECTIVE_ROLLOVER_REVISION,
) -> tuple[Path, str]:
    """Select exactly one private, complete corrective archive directory."""

    custody_descriptor = -1
    archive_descriptor = -1
    completed_descriptor = -1
    try:
        custody_root = archive_parent.parent
        archive_basename = _corrective_rollover_archive_basename_v1(prior_revision)
        if (
            not archive_parent.is_absolute()
            or archive_parent.name != archive_basename
            or custody_root.is_symlink()
            or custody_root.resolve(strict=True) != custody_root
            or archive_parent.is_symlink()
            or archive_parent.resolve(strict=True) != archive_parent
        ):
            raise OSError
        custody_descriptor = os.open(
            custody_root,
            os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
        )
        custody = os.fstat(custody_descriptor)
        custody_entry = custody_root.lstat()
        archive_descriptor = os.open(
            archive_parent.name,
            os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
            dir_fd=custody_descriptor,
        )
        archive = os.fstat(archive_descriptor)
        archive_entry = os.stat(
            archive_parent.name,
            dir_fd=custody_descriptor,
            follow_symlinks=False,
        )
        entries = os.listdir(archive_descriptor)
        if len(entries) != 1:
            raise OSError
        match = re.fullmatch(
            rf"{re.escape(prior_revision)}-([0-9a-f]{{64}})",
            entries[0],
        )
        if (
            match is None
            or not stat.S_ISDIR(custody.st_mode)
            or custody.st_uid != os.getuid()
            or stat.S_IMODE(custody.st_mode) != 0o700
            or (custody.st_dev, custody.st_ino)
            != (custody_entry.st_dev, custody_entry.st_ino)
            or not stat.S_ISDIR(archive.st_mode)
            or archive.st_uid != os.getuid()
            or stat.S_IMODE(archive.st_mode) != 0o700
            or archive.st_dev != custody.st_dev
            or (archive.st_dev, archive.st_ino)
            != (archive_entry.st_dev, archive_entry.st_ino)
        ):
            raise OSError
        completed_descriptor = os.open(
            entries[0],
            os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
            dir_fd=archive_descriptor,
        )
        completed = os.fstat(completed_descriptor)
        completed_entry = os.stat(
            entries[0],
            dir_fd=archive_descriptor,
            follow_symlinks=False,
        )
        expected_artifacts = {
            ACTIVATION_JOURNAL_BASENAME,
            ROLLBACK_UNIT_PATH.name,
            RECEIPT_PATH.name,
        }
        if (
            not stat.S_ISDIR(completed.st_mode)
            or completed.st_uid != os.getuid()
            or stat.S_IMODE(completed.st_mode) != 0o700
            or completed.st_dev != archive.st_dev
            or (completed.st_dev, completed.st_ino)
            != (completed_entry.st_dev, completed_entry.st_ino)
            or set(os.listdir(completed_descriptor)) != expected_artifacts
        ):
            raise OSError
        return archive_parent / entries[0], match.group(1)
    except (OSError, TypeError, ValueError):
        raise M5ServiceActivationErrorV1(
            "m5_service_rollover_archive_invalid"
        ) from None
    finally:
        for descriptor in (
            completed_descriptor,
            archive_descriptor,
            custody_descriptor,
        ):
            if descriptor >= 0:
                try:
                    os.close(descriptor)
                except OSError:
                    pass


def _close_completed_activation_rollover_v1(
    retained: _RetainedCompletedActivationRolloverV1,
) -> None:
    """Close retained rollover custody without mutating its artifacts."""

    for artifact in retained.artifacts:
        try:
            os.close(artifact.descriptor)
        except OSError:
            pass
    try:
        os.close(retained.directory_descriptor)
    except OSError:
        pass
    if retained.archive_parent_descriptor >= 0:
        try:
            os.close(retained.archive_parent_descriptor)
        except OSError:
            pass


def _rename_activation_rollover_noreplace_v1(
    source_name: str,
    target_name: str,
    *,
    source_directory_descriptor: int,
    target_directory_descriptor: int,
) -> None:
    if (
        _RENAMEAT2 is None
        or Path(source_name).name != source_name
        or Path(target_name).name != target_name
    ):
        raise M5ServiceActivationErrorV1(
            "m5_service_rollover_atomic_noreplace_unavailable"
        )
    ctypes.set_errno(0)
    result = _RENAMEAT2(
        source_directory_descriptor,
        os.fsencode(source_name),
        target_directory_descriptor,
        os.fsencode(target_name),
        _RENAME_NOREPLACE,
    )
    if result == 0:
        return
    error_number = ctypes.get_errno()
    if error_number == errno.EEXIST:
        raise FileExistsError(error_number, os.strerror(error_number), target_name)
    if error_number in {
        errno.EINVAL,
        errno.ENOSYS,
        errno.ENOTSUP,
        errno.EOPNOTSUPP,
    }:
        raise M5ServiceActivationErrorV1(
            "m5_service_rollover_atomic_noreplace_unavailable"
        )
    raise OSError(error_number, os.strerror(error_number), source_name)


def _archive_completed_activation_rollover_v1(
    retained: _RetainedCompletedActivationRolloverV1,
    *,
    preserved_rollovers: tuple[_RetainedCompletedActivationRolloverV1, ...] = (),
) -> str:
    """Commit one completed transition by an atomic whole-directory move."""

    state_descriptor = -1
    custody_descriptor = -1
    archive_descriptor = -1
    fresh_descriptor = -1
    committed_retained: _RetainedCompletedActivationRolloverV1 | None = None
    committed = False
    try:
        if (
            retained.transition_root.name != TRANSITION_ROOT.name
            or retained.transition_root.parent.name != "state"
        ):
            raise M5ServiceActivationErrorV1("m5_service_rollover_archive_invalid")
        _require_retained_activation_rollover_v1(
            retained,
            canonical_path_required=True,
        )
        _require_preserved_activation_rollovers_v1(preserved_rollovers)
        state_root = retained.transition_root.parent
        custody_root = state_root.parent
        state_descriptor = os.open(
            state_root,
            os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
        )
        state = os.fstat(state_descriptor)
        current_state = state_root.lstat()
        custody_descriptor = os.open(
            custody_root,
            os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
        )
        custody = os.fstat(custody_descriptor)
        current_custody = custody_root.lstat()
        if (
            state_root.is_symlink()
            or state_root.resolve(strict=True) != state_root
            or not stat.S_ISDIR(state.st_mode)
            or state.st_uid != os.getuid()
            or (state.st_dev, state.st_ino)
            != (current_state.st_dev, current_state.st_ino)
            or state.st_dev != retained.directory_device
            or custody_root.is_symlink()
            or custody_root.resolve(strict=True) != custody_root
            or not stat.S_ISDIR(custody.st_mode)
            or custody.st_uid != os.getuid()
            or stat.S_IMODE(custody.st_mode) != 0o700
            or (custody.st_dev, custody.st_ino)
            != (current_custody.st_dev, current_custody.st_ino)
            or custody.st_dev != state.st_dev
        ):
            raise OSError
        _require_preserved_activation_rollovers_v1(preserved_rollovers)
        try:
            os.mkdir(
                retained.archive_parent.name,
                0o700,
                dir_fd=custody_descriptor,
            )
        except FileExistsError:
            pass
        _require_preserved_activation_rollovers_v1(preserved_rollovers)
        archive_descriptor = os.open(
            retained.archive_parent.name,
            os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
            dir_fd=custody_descriptor,
        )
        archive = os.fstat(archive_descriptor)
        archive_entry = os.stat(
            retained.archive_parent.name,
            dir_fd=custody_descriptor,
            follow_symlinks=False,
        )
        if (
            not stat.S_ISDIR(archive.st_mode)
            or archive.st_uid != os.getuid()
            or stat.S_IMODE(archive.st_mode) != 0o700
            or archive.st_dev != state.st_dev
            or (archive.st_dev, archive.st_ino)
            != (archive_entry.st_dev, archive_entry.st_ino)
        ):
            raise OSError
        if os.listdir(archive_descriptor):
            raise FileExistsError
        _require_retained_activation_rollover_v1(
            retained,
            canonical_path_required=True,
        )
        source_entry = os.stat(
            retained.transition_root.name,
            dir_fd=state_descriptor,
            follow_symlinks=False,
        )
        current_state_entry = os.stat(
            state_root.name,
            dir_fd=custody_descriptor,
            follow_symlinks=False,
        )
        current_archive_entry = os.stat(
            retained.archive_parent.name,
            dir_fd=custody_descriptor,
            follow_symlinks=False,
        )
        if (
            (source_entry.st_dev, source_entry.st_ino)
            != (retained.directory_device, retained.directory_inode)
            or (current_state_entry.st_dev, current_state_entry.st_ino)
            != (state.st_dev, state.st_ino)
            or (current_archive_entry.st_dev, current_archive_entry.st_ino)
            != (archive.st_dev, archive.st_ino)
        ):
            raise OSError
        os.fsync(retained.directory_descriptor)
        if os.listdir(archive_descriptor):
            raise FileExistsError
        _require_preserved_activation_rollovers_v1(preserved_rollovers)
        _rename_activation_rollover_noreplace_v1(
            retained.transition_root.name,
            retained.archive_id,
            source_directory_descriptor=state_descriptor,
            target_directory_descriptor=archive_descriptor,
        )
        committed = True
        _require_preserved_activation_rollovers_v1(preserved_rollovers)
        archived_entry = os.stat(
            retained.archive_id,
            dir_fd=archive_descriptor,
            follow_symlinks=False,
        )
        if (archived_entry.st_dev, archived_entry.st_ino) != (
            retained.directory_device,
            retained.directory_inode,
        ) or set(os.listdir(archive_descriptor)) != {retained.archive_id}:
            raise OSError
        current_state_entry = os.stat(
            state_root.name,
            dir_fd=custody_descriptor,
            follow_symlinks=False,
        )
        current_archive_entry = os.stat(
            retained.archive_parent.name,
            dir_fd=custody_descriptor,
            follow_symlinks=False,
        )
        if (current_state_entry.st_dev, current_state_entry.st_ino) != (
            state.st_dev,
            state.st_ino,
        ) or (current_archive_entry.st_dev, current_archive_entry.st_ino) != (
            archive.st_dev,
            archive.st_ino,
        ):
            raise OSError
        _require_retained_activation_rollover_v1(
            retained,
            canonical_path_required=False,
        )
        os.fsync(retained.directory_descriptor)
        os.fsync(archive_descriptor)
        os.fsync(state_descriptor)
        os.fsync(custody_descriptor)
        _require_preserved_activation_rollovers_v1(preserved_rollovers)
        os.mkdir(retained.transition_root.name, 0o700, dir_fd=state_descriptor)
        _require_preserved_activation_rollovers_v1(preserved_rollovers)
        fresh_descriptor = os.open(
            retained.transition_root.name,
            os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
            dir_fd=state_descriptor,
        )
        fresh = os.fstat(fresh_descriptor)
        fresh_entry = os.stat(
            retained.transition_root.name,
            dir_fd=state_descriptor,
            follow_symlinks=False,
        )
        if (
            not stat.S_ISDIR(fresh.st_mode)
            or fresh.st_uid != os.getuid()
            or stat.S_IMODE(fresh.st_mode) != 0o700
            or fresh.st_dev != state.st_dev
            or (fresh.st_dev, fresh.st_ino) != (fresh_entry.st_dev, fresh_entry.st_ino)
            or os.listdir(fresh_descriptor)
        ):
            raise OSError
        os.fsync(fresh_descriptor)
        os.fsync(state_descriptor)
        committed_retained = _retain_archived_activation_rollover_after_commit_v1(
            retained
        )
        _require_preserved_activation_rollovers_v1(
            (*preserved_rollovers, committed_retained)
        )
        return retained.archive_id
    except FileExistsError:
        reason = (
            "m5_service_rollover_archive_committed"
            if committed
            else "m5_service_rollover_archive_exists"
        )
        raise M5ServiceActivationErrorV1(reason) from None
    except M5ServiceActivationErrorV1:
        raise
    except (OSError, TypeError, ValueError):
        reason = (
            "m5_service_rollover_archive_committed"
            if committed
            else "m5_service_rollover_archive_invalid"
        )
        raise M5ServiceActivationErrorV1(reason) from None
    finally:
        if committed_retained is not None:
            _close_completed_activation_rollover_v1(committed_retained)
        for descriptor in (
            fresh_descriptor,
            archive_descriptor,
            custody_descriptor,
            state_descriptor,
        ):
            if descriptor >= 0:
                try:
                    os.close(descriptor)
                except OSError:
                    pass


def _runtime_regular_file_digest(
    path: Path,
    *,
    maximum: int,
    permitted_owners: frozenset[int],
) -> tuple[os.stat_result, str]:
    descriptor = -1
    try:
        descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
        before = os.fstat(descriptor)
        current = path.lstat()
        if (
            not stat.S_ISREG(before.st_mode)
            or before.st_uid not in permitted_owners
            or before.st_nlink != 1
            or before.st_size < 0
            or before.st_size > maximum
            or _stable_stat_identity(before) != _stable_stat_identity(current)
        ):
            raise OSError
        digest = hashlib.sha256()
        remaining = before.st_size
        while remaining:
            chunk = os.read(descriptor, min(1024 * 1024, remaining))
            if not chunk:
                raise OSError
            digest.update(chunk)
            remaining -= len(chunk)
        if os.read(descriptor, 1):
            raise OSError
        after = os.fstat(descriptor)
        current_after = path.lstat()
        if _stable_stat_identity(after) != _stable_stat_identity(
            before
        ) or _stable_stat_identity(current_after) != _stable_stat_identity(before):
            raise OSError
        return before, digest.hexdigest()
    except OSError:
        raise M5ServiceActivationErrorV1(
            "m5_service_rollback_runtime_invalid"
        ) from None
    finally:
        if descriptor >= 0:
            os.close(descriptor)


def _rollback_runtime_marker(root: Path, expected_revision: str) -> bytes:
    path = root / ".agentmonitor-runtime"
    descriptor = -1
    try:
        descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
        info = os.fstat(descriptor)
        current = path.lstat()
        if (
            not stat.S_ISREG(info.st_mode)
            or info.st_uid != os.getuid()
            or info.st_nlink != 1
            or stat.S_IMODE(info.st_mode) != 0o600
            or not 1 <= info.st_size <= 512
            or _stable_stat_identity(info) != _stable_stat_identity(current)
        ):
            raise OSError
        content = os.read(descriptor, 513)
        after = os.fstat(descriptor)
        current_after = path.lstat()
        if (
            len(content) != info.st_size
            or _stable_stat_identity(after) != _stable_stat_identity(info)
            or _stable_stat_identity(current_after) != _stable_stat_identity(info)
            or re.fullmatch(
                expected_revision.encode("ascii") + rb" [0-9a-f]{64} [0-9a-f]{64}\n",
                content,
            )
            is None
        ):
            raise OSError
        return content
    except (OSError, UnicodeError):
        raise M5ServiceActivationErrorV1(
            "m5_service_rollback_runtime_invalid"
        ) from None
    finally:
        if descriptor >= 0:
            os.close(descriptor)


def _rollback_runtime_snapshot_once(
    root: Path,
    expected_revision: str,
) -> _RollbackRuntimeStateV1:
    """Hash exact rollback-tree entries without following in-tree links."""

    try:
        root_info = root.lstat()
        if (
            _REVISION.fullmatch(expected_revision) is None
            or root.is_symlink()
            or not stat.S_ISDIR(root_info.st_mode)
            or root_info.st_uid != os.getuid()
            or stat.S_IMODE(root_info.st_mode) != 0o700
            or root.resolve(strict=True) != root
        ):
            raise OSError
    except OSError:
        raise M5ServiceActivationErrorV1(
            "m5_service_rollback_runtime_invalid"
        ) from None

    digest = hashlib.sha256()
    entry_count = 0
    total_file_bytes = 0

    def record(relative: str, kind: str, info: os.stat_result) -> None:
        material = (
            relative,
            kind,
            info.st_dev,
            info.st_ino,
            stat.S_IMODE(info.st_mode),
            info.st_uid,
            info.st_gid,
            info.st_nlink,
            info.st_size,
            info.st_mtime_ns,
            info.st_ctime_ns,
        )
        digest.update(
            json.dumps(material, ensure_ascii=True, separators=(",", ":")).encode(
                "ascii"
            )
        )
        digest.update(b"\0")

    def visit(directory: Path, relative_parent: Path) -> None:
        nonlocal entry_count, total_file_bytes
        before = directory.lstat()
        if (
            directory.is_symlink()
            or not stat.S_ISDIR(before.st_mode)
            or before.st_uid != os.getuid()
            or before.st_dev != root_info.st_dev
        ):
            raise OSError
        names_before = sorted(os.listdir(directory), key=os.fsencode)
        for name in names_before:
            if not name or name in {".", ".."} or "\0" in name:
                raise OSError
            path = directory / name
            relative_path = relative_parent / name
            relative = relative_path.as_posix()
            info = path.lstat()
            if info.st_uid != os.getuid() or info.st_dev != root_info.st_dev:
                raise OSError
            entry_count += 1
            if entry_count > MAX_ROLLBACK_RUNTIME_ENTRIES:
                raise OSError
            if stat.S_ISDIR(info.st_mode):
                record(relative, "directory", info)
                visit(path, relative_path)
            elif stat.S_ISREG(info.st_mode):
                file_info, file_digest = _runtime_regular_file_digest(
                    path,
                    maximum=MAX_ROLLBACK_RUNTIME_FILE_BYTES,
                    permitted_owners=frozenset({os.getuid()}),
                )
                total_file_bytes += file_info.st_size
                if total_file_bytes > MAX_ROLLBACK_RUNTIME_BYTES:
                    raise OSError
                record(relative, "file", file_info)
                digest.update(file_digest.encode("ascii"))
                digest.update(b"\0")
            elif stat.S_ISLNK(info.st_mode):
                target = os.readlink(path)
                if len(os.fsencode(target)) > 4096 or path.lstat() != info:
                    raise OSError
                record(relative, "symlink", info)
                digest.update(os.fsencode(target))
                digest.update(b"\0")
            else:
                raise OSError
        after = directory.lstat()
        if (
            _stable_stat_identity(after) != _stable_stat_identity(before)
            or sorted(os.listdir(directory), key=os.fsencode) != names_before
        ):
            raise OSError

    try:
        record(".", "directory", root_info)
        visit(root, Path())
        executable = root / "backend/.venv/bin/python"
        executable_target = executable.resolve(strict=True)
        target_info, target_digest = _runtime_regular_file_digest(
            executable_target,
            maximum=MAX_ROLLBACK_RUNTIME_FILE_BYTES,
            permitted_owners=frozenset({0, os.getuid()}),
        )
        if target_info.st_mode & 0o022 or not os.access(executable_target, os.X_OK):
            raise OSError
        record(str(executable_target), "resolved-executable", target_info)
        digest.update(target_digest.encode("ascii"))
        digest.update(b"\0")
        root_after = root.lstat()
        if _stable_stat_identity(root_after) != _stable_stat_identity(root_info):
            raise OSError
    except (OSError, M5ServiceActivationErrorV1):
        raise M5ServiceActivationErrorV1(
            "m5_service_rollback_runtime_invalid"
        ) from None
    return _RollbackRuntimeStateV1(
        expected_revision,
        root_info.st_dev,
        root_info.st_ino,
        stat.S_IMODE(root_info.st_mode),
        entry_count,
        total_file_bytes,
        digest.hexdigest(),
    )


def _rollback_runtime_state(
    root: Path = ROLLBACK_ROOT,
    expected_revision: str = PINNED_ROLLBACK_REVISION,
) -> _RollbackRuntimeStateV1:
    """Return one stable, content-bound snapshot of the trusted runtime."""

    marker_before = _rollback_runtime_marker(root, expected_revision)
    first = _rollback_runtime_snapshot_once(root, expected_revision)
    marker_after = _rollback_runtime_marker(root, expected_revision)
    second = _rollback_runtime_snapshot_once(root, expected_revision)
    if marker_before != marker_after or first != second:
        raise M5ServiceActivationErrorV1("m5_service_rollback_runtime_changed")
    return first


def _require_rollback_runtime_state(expected: _RollbackRuntimeStateV1) -> None:
    try:
        observed = _rollback_runtime_state()
    except M5ServiceActivationErrorV1:
        raise M5ServiceActivationFailedV1(
            "m5_service_rollback_material_changed"
        ) from None
    if observed != expected:
        raise M5ServiceActivationFailedV1("m5_service_rollback_material_changed")


def _require_transition_stop_state(
    revision: str,
    rollback_runtime_state: _RollbackRuntimeStateV1,
) -> None:
    """Reprove both immutable inputs at the immediate pre-stop boundary."""

    _require_revision(revision)
    _require_rollback_runtime_state(rollback_runtime_state)
    _require_revision(revision)


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _atomic_replace(path: Path, content: bytes, mode: int) -> None:
    descriptor = -1
    temporary: Path | None = None
    try:
        descriptor, raw = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
        temporary = Path(raw)
        os.fchmod(descriptor, mode)
        with os.fdopen(descriptor, "wb") as stream:
            descriptor = -1
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        temporary = None
        _fsync_directory(path.parent)
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def install_candidate_unit_v1(candidate: M5ServiceCandidateV1) -> UnitSnapshotV1 | None:
    """Atomically install an owner-only unit and return its exact prior snapshot."""

    validate_service_candidate_v1(candidate)
    try:
        parent = candidate.unit_path.parent.lstat()
        if (
            not stat.S_ISDIR(parent.st_mode)
            or candidate.unit_path.parent.is_symlink()
            or parent.st_uid != os.getuid()
        ):
            raise OSError
        info, previous = _safe_regular_file(candidate.unit_path, maximum=MAX_UNIT_BYTES)
        replacement = candidate.unit_text.encode("utf-8")
        if previous == replacement:
            return None
        snapshot = UnitSnapshotV1(
            candidate.unit_path,
            previous,
            stat.S_IMODE(info.st_mode),
            hashlib.sha256(previous).hexdigest(),
            info.st_dev,
            info.st_ino,
        )
        current = candidate.unit_path.lstat()
        if (current.st_dev, current.st_ino, current.st_mtime_ns, current.st_size) != (
            info.st_dev,
            info.st_ino,
            info.st_mtime_ns,
            info.st_size,
        ):
            raise M5ServiceActivationErrorV1("m5_service_unit_changed")
        _atomic_replace(candidate.unit_path, replacement, 0o600)
        return snapshot
    except M5ServiceActivationErrorV1:
        raise
    except OSError:
        raise M5ServiceActivationErrorV1("m5_service_unit_invalid") from None


def restore_unit_snapshot_v1(snapshot: UnitSnapshotV1) -> None:
    """Restore an exact unit snapshot with a same-directory atomic replacement."""

    if (
        not isinstance(snapshot, UnitSnapshotV1)
        or not snapshot.path.is_absolute()
        or snapshot.path.name != SERVICE_NAME
        or snapshot.mode != 0o600
        or type(snapshot.device) is not int
        or snapshot.device < 0
        or type(snapshot.inode) is not int
        or snapshot.inode <= 0
        or not 1 <= len(snapshot.content) <= MAX_UNIT_BYTES
        or hashlib.sha256(snapshot.content).hexdigest() != snapshot.digest
    ):
        raise M5ServiceActivationFailedV1("m5_service_rollback_failed")
    try:
        _atomic_replace(snapshot.path, snapshot.content, snapshot.mode)
        _, restored = _safe_regular_file(snapshot.path, maximum=MAX_UNIT_BYTES)
        if restored != snapshot.content:
            raise OSError
    except (M5ServiceActivationErrorV1, OSError):
        raise M5ServiceActivationFailedV1("m5_service_rollback_failed") from None


def validate_rollback_systemd_service_v1(
    candidate: M5ServiceCandidateV1,
    observation: SystemdServiceObservationV1,
) -> None:
    if not isinstance(candidate, M5ServiceCandidateV1) or not _observation_matches(
        candidate, observation
    ):
        raise M5ServiceActivationFailedV1("m5_service_rollback_failed")


def validate_receipt_systemd_ownership_v1(
    candidate: M5ServiceCandidateV1,
    *,
    restarted_main_pid: int,
    restarted_start_time_ticks: int,
    observation: SystemdServiceObservationV1,
) -> None:
    try:
        validate_selected_systemd_service_v1(candidate, observation)
        if (
            type(restarted_main_pid) is not int
            or restarted_main_pid <= 0
            or type(restarted_start_time_ticks) is not int
            or restarted_start_time_ticks <= 0
            or observation.main_pid != restarted_main_pid
            or observation.main_pid_start_time_ticks != restarted_start_time_ticks
        ):
            raise M5ServiceActivationErrorV1("m5_service_selection_invalid")
    except M5ServiceActivationErrorV1:
        raise M5ServiceActivationFailedV1("m5_service_receipt_binding_failed") from None


def _systemd_environment() -> dict[str, str]:
    return {
        "PATH": "/usr/bin:/bin",
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "XDG_RUNTIME_DIR": f"/run/user/{os.getuid()}",
    }


def _run_systemctl(
    *arguments: str, timeout: int = 60
) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            (str(SYSTEMCTL), "--user", *arguments),
            cwd=ROOT,
            env=_systemd_environment(),
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout,
        )
    except (OSError, subprocess.SubprocessError):
        raise M5ServiceActivationFailedV1("m5_service_systemd_unavailable") from None


def _systemctl_ok(*arguments: str, timeout: int = 60) -> None:
    result = _run_systemctl(*arguments, timeout=timeout)
    if result.returncode != 0 or len(result.stdout) > 8192 or len(result.stderr) > 8192:
        raise M5ServiceActivationFailedV1("m5_service_systemd_failed")


def _parse_exec_start(value: str) -> tuple[str, ...]:
    try:
        if value.count("{ path=") != 1 or " ; argv[]=" not in value:
            raise ValueError
        shown = value.split(" ; argv[]=", 1)[1].split(" ; ignore_errors=", 1)[0]
        return tuple(shlex.split(shown))
    except (IndexError, ValueError):
        raise M5ServiceActivationErrorV1("m5_service_unit_invalid") from None


def _parse_seconds(value: str) -> int:
    match = re.fullmatch(r"([1-9][0-9]{0,5})s", value)
    if match is None:
        raise M5ServiceActivationErrorV1("m5_service_unit_invalid")
    return int(match.group(1))


def _process_start_ticks(pid: int) -> int:
    try:
        process = Path(f"/proc/{pid}")
        if process.stat().st_uid != os.getuid():
            raise OSError
        raw = (process / "stat").read_bytes()
        if len(raw) > 16_384:
            raise OSError
        fields = raw.decode("ascii").rsplit(") ", 1)[1].split()
        value = int(fields[19])
        if value <= 0:
            raise OSError
        return value
    except (IndexError, OSError, UnicodeError, ValueError):
        raise M5ServiceActivationErrorV1("m5_service_process_invalid") from None


def _process_argv(pid: int) -> tuple[str, ...]:
    try:
        raw = Path(f"/proc/{pid}/cmdline").read_bytes()
        if not raw or len(raw) > 8192 or not raw.endswith(b"\0"):
            raise OSError
        return tuple(item.decode("utf-8") for item in raw[:-1].split(b"\0"))
    except (OSError, UnicodeError):
        raise M5ServiceActivationErrorV1("m5_service_process_invalid") from None


def _process_cgroup(pid: int) -> str:
    try:
        raw = Path(f"/proc/{pid}/cgroup").read_bytes()
        fields = raw.decode("ascii").strip().split(":", 2)
        if len(raw) > 4096 or len(fields) != 3 or fields[:2] != ["0", ""]:
            raise OSError
        return fields[2]
    except (OSError, UnicodeError):
        raise M5ServiceActivationErrorV1("m5_service_process_invalid") from None


def _ready_origins(origins: tuple[str, ...]) -> tuple[str, ...]:
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    ready: list[str] = []
    for origin in origins:
        try:
            with opener.open(origin + "/", timeout=2) as response:
                if response.status == 200:
                    ready.append(origin)
        except (OSError, urllib.error.URLError):
            continue
    return tuple(ready)


def _systemd_properties() -> dict[str, str]:
    names = (
        "FragmentPath,LoadState,ActiveState,SubState,UnitFileState,MainPID,"
        "ControlGroup,WorkingDirectory,ExecStart,Environment,After,Wants,Restart,"
        "RestartUSec,TimeoutStopUSec,UMask"
    )
    result = _run_systemctl("show", SERVICE_NAME, f"--property={names}")
    if result.returncode != 0 or result.stderr or len(result.stdout) > 32_768:
        raise M5ServiceActivationErrorV1("m5_service_unit_invalid")
    try:
        return dict(
            line.split("=", 1) for line in result.stdout.splitlines() if "=" in line
        )
    except ValueError:
        raise M5ServiceActivationErrorV1("m5_service_unit_invalid") from None


def observe_selected_systemd_service_v1(
    candidate: M5ServiceCandidateV1,
) -> SystemdServiceObservationV1:
    """Read systemd and /proc independently for the exact fixed dashboard unit."""

    properties = _systemd_properties()
    try:
        pid = int(properties["MainPID"])
        command = _parse_exec_start(properties["ExecStart"])
        process_command = _process_argv(pid)
        process_root = Path(f"/proc/{pid}/cwd").resolve(strict=True)
        process_start = _process_start_ticks(pid)
        process_control_group = _process_cgroup(pid)
        # `/proc/<pid>/exe` resolves a venv's Python link; cmdline keeps the
        # selected launch entry point needed for the unit/root binding.
        resolved_executable = Path(f"/proc/{pid}/exe").resolve(strict=True)
        if resolved_executable != candidate.executable.resolve(strict=True):
            raise OSError
        after = frozenset(properties["After"].split())
        wants = frozenset(properties["Wants"].split())
        if (
            not set(candidate.after_units) <= after
            or not set(candidate.wants_units) <= wants
        ):
            raise OSError
        _, loaded_unit = _safe_regular_file(
            Path(properties["FragmentPath"]), maximum=MAX_UNIT_BYTES
        )
        if loaded_unit != candidate.unit_text.encode("utf-8"):
            raise OSError
        ready_origins = _ready_origins(candidate.required_origins)
        properties_after = _systemd_properties()
        if (
            properties_after != properties
            or int(properties_after["MainPID"]) != pid
            or _process_start_ticks(pid) != process_start
            or _process_cgroup(pid) != process_control_group
            or _process_argv(pid) != process_command
            or Path(f"/proc/{pid}/cwd").resolve(strict=True) != process_root
            or Path(f"/proc/{pid}/exe").resolve(strict=True) != resolved_executable
        ):
            raise OSError
        observation = SystemdServiceObservationV1(
            unit_name=SERVICE_NAME,
            fragment_path=Path(properties["FragmentPath"]),
            load_state=properties["LoadState"],
            active_state=properties["ActiveState"],
            sub_state=properties["SubState"],
            unit_file_state=properties["UnitFileState"],
            main_pid=pid,
            main_pid_start_time_ticks=process_start,
            control_group=properties["ControlGroup"],
            process_control_group=process_control_group,
            unit_working_directory=Path(properties["WorkingDirectory"]),
            unit_argv=command,
            unit_executable=Path(command[0]),
            process_working_directory=process_root,
            process_argv=process_command,
            process_executable=Path(process_command[0]),
            environment=tuple(shlex.split(properties["Environment"])),
            after_units=candidate.after_units,
            wants_units=candidate.wants_units,
            restart_policy=properties["Restart"],
            restart_delay_seconds=_parse_seconds(properties["RestartUSec"]),
            timeout_stop_seconds=_parse_seconds(properties["TimeoutStopUSec"]),
            umask=properties["UMask"],
            source_revision=candidate.source_revision,
            ready_origins=ready_origins,
        )
    except (KeyError, OSError, ValueError):
        raise M5ServiceActivationErrorV1("m5_service_process_invalid") from None
    return observation


def _wait_for_candidate(
    candidate: M5ServiceCandidateV1, *, timeout_seconds: float = 45
) -> SystemdServiceObservationV1:
    deadline = time.monotonic() + timeout_seconds
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            observation = observe_selected_systemd_service_v1(candidate)
            validate_selected_systemd_service_v1(candidate, observation)
            return observation
        except (M5ServiceActivationErrorV1, OSError) as error:
            last_error = error
            time.sleep(0.25)
    raise M5ServiceActivationFailedV1("m5_service_readiness_failed") from last_error


def restart_selected_systemd_service_v1(
    candidate: M5ServiceCandidateV1,
    selected: SystemdServiceObservationV1,
) -> SystemdServiceObservationV1:
    """Restart the exact selected dashboard through its owning user manager."""

    validate_selected_systemd_service_v1(candidate, selected)
    current = observe_selected_systemd_service_v1(candidate)
    validate_selected_systemd_service_v1(candidate, current)
    if (
        current.main_pid != selected.main_pid
        or current.main_pid_start_time_ticks != selected.main_pid_start_time_ticks
    ):
        raise M5ServiceActivationErrorV1("m5_service_selection_changed")
    _systemctl_ok("restart", SERVICE_NAME, timeout=60)
    restarted = _wait_for_candidate(candidate)
    if (
        restarted.main_pid == selected.main_pid
        and restarted.main_pid_start_time_ticks == selected.main_pid_start_time_ticks
    ):
        raise M5ServiceActivationFailedV1("m5_service_restart_generation_unchanged")
    return restarted


def clean_detached_revision_v1(root: Path = ROOT) -> str:
    """Return one stable clean detached Git revision without provider access."""

    environment = {
        "PATH": "/usr/bin:/bin",
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "GIT_OPTIONAL_LOCKS": "0",
    }

    def run(*arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            (str(GIT), *arguments),
            cwd=root,
            env=environment,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            check=False,
            timeout=15,
        )

    try:
        root_info = root.lstat()
        resolved_root = root.resolve(strict=True)
        if (
            root.is_symlink()
            or not stat.S_ISDIR(root_info.st_mode)
            or root_info.st_uid != os.getuid()
            or resolved_root != root
            or resolved_root == Path("/")
            or any(
                resolved_root == unsafe or unsafe in resolved_root.parents
                for unsafe in (Path("/tmp"), Path("/var/tmp"), Path("/dev/shm"))
            )
        ):
            raise OSError
        top_before = run("rev-parse", "--show-toplevel")
        before = run("rev-parse", "--verify", "HEAD^{commit}")
        detached = run("symbolic-ref", "-q", "HEAD")
        status = run("status", "--porcelain=v1", "--untracked-files=all")
        after = run("rev-parse", "--verify", "HEAD^{commit}")
        top_after = run("rev-parse", "--show-toplevel")
    except (OSError, subprocess.SubprocessError):
        raise M5ServiceActivationErrorV1("m5_service_checkout_invalid") from None
    revision = before.stdout.strip()
    if (
        top_before.returncode
        or before.returncode
        or status.returncode
        or after.returncode
        or top_after.returncode
        or before.stderr
        or status.stderr
        or after.stderr
        or top_before.stderr
        or top_after.stderr
        or detached.returncode != 1
        or detached.stdout
        or detached.stderr
        or _REVISION.fullmatch(revision) is None
        or after.stdout.strip() != revision
        or status.stdout
        or Path(top_before.stdout.strip()) != resolved_root
        or Path(top_after.stdout.strip()) != resolved_root
    ):
        raise M5ServiceActivationErrorV1("m5_service_checkout_not_clean")
    return revision


def require_clean_detached_revision_v1(
    expected_revision: str,
    *,
    root: Path = ROOT,
) -> None:
    """Fail when a detached clean checkout no longer has its selected revision."""

    if (
        _REVISION.fullmatch(expected_revision) is None
        or clean_detached_revision_v1(root) != expected_revision
    ):
        raise M5ServiceActivationErrorV1("m5_service_checkout_changed")


def _read_clean_revision(root: Path) -> str:
    """Compatibility alias for existing private activation code."""

    return clean_detached_revision_v1(root)


def revalidate_current_systemd_binding_v1(
    candidate: M5ServiceCandidateV1,
    *,
    selected_pid: int,
    selected_start_time_ticks: int,
) -> SystemdServiceObservationV1:
    """Reprove one detached revision and exact current service generation."""

    validate_service_candidate_v1(candidate)
    if (
        type(selected_pid) is not int
        or selected_pid <= 0
        or type(selected_start_time_ticks) is not int
        or selected_start_time_ticks <= 0
        or clean_detached_revision_v1(candidate.checkout_root)
        != candidate.source_revision
    ):
        raise M5ServiceActivationErrorV1("m5_service_selection_invalid")
    observation = observe_selected_systemd_service_v1(candidate)
    validate_selected_systemd_service_v1(candidate, observation)
    if (
        observation.main_pid != selected_pid
        or observation.main_pid_start_time_ticks != selected_start_time_ticks
    ):
        raise M5ServiceActivationErrorV1("m5_service_selection_changed")
    return observation


def select_current_systemd_binding_v1(
    *,
    source_revision: str,
    data_root: Path,
    selected_pid: int,
    selected_start_time_ticks: int,
    checkout_root: Path = ROOT,
) -> tuple[M5ServiceCandidateV1, SystemdServiceObservationV1]:
    """Select a clean detached checkout and exact live systemd generation."""

    if (
        data_root != DATA_ROOT
        or clean_detached_revision_v1(checkout_root) != source_revision
    ):
        raise M5ServiceActivationErrorV1("m5_service_selection_invalid")
    candidate = candidate_for_checkout_v1(
        source_revision=source_revision,
        data_root=data_root,
        checkout_root=checkout_root,
    )
    observation = revalidate_current_systemd_binding_v1(
        candidate,
        selected_pid=selected_pid,
        selected_start_time_ticks=selected_start_time_ticks,
    )
    return candidate, observation


def _selectors(environment: Mapping[str, str]) -> ActivationSelectorsV1:
    required = (
        "AGENTMONITOR_TEST_OWNER_DATA_ROOT",
        "AGENTMONITOR_TEST_DASHBOARD_ORIGIN",
        "AGENTMONITOR_TEST_DASHBOARD_CDP_ENDPOINT",
        "AGENTMONITOR_M5_SERVICE_PID",
    )
    if not all(environment.get(key) for key in required):
        raise M5ServiceActivationErrorV1("m5_service_live_selectors_required")
    try:
        root = Path(environment[required[0]])
        root_info = root.lstat()
        origin = environment[required[1]]
        endpoint = environment[required[2]]
        pid_text = environment[required[3]]
        endpoint_url = urlsplit(endpoint)
        if (
            root != DATA_ROOT
            or root.resolve(strict=True) != DATA_ROOT
            or not stat.S_ISDIR(root_info.st_mode)
            or root_info.st_uid != os.getuid()
            or stat.S_IMODE(root_info.st_mode) != 0o700
            or origin != LOOPBACK_ORIGIN
            or endpoint_url.scheme != "http"
            or endpoint_url.hostname != "127.0.0.1"
            or endpoint_url.port is None
            or endpoint_url.path not in {"", "/"}
            or endpoint_url.query
            or endpoint_url.fragment
            or re.fullmatch(r"(?:0|[1-9][0-9]{0,9})", pid_text) is None
        ):
            raise OSError
    except (OSError, TypeError, ValueError):
        raise M5ServiceActivationErrorV1("m5_service_live_selectors_invalid") from None
    return ActivationSelectorsV1(root, origin, endpoint, int(pid_text))


def _ensure_private_transition_root_v1(transition_root: Path) -> None:
    """Create or revalidate the owner-only fixed transition custody root."""

    try:
        if not transition_root.is_absolute():
            raise OSError
        transition_root.mkdir(mode=0o700, parents=True, exist_ok=True)
        info = transition_root.lstat()
        if (
            transition_root.is_symlink()
            or transition_root.resolve(strict=True) != transition_root
            or not stat.S_ISDIR(info.st_mode)
            or info.st_uid != os.getuid()
            or stat.S_IMODE(info.st_mode) != 0o700
        ):
            raise OSError
    except OSError:
        raise M5ServiceActivationErrorV1("m5_service_activation_lock_invalid") from None


def acquire_m5_service_activation_lock_v1(
    transition_root: Path = TRANSITION_ROOT,
) -> M5CompletionLockV1:
    """Acquire one nonblocking kernel guard for the fixed dashboard service."""

    _ensure_private_transition_root_v1(transition_root)
    try:
        return acquire_m5_completion_lock_v1(transition_root / ACTIVATION_LOCK_BASENAME)
    except M5CompletionLockErrorV1 as error:
        reason = (
            "m5_service_activation_busy"
            if str(error) == "m5_completion_lock_busy"
            else "m5_service_activation_lock_invalid"
        )
        raise M5ServiceActivationErrorV1(reason) from None


def validate_m5_service_activation_lock_v1(lock: M5CompletionLockV1) -> None:
    """Fail when the held kernel guard or its private custody root changed."""

    try:
        validate_m5_completion_lock_v1(lock)
    except M5CompletionLockErrorV1:
        raise M5ServiceActivationErrorV1("m5_service_activation_lock_changed") from None


def release_m5_service_activation_lock_v1(lock: M5CompletionLockV1) -> None:
    """Release the process-held service transition guard."""

    try:
        release_m5_completion_lock_v1(lock)
    except OSError:
        raise M5ServiceActivationErrorV1("m5_service_activation_lock_invalid") from None


def select_m5_service_activation_result_v1(
    body_error: BaseException | None,
    cleanup_error: M5ServiceActivationErrorV1 | None,
) -> BaseException | None:
    """Preserve the transition result; use cleanup failure only without one."""

    return body_error if body_error is not None else cleanup_error


def _validate_owner_files() -> None:
    try:
        for path in (CONFIG_PATH, DATABASE_PATH):
            info = path.lstat()
            if (
                path.is_symlink()
                or not stat.S_ISREG(info.st_mode)
                or info.st_uid != os.getuid()
                or info.st_nlink != 1
                or stat.S_IMODE(info.st_mode) != 0o600
            ):
                raise OSError
        for executable in (
            CLAUDE_BIN_DIRECTORY / "claude",
            CODEX_BIN_DIRECTORY / "codex",
        ):
            resolved = executable.resolve(strict=True)
            info = resolved.lstat()
            if (
                not stat.S_ISREG(info.st_mode)
                or info.st_mode & 0o022
                or not os.access(resolved, os.X_OK)
            ):
                raise OSError
    except OSError:
        raise M5ServiceActivationErrorV1("m5_service_runtime_invalid") from None


_JOURNAL_KEYS = frozenset(
    {
        "schema",
        "phase",
        "unit_name",
        "previous_unit_sha256",
        "previous_unit_mode",
        "previous_unit_device",
        "previous_unit_inode",
        "previous_main_pid",
        "previous_main_pid_start_time_ticks",
        "previous_source_revision",
        "candidate_source_revision",
        "preserved_launch_sha256",
    }
)


def _preserved_launch_digest(
    candidate: M5ServiceCandidateV1,
    rollback: M5ServiceCandidateV1,
) -> str:
    """Bind fields that the bounded transition is not permitted to change."""

    if (
        candidate.unit_name != rollback.unit_name
        or candidate.unit_path != rollback.unit_path
        or candidate.argv[1:] != rollback.argv[1:]
        or candidate.config_path != rollback.config_path
        or candidate.data_root != rollback.data_root
        or candidate.environment[1:] != rollback.environment[1:]
        or candidate.after_units != rollback.after_units
        or candidate.wants_units != rollback.wants_units
        or candidate.restart_policy != rollback.restart_policy
        or candidate.restart_delay_seconds != rollback.restart_delay_seconds
        or candidate.umask != rollback.umask
        or candidate.required_origins != rollback.required_origins
        or candidate.timeout_stop_seconds != 45
        or rollback.timeout_stop_seconds not in (30, 45)
    ):
        raise M5ServiceActivationErrorV1("m5_service_journal_invalid")
    material = {
        "unit_name": candidate.unit_name,
        "unit_path": str(candidate.unit_path),
        "argv_tail": candidate.argv[1:],
        "config_path": str(candidate.config_path),
        "data_root": str(candidate.data_root),
        "environment_tail": candidate.environment[1:],
        "after_units": candidate.after_units,
        "wants_units": candidate.wants_units,
        "restart_policy": candidate.restart_policy,
        "restart_delay_seconds": candidate.restart_delay_seconds,
        "umask": candidate.umask,
        "required_origins": candidate.required_origins,
    }
    encoded = json.dumps(material, sort_keys=True, separators=(",", ":")).encode(
        "ascii"
    )
    return hashlib.sha256(encoded).hexdigest()


def build_activation_journal_v1(
    candidate: M5ServiceCandidateV1,
    rollback: M5ServiceCandidateV1,
    observation: SystemdServiceObservationV1,
    snapshot: UnitSnapshotV1,
    *,
    phase: str,
) -> dict[str, object]:
    """Build the closed, sanitized journal document before service mutation."""

    validate_service_candidate_v1(candidate)
    if (
        not isinstance(rollback, M5ServiceCandidateV1)
        or not isinstance(snapshot, UnitSnapshotV1)
        or phase != "prepared"
        or snapshot.path != candidate.unit_path
        or snapshot.path != rollback.unit_path
        or snapshot.content != rollback.unit_text.encode("utf-8")
        or snapshot.mode != 0o600
        or hashlib.sha256(snapshot.content).hexdigest() != snapshot.digest
        or type(snapshot.device) is not int
        or snapshot.device < 0
        or type(snapshot.inode) is not int
        or snapshot.inode <= 0
        or not _observation_matches(rollback, observation)
    ):
        raise M5ServiceActivationErrorV1("m5_service_journal_invalid")
    document: dict[str, object] = {
        "schema": "agentmonitor.m5-service-activation-journal.v1",
        "phase": phase,
        "unit_name": candidate.unit_name,
        "previous_unit_sha256": snapshot.digest,
        "previous_unit_mode": snapshot.mode,
        "previous_unit_device": snapshot.device,
        "previous_unit_inode": snapshot.inode,
        "previous_main_pid": observation.main_pid,
        "previous_main_pid_start_time_ticks": observation.main_pid_start_time_ticks,
        "previous_source_revision": rollback.source_revision,
        "candidate_source_revision": candidate.source_revision,
        "preserved_launch_sha256": _preserved_launch_digest(candidate, rollback),
    }
    validate_activation_journal_v1(document)
    return document


def validate_activation_journal_v1(document: Mapping[str, object]) -> None:
    """Validate the exact private journal schema without reading host state."""

    try:
        valid = (
            isinstance(document, dict)
            and set(document) == _JOURNAL_KEYS
            and document["schema"] == "agentmonitor.m5-service-activation-journal.v1"
            and document["phase"] == "prepared"
            and document["unit_name"] == SERVICE_NAME
            and isinstance(document["previous_unit_sha256"], str)
            and _DIGEST.fullmatch(document["previous_unit_sha256"]) is not None
            and type(document["previous_unit_mode"]) is int
            and document["previous_unit_mode"] == 0o600
            and type(document["previous_unit_device"]) is int
            and document["previous_unit_device"] >= 0
            and type(document["previous_unit_inode"]) is int
            and document["previous_unit_inode"] > 0
            and type(document["previous_main_pid"]) is int
            and document["previous_main_pid"] > 0
            and type(document["previous_main_pid_start_time_ticks"]) is int
            and document["previous_main_pid_start_time_ticks"] > 0
            and isinstance(document["previous_source_revision"], str)
            and _REVISION.fullmatch(document["previous_source_revision"]) is not None
            and isinstance(document["candidate_source_revision"], str)
            and _REVISION.fullmatch(document["candidate_source_revision"]) is not None
            and document["candidate_source_revision"]
            != document["previous_source_revision"]
            and isinstance(document["preserved_launch_sha256"], str)
            and _DIGEST.fullmatch(document["preserved_launch_sha256"]) is not None
        )
    except (KeyError, TypeError):
        valid = False
    if not valid:
        raise M5ServiceActivationErrorV1("m5_service_journal_invalid")


def activation_journal_material_matches_v1(
    first: Mapping[str, object],
    second: Mapping[str, object],
) -> bool:
    """Compare immutable journal material while allowing a trusted PID restart."""

    try:
        validate_activation_journal_v1(first)
        validate_activation_journal_v1(second)
    except M5ServiceActivationErrorV1:
        return False
    stable_first = dict(first)
    stable_second = dict(second)
    for key in ("previous_main_pid", "previous_main_pid_start_time_ticks"):
        stable_first.pop(key)
        stable_second.pop(key)
    return stable_first == stable_second


def _validate_private_parent(path: Path) -> None:
    try:
        parent = path.parent.lstat()
        if (
            path.name != ACTIVATION_JOURNAL_BASENAME
            or path.parent.is_symlink()
            or not stat.S_ISDIR(parent.st_mode)
            or parent.st_uid != os.getuid()
            or stat.S_IMODE(parent.st_mode) != 0o700
        ):
            raise OSError
    except OSError:
        raise M5ServiceActivationErrorV1("m5_service_journal_path_invalid") from None


def write_private_activation_journal_v1(
    path: Path, document: Mapping[str, object]
) -> None:
    """Create the journal once with owner-only custody and durable metadata."""

    validate_activation_journal_v1(document)
    _validate_private_parent(path)
    try:
        existing = path.lstat()
    except FileNotFoundError:
        existing = None
    except OSError:
        raise M5ServiceActivationErrorV1("m5_service_journal_path_invalid") from None
    if existing is not None:
        if path.is_symlink() or not stat.S_ISREG(existing.st_mode):
            raise M5ServiceActivationErrorV1("m5_service_journal_path_invalid")
        raise M5ServiceActivationErrorV1("m5_service_journal_exists")
    payload = _json_bytes(document)
    descriptor = -1
    try:
        descriptor = os.open(
            path,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0),
            0o600,
        )
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "wb") as stream:
            descriptor = -1
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        _fsync_directory(path.parent)
    except FileExistsError:
        raise M5ServiceActivationErrorV1("m5_service_journal_exists") from None
    except OSError:
        raise M5ServiceActivationErrorV1("m5_service_journal_path_invalid") from None
    finally:
        if descriptor >= 0:
            os.close(descriptor)


def read_private_activation_journal_v1(path: Path) -> dict[str, object]:
    """Read a bounded journal only when its live metadata remains private."""

    _validate_private_parent(path)
    descriptor = -1
    try:
        descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
        info = os.fstat(descriptor)
        current = path.lstat()
        if (
            not stat.S_ISREG(info.st_mode)
            or info.st_uid != os.getuid()
            or stat.S_IMODE(info.st_mode) != 0o600
            or info.st_nlink != 1
            or info.st_size < 1
            or info.st_size > MAX_JSON_BYTES
            or (info.st_dev, info.st_ino) != (current.st_dev, current.st_ino)
        ):
            raise OSError
        payload = os.read(descriptor, MAX_JSON_BYTES + 1)
        if len(payload) != info.st_size:
            raise OSError
        value = json.loads(payload)
    except (OSError, ValueError, TypeError):
        raise M5ServiceActivationErrorV1("m5_service_journal_path_invalid") from None
    finally:
        if descriptor >= 0:
            os.close(descriptor)
    if not isinstance(value, dict):
        raise M5ServiceActivationErrorV1("m5_service_journal_invalid")
    validate_activation_journal_v1(value)
    return value


def _write_create_once(path: Path, content: bytes) -> tuple[int, int]:
    if not 1 <= len(content) <= MAX_JSON_BYTES:
        raise M5ServiceActivationErrorV1("m5_service_artifact_invalid")
    descriptor = -1
    created_identity: tuple[int, int] | None = None
    try:
        descriptor = os.open(
            path,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0),
            0o600,
        )
        metadata = os.fstat(descriptor)
        created_identity = (metadata.st_dev, metadata.st_ino)
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "wb") as stream:
            descriptor = -1
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        _fsync_directory(path.parent)
        current = path.lstat()
        if (
            not stat.S_ISREG(current.st_mode)
            or current.st_uid != os.getuid()
            or stat.S_IMODE(current.st_mode) != 0o600
            or current.st_nlink != 1
            or (current.st_dev, current.st_ino) != created_identity
            or current.st_size != len(content)
        ):
            raise OSError
        return created_identity
    except BaseException:
        if created_identity is not None:
            _unlink_created_activation_receipt_v1(
                path,
                device=created_identity[0],
                inode=created_identity[1],
            )
        raise
    finally:
        if descriptor >= 0:
            os.close(descriptor)


def _unlink_created_activation_receipt_v1(
    path: Path,
    *,
    device: int,
    inode: int,
) -> None:
    """Remove only the canonical name that still identifies our receipt inode."""

    try:
        current = path.lstat()
    except FileNotFoundError:
        return
    except OSError:
        raise M5ServiceActivationFailedV1("m5_service_receipt_cleanup_failed") from None
    if (
        not stat.S_ISREG(current.st_mode)
        or current.st_uid != os.getuid()
        or stat.S_IMODE(current.st_mode) != 0o600
        or current.st_nlink != 1
        or (current.st_dev, current.st_ino) != (device, inode)
    ):
        raise M5ServiceActivationFailedV1("m5_service_receipt_cleanup_failed")
    try:
        path.unlink()
        _fsync_directory(path.parent)
    except OSError:
        raise M5ServiceActivationFailedV1("m5_service_receipt_cleanup_failed") from None


def _json_bytes(document: Mapping[str, object]) -> bytes:
    payload = (
        json.dumps(document, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode("ascii")
    if len(payload) > MAX_JSON_BYTES:
        raise M5ServiceActivationFailedV1("m5_service_artifact_invalid")
    return payload


def _prepare_transition_artifacts(
    *,
    snapshot: UnitSnapshotV1,
    candidate: M5ServiceCandidateV1,
    rollback: M5ServiceCandidateV1,
    selected: SystemdServiceObservationV1,
    preserved_rollovers: tuple[_RetainedCompletedActivationRolloverV1, ...] = (),
) -> None:
    _require_preserved_activation_rollovers_v1(preserved_rollovers)
    TRANSITION_ROOT.mkdir(mode=0o700, parents=True, exist_ok=True)
    _require_preserved_activation_rollovers_v1(preserved_rollovers)
    info = TRANSITION_ROOT.lstat()
    if (
        TRANSITION_ROOT.is_symlink()
        or not stat.S_ISDIR(info.st_mode)
        or info.st_uid != os.getuid()
        or stat.S_IMODE(info.st_mode) != 0o700
    ):
        raise M5ServiceActivationErrorV1("m5_service_transition_custody_invalid")
    document = build_activation_journal_v1(
        candidate,
        rollback,
        selected,
        snapshot,
        phase="prepared",
    )
    journal_exists = JOURNAL_PATH.exists() or JOURNAL_PATH.is_symlink()
    rollback_exists = ROLLBACK_UNIT_PATH.exists() or ROLLBACK_UNIT_PATH.is_symlink()
    if journal_exists or rollback_exists:
        if not journal_exists or not rollback_exists:
            raise M5ServiceActivationErrorV1("m5_service_transition_recovery_required")
        observed_document = read_private_activation_journal_v1(JOURNAL_PATH)
        try:
            _, rollback_bytes = _safe_regular_file(
                ROLLBACK_UNIT_PATH, maximum=MAX_UNIT_BYTES
            )
        except M5ServiceActivationErrorV1:
            raise M5ServiceActivationErrorV1(
                "m5_service_transition_recovery_required"
            ) from None
        if (
            not activation_journal_material_matches_v1(observed_document, document)
            or rollback_bytes != snapshot.content
        ):
            raise M5ServiceActivationErrorV1("m5_service_transition_recovery_required")
        return
    _require_preserved_activation_rollovers_v1(preserved_rollovers)
    _write_create_once(ROLLBACK_UNIT_PATH, snapshot.content)
    _require_preserved_activation_rollovers_v1(preserved_rollovers)
    write_private_activation_journal_v1(JOURNAL_PATH, document)
    _require_preserved_activation_rollovers_v1(preserved_rollovers)


def _load_json_artifact(path: Path) -> dict[str, object]:
    try:
        _, payload = _safe_regular_file(path, maximum=MAX_JSON_BYTES)
        value = json.loads(payload)
    except (M5ServiceActivationErrorV1, ValueError):
        raise M5ServiceActivationErrorV1("m5_service_artifact_invalid") from None
    if not isinstance(value, dict):
        raise M5ServiceActivationErrorV1("m5_service_artifact_invalid")
    return value


def _browser_proof(
    selectors: ActivationSelectorsV1,
    *,
    revision: str,
    require_revision: bool,
) -> dict[str, object]:
    environment = {
        "PATH": "/usr/bin:/bin",
        "AGENTMONITOR_TEST_DASHBOARD_CDP_ENDPOINT": selectors.dashboard_cdp_endpoint,
        "AGENTMONITOR_TEST_DASHBOARD_ORIGIN": selectors.dashboard_origin,
        "AGENTMONITOR_M5_IMPLEMENTATION_REVISION": revision,
        "AGENTMONITOR_M5_SERVICE_REVISION_MODE": (
            "candidate" if require_revision else "baseline"
        ),
    }
    try:
        result = subprocess.run(
            (str(NODE), str(BROWSER_SCRIPT)),
            cwd=ROOT,
            env=environment,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            check=False,
            timeout=120,
        )
    except (OSError, subprocess.SubprocessError):
        raise M5ServiceActivationErrorV1("m5_service_browser_unavailable") from None
    if result.returncode != 0 or result.stderr or len(result.stdout) > MAX_JSON_BYTES:
        raise M5ServiceActivationErrorV1("m5_service_browser_unavailable")
    try:
        proof = json.loads(result.stdout)
    except ValueError:
        raise M5ServiceActivationFailedV1("m5_service_browser_invalid") from None
    if (
        not isinstance(proof, dict)
        or proof.get("schema") != "agentmonitor.m5-service-revision-proof.v1"
        or proof.get("implementation_revision") != revision
        or proof.get("mode") != ("candidate" if require_revision else "baseline")
        or _DIGEST.fullmatch(str(proof.get("registry_digest_before", ""))) is None
        or proof.get("registry_digest_before") != proof.get("registry_digest_after")
        or proof.get("mutations") != 0
        or (require_revision and proof.get("service_source_revision") != revision)
    ):
        raise M5ServiceActivationFailedV1("m5_service_browser_invalid")
    return proof


def verify_current_service_revision_browser_v1(
    *,
    dashboard_origin: str,
    dashboard_cdp_endpoint: str,
    source_revision: str,
    checkout_root: Path = ROOT,
) -> M5ServiceRevisionProofV1:
    """Prove current Operations revision and Registry stability in shared Chrome."""

    try:
        endpoint = urlsplit(dashboard_cdp_endpoint)
        if (
            dashboard_origin != LOOPBACK_ORIGIN
            or endpoint.scheme != "http"
            or endpoint.hostname != "127.0.0.1"
            or endpoint.port is None
            or endpoint.path not in {"", "/"}
            or endpoint.query
            or endpoint.fragment
            or clean_detached_revision_v1(checkout_root) != source_revision
        ):
            raise ValueError
    except (OSError, TypeError, ValueError):
        raise M5ServiceActivationErrorV1(
            "m5_service_browser_selection_invalid"
        ) from None
    proof = _browser_proof(
        ActivationSelectorsV1(
            DATA_ROOT,
            dashboard_origin,
            dashboard_cdp_endpoint,
            1,
        ),
        revision=source_revision,
        require_revision=True,
    )
    if clean_detached_revision_v1(checkout_root) != source_revision:
        raise M5ServiceActivationErrorV1("m5_service_checkout_changed")
    service_revision = proof.get("service_source_revision")
    registry_digest = proof.get("registry_digest_before")
    if (
        not isinstance(service_revision, str)
        or service_revision != source_revision
        or not isinstance(registry_digest, str)
        or _DIGEST.fullmatch(registry_digest) is None
    ):
        raise M5ServiceActivationFailedV1("m5_service_browser_invalid")
    return M5ServiceRevisionProofV1(
        source_revision,
        service_revision,
        registry_digest,
    )


def _rollback_candidate(snapshot: UnitSnapshotV1) -> M5ServiceCandidateV1:
    expected = _render_unit(
        ROLLBACK_ROOT,
        data_root=DATA_ROOT,
        timeout_stop_seconds=30,
    )
    if (
        snapshot.path != UNIT_PATH
        or snapshot.mode != 0o600
        or snapshot.content != expected.encode("utf-8")
        or hashlib.sha256(snapshot.content).hexdigest() != snapshot.digest
    ):
        raise M5ServiceActivationErrorV1("m5_service_rollback_material_invalid")
    return M5ServiceCandidateV1(
        unit_name=SERVICE_NAME,
        unit_path=UNIT_PATH,
        checkout_root=ROLLBACK_ROOT,
        source_revision=PINNED_ROLLBACK_REVISION,
        executable=ROLLBACK_ROOT / "backend/.venv/bin/python",
        argv=_argv(ROLLBACK_ROOT),
        config_path=CONFIG_PATH,
        data_root=DATA_ROOT,
        environment=_environment(ROLLBACK_ROOT),
        after_units=("network-online.target",),
        wants_units=("network-online.target",),
        restart_policy="on-failure",
        restart_delay_seconds=5,
        timeout_stop_seconds=30,
        umask="0077",
        required_origins=REQUIRED_ORIGINS,
        unit_text=snapshot.content.decode("utf-8"),
    )


def _unit_bytes_are(candidate: M5ServiceCandidateV1) -> bool:
    try:
        _, content = _safe_regular_file(candidate.unit_path, maximum=MAX_UNIT_BYTES)
    except M5ServiceActivationErrorV1:
        return False
    return content == candidate.unit_text.encode("utf-8")


def _stop_owned_candidate(
    candidate: M5ServiceCandidateV1,
    selected: SystemdServiceObservationV1 | None,
    rollback_runtime_state: _RollbackRuntimeStateV1,
    preserved_rollovers: tuple[_RetainedCompletedActivationRolloverV1, ...] = (),
) -> None:
    """Stop only the fixed unit while its installed bytes select the candidate."""

    if not _unit_bytes_are(candidate):
        raise M5ServiceActivationFailedV1("m5_service_candidate_ownership_lost")
    if selected is not None and not _service_process_matches(candidate, selected):
        raise M5ServiceActivationFailedV1("m5_service_candidate_ownership_lost")
    try:
        live = observe_selected_systemd_service_v1(candidate)
    except M5ServiceActivationErrorV1:
        live = None
    if live is not None:
        if not _service_process_matches(candidate, live):
            raise M5ServiceActivationFailedV1("m5_service_candidate_ownership_lost")
        # `selected` is evidence for the earlier generation. If systemd has
        # already restarted it after a failure, the fresh exact observation
        # above owns the replacement generation that must now be stopped.
    else:
        properties = _systemd_properties()
        try:
            if (
                Path(properties["FragmentPath"]) != candidate.unit_path
                or int(properties["MainPID"]) != 0
                or properties["ActiveState"] not in {"inactive", "failed"}
            ):
                raise ValueError
        except (KeyError, ValueError):
            raise M5ServiceActivationFailedV1(
                "m5_service_candidate_ownership_lost"
            ) from None
    _require_rollback_runtime_state(rollback_runtime_state)
    _require_preserved_activation_rollovers_v1(preserved_rollovers)
    _systemctl_ok("stop", SERVICE_NAME, timeout=60)
    _require_preserved_activation_rollovers_v1(preserved_rollovers)


def _rollback(
    snapshot: UnitSnapshotV1,
    candidate: M5ServiceCandidateV1,
    rollback_runtime_state: _RollbackRuntimeStateV1,
    *,
    selected_candidate: SystemdServiceObservationV1 | None = None,
    preserved_rollovers: tuple[_RetainedCompletedActivationRolloverV1, ...] = (),
) -> SystemdServiceObservationV1:
    """Restore and prove the exact trusted service after any post-stop failure."""

    try:
        rollback = _rollback_candidate(snapshot)
        if _unit_bytes_are(candidate):
            _stop_owned_candidate(
                candidate,
                selected_candidate,
                rollback_runtime_state,
                preserved_rollovers,
            )
            _require_preserved_activation_rollovers_v1(preserved_rollovers)
            restore_unit_snapshot_v1(snapshot)
            _require_preserved_activation_rollovers_v1(preserved_rollovers)
        elif not _unit_bytes_are(rollback):
            raise M5ServiceActivationFailedV1("m5_service_activation_rollback_failed")
        _require_preserved_activation_rollovers_v1(preserved_rollovers)
        _systemctl_ok("daemon-reload")
        _require_preserved_activation_rollovers_v1(preserved_rollovers)
        _require_rollback_runtime_state(rollback_runtime_state)
        _require_preserved_activation_rollovers_v1(preserved_rollovers)
        _systemctl_ok("start", SERVICE_NAME, timeout=60)
        _require_preserved_activation_rollovers_v1(preserved_rollovers)
        restored = _wait_for_observation(rollback, rollback=True)
        validate_rollback_systemd_service_v1(rollback, restored)
        _require_rollback_runtime_state(rollback_runtime_state)
        return restored
    except (Exception, KeyboardInterrupt):
        raise M5ServiceActivationRollbackFailedV1(
            "m5_service_activation_rollback_failed"
        ) from None


def _recover_post_stop_failure(
    error: BaseException,
    snapshot: UnitSnapshotV1,
    candidate: M5ServiceCandidateV1,
    rollback_runtime_state: _RollbackRuntimeStateV1,
    *,
    selected_candidate: SystemdServiceObservationV1 | None = None,
    resume_drill: bool = False,
    failure_phase: Literal["candidate_starting", "candidate_finalizing"] = (
        "candidate_starting"
    ),
    receipt_cleanup_error: M5ServiceActivationFailedV1 | None = None,
    preserved_rollovers: tuple[_RetainedCompletedActivationRolloverV1, ...] = (),
) -> SystemdServiceObservationV1:
    """Route both the live drill and unexpected failures through one rollback."""

    original_failure = (
        str(error)
        if isinstance(error, (M5ServiceActivationErrorV1, M5ServiceActivationFailedV1))
        and re.fullmatch(r"[a-z0-9_]{1,128}", str(error)) is not None
        else "m5_service_activation_failed"
    )
    decision = activation_transition_step_v1(
        failure_phase,
        "failed",
        original_failure=original_failure,
    )
    if decision.effect != "verify_rollback_runtime":
        raise M5ServiceActivationFailedV1("m5_service_transition_invalid")
    restored = _rollback(
        snapshot,
        candidate,
        rollback_runtime_state,
        selected_candidate=selected_candidate,
        preserved_rollovers=preserved_rollovers,
    )
    if receipt_cleanup_error is not None:
        raise receipt_cleanup_error
    if resume_drill and isinstance(error, _M5ServiceRollbackDrillV1):
        return restored
    if isinstance(error, (M5ServiceActivationErrorV1, M5ServiceActivationFailedV1)):
        raise error
    if isinstance(error, KeyboardInterrupt):
        raise error
    raise M5ServiceActivationFailedV1("m5_service_activation_failed") from None


def _wait_for_observation(
    candidate: M5ServiceCandidateV1,
    *,
    rollback: bool = False,
    timeout_seconds: float = 45,
) -> SystemdServiceObservationV1:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        try:
            observation = observe_selected_systemd_service_v1(candidate)
            if rollback:
                validate_rollback_systemd_service_v1(candidate, observation)
            else:
                validate_selected_systemd_service_v1(candidate, observation)
            return observation
        except (M5ServiceActivationErrorV1, M5ServiceActivationFailedV1):
            time.sleep(0.25)
    reason = "m5_service_rollback_failed" if rollback else "m5_service_readiness_failed"
    raise M5ServiceActivationFailedV1(reason)


_RECEIPT_KEYS = frozenset(
    {
        "schema",
        "candidate_revision",
        "candidate_root",
        "candidate_unit_digest",
        "rollback_revision",
        "rollback_unit_digest",
        "rollback_runtime_digest",
        "journal_digest",
        "main_pid",
        "main_pid_start_time_ticks",
        "rollback_proven",
        "status",
    }
)


def _validate_receipt(
    document: Mapping[str, object], candidate: M5ServiceCandidateV1
) -> None:
    try:
        valid = (
            isinstance(document, dict)
            and set(document) == _RECEIPT_KEYS
            and document["schema"] == "agentmonitor.m5-service-activation-receipt.v1"
            and document["candidate_revision"] == candidate.source_revision
            and document["candidate_root"] == str(candidate.checkout_root)
            and document["candidate_unit_digest"]
            == hashlib.sha256(candidate.unit_text.encode("utf-8")).hexdigest()
            and document["rollback_revision"] == PINNED_ROLLBACK_REVISION
            and isinstance(document["rollback_unit_digest"], str)
            and _DIGEST.fullmatch(document["rollback_unit_digest"]) is not None
            and isinstance(document["rollback_runtime_digest"], str)
            and _DIGEST.fullmatch(document["rollback_runtime_digest"]) is not None
            and isinstance(document["journal_digest"], str)
            and _DIGEST.fullmatch(document["journal_digest"]) is not None
            and type(document["main_pid"]) is int
            and document["main_pid"] > 0
            and type(document["main_pid_start_time_ticks"]) is int
            and document["main_pid_start_time_ticks"] > 0
            and document["rollback_proven"] is True
            and document["status"] == "active"
        )
    except (KeyError, TypeError):
        valid = False
    if not valid:
        raise M5ServiceActivationErrorV1("m5_service_receipt_invalid")


def _rollback_candidate_for_receipt_v1(
    candidate: M5ServiceCandidateV1,
    rollback_root: Path,
    rollback_unit_text: str,
) -> M5ServiceCandidateV1:
    """Reconstruct the exact trusted launch whose bytes the receipt names."""

    return M5ServiceCandidateV1(
        unit_name=SERVICE_NAME,
        unit_path=candidate.unit_path,
        checkout_root=rollback_root,
        source_revision=PINNED_ROLLBACK_REVISION,
        executable=rollback_root / "backend/.venv/bin/python",
        argv=_argv(rollback_root),
        config_path=CONFIG_PATH,
        data_root=DATA_ROOT,
        environment=_environment(rollback_root),
        after_units=("network-online.target",),
        wants_units=("network-online.target",),
        restart_policy="on-failure",
        restart_delay_seconds=5,
        timeout_stop_seconds=30,
        umask="0077",
        required_origins=REQUIRED_ORIGINS,
        unit_text=rollback_unit_text,
    )


def _validate_completed_activation_material_v1(
    candidate: M5ServiceCandidateV1,
    *,
    require_candidate_unit: bool,
    receipt_path: Path = RECEIPT_PATH,
    journal_path: Path = JOURNAL_PATH,
    rollback_unit_path: Path = ROLLBACK_UNIT_PATH,
    rollback_root: Path = ROLLBACK_ROOT,
) -> ValidatedM5ServiceActivationReceiptV1:
    """Validate immutable completed evidence before or after trusted rollback."""

    try:
        if type(require_candidate_unit) is not bool:
            raise TypeError
        validate_service_candidate_v1(candidate)
        transition_root = receipt_path.parent
        root_info = transition_root.lstat()
        if (
            not transition_root.is_absolute()
            or transition_root.is_symlink()
            or transition_root.resolve(strict=True) != transition_root
            or not stat.S_ISDIR(root_info.st_mode)
            or root_info.st_uid != os.getuid()
            or stat.S_IMODE(root_info.st_mode) != 0o700
            or receipt_path.name != RECEIPT_PATH.name
            or journal_path.parent != transition_root
            or journal_path.name != ACTIVATION_JOURNAL_BASENAME
            or rollback_unit_path.parent != transition_root
            or rollback_unit_path.name != ROLLBACK_UNIT_PATH.name
        ):
            raise OSError

        if require_candidate_unit:
            _, candidate_unit_bytes = _safe_regular_file(
                candidate.unit_path,
                maximum=MAX_UNIT_BYTES,
            )
            if candidate_unit_bytes != candidate.unit_text.encode("utf-8"):
                raise ValueError

        _, receipt_payload = _safe_regular_file(
            receipt_path,
            maximum=MAX_JSON_BYTES,
        )
        receipt = json.loads(receipt_payload)
        if not isinstance(receipt, dict):
            raise TypeError
        _validate_receipt(receipt, candidate)
        if receipt_payload != _json_bytes(receipt):
            raise ValueError

        _, journal_payload = _safe_regular_file(
            journal_path,
            maximum=MAX_JSON_BYTES,
        )
        journal = json.loads(journal_payload)
        if not isinstance(journal, dict):
            raise TypeError
        validate_activation_journal_v1(journal)
        if journal_payload != _json_bytes(journal):
            raise ValueError

        _, rollback_unit_bytes = _safe_regular_file(
            rollback_unit_path,
            maximum=MAX_UNIT_BYTES,
        )
        rollback_unit_text = _render_unit(
            rollback_root,
            data_root=DATA_ROOT,
            timeout_stop_seconds=30,
        )
        if rollback_unit_bytes != rollback_unit_text.encode("utf-8"):
            raise ValueError
        rollback = _rollback_candidate_for_receipt_v1(
            candidate,
            rollback_root,
            rollback_unit_text,
        )
        rollback_runtime = _rollback_runtime_state(
            rollback_root,
            PINNED_ROLLBACK_REVISION,
        )
        rollback_unit_digest = hashlib.sha256(rollback_unit_bytes).hexdigest()
        journal_digest = hashlib.sha256(journal_payload).hexdigest()
        if (
            journal["candidate_source_revision"] != candidate.source_revision
            or journal["previous_source_revision"] != PINNED_ROLLBACK_REVISION
            or journal["previous_unit_sha256"] != rollback_unit_digest
            or journal["preserved_launch_sha256"]
            != _preserved_launch_digest(candidate, rollback)
            or receipt["rollback_unit_digest"] != rollback_unit_digest
            or receipt["rollback_runtime_digest"] != rollback_runtime.tree_digest
            or receipt["journal_digest"] != journal_digest
        ):
            raise ValueError
        return ValidatedM5ServiceActivationReceiptV1(
            digest=hashlib.sha256(receipt_payload).hexdigest(),
            candidate_revision=candidate.source_revision,
            rollback_revision=PINNED_ROLLBACK_REVISION,
            journal_digest=journal_digest,
            rollback_unit_digest=rollback_unit_digest,
            rollback_runtime_digest=rollback_runtime.tree_digest,
            main_pid=int(receipt["main_pid"]),
            main_pid_start_time_ticks=int(receipt["main_pid_start_time_ticks"]),
        )
    except (
        KeyError,
        M5ServiceActivationErrorV1,
        M5ServiceActivationFailedV1,
        OSError,
        TypeError,
        UnicodeError,
        ValueError,
    ):
        raise M5ServiceActivationErrorV1("m5_service_receipt_invalid") from None


def validate_current_activation_receipt_v1(
    candidate: M5ServiceCandidateV1,
    current: SystemdServiceObservationV1,
    *,
    receipt_path: Path = RECEIPT_PATH,
    journal_path: Path = JOURNAL_PATH,
    rollback_unit_path: Path = ROLLBACK_UNIT_PATH,
    rollback_root: Path = ROLLBACK_ROOT,
) -> ValidatedM5ServiceActivationReceiptV1:
    """Validate the current activation receipt and every rollback binding."""

    try:
        validate_selected_systemd_service_v1(candidate, current)
        return _validate_completed_activation_material_v1(
            candidate,
            require_candidate_unit=True,
            receipt_path=receipt_path,
            journal_path=journal_path,
            rollback_unit_path=rollback_unit_path,
            rollback_root=rollback_root,
        )
    except (M5ServiceActivationErrorV1, M5ServiceActivationFailedV1):
        raise M5ServiceActivationErrorV1("m5_service_receipt_invalid") from None


def _write_receipt(
    candidate: M5ServiceCandidateV1,
    active: SystemdServiceObservationV1,
    *,
    snapshot: UnitSnapshotV1,
    rollback_runtime_state: _RollbackRuntimeStateV1,
    preserved_rollovers: tuple[_RetainedCompletedActivationRolloverV1, ...] = (),
) -> tuple[int, int] | None:
    try:
        _, rollback_bytes = _safe_regular_file(
            ROLLBACK_UNIT_PATH,
            maximum=MAX_UNIT_BYTES,
        )
    except M5ServiceActivationErrorV1:
        raise M5ServiceActivationFailedV1(
            "m5_service_rollback_material_changed"
        ) from None
    if (
        rollback_bytes != snapshot.content
        or _rollback_runtime_state() != rollback_runtime_state
    ):
        raise M5ServiceActivationFailedV1("m5_service_rollback_material_changed")
    journal = read_private_activation_journal_v1(JOURNAL_PATH)
    document = {
        "schema": "agentmonitor.m5-service-activation-receipt.v1",
        "candidate_revision": candidate.source_revision,
        "candidate_root": str(candidate.checkout_root),
        "candidate_unit_digest": hashlib.sha256(
            candidate.unit_text.encode("utf-8")
        ).hexdigest(),
        "rollback_revision": PINNED_ROLLBACK_REVISION,
        "rollback_unit_digest": snapshot.digest,
        "rollback_runtime_digest": rollback_runtime_state.tree_digest,
        "journal_digest": hashlib.sha256(_json_bytes(journal)).hexdigest(),
        "main_pid": active.main_pid,
        "main_pid_start_time_ticks": active.main_pid_start_time_ticks,
        "rollback_proven": True,
        "status": "active",
    }
    _validate_receipt(document, candidate)
    if RECEIPT_PATH.exists():
        existing = _load_json_artifact(RECEIPT_PATH)
        _validate_receipt(existing, candidate)
        stable = dict(document)
        stable.pop("main_pid")
        stable.pop("main_pid_start_time_ticks")
        comparable = dict(existing)
        comparable.pop("main_pid", None)
        comparable.pop("main_pid_start_time_ticks", None)
        if comparable != stable:
            raise M5ServiceActivationErrorV1("m5_service_receipt_invalid")
        return None
    _require_preserved_activation_rollovers_v1(preserved_rollovers)
    created = _write_create_once(RECEIPT_PATH, _json_bytes(document))
    _require_preserved_activation_rollovers_v1(preserved_rollovers)
    return created


def _verify_unit_draft(
    candidate: M5ServiceCandidateV1,
    preserved_rollovers: tuple[_RetainedCompletedActivationRolloverV1, ...] = (),
) -> None:
    _require_preserved_activation_rollovers_v1(preserved_rollovers)
    TRANSITION_ROOT.mkdir(mode=0o700, parents=True, exist_ok=True)
    _require_preserved_activation_rollovers_v1(preserved_rollovers)
    draft = TRANSITION_ROOT / f"candidate-{os.getpid()}.service"
    if draft.exists() or draft.is_symlink():
        raise M5ServiceActivationErrorV1("m5_service_unit_draft_invalid")
    try:
        _require_preserved_activation_rollovers_v1(preserved_rollovers)
        _write_create_once(draft, candidate.unit_text.encode("utf-8"))
        _require_preserved_activation_rollovers_v1(preserved_rollovers)
        result = subprocess.run(
            (str(SYSTEMD_ANALYZE), "--user", "verify", str(draft)),
            cwd=ROOT,
            env=_systemd_environment(),
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
        if result.returncode != 0:
            raise M5ServiceActivationFailedV1("m5_service_unit_verify_failed")
    finally:
        _require_preserved_activation_rollovers_v1(preserved_rollovers)
        draft.unlink(missing_ok=True)
        _fsync_directory(TRANSITION_ROOT)
        _require_preserved_activation_rollovers_v1(preserved_rollovers)


def _path_present(path: Path) -> bool:
    try:
        path.lstat()
    except FileNotFoundError:
        return False
    except OSError:
        return True
    return True


def _require_revision(expected: str) -> None:
    require_clean_detached_revision_v1(expected, root=ROOT)


def _run_candidate_build(
    candidate: M5ServiceCandidateV1,
    preserved_rollovers: tuple[_RetainedCompletedActivationRolloverV1, ...] = (),
) -> None:
    """Run the canonical build against the exact candidate before any stop."""

    environment = {
        "PATH": f"{Path.home()}/.local/bin:/usr/bin:/bin",
        "HOME": str(Path.home()),
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
    }
    _require_preserved_activation_rollovers_v1(preserved_rollovers)
    try:
        try:
            result = subprocess.run(
                (
                    str(candidate.executable),
                    "tools/automation/run.py",
                    "AUTO-BUILD",
                ),
                cwd=candidate.checkout_root,
                env=environment,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
                timeout=300,
            )
        finally:
            _require_preserved_activation_rollovers_v1(preserved_rollovers)
    except (OSError, subprocess.SubprocessError):
        raise M5ServiceActivationFailedV1("m5_service_build_failed") from None
    if result.returncode != 0:
        raise M5ServiceActivationFailedV1("m5_service_build_failed")
    try:
        build = candidate.checkout_root / "frontend/dist/index.html"
        info = build.lstat()
        if build.is_symlink() or not stat.S_ISREG(info.st_mode) or info.st_size < 1:
            raise OSError
    except OSError:
        raise M5ServiceActivationFailedV1("m5_service_build_failed") from None


def _database_state(path: Path) -> _DatabaseStateV1:
    connection: sqlite3.Connection | None = None
    try:
        info = path.lstat()
        if (
            path.is_symlink()
            or not stat.S_ISREG(info.st_mode)
            or info.st_uid != os.getuid()
            or info.st_nlink != 1
            or stat.S_IMODE(info.st_mode) != 0o600
        ):
            raise OSError
        connection = sqlite3.connect(
            f"file:{path}?mode=ro",
            uri=True,
            timeout=5,
        )
        connection.execute("PRAGMA query_only = ON")
        integrity = connection.execute("PRAGMA quick_check").fetchall()
        user_version = connection.execute("PRAGMA user_version").fetchone()
        schema_version = connection.execute("PRAGMA schema_version").fetchone()
        schema = connection.execute(
            "SELECT type, name, tbl_name, sql FROM sqlite_master "
            "ORDER BY type, name, tbl_name"
        ).fetchall()
        if (
            integrity != [("ok",)]
            or user_version is None
            or schema_version is None
            or type(user_version[0]) is not int
            or type(schema_version[0]) is not int
        ):
            raise sqlite3.DatabaseError
        encoded_schema = json.dumps(
            schema,
            ensure_ascii=True,
            separators=(",", ":"),
        ).encode("ascii")
        return _DatabaseStateV1(
            info.st_dev,
            info.st_ino,
            user_version[0],
            schema_version[0],
            hashlib.sha256(encoded_schema).hexdigest(),
        )
    except (OSError, sqlite3.Error, TypeError, ValueError):
        raise M5ServiceActivationErrorV1("m5_service_runtime_invalid") from None
    finally:
        if connection is not None:
            connection.close()


def _existing_transition_snapshot(
    candidate: M5ServiceCandidateV1,
) -> tuple[UnitSnapshotV1, M5ServiceCandidateV1, dict[str, object]] | None:
    journal_present = _path_present(JOURNAL_PATH)
    rollback_present = _path_present(ROLLBACK_UNIT_PATH)
    if not journal_present and not rollback_present:
        return None
    if not journal_present or not rollback_present:
        raise M5ServiceActivationErrorV1("m5_service_transition_recovery_required")
    document = read_private_activation_journal_v1(JOURNAL_PATH)
    try:
        _, content = _safe_regular_file(ROLLBACK_UNIT_PATH, maximum=MAX_UNIT_BYTES)
        mode = document["previous_unit_mode"]
        digest = document["previous_unit_sha256"]
        device = document["previous_unit_device"]
        inode = document["previous_unit_inode"]
        if (
            type(mode) is not int
            or not isinstance(digest, str)
            or type(device) is not int
            or type(inode) is not int
        ):
            raise TypeError
        snapshot = UnitSnapshotV1(
            UNIT_PATH,
            content,
            mode,
            digest,
            device,
            inode,
        )
        rollback = _rollback_candidate(snapshot)
    except (KeyError, TypeError, ValueError, M5ServiceActivationErrorV1):
        raise M5ServiceActivationErrorV1(
            "m5_service_transition_recovery_required"
        ) from None
    if (
        document["candidate_source_revision"] != candidate.source_revision
        or document["previous_source_revision"] != PINNED_ROLLBACK_REVISION
        or document["preserved_launch_sha256"]
        != _preserved_launch_digest(candidate, rollback)
    ):
        raise M5ServiceActivationErrorV1("m5_service_transition_recovery_required")
    return snapshot, rollback, document


def _observe_known_transition_state(
    candidate: M5ServiceCandidateV1,
    rollback: M5ServiceCandidateV1,
    *,
    receipt_present: bool,
) -> tuple[SystemdServiceObservationV1 | None, str]:
    try:
        current = observe_selected_systemd_service_v1(candidate)
        validate_selected_systemd_service_v1(candidate, current)
        return current, "candidate"
    except (M5ServiceActivationErrorV1, M5ServiceActivationFailedV1):
        pass
    try:
        current = observe_selected_systemd_service_v1(rollback)
        validate_rollback_systemd_service_v1(rollback, current)
        return current, "rollback"
    except (M5ServiceActivationErrorV1, M5ServiceActivationFailedV1):
        pass
    try:
        properties = _systemd_properties()
        _, unit_content = _safe_regular_file(UNIT_PATH, maximum=MAX_UNIT_BYTES)
        decision = inactive_transition_recovery_decision_v1(
            candidate,
            rollback,
            unit_content=unit_content,
            fragment_path=Path(properties["FragmentPath"]),
            active_state=properties["ActiveState"],
            main_pid=int(properties["MainPID"]),
            journal_present=True,
            receipt_present=receipt_present,
        )
        if decision != "restore_rollback":
            raise ValueError
        kind = (
            "candidate_inactive"
            if unit_content == candidate.unit_text.encode("utf-8")
            else "rollback_inactive"
        )
        return None, kind
    except (KeyError, M5ServiceActivationErrorV1, ValueError):
        raise M5ServiceActivationErrorV1("m5_service_unit_unknown") from None


def _capture_unit_snapshot() -> UnitSnapshotV1:
    info, content = _safe_regular_file(UNIT_PATH, maximum=MAX_UNIT_BYTES)
    return UnitSnapshotV1(
        UNIT_PATH,
        content,
        stat.S_IMODE(info.st_mode),
        hashlib.sha256(content).hexdigest(),
        info.st_dev,
        info.st_ino,
    )


def _complete_partial_transition_artifacts(
    candidate: M5ServiceCandidateV1,
    selectors: ActivationSelectorsV1,
    preserved_rollovers: tuple[_RetainedCompletedActivationRolloverV1, ...] = (),
) -> None:
    """Finish only a proven pre-mutation half-written artifact pair."""

    journal_present = _path_present(JOURNAL_PATH)
    rollback_present = _path_present(ROLLBACK_UNIT_PATH)
    if journal_present == rollback_present:
        return
    snapshot = _capture_unit_snapshot()
    rollback = _rollback_candidate(snapshot)
    current = observe_selected_systemd_service_v1(rollback)
    validate_rollback_systemd_service_v1(rollback, current)
    if current.main_pid != selectors.service_pid:
        raise M5ServiceActivationErrorV1("m5_service_selection_changed")
    decision = partial_artifact_recovery_decision_v1(
        journal_present=journal_present,
        rollback_present=rollback_present,
        trusted_service_active=True,
    )
    if decision == "blocked" or decision == "unchanged":
        raise M5ServiceActivationErrorV1("m5_service_transition_recovery_required")
    if decision == "complete_journal":
        try:
            _, backup = _safe_regular_file(ROLLBACK_UNIT_PATH, maximum=MAX_UNIT_BYTES)
        except M5ServiceActivationErrorV1:
            raise M5ServiceActivationErrorV1(
                "m5_service_transition_recovery_required"
            ) from None
        if backup != snapshot.content:
            raise M5ServiceActivationErrorV1("m5_service_transition_recovery_required")
        document = build_activation_journal_v1(
            candidate,
            rollback,
            current,
            snapshot,
            phase="prepared",
        )
        _require_preserved_activation_rollovers_v1(preserved_rollovers)
        write_private_activation_journal_v1(JOURNAL_PATH, document)
        _require_preserved_activation_rollovers_v1(preserved_rollovers)
        return

    document = read_private_activation_journal_v1(JOURNAL_PATH)
    expected = build_activation_journal_v1(
        candidate,
        rollback,
        current,
        snapshot,
        phase="prepared",
    )
    if not activation_journal_material_matches_v1(document, expected):
        raise M5ServiceActivationErrorV1("m5_service_transition_recovery_required")
    if decision != "complete_rollback_copy":
        raise M5ServiceActivationErrorV1("m5_service_transition_recovery_required")
    _require_preserved_activation_rollovers_v1(preserved_rollovers)
    _write_create_once(ROLLBACK_UNIT_PATH, snapshot.content)
    _require_preserved_activation_rollovers_v1(preserved_rollovers)


def _install_and_start_candidate(
    candidate: M5ServiceCandidateV1,
    snapshot: UnitSnapshotV1,
    preserved_rollovers: tuple[_RetainedCompletedActivationRolloverV1, ...] = (),
) -> SystemdServiceObservationV1:
    _require_revision(candidate.source_revision)
    _require_preserved_activation_rollovers_v1(preserved_rollovers)
    installed = install_candidate_unit_v1(candidate)
    _require_preserved_activation_rollovers_v1(preserved_rollovers)
    if (
        installed is None
        or installed.content != snapshot.content
        or installed.mode != snapshot.mode
        or installed.digest != snapshot.digest
        or installed.device != snapshot.device
        or installed.inode != snapshot.inode
    ):
        raise M5ServiceActivationFailedV1("m5_service_unit_install_failed")
    _require_preserved_activation_rollovers_v1(preserved_rollovers)
    _systemctl_ok("daemon-reload")
    _require_preserved_activation_rollovers_v1(preserved_rollovers)
    _require_revision(candidate.source_revision)
    _require_preserved_activation_rollovers_v1(preserved_rollovers)
    _systemctl_ok("start", SERVICE_NAME, timeout=60)
    _require_preserved_activation_rollovers_v1(preserved_rollovers)
    active = _wait_for_candidate(candidate)
    _require_revision(candidate.source_revision)
    return active


def _verify_transition_material(
    candidate: M5ServiceCandidateV1,
    snapshot: UnitSnapshotV1,
    document: Mapping[str, object],
) -> None:
    observed = read_private_activation_journal_v1(JOURNAL_PATH)
    try:
        _, rollback_bytes = _safe_regular_file(
            ROLLBACK_UNIT_PATH, maximum=MAX_UNIT_BYTES
        )
    except M5ServiceActivationErrorV1:
        raise M5ServiceActivationFailedV1(
            "m5_service_rollback_material_changed"
        ) from None
    if (
        observed != document
        or rollback_bytes != snapshot.content
        or not _unit_bytes_are(candidate)
    ):
        raise M5ServiceActivationFailedV1("m5_service_rollback_material_changed")


def _observe_corrective_rollover_service_v1(
    candidate: M5ServiceCandidateV1,
    rollback: M5ServiceCandidateV1,
) -> tuple[SystemdServiceObservationV1, str]:
    """Observe only the approved prior candidate or its pinned rollback."""

    try:
        current = observe_selected_systemd_service_v1(candidate)
        validate_selected_systemd_service_v1(candidate, current)
        return current, candidate.source_revision
    except (M5ServiceActivationErrorV1, M5ServiceActivationFailedV1):
        pass
    try:
        current = observe_selected_systemd_service_v1(rollback)
        validate_rollback_systemd_service_v1(rollback, current)
        return current, PINNED_ROLLBACK_REVISION
    except (M5ServiceActivationErrorV1, M5ServiceActivationFailedV1):
        raise M5ServiceActivationErrorV1(
            "m5_service_rollover_service_invalid"
        ) from None


def _corrective_rollover_retry_transition_state_v1(
    activation_lock: M5CompletionLockV1,
) -> Literal["fresh", "journal_only", "rollback_only", "prepared"]:
    """Classify only safe artifacts from an interrupted corrected activation."""

    validate_m5_service_activation_lock_v1(activation_lock)
    descriptors: list[int] = []
    allowed = {
        ACTIVATION_JOURNAL_BASENAME: MAX_JSON_BYTES,
        ROLLBACK_UNIT_PATH.name: MAX_UNIT_BYTES,
    }
    states: dict[
        frozenset[str], Literal["fresh", "journal_only", "rollback_only", "prepared"]
    ] = {
        frozenset(): "fresh",
        frozenset({ACTIVATION_JOURNAL_BASENAME}): "journal_only",
        frozenset({ROLLBACK_UNIT_PATH.name}): "rollback_only",
        frozenset(allowed): "prepared",
    }
    try:
        entries = frozenset(os.listdir(activation_lock.directory_descriptor))
        state = states.get(entries)
        if state is None:
            raise OSError
        for basename in sorted(entries):
            descriptor = os.open(
                basename,
                os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC,
                dir_fd=activation_lock.directory_descriptor,
            )
            descriptors.append(descriptor)
            metadata = os.fstat(descriptor)
            current = os.stat(
                basename,
                dir_fd=activation_lock.directory_descriptor,
                follow_symlinks=False,
            )
            if (
                not stat.S_ISREG(metadata.st_mode)
                or metadata.st_uid != os.getuid()
                or stat.S_IMODE(metadata.st_mode) != 0o600
                or metadata.st_nlink != 1
                or metadata.st_dev != activation_lock.directory_device
                or not 1 <= metadata.st_size <= allowed[basename]
                or _stable_stat_identity(current) != _stable_stat_identity(metadata)
            ):
                raise OSError
        if frozenset(os.listdir(activation_lock.directory_descriptor)) != entries:
            raise OSError
        validate_m5_service_activation_lock_v1(activation_lock)
        return state
    except (OSError, TypeError, ValueError):
        raise M5ServiceActivationErrorV1(
            "m5_service_rollover_fresh_root_invalid"
        ) from None
    finally:
        for descriptor in descriptors:
            try:
                os.close(descriptor)
            except OSError:
                pass


def _observe_corrective_rollover_retry_transition_v1(
    candidate: M5ServiceCandidateV1,
    selectors: ActivationSelectorsV1,
    state: Literal["fresh", "journal_only", "rollback_only", "prepared"],
    rollback_from_archive: M5ServiceCandidateV1,
) -> tuple[SystemdServiceObservationV1 | None, str | None, str]:
    """Bind one safe fresh-root state to the exact current service transition."""

    if state == "fresh":
        current = observe_selected_systemd_service_v1(rollback_from_archive)
        validate_rollback_systemd_service_v1(rollback_from_archive, current)
        if current.main_pid != selectors.service_pid:
            raise M5ServiceActivationErrorV1("m5_service_selection_changed")
        return current, PINNED_ROLLBACK_REVISION, "rollback"

    if state in {"journal_only", "rollback_only"}:
        snapshot = _capture_unit_snapshot()
        rollback = _rollback_candidate(snapshot)
        current = observe_selected_systemd_service_v1(rollback)
        validate_rollback_systemd_service_v1(rollback, current)
        if current.main_pid != selectors.service_pid:
            raise M5ServiceActivationErrorV1("m5_service_selection_changed")
        if state == "rollback_only":
            try:
                _, backup = _safe_regular_file(
                    ROLLBACK_UNIT_PATH,
                    maximum=MAX_UNIT_BYTES,
                )
            except M5ServiceActivationErrorV1:
                raise M5ServiceActivationErrorV1(
                    "m5_service_transition_recovery_required"
                ) from None
            if backup != snapshot.content:
                raise M5ServiceActivationErrorV1(
                    "m5_service_transition_recovery_required"
                )
        else:
            document = read_private_activation_journal_v1(JOURNAL_PATH)
            expected = build_activation_journal_v1(
                candidate,
                rollback,
                current,
                snapshot,
                phase="prepared",
            )
            if not activation_journal_material_matches_v1(document, expected):
                raise M5ServiceActivationErrorV1(
                    "m5_service_transition_recovery_required"
                )
        return current, PINNED_ROLLBACK_REVISION, "rollback"

    existing = _existing_transition_snapshot(candidate)
    if existing is None:
        raise M5ServiceActivationErrorV1("m5_service_transition_recovery_required")
    _snapshot, rollback, _document = existing
    prepared_current, current_kind = _observe_known_transition_state(
        candidate,
        rollback,
        receipt_present=False,
    )
    if prepared_current is None:
        return None, None, current_kind
    if prepared_current.main_pid != selectors.service_pid:
        raise M5ServiceActivationErrorV1("m5_service_selection_changed")
    service_revision = (
        candidate.source_revision
        if current_kind == "candidate"
        else PINNED_ROLLBACK_REVISION
    )
    return prepared_current, service_revision, current_kind


def _retain_validated_activation_rollover_archive_v1(
    *,
    prior_revision: str,
    archive_parent: Path,
    rollback_runtime_state: _RollbackRuntimeStateV1,
) -> _ValidatedRetainedActivationArchiveV1:
    """Validate and descriptor-retain one exact completed archive."""

    archived_root, receipt_digest = _select_completed_activation_rollover_archive_v1(
        archive_parent=archive_parent,
        prior_revision=prior_revision,
    )
    receipt_path = archived_root / RECEIPT_PATH.name
    journal_path = archived_root / ACTIVATION_JOURNAL_BASENAME
    rollback_unit_path = archived_root / ROLLBACK_UNIT_PATH.name
    receipt_document = _load_json_artifact(receipt_path)
    if receipt_document.get("candidate_revision") != prior_revision:
        raise M5ServiceActivationErrorV1("m5_service_receipt_invalid")
    prior_root_value = receipt_document.get("candidate_root")
    if not isinstance(prior_root_value, str):
        raise M5ServiceActivationErrorV1("m5_service_receipt_invalid")
    prior_root = Path(prior_root_value)
    if clean_detached_revision_v1(prior_root) != prior_revision:
        raise M5ServiceActivationErrorV1("m5_service_rollover_checkout_invalid")
    prior_candidate = candidate_for_checkout_v1(
        source_revision=prior_revision,
        checkout_root=prior_root,
    )
    completed = _validate_completed_activation_material_v1(
        prior_candidate,
        require_candidate_unit=False,
        receipt_path=receipt_path,
        journal_path=journal_path,
        rollback_unit_path=rollback_unit_path,
    )
    if (
        completed.digest != receipt_digest
        or completed.rollback_runtime_digest != rollback_runtime_state.tree_digest
    ):
        raise M5ServiceActivationErrorV1("m5_service_receipt_invalid")
    retained = _retain_completed_activation_rollover_v1(
        transition_root=archived_root,
        archive_parent=archive_parent,
        prior_revision=prior_revision,
        receipt_digest=completed.digest,
        journal_digest=completed.journal_digest,
        rollback_unit_digest=completed.rollback_unit_digest,
    )
    try:
        _require_preserved_activation_rollovers_v1((retained,))
        selected_root_now, receipt_digest_now = (
            _select_completed_activation_rollover_archive_v1(
                archive_parent=archive_parent,
                prior_revision=prior_revision,
            )
        )
        if selected_root_now != archived_root or receipt_digest_now != receipt_digest:
            raise M5ServiceActivationErrorV1("m5_service_receipt_invalid")
        return _ValidatedRetainedActivationArchiveV1(
            prior_candidate,
            completed,
            retained,
        )
    except BaseException:
        _close_completed_activation_rollover_v1(retained)
        raise


def _retain_activation_rollover_archive_chain_v1(
    latest_revision: str,
    rollback_runtime_state: _RollbackRuntimeStateV1,
) -> tuple[_ValidatedRetainedActivationArchiveV1, ...]:
    """Retain the fixed singleton archive chain through one stable proof."""

    revisions = _corrective_rollover_chain_revisions_v1(latest_revision)
    retained_archives: list[_ValidatedRetainedActivationArchiveV1] = []
    try:
        for revision in revisions:
            retained_archives.append(
                _retain_validated_activation_rollover_archive_v1(
                    prior_revision=revision,
                    archive_parent=_corrective_rollover_archive_root_v1(revision),
                    rollback_runtime_state=rollback_runtime_state,
                )
            )
        result = tuple(retained_archives)
        _require_preserved_activation_rollovers_v1(
            tuple(archive.retained for archive in result)
        )
        retained_archives.clear()
        return result
    finally:
        for archive in reversed(retained_archives):
            _close_completed_activation_rollover_v1(archive.retained)


def _close_activation_rollover_archive_chain_v1(
    archives: tuple[_ValidatedRetainedActivationArchiveV1, ...],
) -> None:
    for archive in reversed(archives):
        _close_completed_activation_rollover_v1(archive.retained)


def _validate_completed_activation_rollover_archive_retry_v1(
    selectors: ActivationSelectorsV1,
    candidate: M5ServiceCandidateV1,
    rollback_runtime_state: _RollbackRuntimeStateV1,
    activation_lock: M5CompletionLockV1,
    archive_chain: tuple[_ValidatedRetainedActivationArchiveV1, ...],
) -> tuple[_ValidatedRetainedActivationArchiveV1, ...]:
    """Reprove the committed corrective archive before a fresh activation."""

    if not archive_chain:
        raise M5ServiceActivationErrorV1("m5_service_rollover_archive_invalid")
    archived = archive_chain[-1]
    prior_candidate = archived.candidate
    completed = archived.completed
    retained = archived.retained
    prior_revision = completed.candidate_revision
    archived_root = retained.transition_root
    receipt_digest = completed.digest
    receipt_path = archived_root / RECEIPT_PATH.name
    journal_path = archived_root / ACTIVATION_JOURNAL_BASENAME
    rollback_unit_path = archived_root / ROLLBACK_UNIT_PATH.name
    prior_root = prior_candidate.checkout_root
    preserved_rollovers = tuple(archive.retained for archive in archive_chain)
    try:
        validate_m5_service_activation_lock_v1(activation_lock)
        rollback_unit_text = _render_unit(
            ROLLBACK_ROOT,
            data_root=DATA_ROOT,
            timeout_stop_seconds=30,
        )
        rollback_candidate = _rollback_candidate_for_receipt_v1(
            prior_candidate,
            ROLLBACK_ROOT,
            rollback_unit_text,
        )
        transition_state = _corrective_rollover_retry_transition_state_v1(
            activation_lock
        )
        current, service_revision, current_kind = (
            _observe_corrective_rollover_retry_transition_v1(
                candidate,
                selectors,
                transition_state,
                rollback_candidate,
            )
        )
        browser: dict[str, object] | None = None
        if service_revision is not None:
            browser_revision, browser_requires_revision = (
                corrective_rollover_browser_expectation_v1(
                    service_revision=service_revision,
                    candidate_revision=candidate.source_revision,
                )
            )
            browser = _browser_proof(
                selectors,
                revision=browser_revision,
                require_revision=browser_requires_revision,
            )
        registry_digest = (
            browser["registry_digest_before"] if browser is not None else None
        )
        database_state = _database_state(DATABASE_PATH)

        _require_revision(candidate.source_revision)
        require_clean_detached_revision_v1(
            prior_revision,
            root=prior_root,
        )
        _require_rollback_runtime_state(rollback_runtime_state)
        _require_preserved_activation_rollovers_v1(preserved_rollovers)
        selected_root_now, receipt_digest_now = (
            _select_completed_activation_rollover_archive_v1(
                archive_parent=retained.archive_parent,
                prior_revision=prior_revision,
            )
        )
        if (
            selected_root_now != archived_root
            or receipt_digest_now != receipt_digest
            or _validate_completed_activation_material_v1(
                prior_candidate,
                require_candidate_unit=False,
                receipt_path=receipt_path,
                journal_path=journal_path,
                rollback_unit_path=rollback_unit_path,
            )
            != completed
        ):
            raise M5ServiceActivationErrorV1("m5_service_receipt_invalid")
        transition_state_now = _corrective_rollover_retry_transition_state_v1(
            activation_lock
        )
        current_now, service_revision_now, current_kind_now = (
            _observe_corrective_rollover_retry_transition_v1(
                candidate,
                selectors,
                transition_state_now,
                rollback_candidate,
            )
        )
        if (
            transition_state_now != transition_state
            or service_revision_now != service_revision
            or current_kind_now != current_kind
            or (current is None) != (current_now is None)
            or (
                current is not None
                and current_now is not None
                and (
                    current_now.main_pid != current.main_pid
                    or current_now.main_pid_start_time_ticks
                    != current.main_pid_start_time_ticks
                )
            )
        ):
            raise M5ServiceActivationErrorV1("m5_service_selection_changed")
        if service_revision is not None:
            final_browser_revision, final_browser_requires_revision = (
                corrective_rollover_browser_expectation_v1(
                    service_revision=service_revision,
                    candidate_revision=candidate.source_revision,
                )
            )
            final_browser = _browser_proof(
                selectors,
                revision=final_browser_revision,
                require_revision=final_browser_requires_revision,
            )
            if final_browser["registry_digest_before"] != registry_digest:
                raise M5ServiceActivationFailedV1("m5_service_registry_changed")
        if _database_state(DATABASE_PATH) != database_state:
            raise M5ServiceActivationFailedV1("m5_service_database_changed")
        validate_m5_service_activation_lock_v1(activation_lock)
        if (
            _corrective_rollover_retry_transition_state_v1(activation_lock)
            != transition_state
        ):
            raise M5ServiceActivationErrorV1("m5_service_selection_changed")
        _require_preserved_activation_rollovers_v1(preserved_rollovers)
        return archive_chain
    except BaseException:
        _close_activation_rollover_archive_chain_v1(archive_chain)
        raise


def _maybe_correct_completed_activation_rollover_v1(
    selectors: ActivationSelectorsV1,
    candidate: M5ServiceCandidateV1,
    rollback_runtime_state: _RollbackRuntimeStateV1,
    activation_lock: M5CompletionLockV1,
) -> tuple[_ValidatedRetainedActivationArchiveV1, ...]:
    """Restore and archive one exact member of the approved rollover chain."""

    first_archive_state = _corrective_rollover_archive_parent_state_v1(
        archive_parent=CORRECTIVE_ARCHIVE_ROOT,
        prior_revision=CORRECTIVE_ROLLOVER_REVISION,
    )
    second_archive_state = _corrective_rollover_archive_parent_state_v1(
        archive_parent=SECOND_CORRECTIVE_ARCHIVE_ROOT,
        prior_revision=SECOND_CORRECTIVE_ROLLOVER_REVISION,
    )
    third_archive_state = _corrective_rollover_archive_parent_state_v1(
        archive_parent=THIRD_CORRECTIVE_ARCHIVE_ROOT,
        prior_revision=THIRD_CORRECTIVE_ROLLOVER_REVISION,
    )
    fourth_archive_state = _corrective_rollover_archive_parent_state_v1(
        archive_parent=FOURTH_CORRECTIVE_ARCHIVE_ROOT,
        prior_revision=FOURTH_CORRECTIVE_ROLLOVER_REVISION,
    )
    fifth_archive_state = _corrective_rollover_archive_parent_state_v1(
        archive_parent=FIFTH_CORRECTIVE_ARCHIVE_ROOT,
        prior_revision=FIFTH_CORRECTIVE_ROLLOVER_REVISION,
    )
    sixth_archive_state = _corrective_rollover_archive_parent_state_v1(
        archive_parent=SIXTH_CORRECTIVE_ARCHIVE_ROOT,
        prior_revision=SIXTH_CORRECTIVE_ROLLOVER_REVISION,
    )
    seventh_archive_state = _corrective_rollover_archive_parent_state_v1(
        archive_parent=SEVENTH_CORRECTIVE_ARCHIVE_ROOT,
        prior_revision=SEVENTH_CORRECTIVE_ROLLOVER_REVISION,
    )
    eighth_archive_state = _corrective_rollover_archive_parent_state_v1(
        archive_parent=EIGHTH_CORRECTIVE_ARCHIVE_ROOT,
        prior_revision=EIGHTH_CORRECTIVE_ROLLOVER_REVISION,
    )
    ninth_archive_state = _corrective_rollover_archive_parent_state_v1(
        archive_parent=NINTH_CORRECTIVE_ARCHIVE_ROOT,
        prior_revision=NINTH_CORRECTIVE_ROLLOVER_REVISION,
    )
    tenth_archive_state = _corrective_rollover_archive_parent_state_v1(
        archive_parent=TENTH_CORRECTIVE_ARCHIVE_ROOT,
        prior_revision=TENTH_CORRECTIVE_ROLLOVER_REVISION,
    )
    eleventh_archive_state = _corrective_rollover_archive_parent_state_v1(
        archive_parent=ELEVENTH_CORRECTIVE_ARCHIVE_ROOT,
        prior_revision=ELEVENTH_CORRECTIVE_ROLLOVER_REVISION,
    )
    twelfth_archive_state = _corrective_rollover_archive_parent_state_v1(
        archive_parent=TWELFTH_CORRECTIVE_ARCHIVE_ROOT,
        prior_revision=TWELFTH_CORRECTIVE_ROLLOVER_REVISION,
    )
    thirteenth_archive_state = _corrective_rollover_archive_parent_state_v1(
        archive_parent=THIRTEENTH_CORRECTIVE_ARCHIVE_ROOT,
        prior_revision=THIRTEENTH_CORRECTIVE_ROLLOVER_REVISION,
    )
    fourteenth_archive_state = _corrective_rollover_archive_parent_state_v1(
        archive_parent=FOURTEENTH_CORRECTIVE_ARCHIVE_ROOT,
        prior_revision=FOURTEENTH_CORRECTIVE_ROLLOVER_REVISION,
    )
    fifteenth_archive_state = _corrective_rollover_archive_parent_state_v1(
        archive_parent=FIFTEENTH_CORRECTIVE_ARCHIVE_ROOT,
        prior_revision=FIFTEENTH_CORRECTIVE_ROLLOVER_REVISION,
    )
    receipt_document: dict[str, object] | None = None
    receipt_revision: str | None = None
    if _path_present(RECEIPT_PATH):
        receipt_document = _load_json_artifact(RECEIPT_PATH)
        receipt_revision_value = receipt_document.get("candidate_revision")
        if not isinstance(receipt_revision_value, str):
            raise M5ServiceActivationErrorV1("m5_service_receipt_invalid")
        receipt_revision = receipt_revision_value
    transition_action, transition_revision = corrective_rollover_transition_policy_v1(
        receipt_revision=receipt_revision,
        candidate_revision=candidate.source_revision,
        archive_states=(
            first_archive_state,
            second_archive_state,
            third_archive_state,
            fourth_archive_state,
            fifth_archive_state,
            sixth_archive_state,
            seventh_archive_state,
            eighth_archive_state,
            ninth_archive_state,
            tenth_archive_state,
            eleventh_archive_state,
            twelfth_archive_state,
            thirteenth_archive_state,
            fourteenth_archive_state,
            fifteenth_archive_state,
        ),
    )
    if transition_action == "blocked":
        raise M5ServiceActivationErrorV1("m5_service_transition_recovery_required")
    if transition_action == "none":
        return ()
    if transition_revision is None:
        raise M5ServiceActivationErrorV1("m5_service_transition_recovery_required")
    if transition_action == "retain":
        return _retain_activation_rollover_archive_chain_v1(
            transition_revision,
            rollback_runtime_state,
        )
    if transition_action == "retry":
        archive_chain = _retain_activation_rollover_archive_chain_v1(
            transition_revision,
            rollback_runtime_state,
        )
        return _validate_completed_activation_rollover_archive_retry_v1(
            selectors,
            candidate,
            rollback_runtime_state,
            activation_lock,
            archive_chain,
        )
    if transition_action != "archive" or receipt_document is None:
        raise M5ServiceActivationErrorV1("m5_service_transition_recovery_required")
    completed_revision = transition_revision
    completed_index = CORRECTIVE_ROLLOVER_REVISIONS.index(completed_revision)
    if completed_index == 0:
        preserved_archive_chain: tuple[_ValidatedRetainedActivationArchiveV1, ...] = ()
    else:
        preserved_archive_chain = _retain_activation_rollover_archive_chain_v1(
            CORRECTIVE_ROLLOVER_REVISIONS[completed_index - 1],
            rollback_runtime_state,
        )
    preserved_rollovers = tuple(archive.retained for archive in preserved_archive_chain)
    archive_parent = _corrective_rollover_archive_root_v1(completed_revision)
    try:
        prior_root_value = receipt_document.get("candidate_root")
        if not isinstance(prior_root_value, str):
            raise M5ServiceActivationErrorV1("m5_service_receipt_invalid")
        prior_root = Path(prior_root_value)
        if clean_detached_revision_v1(prior_root) != completed_revision:
            raise M5ServiceActivationErrorV1("m5_service_rollover_checkout_invalid")
        prior_candidate = candidate_for_checkout_v1(
            source_revision=completed_revision,
            checkout_root=prior_root,
        )
        completed = _validate_completed_activation_material_v1(
            prior_candidate,
            require_candidate_unit=False,
        )
        existing = _existing_transition_snapshot(prior_candidate)
        if existing is None:
            raise M5ServiceActivationErrorV1("m5_service_transition_recovery_required")
        snapshot, rollback_candidate, _journal = existing
        if completed.rollback_runtime_digest != rollback_runtime_state.tree_digest:
            raise M5ServiceActivationErrorV1("m5_service_receipt_invalid")
        retained = _retain_completed_activation_rollover_v1(
            transition_root=TRANSITION_ROOT,
            archive_parent=archive_parent,
            prior_revision=completed_revision,
            receipt_digest=completed.digest,
            journal_digest=completed.journal_digest,
            rollback_unit_digest=completed.rollback_unit_digest,
        )
    except BaseException:
        _close_activation_rollover_archive_chain_v1(preserved_archive_chain)
        raise
    try:
        _require_preserved_activation_rollovers_v1(preserved_rollovers)
        current, service_revision = _observe_corrective_rollover_service_v1(
            prior_candidate,
            rollback_candidate,
        )
        decision = corrective_activation_rollover_decision_v1(
            candidate_revision=candidate.source_revision,
            completed_revision=completed.candidate_revision,
            service_revision=service_revision,
        )
        if decision not in {"rollback_candidate", "archive_restored"}:
            raise M5ServiceActivationErrorV1("m5_service_transition_recovery_required")
        if current.main_pid != selectors.service_pid:
            raise M5ServiceActivationErrorV1("m5_service_selection_changed")
        if decision == "rollback_candidate":
            current_receipt = validate_current_activation_receipt_v1(
                prior_candidate,
                current,
            )
            if (
                current_receipt != completed
                or completed_activation_rollover_generation_v1(
                    completed_revision=completed.candidate_revision,
                    service_revision=service_revision,
                    receipt_main_pid=completed.main_pid,
                    receipt_start_time_ticks=completed.main_pid_start_time_ticks,
                    current_main_pid=current.main_pid,
                    current_start_time_ticks=current.main_pid_start_time_ticks,
                )
                == "blocked"
            ):
                raise M5ServiceActivationErrorV1("m5_service_receipt_invalid")

        initial_browser_revision, initial_browser_requires_revision = (
            corrective_rollover_browser_expectation_v1(
                service_revision=service_revision,
                candidate_revision=prior_candidate.source_revision,
            )
        )
        initial_browser = _browser_proof(
            selectors,
            revision=initial_browser_revision,
            require_revision=initial_browser_requires_revision,
        )
        registry_digest = initial_browser["registry_digest_before"]
        database_state = _database_state(DATABASE_PATH)
        _require_revision(candidate.source_revision)
        require_clean_detached_revision_v1(completed_revision, root=prior_root)
        _require_rollback_runtime_state(rollback_runtime_state)
        _require_preserved_activation_rollovers_v1(preserved_rollovers)
        current_now, service_revision_now = _observe_corrective_rollover_service_v1(
            prior_candidate,
            rollback_candidate,
        )
        if (
            service_revision_now != service_revision
            or current_now.main_pid != current.main_pid
            or current_now.main_pid_start_time_ticks
            != current.main_pid_start_time_ticks
        ):
            raise M5ServiceActivationErrorV1("m5_service_selection_changed")
        material_now = _validate_completed_activation_material_v1(
            prior_candidate,
            require_candidate_unit=decision == "rollback_candidate",
        )
        if material_now != completed:
            raise M5ServiceActivationErrorV1("m5_service_receipt_invalid")
        _require_retained_activation_rollover_v1(
            retained,
            canonical_path_required=True,
        )
        _require_preserved_activation_rollovers_v1(preserved_rollovers)
        validate_m5_service_activation_lock_v1(activation_lock)

        if decision == "rollback_candidate":
            restored = _rollback(
                snapshot,
                prior_candidate,
                rollback_runtime_state,
                selected_candidate=current_now,
                preserved_rollovers=preserved_rollovers,
            )
        else:
            restored = current_now
        _require_preserved_activation_rollovers_v1(preserved_rollovers)
        validate_rollback_systemd_service_v1(rollback_candidate, restored)
        _require_rollback_runtime_state(rollback_runtime_state)
        restored_now = observe_selected_systemd_service_v1(rollback_candidate)
        validate_rollback_systemd_service_v1(rollback_candidate, restored_now)
        if (
            restored_now.main_pid != restored.main_pid
            or restored_now.main_pid_start_time_ticks
            != restored.main_pid_start_time_ticks
        ):
            raise M5ServiceActivationErrorV1("m5_service_selection_changed")
        rollback_browser_revision, rollback_browser_requires_revision = (
            corrective_rollover_browser_expectation_v1(
                service_revision=PINNED_ROLLBACK_REVISION,
                candidate_revision=candidate.source_revision,
            )
        )
        rollback_browser = _browser_proof(
            selectors,
            revision=rollback_browser_revision,
            require_revision=rollback_browser_requires_revision,
        )
        if rollback_browser["registry_digest_before"] != registry_digest:
            raise M5ServiceActivationFailedV1("m5_service_registry_changed")
        if _database_state(DATABASE_PATH) != database_state:
            raise M5ServiceActivationFailedV1("m5_service_database_changed")
        _require_revision(candidate.source_revision)
        require_clean_detached_revision_v1(completed_revision, root=prior_root)
        final_material = _validate_completed_activation_material_v1(
            prior_candidate,
            require_candidate_unit=False,
        )
        if final_material != completed:
            raise M5ServiceActivationErrorV1("m5_service_receipt_invalid")
        _require_retained_activation_rollover_v1(
            retained,
            canonical_path_required=True,
        )
        _require_preserved_activation_rollovers_v1(preserved_rollovers)
        validate_m5_service_activation_lock_v1(activation_lock)
        _archive_completed_activation_rollover_v1(
            retained,
            preserved_rollovers=preserved_rollovers,
        )
        committed_archive = _retain_validated_activation_rollover_archive_v1(
            prior_revision=completed_revision,
            archive_parent=archive_parent,
            rollback_runtime_state=rollback_runtime_state,
        )
        completed_archive_chain = (*preserved_archive_chain, committed_archive)
        completed_rollovers = tuple(
            archive.retained for archive in completed_archive_chain
        )
        try:
            _require_rollback_runtime_state(rollback_runtime_state)
            _require_preserved_activation_rollovers_v1(completed_rollovers)
            archived_snapshot = _capture_unit_snapshot()
            if (
                archived_snapshot.content != snapshot.content
                or archived_snapshot.mode != snapshot.mode
                or archived_snapshot.digest != snapshot.digest
                or archived_snapshot.device != snapshot.device
            ):
                raise M5ServiceActivationFailedV1(
                    "m5_service_rollback_material_changed"
                )
            archived_rollback = _rollback_candidate(archived_snapshot)
            archived_service = observe_selected_systemd_service_v1(archived_rollback)
            validate_rollback_systemd_service_v1(
                archived_rollback,
                archived_service,
            )
            if (
                archived_service.main_pid != restored_now.main_pid
                or archived_service.main_pid_start_time_ticks
                != restored_now.main_pid_start_time_ticks
            ):
                raise M5ServiceActivationErrorV1("m5_service_selection_changed")
            if _database_state(DATABASE_PATH) != database_state:
                raise M5ServiceActivationFailedV1("m5_service_database_changed")
            _require_revision(candidate.source_revision)
            _prepare_transition_artifacts(
                snapshot=archived_snapshot,
                candidate=candidate,
                rollback=archived_rollback,
                selected=archived_service,
                preserved_rollovers=completed_rollovers,
            )
            _require_revision(candidate.source_revision)
            _require_preserved_activation_rollovers_v1(completed_rollovers)
            prepared = _existing_transition_snapshot(candidate)
            if prepared is None or set(os.listdir(TRANSITION_ROOT)) != {
                ACTIVATION_JOURNAL_BASENAME,
                ROLLBACK_UNIT_PATH.name,
            }:
                raise M5ServiceActivationErrorV1(
                    "m5_service_transition_recovery_required"
                )
            prepared_document = prepared[2]
            prepared_revision = prepared_document.get("candidate_source_revision")
            rerun_decision = corrective_rollover_rerun_decision_v1(
                transition_state="prepared",
                candidate_revision=candidate.source_revision,
                journal_candidate_revision=(
                    prepared_revision if isinstance(prepared_revision, str) else None
                ),
            )
            if rerun_decision != "rerun":
                raise M5ServiceActivationErrorV1(
                    "m5_service_transition_recovery_required"
                )
            _require_preserved_activation_rollovers_v1(completed_rollovers)
            raise M5ServiceActivationRerunRequiredV1(archived_service.main_pid)
        finally:
            _close_completed_activation_rollover_v1(committed_archive.retained)
    finally:
        _close_completed_activation_rollover_v1(retained)
        _close_activation_rollover_archive_chain_v1(preserved_archive_chain)


def _continue_activation_under_lock(
    selectors: ActivationSelectorsV1,
    activation_lock: M5CompletionLockV1,
    rollback_runtime_state: _RollbackRuntimeStateV1,
    revision: str,
    candidate: M5ServiceCandidateV1,
    preserved_rollovers: tuple[_RetainedCompletedActivationRolloverV1, ...],
) -> SystemdServiceObservationV1:
    _run_candidate_build(candidate, preserved_rollovers)
    _require_revision(revision)
    _require_preserved_activation_rollovers_v1(preserved_rollovers)
    _verify_unit_draft(candidate, preserved_rollovers)
    _require_revision(revision)
    _require_preserved_activation_rollovers_v1(preserved_rollovers)
    _complete_partial_transition_artifacts(
        candidate,
        selectors,
        preserved_rollovers,
    )
    _require_revision(revision)
    _require_preserved_activation_rollovers_v1(preserved_rollovers)

    existing = _existing_transition_snapshot(candidate)
    receipt_present = _path_present(RECEIPT_PATH)
    current: SystemdServiceObservationV1 | None
    if existing is None:
        if receipt_present:
            raise M5ServiceActivationErrorV1("m5_service_transition_recovery_required")
        snapshot = _capture_unit_snapshot()
        rollback_candidate = _rollback_candidate(snapshot)
        current = observe_selected_systemd_service_v1(rollback_candidate)
        validate_rollback_systemd_service_v1(rollback_candidate, current)
        document: dict[str, object] | None = None
        if current.main_pid != selectors.service_pid:
            raise M5ServiceActivationErrorV1("m5_service_selection_changed")
    else:
        snapshot, rollback_candidate, document = existing
        current, current_kind = _observe_known_transition_state(
            candidate,
            rollback_candidate,
            receipt_present=receipt_present,
        )
        if current is None:
            decision: Literal[
                "activate", "already_active", "restore_rollback", "blocked"
            ] = "restore_rollback" if not receipt_present else "blocked"
        else:
            decision = activation_recovery_decision_v1(
                candidate,
                rollback_candidate,
                current,
                journal_present=True,
                receipt_present=receipt_present,
            )
        if decision == "already_active":
            if current is None:
                raise M5ServiceActivationErrorV1(
                    "m5_service_transition_recovery_required"
                )
            if current.main_pid != selectors.service_pid:
                raise M5ServiceActivationErrorV1("m5_service_selection_changed")
            receipt = _load_json_artifact(RECEIPT_PATH)
            _validate_receipt(receipt, candidate)
            if (
                receipt["rollback_unit_digest"] != snapshot.digest
                or receipt["rollback_runtime_digest"]
                != rollback_runtime_state.tree_digest
                or receipt["journal_digest"]
                != hashlib.sha256(_json_bytes(document)).hexdigest()
            ):
                raise M5ServiceActivationErrorV1("m5_service_receipt_invalid")
            _verify_transition_material(candidate, snapshot, document)
            proof = _browser_proof(selectors, revision=revision, require_revision=True)
            if proof["registry_digest_before"] != proof["registry_digest_after"]:
                raise M5ServiceActivationFailedV1("m5_service_registry_changed")
            _require_revision(revision)
            validate_receipt_systemd_ownership_v1(
                candidate,
                restarted_main_pid=current.main_pid,
                restarted_start_time_ticks=current.main_pid_start_time_ticks,
                observation=observe_selected_systemd_service_v1(candidate),
            )
            _require_preserved_activation_rollovers_v1(preserved_rollovers)
            validate_m5_service_activation_lock_v1(activation_lock)
            release_m5_service_activation_lock_v1(activation_lock)
            return current
        if decision != "restore_rollback":
            raise M5ServiceActivationErrorV1("m5_service_transition_recovery_required")
        current = _rollback(
            snapshot,
            candidate,
            rollback_runtime_state,
            selected_candidate=(
                current if current is not None and current_kind == "candidate" else None
            ),
            preserved_rollovers=preserved_rollovers,
        )

    if current is None:
        raise M5ServiceActivationErrorV1("m5_service_transition_recovery_required")
    baseline = _browser_proof(selectors, revision=revision, require_revision=False)
    baseline_digest = baseline["registry_digest_before"]
    database_state = _database_state(DATABASE_PATH)
    _require_revision(revision)
    _prepare_transition_artifacts(
        snapshot=snapshot,
        candidate=candidate,
        rollback=rollback_candidate,
        selected=current,
        preserved_rollovers=preserved_rollovers,
    )
    document = read_private_activation_journal_v1(JOURNAL_PATH)
    _require_revision(revision)
    selected_now = observe_selected_systemd_service_v1(rollback_candidate)
    validate_rollback_systemd_service_v1(rollback_candidate, selected_now)
    if (
        selected_now.main_pid != current.main_pid
        or selected_now.main_pid_start_time_ticks != current.main_pid_start_time_ticks
    ):
        raise M5ServiceActivationErrorV1("m5_service_selection_changed")

    service_mutated = False
    failure_phase: Literal["candidate_starting", "candidate_finalizing"] = (
        "candidate_starting"
    )
    created_receipt_identity: tuple[int, int] | None = None
    try:
        validate_m5_service_activation_lock_v1(activation_lock)
        _require_transition_stop_state(revision, rollback_runtime_state)
        service_mutated = True
        _require_preserved_activation_rollovers_v1(preserved_rollovers)
        _systemctl_ok("stop", SERVICE_NAME, timeout=60)
        _require_preserved_activation_rollovers_v1(preserved_rollovers)
        first_active = _install_and_start_candidate(
            candidate,
            snapshot,
            preserved_rollovers,
        )
        first_proof = _browser_proof(
            selectors, revision=revision, require_revision=True
        )
        if first_proof["registry_digest_before"] != baseline_digest:
            raise M5ServiceActivationFailedV1("m5_service_registry_changed")
        validate_receipt_systemd_ownership_v1(
            candidate,
            restarted_main_pid=first_active.main_pid,
            restarted_start_time_ticks=first_active.main_pid_start_time_ticks,
            observation=observe_selected_systemd_service_v1(candidate),
        )
        _verify_transition_material(candidate, snapshot, document)
        if _database_state(DATABASE_PATH) != database_state:
            raise M5ServiceActivationFailedV1("m5_service_database_changed")

        # Trigger the production failure handler after a proven candidate start.
        # It performs the actual trusted rollback before this drill resumes.
        drill_failure = _M5ServiceRollbackDrillV1("m5_service_rollback_drill")
        restored = _recover_post_stop_failure(
            drill_failure,
            snapshot,
            candidate,
            rollback_runtime_state,
            selected_candidate=first_active,
            resume_drill=True,
            preserved_rollovers=preserved_rollovers,
        )
        rollback_proof = _browser_proof(
            selectors, revision=revision, require_revision=False
        )
        if rollback_proof["registry_digest_before"] != baseline_digest:
            raise M5ServiceActivationFailedV1("m5_service_registry_changed")
        validate_rollback_systemd_service_v1(rollback_candidate, restored)
        if _database_state(DATABASE_PATH) != database_state:
            raise M5ServiceActivationFailedV1("m5_service_database_changed")
        _require_revision(revision)

        restored_now = observe_selected_systemd_service_v1(rollback_candidate)
        validate_rollback_systemd_service_v1(rollback_candidate, restored_now)
        if (
            restored_now.main_pid != restored.main_pid
            or restored_now.main_pid_start_time_ticks
            != restored.main_pid_start_time_ticks
        ):
            raise M5ServiceActivationFailedV1("m5_service_selection_changed")
        _require_transition_stop_state(revision, rollback_runtime_state)
        _require_preserved_activation_rollovers_v1(preserved_rollovers)
        _systemctl_ok("stop", SERVICE_NAME, timeout=60)
        _require_preserved_activation_rollovers_v1(preserved_rollovers)
        final_previous = _capture_unit_snapshot()
        if (
            final_previous.content != snapshot.content
            or final_previous.mode != snapshot.mode
            or final_previous.digest != snapshot.digest
            or final_previous.device != snapshot.device
        ):
            raise M5ServiceActivationFailedV1("m5_service_rollback_material_changed")
        final_active = _install_and_start_candidate(
            candidate,
            final_previous,
            preserved_rollovers,
        )
        final_proof = _browser_proof(
            selectors, revision=revision, require_revision=True
        )
        if final_proof["registry_digest_before"] != baseline_digest:
            raise M5ServiceActivationFailedV1("m5_service_registry_changed")
        _require_revision(revision)
        validate_receipt_systemd_ownership_v1(
            candidate,
            restarted_main_pid=final_active.main_pid,
            restarted_start_time_ticks=final_active.main_pid_start_time_ticks,
            observation=observe_selected_systemd_service_v1(candidate),
        )
        _verify_transition_material(candidate, snapshot, document)
        if _database_state(DATABASE_PATH) != database_state:
            raise M5ServiceActivationFailedV1("m5_service_database_changed")
        _require_revision(revision)
        failure_phase = "candidate_finalizing"
        validate_m5_service_activation_lock_v1(activation_lock)
        created_receipt_identity = _write_receipt(
            candidate,
            final_active,
            snapshot=snapshot,
            rollback_runtime_state=rollback_runtime_state,
            preserved_rollovers=preserved_rollovers,
        )
        validate_m5_service_activation_lock_v1(activation_lock)
        release_m5_service_activation_lock_v1(activation_lock)
        return final_active
    except (Exception, KeyboardInterrupt) as error:
        receipt_cleanup_error: M5ServiceActivationFailedV1 | None = None
        if created_receipt_identity is not None:
            try:
                _require_preserved_activation_rollovers_v1(preserved_rollovers)
                _unlink_created_activation_receipt_v1(
                    RECEIPT_PATH,
                    device=created_receipt_identity[0],
                    inode=created_receipt_identity[1],
                )
                _require_preserved_activation_rollovers_v1(preserved_rollovers)
            except (
                M5ServiceActivationErrorV1,
                M5ServiceActivationFailedV1,
            ) as cleanup_error:
                receipt_cleanup_error = M5ServiceActivationFailedV1(str(cleanup_error))
        if service_mutated:
            _recover_post_stop_failure(
                error,
                snapshot,
                candidate,
                rollback_runtime_state,
                failure_phase=failure_phase,
                receipt_cleanup_error=receipt_cleanup_error,
                preserved_rollovers=preserved_rollovers,
            )
        if receipt_cleanup_error is not None:
            raise receipt_cleanup_error from error
        if isinstance(error, KeyboardInterrupt):
            raise
        if isinstance(error, (M5ServiceActivationErrorV1, M5ServiceActivationFailedV1)):
            raise
        raise M5ServiceActivationFailedV1("m5_service_activation_failed") from None


def _activate_under_lock(
    selectors: ActivationSelectorsV1,
    activation_lock: M5CompletionLockV1,
) -> SystemdServiceObservationV1:
    _validate_owner_files()
    rollback_runtime_state = _rollback_runtime_state()
    revision = clean_detached_revision_v1(ROOT)
    candidate = candidate_for_checkout_v1(source_revision=revision)
    archive_chain = _maybe_correct_completed_activation_rollover_v1(
        selectors,
        candidate,
        rollback_runtime_state,
        activation_lock,
    )
    preserved_rollovers = tuple(archive.retained for archive in archive_chain)
    try:
        _require_preserved_activation_rollovers_v1(preserved_rollovers)
        return _continue_activation_under_lock(
            selectors,
            activation_lock,
            rollback_runtime_state,
            revision,
            candidate,
            preserved_rollovers,
        )
    finally:
        _close_activation_rollover_archive_chain_v1(archive_chain)


def _activate(selectors: ActivationSelectorsV1) -> SystemdServiceObservationV1:
    """Serialize every inspection, recovery, mutation, and rollback attempt."""

    activation_lock = acquire_m5_service_activation_lock_v1()
    try:
        validate_m5_service_activation_lock_v1(activation_lock)
        return _activate_under_lock(selectors, activation_lock)
    except BaseException as body_error:
        cleanup_error: M5ServiceActivationErrorV1 | None = None
        try:
            release_m5_service_activation_lock_v1(activation_lock)
        except M5ServiceActivationErrorV1 as error:
            cleanup_error = error
        selected_error = select_m5_service_activation_result_v1(
            body_error,
            cleanup_error,
        )
        if selected_error is body_error:
            raise
        if selected_error is None:
            raise M5ServiceActivationFailedV1("m5_service_activation_failed") from None
        raise selected_error from body_error


def _status() -> tuple[bool, str]:
    try:
        if _path_present(RECEIPT_PATH):
            receipt = _load_json_artifact(RECEIPT_PATH)
            revision = receipt.get("candidate_revision")
            root_value = receipt.get("candidate_root")
            if (
                not isinstance(revision, str)
                or _REVISION.fullmatch(revision) is None
                or not isinstance(root_value, str)
            ):
                raise M5ServiceActivationErrorV1("m5_service_receipt_invalid")
            root = Path(root_value)
            if (
                root.resolve(strict=True) != root
                or _read_clean_revision(root) != revision
            ):
                raise M5ServiceActivationErrorV1("m5_service_receipt_invalid")
            candidate = candidate_for_checkout_v1(
                source_revision=revision,
                checkout_root=root,
            )
            transition = _existing_transition_snapshot(candidate)
            if transition is None:
                raise M5ServiceActivationErrorV1("m5_service_receipt_invalid")
            snapshot, _, document = transition
            _validate_receipt(receipt, candidate)
            rollback_runtime_state = _rollback_runtime_state()
            if (
                receipt["rollback_unit_digest"] != snapshot.digest
                or receipt["rollback_runtime_digest"]
                != rollback_runtime_state.tree_digest
                or receipt["journal_digest"]
                != hashlib.sha256(_json_bytes(document)).hexdigest()
            ):
                raise M5ServiceActivationErrorV1("m5_service_receipt_invalid")
            active = observe_selected_systemd_service_v1(candidate)
            validate_selected_systemd_service_v1(candidate, active)
            return True, f"receipt-bound clean revision {revision}"
        info, content = _safe_regular_file(UNIT_PATH, maximum=MAX_UNIT_BYTES)
        snapshot = UnitSnapshotV1(
            UNIT_PATH,
            content,
            stat.S_IMODE(info.st_mode),
            hashlib.sha256(content).hexdigest(),
            info.st_dev,
            info.st_ino,
        )
        rollback = _rollback_candidate(snapshot)
        _rollback_runtime_state()
        active = observe_selected_systemd_service_v1(rollback)
        validate_rollback_systemd_service_v1(rollback, active)
        return True, f"trusted rollback revision {PINNED_ROLLBACK_REVISION}"
    except (M5ServiceActivationErrorV1, M5ServiceActivationFailedV1, OSError):
        return False, "service binding unavailable"


def main(arguments: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--status", action="store_true")
    options = parser.parse_args(arguments)
    if options.status:
        passed, detail = _status()
        print(f"M5 SERVICE STATUS: {'YES' if passed else 'NO'} — {detail}")
        return 0 if passed else 3
    try:
        # Selectors are deliberately the first live-operation step. A bare
        # canonical invocation cannot inspect or mutate the user unit.
        selectors = _selectors(os.environ)
        active = _activate(selectors)
        print(
            "M5 SERVICE ACTIVATION: PASSED — exact clean revision active under "
            f"systemd; AGENTMONITOR_M5_SERVICE_PID={active.main_pid}"
        )
        return 0
    except M5ServiceActivationRerunRequiredV1 as error:
        print(
            "M5 SERVICE ACTIVATION: RERUN REQUIRED — trusted rollback active; "
            f"AGENTMONITOR_M5_SERVICE_PID={error.trusted_service_pid}"
        )
        return 5
    except M5ServiceActivationRollbackFailedV1 as error:
        print(f"M5 SERVICE ACTIVATION: FAILED — {error}")
        return 4
    except M5ServiceActivationErrorV1 as error:
        print(f"M5 SERVICE ACTIVATION: BLOCKED — {error}")
        return 3
    except M5ServiceActivationFailedV1 as error:
        print(f"M5 SERVICE ACTIVATION: FAILED — {error}")
        return 1
    except (OSError, subprocess.SubprocessError, UnicodeError, ValueError):
        print("M5 SERVICE ACTIVATION: FAILED — execution_unavailable")
        return 1


if __name__ == "__main__":
    sys.exit(main())
