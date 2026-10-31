"""M2-only absent-file schema initialization; no existing-database upgrades.

Usage: python -m agentmonitor.composition.iam_fresh_init --data-root PATH
The owner creates PATH as an existing, owner-only (0700) directory first.
This does not bootstrap credentials, read .env, or implement AUTO-MIGRATE.
"""

import sys
from pathlib import Path

from agentmonitor.adapters.persistence._shared.sqlite.core.policy import DatabaseRefV1
from agentmonitor.adapters.persistence._shared.sqlite.schema.compatibility import (
    InspectSchemaCompatibilityV1,
    RequireWritableSchemaV1,
    application_schema_range,
    migrate_to_head,
)


def main(argv: list[str] | None = None) -> int:
    arguments = sys.argv[1:] if argv is None else argv
    if len(arguments) != 2 or arguments[0] != "--data-root":
        print("invalid_operator_arguments")
        return 2
    root = Path(arguments[1])
    if not root.is_absolute():
        print("schema_initialization_refused")
        return 2
    try:
        database_ref = DatabaseRefV1(root / "agentmonitor.db", root)
        if database_ref.validate(missing_ok=True) is not None:
            print("database_already_exists")
            return 2
        migrate_to_head(database_ref)
        RequireWritableSchemaV1(
            InspectSchemaCompatibilityV1(
                database_ref, application_schema_range(), "runtime_read_write"
            )
        )
    except (OSError, RuntimeError, ValueError):
        print("schema_initialization_refused")
        return 2
    print("schema_initialized")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
