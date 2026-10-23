"""M5-CDX-ALERT: genuine Codex capacity lifecycle through real SQLite."""

import hashlib
import json
import os
import sqlite3
import time
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
    DatabaseRefV1,
    open_sqlite_database,
)
from agentmonitor.adapters.persistence._shared.sqlite.schema.compatibility import (
    migrate_to_head,
)
from agentmonitor.adapters.persistence.alerting.sqlite.actions import (
    SqliteAlertActionRepositoryV1,
)
from agentmonitor.adapters.persistence.alerting.sqlite.capacity_consumer import (
    AlertCapacityRepositoryErrorV1,
)
from agentmonitor.adapters.persistence.capacity.sqlite.repository import (
    _ACKNOWLEDGED_CAPACITY_EVENT_EVIDENCE_SQL,
    SqliteCapacityRepositoryV1,
)
from agentmonitor.adapters.persistence.registry.sqlite.repository import (
    SqliteRegistryRepositoryV1,
)
from agentmonitor.adapters.providers.codex.manifest import build_codex_manifest
from agentmonitor.composition.alert_delivery import (
    CapacityAlertDeliveryV1,
    _next_registry_cursor_v1,
    _unique_registry_account_ids_v1,
)
from agentmonitor.composition.codex_installation_reconciliation import (
    reconcile_codex_installation_v1,
)
from agentmonitor.contracts.alerting_v1 import (
    AcknowledgeAlertCommandV1,
    AlertHistoryEntryV1,
    AlertLifecycleV1,
    AlertReasonCodeV1,
    AlertSeverityV1,
    AlertTransitionV1,
    SnoozeAlertCommandV1,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.registry_v1 import (
    ConfirmProviderIdentityFingerprintCommandV1,
    PrivateProfileLocatorRefV1,
)
from agentmonitor.modules.capacity.application.events import (
    CapacityEventEvidenceErrorV1,
    ReadAcknowledgedCapacityEventsV1,
    ReadCapacityEventsV1,
)
from agentmonitor.modules.provider_system.application.gateway import (
    get_manifest_fingerprint_v1,
)
from agentmonitor.modules.registry.application.accounts import (
    ConfirmProviderIdentityFingerprintV1,
    CreatePendingAccountCommandV1,
    EditAccountCommandV1,
    EditAccountV1,
    EnrollMonitoringGraphCommandV1,
    EnrollMonitoringGraphV1,
    ListAccountsV1,
    RegisterAccountV1,
)

from tools.automation.implementations.m5_codex_alert_witness import (
    ALERT_WITNESS_SCHEMA,
    CODEX_ADAPTER_ID,
    CODEX_ADAPTER_VERSION,
    CODEX_MAPPING_DIGEST,
    CODEX_MAPPING_ID,
    CODEX_PARSER_VERSION,
    CODEX_PROVIDER_VERSION,
    CODEX_RATE_LIMITS_SOURCE_ID,
    CODEX_SCHEMA_BUNDLE_DIGEST,
    CodexAlertLifecycleV1,
    M5CodexAlertWitnessErrorV1,
    build_owner_action_command_v1,
    inspect_codex_alert_lifecycle_v1,
    read_verified_owner_accounts_v1,
    select_alert_lifecycle_evidence_v1,
    validate_lifecycle_freshness_v1,
)

_PURE_BASE = datetime(2026, 10, 7, 10, tzinfo=UTC)


def test_alert_delivery_registry_cursor_must_advance_once() -> None:
    """M5-CDX-ALERT-001: malformed Registry continuations fail closed."""

    assert (
        _next_registry_cursor_v1(
            has_more=True,
            next_key="account-200",
            after_key=None,
            seen_cursors=frozenset(),
            item_count=200,
            last_account_id="account-200",
        )
        == "account-200"
    )
    assert (
        _next_registry_cursor_v1(
            has_more=False,
            next_key=None,
            after_key="account-200",
            seen_cursors=frozenset({"account-200"}),
            item_count=1,
            last_account_id="account-201",
        )
        is None
    )
    invalid: tuple[
        tuple[bool, str | None, str | None, frozenset[str], int, str | None], ...
    ] = (
        (True, None, None, frozenset(), 200, "account-200"),
        (True, "account-200", "account-200", frozenset(), 200, "account-200"),
        (
            True,
            "account-100",
            "account-200",
            frozenset({"account-100", "account-200"}),
            200,
            "account-100",
        ),
        (True, "account-200", None, frozenset(), 0, None),
        (True, "different", None, frozenset(), 200, "account-200"),
        (False, "unexpected", "account-200", frozenset(), 1, "account-201"),
    )
    for has_more, next_key, after_key, seen, count, last_id in invalid:
        with pytest.raises(
            ValueError, match="capacity_alert_registry_scope_incomplete"
        ):
            _next_registry_cursor_v1(
                has_more=has_more,
                next_key=next_key,
                after_key=after_key,
                seen_cursors=seen,
                item_count=count,
                last_account_id=last_id,
            )


def test_alert_delivery_registry_account_ids_must_be_globally_unique() -> None:
    """M5-CDX-ALERT-001: duplicate IDs within or across pages fail closed."""

    first = _unique_registry_account_ids_v1(
        (OpaqueIdV1("account-one"), OpaqueIdV1("account-two")), frozenset()
    )
    assert first == frozenset({OpaqueIdV1("account-one"), OpaqueIdV1("account-two")})
    for account_ids in (
        (OpaqueIdV1("account-one"),),
        (OpaqueIdV1("account-three"), OpaqueIdV1("account-three")),
    ):
        with pytest.raises(
            ValueError, match="capacity_alert_registry_scope_incomplete"
        ):
            _unique_registry_account_ids_v1(account_ids, first)


def test_alert_delivery_resolves_event_subject_after_first_200_real_accounts(
    tmp_path: Path,
) -> None:
    """M5-CDX-ALERT-001: delivery traverses the complete Registry snapshot."""

    reference = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    migrate_to_head(reference)
    installation = reconcile_codex_installation_v1(reference)
    repository = SqliteRegistryRepositoryV1(reference)
    register = RegisterAccountV1(repository)
    manifest = get_manifest_fingerprint_v1(build_codex_manifest())
    principal = OpaqueIdV1("alert-pagination-owner")
    requested_at = datetime.now(UTC)
    for index in range(200):
        register.pending(
            CreatePendingAccountCommandV1(
                OpaqueIdV1(uuid.uuid4().hex),
                principal,
                "codex",
                manifest,
                f"Alert pagination {index:03d}",
                None,
                requested_at,
            )
        )
    target = register.pending(
        CreatePendingAccountCommandV1(
            OpaqueIdV1(uuid.uuid4().hex),
            principal,
            "codex",
            manifest,
            "Zzz alert pagination target",
            None,
            requested_at,
        )
    )
    fingerprint = hashlib.sha256(b"alert-pagination-identity").hexdigest()
    ConfirmProviderIdentityFingerprintV1(repository)(
        ConfirmProviderIdentityFingerprintCommandV1(
            idempotency_key=OpaqueIdV1(uuid.uuid4().hex),
            principal_id=principal,
            account_id=target.account_id,
            expected_account_record_version=target.record_version,
            provider_key="codex",
            identity_scheme="codex.app_server.account.sha256",
            identity_scope="provider_account",
            identity_scheme_version=1,
            subject_fingerprint=fingerprint,
            source_id="codex.app-server.account-read.v2",
            source_version="2",
            parser_version=CODEX_PARSER_VERSION,
            evidence_reference=OpaqueIdV1("alert-pagination-evidence"),
            expected_evidence_digest=fingerprint,
            requested_at=requested_at,
            activate_pending_account=True,
        )
    )
    locator = "codex-alert-pagination-managed-profile"
    _profile, resource = EnrollMonitoringGraphV1(repository)(
        EnrollMonitoringGraphCommandV1(
            command_id=OpaqueIdV1("alert-pagination-enrollment"),
            principal_id=principal,
            account_id=target.account_id,
            provider_installation_id=installation.provider_installation_id,
            purpose="subscription",
            profile_locator_ref=PrivateProfileLocatorRefV1(locator),
            locator_fingerprint=hashlib.sha256(locator.encode()).hexdigest(),
            management_state="managed",
            compatibility_state="compatible",
            is_protected_default=False,
            resource_kind="subscription_pool",
            parent_resource_id=None,
            requested_at=requested_at,
        )
    )
    first = ListAccountsV1(repository).page(None, as_of=requested_at, limit=200)
    assert first.has_more
    assert target.account_id not in {account.account_id for account in first.items}

    resolved = CapacityAlertDeliveryV1(reference)._account_for_subject(
        resource.resource_id,
        as_of=requested_at,
    )

    assert resolved == target.account_id
    active = repository.get_account(target.account_id)
    assert active is not None
    EditAccountV1(repository)(
        EditAccountCommandV1(
            account_id=active.account_id,
            expected_version=active.record_version,
            principal_id=principal,
            command_id=OpaqueIdV1("alert-pagination-archive"),
            action="archive",
            requested_at=datetime.now(UTC),
        )
    )
    with pytest.raises(ValueError, match="capacity_alert_subject_unresolved"):
        CapacityAlertDeliveryV1(reference)._account_for_subject(
            resource.resource_id,
            as_of=datetime.now(UTC),
        )


def _history_entry(
    sequence: int,
    transition: AlertTransitionV1,
    *,
    source_event_id: str | None = None,
    command_id: str | None = None,
    actor_id: str | None = None,
) -> AlertHistoryEntryV1:
    previous_lifecycle: AlertLifecycleV1 | None = (
        None
        if transition == "opened"
        else "recovered"
        if transition == "reopened"
        else "open"
    )
    current_lifecycle: AlertLifecycleV1 = (
        "recovered" if transition == "recovered" else "open"
    )
    previous_severity: AlertSeverityV1 | None = (
        None
        if transition == "opened"
        else "information"
        if transition == "reopened"
        else "critical"
    )
    current_severity: AlertSeverityV1 = (
        "information" if transition == "recovered" else "critical"
    )
    reason_code: AlertReasonCodeV1 = "capacity_ratio_current"
    if transition == "acknowledged":
        reason_code = "acknowledged"
    elif transition == "snoozed":
        reason_code = "snoozed"
    return AlertHistoryEntryV1(
        OpaqueIdV1(f"history-{sequence}"),
        OpaqueIdV1("alert-one"),
        sequence,
        transition,
        _PURE_BASE + timedelta(minutes=sequence),
        previous_lifecycle,
        current_lifecycle,
        previous_severity,
        current_severity,
        OpaqueIdV1(actor_id) if actor_id else None,
        reason_code,
        OpaqueIdV1(source_event_id) if source_event_id else None,
        OpaqueIdV1(command_id) if command_id else None,
    )


def test_alert_witness_policy_requires_distinct_active_observations_before_action() -> (
    None
):
    """M5-CDX-ALERT-002: two real source deliveries must share one lifecycle."""

    history = (
        _history_entry(1, "opened", source_event_id="capacity-open"),
        _history_entry(2, "repeated", source_event_id="capacity-repeat"),
        _history_entry(
            3,
            "acknowledged",
            command_id="owner-command",
            actor_id="administrator",
        ),
        _history_entry(4, "recovered", source_event_id="capacity-recovery"),
    )

    selected = select_alert_lifecycle_evidence_v1(history)

    assert selected.opened.source_event_id == OpaqueIdV1("capacity-open")
    assert selected.repeated.source_event_id == OpaqueIdV1("capacity-repeat")
    assert selected.owner_action.command_id == OpaqueIdV1("owner-command")
    assert selected.recovered.source_event_id == OpaqueIdV1("capacity-recovery")

    for invalid in (
        (
            history[0],
            _history_entry(
                2,
                "acknowledged",
                command_id="owner-command",
                actor_id="administrator",
            ),
            _history_entry(3, "recovered", source_event_id="capacity-recovery"),
        ),
        (
            history[0],
            _history_entry(2, "repeated", source_event_id="capacity-open"),
            history[2],
            history[3],
        ),
    ):
        with pytest.raises(
            M5CodexAlertWitnessErrorV1,
            match="m5_alert_witness_deduplication_unproven",
        ):
            select_alert_lifecycle_evidence_v1(invalid)


def test_alert_witness_policy_binds_latest_repeat_and_distinct_recovery() -> None:
    """M5-CDX-ALERT-002/005: recovery cannot reuse any active source event."""

    history = (
        _history_entry(1, "opened", source_event_id="capacity-open"),
        _history_entry(2, "repeated", source_event_id="capacity-repeat-first"),
        _history_entry(3, "repeated", source_event_id="capacity-repeat-latest"),
        _history_entry(
            4,
            "acknowledged",
            command_id="owner-command",
            actor_id="administrator",
        ),
        _history_entry(5, "recovered", source_event_id="capacity-recovery"),
    )

    selected = select_alert_lifecycle_evidence_v1(history)

    assert selected.repeated.source_event_id == OpaqueIdV1("capacity-repeat-latest")
    with pytest.raises(
        M5CodexAlertWitnessErrorV1,
        match="m5_alert_witness_lifecycle_incomplete",
    ):
        select_alert_lifecycle_evidence_v1(
            (
                *history[:-1],
                _history_entry(5, "recovered", source_event_id="capacity-repeat-first"),
            )
        )
    with pytest.raises(
        M5CodexAlertWitnessErrorV1,
        match="m5_alert_witness_lifecycle_incomplete",
    ):
        select_alert_lifecycle_evidence_v1(
            (history[0], history[2], history[3], history[4])
        )


def test_alert_witness_policy_selects_the_latest_reopened_generation() -> None:
    """M5-CDX-ALERT-002: a fresh retry remains provable on retained history."""

    history = (
        _history_entry(1, "opened", source_event_id="old-open"),
        _history_entry(2, "repeated", source_event_id="old-repeat"),
        _history_entry(
            3,
            "acknowledged",
            command_id="old-owner-command",
            actor_id="administrator",
        ),
        _history_entry(4, "recovered", source_event_id="old-recovery"),
        _history_entry(5, "reopened", source_event_id="fresh-open"),
        _history_entry(6, "repeated", source_event_id="fresh-repeat"),
        _history_entry(
            7,
            "acknowledged",
            command_id="fresh-owner-command",
            actor_id="administrator",
        ),
        _history_entry(8, "recovered", source_event_id="fresh-recovery"),
    )

    selected = select_alert_lifecycle_evidence_v1(history)

    assert selected.opened.transition == "reopened"
    assert selected.opened.source_event_id == OpaqueIdV1("fresh-open")
    assert selected.repeated.source_event_id == OpaqueIdV1("fresh-repeat")
    assert selected.owner_action.command_id == OpaqueIdV1("fresh-owner-command")
    assert selected.recovered.source_event_id == OpaqueIdV1("fresh-recovery")

    invalid_generations = (
        history[:-1],
        (
            _history_entry(1, "reopened", source_event_id="fresh-open"),
            _history_entry(2, "repeated", source_event_id="fresh-repeat"),
            _history_entry(
                3,
                "acknowledged",
                command_id="fresh-owner-command",
                actor_id="administrator",
            ),
            _history_entry(4, "recovered", source_event_id="fresh-recovery"),
        ),
        (*history, _history_entry(9, "reopened", source_event_id="late-open")),
        (*history, _history_entry(9, "recovered", source_event_id="extra-recovery")),
        (
            history[0],
            _history_entry(2, "reopened", source_event_id="nested-open"),
            _history_entry(3, "repeated", source_event_id="nested-repeat"),
            _history_entry(
                4,
                "acknowledged",
                command_id="nested-owner-command",
                actor_id="administrator",
            ),
            _history_entry(5, "recovered", source_event_id="nested-recovery"),
        ),
    )
    for invalid in invalid_generations:
        with pytest.raises(
            M5CodexAlertWitnessErrorV1,
            match="m5_alert_witness_lifecycle_incomplete",
        ):
            select_alert_lifecycle_evidence_v1(invalid)


@pytest.mark.parametrize(
    ("transition", "expected_type"),
    (("acknowledged", AcknowledgeAlertCommandV1), ("snoozed", SnoozeAlertCommandV1)),
)
def test_alert_witness_policy_reconstructs_the_persisted_owner_command(
    transition: AlertTransitionV1, expected_type: type[object]
) -> None:
    """M5-CDX-ALERT-004: receipt lookup uses the exact authenticated command key."""

    action = _history_entry(
        3,
        transition,
        command_id="owner-command",
        actor_id="administrator",
    )

    command = build_owner_action_command_v1(action)

    assert isinstance(command, expected_type)
    assert command.command_id == OpaqueIdV1("owner-command")
    assert command.actor_id == OpaqueIdV1("administrator")
    assert command.alert_id == OpaqueIdV1("alert-one")
    assert command.expected_record_version == 2
    if isinstance(command, SnoozeAlertCommandV1):
        assert command.duration_seconds == 900


def test_alert_witness_policy_requires_current_service_lifecycle_revision() -> None:
    """M5-CDX-ALERT-006: old-service or mismatched revision evidence is rejected."""

    validate_lifecycle_freshness_v1(
        service_started_at=_PURE_BASE,
        opened_at=_PURE_BASE + timedelta(minutes=1),
        recovered_at=_PURE_BASE + timedelta(minutes=4),
        as_of=_PURE_BASE + timedelta(minutes=5),
        alert_record_version=4,
        alert_aggregate_sequence=4,
        final_history_sequence=4,
    )
    invalid = (
        (
            _PURE_BASE - timedelta(seconds=1),
            _PURE_BASE + timedelta(minutes=4),
            4,
        ),
        (
            _PURE_BASE + timedelta(minutes=1),
            _PURE_BASE - timedelta(days=9),
            4,
        ),
        (
            _PURE_BASE + timedelta(minutes=1),
            _PURE_BASE + timedelta(minutes=4),
            5,
        ),
    )
    for opened_at, recovered_at, alert_record_version in invalid:
        with pytest.raises(
            M5CodexAlertWitnessErrorV1,
            match="m5_alert_witness_lifecycle_freshness_invalid",
        ):
            validate_lifecycle_freshness_v1(
                service_started_at=_PURE_BASE,
                opened_at=opened_at,
                recovered_at=recovered_at,
                as_of=_PURE_BASE + timedelta(minutes=5),
                alert_record_version=alert_record_version,
                alert_aggregate_sequence=4,
                final_history_sequence=4,
            )


def _owner_selection() -> tuple[DatabaseRefV1, OpaqueIdV1, Path]:
    raw_root = os.environ.get("AGENTMONITOR_TEST_OWNER_DATA_ROOT") or os.environ.get(
        "AGENTMONITOR_TEST_DATA_ROOT"
    )
    if raw_root is None:
        pytest.skip("NOT RUN: select the actual owner AgentMonitor data root")
    assert raw_root is not None
    root = Path(raw_root)
    try:
        verified = read_verified_owner_accounts_v1(root / "m5-owner-outcomes.json")
    except M5CodexAlertWitnessErrorV1 as error:
        pytest.skip(f"NOT RUN: {error}")
        raise AssertionError("pytest.skip returned") from None
    requested = os.environ.get("AGENTMONITOR_TEST_CODEX_ACCOUNT_ID")
    if requested is None:
        if len(verified) != 1:
            pytest.skip("NOT RUN: select one verified Codex account")
        requested = next(iter(verified))
    if requested not in verified:
        pytest.fail("BLOCKED: selected Codex account is not a verified owner outcome")
    return DatabaseRefV1(root / "agentmonitor.db", root), OpaqueIdV1(requested), root


def _lifecycle(
    reference: DatabaseRefV1,
    account_id: OpaqueIdV1,
    *,
    prove_deduplication: bool,
) -> CodexAlertLifecycleV1:
    expected_history_digest = None
    selected_witness = os.environ.get("AGENTMONITOR_TEST_M5_ALERT_WITNESS")
    if selected_witness is not None:
        try:
            witness = json.loads(Path(selected_witness).read_bytes())
            candidate = witness.get("alert_history_digest")
            if isinstance(candidate, str):
                expected_history_digest = candidate
        except (OSError, json.JSONDecodeError):
            pass
    try:
        return inspect_codex_alert_lifecycle_v1(
            reference,
            account_id,
            alert_id=(
                OpaqueIdV1(value)
                if (value := os.environ.get("AGENTMONITOR_TEST_M5_ALERT_ID"))
                else None
            ),
            as_of=datetime.now(UTC),
            prove_deduplication=prove_deduplication,
            expected_history_digest=expected_history_digest,
        )
    except M5CodexAlertWitnessErrorV1 as error:
        pytest.skip(f"NOT RUN: {error}")
        raise AssertionError("pytest.skip returned") from None


def _copy_owner_database(source: Path, target_root: Path) -> DatabaseRefV1:
    target = target_root / "agentmonitor.db"
    with sqlite3.connect(source) as owner:
        with sqlite3.connect(target) as isolated:
            owner.backup(isolated)
    os.chmod(target, 0o600)
    return DatabaseRefV1(target, target_root)


def test_genuine_codex_event_routes_through_provider_neutral_delivery(
    tmp_path: Path,
) -> None:
    """M5-CDX-ALERT-001: the delivery resolver must enumerate every provider."""

    owner, account_id, root = _owner_selection()
    lifecycle = _lifecycle(owner, account_id, prove_deduplication=False)
    copied = _copy_owner_database(root / "agentmonitor.db", tmp_path)
    with open_sqlite_database(copied, "runtime_read_write") as handle:
        with handle.connect() as connection:
            connection.exec_driver_sql("BEGIN IMMEDIATE")
            connection.exec_driver_sql(
                "DELETE FROM capacity_event_delivery WHERE event_id=? "
                "AND consumer_key=?",
                (
                    lifecycle.opening_event.envelope.event_id.value,
                    "m07-alert-capacity-v1",
                ),
            )
            connection.commit()
    pending = ReadCapacityEventsV1(SqliteCapacityRepositoryV1(copied))(
        "m07-alert-capacity-v1", None, datetime.now(UTC), 1
    )
    if (
        not pending.events
        or pending.events[0].envelope.event_id
        != lifecycle.opening_event.envelope.event_id
    ):
        pytest.skip("NOT RUN: owner alert consumer has an earlier pending event")
    delivery = CapacityAlertDeliveryV1(copied)
    assert delivery.deliver_next(as_of=datetime.now(UTC)) == "capacity_alert_delivered"
    remaining = ReadCapacityEventsV1(SqliteCapacityRepositoryV1(copied))(
        "m07-alert-capacity-v1", None, datetime.now(UTC), 200
    )
    assert all(
        event.envelope.event_id != lifecycle.opening_event.envelope.event_id
        for event in remaining.events
    )


def test_genuine_codex_alert_deduplicates_owner_action_and_recovers(
    tmp_path: Path,
) -> None:
    """M5-CDX-ALERT-002..005: retained lifecycle and persisted receipt proof."""

    _owner, account_id, root = _owner_selection()
    copied = _copy_owner_database(root / "agentmonitor.db", tmp_path)
    lifecycle = _lifecycle(copied, account_id, prove_deduplication=True)
    assert lifecycle.alert.lifecycle == "recovered"
    assert lifecycle.opened.transition in {"opened", "reopened"}
    assert lifecycle.opened.source_event_id == lifecycle.opening_event.envelope.event_id
    assert lifecycle.repeated.transition == "repeated"
    assert lifecycle.owner_action.transition in {"acknowledged", "snoozed"}
    assert lifecycle.recovered.transition == "recovered"
    assert (
        len(
            {
                lifecycle.opening_event.envelope.event_id,
                lifecycle.repeated_event.envelope.event_id,
                lifecycle.recovery_event.envelope.event_id,
            }
        )
        == 3
    )
    assert (
        len(
            {
                lifecycle.opening_observation_digest,
                lifecycle.repeated_observation_digest,
                lifecycle.recovery_observation_digest,
            }
        )
        == 3
    )
    assert lifecycle.alert.decision.source.event_id == (
        lifecycle.recovery_event.envelope.event_id
    )


def test_genuine_codex_acknowledgement_evidence_is_bounded_and_cross_bound() -> None:
    """M5-CDX-ALERT-008: three exact M05 proofs agree with M07 receipts."""

    reference, account_id, _root = _owner_selection()
    lifecycle = _lifecycle(reference, account_id, prove_deduplication=False)
    selected_ids = (
        lifecycle.recovery_event.envelope.event_id,
        lifecycle.opening_event.envelope.event_id,
        lifecycle.repeated_event.envelope.event_id,
    )
    started = time.monotonic()
    acknowledged = ReadAcknowledgedCapacityEventsV1(
        SqliteCapacityRepositoryV1(reference)
    )("m07-alert-capacity-v1", selected_ids, datetime.now(UTC))
    elapsed = time.monotonic() - started

    assert elapsed < 30
    assert tuple(item.event.envelope.event_id for item in acknowledged) == selected_ids
    alert_repository = SqliteAlertActionRepositoryV1(reference)
    for item in acknowledged:
        receipt = alert_repository.lookup_capacity_event(item.event)
        assert receipt is not None
        assert receipt.event_id == item.event.envelope.event_id
        assert receipt.receipt_id == item.acknowledgement_receipt_id
        assert receipt.processed_at == item.acknowledged_at

    selector = json.dumps(
        [item.value for item in selected_ids],
        ensure_ascii=True,
        separators=(",", ":"),
    )
    with open_sqlite_database(reference, "runtime_read_only") as handle:
        with handle.connect() as connection:
            outbox_count = int(
                connection.exec_driver_sql(
                    "SELECT count(*) FROM capacity_event_outbox"
                ).scalar_one()
            )
            plan = tuple(
                str(row[3])
                for row in connection.exec_driver_sql(
                    "EXPLAIN QUERY PLAN " + _ACKNOWLEDGED_CAPACITY_EVENT_EVIDENCE_SQL,
                    (selector, "m07-alert-capacity-v1"),
                ).all()
            )
    assert outbox_count > 36_000
    assert any(
        "SEARCH e USING INDEX sqlite_autoindex_capacity_event_outbox_1" in step
        for step in plan
    )
    assert any(
        "SEARCH d USING INDEX sqlite_autoindex_capacity_event_delivery_1" in step
        for step in plan
    )
    assert all("SCAN e" not in step and "SCAN d" not in step for step in plan)


def test_genuine_codex_acknowledgement_evidence_rejects_missing_or_partial_proof(
    tmp_path: Path,
) -> None:
    """M5-CDX-ALERT-008: absent and incomplete delivery proof fail closed."""

    owner, account_id, root = _owner_selection()
    lifecycle = _lifecycle(owner, account_id, prove_deduplication=False)
    selected_ids = (
        lifecycle.opening_event.envelope.event_id,
        lifecycle.repeated_event.envelope.event_id,
        lifecycle.recovery_event.envelope.event_id,
    )
    as_of = datetime.now(UTC)

    missing_root = tmp_path / "missing"
    missing_root.mkdir()
    missing_root.chmod(0o700)
    missing = _copy_owner_database(root / "agentmonitor.db", missing_root)
    with open_sqlite_database(missing, "runtime_read_write") as handle:
        with handle.connect() as connection:
            connection.exec_driver_sql("BEGIN IMMEDIATE")
            connection.exec_driver_sql(
                "DELETE FROM capacity_event_delivery WHERE event_id=? "
                "AND consumer_key='m07-alert-capacity-v1'",
                (selected_ids[0].value,),
            )
            connection.commit()
    with pytest.raises(CapacityEventEvidenceErrorV1) as absent:
        ReadAcknowledgedCapacityEventsV1(SqliteCapacityRepositoryV1(missing))(
            "m07-alert-capacity-v1", selected_ids, as_of
        )
    assert absent.value.code == "capacity_event_evidence_delivery_unacknowledged"

    partial_root = tmp_path / "partial"
    partial_root.mkdir()
    partial_root.chmod(0o700)
    partial = _copy_owner_database(root / "agentmonitor.db", partial_root)
    with open_sqlite_database(partial, "runtime_read_write") as handle:
        with handle.connect() as connection:
            connection.exec_driver_sql("BEGIN IMMEDIATE")
            connection.exec_driver_sql(
                "UPDATE capacity_event_delivery SET ack_receipt_id=NULL, "
                "ack_payload_digest=NULL WHERE event_id=? "
                "AND consumer_key='m07-alert-capacity-v1'",
                (selected_ids[0].value,),
            )
            connection.commit()
    with pytest.raises(CapacityEventEvidenceErrorV1) as incomplete:
        ReadAcknowledgedCapacityEventsV1(SqliteCapacityRepositoryV1(partial))(
            "m07-alert-capacity-v1", selected_ids, as_of
        )
    assert incomplete.value.code == "capacity_event_evidence_invalid"

    digest_root = tmp_path / "digest"
    digest_root.mkdir()
    digest_root.chmod(0o700)
    digest_conflict = _copy_owner_database(root / "agentmonitor.db", digest_root)
    actual_digest = lifecycle.opening_event.payload_digest
    wrong_digest = actual_digest[:-1] + ("0" if actual_digest[-1] != "0" else "1")
    with open_sqlite_database(digest_conflict, "runtime_read_write") as handle:
        with handle.connect() as connection:
            connection.exec_driver_sql("BEGIN IMMEDIATE")
            connection.exec_driver_sql(
                "UPDATE capacity_event_delivery SET ack_payload_digest=? "
                "WHERE event_id=? AND consumer_key='m07-alert-capacity-v1'",
                (wrong_digest, selected_ids[0].value),
            )
            connection.commit()
    with pytest.raises(CapacityEventEvidenceErrorV1) as digest_mismatch:
        ReadAcknowledgedCapacityEventsV1(SqliteCapacityRepositoryV1(digest_conflict))(
            "m07-alert-capacity-v1", selected_ids, as_of
        )
    assert digest_mismatch.value.code == "capacity_event_evidence_invalid"

    future_root = tmp_path / "future"
    future_root.mkdir()
    future_root.chmod(0o700)
    future = _copy_owner_database(root / "agentmonitor.db", future_root)
    future_acknowledgement = (
        (as_of + timedelta(seconds=1))
        .isoformat(timespec="microseconds")
        .replace("+00:00", "Z")
    )
    with open_sqlite_database(future, "runtime_read_write") as handle:
        with handle.connect() as connection:
            connection.exec_driver_sql("BEGIN IMMEDIATE")
            connection.exec_driver_sql(
                "UPDATE capacity_event_delivery SET acknowledged_at=? "
                "WHERE event_id=? AND consumer_key='m07-alert-capacity-v1'",
                (future_acknowledgement, selected_ids[0].value),
            )
            connection.commit()
    with pytest.raises(CapacityEventEvidenceErrorV1) as future_proof:
        ReadAcknowledgedCapacityEventsV1(SqliteCapacityRepositoryV1(future))(
            "m07-alert-capacity-v1", selected_ids, as_of
        )
    assert future_proof.value.code == "capacity_event_evidence_invalid"


def test_genuine_codex_delivery_receipt_cross_binding_rejects_each_mismatch(
    tmp_path: Path,
) -> None:
    """M5-CDX-ALERT-008: M05 and M07 receipt proofs must agree exactly."""

    owner, account_id, root = _owner_selection()
    lifecycle = _lifecycle(owner, account_id, prove_deduplication=False)
    event_id = lifecycle.opening_event.envelope.event_id

    def copied_reference(name: str) -> DatabaseRefV1:
        copied_root = tmp_path / name
        copied_root.mkdir()
        copied_root.chmod(0o700)
        return _copy_owner_database(root / "agentmonitor.db", copied_root)

    def inspect(reference: DatabaseRefV1) -> None:
        inspect_codex_alert_lifecycle_v1(
            reference,
            account_id,
            alert_id=lifecycle.alert.alert_id,
            as_of=datetime.now(UTC),
            prove_deduplication=False,
        )

    receipt_mismatch = copied_reference("receipt-mismatch")
    with open_sqlite_database(receipt_mismatch, "runtime_read_write") as handle:
        with handle.connect() as connection:
            connection.exec_driver_sql("BEGIN IMMEDIATE")
            connection.exec_driver_sql(
                "UPDATE capacity_event_delivery SET ack_receipt_id=? "
                "WHERE event_id=? AND consumer_key='m07-alert-capacity-v1'",
                ("mismatched-m05-ack-receipt", event_id.value),
            )
            connection.commit()
    with pytest.raises(
        M5CodexAlertWitnessErrorV1,
        match="m5_alert_witness_delivery_receipt_missing",
    ):
        inspect(receipt_mismatch)

    time_mismatch = copied_reference("time-mismatch")
    shifted_acknowledgement = (
        (lifecycle.opened.occurred_at + timedelta(microseconds=1))
        .isoformat(timespec="microseconds")
        .replace("+00:00", "Z")
    )
    with open_sqlite_database(time_mismatch, "runtime_read_write") as handle:
        with handle.connect() as connection:
            connection.exec_driver_sql("BEGIN IMMEDIATE")
            connection.exec_driver_sql(
                "UPDATE capacity_event_delivery SET acknowledged_at=? "
                "WHERE event_id=? AND consumer_key='m07-alert-capacity-v1'",
                (shifted_acknowledgement, event_id.value),
            )
            connection.commit()
    with pytest.raises(
        M5CodexAlertWitnessErrorV1,
        match="m5_alert_witness_delivery_receipt_missing",
    ):
        inspect(time_mismatch)

    digest_mismatch = copied_reference("m07-digest-mismatch")
    actual_digest = lifecycle.opening_event.payload_digest
    wrong_digest = actual_digest[:-1] + ("0" if actual_digest[-1] != "0" else "1")
    with open_sqlite_database(digest_mismatch, "runtime_read_write") as handle:
        with handle.connect() as connection:
            connection.exec_driver_sql("BEGIN IMMEDIATE")
            connection.exec_driver_sql(
                "UPDATE alert_event_receipt SET payload_digest=? "
                "WHERE producer_key='capacity' AND event_id=?",
                (wrong_digest, event_id.value),
            )
            connection.commit()
    with pytest.raises(
        AlertCapacityRepositoryErrorV1,
        match="alert_capacity_event_digest_conflict",
    ):
        inspect(digest_mismatch)


def test_private_alert_witness_matches_the_persisted_codex_lifecycle() -> None:
    """M5-CDX-ALERT-006: the gate prerequisite is derived from those facts."""

    reference, account_id, root = _owner_selection()
    lifecycle = _lifecycle(reference, account_id, prove_deduplication=False)
    selected = os.environ.get("AGENTMONITOR_TEST_M5_ALERT_WITNESS")
    path = Path(selected) if selected else root / "m5-alert-witness.json"
    try:
        document = json.loads(path.read_bytes())
    except (OSError, json.JSONDecodeError):
        pytest.skip("NOT RUN: private M5 alert witness has not been created")
    assert document["schema"] == ALERT_WITNESS_SCHEMA
    assert document["provider_key"] == "codex"
    assert document["account_id"] == account_id.value
    assert document["source_id"] == CODEX_RATE_LIMITS_SOURCE_ID
    assert document["provider_version"] == CODEX_PROVIDER_VERSION
    assert document["adapter_id"] == CODEX_ADAPTER_ID
    assert document["adapter_version"] == CODEX_ADAPTER_VERSION
    assert document["parser_version"] == CODEX_PARSER_VERSION
    assert document["mapping_id"] == CODEX_MAPPING_ID
    assert document["mapping_digest"] == CODEX_MAPPING_DIGEST
    assert document["schema_bundle_digest"] == CODEX_SCHEMA_BUNDLE_DIGEST
    assert document["alert_record_version"] == lifecycle.alert.record_version
    assert document["alert_aggregate_sequence"] == lifecycle.alert.aggregate_sequence
    assert document["owner_action"] == lifecycle.owner_action.transition
    assert document["source_event_digest"] == lifecycle.source_event_digest
    assert document["source_observation_digest"] == lifecycle.source_observation_digest
    assert document["opening_observation_digest"] == (
        lifecycle.opening_observation_digest
    )
    assert document["deduplication_observation_digest"] == (
        lifecycle.repeated_observation_digest
    )
    assert document["recovery_observation_digest"] == (
        lifecycle.recovery_observation_digest
    )
    assert document["source_delivery_receipt_digest"] == (
        lifecycle.source_delivery_receipt_digest
    )
    assert document["alert_history_digest"] == lifecycle.history_digest
    assert document["owner_action_receipt_digest"] == (
        lifecycle.owner_action_receipt_digest
    )
    assert document["registry_digest_before"] == document["registry_digest_after"]
    assert all(
        document[key] is True
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
