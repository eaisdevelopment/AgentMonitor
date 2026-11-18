"""Observe two actual commits of one fresh report under its original live fence.

This test-owned decorator delegates every operation to the real SQLite sink.
It creates no report, receipt, lease, credential, source response or substitute
I/O result. Only the original in-memory request may be retried.
"""

from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
    DatabaseRefV1,
    open_sqlite_database,
)
from agentmonitor.adapters.persistence.capacity.sqlite.budget_repository import (
    SqliteBudgetReportRepositoryV1,
)
from agentmonitor.contracts.capacity_v1 import BudgetCollectionInputV1
from agentmonitor.contracts.collection_control_v1 import (
    BudgetCollectionCommitStatusV1,
    BudgetCollectionReceiptV1,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1


class BudgetCommitRetryWitness:
    def __init__(
        self,
        reference: DatabaseRefV1,
        repository: SqliteBudgetReportRepositoryV1,
        witness: dict[str, object],
    ) -> None:
        self._reference = reference
        self._repository = repository
        self._witness = witness

    def _run_counts(self, run_id: OpaqueIdV1) -> tuple[int, ...]:
        # M05-owned test inspection, scoped to this real run so unrelated
        # concurrent quota collection cannot invalidate the observation.
        tables = (
            "capacity_commit_receipt",
            "capacity_budget_observation",
            "capacity_usage_bucket",
        )
        with open_sqlite_database(self._reference, "runtime_read_only") as handle:
            with handle.connect() as connection:
                return tuple(
                    int(
                        connection.exec_driver_sql(
                            f"SELECT count(*) FROM {table} WHERE collection_run_id=?",
                            (run_id.value,),
                        ).scalar_one()
                    )
                    for table in tables
                )

    def commit(self, request: BudgetCollectionInputV1) -> BudgetCollectionReceiptV1:
        first = self._repository.commit(request)
        counts = self._run_counts(request.run_id)
        # The same production sink rechecks its original M02/M04/rate fence.
        # No lease reconstruction, report replacement or provider replay.
        second = self._repository.commit(request)
        reopened = SqliteBudgetReportRepositoryV1(self._reference).get_commit_status(
            request.run_id, request.capability_id
        )
        if (
            first != second
            or counts != self._run_counts(request.run_id)
            or reopened.state != "committed"
            or reopened.receipt != first
        ):
            raise ValueError("native_comparison_commit_retry_mismatch")
        self._witness["commit_retry"] = {
            "attempts": 2,
            "same_receipt": True,
            "same_run_fact_counts": True,
            "reopened_receipt_equal": True,
        }
        return first

    def get_commit_status(
        self, run_id: OpaqueIdV1, capability_id: str
    ) -> BudgetCollectionCommitStatusV1:
        return self._repository.get_commit_status(run_id, capability_id)
