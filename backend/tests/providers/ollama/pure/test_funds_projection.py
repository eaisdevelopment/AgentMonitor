"""M7-MATH-07/08: pure stored-domain DTO mapping, never provider responses."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from agentmonitor.adapters.providers.ollama.api import funds_projection
from agentmonitor.contracts.capacity_v1 import (
    CapacityObservationProvenanceViewV1,
    CapacitySubjectV2,
    ExactMetricFieldV1,
    QuotaWindowViewV2,
)
from agentmonitor.contracts.common_quantity_v1 import ExactQuantityV1
from agentmonitor.contracts.common_v1 import FieldAvailabilityV1, OpaqueIdV1
from agentmonitor.contracts.registry_v1 import ProviderTargetRefV1

NOW = datetime(2026, 11, 11, tzinfo=UTC)


def _amount(value: str) -> ExactMetricFieldV1:
    return ExactMetricFieldV1(
        FieldAvailabilityV1("available"),
        ExactQuantityV1.from_decimal(Decimal(value), unit="usd"),
        "exact",
        "confirmed",
        "provider_reported",
        None,
    )


def _unknown() -> ExactMetricFieldV1:
    return ExactMetricFieldV1(
        FieldAvailabilityV1("unknown"),
        None,
        "unknown",
        "unknown",
        "unknown",
        "source_value_unknown",
    )


def _window() -> QuotaWindowViewV2:
    return QuotaWindowViewV2(
        window_id=OpaqueIdV1("pure-window"),
        subject=CapacitySubjectV2(
            "ollama",
            ProviderTargetRefV1("cloud_service", OpaqueIdV1("amat_" + "a" * 32)),
            OpaqueIdV1("pure-account"),
            OpaqueIdV1("pure-resource"),
        ),
        window_key="ollama_included_credits",
        safe_label="Included credits",
        used=_unknown(),
        remaining=_amount("0.004"),
        limit=_amount("100"),
        remaining_ratio=_unknown(),
        provenance=CapacityObservationProvenanceViewV1(
            "subscription.quota",
            "1.0.0",
            "ollama",
            "1.0.0",
            "1.0.0",
            "ollama.cloud.balance.v1",
            "documented_api",
            "1.0.0",
            None,
            None,
            NOW + timedelta(minutes=15),
            "pure-freshness",
            "exact",
            "confirmed",
            "pure-reported",
            False,
            "pure-decision",
        ),
        freshness="fresh",
        current_observation_id=OpaqueIdV1("pure-observation"),
        collection_run_id=OpaqueIdV1("pure-run"),
        observed_at=NOW,
        collected_at=NOW,
        stored_at=NOW,
        is_constraining=False,
        reset_at=NOW + timedelta(days=1),
        reset_precision="exact",
        completeness="complete",
    )


@pytest.mark.parametrize(
    "amount", ["0", "0.004", "12345678901234567890123456789012345678.123456789"]
)
def test_included_money_is_exact_with_original_lineage(amount: str) -> None:
    window = replace(_window(), remaining=_amount(amount))
    result = funds_projection.project_funds(window, as_of=NOW)
    assert result is not None
    assert result.remaining.value is not None
    assert result.remaining.value.amount.as_decimal() == Decimal(amount)
    assert result.remaining.value.currency == "USD"
    assert result.remaining.precision == window.remaining.precision
    assert result.remaining.confidence == window.remaining.confidence
    assert result.remaining.value_kind == window.remaining.value_kind
    assert result.limit.value is not None
    assert result.limit.value.amount.as_decimal() == Decimal("100")
    assert result.kind == "included_credits"
    assert result.component_id == window.window_id
    assert result.subject == window.subject
    assert result.observation_id == window.current_observation_id
    assert result.collection_run_id == window.collection_run_id
    assert result.provenance == window.provenance
    assert (result.observed_at, result.collected_at, result.stored_at) == (
        NOW,
        NOW,
        NOW,
    )
    assert result.freshness == "fresh"
    assert result.completeness == "complete"
    assert result.is_constraining is False
    assert result.scope_evidence == "unresolved"
    assert result.period is None
    assert result.renewal_at == window.reset_at
    assert result.expires_at is None


def test_purchased_funds_do_not_gain_a_limit_period_or_renewal() -> None:
    window = replace(
        _window(),
        window_key="ollama_purchased_credits",
        limit=_unknown(),
    )
    result = funds_projection.project_funds(window, as_of=NOW)
    assert result is not None
    assert result.kind == "purchased_credits"
    assert result.limit.value is None
    assert result.limit.availability == window.limit.availability
    assert result.limit.reason_code == "source_value_unknown"
    assert result.renewal_at is None
    assert result.expires_at is None
    assert result.period is None
    assert result.is_constraining is False


def test_missing_balance_preserves_its_reason_and_unknown_metadata() -> None:
    field = replace(
        _unknown(),
        availability=FieldAvailabilityV1("withheld_or_denied"),
        reason_code="source_denied",
    )
    result = funds_projection.project_funds(
        replace(_window(), remaining=field), as_of=NOW
    )
    assert result is not None
    assert result.remaining.value is None
    assert result.remaining.availability == field.availability
    assert result.remaining.reason_code == "source_denied"
    assert (
        result.remaining.precision,
        result.remaining.confidence,
        result.remaining.value_kind,
    ) == ("unknown", "unknown", "unknown")


@pytest.mark.parametrize(
    "change", ["legacy", "provider", "source", "unit", "installation"]
)
def test_unrelated_or_nonmonetary_windows_are_not_funds(change: str) -> None:
    window = _window()
    if change == "legacy":
        window = replace(window, window_key="ollama_weekly")
    elif change == "provider":
        window = replace(window, subject=replace(window.subject, provider_key="codex"))
    elif change == "source":
        window = replace(
            window, provenance=replace(window.provenance, source_id="unadmitted-source")
        )
    elif change == "unit":
        assert window.remaining.value is not None
        window = replace(
            window,
            remaining=replace(
                window.remaining, value=replace(window.remaining.value, unit="percent")
            ),
        )
    else:
        window = replace(
            window,
            subject=replace(
                window.subject,
                provider_target=ProviderTargetRefV1(
                    "provider_installation", OpaqueIdV1("pure-installation")
                ),
            ),
        )
    assert funds_projection.project_funds(window, as_of=NOW) is None


@pytest.mark.parametrize("field", ["observed_at", "collected_at", "stored_at"])
def test_future_evidence_is_not_projected_into_an_earlier_query(field: str) -> None:
    future = NOW + timedelta(seconds=1)
    if field == "observed_at":
        window = replace(_window(), observed_at=future)
    elif field == "collected_at":
        window = replace(_window(), collected_at=future)
    else:
        window = replace(_window(), stored_at=future)
    assert funds_projection.project_funds(window, as_of=NOW) is None


def test_freshness_expires_at_deadline_without_discarding_last_amount() -> None:
    window = _window()
    result = funds_projection.project_funds(window, as_of=NOW + timedelta(minutes=15))
    assert result is not None
    assert result.freshness == "stale"
    assert result.remaining.value is not None
    assert result.remaining.value.amount.as_decimal() == Decimal("0.004")


def test_unknown_freshness_and_imprecise_renewal_are_not_promoted() -> None:
    window = replace(
        _window(),
        provenance=replace(_window().provenance, freshness_deadline=None),
        reset_precision="rounded",
    )
    result = funds_projection.project_funds(window, as_of=NOW)
    assert result is not None
    assert result.freshness == "freshness_unknown"
    assert result.renewal_at is None


def test_existing_conflict_and_partial_evidence_remain_visible() -> None:
    result = funds_projection.project_funds(
        replace(_window(), freshness="conflicted", completeness="partial"), as_of=NOW
    )
    assert result is not None
    assert result.freshness == "conflicted"
    assert result.completeness == "partial"


def test_query_requires_explicit_utc_time() -> None:
    with pytest.raises(ValueError, match="timestamp-must-be-aware-utc"):
        funds_projection.project_funds(_window(), as_of=NOW.replace(tzinfo=None))
