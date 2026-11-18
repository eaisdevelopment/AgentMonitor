"""Capture the existing default cost interval once, before durable admission."""

from datetime import datetime, timedelta
from typing import Literal, cast

from agentmonitor.contracts.billing_actions_v1 import BillingReportOptionV1
from agentmonitor.contracts.collection_control_v1 import BillingBudgetReportContextV1


def completed_billing_cost_context(
    requested_at: datetime,
    *,
    range_key: str = "7d",
    source_category: str = "cost",
) -> BillingBudgetReportContextV1:
    if range_key not in {"7d", "30d"}:
        raise ValueError("billing_context_range_invalid")
    end = requested_at.replace(hour=0, minute=0, second=0, microsecond=0)
    return BillingBudgetReportContextV1(
        cast(Literal["7d", "30d"], range_key),
        end - timedelta(days=7 if range_key == "7d" else 30),
        end,
        source_category,
    )


def billing_report_operation_families(provider_key: str) -> tuple[str, ...]:
    """Closed claim allowlist shared by legacy and captured cost admissions."""
    return tuple(
        operation
        for _, _, operations in billing_source_operations(provider_key)
        for operation in operations
    )


def billing_source_operations(
    provider_key: str,
) -> tuple[tuple[str, str, tuple[str, ...]], ...]:
    """Closed source-specific claim sets; all share their provider budget scope."""
    from agentmonitor.adapters.providers.claude.anthropic_api.policy import (
        ANALYTICS_REPORT_SELECTIONS,
        SOURCE_ID,
        USAGE_SOURCE_ID,
    )
    from agentmonitor.adapters.providers.codex.openai_api.policy import (
        ANALYTICS_REPORT_SELECTIONS as OPENAI_SELECTIONS,
    )
    from agentmonitor.adapters.providers.codex.openai_api.policy import (
        SOURCE_ID as OPENAI_SOURCE,
    )
    from agentmonitor.adapters.providers.codex.openai_api.policy import (
        USAGE_SOURCE_ID as OPENAI_USAGE_SOURCE,
    )

    if provider_key == "claude":
        return tuple(
            (
                capability,
                source,
                tuple(
                    f"billing.anthropic.{category}.{range_key}"
                    + ("." + grouping[0] if grouping else "")
                    for category, grouping in ANALYTICS_REPORT_SELECTIONS
                    if category.startswith(prefix)
                    for range_key in ("7d", "30d")
                ),
            )
            for capability, source, prefix in (
                ("api.cost", SOURCE_ID, "cost"),
                ("api.usage", USAGE_SOURCE_ID, "usage"),
            )
        )
    if provider_key == "codex":
        return (
            (
                "api.cost",
                OPENAI_SOURCE,
                tuple(
                    f"billing.openai.{category}.{range_key}"
                    + ("." + grouping[0] if grouping else "")
                    for category, grouping in OPENAI_SELECTIONS
                    if category == "cost"
                    for range_key in ("7d", "30d")
                ),
            ),
            (
                "api.usage",
                OPENAI_USAGE_SOURCE,
                tuple(
                    f"billing.openai.{category}.{range_key}"
                    + ("." + grouping[0] if grouping else "")
                    for category, grouping in OPENAI_SELECTIONS
                    if category.startswith("usage_")
                    for range_key in ("7d", "30d")
                ),
            ),
        )
    raise ValueError("billing_cost_provider_invalid")


def billing_context_supported(
    provider_key: str, context: BillingBudgetReportContextV1
) -> bool:
    from agentmonitor.adapters.providers.claude.anthropic_api.policy import (
        ANALYTICS_REPORT_SELECTIONS,
    )

    if provider_key == "claude":
        return (
            context.source_category,
            context.grouping,
        ) in ANALYTICS_REPORT_SELECTIONS
    from agentmonitor.adapters.providers.codex.openai_api.policy import (
        ANALYTICS_REPORT_SELECTIONS as OPENAI_SELECTIONS,
    )

    return (
        provider_key == "codex"
        and (context.source_category, context.grouping) in OPENAI_SELECTIONS
    )


def billing_report_options(provider_key: str) -> tuple[BillingReportOptionV1, ...]:
    """Public option metadata for the finite admitted report selections."""
    from agentmonitor.adapters.providers.claude.anthropic_api.policy import (
        ANALYTICS_REPORT_SELECTIONS,
        SOURCE_ID,
        USAGE_SOURCE_ID,
    )
    from agentmonitor.adapters.providers.codex.openai_api.policy import (
        ANALYTICS_REPORT_SELECTIONS as OPENAI_SELECTIONS,
    )
    from agentmonitor.adapters.providers.codex.openai_api.policy import (
        SOURCE_ID as OPENAI_SOURCE,
    )
    from agentmonitor.adapters.providers.codex.openai_api.policy import (
        USAGE_SOURCE_ID as OPENAI_USAGE_SOURCE,
    )

    if provider_key == "codex":
        return tuple(
            BillingReportOptionV1(
                OPENAI_SOURCE if category == "cost" else OPENAI_USAGE_SOURCE,
                category,
                grouping,
                (
                    "Reported costs"
                    if category == "cost"
                    else category.removeprefix("usage_")
                    .removesuffix("_tokens")
                    .replace("_", " ")
                    .capitalize()
                    + " usage"
                )
                + (
                    " by "
                    + {
                        "api_key_id": "API key ID",
                        "token_category": "token category",
                    }.get(grouping[0], grouping[0])
                    if grouping
                    else ""
                ),
            )
            for category, grouping in OPENAI_SELECTIONS
        )
    if provider_key != "claude":
        return ()
    names = {
        "cost": "Reported costs",
        "usage": "Usage quantities",
        "cost_tokens": "Token charges only — excludes other costs",
        "usage_tokens": "Token quantities by category",
    }
    dimensions = {
        "workspace": "workspace",
        "api_key_id": "API key ID",
        "model": "model",
    }
    return tuple(
        BillingReportOptionV1(
            USAGE_SOURCE_ID if category.startswith("usage") else SOURCE_ID,
            category,
            grouping,
            names[category]
            + (
                " by " + dimensions[grouping[0]]
                if grouping and grouping[0] in dimensions
                else ""
            ),
        )
        for category, grouping in ANALYTICS_REPORT_SELECTIONS
    )


def billing_scheduled_categories(provider_key: str) -> tuple[str, ...]:
    """Automate ungrouped categories only; owner-requested breakdowns share budget."""
    return tuple(
        item.source_category
        for item in billing_report_options(provider_key)
        if not item.grouping
    )
