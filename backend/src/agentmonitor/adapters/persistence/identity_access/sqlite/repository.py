"""M01 bootstrap repository over the approved real file-backed SQLite policy."""

import re
import secrets
from datetime import UTC, datetime

from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
    DatabaseRefV1,
    SqlitePolicyError,
    open_sqlite_database,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.identity_access_v1 import (
    BootstrapAdministratorOutcomeV1,
    IamInitializationStateV1,
    RecoverAdministratorOutcomeV1,
)
from agentmonitor.modules.identity_access.application.errors import (
    IamRepositoryUnavailableV1,
)
from sqlalchemy.exc import SQLAlchemyError


class IdentityAccessRepositoryErrorV1(IamRepositoryUnavailableV1):
    """Safe typed failure; no SQL, path or credential appears in its text."""

    def __init__(self) -> None:
        super().__init__()


def _utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")


class SqliteIdentityAccessRepositoryV1:
    """Owns only IAM rows and short atomic bootstrap transaction."""

    def __init__(self, database_ref: DatabaseRefV1) -> None:
        self._database_ref = database_ref

    def initialization_state(self) -> IamInitializationStateV1:
        try:
            with open_sqlite_database(
                self._database_ref, "runtime_read_write"
            ) as handle:
                with handle.connect() as connection:
                    rows = (
                        connection.exec_driver_sql(
                            "SELECT hash_policy_version FROM iam_administrator LIMIT 2"
                        )
                        .scalars()
                        .all()
                    )
        except (SqlitePolicyError, SQLAlchemyError):
            raise IdentityAccessRepositoryErrorV1() from None
        if not rows:
            return IamInitializationStateV1("uninitialized", None, "v1_0100")
        if len(rows) != 1:
            return IamInitializationStateV1("incompatible", None, "v1_0100")
        policy = rows[0]
        if policy != "argon2id-rfc9106-low-memory-v1":
            return IamInitializationStateV1("incompatible", None, "v1_0100")
        return IamInitializationStateV1("initialized", policy, "v1_0100")

    def claim_administrator(
        self, password_phc: str, hash_policy_version: str, correlation_id: str
    ) -> BootstrapAdministratorOutcomeV1:
        if (
            hash_policy_version != "argon2id-rfc9106-low-memory-v1"
            or not password_phc.startswith("$argon2id$v=19$m=65536,t=3,p=4$")
            or re.fullmatch(r"[A-Za-z0-9_-]{1,64}", correlation_id) is None
        ):
            raise IdentityAccessRepositoryErrorV1() from None
        admin_id = secrets.token_urlsafe(24)
        audit_id = secrets.token_urlsafe(24)
        instant = _utc_now()
        try:
            with open_sqlite_database(
                self._database_ref, "runtime_read_write"
            ) as handle:
                with handle.connect() as connection:
                    connection.exec_driver_sql("BEGIN IMMEDIATE")
                    count = connection.exec_driver_sql(
                        "SELECT count(*) FROM iam_administrator"
                    ).scalar_one()
                    if count:
                        connection.rollback()
                        return BootstrapAdministratorOutcomeV1(
                            "administrator_already_initialized", None
                        )
                    connection.exec_driver_sql(
                        "INSERT INTO iam_administrator "
                        "(singleton_key, administrator_id, password_phc, "
                        "hash_policy_version, created_at, password_changed_at, "
                        "updated_at, record_version) VALUES (1, ?, ?, ?, ?, ?, ?, 1)",
                        (
                            admin_id,
                            password_phc,
                            hash_policy_version,
                            instant,
                            instant,
                            instant,
                        ),
                    )
                    connection.exec_driver_sql(
                        "INSERT INTO iam_security_audit_event "
                        "(event_id, event_type, occurred_at, recorded_at, "
                        "actor_principal_id, authentication_method, target_type, "
                        "target_id, outcome_code, correlation_id, schema_version, "
                        "aggregate_count) VALUES "
                        "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, NULL)",
                        (
                            audit_id,
                            "administrator_initialized",
                            instant,
                            instant,
                            None,
                            None,
                            "administrator",
                            admin_id,
                            "created",
                            correlation_id,
                        ),
                    )
                    connection.commit()
        except (SqlitePolicyError, SQLAlchemyError):
            raise IdentityAccessRepositoryErrorV1() from None
        return BootstrapAdministratorOutcomeV1("created", OpaqueIdV1(admin_id))

    def recover_administrator(
        self, password_phc: str, hash_policy_version: str, correlation_id: str
    ) -> RecoverAdministratorOutcomeV1:
        """Offline-only credential-wide invalidation; never expose as HTTP/CLI.

        The caller must first obtain the future service-held quiescence receipt.
        Until that seam exists, only isolated real-DB verification may call this
        method; the installed recovery command remains unavailable.
        """
        if (
            hash_policy_version != "argon2id-rfc9106-low-memory-v1"
            or not password_phc.startswith("$argon2id$v=19$m=65536,t=3,p=4$")
            or re.fullmatch(r"[A-Za-z0-9_-]{1,64}", correlation_id) is None
        ):
            raise IdentityAccessRepositoryErrorV1() from None
        instant = _utc_now()
        event_id = secrets.token_urlsafe(24)
        try:
            with open_sqlite_database(
                self._database_ref, "runtime_read_write"
            ) as handle:
                with handle.connect() as connection:
                    connection.exec_driver_sql("BEGIN IMMEDIATE")
                    administrator_id = connection.exec_driver_sql(
                        "SELECT administrator_id FROM iam_administrator LIMIT 1"
                    ).scalar_one_or_none()
                    if administrator_id is None:
                        connection.rollback()
                        return RecoverAdministratorOutcomeV1(
                            "iam_setup_required", None, 0, 0
                        )
                    connection.exec_driver_sql(
                        "UPDATE iam_administrator SET password_phc=?, "
                        "hash_policy_version=?, password_changed_at=?, "
                        "updated_at=?, record_version=record_version+1 "
                        "WHERE singleton_key=1",
                        (password_phc, hash_policy_version, instant, instant),
                    )
                    sessions = connection.exec_driver_sql(
                        "UPDATE iam_browser_session SET revoked_at=?, "
                        "revocation_reason='local_recovery', "
                        "credential_digest=NULL, csrf_digest=NULL, "
                        "record_version=record_version+1 WHERE revoked_at IS NULL",
                        (instant,),
                    ).rowcount
                    tokens = connection.exec_driver_sql(
                        "UPDATE iam_api_token SET revoked_at=?, "
                        "revocation_reason='local_recovery', "
                        "verification_digest=NULL, record_version=record_version+1 "
                        "WHERE revoked_at IS NULL",
                        (instant,),
                    ).rowcount
                    connection.exec_driver_sql(
                        "INSERT INTO iam_security_audit_event "
                        "(event_id, event_type, occurred_at, recorded_at, "
                        "actor_principal_id, authentication_method, target_type, "
                        "target_id, outcome_code, correlation_id, schema_version, "
                        "aggregate_count) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?)",
                        (
                            event_id,
                            "administrator_recovered",
                            instant,
                            instant,
                            None,
                            None,
                            "administrator",
                            administrator_id,
                            "recovered",
                            correlation_id,
                            sessions + tokens,
                        ),
                    )
                    connection.commit()
        except (SqlitePolicyError, SQLAlchemyError):
            raise IdentityAccessRepositoryErrorV1() from None
        return RecoverAdministratorOutcomeV1(
            "recovered", OpaqueIdV1(administrator_id), sessions, tokens
        )
