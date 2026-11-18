"""Current-schema backup/restore of genuine facts, with no credential recovery.

Baseline verification of existing production primitives, not a new backup engine
or provider replay. Only the SQLite file is copied; live configuration, keys and
profiles are never inspected. Every failed comparison emits a closed code.
"""

import http.client
import os
import sqlite3
import stat
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

import pytest
from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
    DatabaseRefV1,
    open_sqlite_database,
)
from agentmonitor.adapters.persistence._shared.sqlite.schema.compatibility import (
    InspectSchemaCompatibilityV1,
    application_schema_range,
)
from agentmonitor.adapters.persistence.capacity.sqlite.budget_repository import (
    SqliteBudgetReportRepositoryV1,
)
from agentmonitor.adapters.persistence.capacity.sqlite.repository import (
    SqliteCapacityRepositoryV1,
)
from agentmonitor.adapters.persistence.registry.sqlite.credential_bindings import (
    SqliteCredentialBindingsV1,
)
from agentmonitor.adapters.persistence.registry.sqlite.credential_lock import (
    account_credential_lock,
)
from agentmonitor.adapters.providers.ollama.api.policy import OllamaUsageRequestV1
from agentmonitor.adapters.providers.ollama.api.source import (
    OllamaUsageAuthorizationSinkV1,
    collect_usage_report_in_worker_v1,
)
from agentmonitor.adapters.providers.ollama.cloud_balance.env_capability import (
    approve_env_credential_file_v1,
    env_credential_file_lease_v1,
)
from agentmonitor.adapters.providers.ollama.cloud_balance.env_policy import (
    ENV_AUTHORIZATION_POLICY_V1,
)
from agentmonitor.composition.billing_env_authorization import (
    OllamaUsageEnvAuthorizationUnavailable,
    OllamaUsageEnvAuthorizationV1,
)
from agentmonitor.composition.ollama_usage_result import _map_failure
from agentmonitor.modules.registry.application.cloud_connection import (
    resolve_active_credential_binding,
)

from backend.tests.live.ollama.test_budget_monetary_persistence import (
    _check_normalized_storage,
    _counts,
    _monetary_report,
    _receipt,
    _require,
)
from backend.tests.live.ollama.test_cloud_registry_revision_admission import (
    _LIVE_DATABASE,
)
from tools.automation.implementations.auto_migrate import (
    _create_sqlite_backup,
    _digest_file,
)


def _private_database_only(root: Path) -> None:
    _require(
        stat.S_IMODE(root.stat().st_mode) == 0o700,
        "financial_backup_directory_not_private",
    )
    allowed = {"agentmonitor.db", "agentmonitor.db-wal", "agentmonitor.db-shm"}
    for path in root.iterdir():
        info = path.lstat()
        _require(
            path.name in allowed
            and stat.S_ISREG(info.st_mode)
            and info.st_uid == os.getuid()
            and stat.S_IMODE(info.st_mode) == 0o600
            and info.st_nlink == 1,
            "financial_backup_contains_non_database_artifact",
        )


def _current_schema_and_integrity(reference: DatabaseRefV1) -> str:
    catalog = application_schema_range()
    view = InspectSchemaCompatibilityV1(reference, catalog, "runtime_read_only")
    _require(
        view.state == "compatible"
        and not view.migration_required
        and view.integrity_state == "passed"
        and view.policy_state == "passed"
        and view.application_range.catalog_digest == catalog.catalog_digest
        and view.current_revision is not None,
        "financial_restore_current_schema_invalid",
    )
    with open_sqlite_database(reference, "runtime_read_only") as database:
        with database.connect() as connection:
            _require(
                connection.exec_driver_sql("PRAGMA integrity_check").scalars().all()
                == ["ok"],
                "financial_restore_integrity_invalid",
            )
            _require(
                connection.exec_driver_sql("PRAGMA foreign_key_check").first() is None,
                "financial_restore_foreign_keys_invalid",
            )
    return str(view.current_revision)


def _collection_counts(reference: DatabaseRefV1) -> tuple[int, int]:
    with open_sqlite_database(reference, "runtime_read_only") as database:
        with database.connect() as connection:
            return (
                int(
                    connection.exec_driver_sql(
                        "SELECT count(*) FROM collection_run"
                    ).scalar_one()
                ),
                int(
                    connection.exec_driver_sql(
                        "SELECT count(*) FROM collection_request"
                    ).scalar_one()
                ),
            )


@pytest.fixture(scope="module")
def financial_backup_restore(
    tmp_path_factory: pytest.TempPathFactory,
) -> tuple[DatabaseRefV1, DatabaseRefV1, str]:
    root = tmp_path_factory.mktemp("m7-financial-restore")
    os.chmod(root, 0o700)
    backup_root, restored_root = root / "backup", root / "restored"
    backup_root.mkdir(mode=0o700)
    restored_root.mkdir(mode=0o700)
    backup = backup_root / "agentmonitor.db"
    restored = restored_root / "agentmonitor.db"
    # The production primitive bounds each SQLite backup at 120 seconds, copies
    # pages rather than files/WAL fragments, creates exclusively and fsyncs.
    with closing(
        sqlite3.connect(f"{_LIVE_DATABASE.as_uri()}?mode=ro", uri=True, timeout=5)
    ) as source:
        source.execute("PRAGMA query_only=ON")
        digest = _create_sqlite_backup(source, backup)
    _require(_digest_file(backup) == digest, "financial_backup_digest_invalid")
    _private_database_only(backup_root)
    # Immutable applies only to this closed, checksum-verified private snapshot;
    # it avoids new WAL/SHM sidecars while reading the backup for restore.
    with closing(
        sqlite3.connect(f"{backup.as_uri()}?mode=ro&immutable=1", uri=True, timeout=5)
    ) as source:
        source.execute("PRAGMA query_only=ON")
        restored_digest = _create_sqlite_backup(source, restored)
    _require(
        _digest_file(restored) == restored_digest, "financial_restore_digest_invalid"
    )
    _require(_digest_file(backup) == digest, "financial_backup_changed_on_restore")
    _private_database_only(restored_root)
    return (
        DatabaseRefV1(backup, backup_root),
        DatabaseRefV1(restored, restored_root),
        digest,
    )


def test_real_financial_backup_restores_current_schema_exact_facts_and_receipts(
    financial_backup_restore: tuple[DatabaseRefV1, DatabaseRefV1, str],
) -> None:
    backup, restored, digest = financial_backup_restore
    _require(
        _current_schema_and_integrity(backup)
        == _current_schema_and_integrity(restored),
        "financial_restore_schema_changed",
    )
    run, stored = _monetary_report(backup)
    receipt = _receipt(backup, run)
    report = stored.report
    _check_normalized_storage(backup, stored, receipt)
    source_repository = SqliteBudgetReportRepositoryV1(backup)
    restored_repository = SqliteBudgetReportRepositoryV1(restored)
    _require(
        restored_repository.get_report(report.subject.account_id, stored.report_id)
        == stored,
        "financial_restore_report_amount_or_coverage_changed",
    )
    _require(_receipt(restored, run) == receipt, "financial_restore_receipt_changed")
    provenance = source_repository.get_report_provenance(
        report.subject.account_id, stored.report_id
    )
    _require(provenance is not None, "financial_backup_provenance_missing")
    _require(
        restored_repository.get_report_provenance(
            report.subject.account_id, stored.report_id
        )
        == provenance,
        "financial_restore_provenance_changed",
    )
    _check_normalized_storage(restored, stored, receipt)
    _require(
        _counts(restored) == _counts(backup), "financial_restore_fact_counts_changed"
    )
    _require(
        _collection_counts(restored) == _collection_counts(backup),
        "financial_restore_dispatched_work",
    )
    # Preserve actual included/purchased balance facts separately as well as API
    # spending; one shared cutoff prevents freshness evaluation from drifting.
    cutoff = datetime.now(UTC)
    windows = SqliteCapacityRepositoryV1(backup).list_quota_windows(
        report.subject.account_id,
        report.subject.resource_id,
        "subscription.quota",
        cutoff,
    )
    _require(
        any(
            window.remaining.value is not None and window.remaining.value.unit == "usd"
            for window in windows
        ),
        "genuine_funds_observation_required",
    )
    _require(
        SqliteCapacityRepositoryV1(restored).list_quota_windows(
            report.subject.account_id,
            report.subject.resource_id,
            "subscription.quota",
            cutoff,
        )
        == windows,
        "financial_restore_funds_observation_changed",
    )
    _private_database_only(backup._approved_root)
    _private_database_only(restored._approved_root)
    _require(_digest_file(backup._path) == digest, "financial_backup_artifact_changed")


def test_restored_real_binding_requires_key_without_dispatch_or_new_facts(
    financial_backup_restore: tuple[DatabaseRefV1, DatabaseRefV1, str],
    tmp_path: Path,
) -> None:
    backup, _, backup_digest = financial_backup_restore
    os.chmod(tmp_path, 0o700)
    restored_root = tmp_path / "credential-restore"
    restored_root.mkdir(mode=0o700)
    restored_path = restored_root / "agentmonitor.db"
    _require(
        _digest_file(backup._path) == backup_digest,
        "financial_backup_artifact_changed",
    )
    # This test owns its restored directory, including the persistent credential
    # lock. Never add that lock to the module's database-only restore artifact.
    # Immutable reads only the closed, verified private backup, never live data.
    with closing(
        sqlite3.connect(
            f"{backup._path.as_uri()}?mode=ro&immutable=1", uri=True, timeout=5
        )
    ) as source:
        source.execute("PRAGMA query_only=ON")
        restored_digest = _create_sqlite_backup(source, restored_path)
    _require(
        _digest_file(restored_path) == restored_digest,
        "financial_credential_restore_digest_invalid",
    )
    _private_database_only(restored_root)
    restored = DatabaseRefV1(restored_path, restored_root)
    run, stored = _monetary_report(restored)
    report = stored.report
    bindings = SqliteCredentialBindingsV1(restored)
    before = bindings.read(report.subject.account_id)
    binding = resolve_active_credential_binding(before)
    _require(binding is not None, "restored_active_credential_binding_required")
    if binding is None:
        return
    facts_before, work_before = _counts(restored), _collection_counts(restored)
    selected = tmp_path / ".env"
    descriptor = os.open(
        selected, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    os.close(descriptor)  # Empty newly created shell; no source config is copied.
    descriptor = os.open(
        tmp_path / ENV_AUTHORIZATION_POLICY_V1.global_lock_name,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
        0o600,
    )
    os.close(descriptor)
    authority = approve_env_credential_file_v1(selected)
    connection = http.client.HTTPSConnection("ollama.com", timeout=1)
    sink = OllamaUsageAuthorizationSinkV1(connection)
    try:
        with account_credential_lock(restored, binding.account_id) as lock:
            with env_credential_file_lease_v1(authority) as lease:
                grant = OllamaUsageEnvAuthorizationV1(
                    binding.binding_id.value,
                    binding.account_id,
                    lock.inherited_lock(binding.account_id),
                    lease.inherited_file(),
                )
                with pytest.raises(OllamaUsageEnvAuthorizationUnavailable) as failed:
                    grant.authorize(sink)
                _require(
                    str(failed.value) == "ollama_usage_authorization_unavailable",
                    "restore_key_refusal_invalid",
                )
                _require(
                    connection.sock is None
                    and connection.__dict__.get("_buffer") == [],
                    "restore_key_refusal_sent_request",
                )
                with pytest.raises(ValueError, match="authorization_missing"):
                    sink.finish()
    finally:
        sink.cancel()
        connection.close()
    _require(selected.stat().st_size == 0, "restore_credential_shell_changed")
    scope: Literal["self", "team"] = (
        "team" if report.source_category == "team_requests_and_cost" else "self"
    )
    request = OllamaUsageRequestV1(
        subject=report.subject,
        binding=binding,
        scope_id=report.scope_id,
        scope_evidence=report.scope_evidence,
        scope_generation=report.scope_generation,
        range_key="7d"
        if (report.requested_period.end - report.requested_period.start).days == 7
        else "30d",
        period=report.requested_period,
        requested_at=run.requested_at,
        scope=scope,
    )
    # Production pre-authorization guard returns before any collection attempt.
    # This is a local failure outcome, never a fabricated provider response.
    result = collect_usage_report_in_worker_v1(request, authorization=None)
    outcome = _map_failure(result)
    _require(
        result.requests_made == 0 and result.report is None,
        "restore_missing_key_collected",
    )
    _require(
        outcome.state == "blocked_user_action_required"
        and outcome.error is not None
        and outcome.error.code == "ollama_usage_authorization_unavailable"
        and outcome.error.retry.disposition == "after_user_action",
        "restore_missing_key_not_credential_required",
    )
    _require(bindings.read(binding.account_id) == before, "restore_binding_changed")
    _require(_counts(restored) == facts_before, "restore_missing_key_added_facts")
    _require(
        _collection_counts(restored) == work_before,
        "restore_missing_key_dispatched_work",
    )
