"""Retained genuine openai report coverage; no fresh source or UI claims."""

import json
from dataclasses import asdict

import pytest

from backend.tests.live.budget_report_verification import (
    RetainedReportEvidence,
    inspect_retained_reports,
)
from backend.tests.live.ollama.test_cloud_registry_revision_admission import (
    _private_real_copy,
)


@pytest.fixture(scope="module")
def retained_evidence(
    tmp_path_factory: pytest.TempPathFactory,
) -> RetainedReportEvidence:
    reference = _private_real_copy(tmp_path_factory.mktemp("openai-retained"))
    return inspect_retained_reports(reference, "openai")


def test_openai_retained_reports_cover_reviewed_mappings_and_ranges(
    retained_evidence: RetainedReportEvidence,
) -> None:
    print(
        "M7_RETAINED_REPORT_EVIDENCE "
        + json.dumps(asdict(retained_evidence), sort_keys=True)
    )
    if retained_evidence.coverage_reason is not None:
        pytest.fail("m7_openai_" + retained_evidence.coverage_reason, pytrace=False)


def test_openai_retained_populated_mappings_are_distinct_from_empty_coverage(
    retained_evidence: RetainedReportEvidence,
) -> None:
    """Conditional populated proof; natural empty is not populated success."""
    if retained_evidence.coverage_reason is not None:
        pytest.fail("m7_openai_" + retained_evidence.coverage_reason, pytrace=False)
    if retained_evidence.missing_populated_mappings:
        pytest.fail("m7_openai_populated_mapping_evidence_absent", pytrace=False)
