"""Pure source-policy routing; no repository double or fabricated boundary."""

from collections.abc import Callable
from dataclasses import replace

import pytest
from agentmonitor.contracts.capacity_v1 import BudgetReportViewV1
from agentmonitor.contracts.common_provenance_v1 import ObservationProvenanceV1

from backend.tests.adapters.providers.claude.anthropic_api import (
    test_anthropic_budget_source_evidence_policy as anthropic,
)
from backend.tests.adapters.providers.codex.openai_api import (
    test_openai_budget_source_evidence_policy as openai,
)
from backend.tests.adapters.providers.ollama.api import (
    test_budget_source_evidence_policy as ollama,
)


@pytest.mark.parametrize(
    "factory,policy",
    [
        (anthropic._inputs, "anthropic_cost_daily_snapshot_v1"),
        (openai._inputs, "openai_cost_daily_snapshot_v1"),
        (ollama._inputs, "ollama_usage_daily_snapshot_v1"),
    ],
)
def test_each_reviewed_source_keeps_its_own_policy(
    factory: Callable[[], tuple[BudgetReportViewV1, ObservationProvenanceV1]],
    policy: str,
) -> None:
    from agentmonitor.composition.budget_analysis import resolve_report_source_evidence

    view, provenance = factory()
    evidence = resolve_report_source_evidence(view, provenance)
    assert evidence is not None
    assert evidence.policy_id == policy
    assert evidence.report_id == view.report_id
    assert evidence.cost_freshness_deadline is None
    assert (
        resolve_report_source_evidence(
            view, replace(provenance, provider_key="unreviewed")
        )
        is None
    )


def test_unknown_provider_cannot_fall_through_to_another_source() -> None:
    from agentmonitor.composition.budget_analysis import resolve_report_source_evidence

    view, provenance = ollama._inputs()
    unknown = replace(
        view,
        report=replace(
            view.report, subject=replace(view.report.subject, provider_key="unreviewed")
        ),
    )
    assert resolve_report_source_evidence(unknown, provenance) is None
