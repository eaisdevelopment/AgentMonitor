"""Fail-closed current-revision acceptance of the bounded V1-M5 Codex slice."""

from __future__ import annotations

import hashlib
import json
import os
import posixpath
import re
import stat
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import NoReturn, cast

from tools.automation.implementations.auto_m3_current_exit import (
    M3CurrentExitErrorV1,
    ServiceLaunchV1,
    _process_start_ticks,
    _read_service_launch,
)
from tools.automation.implementations.m5_codex_admission import (
    M5CodexAdmissionErrorV1,
    M5CodexAdmissionUnavailableV1,
    verify_codex_admission_v1,
)
from tools.automation.implementations.m5_codex_containment import (
    M5CodexContainmentErrorV1,
    M5CodexContainmentUnavailableV1,
    verify_codex_managed_profile_containment_v1,
)
from tools.automation.implementations.m5_codex_quota_witness import (
    QUOTA_WITNESS_BASENAME,
    M5CodexQuotaWitnessErrorV1,
    ValidatedQuotaWitnessV1,
    read_quota_witness_v1,
    registry_graph_digest_for_root_v1,
)
from tools.automation.implementations.m5_completion_lock import (
    M5CompletionLockErrorV1,
    M5CompletionLockV1,
    acquire_m5_completion_lock_v1,
    release_m5_completion_lock_v1,
    validate_m5_completion_lock_v1,
)
from tools.automation.implementations.m5_owner_outcomes import (
    OWNER_OUTCOMES_BASENAME,
    M5OwnerOutcomesErrorV1,
    read_owner_outcomes_file_v2,
)
from tools.automation.implementations.m5_service_activation import (
    M5ServiceActivationErrorV1,
    M5ServiceActivationFailedV1,
    M5ServiceCandidateV1,
    SystemdServiceObservationV1,
    ValidatedM5ServiceActivationReceiptV1,
    acquire_m5_service_activation_lock_v1,
    clean_detached_revision_v1,
    observe_selected_systemd_service_v1,
    release_m5_service_activation_lock_v1,
    restart_selected_systemd_service_v1,
    revalidate_current_systemd_binding_v1,
    select_current_systemd_binding_v1,
    validate_current_activation_receipt_v1,
    validate_m5_service_activation_lock_v1,
    validate_receipt_systemd_ownership_v1,
    verify_current_service_revision_browser_v1,
)

ROOT = Path(__file__).resolve().parents[3]
RECEIPT_RECORD_TYPE = "agentmonitor.m5_current_gate_receipt"
CANONICAL_COMMAND = "python3 tools/automation/run.py AUTO-M5-EXIT"
RECEIPT_DIRECTORY_NAME = ".agentmonitor-local"
RECEIPT_BASENAME = "m5-current-gate-receipt.json"
RECEIPT_PATH = ROOT / RECEIPT_DIRECTORY_NAME / RECEIPT_BASENAME
ALERT_WITNESS_BASENAME = "m5-alert-witness.json"
ALERT_WITNESS_SCHEMA = "agentmonitor.m5-alert-witness.v2"
ALERT_REGISTRY_DIGEST_SCOPE = "all-public-registry-fields-v1"

CODEX_PROVIDER_VERSION = "0.160.0"
CODEX_ADAPTER_ID = "agentmonitor.codex"
CODEX_ADAPTER_VERSION = "1.0.2"
CODEX_PARSER_VERSION = "1.0.1"
CODEX_RATE_LIMITS_SOURCE_ID = "codex.app-server.account-rate-limits-read.v2"
CODEX_MAPPING_ID = "M5-CDX-0-160-0-002"
CODEX_MAPPING_DIGEST = (
    "417c46ba301f9c4217c606beed52be93c9bf497da9ca5b99ca4b1993167688d3"
)
CODEX_SCHEMA_BUNDLE_DIGEST = (
    "36bd8e1d76b12b89b06446a85c45e957945eb8cb63b05061264c3dec97f625da"
)

REQUIRED_LANES = (
    "service_activation",
    "owner_outcomes",
    "alert_prerequisite",
    "exact_codex_admission",
    "authenticated_containment",
    "build",
    "revision_bound_service",
    "technical_suite",
    "codex_browser",
    "process_witness",
    "fresh_quota_lineage",
    "authoritative_quota_reconciliation",
    "alert_lifecycle",
    "registry_unchanged",
    "provider_health",
    "generated_client",
    "sqlite",
    "overview_browser",
    "alerts_browser",
    "operations_browser",
    "planning",
    "quality",
    "mutation",
    "documentation",
    "git_preflight",
)
PRE_SERVICE_ROUTINES = (("build", "AUTO-BUILD"),)
DEPENDENCY_ROUTINES = ("AUTO-M3-TEST",)
LOCAL_ROUTINES = (
    ("planning", "AUTO-PLAN-CHECK"),
    ("quality", "AUTO-QUALITY"),
    ("mutation", "AUTO-MUTATION"),
    ("documentation", "AUTO-DOCS-CHECK"),
    ("git_preflight", "AUTO-GIT-PREFLIGHT"),
)
LIVE_SELECTORS = (
    "AGENTMONITOR_TEST_OWNER_DATA_ROOT",
    "AGENTMONITOR_TEST_DATA_ROOT",
    "AGENTMONITOR_TEST_DASHBOARD_CDP_ENDPOINT",
    "AGENTMONITOR_TEST_DASHBOARD_ORIGIN",
    "AGENTMONITOR_M5_SERVICE_PID",
)
BROWSER_CHECKS = (
    ("overview_browser", "tools/ui/verify_dashboard_provider_filter.mjs"),
    ("alerts_browser", "tools/ui/verify_m4_alerts.mjs"),
    ("operations_browser", "tools/ui/verify_m4_operations.mjs"),
)
STORY_TEST_PATHS = (
    "tools/git/test_preflight.py",
    "tools/automation/test_m5_prerequisite_archive.py",
    "tools/automation/test_m5_completion_lock.py",
    "tools/automation/test_m5_current_exit.py",
    "tools/automation/test_m5_service_activation.py",
    "tools/automation/test_m5_owner_outcomes.py",
    "tools/automation/test_m5_codex_alert_witness.py",
    "tools/automation/test_m5_codex_mutation_policies.py",
    "tools/automation/test_m5_codex_admission.py",
    "tools/automation/test_m5_codex_containment.py",
    "tools/automation/test_m5_codex_quota_witness.py",
    "backend/tests/contracts/providers/codex",
    "backend/tests/adapters/providers/codex",
    "backend/tests/integration/api/test_codex_dashboard_composition.py",
    "backend/tests/integration/capacity/test_codex_capacity_history.py",
    "backend/tests/integration/capacity/test_m4_event_delivery.py::"
    "test_acknowledged_event_evidence_selector_bounds_fail_closed",
    "backend/tests/integration/collection_control/test_codex_composition.py",
    "backend/tests/integration/collection_control/test_codex_dashboard_collection.py",
    "backend/tests/integration/registry/test_codex_managed_connection.py",
    "backend/tests/integration/registry/test_provider_connection_dispatch.py",
    "backend/tests/integration/alerting/test_codex_capacity_lifecycle.py",
    "backend/tests/integration/operations/test_health_and_diagnostics.py",
    "backend/tests/integration/foundation/test_source_revision.py",
    "backend/tests/integration/api/test_openapi_policy.py",
    "backend/tests/integration/api/test_operations_routes.py",
    "backend/tests/integration/api/test_provider_connection_routes.py",
    "backend/tests/operations/pure/test_diagnostic_policy.py",
    "backend/tests/integration/provider_system/test_compatibility.py",
    "backend/tests/live/codex/test_codex_process_locations.py",
    "backend/tests/live/codex/test_codex_runtime_observation.py",
    "backend/tests/integration/release/test_v1_m5_codex_slice.py",
)
STORY_AUTOMATION_TEST_IDS = (
    "tools/automation/test_run.py::AutomationRoutineTests::test_m5_service_activation_rerun_is_not_reported_as_failure",
    "tools/automation/test_run.py::AutomationRoutineTests::test_m5_service_activation_without_selection_never_mutates_unit",
    "tools/automation/test_run.py::AutomationRoutineTests::test_m5_prerequisite_archive_without_selection_never_moves_files",
    "tools/automation/test_run.py::AutomationRoutineTests::test_m5_owner_outcomes_without_real_selectors_never_writes_file",
    "tools/automation/test_run.py::AutomationRoutineTests::test_m5_alert_witness_without_real_selectors_never_writes_receipt",
    "tools/automation/test_run.py::AutomationRoutineTests::test_m5_quota_witness_without_real_selectors_never_writes_receipt",
    "tools/automation/test_run.py::AutomationRoutineTests::test_m5_exit_without_real_selectors_never_claims_completion",
    "tools/automation/test_run.py::AutomationRoutineTests::test_real_catalog_defines_every_mandatory_routine",
)
STORY_NODE_TEST_PATHS = (
    "tools/ui/test_m5_codex_policy.mjs",
    "frontend/tests/pure/alert-history-pagination.mjs",
    "frontend/tests/pure/alert-presentation.mjs",
    "frontend/tests/pure/provider-account-presentation.mjs",
    "frontend/tests/pure/quota-reset-presentation.mjs",
)
STORY_NODE_TEST_COUNT = 21
STORY_NODE_TEST_INVENTORY_SHA256 = (
    "ac6afb5a290f5bf5940581ef13db21acccce947f3d40f97b498b57189f2db7e7"
)
STORY_BROWSER_SCENARIOS = ("account_beyond_page",)
# Updated only from the exact collected inventory after intentional test changes.
STORY_PYTEST_TEST_COUNT = 600
STORY_PYTEST_DECLARED_TEST_COUNT = 1_158
STORY_PYTEST_TEST_INVENTORY_SHA256 = (
    "ad0b77bd19a52f0b0ff29958963414e6836882a659096d7f291cafb7368e4b3e"
)
STORY_ARTIFACTS = (
    "tools/git/preflight.py",
    "tools/automation/_m5_test_git.py",
    "tools/automation/implementations/m5_completion_lock.py",
    "tools/automation/implementations/m5_service_activation.py",
    "tools/automation/test_m5_service_activation.py",
    "tools/automation/implementations/m5_prerequisite_archive.py",
    "tools/automation/implementations/m5_owner_outcomes.py",
    "tools/automation/test_m5_owner_outcomes.py",
    "tools/automation/implementations/m5_codex_alert_witness.py",
    "tools/automation/test_m5_codex_alert_witness.py",
    "tools/automation/test_m5_codex_mutation_policies.py",
    "tools/automation/implementations/m5_codex_admission.py",
    "tools/automation/test_m5_codex_admission.py",
    "tools/automation/implementations/m5_codex_containment.py",
    "tools/automation/test_m5_codex_containment.py",
    "tools/automation/implementations/m5_codex_quota_witness.py",
    "tools/automation/test_m5_codex_quota_witness.py",
    "tools/automation/test_run.py",
    "tools/ui/m5_codex_policy.mjs",
    *STORY_NODE_TEST_PATHS,
    "tools/ui/verify_m5_codex.mjs",
    "tools/ui/verify_m5_service_revision.mjs",
    "tools/ui/verify_m5_codex_alert_lifecycle.mjs",
    "tools/ui/verify_m5_codex_quota_reconciliation.mjs",
    "tools/ui/verify_dashboard_provider_filter.mjs",
    "tools/ui/m5_registry_pages.mjs",
    "frontend/tests/browser/p02/run_browser.py",
    "frontend/tests/browser/p02/account_beyond_page.mjs",
    *STORY_TEST_PATHS,
)
STORY_PYTEST_FLAGS = (
    "-c",
    "backend/pyproject.toml",
    "--rootdir=.",
    "-o",
    "junit_family=legacy",
    "-q",
    "--tb=short",
    "-p",
    "tools.automation.pytest_no_skip",
    "--import-mode=importlib",
)

_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_REVISION = re.compile(r"[0-9a-f]{40}\Z")
_OPAQUE = re.compile(r"[A-Za-z0-9_-]{1,64}\Z")
_SAFE_EVIDENCE = re.compile(r"[A-Za-z0-9_.:+-]{1,160}\Z")
_UTC_TIMESTAMP = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{3})?Z\Z")
_MAX_PREREQUISITE_AGE = timedelta(days=8)
_MAIN_BROWSER_WITNESS_KEYS = frozenset(
    {
        "event",
        "service_revision",
        "account_count",
        "verified_count",
        "owner_unavailable_count",
        "current_history_count",
        "fresh_after_restart_count",
        "process_count",
        "process_scan_truncated",
        "mutations",
        "provider_version",
        "adapter_version",
        "parser_version",
        "schema_bundle_digest",
        "mapping_id",
        "mapping_digest",
        "provider_health",
        "fleet_metadata_digest",
        "identity_set_digest",
        "collection_run_set_digest",
        "quota_value_set_digest",
        "history_value_set_digest",
        "process_set_digest",
        "registry_digest",
    }
)


class M5CurrentExitErrorV1(ValueError):
    """One sanitized missing or invalid live-prerequisite reason."""


class M5CurrentExitFailedV1(M5CurrentExitErrorV1):
    """A required implemented M5 boundary failed."""


@dataclass(frozen=True, slots=True)
class CreatedM5ReceiptV1:
    """An open handle to the exact final receipt inode created by this run."""

    descriptor: int
    device: int
    inode: int


def _missing_story_artifacts_v1(
    root: Path, artifacts: tuple[str, ...]
) -> tuple[str, ...]:
    """Return static selectors whose source artifacts are absent."""

    missing: list[str] = []
    for artifact in artifacts:
        source_path = artifact.partition("::")[0]
        if not source_path or not (root / source_path).exists():
            missing.append(artifact)
    return tuple(missing)


def _translated_service_error_v1(
    error: M3CurrentExitErrorV1, *, pre_restart: bool
) -> M5CurrentExitErrorV1:
    """Preserve a changed input as Blocked and type gate-owned failures Failed."""

    if pre_restart and str(error) == "m3_current_service_process_invalid":
        return M5CurrentExitErrorV1("m5_current_service_selection_changed")
    return M5CurrentExitFailedV1(
        "m5_current_service_restart_failed"
        if pre_restart
        else "m5_current_service_receipt_binding_failed"
    )


def _translated_systemd_service_error_v1(
    error: M5ServiceActivationErrorV1 | M5ServiceActivationFailedV1,
    *,
    pre_restart: bool,
) -> M5CurrentExitErrorV1:
    """Map selection drift to Blocked and gate-owned failures to Failed."""

    if pre_restart and isinstance(error, M5ServiceActivationErrorV1):
        return M5CurrentExitErrorV1("m5_current_service_selection_changed")
    return M5CurrentExitFailedV1(
        "m5_current_service_restart_failed"
        if pre_restart
        else "m5_current_service_receipt_binding_failed"
    )


def _translated_checkout_error_v1(
    error: M3CurrentExitErrorV1,
) -> M5CurrentExitErrorV1:
    """Keep a dirty checkout Blocked and type Git execution defects Failed."""

    if str(error) == "m3_current_checkout_not_clean":
        return M5CurrentExitErrorV1("m5_current_checkout_not_clean")
    return M5CurrentExitFailedV1("m5_current_git_revision_failed")


def _clean_m5_revision_v1() -> str:
    try:
        return clean_detached_revision_v1(ROOT)
    except M5ServiceActivationErrorV1 as error:
        if str(error) == "m5_service_checkout_not_clean":
            raise M5CurrentExitErrorV1("m5_current_checkout_not_clean") from error
        raise M5CurrentExitFailedV1("m5_current_git_revision_failed") from error


def _acquire_m5_current_service_transition_lock_v1(
    transition_root: Path | None = None,
) -> M5CompletionLockV1:
    """Map the shared service transition lock into fail-closed M5 exit reasons."""

    try:
        if transition_root is None:
            return acquire_m5_service_activation_lock_v1()
        return acquire_m5_service_activation_lock_v1(transition_root)
    except M5ServiceActivationErrorV1 as error:
        reason = (
            "m5_current_service_transition_busy"
            if str(error) == "m5_service_activation_busy"
            else "m5_current_service_transition_lock_invalid"
        )
        raise M5CurrentExitErrorV1(reason) from None


def _validate_m5_current_service_transition_lock_v1(
    lock: M5CompletionLockV1,
) -> None:
    try:
        validate_m5_service_activation_lock_v1(lock)
    except M5ServiceActivationErrorV1:
        raise M5CurrentExitErrorV1(
            "m5_current_service_transition_lock_changed"
        ) from None


def _release_m5_current_service_transition_lock_v1(
    lock: M5CompletionLockV1,
) -> M5CurrentExitFailedV1 | None:
    """Release without allowing cleanup failure to escape the gate result."""

    try:
        release_m5_service_activation_lock_v1(lock)
    except M5ServiceActivationErrorV1:
        return M5CurrentExitFailedV1("m5_current_service_transition_release_failed")
    return None


def _select_m5_current_result_v1(
    body_code: int | None,
    body_message: str | None,
    cleanup_errors: tuple[M5CurrentExitFailedV1, ...],
) -> tuple[int | None, str | None]:
    """Preserve a typed body result, otherwise report the first cleanup failure."""

    if body_code is not None:
        if body_code not in {1, 3} or not body_message:
            raise M5CurrentExitFailedV1("m5_current_result_invalid")
        return body_code, body_message
    if body_message is not None:
        raise M5CurrentExitFailedV1("m5_current_result_invalid")
    if cleanup_errors:
        return 1, f"M5 CURRENT EXIT: FAILED — {cleanup_errors[0]}"
    return None, None


def _m5_current_receipt_cleanup_required_v1(
    *,
    receipt_created: bool,
    receipt_removed: bool,
    result_code: int | None,
    pending_base_exception: BaseException | None,
    cleanup_errors: tuple[M5CurrentExitFailedV1, ...],
) -> bool:
    """Require invalidation for every unsuccessful or interrupted finalization."""

    return (
        receipt_created
        and not receipt_removed
        and (
            result_code is not None
            or pending_base_exception is not None
            or bool(cleanup_errors)
        )
    )


def _validate_activation_receipt_for_exit_v1(
    candidate: M5ServiceCandidateV1,
    current: SystemdServiceObservationV1 | None = None,
) -> ValidatedM5ServiceActivationReceiptV1:
    try:
        observed = current or observe_selected_systemd_service_v1(candidate)
        return validate_current_activation_receipt_v1(candidate, observed)
    except M5ServiceActivationErrorV1:
        raise M5CurrentExitErrorV1("m5_current_activation_receipt_invalid") from None


@dataclass(frozen=True, slots=True)
class SelectedServiceV1:
    """Exact already-running AgentMonitor process authorized for restart."""

    pid: int
    start_time_ticks: int
    launch: ServiceLaunchV1
    candidate: M5ServiceCandidateV1 | None = field(default=None, repr=False)
    systemd_observation: SystemdServiceObservationV1 | None = field(
        default=None, repr=False
    )


@dataclass(frozen=True, slots=True)
class VerifiedOwnerOutcomeV1:
    """Private gate input; fields must never enter public evidence."""

    account_id: str = field(repr=False)


@dataclass(frozen=True, slots=True)
class OwnerOutcomesV1:
    """Privacy-minimized result plus private selectors needed by live checks."""

    digest: str
    verified: tuple[VerifiedOwnerOutcomeV1, ...] = field(repr=False)
    unavailable_account_ids: tuple[str, ...] = field(repr=False)

    @property
    def account_count(self) -> int:
        return len(self.verified) + len(self.unavailable_account_ids)

    @property
    def verified_count(self) -> int:
        return len(self.verified)

    @property
    def owner_unavailable_count(self) -> int:
        return len(self.unavailable_account_ids)

    @property
    def primary_verified_account_id(self) -> str | None:
        return self.verified[0].account_id if self.verified else None

    @property
    def verified_account_ids(self) -> frozenset[str]:
        return frozenset(item.account_id for item in self.verified)


@dataclass(frozen=True, slots=True)
class AlertWitnessV1:
    """Sanitized facts retained after validating the private alert receipt."""

    digest: str
    owner_action: str
    registry_digest: str


def _utc_text(value: datetime) -> str:
    if value.utcoffset() is None or value.utcoffset() != timedelta(0):
        raise M5CurrentExitFailedV1("m5_current_receipt_time_invalid")
    return value.isoformat(timespec="seconds").replace("+00:00", "Z")


def _utc_value(value: object) -> datetime:
    if type(value) is not str or _UTC_TIMESTAMP.fullmatch(value) is None:
        raise ValueError
    parsed = datetime.fromisoformat(value)
    if parsed.utcoffset() != timedelta(0):
        raise ValueError
    return parsed


def _digest_values(values: object) -> str:
    payload = json.dumps(
        values, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _read_private_json_v1(
    path: Path, *, expected_basename: str, error_code: str
) -> tuple[object, str]:
    descriptor = -1
    parent_descriptor = -1
    try:
        if not path.is_absolute() or path.name != expected_basename:
            raise OSError
        parent_descriptor = os.open(
            path.parent,
            os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
        )
        parent_metadata = os.fstat(parent_descriptor)
        parent_path_metadata = path.parent.lstat()
        if (
            path.parent.resolve(strict=True) != path.parent
            or not stat.S_ISDIR(parent_metadata.st_mode)
            or parent_metadata.st_uid != os.getuid()
            or stat.S_IMODE(parent_metadata.st_mode) != 0o700
            or (parent_metadata.st_dev, parent_metadata.st_ino)
            != (parent_path_metadata.st_dev, parent_path_metadata.st_ino)
        ):
            raise OSError
        descriptor = os.open(
            path.name,
            os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC,
            dir_fd=parent_descriptor,
        )
        metadata = os.fstat(descriptor)
        path_metadata = os.stat(
            path.name, dir_fd=parent_descriptor, follow_symlinks=False
        )
        if (
            not stat.S_ISREG(metadata.st_mode)
            or metadata.st_uid != os.getuid()
            or stat.S_IMODE(metadata.st_mode) != 0o600
            or metadata.st_nlink != 1
            or not 2 <= metadata.st_size <= 16_384
            or (metadata.st_dev, metadata.st_ino)
            != (path_metadata.st_dev, path_metadata.st_ino)
        ):
            raise OSError
        remaining = metadata.st_size
        chunks: list[bytes] = []
        while remaining:
            chunk = os.read(descriptor, remaining)
            if not chunk:
                raise OSError
            chunks.append(chunk)
            remaining -= len(chunk)
        payload = b"".join(chunks)
        final_metadata = os.fstat(descriptor)
        final_path_metadata = os.stat(
            path.name, dir_fd=parent_descriptor, follow_symlinks=False
        )
        final_parent_metadata = os.fstat(parent_descriptor)
        final_parent_path_metadata = path.parent.lstat()
        if (
            len(payload) != metadata.st_size
            or final_metadata.st_size != metadata.st_size
            or (final_metadata.st_dev, final_metadata.st_ino)
            != (metadata.st_dev, metadata.st_ino)
            or (final_path_metadata.st_dev, final_path_metadata.st_ino)
            != (metadata.st_dev, metadata.st_ino)
            or not stat.S_ISDIR(final_parent_metadata.st_mode)
            or final_parent_metadata.st_uid != os.getuid()
            or stat.S_IMODE(final_parent_metadata.st_mode) != 0o700
            or (final_parent_metadata.st_dev, final_parent_metadata.st_ino)
            != (parent_metadata.st_dev, parent_metadata.st_ino)
            or (final_parent_path_metadata.st_dev, final_parent_path_metadata.st_ino)
            != (parent_metadata.st_dev, parent_metadata.st_ino)
        ):
            raise OSError
        document = json.loads(payload.decode("utf-8"))
        return document, hashlib.sha256(payload).hexdigest()
    except (
        OSError,
        RuntimeError,
        UnicodeError,
        ValueError,
        TypeError,
        json.JSONDecodeError,
    ):
        raise M5CurrentExitErrorV1(error_code) from None
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        if parent_descriptor >= 0:
            os.close(parent_descriptor)


def read_owner_outcomes_v1(
    path: Path,
    *,
    expected_revision: str,
    selected_service: SelectedServiceV1,
    now: datetime,
) -> OwnerOutcomesV1:
    """Validate the exact fresh owner attestation for the pre-gate service."""

    try:
        document, digest = read_owner_outcomes_file_v2(path, now=now)
        if (
            _REVISION.fullmatch(expected_revision) is None
            or document.implementation_revision != expected_revision
            or document.service_pid != selected_service.pid
            or document.service_start_time_ticks != selected_service.start_time_ticks
        ):
            raise ValueError
        ordered_verified = tuple(
            sorted(
                (
                    VerifiedOwnerOutcomeV1(item.account_id)
                    for item in document.outcomes
                    if item.disposition == "verified"
                ),
                key=lambda item: item.account_id,
            )
        )
        return OwnerOutcomesV1(
            digest=digest,
            verified=ordered_verified,
            unavailable_account_ids=document.unavailable_account_ids,
        )
    except (M5OwnerOutcomesErrorV1, TypeError, ValueError):
        raise M5CurrentExitErrorV1("m5_current_owner_outcomes_invalid") from None


def read_alert_witness_v1(
    path: Path,
    *,
    expected_revision: str,
    selected_service: SelectedServiceV1,
    verified_account_ids: frozenset[str],
    now: datetime,
) -> AlertWitnessV1:
    """Validate a prior owner action and source-proven alert recovery receipt."""

    document, digest = _read_private_json_v1(
        path,
        expected_basename=ALERT_WITNESS_BASENAME,
        error_code="m5_current_alert_witness_invalid",
    )
    expected_keys = {
        "schema",
        "implementation_revision",
        "service_source_revision",
        "service_pid",
        "service_start_time_ticks",
        "service_started_at",
        "service_checked_at",
        "service_versions_digest",
        "provider_key",
        "account_id",
        "source_id",
        "provider_version",
        "adapter_id",
        "adapter_version",
        "parser_version",
        "mapping_id",
        "mapping_digest",
        "schema_bundle_digest",
        "alert_record_version",
        "alert_aggregate_sequence",
        "opened_at",
        "deduplicated_at",
        "owner_action_at",
        "recovered_at",
        "recorded_at",
        "owner_action",
        "opened",
        "deduplicated",
        "browser_presented",
        "recovered",
        "source_proven_opening",
        "source_proven_deduplication",
        "source_proven_recovery",
        "source_event_digest",
        "source_observation_digest",
        "opening_observation_digest",
        "deduplication_observation_digest",
        "recovery_observation_digest",
        "source_delivery_receipt_digest",
        "alert_history_digest",
        "owner_action_receipt_digest",
        "registry_digest_scope",
        "registry_digest_before",
        "registry_digest_after",
    }
    try:
        if type(document) is not dict or set(document) != expected_keys:
            raise ValueError
        times = tuple(
            _utc_value(document[key])
            for key in (
                "service_started_at",
                "opened_at",
                "deduplicated_at",
                "owner_action_at",
                "recovered_at",
                "service_checked_at",
                "recorded_at",
            )
        )
        digests = tuple(
            document[key]
            for key in (
                "service_versions_digest",
                "source_event_digest",
                "source_observation_digest",
                "opening_observation_digest",
                "deduplication_observation_digest",
                "recovery_observation_digest",
                "source_delivery_receipt_digest",
                "alert_history_digest",
                "owner_action_receipt_digest",
                "registry_digest_before",
                "registry_digest_after",
            )
        )
        if (
            document["schema"] != ALERT_WITNESS_SCHEMA
            or document["implementation_revision"] != expected_revision
            or document["service_source_revision"] != expected_revision
            or _REVISION.fullmatch(expected_revision) is None
            or type(document["service_pid"]) is not int
            or document["service_pid"] != selected_service.pid
            or type(document["service_start_time_ticks"]) is not int
            or document["service_start_time_ticks"] != selected_service.start_time_ticks
            or document["provider_key"] != "codex"
            or document["account_id"] not in verified_account_ids
            or document["source_id"] != CODEX_RATE_LIMITS_SOURCE_ID
            or document["provider_version"] != CODEX_PROVIDER_VERSION
            or document["adapter_id"] != CODEX_ADAPTER_ID
            or document["adapter_version"] != CODEX_ADAPTER_VERSION
            or document["parser_version"] != CODEX_PARSER_VERSION
            or document["mapping_id"] != CODEX_MAPPING_ID
            or document["mapping_digest"] != CODEX_MAPPING_DIGEST
            or document["schema_bundle_digest"] != CODEX_SCHEMA_BUNDLE_DIGEST
            or type(document["alert_record_version"]) is not int
            or type(document["alert_aggregate_sequence"]) is not int
            or document["alert_record_version"] < 4
            or document["alert_aggregate_sequence"] != document["alert_record_version"]
            or document["owner_action"] not in {"acknowledged", "snoozed"}
            or any(
                document[key] is not True
                for key in (
                    "opened",
                    "deduplicated",
                    "browser_presented",
                    "recovered",
                    "source_proven_opening",
                    "source_proven_deduplication",
                    "source_proven_recovery",
                )
            )
            or any(
                type(value) is not str or _SHA256.fullmatch(value) is None
                for value in digests
            )
            or document["registry_digest_scope"] != ALERT_REGISTRY_DIGEST_SCOPE
            or document["registry_digest_before"] != document["registry_digest_after"]
            or not times[0]
            <= times[1]
            <= times[2]
            <= times[3]
            <= times[4]
            <= times[5]
            <= times[6]
            or times[6] > now + timedelta(minutes=5)
            or now - times[6] > _MAX_PREREQUISITE_AGE
        ):
            raise ValueError
        return AlertWitnessV1(
            digest=digest,
            owner_action=document["owner_action"],
            registry_digest=document["registry_digest_after"],
        )
    except (KeyError, TypeError, ValueError):
        raise M5CurrentExitErrorV1("m5_current_alert_witness_invalid") from None


def build_passed_receipt_v1(
    *,
    implementation_revision: str,
    started_at: datetime,
    completed_at: datetime,
    activation_receipt_digest: str,
    owner_outcomes_digest: str,
    alert_witness_digest: str,
    quota_witness_digest: str,
    quota_value_set_digest: str,
    quota_history_value_set_digest: str,
    post_restart_history_value_set_digest: str,
    owner_observation_digest: str,
    registry_graph_digest: str,
    containment_evidence_digest: str,
    containment_provider_access_count: int,
    containment_provider_write_count: int,
    containment_default_profile_access_count: int,
    containment_default_profile_write_count: int,
    quota_window_count: int,
    fleet_metadata_digest: str,
    identity_set_digest: str,
    collection_run_set_digest: str,
    process_set_digest: str,
    verified_count: int,
    owner_unavailable_count: int,
    process_count: int,
    process_scan_truncated: bool,
    test_count: int,
    lane_evidence: Mapping[str, str],
) -> dict[str, object]:
    """Build a sanitized receipt only for the exact complete M5 lane set."""

    digests = (
        activation_receipt_digest,
        owner_outcomes_digest,
        alert_witness_digest,
        quota_witness_digest,
        quota_value_set_digest,
        quota_history_value_set_digest,
        post_restart_history_value_set_digest,
        owner_observation_digest,
        registry_graph_digest,
        containment_evidence_digest,
        fleet_metadata_digest,
        identity_set_digest,
        collection_run_set_digest,
        process_set_digest,
    )
    if (
        _REVISION.fullmatch(implementation_revision) is None
        or any(_SHA256.fullmatch(value) is None for value in digests)
        or type(verified_count) is not int
        or type(owner_unavailable_count) is not int
        or verified_count < 1
        or owner_unavailable_count < 0
        or verified_count + owner_unavailable_count != 4
        or type(quota_window_count) is not int
        or quota_window_count < verified_count
        or type(containment_provider_access_count) is not int
        or containment_provider_access_count < 1
        or type(containment_provider_write_count) is not int
        or containment_provider_write_count < 0
        or type(containment_default_profile_access_count) is not int
        or containment_default_profile_access_count != 0
        or type(containment_default_profile_write_count) is not int
        or containment_default_profile_write_count != 0
        or type(process_count) is not int
        or not 5 <= process_count <= 6
        or type(process_scan_truncated) is not bool
        or type(test_count) is not int
        or test_count < 1
        or completed_at < started_at
    ):
        raise M5CurrentExitFailedV1("m5_current_receipt_identity_invalid")
    if set(lane_evidence) != set(REQUIRED_LANES) or any(
        type(value) is not str or _SAFE_EVIDENCE.fullmatch(value) is None
        for value in lane_evidence.values()
    ):
        raise M5CurrentExitFailedV1("m5_current_lane_set_invalid")
    completed_text = _utc_text(completed_at)
    return {
        "schema_version": "1.0.0",
        "record_type": RECEIPT_RECORD_TYPE,
        "receipt_id": "M5-CURRENT-GATE-"
        + completed_text.replace(":", "").replace("-", ""),
        "milestone_id": "V1-M5",
        "command_id": "AUTO-M5-EXIT",
        "command": CANONICAL_COMMAND,
        "implementation_revision": implementation_revision,
        "started_at": _utc_text(started_at),
        "completed_at": completed_text,
        "status": "passed",
        "exit_code": 0,
        "skips": [],
        "test_count": test_count,
        "account_count": 4,
        "verified_count": verified_count,
        "owner_unavailable_count": owner_unavailable_count,
        "process_count": process_count,
        "process_scan_completeness": (
            "partial" if process_scan_truncated else "complete"
        ),
        "provider_version": CODEX_PROVIDER_VERSION,
        "adapter_version": CODEX_ADAPTER_VERSION,
        "parser_version": CODEX_PARSER_VERSION,
        "schema_bundle_digest": CODEX_SCHEMA_BUNDLE_DIGEST,
        "mapping_id": CODEX_MAPPING_ID,
        "mapping_digest": CODEX_MAPPING_DIGEST,
        "activation_receipt_digest": activation_receipt_digest,
        "owner_outcomes_digest": owner_outcomes_digest,
        "alert_witness_digest": alert_witness_digest,
        "quota_witness_digest": quota_witness_digest,
        "quota_value_set_digest": quota_value_set_digest,
        "quota_history_value_set_digest": quota_history_value_set_digest,
        "post_restart_history_value_set_digest": (
            post_restart_history_value_set_digest
        ),
        "owner_observation_digest": owner_observation_digest,
        "registry_graph_digest": registry_graph_digest,
        "containment_evidence_digest": containment_evidence_digest,
        "containment_provider_access_count": containment_provider_access_count,
        "containment_provider_write_count": containment_provider_write_count,
        "containment_default_profile_access_count": (
            containment_default_profile_access_count
        ),
        "containment_default_profile_write_count": (
            containment_default_profile_write_count
        ),
        "quota_window_count": quota_window_count,
        "fleet_metadata_digest": fleet_metadata_digest,
        "identity_set_digest": identity_set_digest,
        "collection_run_set_digest": collection_run_set_digest,
        "process_set_digest": process_set_digest,
        "required_lanes": [
            {
                "lane_id": lane,
                "status": "passed",
                "evidence": lane_evidence[lane],
            }
            for lane in REQUIRED_LANES
        ],
    }


def _validate_receipt_target_v1(path: Path) -> None:
    try:
        directory = path.parent.lstat()
    except OSError as error:
        raise M5CurrentExitErrorV1("m5_current_receipt_path_invalid") from error
    if (
        not path.is_absolute()
        or path.name != RECEIPT_BASENAME
        or path.parent.name != RECEIPT_DIRECTORY_NAME
        or not stat.S_ISDIR(directory.st_mode)
        or directory.st_uid != os.getuid()
        or stat.S_IMODE(directory.st_mode) != 0o700
        or path.exists()
        or path.is_symlink()
    ):
        raise M5CurrentExitErrorV1("m5_current_receipt_path_invalid")


def _acquire_m5_current_completion_lock_v1(
    final_receipt_path: Path,
) -> M5CompletionLockV1:
    """Translate shared lifecycle-lock refusal into the M5 exit vocabulary."""

    try:
        return acquire_m5_completion_lock_v1(final_receipt_path)
    except M5CompletionLockErrorV1:
        raise M5CurrentExitErrorV1("m5_current_completion_lock_unavailable") from None


def _validate_m5_current_completion_lock_v1(lock: M5CompletionLockV1) -> None:
    try:
        validate_m5_completion_lock_v1(lock)
    except M5CompletionLockErrorV1:
        raise M5CurrentExitErrorV1("m5_current_completion_lock_changed") from None


def _duplicate_m5_current_guard_descriptors_v1(
    completion_lock: M5CompletionLockV1,
    service_transition_lock: M5CompletionLockV1,
) -> tuple[int, int]:
    """Retain both kernel guard names through post-release receipt cleanup."""

    completion_guard = -1
    transition_guard = -1
    try:
        completion_guard = os.dup(completion_lock.guard_descriptor)
        os.set_inheritable(completion_guard, False)
        transition_guard = os.dup(service_transition_lock.guard_descriptor)
        os.set_inheritable(transition_guard, False)
        return completion_guard, transition_guard
    except OSError:
        if completion_guard >= 0:
            os.close(completion_guard)
        if transition_guard >= 0:
            os.close(transition_guard)
        raise M5CurrentExitFailedV1("m5_current_guard_retention_failed") from None


def _validate_receipt_directory_descriptor_v1(
    path: Path,
    directory_descriptor: int,
    *,
    device: int,
    inode: int,
) -> None:
    """Prove one held directory descriptor still owns the canonical path."""

    directory = os.fstat(directory_descriptor)
    path_directory = path.parent.lstat()
    if (
        not path.is_absolute()
        or path.name != RECEIPT_BASENAME
        or path.parent.name != RECEIPT_DIRECTORY_NAME
        or not stat.S_ISDIR(directory.st_mode)
        or directory.st_uid != os.getuid()
        or stat.S_IMODE(directory.st_mode) != 0o700
        or (directory.st_dev, directory.st_ino) != (device, inode)
        or (path_directory.st_dev, path_directory.st_ino) != (device, inode)
    ):
        raise OSError


def _validate_created_receipt_inode_at_v1(
    directory_descriptor: int,
    basename: str,
    descriptor: int,
    *,
    device: int,
    inode: int,
) -> None:
    """Prove the open receipt and its held-directory entry are one private inode."""

    metadata = os.fstat(descriptor)
    path_metadata = os.stat(
        basename,
        dir_fd=directory_descriptor,
        follow_symlinks=False,
    )
    if (
        basename != RECEIPT_BASENAME
        or not stat.S_ISREG(metadata.st_mode)
        or metadata.st_uid != os.getuid()
        or stat.S_IMODE(metadata.st_mode) != 0o600
        or metadata.st_nlink != 1
        or (metadata.st_dev, metadata.st_ino) != (device, inode)
        or (path_metadata.st_dev, path_metadata.st_ino) != (device, inode)
        or not stat.S_ISREG(path_metadata.st_mode)
        or path_metadata.st_uid != os.getuid()
        or stat.S_IMODE(path_metadata.st_mode) != 0o600
        or path_metadata.st_nlink != 1
    ):
        raise OSError


def _validate_m5_current_final_custody_v1(
    completion_lock: M5CompletionLockV1,
    service_transition_lock: M5CompletionLockV1,
    *,
    directory_descriptor: int,
    created_receipt: CreatedM5ReceiptV1,
) -> None:
    """Revalidate both guards and the canonical receipt entry before success."""

    _validate_m5_current_completion_lock_v1(completion_lock)
    _validate_m5_current_service_transition_lock_v1(service_transition_lock)
    _validate_created_receipt_inode_at_v1(
        directory_descriptor,
        RECEIPT_BASENAME,
        created_receipt.descriptor,
        device=created_receipt.device,
        inode=created_receipt.inode,
    )


def _invalidate_created_receipt_inode_v1(
    directory_descriptor: int,
    basename: str,
    descriptor: int,
    *,
    device: int,
    inode: int,
) -> bool:
    """Erase our exact bytes, then remove only an entry still naming that inode."""

    try:
        metadata = os.fstat(descriptor)
        if (
            not stat.S_ISREG(metadata.st_mode)
            or metadata.st_uid != os.getuid()
            or (metadata.st_dev, metadata.st_ino) != (device, inode)
        ):
            return False
        os.ftruncate(descriptor, 0)
        os.fsync(descriptor)
        try:
            current = os.stat(
                basename,
                dir_fd=directory_descriptor,
                follow_symlinks=False,
            )
        except FileNotFoundError:
            os.fsync(directory_descriptor)
            return True
        if (current.st_dev, current.st_ino) != (device, inode):
            os.fsync(directory_descriptor)
            return True
        os.unlink(basename, dir_fd=directory_descriptor)
        os.fsync(directory_descriptor)
        return True
    except OSError:
        return False


def _remove_failed_m5_current_receipt_v1(
    directory_descriptor: int,
    receipt_descriptor: int,
    *,
    basename: str,
    directory_device: int,
    directory_inode: int,
    device: int,
    inode: int,
) -> None:
    """Invalidate our pass bytes and remove only its unchanged private entry."""

    try:
        directory = os.fstat(directory_descriptor)
        receipt = os.fstat(receipt_descriptor)
        if (
            basename != RECEIPT_BASENAME
            or not stat.S_ISDIR(directory.st_mode)
            or directory.st_uid != os.getuid()
            or (directory.st_dev, directory.st_ino)
            != (directory_device, directory_inode)
            or not stat.S_ISREG(receipt.st_mode)
            or receipt.st_uid != os.getuid()
            or (receipt.st_dev, receipt.st_ino) != (device, inode)
            or type(device) is not int
            or device < 0
            or type(inode) is not int
            or inode <= 0
        ):
            raise OSError
        os.ftruncate(receipt_descriptor, 0)
        os.fsync(receipt_descriptor)
        try:
            current = os.stat(
                basename,
                dir_fd=directory_descriptor,
                follow_symlinks=False,
            )
        except FileNotFoundError:
            raise OSError from None
        if (
            not stat.S_ISREG(current.st_mode)
            or current.st_uid != os.getuid()
            or stat.S_IMODE(current.st_mode) != 0o600
            or current.st_nlink != 1
            or (current.st_dev, current.st_ino) != (device, inode)
        ):
            raise OSError
        os.unlink(basename, dir_fd=directory_descriptor)
        os.fsync(directory_descriptor)
        try:
            remaining = os.stat(
                basename,
                dir_fd=directory_descriptor,
                follow_symlinks=False,
            )
        except FileNotFoundError:
            return
        if (remaining.st_dev, remaining.st_ino) == (device, inode):
            raise OSError
    except OSError:
        raise M5CurrentExitFailedV1("m5_current_receipt_cleanup_failed") from None


def _remove_failed_m5_current_receipt_while_locked_v1(
    completion_lock: M5CompletionLockV1,
    service_transition_lock: M5CompletionLockV1,
    directory_descriptor: int,
    receipt_descriptor: int,
    *,
    directory_identity: tuple[int, int],
    receipt_identity: tuple[int, int],
) -> None:
    """Invalidate a failed receipt before releasing either original guard."""

    if (
        completion_lock.guard_descriptor < 0
        or service_transition_lock.guard_descriptor < 0
    ):
        raise M5CurrentExitFailedV1("m5_current_receipt_cleanup_failed")
    _remove_failed_m5_current_receipt_v1(
        directory_descriptor,
        receipt_descriptor,
        basename=RECEIPT_BASENAME,
        directory_device=directory_identity[0],
        directory_inode=directory_identity[1],
        device=receipt_identity[0],
        inode=receipt_identity[1],
    )


def _write_private_receipt_at_v1(
    path: Path,
    receipt: Mapping[str, object],
    *,
    directory_descriptor: int,
    directory_device: int,
    directory_inode: int,
    retain_descriptor: bool,
) -> tuple[tuple[int, int], int]:
    """Create one owner-only result relative to a previously trusted directory."""

    payload = (json.dumps(receipt, indent=2, sort_keys=False) + "\n").encode("utf-8")
    descriptor = -1
    created_identity: tuple[int, int] | None = None
    try:
        _validate_receipt_directory_descriptor_v1(
            path,
            directory_descriptor,
            device=directory_device,
            inode=directory_inode,
        )
        descriptor = os.open(
            path.name,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
            0o600,
            dir_fd=directory_descriptor,
        )
        metadata = os.fstat(descriptor)
        created_identity = (metadata.st_dev, metadata.st_ino)
        _validate_created_receipt_inode_at_v1(
            directory_descriptor,
            path.name,
            descriptor,
            device=created_identity[0],
            inode=created_identity[1],
        )
        position = 0
        while position < len(payload):
            written = os.write(descriptor, payload[position : position + 65_536])
            if written <= 0:
                raise OSError
            position += written
        os.fsync(descriptor)
        _validate_created_receipt_inode_at_v1(
            directory_descriptor,
            path.name,
            descriptor,
            device=created_identity[0],
            inode=created_identity[1],
        )
        os.fsync(directory_descriptor)
        _validate_receipt_directory_descriptor_v1(
            path,
            directory_descriptor,
            device=directory_device,
            inode=directory_inode,
        )
        _validate_created_receipt_inode_at_v1(
            directory_descriptor,
            path.name,
            descriptor,
            device=created_identity[0],
            inode=created_identity[1],
        )
        result_descriptor = descriptor if retain_descriptor else -1
        if not retain_descriptor:
            os.close(descriptor)
        descriptor = -1
        return created_identity, result_descriptor
    except OSError:
        if created_identity is not None and descriptor >= 0:
            invalidated = _invalidate_created_receipt_inode_v1(
                directory_descriptor,
                path.name,
                descriptor,
                device=created_identity[0],
                inode=created_identity[1],
            )
            if not invalidated:
                raise M5CurrentExitFailedV1(
                    "m5_current_receipt_cleanup_failed"
                ) from None
        raise M5CurrentExitFailedV1("m5_current_receipt_write_failed") from None
    except BaseException as error:
        if created_identity is not None and descriptor >= 0:
            invalidated = _invalidate_created_receipt_inode_v1(
                directory_descriptor,
                path.name,
                descriptor,
                device=created_identity[0],
                inode=created_identity[1],
            )
            if not invalidated:
                raise M5CurrentExitFailedV1(
                    "m5_current_receipt_cleanup_failed"
                ) from error
        raise
    finally:
        if descriptor >= 0:
            try:
                os.close(descriptor)
            except OSError:
                pass


def write_private_receipt_v1(
    path: Path, receipt: Mapping[str, object]
) -> tuple[int, int]:
    """Create one owner-only result without following or replacing a path."""

    _validate_receipt_target_v1(path)
    directory_descriptor = -1
    try:
        directory_descriptor = os.open(
            path.parent,
            os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW,
        )
        directory = os.fstat(directory_descriptor)
        created_identity, retained_descriptor = _write_private_receipt_at_v1(
            path,
            receipt,
            directory_descriptor=directory_descriptor,
            directory_device=directory.st_dev,
            directory_inode=directory.st_ino,
            retain_descriptor=False,
        )
        assert retained_descriptor == -1
        return created_identity
    except OSError:
        raise M5CurrentExitFailedV1("m5_current_receipt_write_failed") from None
    finally:
        if directory_descriptor >= 0:
            try:
                os.close(directory_descriptor)
            except OSError:
                pass


def _raise_after_created_m5_receipt_failure_v1(
    error: BaseException,
    *,
    directory_descriptor: int,
    basename: str,
    receipt_descriptor: int,
    receipt_identity: tuple[int, int],
) -> NoReturn:
    """Invalidate the exact post-write receipt, then preserve the primary error."""

    invalidated = _invalidate_created_receipt_inode_v1(
        directory_descriptor,
        basename,
        receipt_descriptor,
        device=receipt_identity[0],
        inode=receipt_identity[1],
    )
    try:
        os.close(receipt_descriptor)
    except OSError:
        pass
    if not invalidated:
        raise M5CurrentExitFailedV1("m5_current_receipt_cleanup_failed") from error
    raise error


def write_verified_receipt_v1(
    candidate: M5ServiceCandidateV1,
    restarted: SystemdServiceObservationV1,
    path: Path,
    receipt: Mapping[str, object],
    *,
    directory_descriptor: int,
    directory_device: int,
    directory_inode: int,
) -> CreatedM5ReceiptV1:
    """Create the receipt only while systemd owns the restarted generation."""

    validate_receipt_systemd_ownership_v1(
        candidate,
        restarted_main_pid=restarted.main_pid,
        restarted_start_time_ticks=restarted.main_pid_start_time_ticks,
        observation=observe_selected_systemd_service_v1(candidate),
    )
    created_identity, receipt_descriptor = _write_private_receipt_at_v1(
        path,
        receipt,
        directory_descriptor=directory_descriptor,
        directory_device=directory_device,
        directory_inode=directory_inode,
        retain_descriptor=True,
    )
    try:
        validate_receipt_systemd_ownership_v1(
            candidate,
            restarted_main_pid=restarted.main_pid,
            restarted_start_time_ticks=restarted.main_pid_start_time_ticks,
            observation=observe_selected_systemd_service_v1(candidate),
        )
    except BaseException as error:
        _raise_after_created_m5_receipt_failure_v1(
            error,
            directory_descriptor=directory_descriptor,
            basename=path.name,
            receipt_descriptor=receipt_descriptor,
            receipt_identity=created_identity,
        )
    return CreatedM5ReceiptV1(
        descriptor=receipt_descriptor,
        device=created_identity[0],
        inode=created_identity[1],
    )


def _revalidate_runtime_binding_v1(
    candidate: M5ServiceCandidateV1,
    *,
    expected_revision: str,
    selected_pid: int,
    selected_start_time_ticks: int,
    dashboard_origin: str,
    dashboard_cdp_endpoint: str,
    checkout_root: Path = ROOT,
) -> None:
    """Reprove Git, systemd and authenticated Operations at an exit boundary."""

    try:
        if clean_detached_revision_v1(checkout_root) != expected_revision:
            raise M5ServiceActivationErrorV1("m5_service_checkout_changed")
        revalidate_current_systemd_binding_v1(
            candidate,
            selected_pid=selected_pid,
            selected_start_time_ticks=selected_start_time_ticks,
        )
        verify_current_service_revision_browser_v1(
            dashboard_origin=dashboard_origin,
            dashboard_cdp_endpoint=dashboard_cdp_endpoint,
            source_revision=expected_revision,
            checkout_root=checkout_root,
        )
        revalidate_current_systemd_binding_v1(
            candidate,
            selected_pid=selected_pid,
            selected_start_time_ticks=selected_start_time_ticks,
        )
    except (M5ServiceActivationErrorV1, M5ServiceActivationFailedV1):
        raise M5CurrentExitErrorV1("m5_current_service_selection_changed") from None


def _validate_live_selection(
    environment: Mapping[str, str], *, expected_revision: str
) -> SelectedServiceV1:
    if not all(environment.get(key) for key in LIVE_SELECTORS):
        raise M5CurrentExitErrorV1("m5_current_live_selectors_required")
    service_pid = environment["AGENTMONITOR_M5_SERVICE_PID"]
    if re.fullmatch(r"[1-9][0-9]{0,9}", service_pid) is None:
        raise M5CurrentExitErrorV1("m5_current_service_pid_required")
    try:
        owner_root = Path(environment["AGENTMONITOR_TEST_OWNER_DATA_ROOT"])
        test_root = Path(environment["AGENTMONITOR_TEST_DATA_ROOT"])
        root_info = owner_root.lstat()
        pid = int(service_pid)
        start_time_ticks = _process_start_ticks(pid)
        launch = _read_service_launch(
            pid, environment["AGENTMONITOR_TEST_DASHBOARD_ORIGIN"]
        )
        candidate, systemd_observation = select_current_systemd_binding_v1(
            source_revision=expected_revision,
            data_root=owner_root,
            selected_pid=pid,
            selected_start_time_ticks=start_time_ticks,
        )
        if (
            not owner_root.is_absolute()
            or owner_root.resolve(strict=True) != owner_root
            or test_root != owner_root
            or not stat.S_ISDIR(root_info.st_mode)
            or root_info.st_uid != os.getuid()
            or stat.S_IMODE(root_info.st_mode) != 0o700
            or launch.data_root != owner_root
            or _process_start_ticks(pid) != start_time_ticks
            or systemd_observation.main_pid != pid
            or systemd_observation.main_pid_start_time_ticks != start_time_ticks
        ):
            raise OSError
        _revalidate_runtime_binding_v1(
            candidate,
            expected_revision=expected_revision,
            selected_pid=pid,
            selected_start_time_ticks=start_time_ticks,
            dashboard_origin=environment["AGENTMONITOR_TEST_DASHBOARD_ORIGIN"],
            dashboard_cdp_endpoint=environment[
                "AGENTMONITOR_TEST_DASHBOARD_CDP_ENDPOINT"
            ],
        )
    except (
        M3CurrentExitErrorV1,
        M5ServiceActivationErrorV1,
        M5ServiceActivationFailedV1,
        OSError,
        RuntimeError,
    ):
        raise M5CurrentExitErrorV1("m5_current_service_selection_invalid") from None
    return SelectedServiceV1(
        pid,
        start_time_ticks,
        launch,
        candidate,
        systemd_observation,
    )


def _run_command(
    command: tuple[str, ...] | list[str],
    environment: Mapping[str, str],
    *,
    timeout: int,
    blocked_reason: str,
    failed_reason: str,
    capture: bool = False,
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        command,
        cwd=ROOT,
        env=environment,
        capture_output=capture,
        text=True,
        check=False,
        timeout=timeout,
    )
    if capture:
        if result.stdout:
            print(result.stdout.rstrip(), flush=True)
        if result.stderr:
            print(result.stderr.rstrip(), file=sys.stderr, flush=True)
    if result.returncode == 3:
        raise M5CurrentExitErrorV1(blocked_reason)
    if result.returncode != 0:
        raise M5CurrentExitFailedV1(failed_reason)
    return result


def _run_routine(routine: str, environment: Mapping[str, str]) -> None:
    child_environment = _routine_environment_v1(routine, environment)
    _run_command(
        [sys.executable, "tools/automation/run.py", routine],
        child_environment,
        timeout=3600,
        blocked_reason=f"m5_current_{routine.lower()}_blocked",
        failed_reason=f"m5_current_{routine.lower()}_failed",
    )


def _routine_environment_v1(
    routine: str, environment: Mapping[str, str]
) -> dict[str, str]:
    """Scope the detached-checkout exception to the M5 Git preflight child."""

    child_environment = dict(environment)
    child_environment.pop("AGENTMONITOR_M5_DETACHED_GIT_PREFLIGHT", None)
    if routine == "AUTO-GIT-PREFLIGHT":
        child_environment["AGENTMONITOR_M5_DETACHED_GIT_PREFLIGHT"] = "1"
    return child_environment


def _node_test_count_v1(output: str) -> int:
    """Require an executed Node test report with no skipped or deferred work."""

    expected = {"tests", "pass", "fail", "cancelled", "skipped", "todo"}
    summary: dict[str, int] = {}
    for line in output.splitlines():
        match = re.fullmatch(
            r"# (tests|pass|fail|cancelled|skipped|todo) ([0-9]+)", line.strip()
        )
        if match is None:
            continue
        key, raw_value = match.groups()
        if key in summary:
            raise M5CurrentExitFailedV1("m5_current_browser_policy_report_invalid")
        summary[key] = int(raw_value)
    if set(summary) != expected or summary["tests"] < 1:
        raise M5CurrentExitFailedV1("m5_current_browser_policy_report_invalid")
    if summary["skipped"] or summary["todo"]:
        raise M5CurrentExitFailedV1("m5_current_browser_policy_skipped")
    if summary["fail"] or summary["cancelled"] or summary["pass"] != summary["tests"]:
        raise M5CurrentExitFailedV1("m5_current_browser_policy_report_invalid")
    return summary["tests"]


def _validate_node_test_inventory_v1(
    output: str,
    *,
    expected_count: int = STORY_NODE_TEST_COUNT,
    expected_digest: str = STORY_NODE_TEST_INVENTORY_SHA256,
) -> int:
    """Bind the passing TAP summary to every exact executed Node subtest."""

    test_count = _node_test_count_v1(output)
    names = tuple(
        line.strip().removeprefix("# Subtest: ")
        for line in output.splitlines()
        if line.strip().startswith("# Subtest: ")
    )
    if (
        type(expected_count) is not int
        or expected_count < 1
        or _SHA256.fullmatch(expected_digest) is None
        or test_count != expected_count
        or len(names) != test_count
        or len(set(names)) != len(names)
        or any(not name or len(name) > 512 or "\x00" in name for name in names)
        or _digest_values(sorted(names)) != expected_digest
    ):
        raise M5CurrentExitFailedV1("m5_current_browser_policy_inventory_invalid")
    return test_count


def _normalized_pytest_report_file_v1(value: object) -> str:
    if (
        type(value) is not str
        or not value
        or len(value) > 512
        or "\x00" in value
        or "\\" in value
        or value.startswith("/")
    ):
        raise ValueError
    if any(component in {".", ".."} for component in value.split("/")):
        raise ValueError
    normalized = posixpath.normpath(value)
    if (
        normalized.startswith("../")
        or normalized == ".."
        or not normalized.endswith(".py")
        or (
            not normalized.startswith(("backend/tests/", "tools/automation/"))
            and normalized != "tools/git/test_preflight.py"
        )
    ):
        raise ValueError
    return normalized


def _selected_pytest_report_file_v1(value: object) -> str:
    normalized = _normalized_pytest_report_file_v1(value)
    for selector in (*STORY_TEST_PATHS, *STORY_AUTOMATION_TEST_IDS):
        selected_path = selector.split("::", maxsplit=1)[0].rstrip("/")
        if selected_path.endswith(".py"):
            if normalized == selected_path:
                return normalized
        elif normalized.startswith(selected_path + "/"):
            return normalized
    raise ValueError


def _junit_nonnegative_count_v1(value: object) -> int:
    if type(value) is not str or re.fullmatch(r"(?:0|[1-9][0-9]{0,9})", value) is None:
        raise ValueError
    return int(value)


def _validate_pytest_report_inventory_v1(
    report: Path,
    *,
    expected_count: int = STORY_PYTEST_TEST_COUNT,
    expected_declared_count: int = STORY_PYTEST_DECLARED_TEST_COUNT,
    expected_digest: str = STORY_PYTEST_TEST_INVENTORY_SHA256,
) -> tuple[int, int]:
    """Require exact selected parents and parent-plus-subtest outcomes."""

    try:
        document = ET.parse(report).getroot()
        root_children = tuple(document)
        if (
            document.tag != "testsuites"
            or len(root_children) != 1
            or root_children[0].tag != "testsuite"
        ):
            raise ValueError
        suite = root_children[0]
        if tuple(document.iter("testsuite")) != (suite,):
            raise ValueError
        cases = tuple(suite.iter("testcase"))
        direct_cases = tuple(child for child in suite if child.tag == "testcase")
        if cases != direct_cases:
            raise ValueError
        declared_count = _junit_nonnegative_count_v1(suite.get("tests"))
        error_count = _junit_nonnegative_count_v1(suite.get("errors"))
        failure_count = _junit_nonnegative_count_v1(suite.get("failures"))
        skip_count = _junit_nonnegative_count_v1(suite.get("skipped"))
        failure_elements = tuple(
            element
            for result_tag in ("error", "failure")
            for element in document.iter(result_tag)
        )
        skipped_elements = tuple(document.iter("skipped"))
        identifiers = tuple(
            sorted(
                _selected_pytest_report_file_v1(case.get("file"))
                + "::"
                + cast(str, case.get("name"))
                for case in cases
                if (
                    type(case.get("name")) is str
                    and bool(case.get("name"))
                    and len(cast(str, case.get("name"))) <= 2_048
                    and "\x00" not in cast(str, case.get("name"))
                )
            )
        )
    except (OSError, TypeError, ValueError, ET.ParseError):
        raise M5CurrentExitFailedV1("m5_current_story_report_invalid") from None
    if (
        type(expected_count) is not int
        or expected_count < 1
        or type(expected_declared_count) is not int
        or expected_declared_count < expected_count
        or _SHA256.fullmatch(expected_digest) is None
        or len(identifiers) != len(cases)
        or declared_count < len(cases)
        or len(set(identifiers)) != len(identifiers)
        or len(cases) != expected_count
        or declared_count != expected_declared_count
        or _digest_values(identifiers) != expected_digest
        or error_count
        or failure_count
        or failure_elements
    ):
        raise M5CurrentExitFailedV1("m5_current_story_inventory_invalid")
    if skip_count or skipped_elements:
        raise M5CurrentExitFailedV1("m5_current_story_suite_skipped")
    return len(cases), skip_count


def _run_story_suite(environment: Mapping[str, str]) -> int:
    node_result = _run_command(
        ["node", "--experimental-strip-types", "--test", *STORY_NODE_TEST_PATHS],
        environment,
        timeout=60,
        blocked_reason="m5_current_browser_policy_blocked",
        failed_reason="m5_current_browser_policy_failed",
        capture=True,
    )
    node_test_count = _validate_node_test_inventory_v1(node_result.stdout)
    with tempfile.TemporaryDirectory(prefix="agentmonitor-m5-current-") as raw:
        report = Path(raw) / "results.xml"
        _run_command(
            [
                str(ROOT / "backend/.venv/bin/python"),
                "-m",
                "pytest",
                *STORY_TEST_PATHS,
                *STORY_AUTOMATION_TEST_IDS,
                *STORY_PYTEST_FLAGS,
                f"--junitxml={report}",
            ],
            environment,
            timeout=2400,
            blocked_reason="m5_current_story_suite_blocked",
            failed_reason="m5_current_story_suite_failed",
        )
        test_count, _ = _validate_pytest_report_inventory_v1(report)
        for scenario in STORY_BROWSER_SCENARIOS:
            _run_command(
                [
                    str(ROOT / "backend/.venv/bin/python"),
                    "frontend/tests/browser/p02/run_browser.py",
                    scenario,
                    "--no-build",
                ],
                environment,
                timeout=300,
                blocked_reason="m5_current_story_browser_blocked",
                failed_reason="m5_current_story_browser_failed",
            )
        return node_test_count + test_count + len(STORY_BROWSER_SCENARIOS)


def _run_codex_browser(
    environment: Mapping[str, str], *, preflight: bool
) -> dict[str, object]:
    child_environment = dict(environment)
    if preflight:
        child_environment["AGENTMONITOR_M5_PREFLIGHT_ONLY"] = "1"
        child_environment.pop("AGENTMONITOR_M5_SERVICE_STARTED_AT", None)
    else:
        child_environment.pop("AGENTMONITOR_M5_PREFLIGHT_ONLY", None)
    result = _run_command(
        ["node", "tools/ui/verify_m5_codex.mjs"],
        child_environment,
        timeout=450 if preflight else 900,
        blocked_reason=(
            "m5_current_codex_preflight_blocked"
            if preflight
            else "m5_current_codex_browser_blocked"
        ),
        failed_reason=(
            "m5_current_codex_preflight_failed"
            if preflight
            else "m5_current_codex_browser_failed"
        ),
        capture=True,
    )
    expected_event = "m5_codex_preflight" if preflight else "m5_codex_witness"
    witnesses: list[dict[str, object]] = []
    for line in result.stdout.splitlines():
        try:
            candidate = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(candidate, dict) and candidate.get("event") == expected_event:
            witnesses.append(candidate)
    if len(witnesses) != 1:
        raise M5CurrentExitFailedV1("m5_current_codex_receipt_missing")
    return witnesses[0]


def _valid_digest(value: object) -> bool:
    return type(value) is str and _SHA256.fullmatch(value) is not None


def _validate_witness_v1(
    witness: Mapping[str, object],
    *,
    event: str,
    require_fresh: bool,
    expected_revision: str,
) -> None:
    verified = witness.get("verified_count")
    unavailable = witness.get("owner_unavailable_count")
    account_count = witness.get("account_count")
    current_history_count = witness.get("current_history_count")
    fresh_after_restart_count = witness.get("fresh_after_restart_count")
    process_count = witness.get("process_count")
    mutations = witness.get("mutations")
    if (
        set(witness) != _MAIN_BROWSER_WITNESS_KEYS
        or witness.get("event") != event
        or witness.get("service_revision") != expected_revision
        or _REVISION.fullmatch(expected_revision) is None
        or type(account_count) is not int
        or account_count != 4
        or type(verified) is not int
        or type(unavailable) is not int
        or verified < 1
        or unavailable < 0
        or verified + unavailable != 4
        or type(current_history_count) is not int
        or current_history_count != verified
        or type(fresh_after_restart_count) is not int
        or fresh_after_restart_count != (verified if require_fresh else 0)
        or type(process_count) is not int
        or not 5 <= process_count <= 6
        or type(witness.get("process_scan_truncated")) is not bool
        or type(mutations) is not int
        or mutations != 0
        or witness.get("provider_version") != CODEX_PROVIDER_VERSION
        or witness.get("adapter_version") != CODEX_ADAPTER_VERSION
        or witness.get("parser_version") != CODEX_PARSER_VERSION
        or witness.get("schema_bundle_digest") != CODEX_SCHEMA_BUNDLE_DIGEST
        or witness.get("mapping_id") != CODEX_MAPPING_ID
        or witness.get("mapping_digest") != CODEX_MAPPING_DIGEST
        or witness.get("provider_health") != "healthy"
        or not all(
            _valid_digest(witness.get(key))
            for key in (
                "fleet_metadata_digest",
                "identity_set_digest",
                "collection_run_set_digest",
                "quota_value_set_digest",
                "history_value_set_digest",
                "process_set_digest",
                "registry_digest",
            )
        )
    ):
        raise M5CurrentExitFailedV1(
            "m5_current_codex_witness_invalid"
            if require_fresh
            else "m5_current_codex_preflight_invalid"
        )


def validate_codex_transition_v1(
    preflight: Mapping[str, object],
    witness: Mapping[str, object],
    *,
    expected_revision: str,
) -> tuple[str, str, str, str, str, int, int, int, bool]:
    """Validate stable selection plus fresh genuine Codex post-restart lineage."""

    _validate_witness_v1(
        preflight,
        event="m5_codex_preflight",
        require_fresh=False,
        expected_revision=expected_revision,
    )
    _validate_witness_v1(
        witness,
        event="m5_codex_witness",
        require_fresh=True,
        expected_revision=expected_revision,
    )
    if witness.get("fleet_metadata_digest") != preflight.get("fleet_metadata_digest"):
        raise M5CurrentExitErrorV1("m5_current_fleet_metadata_changed")
    if witness.get("identity_set_digest") != preflight.get("identity_set_digest"):
        raise M5CurrentExitErrorV1("m5_current_fleet_identity_changed")
    if witness.get("quota_value_set_digest") != preflight.get("quota_value_set_digest"):
        raise M5CurrentExitErrorV1("m5_current_authoritative_quota_changed")
    if witness.get("registry_digest") != preflight.get("registry_digest"):
        raise M5CurrentExitErrorV1("m5_current_registry_changed")
    if witness.get("collection_run_set_digest") == preflight.get(
        "collection_run_set_digest"
    ):
        raise M5CurrentExitErrorV1("m5_current_collection_not_fresh")
    if witness.get("history_value_set_digest") == preflight.get(
        "history_value_set_digest"
    ):
        raise M5CurrentExitErrorV1("m5_current_history_not_fresh")
    return (
        str(witness["fleet_metadata_digest"]),
        str(witness["identity_set_digest"]),
        str(witness["collection_run_set_digest"]),
        str(witness["process_set_digest"]),
        str(witness["registry_digest"]),
        cast(int, witness["verified_count"]),
        cast(int, witness["owner_unavailable_count"]),
        cast(int, witness["process_count"]),
        cast(bool, witness["process_scan_truncated"]),
    )


def _validate_authoritative_quota_preflight_v1(
    quota: ValidatedQuotaWitnessV1, preflight: Mapping[str, object]
) -> None:
    if (
        preflight.get("verified_count") != quota.account_count
        or preflight.get("identity_set_digest") != quota.identity_set_digest
        or preflight.get("collection_run_set_digest") != quota.collection_run_set_digest
        or preflight.get("quota_value_set_digest") != quota.quota_value_set_digest
        or preflight.get("history_value_set_digest") != quota.history_value_set_digest
    ):
        raise M5CurrentExitErrorV1("m5_current_authoritative_quota_mismatch")


def validate_authoritative_quota_v1(
    quota: ValidatedQuotaWitnessV1,
    preflight: Mapping[str, object],
    witness: Mapping[str, object],
) -> None:
    """Bind owner-observed provider values to both browser gate phases."""

    _validate_authoritative_quota_preflight_v1(quota, preflight)
    if (
        witness.get("verified_count") != quota.account_count
        or witness.get("identity_set_digest") != quota.identity_set_digest
        or witness.get("quota_value_set_digest") != quota.quota_value_set_digest
    ):
        raise M5CurrentExitErrorV1("m5_current_authoritative_quota_changed")


def _read_current_quota_witness_v1(
    path: Path,
    *,
    expected_revision: str,
    service_pid: int,
    service_start_time_ticks: int,
    owner_outcomes_digest: str,
    verified_account_count: int,
    now: datetime,
) -> ValidatedQuotaWitnessV1:
    """Reread quota evidence against the receipt completion time."""

    return read_quota_witness_v1(
        path,
        expected_revision=expected_revision,
        service_pid=service_pid,
        service_start_time_ticks=service_start_time_ticks,
        owner_outcomes_digest=owner_outcomes_digest,
        verified_account_count=verified_account_count,
        now=now,
    )


def main() -> int:
    service: SystemdServiceObservationV1 | None = None
    completion_lock: M5CompletionLockV1 | None = None
    service_transition_lock: M5CompletionLockV1 | None = None
    result_code: int | None = None
    result_message: str | None = None
    cleanup_errors: list[M5CurrentExitFailedV1] = []
    created_receipt: CreatedM5ReceiptV1 | None = None
    receipt_cleanup_descriptor = -1
    receipt_directory_identity: tuple[int, int] | None = None
    retained_completion_guard_descriptor = -1
    retained_transition_guard_descriptor = -1
    pending_base_exception: BaseException | None = None
    try:
        missing = _missing_story_artifacts_v1(ROOT, STORY_ARTIFACTS)
        if missing:
            raise M5CurrentExitFailedV1("m5_current_story_artifact_missing")
        environment = os.environ.copy()
        environment["PYTHONPATH"] = str(ROOT / "backend/src")
        revision = _clean_m5_revision_v1()
        service_transition_lock = _acquire_m5_current_service_transition_lock_v1()
        _validate_m5_current_service_transition_lock_v1(service_transition_lock)
        selected_service = _validate_live_selection(
            environment, expected_revision=revision
        )
        owner_root = selected_service.launch.data_root
        candidate = selected_service.candidate
        selected_systemd_service = selected_service.systemd_observation
        if candidate is None or selected_systemd_service is None:
            raise M5CurrentExitFailedV1("m5_current_service_selection_invalid")
        completion_lock = _acquire_m5_current_completion_lock_v1(RECEIPT_PATH)
        _validate_receipt_target_v1(RECEIPT_PATH)
        activation_receipt = _validate_activation_receipt_for_exit_v1(
            candidate,
            selected_systemd_service,
        )
        outcomes_path = owner_root / OWNER_OUTCOMES_BASENAME
        quota_path = owner_root / QUOTA_WITNESS_BASENAME
        alert_path = owner_root / ALERT_WITNESS_BASENAME
        outcomes = read_owner_outcomes_v1(
            outcomes_path,
            expected_revision=revision,
            selected_service=selected_service,
            now=datetime.now(UTC),
        )
        primary_account = outcomes.primary_verified_account_id
        if primary_account is None:
            raise M5CurrentExitErrorV1("m5_current_verified_account_required")
        quota = read_quota_witness_v1(
            quota_path,
            expected_revision=revision,
            service_pid=selected_service.pid,
            service_start_time_ticks=selected_service.start_time_ticks,
            owner_outcomes_digest=outcomes.digest,
            verified_account_count=outcomes.verified_count,
            now=datetime.now(UTC),
        )
        alert = read_alert_witness_v1(
            alert_path,
            expected_revision=revision,
            selected_service=selected_service,
            verified_account_ids=outcomes.verified_account_ids,
            now=datetime.now(UTC),
        )
        environment["AGENTMONITOR_TEST_M5_OWNER_OUTCOMES"] = str(outcomes_path)
        environment["AGENTMONITOR_TEST_M5_QUOTA_WITNESS"] = str(quota_path)
        environment["AGENTMONITOR_TEST_M5_ALERT_WITNESS"] = str(alert_path)
        environment["AGENTMONITOR_M5_OWNER_IMPLEMENTATION_REVISION"] = revision
        environment["AGENTMONITOR_M5_OWNER_SERVICE_PID"] = str(selected_service.pid)
        environment["AGENTMONITOR_M5_OWNER_SERVICE_START_TIME_TICKS"] = str(
            selected_service.start_time_ticks
        )
        environment["AGENTMONITOR_TEST_CODEX_ACCOUNT_ID"] = primary_account
        environment["AGENTMONITOR_TEST_CODEX_MANAGED_ACCOUNT_ID"] = primary_account
        started_at = datetime.now(UTC)
        admission = verify_codex_admission_v1()
        if (
            admission.provider_version != CODEX_PROVIDER_VERSION
            or admission.schema_bundle_digest != CODEX_SCHEMA_BUNDLE_DIGEST
            or admission.mapping_digest != CODEX_MAPPING_DIGEST
            or admission.schema_count != 4
            or admission.experimental_schema_mode
            or admission.default_profile_access_count != 0
            or admission.default_profile_write_count != 0
        ):
            raise M5CurrentExitFailedV1("m5_current_codex_admission_invalid")
        registry_graph_before = registry_graph_digest_for_root_v1(owner_root)
        if registry_graph_before != quota.registry_graph_digest:
            raise M5CurrentExitErrorV1("m5_current_registry_graph_changed")
        backend_source = ROOT / "backend/src"
        if str(backend_source) not in sys.path:
            sys.path.insert(0, str(backend_source))
        from agentmonitor.composition.codex_managed_connection import (
            managed_codex_root_v1,
        )
        from agentmonitor.contracts.common_v1 import OpaqueIdV1

        managed_profile_root = managed_codex_root_v1(
            owner_root, OpaqueIdV1(primary_account)
        )
        containment = verify_codex_managed_profile_containment_v1(
            owner_data_root=owner_root,
            account_id=primary_account,
            managed_profiles_root=owner_root / "profiles" / "codex",
            managed_profile_root=managed_profile_root,
            revision=revision,
            service_pid=selected_service.pid,
            service_start_time_ticks=selected_service.start_time_ticks,
        )
        if (
            _SHA256.fullmatch(containment.evidence_digest) is None
            or type(containment.provider_access_count) is not int
            or containment.provider_access_count < 1
            or type(containment.provider_write_count) is not int
            or containment.provider_write_count < 0
            or type(containment.default_profile_access_count) is not int
            or containment.default_profile_access_count != 0
            or type(containment.default_profile_write_count) is not int
            or containment.default_profile_write_count != 0
        ):
            raise M5CurrentExitFailedV1("m5_current_codex_containment_invalid")
        registry_graph_after_containment = registry_graph_digest_for_root_v1(owner_root)
        if registry_graph_after_containment != registry_graph_before:
            raise M5CurrentExitErrorV1("m5_current_registry_graph_changed")
        preflight = _run_codex_browser(environment, preflight=True)
        _validate_witness_v1(
            preflight,
            event="m5_codex_preflight",
            require_fresh=False,
            expected_revision=revision,
        )
        _validate_authoritative_quota_preflight_v1(quota, preflight)
        if preflight.get("registry_digest") != alert.registry_digest:
            raise M5CurrentExitErrorV1("m5_current_alert_registry_state_changed")
        lane_evidence: dict[str, str] = {
            "service_activation": "rollback_drill_receipt_validated",
            "owner_outcomes": "four_owner_outcomes_validated",
            "alert_prerequisite": "codex_alert_receipt_validated",
            "exact_codex_admission": "codex_schema_mapping_no_default_access",
            "authenticated_containment": "codex_identity_quota_trace_confined",
            "authoritative_quota_reconciliation": (
                f"codex_windows_{quota.window_count}_owner_reconciled"
            ),
        }
        for lane, routine in PRE_SERVICE_ROUTINES:
            _run_routine(routine, environment)
            lane_evidence[lane] = f"{routine.lower()}_passed"
        lane_evidence["generated_client"] = "auto_build_generated_client_passed"
        _revalidate_runtime_binding_v1(
            candidate,
            expected_revision=revision,
            selected_pid=selected_service.pid,
            selected_start_time_ticks=selected_service.start_time_ticks,
            dashboard_origin=environment["AGENTMONITOR_TEST_DASHBOARD_ORIGIN"],
            dashboard_cdp_endpoint=environment[
                "AGENTMONITOR_TEST_DASHBOARD_CDP_ENDPOINT"
            ],
        )
        _validate_m5_current_service_transition_lock_v1(service_transition_lock)
        try:
            service = restart_selected_systemd_service_v1(
                candidate,
                selected_systemd_service,
            )
        except (M5ServiceActivationErrorV1, M5ServiceActivationFailedV1) as error:
            raise _translated_systemd_service_error_v1(
                error, pre_restart=True
            ) from error
        service_started_at = datetime.now(UTC)
        environment["AGENTMONITOR_M5_SERVICE_STARTED_AT"] = (
            service_started_at.isoformat(timespec="milliseconds").replace("+00:00", "Z")
        )
        lane_evidence["revision_bound_service"] = "service_restarted_from_clean_head"
        witness = _run_codex_browser(environment, preflight=False)
        (
            fleet_digest,
            identity_digest,
            collection_digest,
            process_digest,
            _registry_digest,
            verified_count,
            unavailable_count,
            process_count,
            process_scan_truncated,
        ) = validate_codex_transition_v1(preflight, witness, expected_revision=revision)
        validate_authoritative_quota_v1(quota, preflight, witness)
        for routine in DEPENDENCY_ROUTINES:
            _run_routine(routine, environment)
        test_count = _run_story_suite(environment)
        lane_evidence["technical_suite"] = (
            f"auto_m3_test_and_pytest_{test_count}_passed_zero_skips"
        )
        lane_evidence["sqlite"] = "real_file_sqlite_suite_passed"
        lane_evidence.update(
            codex_browser="codex_api_ui_history_passed",
            process_witness=(
                f"codex_processes_{process_count}_verified_"
                + ("partial_scan" if process_scan_truncated else "complete_scan")
            ),
            fresh_quota_lineage=f"codex_accounts_{verified_count}_fresh_history",
            alert_lifecycle=f"codex_alert_{alert.owner_action}_recovered",
            registry_unchanged="pre_post_registry_digest_matched",
            provider_health="codex_health_and_isolation_passed",
            overview_browser="codex_overview_rendered_read_only",
        )
        for lane, script in BROWSER_CHECKS:
            _run_command(
                ["node", script],
                environment,
                timeout=900,
                blocked_reason=f"m5_current_{lane}_blocked",
                failed_reason=f"m5_current_{lane}_failed",
            )
            lane_evidence[lane] = f"{lane}_passed"
        for lane, routine in LOCAL_ROUTINES:
            _run_routine(routine, environment)
            lane_evidence[lane] = f"{routine.lower()}_passed"
        _revalidate_runtime_binding_v1(
            candidate,
            expected_revision=revision,
            selected_pid=service.main_pid,
            selected_start_time_ticks=service.main_pid_start_time_ticks,
            dashboard_origin=environment["AGENTMONITOR_TEST_DASHBOARD_ORIGIN"],
            dashboard_cdp_endpoint=environment[
                "AGENTMONITOR_TEST_DASHBOARD_CDP_ENDPOINT"
            ],
        )
        final_outcomes = read_owner_outcomes_v1(
            outcomes_path,
            expected_revision=revision,
            selected_service=selected_service,
            now=datetime.now(UTC),
        )
        if final_outcomes.digest != outcomes.digest:
            raise M5CurrentExitErrorV1("m5_current_owner_outcomes_changed")
        final_alert = read_alert_witness_v1(
            alert_path,
            expected_revision=revision,
            selected_service=selected_service,
            verified_account_ids=outcomes.verified_account_ids,
            now=datetime.now(UTC),
        )
        if final_alert.digest != alert.digest:
            raise M5CurrentExitErrorV1("m5_current_alert_witness_changed")
        registry_graph_after = registry_graph_digest_for_root_v1(owner_root)
        if registry_graph_after != registry_graph_before:
            raise M5CurrentExitErrorV1("m5_current_registry_graph_changed")
        completed_at = datetime.now(UTC)
        final_quota = _read_current_quota_witness_v1(
            quota_path,
            expected_revision=revision,
            service_pid=selected_service.pid,
            service_start_time_ticks=selected_service.start_time_ticks,
            owner_outcomes_digest=outcomes.digest,
            verified_account_count=outcomes.verified_count,
            now=completed_at,
        )
        if final_quota.digest != quota.digest:
            raise M5CurrentExitErrorV1("m5_current_quota_witness_changed")
        receipt = build_passed_receipt_v1(
            implementation_revision=revision,
            started_at=started_at,
            completed_at=completed_at,
            activation_receipt_digest=activation_receipt.digest,
            owner_outcomes_digest=outcomes.digest,
            alert_witness_digest=alert.digest,
            quota_witness_digest=quota.digest,
            quota_value_set_digest=quota.quota_value_set_digest,
            quota_history_value_set_digest=quota.history_value_set_digest,
            post_restart_history_value_set_digest=str(
                witness["history_value_set_digest"]
            ),
            owner_observation_digest=quota.owner_observation_digest,
            registry_graph_digest=quota.registry_graph_digest,
            containment_evidence_digest=containment.evidence_digest,
            containment_provider_access_count=containment.provider_access_count,
            containment_provider_write_count=containment.provider_write_count,
            containment_default_profile_access_count=(
                containment.default_profile_access_count
            ),
            containment_default_profile_write_count=(
                containment.default_profile_write_count
            ),
            quota_window_count=quota.window_count,
            fleet_metadata_digest=fleet_digest,
            identity_set_digest=identity_digest,
            collection_run_set_digest=collection_digest,
            process_set_digest=process_digest,
            verified_count=verified_count,
            owner_unavailable_count=unavailable_count,
            process_count=process_count,
            process_scan_truncated=process_scan_truncated,
            test_count=test_count,
            lane_evidence=lane_evidence,
        )
        _revalidate_runtime_binding_v1(
            candidate,
            expected_revision=revision,
            selected_pid=service.main_pid,
            selected_start_time_ticks=service.main_pid_start_time_ticks,
            dashboard_origin=environment["AGENTMONITOR_TEST_DASHBOARD_ORIGIN"],
            dashboard_cdp_endpoint=environment[
                "AGENTMONITOR_TEST_DASHBOARD_CDP_ENDPOINT"
            ],
        )
        _validate_m5_current_service_transition_lock_v1(service_transition_lock)
        final_activation_receipt = _validate_activation_receipt_for_exit_v1(candidate)
        if final_activation_receipt.digest != activation_receipt.digest:
            raise M5CurrentExitErrorV1("m5_current_activation_receipt_changed")
        _validate_m5_current_completion_lock_v1(completion_lock)
        _validate_receipt_target_v1(RECEIPT_PATH)
        try:
            receipt_cleanup_descriptor = os.dup(completion_lock.directory_descriptor)
            os.set_inheritable(receipt_cleanup_descriptor, False)
            receipt_directory_identity = (
                completion_lock.directory_device,
                completion_lock.directory_inode,
            )
            (
                retained_completion_guard_descriptor,
                retained_transition_guard_descriptor,
            ) = _duplicate_m5_current_guard_descriptors_v1(
                completion_lock,
                service_transition_lock,
            )
            created_receipt = write_verified_receipt_v1(
                candidate,
                service,
                RECEIPT_PATH,
                receipt,
                directory_descriptor=receipt_cleanup_descriptor,
                directory_device=completion_lock.directory_device,
                directory_inode=completion_lock.directory_inode,
            )
        except (M5ServiceActivationErrorV1, M5ServiceActivationFailedV1) as error:
            raise _translated_systemd_service_error_v1(
                error, pre_restart=False
            ) from error
        _validate_m5_current_final_custody_v1(
            completion_lock,
            service_transition_lock,
            directory_descriptor=receipt_cleanup_descriptor,
            created_receipt=created_receipt,
        )
    except M5CurrentExitFailedV1 as error:
        result_code = 1
        result_message = f"M5 CURRENT EXIT: FAILED — {error}"
    except (
        M5CurrentExitErrorV1,
        M5CodexQuotaWitnessErrorV1,
        M5CodexAdmissionUnavailableV1,
        M5CodexContainmentUnavailableV1,
        M3CurrentExitErrorV1,
    ) as error:
        result_code = 3
        result_message = f"M5 CURRENT EXIT: BLOCKED — {error}"
    except (
        M5CodexAdmissionErrorV1,
        M5CodexContainmentErrorV1,
        OSError,
        subprocess.TimeoutExpired,
        ValueError,
    ):
        result_code = 1
        result_message = "M5 CURRENT EXIT: FAILED — execution_unavailable"
    except BaseException as error:
        pending_base_exception = error

    receipt_removed = False
    pre_release_cleanup_required = _m5_current_receipt_cleanup_required_v1(
        receipt_created=created_receipt is not None,
        receipt_removed=receipt_removed,
        result_code=result_code,
        pending_base_exception=pending_base_exception,
        cleanup_errors=(),
    )
    if pre_release_cleanup_required:
        try:
            assert created_receipt is not None
            assert completion_lock is not None
            assert service_transition_lock is not None
            if receipt_cleanup_descriptor < 0 or receipt_directory_identity is None:
                raise M5CurrentExitFailedV1("m5_current_receipt_cleanup_failed")
            _remove_failed_m5_current_receipt_while_locked_v1(
                completion_lock,
                service_transition_lock,
                receipt_cleanup_descriptor,
                created_receipt.descriptor,
                directory_identity=receipt_directory_identity,
                receipt_identity=(created_receipt.device, created_receipt.inode),
            )
            receipt_removed = True
        except M5CurrentExitFailedV1 as error:
            cleanup_errors.append(error)
        except BaseException as error:
            if pending_base_exception is None:
                pending_base_exception = error

    try:
        if completion_lock is not None:
            release_m5_completion_lock_v1(completion_lock)
    except OSError:
        cleanup_errors.append(
            M5CurrentExitFailedV1("m5_current_completion_lock_release_failed")
        )
    except BaseException as error:
        if pending_base_exception is None:
            pending_base_exception = error
    try:
        if service_transition_lock is not None:
            transition_release_error = _release_m5_current_service_transition_lock_v1(
                service_transition_lock
            )
            if transition_release_error is not None:
                cleanup_errors.append(transition_release_error)
    except BaseException as error:
        if pending_base_exception is None:
            pending_base_exception = error

    post_release_cleanup_required = _m5_current_receipt_cleanup_required_v1(
        receipt_created=created_receipt is not None,
        receipt_removed=receipt_removed,
        result_code=result_code,
        pending_base_exception=pending_base_exception,
        cleanup_errors=tuple(cleanup_errors),
    )
    try:
        if post_release_cleanup_required:
            assert created_receipt is not None
            if receipt_cleanup_descriptor < 0 or receipt_directory_identity is None:
                raise M5CurrentExitFailedV1("m5_current_receipt_cleanup_failed")
            _remove_failed_m5_current_receipt_v1(
                receipt_cleanup_descriptor,
                created_receipt.descriptor,
                basename=RECEIPT_BASENAME,
                directory_device=receipt_directory_identity[0],
                directory_inode=receipt_directory_identity[1],
                device=created_receipt.device,
                inode=created_receipt.inode,
            )
            receipt_removed = True
    except M5CurrentExitFailedV1 as error:
        cleanup_errors.append(error)
    except BaseException as error:
        if pending_base_exception is None:
            pending_base_exception = error
    finally:
        if created_receipt is not None:
            try:
                os.close(created_receipt.descriptor)
            except OSError:
                pass
        if receipt_cleanup_descriptor >= 0:
            try:
                os.close(receipt_cleanup_descriptor)
            except OSError:
                pass
        for descriptor in (
            retained_completion_guard_descriptor,
            retained_transition_guard_descriptor,
        ):
            if descriptor >= 0:
                try:
                    os.close(descriptor)
                except OSError:
                    pass
    if pending_base_exception is not None:
        raise pending_base_exception
    result_code, result_message = _select_m5_current_result_v1(
        result_code,
        result_message,
        tuple(cleanup_errors),
    )
    if result_code is not None:
        assert result_message is not None
        print(result_message)
        return result_code
    print(
        "M5 CURRENT EXIT: PASSED — exact Codex admission, four account outcomes, "
        "fresh quota history, representative processes, recovered alert, built browser "
        "and local gates"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
