"""Receipt-only recovery policy uses pure DTOs, never replacement ports."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from typing import Any, cast

import pytest
from agentmonitor.contracts.collection_control_v1 import (
    BudgetCollectionCommitStatusV1,
    BudgetCollectionReceiptV1,
    BudgetCollectionRunViewV1,
    CollectionFailedV1,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.modules.collection_control.application.budget_executor import (
    reconcile_budget_receipt,
)
from agentmonitor.modules.collection_control.application.executor import (
    CollectionExecutionErrorV1,
)

NOW = datetime(2026, 11, 11, tzinfo=UTC)


def _run() -> BudgetCollectionRunViewV1:
    return BudgetCollectionRunViewV1(
        OpaqueIdV1("pure-run"),
        OpaqueIdV1("pure-schedule"),
        "claude",
        OpaqueIdV1("pure-account"),
        OpaqueIdV1("pure-resource"),
        "api.billing",
        "committing",
        "pure-source",
        "1.0.0",
        None,
        2,
        3,
        NOW,
        NOW,
        None,
        NOW + timedelta(seconds=30),
        None,
        "a" * 64,
        "succeeded",
        None,
        (),
        None,
    )


def _receipt() -> BudgetCollectionReceiptV1:
    return BudgetCollectionReceiptV1(
        _run().run_id,
        2,
        "api.billing",
        "budget.report.v1",
        "a" * 64,
        "capacity.budget",
        "1.0.0",
        OpaqueIdV1("pure-report"),
        (),
        NOW,
        1,
    )


def test_empty_report_recovery_returns_original_receipt_without_new_facts() -> None:
    receipt = _receipt()
    actual = reconcile_budget_receipt(
        _run(), BudgetCollectionCommitStatusV1("committed", receipt), NOW
    )
    assert actual is receipt
    assert receipt.fact_ids == ()


def test_missing_receipt_produces_interrupted_failure_without_retrying_source() -> None:
    actual = reconcile_budget_receipt(
        _run(),
        BudgetCollectionCommitStatusV1("not_committed", None),
        NOW,
        interruption_claimed=True,
    )
    assert isinstance(actual, CollectionFailedV1)
    assert actual.error_code == "collection_commit_interrupted"


@pytest.mark.parametrize("state", ["unavailable", "conflict"])
def test_unavailable_or_conflicting_receipt_cannot_finalize(state: Any) -> None:
    with pytest.raises(CollectionExecutionErrorV1):
        reconcile_budget_receipt(
            _run(), BudgetCollectionCommitStatusV1(state, None), NOW
        )


@pytest.mark.parametrize(
    "field,value",
    [
        ("run_id", OpaqueIdV1("other-run")),
        ("target_generation", 3),
        ("capability_id", "other"),
        ("payload_schema", "other"),
        ("payload_digest", "b" * 64),
    ],
)
def test_receipt_identity_cannot_be_substituted(field: str, value: object) -> None:
    receipt = replace(_receipt(), **cast(dict[str, Any], {field: value}))
    with pytest.raises(
        CollectionExecutionErrorV1, match="collection_commit_recovery_invalid"
    ):
        reconcile_budget_receipt(
            _run(), BudgetCollectionCommitStatusV1("committed", receipt), NOW
        )


def test_absent_receipt_under_live_owner_stays_committing_until_refenced() -> None:
    with pytest.raises(
        CollectionExecutionErrorV1, match="collection_commit_recovery_pending"
    ):
        reconcile_budget_receipt(
            _run(), BudgetCollectionCommitStatusV1("not_committed", None), NOW
        )
