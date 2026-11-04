"""Pure acceptance-policy regression for the owner's local Ollama deferral."""

from dataclasses import replace

import pytest

from tools.automation.implementations.m6_direct_evidence import (
    DIRECT_EXECUTABLE_SELECTION_V1,
    BoundaryCheckV1,
    classify_direct_m6_evidence_v1,
)
from tools.automation.implementations.m6_exit_policy import (
    ACCEPTANCE_IDS,
    REQUIRED_CHECKS,
    STORY_IDS,
)
from tools.automation.test_m6_direct_evidence import _complete_facts


def test_local_scope_and_provider_commands_are_not_m6_prerequisites():
    assert set(ACCEPTANCE_IDS) == {
        "M6-A01",
        "M6-A03",
        "M6-A04",
        "M6-A05",
        "M6-A07",
        "M6-A08",
        "M6-A09",
        "M6-A10",
    }
    assert set(STORY_IDS) == {"ST-OLL-001", "ST-OLL-003", "ST-OLL-004", "ST-OLL-005"}
    assert "AUTO-M6-LOCAL-ADMIT" not in REQUIRED_CHECKS
    assert "local_inventory" not in dict(DIRECT_EXECUTABLE_SELECTION_V1)


@pytest.mark.parametrize("status", ("failed", "blocked", "not_run"))
def test_cloud_acceptance_is_independent_of_unavailable_local_ollama(status):
    unavailable = BoundaryCheckV1(status, 1, reason_code="local_ollama_deferred")
    facts = replace(
        _complete_facts(),
        local_admission=unavailable,
        local_inventory=unavailable,
        process_browser=unavailable,
        registered_local_installations=0,
        observed_local_installations=0,
        observed_model_hosts=0,
        model_host_evidence=(),
        process_observation_count=0,
    )
    outcomes = classify_direct_m6_evidence_v1(facts)
    assert not {"M6-A02", "M6-A06", "ST-OLL-002"}.intersection(outcomes)
    assert all(item.status == "passed" for item in outcomes.values())
    broken_cloud = classify_direct_m6_evidence_v1(
        replace(facts, source_security=unavailable)
    )
    assert broken_cloud["M6-A09"].status == status
    assert broken_cloud["ST-OLL-001"].status == status
    assert broken_cloud["ST-OLL-005"].status == status


def test_historical_catalog_cannot_be_reused_as_cloud_only_acceptance():
    from tools.automation.implementations.m6_exit_policy import validate_catalog_v1
    from tools.automation.test_m6_exit import _catalog

    catalog = _catalog()
    catalog["schema_version"] = "1.0.0"
    assert "m6_catalog_header_invalid" in validate_catalog_v1(catalog)
    catalog["schema_version"] = "1.1.0"
    catalog["acceptance_ids"].append("M6-A02")
    assert "m6_catalog_acceptance_invalid" in validate_catalog_v1(catalog)
