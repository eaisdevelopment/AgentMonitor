"""Immutable report authorization policy; constructed values remain pure."""

from datetime import timedelta
from importlib import import_module

from agentmonitor.contracts.common_v1 import OpaqueIdV1

from backend.tests.capacity.pure.test_budget_report_selection import _report


def test_selected_report_never_substitutes_another_resource_period_or_future() -> None:
    module = import_module("agentmonitor.modules.capacity.domain.budget_account_spend")
    matches = getattr(module, "matches_selected_report", None)
    assert matches is not None, "immutable_budget_report_selection_missing"
    stored = _report(1, "0.10")
    args = {
        "account_id": stored.report.subject.account_id,
        "resource_id": stored.report.subject.resource_id,
        "report_id": stored.report_id,
        "period": stored.report.requested_period,
        "as_of": stored.stored_at,
    }
    assert matches(stored, **args)
    for changed in (
        {"account_id": OpaqueIdV1("different-account")},
        {"resource_id": OpaqueIdV1("different-resource")},
        {"report_id": OpaqueIdV1("different-report")},
        {"as_of": stored.stored_at - timedelta(microseconds=1)},
    ):
        assert not matches(stored, **(args | changed))
    assert not matches(None, **args)
