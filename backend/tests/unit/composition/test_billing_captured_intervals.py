"""Pure captured request composition; no provider calls or boundary substitutes."""

from dataclasses import replace
from datetime import timedelta
from typing import Any, Literal

import pytest
from agentmonitor.adapters.providers.claude.anthropic_api.source import (
    AnthropicCostResultV1,
)
from agentmonitor.adapters.providers.codex.openai_api.source import OpenAICostResultV1
from agentmonitor.composition.billing_run import (
    anthropic_billing_outcome,
    anthropic_billing_request,
    build_anthropic_billing_run,
    normalize_anthropic_billing_outcome,
)
from agentmonitor.composition.openai_billing_run import (
    build_openai_billing_run,
    normalize_openai_billing_outcome,
    openai_billing_outcome,
    openai_billing_request,
)
from agentmonitor.contracts.collection_control_v1 import (
    BillingBudgetReportContextV1,
    BudgetCollectionRunAdmissionV1,
    BudgetCollectionRunAdmissionV2,
)

from backend.tests.contracts import test_anthropic_billing_run as anthropic
from backend.tests.contracts import test_openai_billing_run as openai

Provider = Literal["claude", "codex"]


def _context(days: Literal[7, 30], age: int = 0) -> BillingBudgetReportContextV1:
    end = anthropic.NOW.replace(hour=0) - timedelta(days=age)
    return BillingBudgetReportContextV1(
        "7d" if days == 7 else "30d", end - timedelta(days=days), end, "cost"
    )


def _build(provider: Provider, **changes: Any) -> BudgetCollectionRunAdmissionV1:
    fixture = anthropic if provider == "claude" else openai
    previous = fixture._admission()
    names = (
        "registry_revision",
        "scheduler_instance_id",
        "run_id",
        "schedule_id",
        "request_id",
        "retry_chain_id",
        "correlation_id",
        "causation_id",
        "trigger",
        "request_principal_id",
        "idempotency_key_digest",
        "requested_at",
        "deadline_at",
        "attempt_ordinal",
    )
    values = {name: getattr(previous, name) for name in names}
    values.update(target=fixture._target(), access_target=fixture._access_target())
    builder = (
        build_anthropic_billing_run
        if provider == "claude"
        else build_openai_billing_run
    )
    return builder(**(values | changes))


@pytest.mark.parametrize("provider", ["claude", "codex"])
@pytest.mark.parametrize("days", [7, 30])
@pytest.mark.parametrize("age", [0, 14])
def test_captured_interval_is_reconstructed_without_changing_request_time(
    provider: Provider, days: Literal[7, 30], age: int
) -> None:
    context = _context(days, age)
    admission = _build(provider, report_context=context)
    assert isinstance(admission, BudgetCollectionRunAdmissionV2)
    assert admission.report_context == context
    assert (
        admission.operation_family
        == f"billing.{'anthropic' if provider == 'claude' else 'openai'}.cost.{days}d"
    )
    request = (
        anthropic_billing_request if provider == "claude" else openai_billing_request
    )(admission)
    assert request.requested_at == anthropic.NOW
    assert request.period.start == context.interval_start
    assert request.period.end == context.interval_end


@pytest.mark.parametrize("provider", ["claude", "codex"])
def test_legacy_no_context_retains_v1_and_exact_request_identity(
    provider: Provider,
) -> None:
    admission = _build(provider)
    assert type(admission) is BudgetCollectionRunAdmissionV1
    assert (
        admission.request_digest
        == {
            "claude": (
                "91c1e7d132e2df33efe20cd1faad27b409f41008be7aa811f64d84e0d8e499ae"
            ),
            "codex": "111d52d7cba22620dacc9025c5c1d48cff413f88033b359d87ffe8457e5e468e",
        }[provider]
    )
    assert _build(provider, report_context=None) == admission


@pytest.mark.parametrize("provider", ["claude", "codex"])
def test_captured_context_binds_request_identity_and_rejects_tampering(
    provider: Provider,
) -> None:
    original = _build(provider, report_context=_context(7))
    older = _build(provider, report_context=_context(7, 1))
    wider = _build(provider, report_context=_context(30))
    assert (
        len(
            {
                original.request_digest,
                older.request_digest,
                wider.request_digest,
                _build(provider).request_digest,
            }
        )
        == 4
    )
    assert isinstance(original, BudgetCollectionRunAdmissionV2)
    reader = (
        anthropic_billing_request if provider == "claude" else openai_billing_request
    )
    with pytest.raises(ValueError):
        reader(replace(original, report_context=_context(7, 1)))
    with pytest.raises(ValueError):
        reader(replace(wider, operation_family=original.operation_family))


@pytest.mark.parametrize("provider", ["claude", "codex"])
@pytest.mark.parametrize("change", ["category", "grouping", "future"])
def test_unadmitted_context_is_rejected_before_run_is_returned(
    provider: Provider, change: str
) -> None:
    context = _context(7)
    if change == "category":
        context = replace(context, source_category="usage")
    elif change == "grouping":
        context = replace(context, grouping=("model",))
    else:
        context = _context(7, -1)
    with pytest.raises(ValueError):
        _build(provider, report_context=context)


@pytest.mark.parametrize("provider", ["claude", "codex"])
def test_both_admitted_ranges_are_in_worker_claim_allowlist(provider: Provider) -> None:
    from agentmonitor.composition.billing_collection import (
        billing_cost_operation_families,
    )

    assert billing_cost_operation_families(provider) == tuple(
        _build(provider, report_context=_context(days)).operation_family
        for days in (7, 30)
    )
    with pytest.raises(ValueError):
        billing_cost_operation_families("ollama")


@pytest.mark.parametrize("provider", ["claude", "codex"])
def test_normalization_cannot_commit_another_interval_under_captured_admission(
    provider: Provider,
) -> None:
    fixture = anthropic if provider == "claude" else openai
    legacy = fixture._admission()
    captured = _build(provider, report_context=_context(30))
    completed = legacy.requested_at + timedelta(seconds=2)
    if provider == "claude":
        result = AnthropicCostResultV1(
            "success", "anthropic_cost_success", fixture._report(), 1, 200
        )
        outcome = anthropic_billing_outcome(legacy, result, completed)
        with pytest.raises(ValueError):
            normalize_anthropic_billing_outcome(captured, outcome, completed)
    else:
        result_openai = OpenAICostResultV1(
            "success", "openai_cost_success", fixture._report(), 1, 200
        )
        outcome = openai_billing_outcome(legacy, result_openai, completed)
        with pytest.raises(ValueError):
            normalize_openai_billing_outcome(captured, outcome, completed)


@pytest.mark.parametrize("provider", ["claude", "codex"])
def test_explicit_manual_collection_does_not_require_automatic_monitoring(
    provider: Provider,
) -> None:
    from agentmonitor.contracts.common_v1 import OpaqueIdV1

    fixture = anthropic if provider == "claude" else openai
    target = fixture._target(purpose="verification")
    target = replace(
        target, connection=replace(target.connection, monitoring_preference="disabled")
    )
    admission = _build(
        provider,
        target=target,
        trigger="manual",
        request_principal_id=OpaqueIdV1("owner"),
        idempotency_key_digest="a" * 64,
        report_context=_context(30),
    )
    assert admission.billing_target.connection.monitoring_preference == "disabled"
    request = (
        anthropic_billing_request if provider == "claude" else openai_billing_request
    )(admission)
    assert request.period.start == _context(30).interval_start
