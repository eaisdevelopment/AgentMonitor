"""Combine real stored cooldowns without collecting or changing owner state.

An explicitly selected genuine snapshot may be queried at its captured time.
That is a query of retained metadata, not a claim of current eligibility.
"""

import hashlib
import os
import shutil
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from agentmonitor.adapters.persistence._shared.sqlite.core.policy import DatabaseRefV1
from agentmonitor.adapters.persistence.collection_control.sqlite import (
    ollama_cloud_admission as cloud_admission,
)
from agentmonitor.adapters.persistence.collection_control.sqlite.repository import (
    SqliteCollectionRepositoryV1,
)
from agentmonitor.adapters.persistence.registry.sqlite.credential_bindings import (
    SqliteCloudCredentialRegistryV1,
)
from agentmonitor.adapters.persistence.registry.sqlite.repository import (
    SqliteRegistryRepositoryV1,
)
from agentmonitor.adapters.providers.ollama.api.policy import completed_period
from agentmonitor.composition.cloud_usage_actions import CloudUsageActionsV1
from agentmonitor.composition.ollama_usage_run import build_ollama_usage_run
from agentmonitor.contracts.collection_control_v1 import CloudBudgetReportContextV1
from agentmonitor.contracts.common_v1 import OpaqueIdV1


def _digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def test_real_eligibility_reports_later_context_budget_boundary(
    tmp_path: Path,
) -> None:
    source_name = os.environ.get("AGENTMONITOR_M7_ELIGIBILITY_DATABASE")
    selected_time = os.environ.get("AGENTMONITOR_M7_ELIGIBILITY_AS_OF")
    assert (source_name is None) == (selected_time is None), (
        "eligibility_snapshot_and_capture_time_required_together"
    )
    source = Path(source_name or "/home/dev/.local/share/agentmonitor/agentmonitor.db")
    assert source.is_absolute() and source.is_file()
    as_of = (
        datetime.now(UTC)
        if selected_time is None
        else datetime.fromisoformat(selected_time)
    )
    assert as_of.utcoffset() == UTC.utcoffset(as_of)
    root = tmp_path / "private"
    root.mkdir(mode=0o700)
    target = root / "agentmonitor.db"
    os.close(os.open(target, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600))
    try:
        with sqlite3.connect(f"file:{source}?mode=ro", uri=True) as original:
            with sqlite3.connect(target) as copied:
                original.backup(copied)
        before = _digest(target)
        reference = DatabaseRefV1(target, root)
        registry = SqliteRegistryRepositoryV1(reference)
        cloud = SqliteCloudCredentialRegistryV1(reference)
        runs = SqliteCollectionRepositoryV1(reference)
        gate = cloud_admission.SqliteOllamaCloudAdmissionRepositoryV1(reference)
        actions = CloudUsageActionsV1(reference)
        state, shared_boundary = gate.read_usage_gate_status(as_of)
        assert state in {"busy", "not_due"} and shared_boundary is not None, (
            "genuine_shared_cooldown_evidence_required"
        )
        later_contexts = 0
        checked = 0
        ranges: tuple[Literal["7d", "30d"], ...] = ("7d", "30d")
        for account in registry.list_accounts("ollama", 100):
            if (
                account.lifecycle != "active"
                or not account.is_effective_monitoring_enabled
            ):
                continue
            graph = cloud.read_monitoring_target(account.account_id)
            if graph is None or graph.lifecycle != "active":
                continue
            service = cloud.read_active_access_target(graph.access_target_id)
            if service is None or service.lifecycle != "active":
                continue
            for range_key in ranges:
                period = completed_period(as_of, range_key)
                context = CloudBudgetReportContextV1(
                    "self", range_key, period.start, period.end
                )
                sample = build_ollama_usage_run(
                    graph=graph,
                    service=service,
                    context=context,
                    registry_revision=account.registry_revision,
                    scheduler_instance_id=OpaqueIdV1("eligibility-read"),
                    run_id=OpaqueIdV1("eligibility-read"),
                    request_id=OpaqueIdV1("eligibility-read"),
                    requested_at=as_of,
                )
                budget_boundary = runs.get_budget_next_allowed_at(
                    sample.budget_scope_digest, "request", "count", as_of
                )
                expected = (
                    shared_boundary
                    if budget_boundary is None
                    else max(shared_boundary, budget_boundary)
                )
                actual = actions.eligibility(
                    account.account_id, graph.resource_id, context, as_of
                )
                assert actual is not None
                assert actual.account_id == account.account_id
                assert actual.resource_id == graph.resource_id
                assert actual.report_context == context
                assert actual.checked_at == as_of
                assert actual.reason_code == "cloud_usage_rate_limited"
                assert actual.can_collect is False
                assert actual.next_allowed_at == expected, (
                    "eligibility_hides_later_context_budget"
                )
                checked += 1
                if budget_boundary is not None and budget_boundary > shared_boundary:
                    later_contexts += 1
        assert later_contexts > 0, "genuine_later_context_budget_evidence_required"
        assert _digest(target) == before, "eligibility_changed_stored_metadata"
        print(
            "M7 ELIGIBILITY COOLDOWN: "
            f"contexts={checked} later_budget_contexts={later_contexts}; "
            "provider_requests=0; metadata_unchanged=true"
        )
    finally:
        shutil.rmtree(root)
