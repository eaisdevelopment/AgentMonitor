"""Pure captured selection/normalization rules; no provider or persistence I/O."""

from dataclasses import replace
from datetime import timedelta
from typing import Any, Literal, cast

import pytest
from agentmonitor.adapters.providers.codex.openai_api.manifest import (
    USAGE_PROVIDER_VERSION,
)
from agentmonitor.adapters.providers.codex.openai_api.policy import (
    USAGE_SOURCE_ID,
    OpenAIUsageRequestV1,
)
from agentmonitor.adapters.providers.codex.openai_api.source import (
    OpenAICostResultV1,
    OpenAIUsageResultV1,
)
from agentmonitor.composition.billing_context import (
    billing_context_supported,
    billing_report_options,
    billing_source_operations,
)
from agentmonitor.composition.openai_billing_run import (
    normalize_openai_billing_outcome,
    openai_billing_outcome,
    openai_billing_request,
)
from agentmonitor.contracts.capacity_v1 import BudgetCollectionInputV1
from agentmonitor.contracts.collection_control_v1 import BillingBudgetReportContextV1

from backend.tests.contracts.test_openai_billing_run import (
    NOW,
    _build,
    _report,
    _target,
)

STANDARD = ((), ("project",), ("api_key_id",), ("model",))
SELECTIONS = (
    [("cost", group) for group in STANDARD[:3]]
    + [
        ("usage_" + category, group)
        for category in (
            "completions",
            "embeddings",
            "moderations",
            "images",
            "audio_speeches",
            "audio_transcriptions",
            "web_search_calls",
            "decisions",
        )
        for group in STANDARD
    ]
    + [
        ("usage_" + category, group)
        for category in ("code_interpreter_sessions", "vector_stores")
        for group in STANDARD[:2]
    ]
    + [("usage_file_search_calls", group) for group in STANDARD[:3]]
    + [
        ("usage_" + category + "_tokens", ("token_category",))
        for category in ("completions", "embeddings", "moderations", "decisions")
    ]
)


def _context(
    category: str, group: tuple[str, ...], days: int = 7
) -> BillingBudgetReportContextV1:
    end = NOW.replace(hour=0)
    return BillingBudgetReportContextV1(
        cast(Literal["7d", "30d"], f"{days}d"),
        end - timedelta(days=days),
        end,
        category,
        group,
    )


@pytest.mark.parametrize("category,group", SELECTIONS)
@pytest.mark.parametrize("days", [7, 30])
def test_all_reviewed_selections_roundtrip_exactly_without_a_separate_budget(
    category: str, group: tuple[str, ...], days: int
) -> None:
    context = _context(category, group, days)
    admission = _build(report_context=context)
    request = openai_billing_request(admission)
    usage = category != "cost"
    assert isinstance(request, OpenAIUsageRequestV1) == usage
    assert request.grouping == group
    assert request.period.start == context.interval_start
    assert request.period.end == context.interval_end
    if isinstance(request, OpenAIUsageRequestV1):
        assert request.category == category.removeprefix("usage_").removesuffix(
            "_tokens"
        )
    assert admission.capability_id == ("api.usage" if usage else "api.cost")
    assert admission.budget_scope_digest == _build().budget_scope_digest
    assert admission.budget_units == _build().budget_units == 20
    assert admission.collection_policy_version == "1.2.0"
    assert admission.operation_family == f"billing.openai.{category}.{days}d" + (
        "." + group[0] if group else ""
    )
    assert billing_context_supported("codex", context)
    assert (category, group) in {
        (item.source_category, item.grouping)
        for item in billing_report_options("codex")
    }


@pytest.mark.parametrize(
    "category,group",
    [
        ("cost", ("model",)),
        ("usage_unknown", ()),
        ("usage_images_tokens", ("token_category",)),
        ("usage_vector_stores", ("model",)),
        ("usage_completions", ("token_category",)),
        ("usage_completions_tokens", ()),
        ("usage_file_search_calls", ("model",)),
    ],
)
def test_unreviewed_selection_fails_before_request(
    category: str, group: tuple[str, ...]
) -> None:
    context = _context(category, group)
    assert not billing_context_supported("codex", context)
    with pytest.raises(ValueError, match="openai_billing_run_invalid"):
        _build(report_context=context)


def test_usage_has_its_own_source_mechanism_and_cannot_be_money() -> None:
    admission = _build(report_context=_context("usage_completions", ()))
    report = replace(
        _report(currency=None),
        source_id=USAGE_SOURCE_ID,
        source_category="usage_completions",
        cost_basis="not_applicable",
    )
    completed = NOW + timedelta(seconds=3)
    outcome = openai_billing_outcome(
        admission, OpenAIUsageResultV1("success", "ignored", report, 1, 200), completed
    )
    assert outcome.state == "success" and outcome.provenance is not None
    assert outcome.provenance.capability_id == "api.usage"
    assert outcome.provenance.mechanism_version == USAGE_PROVIDER_VERSION
    assert outcome.provenance.confidence_reason_code == "provider_reported_usage"
    assert outcome.provenance.provider_version is None
    commit = normalize_openai_billing_outcome(admission, outcome, completed)
    assert isinstance(commit, BudgetCollectionInputV1)
    assert commit.payload.currency is None and not commit.payload.empty_means_zero
    for wrong in (
        OpenAICostResultV1("success", "ignored", report, 1, 200),
        OpenAIUsageResultV1(
            "success",
            "ignored",
            replace(report, source_category="usage_images"),
            1,
            200,
        ),
    ):
        assert (
            openai_billing_outcome(admission, wrong, completed).state
            == "internal_adapter_error"
        )


def test_source_inventory_cannot_alias_cost_and_usage_operations() -> None:
    sources = billing_source_operations("codex")
    assert len(sources) == 2
    cost, usage = (set(item[2]) for item in sources)
    assert len(cost) == 6 and len(usage) == 86 and not cost & usage
    assert len(billing_report_options("codex")) == 46


def test_automatic_categories_have_distinct_intents_and_oldest_first_order() -> None:
    from agentmonitor.composition.billing_schedule import (
        billing_schedule_intent,
        due_billing_targets,
    )

    target = _target(purpose="monitoring")
    categories = tuple(category for category, group in SELECTIONS if not group)
    intents = [
        billing_schedule_intent(target, NOW, source_category=category)
        for category in categories
    ]
    assert len({item.schedule_id for item in intents}) == 12
    assert len({item.run_id for item in intents}) == 12
    now = NOW + timedelta(minutes=1)
    due = due_billing_targets(
        (
            (target, "7d", now, "cost"),
            (target, "30d", None, "usage_images"),
            (target, "7d", now - timedelta(hours=1), "usage_completions"),
        ),
        now,
    )
    assert [item.report_context.source_category for item in due] == [
        "usage_images",
        "usage_completions",
    ]


@pytest.mark.parametrize(
    "field,value",
    [
        ("source_id", "openai.organization.costs.v1"),
        ("capability_id", "api.cost"),
        ("provider_version", "openai-organization-costs-docs-2026-11-11"),
        ("operation_family", "billing.openai.cost.7d"),
    ],
)
def test_usage_admission_cannot_be_restored_as_cost(field: str, value: str) -> None:
    admission = _build(report_context=_context("usage_images", ()))
    changes: dict[str, Any] = {field: value}
    with pytest.raises(ValueError, match="openai_billing_run_invalid"):
        openai_billing_request(replace(admission, **changes))


@pytest.mark.parametrize("policy", ["1.0.0", "1.1.0", "1.2.0"])
@pytest.mark.parametrize("category", ["cost", "usage_images"])
def test_owner_replay_keeps_source_identity_across_policy_upgrade(
    policy: str, category: str
) -> None:
    from agentmonitor.composition.billing_actions import (
        _require_replay,
        billing_check_identifiers,
    )
    from agentmonitor.contracts.billing_actions_v1 import BillingCollectCommandV1
    from agentmonitor.contracts.common_v1 import OpaqueIdV1

    from backend.tests.contracts.test_billing_monitoring_proof import _evidence

    _, stored, _, _ = _evidence()
    target = _target()
    command = BillingCollectCommandV1(
        target.connection.account_id,
        target.connection.resource_id,
        1,
        target.connection.record_version,
        OpaqueIdV1("owner"),
        OpaqueIdV1("command"),
        NOW,
        _context(category, ()),
    )
    identifiers = billing_check_identifiers(command, collection_policy_version=policy)
    stored = replace(
        stored,
        run_id=identifiers.run_id,
        schedule_id=identifiers.schedule_id,
        provider_key="codex",
        account_id=target.connection.account_id,
        resource_id=target.connection.resource_id,
        source_id=USAGE_SOURCE_ID
        if category != "cost"
        else "openai.organization.costs.v1",
        capability_id="api.usage" if category != "cost" else "api.cost",
    )
    assert (
        _require_replay(command, billing_check_identifiers(command), stored, target)
        == stored
    )
    with pytest.raises(ValueError, match="billing_check_idempotency_conflict"):
        _require_replay(
            command, identifiers, replace(stored, source_id="different-source"), target
        )
