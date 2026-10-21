"""Owner-assisted authoritative Codex quota reconciliation for V1-M5.

The pure policy in this module compares safe whole-percent and reset facts.  The
operational command is completed below the policy and never invokes Codex: the
owner reads the official ``/status`` view and enters only those safe facts.
"""

# This operator command inserts the checkout's backend source path before imports.
# ruff: noqa: E402

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import subprocess
import sys
from collections.abc import Mapping
from dataclasses import dataclass, is_dataclass
from dataclasses import fields as dataclass_fields
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import cast
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "backend/src"))

from agentmonitor.adapters.persistence._shared.sqlite.core.policy import DatabaseRefV1
from agentmonitor.adapters.persistence.registry.sqlite.repository import (
    SqliteRegistryRepositoryV1,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.registry_v1 import (
    AccountViewV1,
    OrganizationViewV1,
    ProviderInstallationViewV1,
)
from agentmonitor.modules.registry.application.accounts import ListAccountsV1
from agentmonitor.modules.registry.application.discovery import (
    ListProviderInstallationsV1,
)
from agentmonitor.modules.registry.application.organizations import ListOrganizationsV1

from tools.automation.implementations.auto_m3_current_exit import (
    ServiceLaunchV1,
    _process_start_ticks,
    _read_service_launch,
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
    clean_detached_revision_v1,
    revalidate_current_systemd_binding_v1,
    select_current_systemd_binding_v1,
    verify_current_service_revision_browser_v1,
)

_OPAQUE = re.compile(r"[A-Za-z0-9_.:@/-]{1,128}\Z")
_UTC_TIMESTAMP = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z\Z")
_RESET_PRECISIONS = frozenset({"exact", "rounded", "range", "estimated"})
_DISPLAY_PRECISIONS = frozenset({"second", "minute", "hour", "day"})
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
QUOTA_WITNESS_BASENAME = "m5-quota-witness.json"
QUOTA_WITNESS_SCHEMA = "agentmonitor.m5-quota-witness.v1"
BROWSER_PROOF_SCHEMA = "agentmonitor.m5-quota-browser-proof.v1"
CODEX_PROVIDER_VERSION = "0.160.0"
CODEX_RATE_LIMITS_SOURCE_ID = "codex.app-server.account-rate-limits-read.v2"
OWNER_OBSERVATION_INSTRUCTION = (
    "Open the official Codex /status view for each account below. "
    "Enter only the displayed whole percentages and reset times; "
    "do not paste output."
)
MAX_REGISTRY_PAGE_COUNT = 10_000


class M5CodexQuotaWitnessErrorV1(ValueError):
    """One bounded quota-witness error without private observation values."""


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
    """Recheck Git, systemd and Operations immediately before witness creation."""

    try:
        if clean_detached_revision_v1(checkout_root) != expected_revision:
            raise M5ServiceActivationErrorV1("m5_service_checkout_not_clean")
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
        raise M5CodexQuotaWitnessErrorV1("m5_quota_witness_context_changed") from None


def _select_runtime_binding_v1(
    environment: Mapping[str, str], *, checkout_root: Path = ROOT
) -> tuple[Path, str, str, int, int, ServiceLaunchV1, str, M5ServiceCandidateV1]:
    """Bind one clean detached checkout to its exact systemd-owned service."""

    try:
        revision = clean_detached_revision_v1(checkout_root)
    except (M5ServiceActivationErrorV1, M5ServiceActivationFailedV1):
        raise M5CodexQuotaWitnessErrorV1("m5_quota_witness_checkout_invalid") from None
    try:
        owner_root = Path(environment["AGENTMONITOR_TEST_OWNER_DATA_ROOT"])
        endpoint = environment["AGENTMONITOR_TEST_DASHBOARD_CDP_ENDPOINT"]
        origin = environment["AGENTMONITOR_TEST_DASHBOARD_ORIGIN"]
        service_pid = int(environment["AGENTMONITOR_M5_SERVICE_PID"])
        service_ticks = _process_start_ticks(service_pid)
        launch = _read_service_launch(service_pid, origin)
        candidate, _observation = select_current_systemd_binding_v1(
            source_revision=revision,
            data_root=owner_root,
            selected_pid=service_pid,
            selected_start_time_ticks=service_ticks,
            checkout_root=checkout_root,
        )
        _revalidate_runtime_binding_v1(
            candidate,
            expected_revision=revision,
            selected_pid=service_pid,
            selected_start_time_ticks=service_ticks,
            dashboard_origin=origin,
            dashboard_cdp_endpoint=endpoint,
            checkout_root=checkout_root,
        )
    except (
        KeyError,
        TypeError,
        ValueError,
        M5ServiceActivationFailedV1,
    ):
        raise M5CodexQuotaWitnessErrorV1(
            "m5_quota_witness_selection_required"
        ) from None
    return (
        owner_root,
        endpoint,
        origin,
        service_pid,
        service_ticks,
        launch,
        revision,
        candidate,
    )


@dataclass(frozen=True, slots=True)
class QuotaReconciliationV1:
    """Sanitized result of an exact owner/provider comparison."""

    account_count: int
    window_count: int
    value_set_digest: str
    collection_run_set_digest: str
    owner_observation_digest: str


@dataclass(frozen=True, slots=True)
class ValidatedQuotaWitnessV1:
    """Sanitized prerequisite facts accepted by the M5 exit gate."""

    digest: str
    account_count: int
    window_count: int
    identity_set_digest: str
    collection_run_set_digest: str
    quota_value_set_digest: str
    history_value_set_digest: str
    owner_observation_digest: str
    registry_graph_digest: str


@dataclass(frozen=True, slots=True)
class _AgentQuotaWindowV1:
    semantic_role: str
    remaining_percent: int
    reset_at: datetime | None
    collected_at: datetime


@dataclass(frozen=True, slots=True)
class _OwnerQuotaWindowV1:
    semantic_role: str
    remaining_percent: int
    reset_at: datetime | None
    display_precision: str
    observed_at: datetime


def _digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value, ensure_ascii=True, separators=(",", ":"), sort_keys=True
        ).encode("ascii")
    ).hexdigest()


def _timestamp(value: object) -> datetime:
    if type(value) is not str or _UTC_TIMESTAMP.fullmatch(value) is None:
        raise M5CodexQuotaWitnessErrorV1("m5_quota_witness_input_invalid")
    parsed = datetime.fromisoformat(value)
    if parsed.utcoffset() != timedelta(0):
        raise M5CodexQuotaWitnessErrorV1("m5_quota_witness_input_invalid")
    return parsed.astimezone(UTC)


def parse_quota_witness_document_v1(
    document: object,
    *,
    expected_revision: str,
    service_pid: int,
    service_start_time_ticks: int,
    owner_outcomes_digest: str,
    verified_account_count: int,
    now: datetime,
) -> ValidatedQuotaWitnessV1:
    """Validate a private witness as a pure closed-document policy."""

    expected_keys = {
        "schema",
        "implementation_revision",
        "service_source_revision",
        "service_pid",
        "service_start_time_ticks",
        "recorded_at",
        "owner_confirmation",
        "provider_key",
        "provider_version",
        "source_id",
        "account_count",
        "window_count",
        "owner_outcomes_digest",
        "identity_set_digest",
        "collection_run_set_digest",
        "quota_value_set_digest",
        "owner_observation_digest",
        "rendered_value_set_digest",
        "history_value_set_digest",
        "browser_proof_digest",
        "registry_graph_digest_before",
        "registry_graph_digest_after",
        "browser_registry_digest_before",
        "browser_registry_digest_after",
    }
    try:
        if type(document) is not dict or set(document) != expected_keys:
            raise ValueError
        recorded_at = _timestamp(document["recorded_at"])
        digest_keys = tuple(key for key in expected_keys if key.endswith("_digest")) + (
            "registry_graph_digest_before",
            "registry_graph_digest_after",
            "browser_registry_digest_before",
            "browser_registry_digest_after",
        )
        if (
            document["schema"] != QUOTA_WITNESS_SCHEMA
            or document["implementation_revision"] != expected_revision
            or document["service_source_revision"] != expected_revision
            or re.fullmatch(r"[0-9a-f]{40}", expected_revision) is None
            or type(document["service_pid"]) is not int
            or document["service_pid"] != service_pid
            or type(document["service_start_time_ticks"]) is not int
            or document["service_start_time_ticks"] != service_start_time_ticks
            or document["owner_confirmation"] != "interactive_terminal"
            or document["provider_key"] != "codex"
            or document["provider_version"] != CODEX_PROVIDER_VERSION
            or document["source_id"] != CODEX_RATE_LIMITS_SOURCE_ID
            or type(document["account_count"]) is not int
            or document["account_count"] != verified_account_count
            or type(document["window_count"]) is not int
            or document["window_count"] < verified_account_count
            or document["owner_outcomes_digest"] != owner_outcomes_digest
            or any(
                type(document[key]) is not str
                or _SHA256.fullmatch(document[key]) is None
                for key in digest_keys
            )
            or document["quota_value_set_digest"]
            != document["rendered_value_set_digest"]
            or document["registry_graph_digest_before"]
            != document["registry_graph_digest_after"]
            or document["browser_registry_digest_before"]
            != document["browser_registry_digest_after"]
            or recorded_at > now + timedelta(minutes=1)
            or now - recorded_at > timedelta(minutes=15)
        ):
            raise ValueError
        canonical = json.dumps(
            document, ensure_ascii=True, separators=(",", ":"), sort_keys=True
        ).encode("ascii")
        return ValidatedQuotaWitnessV1(
            digest=hashlib.sha256(canonical).hexdigest(),
            account_count=document["account_count"],
            window_count=document["window_count"],
            identity_set_digest=document["identity_set_digest"],
            collection_run_set_digest=document["collection_run_set_digest"],
            quota_value_set_digest=document["quota_value_set_digest"],
            history_value_set_digest=document["history_value_set_digest"],
            owner_observation_digest=document["owner_observation_digest"],
            registry_graph_digest=document["registry_graph_digest_after"],
        )
    except (KeyError, TypeError, ValueError, M5CodexQuotaWitnessErrorV1):
        raise M5CodexQuotaWitnessErrorV1("m5_quota_witness_invalid") from None


def read_quota_witness_v1(
    path: Path,
    *,
    expected_revision: str,
    service_pid: int,
    service_start_time_ticks: int,
    owner_outcomes_digest: str,
    verified_account_count: int,
    now: datetime,
) -> ValidatedQuotaWitnessV1:
    """Safely read one create-once private quota witness for the exit gate."""

    descriptor = -1
    parent_descriptor = -1
    try:
        if not path.is_absolute() or path.name != QUOTA_WITNESS_BASENAME:
            raise OSError
        parent_descriptor = os.open(
            path.parent,
            os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
        )
        parent_metadata = os.fstat(parent_descriptor)
        parent_identity = (parent_metadata.st_dev, parent_metadata.st_ino)
        _validate_private_parent_v1(
            path,
            parent_descriptor,
            device=parent_identity[0],
            inode=parent_identity[1],
        )
        descriptor = os.open(
            path.name,
            os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC,
            dir_fd=parent_descriptor,
        )
        metadata = os.fstat(descriptor)
        file_identity = (metadata.st_dev, metadata.st_ino)
        _validate_created_witness_v1(
            path,
            descriptor,
            parent_descriptor,
            device=file_identity[0],
            inode=file_identity[1],
        )
        if not 2 <= metadata.st_size <= 16_384:
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
        if (
            len(payload) != metadata.st_size
            or final_metadata.st_size != metadata.st_size
        ):
            raise OSError
        _validate_created_witness_v1(
            path,
            descriptor,
            parent_descriptor,
            device=file_identity[0],
            inode=file_identity[1],
        )
        _validate_private_parent_v1(
            path,
            parent_descriptor,
            device=parent_identity[0],
            inode=parent_identity[1],
        )
        document = json.loads(payload.decode("utf-8"))
    except (
        OSError,
        RuntimeError,
        UnicodeError,
        TypeError,
        ValueError,
        json.JSONDecodeError,
    ):
        raise M5CodexQuotaWitnessErrorV1("m5_quota_witness_invalid") from None
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        if parent_descriptor >= 0:
            os.close(parent_descriptor)
    parsed = parse_quota_witness_document_v1(
        document,
        expected_revision=expected_revision,
        service_pid=service_pid,
        service_start_time_ticks=service_start_time_ticks,
        owner_outcomes_digest=owner_outcomes_digest,
        verified_account_count=verified_account_count,
        now=now,
    )
    return ValidatedQuotaWitnessV1(
        digest=hashlib.sha256(payload).hexdigest(),
        account_count=parsed.account_count,
        window_count=parsed.window_count,
        identity_set_digest=parsed.identity_set_digest,
        collection_run_set_digest=parsed.collection_run_set_digest,
        quota_value_set_digest=parsed.quota_value_set_digest,
        history_value_set_digest=parsed.history_value_set_digest,
        owner_observation_digest=parsed.owner_observation_digest,
        registry_graph_digest=parsed.registry_graph_digest,
    )


def _token(value: object) -> str:
    if type(value) is not str or _OPAQUE.fullmatch(value) is None:
        raise M5CodexQuotaWitnessErrorV1("m5_quota_witness_input_invalid")
    return value


def _percent(value: object) -> int:
    if type(value) is not int or not 0 <= value <= 100:
        raise M5CodexQuotaWitnessErrorV1("m5_quota_witness_input_invalid")
    return value


def _reset_bucket(value: datetime, precision: str) -> str:
    if precision == "second":
        return value.replace(microsecond=0).isoformat().replace("+00:00", "Z")
    if precision == "minute":
        return value.replace(second=0, microsecond=0).isoformat().replace("+00:00", "Z")
    if precision == "hour":
        return (
            value.replace(minute=0, second=0, microsecond=0)
            .isoformat()
            .replace("+00:00", "Z")
        )
    if precision == "day":
        return value.date().isoformat()
    raise M5CodexQuotaWitnessErrorV1("m5_quota_witness_input_invalid")


def _agent_records(
    records: object,
) -> tuple[list[list[object]], dict[tuple[str, str], _AgentQuotaWindowV1]]:
    if type(records) is not list or not records:
        raise M5CodexQuotaWitnessErrorV1("m5_quota_witness_input_invalid")
    canonical: list[list[object]] = []
    indexed: dict[tuple[str, str], _AgentQuotaWindowV1] = {}
    account_ids: set[str] = set()
    for record in records:
        if type(record) is not dict or set(record) != {
            "account_id",
            "collection_run_id",
            "collected_at",
            "windows",
        }:
            raise M5CodexQuotaWitnessErrorV1("m5_quota_witness_input_invalid")
        account_id = _token(record["account_id"])
        _token(record["collection_run_id"])
        collected_at = _timestamp(record["collected_at"])
        windows = record["windows"]
        if account_id in account_ids or type(windows) is not list or not windows:
            raise M5CodexQuotaWitnessErrorV1("m5_quota_witness_input_invalid")
        account_ids.add(account_id)
        for window in windows:
            if type(window) is not dict or set(window) != {
                "window_key",
                "semantic_role",
                "remaining_percent",
                "reset_at",
                "reset_precision",
            }:
                raise M5CodexQuotaWitnessErrorV1("m5_quota_witness_input_invalid")
            window_key = _token(window["window_key"])
            semantic_role = _token(window["semantic_role"])
            remaining_percent = _percent(window["remaining_percent"])
            reset = window["reset_at"]
            reset_precision = window["reset_precision"]
            if reset is None:
                if reset_precision != "unknown":
                    raise M5CodexQuotaWitnessErrorV1("m5_quota_witness_input_invalid")
                reset_at = None
            else:
                if reset_precision not in _RESET_PRECISIONS:
                    raise M5CodexQuotaWitnessErrorV1("m5_quota_witness_input_invalid")
                reset_at = _timestamp(reset)
            key = (account_id, window_key)
            if key in indexed:
                raise M5CodexQuotaWitnessErrorV1("m5_quota_witness_input_invalid")
            indexed[key] = _AgentQuotaWindowV1(
                semantic_role=semantic_role,
                remaining_percent=remaining_percent,
                reset_at=reset_at,
                collected_at=collected_at,
            )
            canonical.append(
                [
                    account_id,
                    window_key,
                    semantic_role,
                    remaining_percent,
                    int(reset_at.timestamp()) if reset_at is not None else None,
                    reset_precision,
                ]
            )
    return sorted(canonical), indexed


def _owner_records(
    records: object,
) -> tuple[list[list[object]], dict[tuple[str, str], _OwnerQuotaWindowV1]]:
    if type(records) is not list or not records:
        raise M5CodexQuotaWitnessErrorV1("m5_quota_witness_input_invalid")
    canonical: list[list[object]] = []
    indexed: dict[tuple[str, str], _OwnerQuotaWindowV1] = {}
    account_ids: set[str] = set()
    for record in records:
        if type(record) is not dict or set(record) != {
            "account_id",
            "observed_at",
            "windows",
        }:
            raise M5CodexQuotaWitnessErrorV1("m5_quota_witness_input_invalid")
        account_id = _token(record["account_id"])
        observed_at = _timestamp(record["observed_at"])
        windows = record["windows"]
        if account_id in account_ids or type(windows) is not list or not windows:
            raise M5CodexQuotaWitnessErrorV1("m5_quota_witness_input_invalid")
        account_ids.add(account_id)
        for window in windows:
            if type(window) is not dict or set(window) != {
                "window_key",
                "semantic_role",
                "remaining_percent",
                "reset_at",
                "reset_display_precision",
            }:
                raise M5CodexQuotaWitnessErrorV1("m5_quota_witness_input_invalid")
            window_key = _token(window["window_key"])
            semantic_role = _token(window["semantic_role"])
            remaining_percent = _percent(window["remaining_percent"])
            reset = window["reset_at"]
            display_precision = window["reset_display_precision"]
            if reset is None:
                if display_precision != "none":
                    raise M5CodexQuotaWitnessErrorV1("m5_quota_witness_input_invalid")
                reset_at = None
            else:
                if display_precision not in _DISPLAY_PRECISIONS:
                    raise M5CodexQuotaWitnessErrorV1("m5_quota_witness_input_invalid")
                reset_at = _timestamp(reset)
            key = (account_id, window_key)
            if key in indexed:
                raise M5CodexQuotaWitnessErrorV1("m5_quota_witness_input_invalid")
            indexed[key] = _OwnerQuotaWindowV1(
                semantic_role=semantic_role,
                remaining_percent=remaining_percent,
                reset_at=reset_at,
                display_precision=display_precision,
                observed_at=observed_at,
            )
            canonical.append(
                [
                    account_id,
                    window_key,
                    semantic_role,
                    remaining_percent,
                    int(reset_at.timestamp()) if reset_at is not None else None,
                    display_precision,
                    observed_at.isoformat().replace("+00:00", "Z"),
                ]
            )
    return sorted(canonical), indexed


def reconcile_quota_observations_v1(
    agentmonitor_records: object,
    owner_records: object,
    *,
    maximum_skew_seconds: int = 300,
) -> QuotaReconciliationV1:
    """Compare the provider view with AgentMonitor at its displayed precision."""

    if type(maximum_skew_seconds) is not int or maximum_skew_seconds != 300:
        raise M5CodexQuotaWitnessErrorV1("m5_quota_witness_input_invalid")
    agent_values, agent = _agent_records(agentmonitor_records)
    owner_values, owner = _owner_records(owner_records)
    if set(agent) != set(owner):
        raise M5CodexQuotaWitnessErrorV1("m5_quota_witness_reconciliation_mismatch")
    for key, agent_window in agent.items():
        owner_window = owner[key]
        reset_matches = agent_window.reset_at is None and owner_window.reset_at is None
        if agent_window.reset_at is not None and owner_window.reset_at is not None:
            reset_matches = _reset_bucket(
                agent_window.reset_at, owner_window.display_precision
            ) == _reset_bucket(owner_window.reset_at, owner_window.display_precision)
        if (
            owner_window.semantic_role != agent_window.semantic_role
            or owner_window.remaining_percent != agent_window.remaining_percent
            or not reset_matches
            or abs(
                (owner_window.observed_at - agent_window.collected_at).total_seconds()
            )
            > maximum_skew_seconds
        ):
            raise M5CodexQuotaWitnessErrorV1("m5_quota_witness_reconciliation_mismatch")
    account_count = len({key[0] for key in agent})
    run_material = sorted(
        [record["account_id"], record["collection_run_id"]]
        for record in cast(list[dict[str, object]], agentmonitor_records)
    )
    return QuotaReconciliationV1(
        account_count=account_count,
        window_count=len(agent),
        value_set_digest=_digest(agent_values),
        collection_run_set_digest=_digest(run_material),
        owner_observation_digest=_digest(owner_values),
    )


def _safe_contract_value(value: object) -> object:
    """Normalize only published registry view values; private refs cannot serialize."""

    if isinstance(value, OpaqueIdV1):
        return value.value
    if isinstance(value, datetime):
        return value.astimezone(UTC).isoformat().replace("+00:00", "Z")
    if is_dataclass(value) and not isinstance(value, type):
        return {
            field.name: _safe_contract_value(getattr(value, field.name))
            for field in dataclass_fields(value)
        }
    if isinstance(value, tuple):
        return [_safe_contract_value(item) for item in value]
    if isinstance(value, list):
        return [_safe_contract_value(item) for item in value]
    if isinstance(value, Mapping):
        return {
            str(key): _safe_contract_value(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    if value is None or type(value) in {str, int, bool}:
        return value
    raise M5CodexQuotaWitnessErrorV1("m5_quota_witness_registry_invalid")


def registry_graph_digest_v1(
    reference: DatabaseRefV1,
    *,
    max_page_count: int = MAX_REGISTRY_PAGE_COUNT,
) -> str:
    """Hash the complete published registry graph at one stable revision."""

    if type(max_page_count) is not int or not 1 <= max_page_count <= (
        MAX_REGISTRY_PAGE_COUNT
    ):
        raise M5CodexQuotaWitnessErrorV1("m5_quota_witness_registry_incomplete")
    repository = SqliteRegistryRepositoryV1(reference)
    before = repository.get_registry_scope_snapshot("global", None)
    if before.completeness_state != "complete":
        raise M5CodexQuotaWitnessErrorV1("m5_quota_witness_registry_incomplete")
    as_of = datetime.now(UTC)

    organization_query = ListOrganizationsV1(repository)
    organizations: list[OrganizationViewV1] = []
    organization_after: str | None = None
    organization_cursors: set[str] = set()
    for _page_count in range(max_page_count):
        organization_page = organization_query.page(
            as_of=as_of, limit=200, after_key=organization_after
        )
        if organization_page.availability.state != "available":
            raise M5CodexQuotaWitnessErrorV1("m5_quota_witness_registry_incomplete")
        organizations.extend(organization_page.items)
        if not organization_page.has_more:
            break
        next_key = organization_page.next_key
        if (
            next_key is None
            or next_key == organization_after
            or next_key in organization_cursors
        ):
            raise M5CodexQuotaWitnessErrorV1("m5_quota_witness_registry_incomplete")
        organization_cursors.add(next_key)
        organization_after = next_key
    else:
        raise M5CodexQuotaWitnessErrorV1("m5_quota_witness_registry_incomplete")

    account_query = ListAccountsV1(repository)
    accounts: list[AccountViewV1] = []
    account_after: str | None = None
    account_cursors: set[str] = set()
    for _page_count in range(max_page_count):
        account_page = account_query.page(
            None, as_of=as_of, limit=200, after_key=account_after
        )
        if account_page.availability.state != "available":
            raise M5CodexQuotaWitnessErrorV1("m5_quota_witness_registry_incomplete")
        accounts.extend(account_page.items)
        if not account_page.has_more:
            break
        next_key = account_page.next_key
        if next_key is None or next_key == account_after or next_key in account_cursors:
            raise M5CodexQuotaWitnessErrorV1("m5_quota_witness_registry_incomplete")
        account_cursors.add(next_key)
        account_after = next_key
    else:
        raise M5CodexQuotaWitnessErrorV1("m5_quota_witness_registry_incomplete")

    installation_query = ListProviderInstallationsV1(repository)
    installations: list[ProviderInstallationViewV1] = []
    installation_after: str | None = None
    installation_cursors: set[str] = set()
    for _page_count in range(max_page_count):
        installation_page = installation_query.page(
            None, as_of=as_of, limit=200, after_key=installation_after
        )
        if installation_page.availability.state != "available":
            raise M5CodexQuotaWitnessErrorV1("m5_quota_witness_registry_incomplete")
        installations.extend(installation_page.items)
        if not installation_page.has_more:
            break
        next_key = installation_page.next_key
        if (
            next_key is None
            or next_key == installation_after
            or next_key in installation_cursors
        ):
            raise M5CodexQuotaWitnessErrorV1("m5_quota_witness_registry_incomplete")
        installation_cursors.add(next_key)
        installation_after = next_key
    else:
        raise M5CodexQuotaWitnessErrorV1("m5_quota_witness_registry_incomplete")

    graphs = []
    for account in accounts:
        graphs.append(
            {
                "account": account,
                "profiles": repository.list_monitoring_profiles(account.account_id),
                "resources": repository.list_account_resources(account.account_id),
            }
        )
    after = repository.get_registry_scope_snapshot("global", None)
    if before != after:
        raise M5CodexQuotaWitnessErrorV1("m5_quota_witness_registry_changed")
    return _digest(
        _safe_contract_value(
            {
                "scope": after,
                "organizations": tuple(organizations),
                "graphs": tuple(graphs),
                "installations": tuple(installations),
            }
        )
    )


def registry_graph_digest_for_root_v1(data_root: Path) -> str:
    """Hash the public Registry graph in one selected real owner data root."""

    return registry_graph_digest_v1(
        DatabaseRefV1(data_root / "agentmonitor.db", data_root)
    )


def _browser_proof(
    *,
    endpoint: str,
    origin: str,
    outcomes_path: Path,
    revision: str,
    service_pid: int,
    service_start_time_ticks: int,
) -> dict[str, object]:
    environment = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "AGENTMONITOR_TEST_DASHBOARD_CDP_ENDPOINT": endpoint,
        "AGENTMONITOR_TEST_DASHBOARD_ORIGIN": origin,
        "AGENTMONITOR_TEST_M5_OWNER_OUTCOMES": str(outcomes_path),
        "AGENTMONITOR_M5_IMPLEMENTATION_REVISION": revision,
        "AGENTMONITOR_M5_SERVICE_PID": str(service_pid),
        "AGENTMONITOR_M5_SERVICE_START_TIME_TICKS": str(service_start_time_ticks),
    }
    try:
        result = subprocess.run(
            ["node", "tools/ui/verify_m5_codex_quota_reconciliation.mjs"],
            cwd=ROOT,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
            timeout=300,
        )
    except (OSError, subprocess.TimeoutExpired):
        raise M5CodexQuotaWitnessErrorV1(
            "m5_quota_witness_browser_unavailable"
        ) from None
    if result.returncode != 0:
        last = result.stderr.strip().splitlines()[-1:] or [""]
        if last[0].startswith("M5 CODEX QUOTA BROWSER: "):
            print(last[0], file=sys.stderr)
        raise M5CodexQuotaWitnessErrorV1("m5_quota_witness_browser_unavailable")
    documents: list[dict[str, object]] = []
    for line in result.stdout.splitlines():
        try:
            candidate = json.loads(line)
        except json.JSONDecodeError:
            continue
        if type(candidate) is dict and candidate.get("schema") == BROWSER_PROOF_SCHEMA:
            documents.append(candidate)
    if len(documents) != 1:
        raise M5CodexQuotaWitnessErrorV1("m5_quota_witness_browser_proof_missing")
    return documents[0]


def _validated_browser_records(
    proof: object,
    *,
    revision: str,
    service_pid: int,
    service_start_time_ticks: int,
    verified_account_ids: frozenset[str],
    now: datetime,
) -> tuple[list[dict[str, object]], dict[str, str | int]]:
    expected = {
        "schema",
        "implementation_revision",
        "service_source_revision",
        "service_pid",
        "service_start_time_ticks",
        "captured_at",
        "account_count",
        "window_count",
        "provider_version",
        "source_id",
        "identity_set_digest",
        "collection_run_set_digest",
        "quota_value_set_digest",
        "rendered_value_set_digest",
        "history_value_set_digest",
        "registry_digest_before",
        "registry_digest_after",
        "mutations",
        "records",
    }
    try:
        if type(proof) is not dict or set(proof) != expected:
            raise ValueError
        captured_at = _timestamp(proof["captured_at"])
        digest_keys = (
            "identity_set_digest",
            "collection_run_set_digest",
            "quota_value_set_digest",
            "rendered_value_set_digest",
            "history_value_set_digest",
            "registry_digest_before",
            "registry_digest_after",
        )
        if (
            proof["schema"] != BROWSER_PROOF_SCHEMA
            or proof["implementation_revision"] != revision
            or proof["service_source_revision"] != revision
            or type(proof["service_pid"]) is not int
            or proof["service_pid"] != service_pid
            or type(proof["service_start_time_ticks"]) is not int
            or proof["service_start_time_ticks"] != service_start_time_ticks
            or proof["provider_version"] != CODEX_PROVIDER_VERSION
            or proof["source_id"] != CODEX_RATE_LIMITS_SOURCE_ID
            or type(proof["mutations"]) is not int
            or proof["mutations"] != 0
            or proof["registry_digest_before"] != proof["registry_digest_after"]
            or any(
                type(proof[key]) is not str or _SHA256.fullmatch(proof[key]) is None
                for key in digest_keys
            )
            or captured_at > now + timedelta(minutes=1)
            or now - captured_at > timedelta(minutes=5)
            or type(proof["records"]) is not list
            or type(proof["account_count"]) is not int
            or proof["account_count"] != len(verified_account_ids)
            or proof["account_count"] != len(proof["records"])
            or type(proof["window_count"]) is not int
            or proof["window_count"] < proof["account_count"]
        ):
            raise ValueError
        records: list[dict[str, object]] = []
        account_ids: set[str] = set()
        total_windows = 0
        for record in proof["records"]:
            if type(record) is not dict or set(record) != {
                "account_id",
                "alias",
                "collection_run_id",
                "collected_at",
                "windows",
            }:
                raise ValueError
            account_id = _token(record["account_id"])
            if account_id not in verified_account_ids:
                raise ValueError
            _token(record["collection_run_id"])
            _timestamp(record["collected_at"])
            alias = record["alias"]
            if (
                type(alias) is not str
                or alias != alias.strip()
                or not 1 <= len(alias) <= 128
                or not alias.isprintable()
                or type(record["windows"]) is not list
                or not record["windows"]
            ):
                raise ValueError
            windows = []
            for window in record["windows"]:
                if type(window) is not dict or set(window) != {
                    "window_key",
                    "semantic_role",
                    "remaining_percent",
                    "reset_at",
                    "reset_precision",
                    "current_observation_id",
                }:
                    raise ValueError
                _token(window["current_observation_id"])
                windows.append(dict(window))
            total_windows += len(windows)
            account_ids.add(account_id)
            records.append(
                {
                    "account_id": account_id,
                    "alias": alias,
                    "collection_run_id": record["collection_run_id"],
                    "collected_at": record["collected_at"],
                    "windows": windows,
                }
            )
        if (
            account_ids != set(verified_account_ids)
            or total_windows != proof["window_count"]
        ):
            raise ValueError
        policy_records = [
            {
                "account_id": record["account_id"],
                "collection_run_id": record["collection_run_id"],
                "collected_at": record["collected_at"],
                "windows": [
                    {
                        key: value
                        for key, value in window.items()
                        if key != "current_observation_id"
                    }
                    for window in cast(list[dict[str, object]], record["windows"])
                ],
            }
            for record in records
        ]
        agent_values, _ = _agent_records(policy_records)
        history_values = sorted(
            (
                [
                    record["account_id"],
                    window["window_key"],
                    window["semantic_role"],
                    window["remaining_percent"],
                    (
                        int(_timestamp(window["reset_at"]).timestamp())
                        if window["reset_at"] is not None
                        else None
                    ),
                    window["reset_precision"],
                    window["current_observation_id"],
                ]
                for record in records
                for window in cast(list[dict[str, object]], record["windows"])
            ),
            key=lambda row: json.dumps(row, ensure_ascii=True, separators=(",", ":")),
        )
        if (
            _digest(agent_values) != proof["quota_value_set_digest"]
            or proof["quota_value_set_digest"] != proof["rendered_value_set_digest"]
            or _digest(history_values) != proof["history_value_set_digest"]
        ):
            raise ValueError
        owner_records = [
            {
                "account_id": record["account_id"],
                "alias": record["alias"],
                "collection_run_id": record["collection_run_id"],
                "collected_at": record["collected_at"],
                "windows": policy_record["windows"],
            }
            for record, policy_record in zip(records, policy_records, strict=True)
        ]
        sanitized: dict[str, str | int] = {
            key: cast(str, proof[key]) for key in digest_keys
        }
        sanitized["window_count"] = proof["window_count"]
        return owner_records, sanitized
    except (KeyError, TypeError, ValueError, M5CodexQuotaWitnessErrorV1):
        raise M5CodexQuotaWitnessErrorV1(
            "m5_quota_witness_browser_proof_invalid"
        ) from None


def _owner_observations(
    records: list[dict[str, object]],
) -> list[dict[str, object]]:
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        raise M5CodexQuotaWitnessErrorV1("m5_quota_witness_interactive_owner_required")
    print(OWNER_OBSERVATION_INSTRUCTION)
    observations: list[dict[str, object]] = []
    for record in records:
        print(f"\nAccount: {record['alias']}")
        owner_windows = []
        windows = record["windows"]
        assert isinstance(windows, list)
        for window in windows:
            assert isinstance(window, dict)
            window_key = str(window["window_key"])
            role = str(window["semantic_role"])
            print(f"  Window: {window_key} ({role})")
            raw_percent = input("  Whole percentage left (0-100): ").strip()
            if re.fullmatch(r"(?:0|[1-9][0-9]?|100)", raw_percent) is None:
                raise M5CodexQuotaWitnessErrorV1("m5_quota_witness_owner_input_invalid")
            reset_value = input(
                "  Reset as UTC RFC3339 (for example 2026-10-07T14:30:00Z), or 'none': "
            ).strip()
            if reset_value == "none":
                reset_at = None
                display_precision = "none"
            else:
                _timestamp(reset_value)
                display_precision = input(
                    "  Display precision (second/minute/hour/day): "
                ).strip()
                if display_precision not in _DISPLAY_PRECISIONS:
                    raise M5CodexQuotaWitnessErrorV1(
                        "m5_quota_witness_owner_input_invalid"
                    )
                reset_at = reset_value
            owner_windows.append(
                {
                    "window_key": window_key,
                    "semantic_role": role,
                    "remaining_percent": int(raw_percent),
                    "reset_at": reset_at,
                    "reset_display_precision": display_precision,
                }
            )
        observations.append(
            {
                "account_id": record["account_id"],
                "observed_at": datetime.now(UTC)
                .isoformat(timespec="seconds")
                .replace("+00:00", "Z"),
                "windows": owner_windows,
            }
        )
    phrase = input("\nType I CONFIRM CODEX USAGE to countersign these observations: ")
    if phrase != "I CONFIRM CODEX USAGE":
        raise M5CodexQuotaWitnessErrorV1("m5_quota_witness_owner_confirmation_required")
    return observations


def _validate_private_parent_v1(
    path: Path,
    descriptor: int,
    *,
    device: int,
    inode: int,
) -> None:
    metadata = os.fstat(descriptor)
    path_metadata = path.parent.lstat()
    if (
        not path.is_absolute()
        or path.name != QUOTA_WITNESS_BASENAME
        or path.parent.resolve(strict=True) != path.parent
        or not stat.S_ISDIR(metadata.st_mode)
        or metadata.st_uid != os.getuid()
        or stat.S_IMODE(metadata.st_mode) != 0o700
        or (metadata.st_dev, metadata.st_ino) != (device, inode)
        or (path_metadata.st_dev, path_metadata.st_ino) != (device, inode)
    ):
        raise OSError


def _validate_created_witness_v1(
    path: Path,
    descriptor: int,
    parent_descriptor: int,
    *,
    device: int,
    inode: int,
) -> None:
    metadata = os.fstat(descriptor)
    path_metadata = os.stat(path.name, dir_fd=parent_descriptor, follow_symlinks=False)
    if (
        not stat.S_ISREG(metadata.st_mode)
        or metadata.st_uid != os.getuid()
        or stat.S_IMODE(metadata.st_mode) != 0o600
        or metadata.st_nlink != 1
        or (metadata.st_dev, metadata.st_ino) != (device, inode)
        or (path_metadata.st_dev, path_metadata.st_ino) != (device, inode)
    ):
        raise OSError


def _unlink_created_witness_v1(
    path: Path,
    parent_descriptor: int,
    *,
    device: int,
    inode: int,
) -> None:
    """Remove only the directory entry that still names our created inode."""

    try:
        current = os.stat(path.name, dir_fd=parent_descriptor, follow_symlinks=False)
        if (current.st_dev, current.st_ino) != (device, inode):
            return
        os.unlink(path.name, dir_fd=parent_descriptor)
        os.fsync(parent_descriptor)
    except OSError:
        pass


def _write_create_once(path: Path, document: dict[str, object]) -> str:
    payload = (
        json.dumps(document, ensure_ascii=True, indent=2, sort_keys=True) + "\n"
    ).encode("ascii")
    if len(payload) > 16_384:
        raise M5CodexQuotaWitnessErrorV1("m5_quota_witness_output_invalid")
    descriptor = -1
    parent_descriptor = -1
    created_identity: tuple[int, int] | None = None
    try:
        parent_descriptor = os.open(
            path.parent,
            os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
        )
        parent_metadata = os.fstat(parent_descriptor)
        parent_identity = (parent_metadata.st_dev, parent_metadata.st_ino)
        _validate_private_parent_v1(
            path,
            parent_descriptor,
            device=parent_identity[0],
            inode=parent_identity[1],
        )
        descriptor = os.open(
            path.name,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
            0o600,
            dir_fd=parent_descriptor,
        )
        metadata = os.fstat(descriptor)
        created_identity = (metadata.st_dev, metadata.st_ino)
        _validate_created_witness_v1(
            path,
            descriptor,
            parent_descriptor,
            device=created_identity[0],
            inode=created_identity[1],
        )
        position = 0
        while position < len(payload):
            written = os.write(descriptor, payload[position:])
            if written < 1:
                raise OSError
            position += written
        os.fsync(descriptor)
        _validate_created_witness_v1(
            path,
            descriptor,
            parent_descriptor,
            device=created_identity[0],
            inode=created_identity[1],
        )
        _validate_private_parent_v1(
            path,
            parent_descriptor,
            device=parent_identity[0],
            inode=parent_identity[1],
        )
        os.fsync(parent_descriptor)
        _validate_created_witness_v1(
            path,
            descriptor,
            parent_descriptor,
            device=created_identity[0],
            inode=created_identity[1],
        )
        _validate_private_parent_v1(
            path,
            parent_descriptor,
            device=parent_identity[0],
            inode=parent_identity[1],
        )
    except OSError:
        if created_identity is not None and parent_descriptor >= 0:
            _unlink_created_witness_v1(
                path,
                parent_descriptor,
                device=created_identity[0],
                inode=created_identity[1],
            )
        raise M5CodexQuotaWitnessErrorV1(
            "m5_quota_witness_create_once_failed"
        ) from None
    except BaseException:
        if created_identity is not None and parent_descriptor >= 0:
            _unlink_created_witness_v1(
                path,
                parent_descriptor,
                device=created_identity[0],
                inode=created_identity[1],
            )
        raise
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        if parent_descriptor >= 0:
            os.close(parent_descriptor)
    return hashlib.sha256(payload).hexdigest()


def create_quota_witness_v1(environment: Mapping[str, str]) -> str:
    """Collect an owner countersignature without performing a provider call."""

    (
        owner_root,
        endpoint,
        origin,
        service_pid,
        service_ticks,
        launch,
        revision,
        candidate,
    ) = _select_runtime_binding_v1(environment)
    try:
        owner_metadata = owner_root.lstat()
        if (
            not owner_root.is_absolute()
            or owner_root.resolve(strict=True) != owner_root
            or not stat.S_ISDIR(owner_metadata.st_mode)
            or owner_metadata.st_uid != os.getuid()
            or stat.S_IMODE(owner_metadata.st_mode) != 0o700
            or urlparse(endpoint).hostname != "127.0.0.1"
            or urlparse(origin).hostname != "127.0.0.1"
            or urlparse(origin).scheme != "http"
        ):
            raise ValueError
    except (KeyError, OSError, TypeError, ValueError):
        raise M5CodexQuotaWitnessErrorV1(
            "m5_quota_witness_selection_required"
        ) from None
    now = datetime.now(UTC)
    if launch.data_root != owner_root:
        raise M5CodexQuotaWitnessErrorV1("m5_quota_witness_service_mismatch")
    outcomes_path = owner_root / OWNER_OUTCOMES_BASENAME
    try:
        outcomes, outcomes_digest = read_owner_outcomes_file_v2(outcomes_path, now=now)
    except M5OwnerOutcomesErrorV1:
        raise M5CodexQuotaWitnessErrorV1(
            "m5_quota_witness_owner_outcomes_invalid"
        ) from None
    if (
        outcomes.implementation_revision != revision
        or outcomes.service_pid != service_pid
        or outcomes.service_start_time_ticks != service_ticks
        or not outcomes.verified_account_ids
    ):
        raise M5CodexQuotaWitnessErrorV1("m5_quota_witness_owner_outcomes_mismatch")
    reference = DatabaseRefV1(owner_root / "agentmonitor.db", owner_root)
    registry_before = registry_graph_digest_v1(reference)
    proof = _browser_proof(
        endpoint=endpoint,
        origin=origin,
        outcomes_path=outcomes_path,
        revision=revision,
        service_pid=service_pid,
        service_start_time_ticks=service_ticks,
    )
    records, browser = _validated_browser_records(
        proof,
        revision=revision,
        service_pid=service_pid,
        service_start_time_ticks=service_ticks,
        verified_account_ids=outcomes.verified_account_ids,
        now=datetime.now(UTC),
    )
    owner_observations = _owner_observations(records)
    policy_records = [
        {
            "account_id": record["account_id"],
            "collection_run_id": record["collection_run_id"],
            "collected_at": record["collected_at"],
            "windows": record["windows"],
        }
        for record in records
    ]
    reconciliation = reconcile_quota_observations_v1(policy_records, owner_observations)
    if (
        reconciliation.account_count != len(outcomes.verified_account_ids)
        or reconciliation.window_count != browser["window_count"]
        or reconciliation.value_set_digest != browser["quota_value_set_digest"]
        or reconciliation.collection_run_set_digest
        != browser["collection_run_set_digest"]
    ):
        raise M5CodexQuotaWitnessErrorV1("m5_quota_witness_reconciliation_mismatch")
    registry_after = registry_graph_digest_v1(reference)
    if (
        registry_before != registry_after
        or browser["registry_digest_before"] != browser["registry_digest_after"]
        or _read_service_launch(service_pid, origin) != launch
    ):
        raise M5CodexQuotaWitnessErrorV1("m5_quota_witness_context_changed")
    _revalidate_runtime_binding_v1(
        candidate,
        expected_revision=revision,
        selected_pid=service_pid,
        selected_start_time_ticks=service_ticks,
        dashboard_origin=origin,
        dashboard_cdp_endpoint=endpoint,
    )
    recorded_at = datetime.now(UTC)
    document: dict[str, object] = {
        "schema": QUOTA_WITNESS_SCHEMA,
        "implementation_revision": revision,
        "service_source_revision": revision,
        "service_pid": service_pid,
        "service_start_time_ticks": service_ticks,
        "recorded_at": recorded_at.isoformat(timespec="seconds").replace("+00:00", "Z"),
        "owner_confirmation": "interactive_terminal",
        "provider_key": "codex",
        "provider_version": CODEX_PROVIDER_VERSION,
        "source_id": CODEX_RATE_LIMITS_SOURCE_ID,
        "account_count": reconciliation.account_count,
        "window_count": reconciliation.window_count,
        "owner_outcomes_digest": outcomes_digest,
        "identity_set_digest": browser["identity_set_digest"],
        "collection_run_set_digest": reconciliation.collection_run_set_digest,
        "quota_value_set_digest": reconciliation.value_set_digest,
        "owner_observation_digest": reconciliation.owner_observation_digest,
        "rendered_value_set_digest": browser["rendered_value_set_digest"],
        "history_value_set_digest": browser["history_value_set_digest"],
        "browser_proof_digest": _digest(proof),
        "registry_graph_digest_before": registry_before,
        "registry_graph_digest_after": registry_after,
        "browser_registry_digest_before": browser["registry_digest_before"],
        "browser_registry_digest_after": browser["registry_digest_after"],
    }
    _revalidate_runtime_binding_v1(
        candidate,
        expected_revision=revision,
        selected_pid=service_pid,
        selected_start_time_ticks=service_ticks,
        dashboard_origin=origin,
        dashboard_cdp_endpoint=endpoint,
    )
    return _write_create_once(owner_root / QUOTA_WITNESS_BASENAME, document)


def main() -> int:
    try:
        digest = create_quota_witness_v1(os.environ)
    except (
        M5CodexQuotaWitnessErrorV1,
        M5OwnerOutcomesErrorV1,
        OSError,
        RuntimeError,
        ValueError,
    ) as error:
        code = str(error)
        if re.fullmatch(r"[a-z0-9_]+", code) is None:
            code = "m5_quota_witness_unavailable"
        print(f"M5 CODEX QUOTA WITNESS: BLOCKED — {code}")
        return 3
    print(f"M5 CODEX QUOTA WITNESS: PASSED — receipt_sha256={digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
