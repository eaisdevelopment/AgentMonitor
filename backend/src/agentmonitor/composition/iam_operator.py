"""Local-only CLI composition for one-time administrator bootstrap.

Usage: python -m agentmonitor.composition.iam_operator bootstrap --data-root PATH
Password input is delegated to M01's controlling-TTY adapter. No HTTP or
recovery mode exists until a tested service-quiescence receipt is available.
"""

import sys
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
)


def main(argv: list[str] | None = None) -> int:
    arguments = sys.argv[1:] if argv is None else argv
    if len(arguments) != 3 or arguments[:2] != ["bootstrap", "--data-root"]:
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
            secret = read_confirmed_password()
            if secret is None:
                status = "password_input_unavailable_or_mismatch"
            else:
                outcome = BootstrapAdministratorV1(repository, Argon2PasswordV1())(
                    secret, correlation_id="local-tty-bootstrap"
                )
                status = (
                    "administrator_initialized"
                    if outcome.code == "created"
                    else outcome.code
                )
    except (ValueError, RuntimeError, OSError):
        print("iam_operator_unavailable")
        return 2
    print(status)
    return 0 if status == "administrator_initialized" else 2


if __name__ == "__main__":
    raise SystemExit(main())
