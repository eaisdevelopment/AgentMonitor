"""Explain one authorized financial report through existing read-only ports."""

from dataclasses import replace
from datetime import datetime

from agentmonitor.contracts.budget_forecast_v1 import (
    BudgetForecastV1,
    BudgetObservedRateV1,
    BudgetSourceEvidencePortV1,
)
from agentmonitor.contracts.budget_query_v1 import (
    AccountBudgetFundsPortV1,
    BudgetSelectedReportPortV1,
)
from agentmonitor.contracts.capacity_v1 import BudgetPeriodV1
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.modules.capacity.domain.budget_daily_costs import daily_costs
from agentmonitor.modules.capacity.domain.budget_forecast import (
    BudgetForecastEvidence,
    forecast,
)


class GetBudgetForecastV1:
    def __init__(
        self,
        selected: BudgetSelectedReportPortV1,
        source_evidence: BudgetSourceEvidencePortV1,
        funds: AccountBudgetFundsPortV1,
    ) -> None:
        self._selected = selected
        self._source_evidence = source_evidence
        self._funds = funds

    def __call__(
        self,
        account_id: OpaqueIdV1,
        resource_id: OpaqueIdV1,
        report_id: OpaqueIdV1,
        *,
        period: BudgetPeriodV1,
        as_of: datetime,
    ) -> BudgetForecastV1 | None:
        selected = self._selected(
            account_id, resource_id, report_id, period=period, as_of=as_of
        )
        if selected is None:
            return None
        evidence = self._source_evidence(selected.report)
        if evidence is not None and evidence.report_id != report_id:
            raise ValueError("budget_source_evidence_context_invalid")
        daily = daily_costs(
            selected,
            disjoint_costs=evidence.disjoint_costs if evidence else False,
            zero_day_coverage=evidence.zero_day_coverage if evidence else False,
        )
        result = forecast(
            daily,
            evidence=BudgetForecastEvidence(
                corrections_resolved=evidence.corrections_resolved
                if evidence
                else False,
                cost_freshness_deadline=evidence.cost_freshness_deadline
                if evidence
                else None,
            ),
        )
        if evidence is None:
            result = replace(
                result, rate=None, rate_reason="source_semantics_unavailable"
            )
        funds = self._funds(account_id, as_of=as_of)
        components = tuple(
            c
            for c in funds.components
            if c.subject.account_id == account_id
            and c.subject.resource_id == resource_id
        )
        # The existing funds contract proves observed components, not their
        # financial scope epoch or allocation from this report's cost stream.
        # Do not feed guessed compatibility into the pure date calculation.
        if result.rate is not None:
            reason = (
                "funds_scope_unresolved"
                if any(c.scope_evidence == "unresolved" for c in components)
                else "fund_allocation_unknown"
                if components
                else funds.availability.reason_code
                if funds.availability.state == "unavailable"
                else "funds_unavailable"
            )
            result = replace(result, exhaustion_reason=reason)
        # Authorization/retention may change during the independent source/fund
        # reads. Revalidate the same immutable selection before returning it.
        if (
            self._selected(
                account_id, resource_id, report_id, period=period, as_of=as_of
            )
            != selected
        ):
            return None
        rate = result.rate
        return BudgetForecastV1(
            report=selected.report,
            as_of=as_of,
            rate=None
            if rate is None
            else BudgetObservedRateV1(
                rate.cost,
                rate.covered_seconds,
                rate.period,
                rate.input_report_ids,
                rate.input_bucket_keys,
                rate.day_count,
                rate.display,
                rate.display_rounding,
                rate.display_decimal_places,
            ),
            rate_reason=result.rate_reason,
            exhaustion_reason=result.exhaustion_reason,
            exhaustion_at=result.exhaustion_at,
            funds_observed_at=result.funds_observed_at,
            input_observation_ids=result.input_observation_ids,
            time_left_numerator=None
            if result.time_left_numerator is None
            else str(result.time_left_numerator),
            time_left_denominator=None
            if result.time_left_denominator is None
            else str(result.time_left_denominator),
            method_id=result.method_id,
            method_version=result.method_version,
            time_rounding=result.time_rounding,
            source_evidence=evidence,
        )
