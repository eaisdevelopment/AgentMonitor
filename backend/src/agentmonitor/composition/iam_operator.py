"""Local-only CLI composition for administrator bootstrap and recovery.

Password input is delegated to M01's controlling-TTY adapter. No HTTP or
password argument exists. Recovery holds the service's stable lock throughout.
"""

import fcntl
import os
import stat
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from agentmonitor.adapters.identity_access.argon2_password import Argon2PasswordV1
from agentmonitor.adapters.identity_access.tty_operator import read_confirmed_password
from agentmonitor.adapters.persistence._shared.sqlite.core.policy import DatabaseRefV1
from agentmonitor.adapters.persistence._shared.sqlite.schema.compatibility import (
    InspectSchemaCompatibilityV1,
    RequireWritableSchemaV1,
    application_schema_range,
)
from agentmonitor.adapters.persistence.identity_access.sqlite.repository import (
    SqliteIdentityAccessRepositoryV1,
)
from agentmonitor.modules.identity_access.application.bootstrap import (
    BootstrapAdministratorV1,
    GetIamInitializationStateV1,
    RecoverAdministratorPasswordV1,
)


class OperatorQuiescenceError(RuntimeError):
    """Stable, path-free failure while excluding the service process."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@contextmanager
def _exclusive_service_quiescence(
    root: Path, database_ref: DatabaseRefV1
) -> Iterator[None]:
    """Hold the same nonblocking flock as P01 before any SQLite connection.

    The lock file is permanent: unlinking it could split service/operator locks.
    """
    database_ref.validate()
    directory = os.open(
        root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
    )
    try:
        root_state = os.fstat(directory)
        if (
            not stat.S_ISDIR(root_state.st_mode)
            or stat.S_IMODE(root_state.st_mode) != 0o700
            or root_state.st_uid != os.getuid()
        ):
            raise OperatorQuiescenceError("service_lock_unsafe")
        descriptor = os.open(
            ".agentmonitor-service.lock",
            os.O_RDWR | os.O_CREAT | os.O_CLOEXEC | os.O_NOFOLLOW,
            0o600,
            dir_fd=directory,
        )
        try:
            state = os.fstat(descriptor)
            if (
                not stat.S_ISREG(state.st_mode)
                or stat.S_IMODE(state.st_mode) != 0o600
                or state.st_uid != os.getuid()
            ):
                raise OperatorQuiescenceError("service_lock_unsafe")
            try:
                fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError as error:
                raise OperatorQuiescenceError("service_lock_occupied") from error
            try:
                database_ref.validate()
                path_state = root.lstat()
                if (path_state.st_dev, path_state.st_ino) != (
                    root_state.st_dev,
                    root_state.st_ino,
                ):
                    raise OperatorQuiescenceError("service_lock_unsafe")
                yield
            finally:
                fcntl.flock(descriptor, fcntl.LOCK_UN)
        finally:
            os.close(descriptor)
    finally:
        os.close(directory)


def main(argv: list[str] | None = None) -> int:
    arguments = sys.argv[1:] if argv is None else argv
    if (
        len(arguments) != 3
        or arguments[0] not in {"bootstrap", "recover"}
        or arguments[1] != "--data-root"
    ):
        print("invalid_operator_arguments")
        return 2
    if not (sys.stdin.isatty() and sys.stdout.isatty() and sys.stderr.isatty()):
        print("controlling_tty_required")
        return 2
    root = Path(arguments[2])
    if not root.is_absolute():
        print("database_reference_invalid")
        return 2
    try:
        database_ref = DatabaseRefV1(root / "agentmonitor.db", root)
        if arguments[0] == "recover":
            with _exclusive_service_quiescence(root, database_ref):
                status = _run_recovery(database_ref)
        else:
            RequireWritableSchemaV1(
                InspectSchemaCompatibilityV1(
                    database_ref, application_schema_range(), "runtime_read_write"
                )
            )
            repository = SqliteIdentityAccessRepositoryV1(database_ref)
            initialization = GetIamInitializationStateV1(repository)().state
            if initialization == "initialized":
                status = "administrator_already_initialized"
            elif initialization == "incompatible":
                status = "iam_repository_unavailable"
            else:
                candidate = read_confirmed_password()
                if candidate is None:
                    status = "password_input_unavailable_or_mismatch"
                else:
                    outcome = BootstrapAdministratorV1(repository, Argon2PasswordV1())(
                        candidate, correlation_id="local-tty-bootstrap"
                    )
                    status = (
                        "administrator_initialized"
                        if outcome.code == "created"
                        else outcome.code
                    )
    except OperatorQuiescenceError as error:
        print(error.code)
        return 2
    except (ValueError, RuntimeError, OSError):
        print("iam_operator_unavailable")
        return 2
    print(status)
    return (
        0 if status in {"administrator_initialized", "administrator_recovered"} else 2
    )


def _run_recovery(database_ref: DatabaseRefV1) -> str:
    RequireWritableSchemaV1(
        InspectSchemaCompatibilityV1(
            database_ref, application_schema_range(), "runtime_read_write"
        )
    )
    repository = SqliteIdentityAccessRepositoryV1(database_ref)
    initialization = GetIamInitializationStateV1(repository)().state
    if initialization == "incompatible":
        return "iam_repository_unavailable"
    if initialization == "uninitialized":
        return "iam_setup_required"
    candidate = read_confirmed_password()
    if candidate is None:
        return "password_input_unavailable_or_mismatch"
    outcome = RecoverAdministratorPasswordV1(repository, Argon2PasswordV1())(
        candidate, correlation_id="local-tty-recovery"
    )
    return "administrator_recovered" if outcome.code == "recovered" else outcome.code


if __name__ == "__main__":
    raise SystemExit(main())
