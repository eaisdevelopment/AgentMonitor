"""Passive M7 billing binding replacement/removal witness; no credential values.

Uses retained genuine billing receipts and the existing runtime name-only store
reader. Never enters, copies, rotates, removes or tests a provider credential.
Command provenance, distinct key contents and provider revocation are not proved.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import resource
import subprocess
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from agentmonitor.adapters.persistence._shared.sqlite.core.policy import DatabaseRefV1
from agentmonitor.adapters.persistence.capacity.sqlite.budget_repository import (
    SqliteBudgetReportRepositoryV1,
)
from agentmonitor.adapters.persistence.collection_control.sqlite.repository import (
    SqliteCollectionRepositoryV1,
)
from agentmonitor.adapters.persistence.registry.sqlite.billing_connections import (
    SqliteBillingAccessRepositoryV1,
    SqliteBillingConnectionRepositoryV1,
)
from agentmonitor.adapters.persistence.registry.sqlite.credential_bindings import (
    SqliteCloudCredentialRegistryV1,
    SqliteCredentialBindingsV1,
)
from agentmonitor.adapters.persistence.registry.sqlite.credential_lock import (
    account_credential_lock,
)
from agentmonitor.adapters.persistence.registry.sqlite.repository import (
    SqliteRegistryRepositoryV1,
)
from agentmonitor.composition.billing_context import billing_source_operations
from agentmonitor.composition.ollama_credential_operator import (
    selected_env_from_service,
)
from agentmonitor.composition.ollama_env_store import (
    _managed_entries,
    _read_location_at,
)
from agentmonitor.composition.openai_billing_run import OPENAI_COST_AUTHORITY_ID_V1
from agentmonitor.contracts.collection_control_v1 import (
    BillingBudgetAuthorityV1,
    BudgetCollectionRunViewV1,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.registry_billing_v1 import BillingAccessTargetV1
from agentmonitor.contracts.registry_v1 import (
    AccountViewV1,
    CredentialBindingAggregateV1,
    CredentialBindingRecordV1,
)
from agentmonitor.modules.capacity.application.budget_commit import (
    budget_report_payload_digest,
)
from agentmonitor.modules.registry.application.accounts import ListAccountsV1
from agentmonitor.modules.registry.domain.credential_lock import credential_lock_name

from backend.tests.live.budget_report_verification import _same_binding
from tools.automation.implementations.auto_m7 import (
    CREDENTIAL_LIFECYCLE_CHECKS as CHECKS,
)
from tools.automation.implementations.m6_cutover import _verify_retained_baseline
from tools.automation.implementations.m6_recovery_interval import _identity

LIVE = Path("/home/dev/.local/share/agentmonitor")


class ObservationUnavailable(ValueError):
    """Closed failure code, never exception/credential/file content."""


def _require(condition: bool, reason: str) -> None:
    if not condition:
        raise ObservationUnavailable(reason)


def _bounded(deadline: float) -> None:
    _require(time.monotonic() < deadline, "m7_lifecycle_scan_limit")


@dataclass(frozen=True)
class Lineage:
    run_id: OpaqueIdV1
    report_id: OpaqueIdV1
    binding_id: OpaqueIdV1
    generation: int
    requested_at: datetime
    completed_at: datetime
    digest: str
    exact: tuple[object, ...]


@dataclass(frozen=True)
class Candidate:
    account: AccountViewV1
    target: BillingAccessTargetV1
    aggregate: CredentialBindingAggregateV1
    retired: CredentialBindingRecordV1
    previous: Lineage
    replacement: Lineage


def _same_scope(left: BillingAccessTargetV1, right: BillingAccessTargetV1) -> bool:
    a, b = left.connection, right.connection
    return (
        a.account_id,
        a.resource_id,
        a.provider_key,
        a.scope_generation,
        a.scope_id,
        a.scope_evidence,
    ) == (
        b.account_id,
        b.resource_id,
        b.provider_key,
        b.scope_generation,
        b.scope_id,
        b.scope_evidence,
    )


def _lineage(
    reference: DatabaseRefV1,
    run: BudgetCollectionRunViewV1,
    current: BillingAccessTargetV1,
) -> Lineage | None:
    if run.state != "succeeded" or run.report_id is None or run.account_id is None:
        return None
    repository = SqliteBudgetReportRepositoryV1(reference)
    stored = repository.get_report(run.account_id, run.report_id)
    if stored is None:  # Legitimate retained-history expiry is not proof.
        return None
    authority = SqliteCollectionRepositoryV1(reference).get_budget_target(run.run_id)
    if not isinstance(authority, BillingBudgetAuthorityV1) or not _same_scope(
        authority.target, current
    ):
        return None
    report = stored.report
    status = repository.get_commit_status(run.run_id, run.capability_id)
    provenance = repository.get_report_provenance(run.account_id, run.report_id)
    _require(
        status.state == "committed"
        and status.receipt is not None
        and provenance is not None
        and run.completed_at is not None,
        "m7_lifecycle_lineage_invalid",
    )
    assert status.receipt is not None and provenance is not None
    assert run.completed_at is not None
    receipt = status.receipt
    _require(
        _same_binding(report, authority.target)
        and report.completeness == "complete"
        and report.covered_period == report.requested_period
        and report.subject.account_id == run.account_id == current.connection.account_id
        and report.subject.resource_id
        == run.resource_id
        == current.connection.resource_id
        and report.subject.provider_key
        == run.provider_key
        == current.connection.provider_key
        and receipt.report_id == stored.report_id == run.report_id
        and receipt.run_id == run.run_id
        and receipt.stored_at == stored.stored_at
        and receipt.payload_digest
        == run.payload_digest
        == budget_report_payload_digest(report)
        and receipt.fact_ids == run.observation_ids
        and len(receipt.fact_ids)
        == len(report.cost_buckets) + len(report.usage_buckets)
        and receipt.target_generation
        == run.target_generation
        == report.binding_generation
        and provenance.operation_id == run.run_id
        and provenance.source_id == run.source_id == report.source_id
        and provenance.capability_id == run.capability_id
        and provenance.provider_key == run.provider_key
        and provenance.collected_at == report.collected_at
        and report.requested_period.start == authority.report_context.interval_start
        and report.requested_period.end == authority.report_context.interval_end
        and report.source_category == authority.report_context.source_category
        and report.grouping == authority.report_context.grouping,
        "m7_lifecycle_lineage_invalid",
    )
    return Lineage(
        run.run_id,
        run.report_id,
        report.binding_id,
        report.binding_generation,
        run.requested_at,
        run.completed_at,
        receipt.payload_digest,
        (run, stored, status, provenance, authority),
    )


def inspect_metadata(
    reference: DatabaseRefV1,
    *,
    deadline: float,
) -> tuple[Candidate | None, str | None]:
    """Only published registry/run/report reads; never open credential storage."""
    accounts = ListAccountsV1(SqliteRegistryRepositoryV1(reference))
    billing = SqliteBillingConnectionRepositoryV1(reference)
    access = SqliteBillingAccessRepositoryV1(reference)
    bindings = SqliteCredentialBindingsV1(reference)
    runs = SqliteCollectionRepositoryV1(reference)
    as_of = datetime.now(UTC)
    reason = "m7_billing_rotation_history_absent"
    for provider in ("claude", "codex"):
        sources = {
            (capability, source)
            for capability, source, _ in billing_source_operations(provider)
        }
        cursor = None
        seen_accounts: set[OpaqueIdV1] = set()
        while True:
            _bounded(deadline)
            page = accounts.page(provider, as_of=as_of, limit=100, after_key=cursor)
            _require(
                page.availability.state == "available",
                "m7_lifecycle_inventory_unavailable",
            )
            for account in page.items:
                _bounded(deadline)
                _require(
                    account.account_id not in seen_accounts,
                    "m7_lifecycle_cursor_invalid",
                )
                seen_accounts.add(account.account_id)
                metadata = billing.get(account.account_id)
                if metadata is None:
                    continue
                for connection in metadata.connections:
                    target = access.resolve(
                        account.account_id, connection.resource_id, "monitoring"
                    )
                    if target is None:
                        continue
                    aggregate = bindings.read(account.account_id)
                    retired = {
                        item.binding_id: item
                        for item in aggregate.bindings
                        if item.lifecycle == "cleanup_complete"
                        and item.reason_code == "local_cleanup_completed"
                        and item.generation < target.binding.generation
                    }
                    if not retired:
                        continue
                    reason = "m7_billing_rotation_receipts_absent"
                    witnesses: dict[OpaqueIdV1, Lineage] = {}
                    run_cursor = None
                    seen_runs: set[OpaqueIdV1] = set()
                    while True:
                        _bounded(deadline)
                        batch = runs.list_runs(
                            provider, account.account_id, as_of, 100, run_cursor
                        )
                        for run in batch:
                            _bounded(deadline)
                            _require(
                                run.run_id not in seen_runs,
                                "m7_lifecycle_cursor_invalid",
                            )
                            seen_runs.add(run.run_id)
                            if (
                                not isinstance(run, BudgetCollectionRunViewV1)
                                or (run.capability_id, run.source_id) not in sources
                                or run.resource_id != connection.resource_id
                            ):
                                continue
                            witness = _lineage(reference, run, target)
                            if witness is not None and witness.binding_id in {
                                *retired,
                                target.binding.binding_id,
                            }:
                                witnesses.setdefault(witness.binding_id, witness)
                        replacement = witnesses.get(target.binding.binding_id)
                        if replacement is not None:
                            for old_id, old in retired.items():
                                previous = witnesses.get(old_id)
                                if previous is not None and (
                                    previous.generation == old.generation
                                    and replacement.generation
                                    == target.binding.generation
                                    and previous.completed_at
                                    <= replacement.requested_at
                                ):
                                    return Candidate(
                                        account,
                                        target,
                                        aggregate,
                                        old,
                                        previous,
                                        replacement,
                                    ), None
                        if len(batch) < 100:
                            break
                        _require(len(seen_runs) < 10000, "m7_lifecycle_scan_limit")
                        run_cursor = batch[-1].run_id.value
            if not page.has_more:
                break
            _require(
                page.next_key is not None and page.next_key != cursor,
                "m7_lifecycle_cursor_invalid",
            )
            _require(len(seen_accounts) < 2000, "m7_lifecycle_scan_limit")
            cursor = page.next_key
    return None, reason


def _installed(expected: str) -> Path:
    selected = subprocess.run(
        [
            "systemctl",
            "--user",
            "show",
            "agentmonitor-dashboard.service",
            "--property=WorkingDirectory",
            "--value",
        ],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    runtime = Path(selected.stdout.strip())
    _require(
        selected.returncode == 0
        and runtime.parent == LIVE / "releases"
        and re.fullmatch("m6-candidate-" + expected + "-[a-f0-9]{64}", runtime.name)
        is not None,
        "m7_lifecycle_installed_revision_mismatch",
    )
    _require(
        _verify_retained_baseline(runtime)[0] == expected, "m7_lifecycle_seal_invalid"
    )
    return runtime


def _file_identity(path: Path) -> tuple[int, ...]:
    metadata = path.lstat()
    return (
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_size,
        metadata.st_mtime_ns,
        metadata.st_ctime_ns,
    )


def _retained_location(root: Path) -> Path:
    """Reuse the existing nonsecret reader without its mutating staging recovery."""
    descriptor = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        return _read_location_at(descriptor)
    finally:
        os.close(descriptor)


def _observe_candidate(reference: DatabaseRefV1, candidate: Candidate) -> str:
    """The name-only reader retains no value; actual owner state is never changed."""
    account_id = candidate.account.account_id
    target = candidate.target
    registry = SqliteRegistryRepositoryV1(reference)
    bindings = SqliteCredentialBindingsV1(reference)
    access = SqliteBillingAccessRepositoryV1(reference)
    cloud = SqliteCloudCredentialRegistryV1(reference)
    runs = SqliteCollectionRepositoryV1(reference)
    authority = (
        "anthropic.analytics"
        if target.connection.provider_key == "claude"
        else OPENAI_COST_AUTHORITY_ID_V1
    )
    service = cloud.read_access_target_for_authority(
        target.connection.provider_key, authority
    )
    _require(service is not None, "m7_lifecycle_service_unavailable")
    assert service is not None
    env = selected_env_from_service(reference._approved_root)
    _require(
        _retained_location(reference._approved_root) == env,
        "m7_lifecycle_env_selection_changed",
    )
    # These artifacts must already exist. Observing must not initialize a store.
    env_before = _file_identity(env)
    location_before = _file_identity(reference._approved_root / ".ollama-env-location")
    account_lock = reference._approved_root / credential_lock_name(account_id.value)
    account_lock_before = _file_identity(account_lock)
    lock_before = _file_identity(env.parent / ".ollama-env.lock")
    with account_credential_lock(reference, account_id) as lease:
        _require(
            registry.get_account(account_id) == candidate.account
            and bindings.read(account_id) == candidate.aggregate
            and access.resolve(account_id, target.connection.resource_id, "monitoring")
            == target,
            "m7_lifecycle_account_changed",
        )
        names = _managed_entries(env)
        provider = target.connection.provider_key
        _require(
            (provider, candidate.retired.binding_id.value) not in names,
            "m7_lifecycle_retired_entry_present",
        )
        _require(
            (provider, target.binding.binding_id.value) in names,
            "m7_lifecycle_replacement_entry_absent",
        )
        for captured in (candidate.previous, candidate.replacement):
            run = runs.get_run(captured.run_id)
            _require(
                isinstance(run, BudgetCollectionRunViewV1),
                "m7_lifecycle_lineage_changed",
            )
            assert isinstance(run, BudgetCollectionRunViewV1)
            _require(
                _lineage(reference, run, target) == captured,
                "m7_lifecycle_lineage_changed",
            )
        lease.inherited_lock(account_id)
        _require(
            registry.get_account(account_id) == candidate.account
            and bindings.read(account_id) == candidate.aggregate
            and access.resolve(account_id, target.connection.resource_id, "monitoring")
            == target,
            "m7_lifecycle_account_changed",
        )
        _require(
            cloud.read_access_target_for_authority(provider, authority) == service,
            "m7_lifecycle_service_changed",
        )
        _require(
            selected_env_from_service(reference._approved_root) == env
            and _retained_location(reference._approved_root) == env
            and _file_identity(env) == env_before
            and _file_identity(reference._approved_root / ".ollama-env-location")
            == location_before
            and _file_identity(account_lock) == account_lock_before
            and _file_identity(env.parent / ".ollama-env.lock") == lock_before,
            "m7_lifecycle_env_selection_changed",
        )
    return hashlib.sha256(
        "\0".join(
            (
                account_id.value,
                target.connection.resource_id.value,
                str(target.connection.scope_generation),
                candidate.retired.binding_id.value,
                target.binding.binding_id.value,
                str(target.binding.generation),
                candidate.previous.run_id.value,
                candidate.previous.digest,
                candidate.replacement.run_id.value,
                candidate.replacement.digest,
                service.access_target_id.value,
                str(service.record_version),
                service.manifest_fingerprint,
            )
        ).encode()
    ).hexdigest()


def observe(expected: str) -> dict[str, object]:
    result: dict[str, object] = dict(
        record_type="agentmonitor.m7_credential_lifecycle.v1",
        evidence_scope="one_real_billing_rotation_and_local_removal",
        source_revision=expected,
        status="not_run",
        reason_code=None,
        provider=None,
        proof_digest=None,
        checks={},
        provider_key_revocation_claimed=False,
        distinct_key_content_claimed=False,
        command_provenance_claimed=False,
    )
    try:
        _require(
            re.fullmatch("[a-f0-9]{40}", expected) is not None,
            "m7_lifecycle_revision_invalid",
        )
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
        runtime, identity = _installed(expected), _identity()
        reference = DatabaseRefV1(LIVE / "agentmonitor.db", LIVE)
        database_identity = reference.validate()
        candidate, reason = inspect_metadata(reference, deadline=time.monotonic() + 70)
        if candidate is None:
            result["reason_code"] = reason
            return result
        digest = _observe_candidate(reference, candidate)
        _require(
            _identity() == identity
            and _installed(expected) == runtime
            and reference.validate() == database_identity,
            "m7_lifecycle_service_changed",
        )
        result.update(
            status="passed",
            provider=candidate.target.connection.provider_key,
            proof_digest=digest,
            checks=dict.fromkeys(CHECKS, True),
        )
    except ObservationUnavailable as error:
        result.update(status="blocked", reason_code=str(error))
    except Exception:
        result.update(
            status="blocked", reason_code="m7_lifecycle_observation_unavailable"
        )
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expected-revision", required=True)
    result = observe(parser.parse_args().expected_revision)
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] == "passed" else 3


if __name__ == "__main__":
    raise SystemExit(main())
