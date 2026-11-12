"""Retained genuine money over private SQLite copies; never a provider replay.

These checks exercise existing persistence and receipt reads. They do not claim
a fresh source call or retry a commit without its original live M04/rate lease.
Only the existing private-copy helper reads the owner's database, read-only.
"""

from datetime import UTC, datetime
from pathlib import Path

import pytest
from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
    DatabaseRefV1,
    open_sqlite_database,
)
from agentmonitor.adapters.persistence.capacity.sqlite.budget_repository import (
    SqliteBudgetReportRepositoryV1,
)
from agentmonitor.adapters.persistence.collection_control.sqlite.repository import (
    SqliteCollectionRepositoryV1,
)
from agentmonitor.adapters.persistence.registry.sqlite.repository import (
    SqliteRegistryRepositoryV1,
)
from agentmonitor.contracts.capacity_v1 import BudgetReportViewV1
from agentmonitor.contracts.collection_control_v1 import (
    BudgetCollectionReceiptV1,
    BudgetCollectionRunViewV1,
)
from agentmonitor.modules.capacity.application.budget_commit import (
    budget_report_payload_digest,
)
from agentmonitor.modules.capacity.application.budget_selected import (
    GetSelectedBudgetReportV1,
)
from agentmonitor.modules.capacity.domain.budget_codec import (
    decode_budget_provenance,
    utc_text,
)
from agentmonitor.modules.registry.application.accounts import GetAccountV1

from backend.tests.live.ollama.test_cloud_registry_revision_admission import (
    _private_real_copy,
)


def _require(condition: bool, code: str) -> None:
    # Failed comparisons must not dump entire real reports or private labels.
    if not condition:
        pytest.fail(code, pytrace=False)


def _monetary_report(
    reference: DatabaseRefV1,
) -> tuple[BudgetCollectionRunViewV1, BudgetReportViewV1]:
    runs = SqliteCollectionRepositoryV1(reference)
    reports = SqliteBudgetReportRepositoryV1(reference)
    for run in runs.list_runs("ollama", None, datetime.now(UTC), 500):
        if (
            not isinstance(run, BudgetCollectionRunViewV1)
            or run.source_id != "ollama.cloud.usage.v1"
            or run.state != "succeeded"
            or run.account_id is None
            or run.report_id is None
        ):
            continue
        stored = reports.get_report(run.account_id, run.report_id)
        if (
            stored is not None
            and stored.report.cost_buckets
            and stored.report.currency == "USD"
            and stored.report.completeness == "complete"
            and stored.report.covered_period == stored.report.requested_period
        ):
            return run, stored
    pytest.fail("genuine_complete_monetary_report_required", pytrace=False)


def _receipt(
    reference: DatabaseRefV1, run: BudgetCollectionRunViewV1
) -> BudgetCollectionReceiptV1:
    status = SqliteBudgetReportRepositoryV1(reference).get_commit_status(
        run.run_id, run.capability_id
    )
    _require(status.state == "committed", "genuine_monetary_receipt_missing")
    assert status.receipt is not None
    return status.receipt


def _check_normalized_storage(
    reference: DatabaseRefV1,
    stored: BudgetReportViewV1,
    receipt: BudgetCollectionReceiptV1,
) -> None:
    """Compare M05-owned normalized rows with their actual immutable report."""
    report = stored.report
    with open_sqlite_database(reference, "runtime_read_only") as database:
        with database.connect() as connection:
            costs = (
                connection.exec_driver_sql(
                    "SELECT l.observation_id,o.account_id,o.resource_id,"
                    "o.billing_start,o.billing_end,o.collected_at,o.stored_at,"
                    "o.collection_run_id,o.payload_digest,o.completeness,"
                    "m.coefficient,m.scale,m.currency,m.cost_kind "
                    "FROM capacity_budget_report r "
                    "JOIN capacity_commit_receipt_observation l "
                    "ON l.receipt_id=r.receipt_id AND l.observation_kind='budget' "
                    "JOIN capacity_budget_observation o "
                    "ON o.observation_id=l.observation_id "
                    "JOIN capacity_budget_signed_cost_measure m "
                    "ON m.observation_id=o.observation_id "
                    "WHERE r.report_id=? ORDER BY l.ordinal",
                    (stored.report_id.value,),
                )
                .mappings()
                .all()
            )
            usage = (
                connection.exec_driver_sql(
                    "SELECT l.observation_id,u.account_id,u.resource_id,"
                    "u.bucket_start,u.bucket_end,u.collected_at,u.stored_at,"
                    "u.collection_run_id,u.payload_digest,u.completeness,"
                    "m.coefficient,m.scale,m.unit "
                    "FROM capacity_budget_report r "
                    "JOIN capacity_commit_receipt_observation l "
                    "ON l.receipt_id=r.receipt_id AND l.observation_kind='usage' "
                    "JOIN capacity_usage_bucket u ON u.bucket_id=l.observation_id "
                    "JOIN capacity_usage_measure m ON m.bucket_id=u.bucket_id "
                    "WHERE r.report_id=? ORDER BY l.ordinal",
                    (stored.report_id.value,),
                )
                .mappings()
                .all()
            )
            provenance_text = connection.exec_driver_sql(
                "SELECT canonical_provenance_json FROM capacity_budget_report "
                "WHERE report_id=?",
                (stored.report_id.value,),
            ).scalar_one()
    _require(len(costs) == len(report.cost_buckets), "monetary_fact_count_changed")
    _require(len(usage) == len(report.usage_buckets), "usage_fact_count_changed")
    for row, cost in zip(costs, report.cost_buckets, strict=True):
        _require(
            (
                row["billing_start"],
                row["billing_end"],
                row["coefficient"],
                row["scale"],
                row["currency"],
                row["cost_kind"],
            )
            == (
                utc_text(cost.period.start),
                utc_text(cost.period.end),
                cost.amount.amount.coefficient,
                cost.amount.amount.scale,
                cost.amount.currency,
                cost.kind,
            ),
            "monetary_fact_precision_or_coverage_changed",
        )
    for row, bucket in zip(usage, report.usage_buckets, strict=True):
        _require(
            (
                row["bucket_start"],
                row["bucket_end"],
                row["coefficient"],
                row["scale"],
                row["unit"],
            )
            == (
                utc_text(bucket.period.start),
                utc_text(bucket.period.end),
                bucket.quantity.amount.coefficient,
                bucket.quantity.amount.scale,
                bucket.quantity.unit,
            ),
            "usage_fact_precision_or_coverage_changed",
        )
    for row in (*costs, *usage):
        _require(
            (
                row["account_id"],
                row["resource_id"],
                row["collected_at"],
                row["stored_at"],
                row["collection_run_id"],
                row["payload_digest"],
                row["completeness"],
            )
            == (
                report.subject.account_id.value,
                report.subject.resource_id.value,
                utc_text(report.collected_at),
                utc_text(stored.stored_at),
                receipt.run_id.value,
                receipt.payload_digest,
                report.completeness,
            ),
            "monetary_fact_lineage_changed",
        )
    _require(
        tuple(row["observation_id"] for row in (*costs, *usage))
        == tuple(identity.value for identity in receipt.fact_ids),
        "receipt_fact_lineage_changed",
    )
    provenance = decode_budget_provenance(str(provenance_text))
    _require(
        provenance.source_id == report.source_id
        and provenance.provider_key == report.subject.provider_key
        and provenance.collected_at == report.collected_at
        and provenance.capability_id == receipt.capability_id,
        "monetary_provenance_lineage_changed",
    )


def _counts(reference: DatabaseRefV1) -> tuple[int, ...]:
    # All tables belong to this test's M05 persistence boundary. Counts stay private.
    tables = (
        "capacity_budget_report",
        "capacity_commit_receipt",
        "capacity_commit_receipt_observation",
        "capacity_budget_observation",
        "capacity_budget_signed_cost_measure",
        "capacity_usage_bucket",
        "capacity_usage_measure",
    )
    with open_sqlite_database(reference, "runtime_read_only") as database:
        with database.connect() as connection:
            return tuple(
                int(
                    connection.exec_driver_sql(
                        f"SELECT count(*) FROM {table}"
                    ).scalar_one()
                )
                for table in tables
            )


def test_genuine_monetary_facts_coverage_and_lineage_survive_sqlite_reopen(
    tmp_path: Path,
) -> None:
    reference = _private_real_copy(tmp_path)
    run, stored = _monetary_report(reference)
    receipt = _receipt(reference, run)
    report = stored.report
    _require(
        receipt.report_id == stored.report_id
        and receipt.target_generation
        == report.binding_generation
        == run.target_generation
        and receipt.payload_digest
        == run.payload_digest
        == budget_report_payload_digest(report)
        and receipt.stored_at == stored.stored_at,
        "monetary_run_report_receipt_mismatch",
    )
    _check_normalized_storage(reference, stored, receipt)

    # All initial repository handles have closed; reopen the actual private file.
    reopened_ref = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    reopened = SqliteBudgetReportRepositoryV1(reopened_ref).get_report(
        report.subject.account_id, stored.report_id
    )
    _require(reopened == stored, "monetary_report_changed_on_reopen")
    _require(
        _receipt(reopened_ref, run) == receipt, "monetary_receipt_changed_on_reopen"
    )
    _check_normalized_storage(reopened_ref, stored, receipt)

    selected = GetSelectedBudgetReportV1(
        GetAccountV1(SqliteRegistryRepositoryV1(reopened_ref)),
        SqliteBudgetReportRepositoryV1(reopened_ref),
    )(
        report.subject.account_id,
        report.subject.resource_id,
        stored.report_id,
        period=report.requested_period,
        as_of=datetime.now(UTC),
    )
    _require(selected is not None, "monetary_selected_report_unavailable")
    assert selected is not None
    _require(selected.report == stored, "monetary_selected_context_changed")
    total = selected.reported_spend.total
    _require(total is not None, "genuine_monetary_total_unavailable")
    assert total is not None
    scale = max(bucket.amount.amount.scale for bucket in report.cost_buckets)
    _require(total.amount.scale <= scale, "monetary_total_scale_changed")
    _require(
        total.currency == report.currency
        and int(total.amount.coefficient) * 10 ** (scale - total.amount.scale)
        == sum(
            int(bucket.amount.amount.coefficient)
            * 10 ** (scale - bucket.amount.amount.scale)
            for bucket in report.cost_buckets
        ),
        "monetary_total_not_exact_source_sum",
    )


def test_genuine_receipt_recovery_reads_are_stable_without_duplicate_facts(
    tmp_path: Path,
) -> None:
    reference = _private_real_copy(tmp_path)
    run, stored = _monetary_report(reference)
    before = _counts(reference)
    expected = _receipt(reference, run)
    for _ in range(3):
        reopened = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
        _require(
            _receipt(reopened, run) == expected, "monetary_receipt_recovery_changed"
        )
        _require(
            SqliteBudgetReportRepositoryV1(reopened).get_report(
                stored.report.subject.account_id, stored.report_id
            )
            == stored,
            "monetary_recovery_report_changed",
        )
    _require(_counts(reference) == before, "monetary_recovery_changed_persisted_counts")
