"""Pure projection of admitted stored Ollama credit windows into exact funds."""

from datetime import datetime, timedelta
from typing import Literal

from agentmonitor.contracts.budget_query_v1 import BudgetFundComponentV1
from agentmonitor.contracts.capacity_v1 import (
    ExactMetricFieldV1,
    ExactMoneyFieldV1,
    QuotaWindowViewV2,
)
from agentmonitor.contracts.common_quantity_v1 import ExactMoneyV1


def _money(field: ExactMetricFieldV1) -> ExactMoneyFieldV1:
    return ExactMoneyFieldV1(
        availability=field.availability,
        value=(
            ExactMoneyV1(field.value.amount, "USD") if field.value is not None else None
        ),
        precision=field.precision,
        confidence=field.confidence,
        value_kind=field.value_kind,
        reason_code=field.reason_code,
    )


def project_funds(
    window: QuotaWindowViewV2, *, as_of: datetime
) -> BudgetFundComponentV1 | None:
    """Map stored monetary components, excluding unsupported or future evidence.

    No scope identity, billing-period start, spending order or credit expiry is
    available in this view. A zero component cannot establish account depletion.
    """
    if as_of.utcoffset() != timedelta(0):
        raise ValueError("timestamp-must-be-aware-utc")
    if (
        window.subject.provider_key != "ollama"
        or window.subject.provider_target.target_kind != "cloud_service"
        or window.provenance.source_id != "ollama.cloud.balance.v1"
        or window.collected_at > as_of
        or window.stored_at > as_of
        or window.observed_at is not None
        and window.observed_at > as_of
        or any(
            field.value is not None and field.value.unit != "usd"
            for field in (window.remaining, window.limit)
        )
    ):
        return None
    kind: Literal["included_credits", "purchased_credits"]
    if window.window_key == "ollama_included_credits":
        kind = "included_credits"
    elif window.window_key == "ollama_purchased_credits":
        kind = "purchased_credits"
    else:
        return None
    freshness = window.freshness
    if freshness == "fresh":
        deadline = window.provenance.freshness_deadline
        if deadline is None:
            freshness = "freshness_unknown"
        elif as_of >= deadline:
            freshness = "stale"
    return BudgetFundComponentV1(
        subject=window.subject,
        component_id=window.window_id,
        kind=kind,
        remaining=_money(window.remaining),
        limit=_money(window.limit),
        period=None,
        renewal_at=(
            window.reset_at
            if kind == "included_credits" and window.reset_precision == "exact"
            else None
        ),
        expires_at=None,
        is_constraining=False,
        scope_evidence="unresolved",
        observation_id=window.current_observation_id,
        collection_run_id=window.collection_run_id,
        observed_at=window.observed_at,
        collected_at=window.collected_at,
        stored_at=window.stored_at,
        freshness=freshness,
        completeness=window.completeness,
        provenance=window.provenance,
    )
