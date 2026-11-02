"""Verify actual persisted constraint metadata reaches the API serializer.

Run against an operator-provided private database backup; prints no identities,
metric values, file paths or credentials. Never creates or modifies records.
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from datetime import UTC, datetime
from pathlib import Path

from agentmonitor.adapters.persistence._shared.sqlite.core.policy import DatabaseRefV1
from agentmonitor.adapters.persistence.capacity.sqlite.repository import (
    SqliteCapacityRepositoryV1,
)
from agentmonitor.api.v1.routers.capacity import _window
from agentmonitor.contracts.common_v1 import OpaqueIdV1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backup-root", required=True, type=Path)
    root = parser.parse_args().backup_root
    try:
        reference = DatabaseRefV1(root / "agentmonitor.db", root)
        reference.validate()
        # SQLite's read-only URI avoids changing the supplied backup.
        with sqlite3.connect(
            f"file:{root}/agentmonitor.db?mode=ro", uri=True
        ) as connection:
            rows = connection.execute(
                "SELECT DISTINCT account_id FROM capacity_current_projection "
                "WHERE projection_kind='quota' LIMIT 1000"
            ).fetchall()
        repository = SqliteCapacityRepositoryV1(reference)
        for (account_id,) in rows:
            windows = repository.list_account_quota_windows(
                OpaqueIdV1(account_id), datetime.now(UTC)
            )
            for window in windows:
                if window.is_constraining is None:
                    continue
                wire = _window(window).model_dump()
                if wire.get("is_constraining") != window.is_constraining:
                    print(
                        "CONSTRAINT PROJECTION: FAILED — stored state is absent or changed"
                    )
                    return 1
                print(
                    "CONSTRAINT PROJECTION: PASSED — stored state reaches API projection"
                )
                return 0
    except (OSError, sqlite3.Error, ValueError, TypeError):
        print(
            "CONSTRAINT PROJECTION: BLOCKED — backup or application query unavailable"
        )
        return 3
    print("CONSTRAINT PROJECTION: BLOCKED — no window with known constraint state")
    return 3


if __name__ == "__main__":
    sys.exit(main())
