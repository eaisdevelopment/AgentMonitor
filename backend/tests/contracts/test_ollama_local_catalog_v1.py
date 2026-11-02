"""Pure M03 local catalog contract safety and completeness semantics."""

from datetime import UTC, datetime

import pytest
from agentmonitor.contracts.ollama_local_catalog_v1 import (
    LocalCatalogItemV1,
    LocalCatalogSnapshotV1,
    LocalCatalogViewV1,
)


def test_empty_available_snapshot_is_a_real_empty_observation():
    value = LocalCatalogSnapshotV1(
        "available", "source_available", datetime.now(UTC), ()
    )
    assert value.items == ()


def test_unavailable_snapshot_cannot_claim_empty_results():
    with pytest.raises(ValueError, match="catalog_snapshot_state_invalid"):
        LocalCatalogSnapshotV1(
            "unavailable", "source_unavailable", datetime.now(UTC), ()
        )


def test_unavailable_snapshot_has_no_items():
    value = LocalCatalogSnapshotV1(
        "unavailable", "source_unavailable", datetime.now(UTC), None
    )
    assert value.items is None


def test_duplicate_model_names_are_rejected():
    item = LocalCatalogItemV1("model:tag")
    with pytest.raises(ValueError, match="catalog_snapshot_state_invalid"):
        LocalCatalogSnapshotV1(
            "available", "source_available", datetime.now(UTC), (item, item)
        )


@pytest.mark.parametrize("name", ["", "bad\nname", "x" * 257])
def test_model_names_are_bounded_printable_text(name):
    with pytest.raises(ValueError, match="catalog_model_name_invalid"):
        LocalCatalogItemV1(name)


def test_success_cannot_hide_a_failed_source():
    now = datetime.now(UTC)
    available = LocalCatalogSnapshotV1("available", "source_available", now, ())
    unavailable = LocalCatalogSnapshotV1("unavailable", "source_unavailable", now, None)
    with pytest.raises(ValueError, match="catalog_outcome_invalid"):
        LocalCatalogViewV1(
            "success",
            "0.24.0",
            "ollama.local.catalog.v1",
            now,
            available,
            unavailable,
        )


def test_unverified_version_requires_matching_source_reasons():
    now = datetime.now(UTC)
    unavailable = LocalCatalogSnapshotV1("unavailable", "source_unavailable", now, None)
    with pytest.raises(ValueError, match="catalog_outcome_invalid"):
        LocalCatalogViewV1(
            "unverified_provider_version",
            None,
            "ollama.local.catalog.v1",
            now,
            unavailable,
            unavailable,
        )


def test_catalog_requires_an_observation_time():
    now = datetime.now(UTC)
    unavailable = LocalCatalogSnapshotV1("unavailable", "source_unavailable", now, None)
    with pytest.raises(ValueError, match="catalog_outcome_invalid"):
        LocalCatalogViewV1(
            "provider_unavailable",
            None,
            "ollama.local.catalog.v1",
            None,
            unavailable,
            unavailable,
        )


def test_concurrent_read_reports_busy_without_claiming_success():
    now = datetime.now(UTC)
    busy = LocalCatalogSnapshotV1("unavailable", "collection_in_progress", None, None)
    value = LocalCatalogViewV1(
        "provider_unavailable", None, "ollama.local.catalog.v1", now, busy, busy
    )
    assert value.installed.reason == "collection_in_progress"


def test_deadline_exceeded_is_distinct_from_empty():
    now = datetime.now(UTC)
    timed_out = LocalCatalogSnapshotV1(
        "unavailable", "operation_deadline_exceeded", now, None
    )
    value = LocalCatalogViewV1(
        "deadline_exceeded", None, "ollama.local.catalog.v1", now, timed_out, timed_out
    )
    assert value.loaded.items is None
