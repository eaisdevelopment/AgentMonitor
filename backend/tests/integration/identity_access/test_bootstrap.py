"""ST-IAM-001: production migration, crypto and repository on real SQLite."""

import os
import secrets
import stat
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
    DatabaseRefV1,
    open_sqlite_database,
)
from agentmonitor.adapters.persistence._shared.sqlite.schema import compatibility

IAM_TABLES = {
    "iam_administrator",
    "iam_browser_session",
    "iam_api_token",
    "iam_api_token_scope",
    "iam_login_throttle",
    "iam_idempotency_record",
    "iam_security_audit_event",
}
REGISTRY_TABLES = {
    "reg_registry_state",
    "reg_organization",
    "reg_provider_definition",
    "reg_account",
    "reg_registry_change",
    "reg_provider_installation",
    "reg_discovery_candidate",
    "reg_provider_identity_claim",
    "reg_identity_decision",
    "reg_monitoring_profile",
    "reg_account_resource",
    "reg_profile_resource_link",
    "reg_account_configuration_reference",
    "reg_command_receipt",
    "reg_event_outbox",
}


def database_ref(root: Path) -> DatabaseRefV1:
    return DatabaseRefV1(root / "agentmonitor.db", root)


def test_fresh_migration_preserves_empty_m01_schema_at_current_head(
    tmp_path: Path,
) -> None:
    ref = database_ref(tmp_path)
    compatibility.migrate_to_head(ref)
    assert stat.S_IMODE(ref._path.stat().st_mode) == 0o600
    with open_sqlite_database(ref, "runtime_read_write") as handle:
        with handle.connect() as connection:
            tables = set(
                connection.exec_driver_sql(
                    "SELECT name FROM sqlite_schema WHERE type='table'"
                ).scalars()
            )
            assert IAM_TABLES | REGISTRY_TABLES | {"alembic_version"} <= tables
            assert (
                connection.exec_driver_sql(
                    "SELECT version_num FROM alembic_version"
                ).scalar_one()
                == compatibility.application_schema_range().migration_target_revision
            )
            assert (
                connection.exec_driver_sql(
                    "SELECT count(*) FROM iam_administrator"
                ).scalar_one()
                == 0
            )
            assert (
                connection.exec_driver_sql("PRAGMA foreign_key_check").first() is None
            )
    view = compatibility.InspectSchemaCompatibilityV1(
        ref, compatibility.application_schema_range(), "runtime_read_write"
    )
    assert view.state == "compatible"
    assert (
        compatibility.RequireWritableSchemaV1(view).revision
        == compatibility.application_schema_range().migration_target_revision
    )


def test_existing_empty_file_is_not_silently_initialized(tmp_path: Path) -> None:
    ref = database_ref(tmp_path)
    with open_sqlite_database(ref, "migration_initialize"):
        pass
    before = ref._path.read_bytes()
    with pytest.raises(compatibility.SchemaCompatibilityError) as raised:
        compatibility.migrate_to_head(ref)
    assert raised.value.code == "migration_preflight_refused"
    assert ref._path.read_bytes() == before


def test_altered_credential_schema_is_never_certified_writable(tmp_path: Path) -> None:
    ref = database_ref(tmp_path)
    compatibility.migrate_to_head(ref)
    with open_sqlite_database(ref, "migration_existing") as handle:
        with handle.connect() as connection:
            connection.exec_driver_sql(
                "ALTER TABLE iam_administrator ADD COLUMN unauthorized TEXT"
            )
            connection.commit()
    view = compatibility.InspectSchemaCompatibilityV1(
        ref, compatibility.application_schema_range(), "runtime_read_write"
    )
    assert view.state == "migration_failed"
    with pytest.raises(compatibility.SchemaCompatibilityError) as raised:
        compatibility.RequireWritableSchemaV1(view)
    assert raised.value.code == "schema_not_writable"


def test_bootstrap_commits_one_administrator_and_safe_audit(tmp_path: Path) -> None:
    from agentmonitor.adapters.identity_access.argon2_password import Argon2PasswordV1
    from agentmonitor.adapters.persistence.identity_access.sqlite.repository import (
        SqliteIdentityAccessRepositoryV1,
    )
    from agentmonitor.contracts.identity_access_v1 import SecretInputV1
    from agentmonitor.modules.identity_access.application.bootstrap import (
        BootstrapAdministratorV1,
        GetIamInitializationStateV1,
    )

    ref = database_ref(tmp_path)
    compatibility.migrate_to_head(ref)
    owner_input = secrets.token_urlsafe(32)
    repository = SqliteIdentityAccessRepositoryV1(ref)
    bootstrap = BootstrapAdministratorV1(repository, Argon2PasswordV1())
    initial = GetIamInitializationStateV1(repository)()
    assert initial.state == "uninitialized"
    created = bootstrap(SecretInputV1(owner_input), correlation_id="test-bootstrap")
    assert created.code == "created"
    assert GetIamInitializationStateV1(repository)().state == "initialized"
    assert bootstrap(
        SecretInputV1(owner_input), correlation_id="test-bootstrap-again"
    ).code == ("administrator_already_initialized")
    with open_sqlite_database(ref, "runtime_read_write") as handle:
        with handle.connect() as connection:
            assert (
                connection.exec_driver_sql(
                    "SELECT count(*) FROM iam_administrator"
                ).scalar_one()
                == 1
            )
            assert (
                connection.exec_driver_sql(
                    "SELECT count(*) FROM iam_security_audit_event"
                ).scalar_one()
                == 1
            )
            audit_codes = connection.exec_driver_sql(
                "SELECT event_type, target_type, outcome_code, reason_code "
                "FROM iam_security_audit_event"
            ).one()
            assert tuple(audit_codes) == (
                "administrator_initialized",
                "administrator",
                "created",
                None,
            )
            stored = connection.exec_driver_sql(
                "SELECT password_phc FROM iam_administrator"
            ).scalar_one()
            has_expected_policy = stored.startswith("$argon2id$v=19$m=65536,t=3,p=4$")
            correct_input_matches = Argon2PasswordV1().verify(stored, owner_input)
            wrong_input_matches = Argon2PasswordV1().verify(
                stored, secrets.token_urlsafe(32)
            )
            plaintext_absent = owner_input.encode("utf-8") not in ref._path.read_bytes()
            assert has_expected_policy is True
            assert correct_input_matches is True
            assert wrong_input_matches is False
            assert plaintext_absent is True
    assert os.stat(ref._path).st_uid == os.getuid()


def test_real_verifier_rejects_unencodable_candidate_without_exception() -> None:
    from agentmonitor.adapters.identity_access.argon2_password import Argon2PasswordV1

    verifier = Argon2PasswordV1()
    encoded = verifier.hash(secrets.token_urlsafe(32))
    rejected = verifier.verify(encoded, "\ud800" * 15)
    assert rejected is False


def test_independent_real_bootstraps_use_distinct_random_salts(tmp_path: Path) -> None:
    from agentmonitor.adapters.identity_access.argon2_password import Argon2PasswordV1
    from agentmonitor.adapters.persistence.identity_access.sqlite.repository import (
        SqliteIdentityAccessRepositoryV1,
    )
    from agentmonitor.contracts.identity_access_v1 import SecretInputV1
    from agentmonitor.modules.identity_access.application.bootstrap import (
        BootstrapAdministratorV1,
    )

    password = SecretInputV1(secrets.token_urlsafe(32))
    phc_material: list[str] = []
    for name in ("first", "second"):
        root = tmp_path / name
        root.mkdir(mode=0o700)
        ref = database_ref(root)
        compatibility.migrate_to_head(ref)
        result = BootstrapAdministratorV1(
            SqliteIdentityAccessRepositoryV1(ref), Argon2PasswordV1()
        )(password, correlation_id=name)
        assert result.code == "created"
        with open_sqlite_database(ref, "runtime_read_write") as handle:
            with handle.connect() as connection:
                phc_material.append(
                    connection.exec_driver_sql(
                        "SELECT password_phc FROM iam_administrator"
                    ).scalar_one()
                )
    distinct_salts = phc_material[0] != phc_material[1]
    both_verify = all(
        Argon2PasswordV1().verify(encoded, password.reveal_for_verification())
        for encoded in phc_material
    )
    assert distinct_salts is True
    assert both_verify is True


def test_concurrent_real_bootstraps_claim_exactly_one_administrator(
    tmp_path: Path,
) -> None:
    from agentmonitor.adapters.identity_access.argon2_password import Argon2PasswordV1
    from agentmonitor.adapters.persistence.identity_access.sqlite.repository import (
        SqliteIdentityAccessRepositoryV1,
    )
    from agentmonitor.contracts.identity_access_v1 import SecretInputV1
    from agentmonitor.modules.identity_access.application.bootstrap import (
        BootstrapAdministratorV1,
    )

    ref = database_ref(tmp_path)
    compatibility.migrate_to_head(ref)
    password = SecretInputV1(secrets.token_urlsafe(32))

    def claim(index: int) -> str:
        service = BootstrapAdministratorV1(
            SqliteIdentityAccessRepositoryV1(ref), Argon2PasswordV1()
        )
        return service(password, correlation_id=f"concurrent-{index}").code

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = sorted(executor.map(claim, (1, 2)))
    assert outcomes == ["administrator_already_initialized", "created"]
    with open_sqlite_database(ref, "runtime_read_write") as handle:
        with handle.connect() as connection:
            assert (
                connection.exec_driver_sql(
                    "SELECT count(*) FROM iam_administrator"
                ).scalar_one()
                == 1
            )
            assert (
                connection.exec_driver_sql(
                    "SELECT count(*) FROM iam_security_audit_event"
                ).scalar_one()
                == 1
            )
