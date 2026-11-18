"""Expire genuine reports only in an isolated copy using real producer ports."""

import hashlib
import os
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from agentmonitor.adapters.operations import budget_retention_checkpoint
from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
    DatabaseRefV1,
    open_sqlite_database,
)
from agentmonitor.adapters.persistence.capacity.sqlite.budget_retention import (
    SqliteBudgetRetentionV1,
)
from agentmonitor.composition.budget_retention import (
    build_budget_retention,
    build_budget_retention_checkpoints,
)
from agentmonitor.contracts.capacity_retention_v1 import BudgetRetentionExportRecordV1
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.operations_v1 import OperationsParticipantRequestV1
from sqlalchemy.engine import Connection, RowMapping

from backend.tests.live.ollama.test_cloud_registry_revision_admission import (
    _private_real_copy,
)
from backend.tests.persistence.sqlite.migrations.test_m05_model_remainder import (
    migrate_revision,
)


def _retained_metadata(
    connection: Connection, row: RowMapping
) -> BudgetRetentionExportRecordV1:
    """Read genuine identity metadata without reconstructing every physical fact.

    The retention participant still validates full exports for every selected
    protected/purge candidate. This inventory only establishes latest identity.
    """
    from agentmonitor.adapters.persistence.capacity.sqlite.budget_repository import (
        _receipt,
        _view,
    )
    from agentmonitor.modules.capacity.domain.budget_codec import (
        decode_budget_provenance,
    )

    receipt_row = (
        connection.exec_driver_sql(
            "SELECT * FROM capacity_commit_receipt WHERE receipt_id=?",
            (row["receipt_id"],),
        )
        .mappings()
        .one()
    )
    return BudgetRetentionExportRecordV1(
        int(row["report_sequence"]),
        _view(row),
        decode_budget_provenance(str(row["canonical_provenance_json"])),
        _receipt(connection, receipt_row),
        OpaqueIdV1(str(row["receipt_id"])),
        OpaqueIdV1(str(row["provenance_id"])),
    )


def _prepared(
    tmp_path: Path,
    *,
    monetary: bool = False,
    source_database: Path | None = None,
) -> tuple[
    DatabaseRefV1,
    SqliteBudgetRetentionV1,
    budget_retention_checkpoint.FilesystemBudgetRetentionCheckpointV1,
    OperationsParticipantRequestV1,
    tuple[BudgetRetentionExportRecordV1, ...],
]:
    reference = _private_real_copy(tmp_path, source_database=source_database)
    migrate_revision(reference, "v1_0736", "migration_existing")
    checkpoints = build_budget_retention_checkpoints(tmp_path / "checkpoints")
    participant = build_budget_retention(reference, tmp_path / "checkpoints")
    assert isinstance(participant, SqliteBudgetRetentionV1)
    now = datetime.now(UTC)
    request = OperationsParticipantRequestV1(
        OpaqueIdV1("genuine-retention"),
        OpaqueIdV1("genuine-retention-correlation"),
        now + timedelta(minutes=10),
        1,
        now + timedelta(days=366),
        1,
        None,
        None,
        None,
        None,
    )
    from agentmonitor.modules.capacity.domain.budget_retention import retention_cursor

    positions: tuple[int, ...] = ()
    snapshot = 0
    if monetary:
        with open_sqlite_database(reference, "runtime_read_only") as handle:
            with handle.connect() as connection:
                snapshot = int(
                    connection.exec_driver_sql(
                        "SELECT COALESCE(MAX(report_sequence),0) "
                        "FROM capacity_budget_report"
                    ).scalar_one()
                )
                positions = tuple(
                    int(value)
                    for value in connection.exec_driver_sql(
                        "SELECT report_sequence FROM capacity_budget_report "
                        "WHERE json_array_length("
                        "canonical_report_json,'$.cost_buckets')>0 "
                        "ORDER BY report_sequence LIMIT 1000"
                    ).scalars()
                )
        # Bound the search for one real example, not the database's total size.
        assert positions, "genuine_monetary_candidate_required"
    for index in range(len(positions) if monetary else 100):
        if monetary:
            request = replace(
                request,
                cursor=retention_cursor(request, snapshot, positions[index] - 1),
            )
        preview = participant.preview_expired(request)
        bound = replace(request, preview_digest=preview.digest)
        records = participant.query_export_records(bound)
        if records and (not monetary or records[0].report.report.cost_buckets):
            break
        if monetary:
            continue
        assert preview.next_cursor is not None, "genuine_expirable_report_required"
        request = replace(request, cursor=preview.next_cursor)
    else:
        raise AssertionError("genuine_retention_scan_bound")
    assert len(records) == 1
    return reference, participant, checkpoints, bound, records


def test_genuine_retention_preserves_receipt_and_checkpoint(tmp_path: Path) -> None:
    from agentmonitor.adapters.persistence.capacity.sqlite.budget_repository import (
        SqliteBudgetReportRepositoryV1,
        _receipt_report,
    )
    from agentmonitor.modules.capacity.domain.budget_codec import (
        encode_budget_provenance,
    )

    reference, participant, checkpoints, bound, records = _prepared(tmp_path)
    record = records[0]
    from agentmonitor.modules.capacity.domain.budget_retention_codec import (
        BudgetRetentionCodecV1,
    )

    codec = BudgetRetentionCodecV1()
    assert codec.decode(codec.encode(record)) == record
    repo = SqliteBudgetReportRepositoryV1(reference)
    before = repo.get_commit_status(record.receipt.run_id, record.receipt.capability_id)
    assert before.receipt == record.receipt
    checkpoint = checkpoints.store(bound, records)
    purge = replace(bound, checkpoint_id=checkpoint)
    result = participant.purge_expired(purge)
    assert result.count == 1 and result.outcome in {"complete", "partial"}
    assert participant.purge_expired(purge) == result
    assert checkpoints.verify(purge, records)
    assert (
        repo.get_report(
            record.report.report.subject.account_id, record.report.report_id
        )
        is None
    )
    assert (
        repo.get_commit_status(record.receipt.run_id, record.receipt.capability_id)
        == before
    )
    with open_sqlite_database(reference, "runtime_read_only") as handle:
        with handle.connect() as connection:
            assert connection.exec_driver_sql("PRAGMA foreign_key_check").all() == []
            assert _receipt_report(connection, record.receipt_id.value) == (
                record.report.report_id.value,
                encode_budget_provenance(record.provenance),
            )
            for fact in record.receipt.fact_ids:
                assert (
                    connection.exec_driver_sql(
                        "SELECT observation_id FROM capacity_budget_observation "
                        "WHERE observation_id=? UNION ALL SELECT bucket_id "
                        "FROM capacity_usage_bucket WHERE bucket_id=?",
                        (fact.value, fact.value),
                    ).first()
                    is None
                )


def test_changed_checkpoint_cannot_purge_genuine_facts(tmp_path: Path) -> None:
    reference, participant, checkpoints, bound, records = _prepared(tmp_path)
    checkpoint = checkpoints.store(bound, records)
    files = tuple((tmp_path / "checkpoints").glob("*.zip"))
    assert len(files) == 1
    # Corrupt only the real test-created private artifact; never provider input.
    original = files[0].read_bytes()
    files[0].write_bytes(b"invalid checkpoint")
    with pytest.raises(ValueError, match="budget_(retention_checkpoint|checkpoint)_"):
        participant.purge_expired(replace(bound, checkpoint_id=checkpoint))
    with open_sqlite_database(reference, "runtime_read_only") as handle:
        with handle.connect() as connection:
            assert (
                connection.exec_driver_sql(
                    "SELECT 1 FROM capacity_budget_report WHERE report_id=?",
                    (records[0].report.report_id.value,),
                ).first()
                is not None
            )
            assert (
                connection.exec_driver_sql(
                    "SELECT COUNT(*) FROM capacity_budget_expired_report"
                ).scalar_one()
                == 0
            )
    files[0].write_bytes(original)
    assert (
        participant.purge_expired(replace(bound, checkpoint_id=checkpoint)).count == 1
    )


def test_genuine_monetary_bundle_expires_with_original_receipt(tmp_path: Path) -> None:
    from agentmonitor.adapters.persistence.capacity.sqlite.budget_repository import (
        SqliteBudgetReportRepositoryV1,
    )

    reference, participant, checkpoints, bound, records = _prepared(
        tmp_path, monetary=True
    )
    record = records[0]
    report = record.report.report
    assert report.cost_buckets and report.usage_buckets, (
        "genuine_money_and_usage_required"
    )
    assert any(
        bucket.amount.amount.coefficient != "0" for bucket in report.cost_buckets
    ), "genuine_nonzero_money_required"
    repository = SqliteBudgetReportRepositoryV1(reference)
    before = repository.get_commit_status(
        record.receipt.run_id, record.receipt.capability_id
    )
    checkpoint = checkpoints.store(bound, records)
    assert (
        participant.purge_expired(replace(bound, checkpoint_id=checkpoint)).count == 1
    )
    assert (
        repository.get_commit_status(
            record.receipt.run_id, record.receipt.capability_id
        )
        == before
    )
    assert checkpoints.verify(replace(bound, checkpoint_id=checkpoint), records)
    with open_sqlite_database(reference, "runtime_read_only") as handle:
        with handle.connect() as connection:
            for index, fact in enumerate(record.receipt.fact_ids):
                if index < len(report.cost_buckets):
                    assert (
                        connection.exec_driver_sql(
                            "SELECT 1 FROM capacity_budget_observation "
                            "WHERE observation_id=? UNION ALL SELECT 1 "
                            "FROM capacity_budget_signed_cost_measure "
                            "WHERE observation_id=?",
                            (fact.value, fact.value),
                        ).first()
                        is None
                    )
                else:
                    assert (
                        connection.exec_driver_sql(
                            "SELECT 1 FROM capacity_usage_bucket WHERE bucket_id=? "
                            "UNION ALL SELECT 1 FROM capacity_usage_measure "
                            "WHERE bucket_id=?",
                            (fact.value, fact.value),
                        ).first()
                        is None
                    )
            assert (
                connection.exec_driver_sql(
                    "SELECT 1 FROM capacity_observation_provenance "
                    "WHERE provenance_id=?",
                    (record.provenance_id.value,),
                ).first()
                is not None
            )
            assert connection.exec_driver_sql("PRAGMA foreign_key_check").all() == []


def test_real_latest_contexts_survive_without_preserving_every_historical_window(
    tmp_path: Path,
) -> None:
    from agentmonitor.composition.budget_retention import is_live_budget_context
    from agentmonitor.contracts.capacity_v1 import BudgetReportViewV1
    from agentmonitor.modules.capacity.domain.budget_retention import retention_cursor

    reference, participant, _, bound, _ = _prepared(tmp_path)
    contexts: dict[tuple[object, ...], list[BudgetReportViewV1]] = {}
    sequences: dict[OpaqueIdV1, int] = {}
    with open_sqlite_database(reference, "runtime_read_only") as handle:
        with handle.connect() as connection:
            # This closed private snapshot is finite. Stream its full inventory:
            # a prefix cannot establish which report is latest in each context.
            rows = connection.exec_driver_sql(
                "SELECT * FROM capacity_budget_report ORDER BY report_sequence"
            ).mappings()
            for row in rows:
                record = _retained_metadata(connection, row)
                sequences[record.report.report_id] = record.report_sequence
                if not is_live_budget_context(connection, record):
                    continue
                report = record.report.report
                lineage = (
                    (report.binding_id, report.binding_generation)
                    if report.scope_evidence == "unresolved"
                    else None
                )
                key = (
                    report.subject,
                    report.scope_id,
                    report.scope_generation,
                    lineage,
                    report.source_id,
                    report.source_category,
                    report.cost_basis,
                    report.grouping,
                    report.currency,
                    report.requested_period.end - report.requested_period.start,
                )
                contexts.setdefault(key, []).append(record.report)
    protected: set[OpaqueIdV1] = set()
    widths: set[timedelta] = set()
    for reports in contexts.values():
        ordered = sorted(
            reports,
            key=lambda view: (
                view.report.collected_at,
                view.stored_at,
                view.report_id.value,
            ),
            reverse=True,
        )
        protected.add(ordered[0].report_id)
        widths.add(
            ordered[0].report.requested_period.end
            - ordered[0].report.requested_period.start
        )
        complete = next(
            (
                view
                for view in ordered
                if view.report.completeness == "complete"
                and view.report.covered_period == view.report.requested_period
            ),
            None,
        )
        if complete is not None:
            protected.add(complete.report_id)
    assert {timedelta(days=7), timedelta(days=30)} <= widths, (
        "genuine_both_range_contexts_required"
    )

    def probe(report_id: OpaqueIdV1) -> tuple[BudgetRetentionExportRecordV1, ...]:
        # Pin this actual sequence at both ends. Otherwise each protected-report
        # probe also reconstructs up to 99 unrelated later report bundles.
        sequence = sequences[report_id]
        request = replace(
            bound,
            cursor=retention_cursor(bound, sequence, sequence - 1),
            preview_digest=None,
        )
        preview = participant.preview_expired(request)
        return participant.query_export_records(
            replace(request, preview_digest=preview.digest)
        )

    # Every independently selected latest/latest-complete report must survive.
    for report_id in protected:
        assert not probe(report_id), "latest_live_context_must_survive"
    live_ids = {view.report_id for reports in contexts.values() for view in reports}
    for report_id in sorted(live_ids - protected, key=sequences.__getitem__):
        records = probe(report_id)
        if records:
            assert len(records) == 1 and records[0].report.report_id == report_id
            break
    else:
        raise AssertionError("genuine_superseded_live_context_required")


def test_unknown_project_metadata_cannot_be_dropped_by_retention(
    tmp_path: Path,
) -> None:
    reference, participant, checkpoints, bound, records = _prepared(tmp_path)
    record = records[0]
    checkpoint = checkpoints.store(bound, records)
    assert record.receipt.fact_ids
    table, column = (
        ("capacity_budget_observation", "observation_id")
        if record.report.report.cost_buckets
        else ("capacity_usage_bucket", "bucket_id")
    )
    # Corrupt only association metadata in the private copy. Amounts, provider
    # observations and timestamps are untouched; this is not a source fixture.
    with open_sqlite_database(reference, "runtime_read_write") as handle:
        with handle.connect() as connection:
            with connection.begin():
                connection.exec_driver_sql(
                    f"UPDATE {table} SET project_id=? WHERE {column}=?",
                    (
                        record.report.report.subject.resource_id.value,
                        record.receipt.fact_ids[0].value,
                    ),
                )
    with pytest.raises(ValueError, match="budget_retention_fact_shape_unknown"):
        participant.purge_expired(replace(bound, checkpoint_id=checkpoint))


@pytest.mark.parametrize("kind", ["current", "derivation"])
def test_new_genuine_fact_reference_invalidates_preview_before_purge(
    tmp_path: Path, kind: str
) -> None:
    source_database = None
    source_digest = None
    if kind == "derivation":
        # Retention safety requires an actual derived reference, not fresh
        # consumption today. Reuse the already selected genuine retention
        # snapshot; do not invent observations or change their original times.
        selected = os.environ.get("AGENTMONITOR_M7_RETENTION_PRIOR_DATABASE")
        assert selected, "genuine_retention_derivation_snapshot_required"
        source_database = Path(selected)
        assert source_database.is_absolute() and source_database.is_file()
        with source_database.open("rb") as stream:
            source_digest = hashlib.file_digest(stream, "sha256").hexdigest()
    reference, participant, checkpoints, bound, records = _prepared(
        tmp_path, source_database=source_database
    )
    record = records[0]
    assert record.receipt.fact_ids, "genuine_report_fact_required"
    checkpoint = checkpoints.store(bound, records)
    fact_id = record.receipt.fact_ids[0].value
    if kind == "derivation":
        _produce_genuine_derivation(reference)
    # An inconsistent-reference safety case, not an observed valid forecast.
    # Repoint an EXISTING genuine parent/reference in this private copy only.
    with open_sqlite_database(reference, "runtime_read_write") as handle:
        with handle.connect() as connection:
            with connection.begin():
                if kind == "current":
                    prior = connection.exec_driver_sql(
                        "SELECT projection_id,current_observation_id "
                        "FROM capacity_current_projection LIMIT 1"
                    ).one_or_none()
                    assert prior is not None, "genuine_current_reference_required"
                    connection.exec_driver_sql(
                        "UPDATE capacity_current_projection "
                        "SET current_observation_id=? "
                        "WHERE projection_id=?",
                        (fact_id, prior[0]),
                    )
                else:
                    prior = connection.exec_driver_sql(
                        "SELECT derivation_id,ordinal,input_id "
                        "FROM capacity_derivation_input LIMIT 1"
                    ).one_or_none()
                    assert prior is not None, "genuine_derivation_reference_required"
                    connection.exec_driver_sql(
                        "UPDATE capacity_derivation_input SET input_id=? "
                        "WHERE derivation_id=? AND ordinal=?",
                        (fact_id, prior[0], prior[1]),
                    )
    with pytest.raises(ValueError, match="budget_retention_preview_changed"):
        participant.purge_expired(replace(bound, checkpoint_id=checkpoint))
    after = participant.preview_expired(replace(bound, preview_digest=None))
    exports = participant.query_export_records(
        replace(bound, preview_digest=after.digest)
    )
    assert all(item.report.report_id != record.report.report_id for item in exports)
    with open_sqlite_database(reference, "runtime_read_write") as handle:
        with handle.connect() as connection:
            with connection.begin():
                assert (
                    connection.exec_driver_sql(
                        "SELECT 1 FROM capacity_budget_report WHERE report_id=?",
                        (record.report.report_id.value,),
                    ).first()
                    is not None
                )
                if kind == "current":
                    connection.exec_driver_sql(
                        "UPDATE capacity_current_projection "
                        "SET current_observation_id=? "
                        "WHERE projection_id=?",
                        (prior[1], prior[0]),
                    )
                else:
                    connection.exec_driver_sql(
                        "UPDATE capacity_derivation_input SET input_id=? "
                        "WHERE derivation_id=? AND ordinal=?",
                        (prior[2], prior[0], prior[1]),
                    )
    assert (
        participant.purge_expired(replace(bound, checkpoint_id=checkpoint)).count == 1
    )
    if source_database is not None:
        with source_database.open("rb") as stream:
            assert hashlib.file_digest(stream, "sha256").hexdigest() == source_digest


def _produce_genuine_derivation(reference: DatabaseRefV1) -> None:
    """Use the existing production forecast on its genuine retained snapshot."""
    from agentmonitor.adapters.persistence.capacity.sqlite.current_repository import (
        SqliteCurrentCapacityRepositoryV1,
    )
    from agentmonitor.adapters.persistence.capacity.sqlite.repository import (
        SqliteCapacityRepositoryV1,
    )
    from agentmonitor.contracts.capacity_v1 import CapacityForecastQueryV1
    from agentmonitor.modules.capacity.application.queries import (
        ListCapacityForecastsV1,
    )

    with open_sqlite_database(reference, "runtime_read_only") as handle:
        with handle.connect() as connection:
            if (
                connection.exec_driver_sql(
                    "SELECT 1 FROM capacity_derivation_input LIMIT 1"
                ).first()
                is not None
            ):
                return
            candidates = connection.exec_driver_sql(
                "SELECT p.account_id,p.resource_id,p.projection_id,o.stored_at,"
                "o.observation_id FROM capacity_current_projection p "
                "JOIN capacity_quota_observation o "
                "ON o.observation_id=p.current_observation_id "
                "WHERE p.provider_key='codex' AND p.projection_kind='quota' "
                "ORDER BY p.projection_id LIMIT 32"
            ).all()
    forecasts = ListCapacityForecastsV1(SqliteCapacityRepositoryV1(reference))
    for account, resource, projection, stored_at, observation in candidates:
        as_of = datetime.fromisoformat(str(stored_at))
        page = forecasts(
            CapacityForecastQueryV1(
                OpaqueIdV1(str(account)),
                OpaqueIdV1(str(resource)),
                OpaqueIdV1(str(projection)),
                as_of,
                1,
            )
        )
        if any(
            item.burn_rate is not None
            and item.input_observation_ids
            and item.input_observation_ids[-1].value == observation
            for item in page.items
        ):
            SqliteCurrentCapacityRepositoryV1(reference).refresh_current_projections(
                as_of, None, 32
            )
            with open_sqlite_database(reference, "runtime_read_only") as handle:
                with handle.connect() as connection:
                    assert (
                        connection.exec_driver_sql(
                            "SELECT COUNT(*) FROM capacity_derivation_input"
                        ).scalar_one()
                        > 0
                    ), "genuine_derivation_reference_required"
                    assert (
                        connection.exec_driver_sql(
                            "SELECT 1 FROM capacity_derivation_input d "
                            "LEFT JOIN capacity_quota_observation o "
                            "ON o.observation_id=d.input_id "
                            "WHERE d.input_kind='quota_observation' AND "
                            "(o.observation_id IS NULL "
                            "OR d.input_digest<>o.payload_digest "
                            "OR d.semantic_time<>o.observed_at) LIMIT 1"
                        ).first()
                        is None
                    ), "genuine_derivation_input_mismatch"
            return
    raise AssertionError("genuine_qualifying_forecast_required")
