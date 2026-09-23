"""M03 compatibility repository tests over real file-backed SQLite."""

from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path
from typing import cast

import pytest
from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
    DatabaseRefV1,
    open_sqlite_database,
)
from agentmonitor.adapters.persistence._shared.sqlite.schema.compatibility import (
    migrate_to_head,
)
from agentmonitor.adapters.persistence.provider_system.sqlite.repository import (
    ProviderSystemRepositoryErrorV1,
    SqliteProviderSystemCompatibilityRepositoryV1,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.provider_system_v1 import (
    CompatibilityAssessmentInputV1,
    InvalidProviderContract,
    ProviderSystemOutboxEventV1,
)


def _repository(tmp_path: Path) -> SqliteProviderSystemCompatibilityRepositoryV1:
    reference = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    migrate_to_head(reference)
    return SqliteProviderSystemCompatibilityRepositoryV1(reference)


def _assessment(
    *,
    manifest_fingerprint: str = "a" * 64,
    provider_version: str = "2.1.278",
    assessed_at: datetime | None = None,
) -> CompatibilityAssessmentInputV1:
    instant = assessed_at or datetime(2026, 9, 22, 12, 0, tzinfo=UTC)
    return CompatibilityAssessmentInputV1(
        registration_id=OpaqueIdV1("registration-001"),
        provider_key="claude",
        adapter_id="claude-adapter",
        adapter_version="1.0.0",
        protocol_version="1.0.0",
        installation_id=OpaqueIdV1("installation-001"),
        capability_id="subscription.quota",
        capability_schema_version="1.0",
        source_id="claude.usage.ax-screen-reader.v1",
        provider_version_value=provider_version,
        provider_version_state="available",
        version_scheme="opaque_exact",
        version_rule_id="claude-code-exact-v1",
        compatibility_state="compatible",
        reason_code="exact_evidenced_tuple",
        manifest_schema_version="1.0.0",
        manifest_fingerprint=manifest_fingerprint,
        assessed_at=instant,
        valid_until=instant + timedelta(days=30),
        correlation_id=OpaqueIdV1("correlation-001"),
    )


def _assessment_without_optional_scope(
    *, manifest_fingerprint: str, assessed_at: datetime
) -> CompatibilityAssessmentInputV1:
    return CompatibilityAssessmentInputV1(
        registration_id=OpaqueIdV1("registration-nullable-001"),
        provider_key="claude",
        adapter_id="claude-adapter",
        adapter_version="1.0.0",
        protocol_version="1.0.0",
        installation_id=None,
        capability_id="subscription.quota",
        capability_schema_version="1.0",
        source_id=None,
        provider_version_value=None,
        provider_version_state="unknown",
        version_scheme=None,
        version_rule_id=None,
        compatibility_state="unverified",
        reason_code="version_evidence_unavailable",
        manifest_schema_version="1.0.0",
        manifest_fingerprint=manifest_fingerprint,
        assessed_at=assessed_at,
        valid_until=None,
        correlation_id=OpaqueIdV1("correlation-nullable-001"),
    )


def test_assessment_round_trip_survives_real_sqlite_reopen(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    assessment = _assessment()

    recorded = repository.record(assessment)
    reopened = repository.reopen()

    assert reopened.get(recorded.assessment_id) == recorded
    assert recorded.registration_id == assessment.registration_id
    assert recorded.provider_version_value == "2.1.278"
    assert recorded.compatibility_state == "compatible"
    assert recorded.is_current
    assert recorded.record_version == 1
    assert recorded.supersedes_assessment_id is None


def test_exact_current_input_reuses_assessment_and_outbox(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    assessment = _assessment()

    first = repository.record(assessment)
    second = repository.record(assessment)

    assert second == first
    assert repository.history(
        OpaqueIdV1("registration-001"), "subscription.quota", limit=10
    ) == (first,)
    events = repository.pending_outbox(limit=10)
    assert len(events) == 1
    assert events[0].assessment_id == first.assessment_id
    assert events[0].producer_sequence == 1


def test_semantically_identical_reassessment_ignores_request_metadata(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path)
    first_input = _assessment()
    later_request = replace(
        first_input,
        assessed_at=first_input.assessed_at + timedelta(minutes=5),
        correlation_id=OpaqueIdV1("correlation-002"),
    )

    first = repository.record(first_input)
    replayed = repository.record(later_request)

    assert replayed == first
    assert repository.history(
        OpaqueIdV1("registration-001"), "subscription.quota", limit=10
    ) == (first,)
    assert len(repository.pending_outbox(limit=10)) == 1


def test_changed_input_supersedes_history_and_appends_atomic_outbox(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path)
    first = repository.record(_assessment())
    second = repository.record(
        _assessment(
            manifest_fingerprint="b" * 64,
            provider_version="2.1.279",
            assessed_at=datetime(2026, 9, 22, 12, 5, tzinfo=UTC),
        )
    )

    assert second.assessment_id != first.assessment_id
    assert second.supersedes_assessment_id == first.assessment_id
    assert second.is_current
    superseded = repository.get(first.assessment_id)
    assert superseded is not None
    assert not superseded.is_current
    assert (
        repository.current(
            registration_id=OpaqueIdV1("registration-001"),
            installation_id=OpaqueIdV1("installation-001"),
            capability_id="subscription.quota",
            source_id="claude.usage.ax-screen-reader.v1",
        )
        == second
    )
    assert repository.history(
        OpaqueIdV1("registration-001"), "subscription.quota", limit=10
    ) == (second, superseded)

    events = repository.pending_outbox(limit=10)
    assert tuple(event.assessment_id for event in events) == (
        first.assessment_id,
        second.assessment_id,
    )
    assert tuple(event.producer_sequence for event in events) == (1, 2)


def test_queries_are_bounded_and_fail_with_safe_codes(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    repository.record(_assessment())

    for query in (
        lambda: repository.history(
            OpaqueIdV1("registration-001"), "subscription.quota", limit=101
        ),
        lambda: repository.pending_outbox(limit=0),
    ):
        with pytest.raises(ProviderSystemRepositoryErrorV1) as caught:
            query()
        assert caught.value.code == "provider_system_query_invalid"
        assert "agentmonitor.db" not in str(caught.value)


def test_every_public_query_argument_fails_closed_with_safe_code(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path)
    repository.record(_assessment())
    invalid_opaque = cast(OpaqueIdV1, object())
    invalid_optional_opaque = cast(OpaqueIdV1 | None, "not-an-opaque-id")
    queries: tuple[Callable[[], object], ...] = (
        lambda: repository.get(invalid_opaque),
        lambda: repository.get(OpaqueIdV1("x" * 65)),
        lambda: repository.current(
            registration_id=invalid_opaque,
            installation_id=None,
            capability_id="subscription.quota",
            source_id=None,
        ),
        lambda: repository.current(
            registration_id=OpaqueIdV1("registration-001"),
            installation_id=invalid_optional_opaque,
            capability_id="subscription.quota",
            source_id=None,
        ),
        lambda: repository.current(
            registration_id=OpaqueIdV1("registration-001"),
            installation_id=None,
            capability_id="Subscription.Quota",
            source_id=None,
        ),
        lambda: repository.current(
            registration_id=OpaqueIdV1("registration-001"),
            installation_id=None,
            capability_id=cast(str, object()),
            source_id=None,
        ),
        lambda: repository.current(
            registration_id=OpaqueIdV1("registration-001"),
            installation_id=None,
            capability_id="subscription.quota",
            source_id=" leading-space",
        ),
        lambda: repository.current(
            registration_id=OpaqueIdV1("registration-001"),
            installation_id=None,
            capability_id="subscription.quota",
            source_id=cast(str | None, object()),
        ),
        lambda: repository.history(invalid_opaque, "subscription.quota", limit=10),
        lambda: repository.history(
            OpaqueIdV1("registration-001"), "not_a_capability", limit=10
        ),
        lambda: repository.history(
            OpaqueIdV1("registration-001"),
            "subscription.quota",
            limit=cast(int, True),
        ),
        lambda: repository.pending_outbox(limit=cast(int, True)),
    )

    for query in queries:
        with pytest.raises(ProviderSystemRepositoryErrorV1) as caught:
            query()
        assert caught.value.code == "provider_system_query_invalid"
        assert str(caught.value) == "provider_system_query_invalid"


def test_outbox_contract_rejects_invalid_state_and_timestamp_relationships() -> None:
    instant = datetime(2026, 9, 22, 12, 0, tzinfo=UTC)
    event = ProviderSystemOutboxEventV1(
        event_id=OpaqueIdV1("event-001"),
        event_type="provider.compatibility.assessed.v1",
        assessment_id=OpaqueIdV1("assessment-001"),
        registration_id=OpaqueIdV1("registration-001"),
        provider_key="claude",
        capability_id="subscription.quota",
        compatibility_state="compatible",
        reason_code="exact_evidenced_tuple",
        correlation_id=OpaqueIdV1("correlation-001"),
        producer_sequence=1,
        occurred_at=instant,
        recorded_at=instant,
        delivery_state="pending",
        available_at=instant,
        claimed_at=None,
        delivered_at=None,
        attempt_count=0,
    )

    invalid_events = (
        {"recorded_at": instant - timedelta(microseconds=1)},
        {"available_at": instant - timedelta(microseconds=1)},
        {"claimed_at": instant},
        {"delivery_state": "claimed", "attempt_count": 1},
        {
            "delivery_state": "delivered",
            "claimed_at": instant,
            "attempt_count": 1,
        },
        {
            "delivery_state": "claimed",
            "claimed_at": instant,
            "attempt_count": 0,
        },
        {
            "delivery_state": "delivered",
            "claimed_at": instant + timedelta(seconds=2),
            "delivered_at": instant + timedelta(seconds=1),
            "attempt_count": 1,
        },
    )

    for changes in invalid_events:
        with pytest.raises(InvalidProviderContract):
            replace(event, **changes)

    claimed = replace(
        event,
        delivery_state="claimed",
        claimed_at=instant + timedelta(seconds=1),
        attempt_count=1,
    )
    delivered = replace(
        claimed,
        delivery_state="delivered",
        delivered_at=instant + timedelta(seconds=2),
    )
    assert claimed.delivery_state == "claimed"
    assert delivered.delivery_state == "delivered"

    with pytest.raises(
        InvalidProviderContract, match="provider_system_outbox_timestamp_invalid"
    ):
        replace(event, occurred_at=datetime(2026, 9, 22, 12, 0))


def test_changed_assessments_in_nullable_scope_leave_one_current_row(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path)
    inputs = (
        _assessment_without_optional_scope(
            manifest_fingerprint="c" * 64,
            assessed_at=datetime(2026, 9, 22, 13, 0, tzinfo=UTC),
        ),
        _assessment_without_optional_scope(
            manifest_fingerprint="d" * 64,
            assessed_at=datetime(2026, 9, 22, 13, 1, tzinfo=UTC),
        ),
    )

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = tuple(executor.map(repository.record, inputs))

    current = repository.current(
        registration_id=OpaqueIdV1("registration-nullable-001"),
        installation_id=None,
        capability_id="subscription.quota",
        source_id=None,
    )
    history = repository.history(
        OpaqueIdV1("registration-nullable-001"), "subscription.quota", limit=10
    )
    assert current in results
    assert len(history) == 2
    assert sum(item.is_current for item in history) == 1
    assert {item.assessment_id for item in history} == {
        item.assessment_id for item in results
    }


def test_non_available_version_rejects_scheme_and_rule() -> None:
    with pytest.raises(
        InvalidProviderContract,
        match="compatibility_version_pair_invalid",
    ):
        CompatibilityAssessmentInputV1(
            registration_id=OpaqueIdV1("registration-001"),
            provider_key="claude",
            adapter_id="claude-adapter",
            adapter_version="1.0.0",
            protocol_version="1.0.0",
            installation_id=None,
            capability_id="subscription.quota",
            capability_schema_version="1.0",
            source_id=None,
            provider_version_value=None,
            provider_version_state="unknown",
            version_scheme="opaque_exact",
            version_rule_id="claude-code-exact-v1",
            compatibility_state="unverified",
            reason_code="version_evidence_unavailable",
            manifest_schema_version="1.0.0",
            manifest_fingerprint="e" * 64,
            assessed_at=datetime(2026, 9, 22, 13, 0, tzinfo=UTC),
            valid_until=None,
            correlation_id=OpaqueIdV1("correlation-001"),
        )


def test_assessment_input_rejects_naive_and_non_utc_timestamps() -> None:
    assessment = _assessment()

    with pytest.raises(
        InvalidProviderContract, match="compatibility_timestamp_invalid"
    ):
        replace(assessment, assessed_at=datetime(2026, 9, 22, 13, 0))
    with pytest.raises(
        InvalidProviderContract, match="compatibility_timestamp_invalid"
    ):
        replace(
            assessment,
            valid_until=datetime(
                2026,
                10,
                22,
                13,
                0,
                tzinfo=timezone(timedelta(hours=1)),
            ),
        )


@pytest.mark.parametrize(
    "mutation",
    (
        "UPDATE provider_system_compatibility_assessment "
        "SET assessed_at='2026-09-22T13:00:00.000000+01:00' "
        "WHERE assessment_id=?",
        "UPDATE provider_system_compatibility_assessment "
        "SET valid_until='2026-10-22T13:00:00.000000' "
        "WHERE assessment_id=?",
    ),
)
def test_non_utc_persisted_timestamp_fails_closed(
    tmp_path: Path, mutation: str
) -> None:
    repository = _repository(tmp_path)
    recorded = repository.record(_assessment())
    reference = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    with open_sqlite_database(reference, "runtime_read_write") as handle:
        with handle.connect() as connection:
            connection.exec_driver_sql("PRAGMA ignore_check_constraints = ON")
            connection.exec_driver_sql(mutation, (recorded.assessment_id.value,))
            connection.commit()
            connection.exec_driver_sql("PRAGMA ignore_check_constraints = OFF")

    with pytest.raises(ProviderSystemRepositoryErrorV1) as caught:
        repository.get(recorded.assessment_id)
    assert caught.value.code == "provider_system_record_invalid"


def test_outbox_failure_rolls_back_assessment_atomically(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    reference = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    with open_sqlite_database(reference, "runtime_read_write") as handle:
        with handle.connect() as connection:
            connection.exec_driver_sql(
                "CREATE TRIGGER fail_provider_system_outbox "
                "BEFORE INSERT ON provider_system_event_outbox "
                "BEGIN SELECT RAISE(ABORT, 'outbox unavailable'); END"
            )
            connection.commit()

    with pytest.raises(ProviderSystemRepositoryErrorV1) as caught:
        repository.record(_assessment())
    assert caught.value.code == "provider_system_repository_unavailable"

    with open_sqlite_database(reference, "runtime_read_write") as handle:
        with handle.connect() as connection:
            assessment_count = connection.exec_driver_sql(
                "SELECT count(*) FROM provider_system_compatibility_assessment"
            ).scalar_one()
            outbox_count = connection.exec_driver_sql(
                "SELECT count(*) FROM provider_system_event_outbox"
            ).scalar_one()
    assert (assessment_count, outbox_count) == (0, 0)
