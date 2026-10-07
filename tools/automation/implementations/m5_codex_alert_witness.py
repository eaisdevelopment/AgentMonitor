"""Create the private M5 Codex alert witness from persisted real-system facts.

This command is intentionally separate from ``AUTO-M5-EXIT``.  It can run only
after an owner has completed the alert action in the authenticated dashboard
and a newer genuine Codex capacity reading has recovered the same alert.
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
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from itertools import pairwise
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "backend/src"))

from agentmonitor.adapters.persistence._shared.sqlite.core.policy import DatabaseRefV1
from agentmonitor.adapters.persistence.alerting.sqlite.actions import (
    SqliteAlertActionRepositoryV1,
)
from agentmonitor.adapters.persistence.capacity.sqlite.repository import (
    SqliteCapacityRepositoryV1,
)
from agentmonitor.contracts.alerting_v1 import (
    AcknowledgeAlertCommandV1,
    AlertHistoryEntryV1,
    AlertHistoryQueryV1,
    AlertListQueryV1,
    AlertScopeRefV1,
    AlertSignalReceiptV1,
    AlertViewV1,
    SnoozeAlertCommandV1,
)
from agentmonitor.contracts.capacity_v1 import (
    CapacityCommittedNoticeV1,
    CapacityHistoryPointV1,
    CapacityHistoryQueryV1,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.events_v1 import DurableEventV1
from agentmonitor.modules.alerting.application.queries import (
    ListAlertHistoryV1,
    ListAlertsV1,
)
from agentmonitor.modules.capacity.application.events import ReadCapacityEventsV1
from agentmonitor.modules.capacity.application.queries import ListCapacityHistoryV1

from tools.automation.implementations.auto_m3_current_exit import (
    _clean_revision,
    _process_start_ticks,
    _read_service_launch,
)
from tools.automation.implementations.m5_owner_outcomes import (
    OWNER_OUTCOMES_BASENAME,
    M5OwnerOutcomesErrorV1,
    read_owner_outcomes_file_v2,
)

ALERT_WITNESS_BASENAME = "m5-alert-witness.json"
ALERT_WITNESS_SCHEMA = "agentmonitor.m5-alert-witness.v2"
BROWSER_PROOF_SCHEMA = "agentmonitor.m5-alert-browser-proof.v2"
REGISTRY_DIGEST_SCOPE = "all-public-registry-fields-v1"
OWNER_SNOOZE_SECONDS = 900
MAX_LIFECYCLE_AGE = timedelta(days=8)
MAX_CLOCK_SKEW = timedelta(minutes=5)

CODEX_PROVIDER_VERSION = "0.160.0"
CODEX_ADAPTER_ID = "agentmonitor.codex"
CODEX_ADAPTER_VERSION = "1.0.1"
CODEX_PARSER_VERSION = "1.0.0"
CODEX_RATE_LIMITS_SOURCE_ID = "codex.app-server.account-rate-limits-read.v2"
CODEX_MAPPING_ID = "M5-CDX-0-160-0-002"
CODEX_MAPPING_DIGEST = (
    "2ac086063dbfdae1c673f7cd899ac60d6d559bc72dbb598c6e5196c43567a204"
)
CODEX_SCHEMA_BUNDLE_DIGEST = (
    "36bd8e1d76b12b89b06446a85c45e957945eb8cb63b05061264c3dec97f625da"
)
CODEX_APP_SERVER_MECHANISM_VERSION = (
    "codex-app-server-v2@0.160.0+schema." + CODEX_SCHEMA_BUNDLE_DIGEST
)

_OPAQUE = re.compile(r"[A-Za-z0-9_-]{1,64}\Z")
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")


class M5CodexAlertWitnessErrorV1(ValueError):
    """One bounded reason; no identity, provider payload, or filesystem path."""


@dataclass(frozen=True, slots=True)
class CodexAlertHistoryEvidenceV1:
    opened: AlertHistoryEntryV1
    repeated: AlertHistoryEntryV1
    owner_action: AlertHistoryEntryV1
    recovered: AlertHistoryEntryV1


@dataclass(frozen=True, slots=True)
class CodexObservationEvidenceV1:
    combined_digest: str
    opening_digest: str
    repeated_digest: str
    recovery_digest: str
    opening_observation_id: OpaqueIdV1
    repeated_observation_id: OpaqueIdV1
    recovery_observation_id: OpaqueIdV1


@dataclass(frozen=True, slots=True)
class CodexAlertLifecycleV1:
    account_id: OpaqueIdV1
    alert: AlertViewV1
    history: tuple[AlertHistoryEntryV1, ...]
    opened: AlertHistoryEntryV1
    repeated: AlertHistoryEntryV1
    owner_action: AlertHistoryEntryV1
    recovered: AlertHistoryEntryV1
    opening_event: DurableEventV1[CapacityCommittedNoticeV1]
    repeated_event: DurableEventV1[CapacityCommittedNoticeV1]
    recovery_event: DurableEventV1[CapacityCommittedNoticeV1]
    history_digest: str
    source_event_digest: str
    source_observation_digest: str
    opening_observation_digest: str
    repeated_observation_digest: str
    recovery_observation_digest: str
    source_delivery_receipt_digest: str
    owner_action_receipt_digest: str


def _digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value, ensure_ascii=True, separators=(",", ":"), sort_keys=True
        ).encode("ascii")
    ).hexdigest()


def _utc_text(value: datetime) -> str:
    if value.utcoffset() != timedelta(0):
        raise M5CodexAlertWitnessErrorV1("m5_alert_witness_time_invalid")
    return (
        value.astimezone(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")
    )


def _process_started_at(pid: int, expected_start_ticks: int) -> datetime:
    """Convert one validated Linux process identity to a bounded UTC instant."""

    try:
        if _process_start_ticks(pid) != expected_start_ticks:
            raise ValueError
        ticks_per_second = os.sysconf("SC_CLK_TCK")
        if type(ticks_per_second) is not int or not 1 <= ticks_per_second <= 1_000_000:
            raise ValueError
        raw = Path("/proc/stat").read_text(encoding="ascii")
        if len(raw) > 1_048_576:
            raise ValueError
        boot_values = tuple(
            int(line.split()[1])
            for line in raw.splitlines()
            if line.startswith("btime ") and len(line.split()) == 2
        )
        if len(boot_values) != 1 or boot_values[0] < 1:
            raise ValueError
        return datetime.fromtimestamp(
            boot_values[0] + expected_start_ticks / ticks_per_second, tz=UTC
        )
    except (OSError, UnicodeError, ValueError):
        raise M5CodexAlertWitnessErrorV1(
            "m5_alert_witness_service_freshness_invalid"
        ) from None


def validate_lifecycle_freshness_v1(
    *,
    service_started_at: datetime,
    opened_at: datetime,
    recovered_at: datetime,
    as_of: datetime,
    alert_record_version: int,
    alert_aggregate_sequence: int,
    final_history_sequence: int,
) -> None:
    """Require the selected lifecycle to belong to this fresh service epoch."""

    values = (service_started_at, opened_at, recovered_at, as_of)
    if (
        any(item.utcoffset() != timedelta(0) for item in values)
        or not service_started_at <= opened_at <= recovered_at <= as_of + MAX_CLOCK_SKEW
        or as_of - recovered_at > MAX_LIFECYCLE_AGE
        or type(alert_record_version) is not int
        or type(alert_aggregate_sequence) is not int
        or type(final_history_sequence) is not int
        or not alert_record_version
        == alert_aggregate_sequence
        == final_history_sequence
        or alert_record_version < 4
    ):
        raise M5CodexAlertWitnessErrorV1("m5_alert_witness_lifecycle_freshness_invalid")


def _history_material(
    history: tuple[AlertHistoryEntryV1, ...],
) -> list[list[str | int | None]]:
    return [
        [
            item.event_id.value,
            item.alert_id.value,
            item.aggregate_sequence,
            item.transition,
            _utc_text(item.occurred_at),
            item.previous_lifecycle,
            item.current_lifecycle,
            item.previous_severity,
            item.current_severity,
            item.reason_code,
            item.source_event_id.value if item.source_event_id is not None else None,
        ]
        for item in history
    ]


def select_alert_lifecycle_evidence_v1(
    history: tuple[AlertHistoryEntryV1, ...],
) -> CodexAlertHistoryEvidenceV1:
    """Select one unambiguous open/repeat/action/recovery generation."""

    if (
        not history
        or history[0].aggregate_sequence != 1
        or len({item.alert_id for item in history}) != 1
        or len({item.event_id for item in history}) != len(history)
        or any(
            current.aggregate_sequence + 1 != following.aggregate_sequence
            or current.occurred_at > following.occurred_at
            for current, following in pairwise(history)
        )
    ):
        raise M5CodexAlertWitnessErrorV1("m5_alert_witness_lifecycle_incomplete")
    opened = tuple(item for item in history if item.transition == "opened")
    recovered = tuple(item for item in history if item.transition == "recovered")
    owner_actions = tuple(
        item for item in history if item.transition in {"acknowledged", "snoozed"}
    )
    if len(opened) != 1 or len(recovered) != 1 or len(owner_actions) != 1:
        raise M5CodexAlertWitnessErrorV1("m5_alert_witness_lifecycle_incomplete")
    opening = opened[0]
    action = owner_actions[0]
    recovery = recovered[0]
    repeats = tuple(
        item
        for item in history
        if item.transition == "repeated"
        and opening.aggregate_sequence
        < item.aggregate_sequence
        < action.aggregate_sequence
    )
    active_source_ids = {
        opening.source_event_id,
        *(item.source_event_id for item in repeats),
    }
    if (
        not repeats
        or opening.source_event_id is None
        or any(item.source_event_id is None for item in repeats)
        or len(active_source_ids) != len(repeats) + 1
    ):
        raise M5CodexAlertWitnessErrorV1("m5_alert_witness_deduplication_unproven")
    # The persisted command receipt snapshots the alert state seen by the owner.
    # When several genuine active observations preceded that action, its decision
    # source is the latest one.
    repeated = repeats[-1]
    if (
        recovery.source_event_id is None
        or recovery.source_event_id in active_source_ids
        or action.command_id is None
        or action.actor_id is None
        or not opening.aggregate_sequence
        < repeated.aggregate_sequence
        < action.aggregate_sequence
        < recovery.aggregate_sequence
        or not opening.occurred_at
        <= repeated.occurred_at
        <= action.occurred_at
        <= recovery.occurred_at
    ):
        raise M5CodexAlertWitnessErrorV1("m5_alert_witness_lifecycle_incomplete")
    return CodexAlertHistoryEvidenceV1(opening, repeated, action, recovery)


def build_owner_action_command_v1(
    action: AlertHistoryEntryV1,
) -> AcknowledgeAlertCommandV1 | SnoozeAlertCommandV1:
    """Reconstruct the closed command key used by M07's receipt query port."""

    if (
        action.transition not in {"acknowledged", "snoozed"}
        or action.command_id is None
        or action.actor_id is None
        or action.aggregate_sequence < 2
    ):
        raise M5CodexAlertWitnessErrorV1(
            "m5_alert_witness_owner_action_receipt_missing"
        )
    values = (
        action.command_id,
        action.actor_id,
        action.alert_id,
        action.aggregate_sequence - 1,
        action.occurred_at,
    )
    if action.transition == "snoozed":
        return SnoozeAlertCommandV1(*values, OWNER_SNOOZE_SECONDS)
    return AcknowledgeAlertCommandV1(*values)


def read_verified_owner_accounts_v1(path: Path) -> frozenset[str]:
    """Read verified IDs from the closed, fresh v2 owner attestation."""

    try:
        parsed, _digest_value = read_owner_outcomes_file_v2(path, now=datetime.now(UTC))
        if not parsed.verified_account_ids:
            raise M5OwnerOutcomesErrorV1("m5_owner_outcomes_invalid")
        return parsed.verified_account_ids
    except M5OwnerOutcomesErrorV1:
        raise M5CodexAlertWitnessErrorV1(
            "m5_alert_witness_owner_outcomes_invalid"
        ) from None


def _all_history(
    repository: SqliteAlertActionRepositoryV1,
    alert_id: OpaqueIdV1,
    *,
    as_of: datetime,
) -> tuple[AlertHistoryEntryV1, ...]:
    query = ListAlertHistoryV1(repository)
    after: str | None = None
    items: list[AlertHistoryEntryV1] = []
    for _ in range(32):
        page = query(AlertHistoryQueryV1(alert_id, as_of, 200, after))
        if page.availability.state != "available":
            break
        items.extend(page.items)
        if not page.has_more:
            return tuple(items)
        if page.next_key is None or page.next_key == after:
            break
        after = page.next_key
    raise M5CodexAlertWitnessErrorV1("m5_alert_witness_history_incomplete")


def _candidate_alerts(
    repository: SqliteAlertActionRepositoryV1,
    account_id: OpaqueIdV1,
    *,
    as_of: datetime,
) -> tuple[AlertViewV1, ...]:
    page = ListAlertsV1(repository)(
        AlertListQueryV1(
            as_of,
            condition_type="capacity_remaining",
            scope=AlertScopeRefV1("account", account_id.value),
            lifecycle="recovered",
            limit=200,
        )
    )
    if page.availability.state != "available" or page.has_more:
        raise M5CodexAlertWitnessErrorV1("m5_alert_witness_alert_page_incomplete")
    return tuple(
        item
        for item in page.items
        if item.subject.account_id == account_id
        and item.subject.provider_key == "codex"
        and item.condition_type == "capacity_remaining"
    )


def _events_by_id(
    repository: SqliteCapacityRepositoryV1,
    event_ids: frozenset[OpaqueIdV1],
    *,
    as_of: datetime,
) -> dict[OpaqueIdV1, DurableEventV1[CapacityCommittedNoticeV1]]:
    reader = ReadCapacityEventsV1(repository)
    after: str | None = None
    selected: dict[OpaqueIdV1, DurableEventV1[CapacityCommittedNoticeV1]] = {}
    for _ in range(512):
        page = reader("m5-alert-witness-readonly", after, as_of, 200)
        if page.availability.state != "available":
            break
        for event in page.events:
            if event.envelope.event_id in event_ids:
                selected[event.envelope.event_id] = event
        if len(selected) == len(event_ids):
            return selected
        if page.next_cursor is None or page.next_cursor == after:
            break
        after = page.next_cursor
    raise M5CodexAlertWitnessErrorV1("m5_alert_witness_source_event_missing")


def _require_event_already_acknowledged(
    repository: SqliteCapacityRepositoryV1,
    event_id: OpaqueIdV1,
    *,
    as_of: datetime,
) -> None:
    """Prove the alert consumer already acknowledged this persisted event."""

    reader = ReadCapacityEventsV1(repository)
    after: str | None = None
    for _ in range(512):
        page = reader("m07-alert-capacity-v1", after, as_of, 200)
        if page.availability.state != "available":
            break
        if any(item.envelope.event_id == event_id for item in page.events):
            raise M5CodexAlertWitnessErrorV1(
                "m5_alert_witness_source_event_unacknowledged"
            )
        if page.next_cursor is None or page.next_cursor == after:
            return
        after = page.next_cursor
    raise M5CodexAlertWitnessErrorV1("m5_alert_witness_delivery_state_incomplete")


def _next_source_observation_cursor_v1(
    *, has_more: bool, next_key: str | None, after: str | None
) -> str | None:
    """Advance only a complete, strictly progressing observation page chain."""

    if type(has_more) is not bool:
        raise M5CodexAlertWitnessErrorV1(
            "m5_alert_witness_source_observation_incomplete"
        )
    if not has_more:
        return None
    if type(next_key) is not str or not next_key or next_key == after:
        raise M5CodexAlertWitnessErrorV1(
            "m5_alert_witness_source_observation_incomplete"
        )
    return next_key


def _source_observation_evidence(
    repository: SqliteCapacityRepositoryV1,
    alert: AlertViewV1,
    stages: tuple[
        tuple[
            str,
            DurableEventV1[CapacityCommittedNoticeV1],
            AlertHistoryEntryV1,
        ],
        ...,
    ],
    *,
    as_of: datetime,
) -> CodexObservationEvidenceV1:
    range_start = max(alert.opened_at - timedelta(days=1), as_of - timedelta(days=365))
    range_before = min(as_of, alert.last_seen_at + timedelta(days=1))
    if range_before <= range_start:
        raise M5CodexAlertWitnessErrorV1("m5_alert_witness_history_range_invalid")
    if alert.subject.account_id is None:
        raise M5CodexAlertWitnessErrorV1("m5_alert_witness_account_missing")
    query = ListCapacityHistoryV1(repository)
    after: str | None = None
    points: list[CapacityHistoryPointV1] = []
    for _ in range(128):
        page = query(
            CapacityHistoryQueryV1(
                alert.subject.account_id,
                alert.subject.subject_id,
                OpaqueIdV1(alert.subject.dimension_id),
                "remaining_ratio",
                "poll_snapshot",
                range_start,
                range_before,
                as_of,
                200,
                after,
                None,
                None,
            )
        )
        if page.availability.state != "available":
            raise M5CodexAlertWitnessErrorV1(
                "m5_alert_witness_source_observation_missing"
            )
        points.extend(page.items)
        next_key = _next_source_observation_cursor_v1(
            has_more=page.has_more,
            next_key=page.next_key,
            after=after,
        )
        if next_key is None:
            break
        after = next_key
    else:
        raise M5CodexAlertWitnessErrorV1(
            "m5_alert_witness_source_observation_incomplete"
        )
    if not points:
        raise M5CodexAlertWitnessErrorV1("m5_alert_witness_source_observation_missing")
    stage_digests: dict[str, str] = {}
    stage_observation_ids: dict[str, OpaqueIdV1] = {}
    seen_observations: set[OpaqueIdV1] = set()
    for stage, event, transition in stages:
        run_id = event.envelope.causation_id
        matches = tuple(
            point
            for point in points
            if run_id is not None
            and point.collection_run_id == run_id
            and point.stored_at == event.envelope.recorded_at
        )
        if len(matches) != 1:
            raise M5CodexAlertWitnessErrorV1(
                "m5_alert_witness_source_observation_missing"
            )
        point = matches[0]
        provenance = point.provenance
        if (
            transition.source_event_id != event.envelope.event_id
            or point.observation_id in seen_observations
            or point.subject.provider_key != "codex"
            or point.subject.account_id != alert.subject.account_id
            or point.subject.resource_id != alert.subject.subject_id
            or point.window_id.value != alert.subject.dimension_id
            or point.metric != "remaining_ratio"
            or point.series_kind != "poll_snapshot"
            or point.completeness != "complete"
            or point.value.availability.state != "available"
            or point.value.value is None
            or point.value.value.unit != "ratio"
            or point.value.precision != "exact"
            or point.value.confidence != "high"
            or point.value.value_kind != "derived"
            or provenance.freshness_deadline is None
            or not point.observed_at
            <= point.collected_at
            <= point.stored_at
            < provenance.freshness_deadline
            or provenance.capability_id != "subscription.quota"
            or provenance.capability_schema_version != "1.0"
            or provenance.provider_protocol_version != "1.0.0"
            or provenance.source_id != CODEX_RATE_LIMITS_SOURCE_ID
            or provenance.source_class != "experimental_private_or_browser"
            or provenance.mechanism_version != CODEX_APP_SERVER_MECHANISM_VERSION
            or provenance.provider_version != CODEX_PROVIDER_VERSION
            or provenance.adapter_id != CODEX_ADAPTER_ID
            or provenance.adapter_version != CODEX_ADAPTER_VERSION
            or provenance.parser_version != CODEX_PARSER_VERSION
            or provenance.freshness_policy_id != "codex-rate-limits-five-minute-v1"
            or provenance.precision != "exact"
            or provenance.confidence != "confirmed"
            or provenance.confidence_reason_code
            != "provider_reported_rate_limit_windows"
            or provenance.decision_reference != CODEX_MAPPING_ID
            or provenance.is_experimental is not True
        ):
            raise M5CodexAlertWitnessErrorV1(
                "m5_alert_witness_codex_provenance_invalid"
            )
        seen_observations.add(point.observation_id)
        stage_observation_ids[stage] = point.observation_id
        assert point.value.value is not None
        stage_digests[stage] = _digest(
            {
                "stage": stage,
                "event_id": event.envelope.event_id.value,
                "event_payload_digest": event.payload_digest,
                "collection_run_id": point.collection_run_id.value,
                "observation_id": point.observation_id.value,
                "window_id": point.window_id.value,
                "window_definition_id": point.window_definition_id.value,
                "provider_key": point.subject.provider_key,
                "installation_id": point.subject.installation_id.value,
                "account_id": point.subject.account_id.value,
                "resource_id": point.subject.resource_id.value,
                "window_key": point.window_key,
                "semantic_role": point.semantic_role,
                "native_unit": point.native_unit,
                "definition_version": point.definition_version,
                "metric": point.metric,
                "series_kind": point.series_kind,
                "value": {
                    "coefficient": point.value.value.amount.coefficient,
                    "scale": point.value.value.amount.scale,
                    "unit": point.value.value.unit,
                    "precision": point.value.precision,
                    "confidence": point.value.confidence,
                    "value_kind": point.value.value_kind,
                },
                "observed_at": _utc_text(point.observed_at),
                "interval_start": (
                    _utc_text(point.interval_start)
                    if point.interval_start is not None
                    else None
                ),
                "interval_end": (
                    _utc_text(point.interval_end)
                    if point.interval_end is not None
                    else None
                ),
                "reset_at": (
                    _utc_text(point.reset_at) if point.reset_at is not None else None
                ),
                "reset_precision": point.reset_precision,
                "collected_at": _utc_text(point.collected_at),
                "stored_at": _utc_text(point.stored_at),
                "completeness": point.completeness,
                "provenance": {
                    "capability_id": provenance.capability_id,
                    "capability_schema_version": provenance.capability_schema_version,
                    "provider_protocol_version": provenance.provider_protocol_version,
                    "source_id": provenance.source_id,
                    "source_class": provenance.source_class,
                    "mechanism_version": provenance.mechanism_version,
                    "provider_version": provenance.provider_version,
                    "adapter_id": provenance.adapter_id,
                    "adapter_version": provenance.adapter_version,
                    "parser_version": provenance.parser_version,
                    "freshness_deadline": _utc_text(provenance.freshness_deadline),
                    "freshness_policy_id": provenance.freshness_policy_id,
                    "precision": provenance.precision,
                    "confidence": provenance.confidence,
                    "confidence_reason_code": provenance.confidence_reason_code,
                    "decision_reference": provenance.decision_reference,
                    "is_experimental": provenance.is_experimental,
                },
            }
        )
    recovery_ids = frozenset(alert.decision.source.observation_ids)
    recovery_points = tuple(
        point
        for point in points
        if point.collection_run_id == stages[-1][1].envelope.causation_id
        and point.stored_at == stages[-1][1].envelope.recorded_at
    )
    if (
        not recovery_ids
        or {point.observation_id for point in recovery_points} != set(recovery_ids)
        or recovery_ids != {stage_observation_ids.get("recovery")}
    ):
        raise M5CodexAlertWitnessErrorV1("m5_alert_witness_recovery_provenance_invalid")
    expected_stages = {"opening", "repeated", "recovery"}
    if set(stage_digests) != expected_stages:
        raise M5CodexAlertWitnessErrorV1("m5_alert_witness_source_observation_missing")
    return CodexObservationEvidenceV1(
        _digest([[stage, stage_digests[stage]] for stage in sorted(stage_digests)]),
        stage_digests["opening"],
        stage_digests["repeated"],
        stage_digests["recovery"],
        stage_observation_ids["opening"],
        stage_observation_ids["repeated"],
        stage_observation_ids["recovery"],
    )


def _source_delivery_receipt_digest(
    repository: SqliteAlertActionRepositoryV1,
    alert_id: OpaqueIdV1,
    stages: tuple[
        tuple[
            str,
            DurableEventV1[CapacityCommittedNoticeV1],
            AlertHistoryEntryV1,
        ],
        ...,
    ],
) -> str:
    material: list[list[object]] = []
    generations: list[int] = []
    for stage, event, transition in stages:
        receipt: AlertSignalReceiptV1 | None = repository.lookup_capacity_event(event)
        if (
            receipt is None
            or receipt.event_id != event.envelope.event_id
            or receipt.disposition != "applied"
            or alert_id not in receipt.alert_ids
            or receipt.processed_at != transition.occurred_at
        ):
            raise M5CodexAlertWitnessErrorV1(
                "m5_alert_witness_delivery_receipt_missing"
            )
        generations.append(receipt.source_generation)
        material.append(
            [
                stage,
                receipt.receipt_id.value,
                receipt.event_id.value,
                receipt.disposition,
                receipt.source_generation,
                _utc_text(receipt.processed_at),
                sorted(item.value for item in receipt.alert_ids),
            ]
        )
    if any(current >= following for current, following in pairwise(generations)):
        raise M5CodexAlertWitnessErrorV1("m5_alert_witness_deduplication_unproven")
    return _digest(material)


def _owner_action_receipt_digest(
    repository: SqliteAlertActionRepositoryV1,
    action: AlertHistoryEntryV1,
    repeated_event: DurableEventV1[CapacityCommittedNoticeV1],
    repeated_observation_id: OpaqueIdV1,
) -> str:
    command = build_owner_action_command_v1(action)
    receipt = repository.lookup_alert_command(command)
    if receipt is None:
        raise M5CodexAlertWitnessErrorV1(
            "m5_alert_witness_owner_action_receipt_missing"
        )
    snapshot = receipt.alert
    expected_action_state = (
        snapshot.snoozed_until
        == action.occurred_at + timedelta(seconds=OWNER_SNOOZE_SECONDS)
        if isinstance(command, SnoozeAlertCommandV1)
        else snapshot.acknowledged_at == action.occurred_at
        and snapshot.acknowledged_by == action.actor_id
    )
    if (
        snapshot.alert_id != action.alert_id
        or snapshot.lifecycle != "open"
        or snapshot.record_version != action.aggregate_sequence
        or snapshot.aggregate_sequence != action.aggregate_sequence
        or snapshot.decision.source.event_id != repeated_event.envelope.event_id
        or snapshot.decision.source.observation_ids != (repeated_observation_id,)
        or not expected_action_state
    ):
        raise M5CodexAlertWitnessErrorV1(
            "m5_alert_witness_owner_action_receipt_invalid"
        )
    return _digest(
        [
            receipt.receipt_id.value,
            command.command_id.value,
            command.actor_id.value,
            command.alert_id.value,
            command.expected_record_version,
            action.event_id.value,
            action.transition,
            action.aggregate_sequence,
            snapshot.record_version,
            snapshot.decision.source.event_id.value,
            [item.value for item in snapshot.decision.source.observation_ids],
        ]
    )


def inspect_codex_alert_lifecycle_v1(
    reference: DatabaseRefV1,
    account_id: OpaqueIdV1,
    *,
    alert_id: OpaqueIdV1 | None,
    as_of: datetime,
    prove_deduplication: bool,
    expected_history_digest: str | None = None,
) -> CodexAlertLifecycleV1:
    """Bind one recovered alert to distinct open, repeat, and recovery events."""

    alerts = SqliteAlertActionRepositoryV1(reference)
    candidates = _candidate_alerts(alerts, account_id, as_of=as_of)
    if alert_id is not None:
        candidates = tuple(item for item in candidates if item.alert_id == alert_id)
    if expected_history_digest is not None:
        if _SHA256.fullmatch(expected_history_digest) is None:
            raise M5CodexAlertWitnessErrorV1("m5_alert_witness_history_digest_invalid")
        candidates = tuple(
            item
            for item in candidates
            if _digest(
                _history_material(_all_history(alerts, item.alert_id, as_of=as_of))
            )
            == expected_history_digest
        )
    if len(candidates) != 1:
        raise M5CodexAlertWitnessErrorV1("m5_alert_witness_alert_selection_invalid")
    alert = candidates[0]
    history = _all_history(alerts, alert.alert_id, as_of=as_of)
    selected = select_alert_lifecycle_evidence_v1(history)
    if (
        alert.opened_at != selected.opened.occurred_at
        or alert.recovered_at != selected.recovered.occurred_at
        or alert.decision.source.event_id != selected.recovered.source_event_id
        or alert.decision.truth_state != "current"
        or alert.decision.source.observation_ids == ()
        or alert.decision.remaining_basis_points is None
        or alert.decision.warning_remaining_basis_points is None
        or alert.decision.remaining_basis_points.as_decimal()
        <= alert.decision.warning_remaining_basis_points
    ):
        raise M5CodexAlertWitnessErrorV1("m5_alert_witness_lifecycle_incomplete")
    capacity = SqliteCapacityRepositoryV1(reference)
    assert selected.opened.source_event_id is not None
    assert selected.repeated.source_event_id is not None
    assert selected.recovered.source_event_id is not None
    events = _events_by_id(
        capacity,
        frozenset(
            (
                selected.opened.source_event_id,
                selected.repeated.source_event_id,
                selected.recovered.source_event_id,
            )
        ),
        as_of=as_of,
    )
    opening_event = events[selected.opened.source_event_id]
    repeated_event = events[selected.repeated.source_event_id]
    recovery_event = events[selected.recovered.source_event_id]
    source_events = (opening_event, repeated_event, recovery_event)
    if (
        any(
            event.envelope.subject_id != alert.subject.subject_id
            or event.envelope.producer != "capacity"
            or event.envelope.producer_version != "1.0.0"
            or event.envelope.event_type != "capacity.committed.v1"
            or event.envelope.occurred_at != event.envelope.recorded_at
            or event.event_schema_major != 1
            or event.payload.capability_id != "subscription.quota"
            or event.payload.state != "succeeded"
            or event.envelope.causation_id is None
            for event in source_events
        )
        or len({event.envelope.event_id for event in source_events}) != 3
        or len({event.envelope.causation_id for event in source_events}) != 3
        or len({event.stream_key for event in source_events}) != 1
        or not opening_event.stream_sequence
        < repeated_event.stream_sequence
        < recovery_event.stream_sequence
        or not opening_event.envelope.recorded_at
        <= repeated_event.envelope.recorded_at
        <= recovery_event.envelope.recorded_at
    ):
        raise M5CodexAlertWitnessErrorV1("m5_alert_witness_source_event_invalid")
    history_digest = _digest(_history_material(history))
    if prove_deduplication:
        for event in source_events:
            _require_event_already_acknowledged(
                capacity, event.envelope.event_id, as_of=as_of
            )
    stage_events = (
        ("opening", opening_event, selected.opened),
        ("repeated", repeated_event, selected.repeated),
        ("recovery", recovery_event, selected.recovered),
    )
    source_delivery_receipt_digest = _source_delivery_receipt_digest(
        alerts, alert.alert_id, stage_events
    )
    source_event_digest = _digest(
        [
            [
                stage,
                item.envelope.event_id.value,
                item.envelope.event_type,
                item.envelope.producer,
                item.envelope.producer_version,
                item.event_schema_major,
                item.payload_digest,
                item.payload.capability_id,
                item.payload.projection_count,
                item.payload.state,
                item.envelope.subject_id.value,
                item.envelope.correlation_id.value,
                item.envelope.causation_id.value
                if item.envelope.causation_id is not None
                else None,
                item.stream_key,
                item.stream_sequence,
                _utc_text(item.envelope.occurred_at),
                _utc_text(item.envelope.recorded_at),
            ]
            for stage, item, _transition in stage_events
        ]
    )
    observation_evidence = _source_observation_evidence(
        capacity, alert, stage_events, as_of=as_of
    )
    owner_action_receipt_digest = _owner_action_receipt_digest(
        alerts,
        selected.owner_action,
        repeated_event,
        observation_evidence.repeated_observation_id,
    )
    return CodexAlertLifecycleV1(
        account_id,
        alert,
        history,
        selected.opened,
        selected.repeated,
        selected.owner_action,
        selected.recovered,
        opening_event,
        repeated_event,
        recovery_event,
        history_digest,
        source_event_digest,
        observation_evidence.combined_digest,
        observation_evidence.opening_digest,
        observation_evidence.repeated_digest,
        observation_evidence.recovery_digest,
        source_delivery_receipt_digest,
        owner_action_receipt_digest,
    )


def _browser_proof(
    *,
    endpoint: str,
    origin: str,
    revision: str,
    service_pid: int,
    service_start_time_ticks: int,
    account_id: str,
    alert_id: str,
) -> dict[str, object]:
    environment = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "AGENTMONITOR_TEST_DASHBOARD_CDP_ENDPOINT": endpoint,
        "AGENTMONITOR_TEST_DASHBOARD_ORIGIN": origin,
        "AGENTMONITOR_M5_IMPLEMENTATION_REVISION": revision,
        "AGENTMONITOR_M5_SERVICE_PID": str(service_pid),
        "AGENTMONITOR_M5_SERVICE_START_TIME_TICKS": str(service_start_time_ticks),
        "AGENTMONITOR_TEST_CODEX_ACCOUNT_ID": account_id,
        "AGENTMONITOR_TEST_M5_ALERT_ID": alert_id,
    }
    try:
        result = subprocess.run(
            ["node", "tools/ui/verify_m5_codex_alert_lifecycle.mjs"],
            cwd=ROOT,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
            timeout=180,
        )
    except (OSError, subprocess.TimeoutExpired):
        raise M5CodexAlertWitnessErrorV1(
            "m5_alert_witness_browser_unavailable"
        ) from None
    if result.returncode != 0:
        code = result.stderr.strip().splitlines()[-1:] or [""]
        if not code[0].startswith("M5 CODEX ALERT: "):
            code = ["M5 CODEX ALERT: BLOCKED — browser_unavailable"]
        print(code[0], file=sys.stderr)
        raise M5CodexAlertWitnessErrorV1("m5_alert_witness_browser_unavailable")
    documents: list[dict[str, object]] = []
    for line in result.stdout.splitlines():
        try:
            candidate = json.loads(line)
        except json.JSONDecodeError:
            continue
        if type(candidate) is dict and candidate.get("schema") == BROWSER_PROOF_SCHEMA:
            documents.append(candidate)
    if len(documents) != 1:
        raise M5CodexAlertWitnessErrorV1("m5_alert_witness_browser_proof_missing")
    return documents[0]


def _validate_browser_proof(
    proof: dict[str, object],
    lifecycle: CodexAlertLifecycleV1,
    *,
    revision: str,
    service_pid: int,
    service_start_time_ticks: int,
) -> tuple[str, str, datetime, str, str]:
    expected = {
        "schema",
        "implementation_revision",
        "service_source_revision",
        "service_pid",
        "service_start_time_ticks",
        "account_id",
        "alert_id",
        "presented_at",
        "browser_presented",
        "alert_record_version",
        "history_digest",
        "service_checked_at",
        "service_versions_digest",
        "registry_digest_scope",
        "registry_digest_before",
        "registry_digest_after",
        "mutations",
    }
    try:
        presented = datetime.fromisoformat(str(proof["presented_at"]))
        service_checked = datetime.fromisoformat(str(proof["service_checked_at"]))
        before = proof["registry_digest_before"]
        after = proof["registry_digest_after"]
        versions_digest = proof["service_versions_digest"]
        service_source_revision = proof["service_source_revision"]
        if (
            set(proof) != expected
            or proof["implementation_revision"] != revision
            or service_source_revision != revision
            or type(proof["service_pid"]) is not int
            or proof["service_pid"] != service_pid
            or type(proof["service_start_time_ticks"]) is not int
            or proof["service_start_time_ticks"] != service_start_time_ticks
            or proof["account_id"] != lifecycle.account_id.value
            or proof["alert_id"] != lifecycle.alert.alert_id.value
            or proof["browser_presented"] is not True
            or type(proof["alert_record_version"]) is not int
            or proof["alert_record_version"] != lifecycle.alert.record_version
            or proof["history_digest"] != lifecycle.history_digest
            or type(proof["mutations"]) is not int
            or proof["mutations"] != 0
            or proof["registry_digest_scope"] != REGISTRY_DIGEST_SCOPE
            or type(before) is not str
            or type(after) is not str
            or _SHA256.fullmatch(before) is None
            or before != after
            or type(versions_digest) is not str
            or _SHA256.fullmatch(versions_digest) is None
            or presented.utcoffset() != timedelta(0)
            or service_checked.utcoffset() != timedelta(0)
            or presented < lifecycle.recovered.occurred_at
            or not lifecycle.recovered.occurred_at <= service_checked <= presented
            or presented - service_checked > timedelta(minutes=2)
            or presented > datetime.now(UTC) + timedelta(minutes=5)
        ):
            raise ValueError
        return before, after, service_checked, versions_digest, service_source_revision
    except (KeyError, TypeError, ValueError):
        raise M5CodexAlertWitnessErrorV1(
            "m5_alert_witness_browser_proof_invalid"
        ) from None


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
        or path.name != ALERT_WITNESS_BASENAME
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
    encoded = (
        json.dumps(document, ensure_ascii=True, indent=2, sort_keys=True) + "\n"
    ).encode("ascii")
    if len(encoded) > 16_384:
        raise M5CodexAlertWitnessErrorV1("m5_alert_witness_output_invalid")
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
        while position < len(encoded):
            written = os.write(descriptor, encoded[position:])
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
        raise M5CodexAlertWitnessErrorV1(
            "m5_alert_witness_create_once_failed"
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
    return hashlib.sha256(encoded).hexdigest()


def create_alert_witness_v1(environment: Mapping[str, str]) -> str:
    try:
        owner_root = Path(environment["AGENTMONITOR_TEST_OWNER_DATA_ROOT"])
        endpoint = environment["AGENTMONITOR_TEST_DASHBOARD_CDP_ENDPOINT"]
        origin = environment["AGENTMONITOR_TEST_DASHBOARD_ORIGIN"]
        service_pid = int(environment["AGENTMONITOR_M5_SERVICE_PID"])
    except (KeyError, TypeError, ValueError):
        raise M5CodexAlertWitnessErrorV1(
            "m5_alert_witness_selection_required"
        ) from None
    try:
        owner_metadata = owner_root.stat()
        owner_root_valid = (
            owner_root.is_absolute()
            and owner_root.resolve(strict=True) == owner_root
            and stat.S_ISDIR(owner_metadata.st_mode)
            and stat.S_IMODE(owner_metadata.st_mode) == 0o700
            and owner_metadata.st_uid == os.getuid()
        )
    except OSError:
        owner_root_valid = False
    if not owner_root_valid:
        raise M5CodexAlertWitnessErrorV1("m5_alert_witness_owner_root_invalid")
    try:
        from urllib.parse import urlparse

        if (
            urlparse(endpoint).hostname != "127.0.0.1"
            or urlparse(origin).hostname != "127.0.0.1"
            or urlparse(origin).scheme != "http"
        ):
            raise ValueError
    except ValueError:
        raise M5CodexAlertWitnessErrorV1("m5_alert_witness_loopback_required") from None
    revision = _clean_revision()
    start_ticks = _process_start_ticks(service_pid)
    launch = _read_service_launch(service_pid, origin)
    service_started_at = _process_started_at(service_pid, start_ticks)
    if launch.data_root != owner_root:
        raise M5CodexAlertWitnessErrorV1("m5_alert_witness_service_mismatch")
    now = datetime.now(UTC)
    try:
        owner_outcomes, _owner_outcomes_digest = read_owner_outcomes_file_v2(
            owner_root / OWNER_OUTCOMES_BASENAME, now=now
        )
    except M5OwnerOutcomesErrorV1:
        raise M5CodexAlertWitnessErrorV1(
            "m5_alert_witness_owner_outcomes_invalid"
        ) from None
    if (
        owner_outcomes.implementation_revision != revision
        or owner_outcomes.service_pid != service_pid
        or owner_outcomes.service_start_time_ticks != start_ticks
        or owner_outcomes.owner_confirmed_at < service_started_at
        or not owner_outcomes.verified_account_ids
    ):
        raise M5CodexAlertWitnessErrorV1(
            "m5_alert_witness_owner_outcomes_context_invalid"
        )
    verified = owner_outcomes.verified_account_ids
    requested_account = environment.get("AGENTMONITOR_TEST_CODEX_ACCOUNT_ID")
    if requested_account is None:
        if len(verified) != 1:
            raise M5CodexAlertWitnessErrorV1(
                "m5_alert_witness_account_selection_required"
            )
        requested_account = next(iter(verified))
    if requested_account not in verified:
        raise M5CodexAlertWitnessErrorV1("m5_alert_witness_account_selection_invalid")
    requested_alert = environment.get("AGENTMONITOR_TEST_M5_ALERT_ID")
    if requested_alert is not None and _OPAQUE.fullmatch(requested_alert) is None:
        raise M5CodexAlertWitnessErrorV1("m5_alert_witness_alert_selection_invalid")
    reference = DatabaseRefV1(owner_root / "agentmonitor.db", owner_root)
    lifecycle = inspect_codex_alert_lifecycle_v1(
        reference,
        OpaqueIdV1(requested_account),
        alert_id=OpaqueIdV1(requested_alert) if requested_alert else None,
        as_of=now,
        prove_deduplication=True,
    )
    validate_lifecycle_freshness_v1(
        service_started_at=service_started_at,
        opened_at=lifecycle.opened.occurred_at,
        recovered_at=lifecycle.recovered.occurred_at,
        as_of=now,
        alert_record_version=lifecycle.alert.record_version,
        alert_aggregate_sequence=lifecycle.alert.aggregate_sequence,
        final_history_sequence=lifecycle.history[-1].aggregate_sequence,
    )
    if lifecycle.opened.occurred_at < owner_outcomes.owner_confirmed_at:
        raise M5CodexAlertWitnessErrorV1("m5_alert_witness_lifecycle_freshness_invalid")
    proof = _browser_proof(
        endpoint=endpoint,
        origin=origin,
        revision=revision,
        service_pid=service_pid,
        service_start_time_ticks=start_ticks,
        account_id=requested_account,
        alert_id=lifecycle.alert.alert_id.value,
    )
    (
        registry_before,
        registry_after,
        service_checked_at,
        service_versions_digest,
        service_source_revision,
    ) = _validate_browser_proof(
        proof,
        lifecycle,
        revision=revision,
        service_pid=service_pid,
        service_start_time_ticks=start_ticks,
    )
    if (
        _process_start_ticks(service_pid) != start_ticks
        or _process_started_at(service_pid, start_ticks) != service_started_at
        or _read_service_launch(service_pid, origin) != launch
        or _clean_revision() != revision
    ):
        raise M5CodexAlertWitnessErrorV1("m5_alert_witness_context_changed")
    recorded_at = datetime.now(UTC)
    final_lifecycle = inspect_codex_alert_lifecycle_v1(
        reference,
        OpaqueIdV1(requested_account),
        alert_id=lifecycle.alert.alert_id,
        as_of=recorded_at,
        prove_deduplication=False,
    )
    validate_lifecycle_freshness_v1(
        service_started_at=service_started_at,
        opened_at=final_lifecycle.opened.occurred_at,
        recovered_at=final_lifecycle.recovered.occurred_at,
        as_of=recorded_at,
        alert_record_version=final_lifecycle.alert.record_version,
        alert_aggregate_sequence=final_lifecycle.alert.aggregate_sequence,
        final_history_sequence=final_lifecycle.history[-1].aggregate_sequence,
    )
    if (
        final_lifecycle.alert.record_version != lifecycle.alert.record_version
        or final_lifecycle.alert.aggregate_sequence
        != lifecycle.alert.aggregate_sequence
        or final_lifecycle.history_digest != lifecycle.history_digest
        or final_lifecycle.source_event_digest != lifecycle.source_event_digest
        or final_lifecycle.source_observation_digest
        != lifecycle.source_observation_digest
        or final_lifecycle.opening_observation_digest
        != lifecycle.opening_observation_digest
        or final_lifecycle.repeated_observation_digest
        != lifecycle.repeated_observation_digest
        or final_lifecycle.recovery_observation_digest
        != lifecycle.recovery_observation_digest
        or final_lifecycle.source_delivery_receipt_digest
        != lifecycle.source_delivery_receipt_digest
        or final_lifecycle.owner_action_receipt_digest
        != lifecycle.owner_action_receipt_digest
    ):
        raise M5CodexAlertWitnessErrorV1("m5_alert_witness_lifecycle_changed")
    document: dict[str, object] = {
        "schema": ALERT_WITNESS_SCHEMA,
        "implementation_revision": revision,
        "service_source_revision": service_source_revision,
        "service_pid": service_pid,
        "service_start_time_ticks": start_ticks,
        "service_started_at": _utc_text(service_started_at),
        "service_checked_at": _utc_text(service_checked_at),
        "service_versions_digest": service_versions_digest,
        "provider_key": "codex",
        "account_id": requested_account,
        "source_id": CODEX_RATE_LIMITS_SOURCE_ID,
        "provider_version": CODEX_PROVIDER_VERSION,
        "adapter_id": CODEX_ADAPTER_ID,
        "adapter_version": CODEX_ADAPTER_VERSION,
        "parser_version": CODEX_PARSER_VERSION,
        "mapping_id": CODEX_MAPPING_ID,
        "mapping_digest": CODEX_MAPPING_DIGEST,
        "schema_bundle_digest": CODEX_SCHEMA_BUNDLE_DIGEST,
        "alert_record_version": lifecycle.alert.record_version,
        "alert_aggregate_sequence": lifecycle.alert.aggregate_sequence,
        "opened_at": _utc_text(lifecycle.opened.occurred_at),
        "deduplicated_at": _utc_text(lifecycle.repeated.occurred_at),
        "owner_action_at": _utc_text(lifecycle.owner_action.occurred_at),
        "recovered_at": _utc_text(lifecycle.recovered.occurred_at),
        "recorded_at": _utc_text(recorded_at),
        "owner_action": lifecycle.owner_action.transition,
        "opened": True,
        "deduplicated": True,
        "browser_presented": True,
        "recovered": True,
        "source_proven_opening": True,
        "source_proven_deduplication": True,
        "source_proven_recovery": True,
        "source_event_digest": lifecycle.source_event_digest,
        "source_observation_digest": lifecycle.source_observation_digest,
        "opening_observation_digest": lifecycle.opening_observation_digest,
        "deduplication_observation_digest": lifecycle.repeated_observation_digest,
        "recovery_observation_digest": lifecycle.recovery_observation_digest,
        "source_delivery_receipt_digest": lifecycle.source_delivery_receipt_digest,
        "alert_history_digest": lifecycle.history_digest,
        "owner_action_receipt_digest": lifecycle.owner_action_receipt_digest,
        "registry_digest_scope": REGISTRY_DIGEST_SCOPE,
        "registry_digest_before": registry_before,
        "registry_digest_after": registry_after,
    }
    return _write_create_once(owner_root / ALERT_WITNESS_BASENAME, document)


def main() -> int:
    try:
        digest = create_alert_witness_v1(os.environ)
    except (M5CodexAlertWitnessErrorV1, ValueError) as error:
        code = str(error)
        if not re.fullmatch(r"[a-z0-9_]+", code):
            code = "m5_alert_witness_unavailable"
        print(f"M5 CODEX ALERT WITNESS: BLOCKED — {code}")
        return 3
    print(f"M5 CODEX ALERT WITNESS: PASSED — receipt_sha256={digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
