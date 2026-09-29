"""M4 release prerequisites from the owner's actual read-only installation.

The owner outcome file is private acceptance input, not application data. The
test never prints account labels, profile paths, identities or file contents.
"""

import asyncio
import json
import os
import re
import stat
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from agentmonitor.adapters.persistence._shared.sqlite.core.policy import DatabaseRefV1
from agentmonitor.adapters.persistence._shared.sqlite.schema.compatibility import (
    application_schema_range,
)
from agentmonitor.adapters.persistence._shared.sqlite.schema.live_health import (
    LiveDatabaseHealthReaderV1,
)
from agentmonitor.adapters.persistence.registry.sqlite.repository import (
    SqliteRegistryRepositoryV1,
)
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.database_v1 import DatabaseHealthRequestV1
from agentmonitor.modules.registry.application.accounts import (
    GetAccountV1,
    ListAccountsV1,
    RegistryQueryUnavailableV1,
)

_OPAQUE = re.compile(r"[A-Za-z0-9_.:-]{1,128}\Z")
_SCHEMA = "agentmonitor.m4-owner-outcomes.v1"


def _owner_reference() -> DatabaseRefV1:
    selected = os.environ.get("AGENTMONITOR_TEST_OWNER_DATA_ROOT")
    if not selected:
        pytest.fail("BLOCKED: actual_owner_data_root_required")
    root = Path(selected)
    try:
        reference = DatabaseRefV1(root / "agentmonitor.db", root)
        reference.validate()
    except (OSError, ValueError):
        pytest.fail("BLOCKED: actual_owner_database_unavailable")
    return reference


def _owner_outcomes() -> tuple[tuple[str, str, str], ...]:
    selected = os.environ.get("AGENTMONITOR_TEST_M4_OWNER_OUTCOMES")
    if not selected:
        pytest.fail("BLOCKED: six_owner_outcomes_required")
    descriptor = -1
    try:
        descriptor = os.open(selected, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
        metadata = os.fstat(descriptor)
        if (
            not stat.S_ISREG(metadata.st_mode)
            or metadata.st_size < 1
            or metadata.st_size > 8192
            or metadata.st_uid != os.getuid()
            or stat.S_IMODE(metadata.st_mode) & 0o077
        ):
            raise ValueError
        source = os.read(descriptor, 8193)
        document = json.loads(source)
    except (OSError, UnicodeError, ValueError, TypeError):
        pytest.fail("BLOCKED: private_owner_outcomes_invalid")
    finally:
        if descriptor >= 0:
            os.close(descriptor)
    if (
        type(document) is not dict
        or set(document) != {"schema", "outcomes"}
        or document["schema"] != _SCHEMA
        or type(document["outcomes"]) is not list
        or len(document["outcomes"]) != 6
    ):
        pytest.fail("BLOCKED: six_owner_outcomes_invalid")
    result: list[tuple[str, str, str]] = []
    for item in document["outcomes"]:
        if type(item) is not dict or set(item) != {
            "account_id",
            "organization_id",
            "disposition",
        }:
            pytest.fail("BLOCKED: owner_outcome_record_invalid")
        account_id = item["account_id"]
        organization_id = item["organization_id"]
        disposition = item["disposition"]
        if (
            type(account_id) is not str
            or type(organization_id) is not str
            or _OPAQUE.fullmatch(account_id) is None
            or _OPAQUE.fullmatch(organization_id) is None
            or disposition not in ("verified", "owner_unavailable")
        ):
            pytest.fail("BLOCKED: owner_outcome_record_invalid")
        result.append((account_id, organization_id, disposition))
    if len({item[0] for item in result}) != 6:
        pytest.fail("BLOCKED: duplicate_owner_account_outcome")
    if len({item[1] for item in result}) != 2:
        pytest.fail("BLOCKED: two_owner_organizations_required")
    return tuple(result)


def test_owner_installation_has_current_live_marker_and_readable_registry() -> None:
    reference = _owner_reference()
    schema_range = application_schema_range()
    now = datetime.now(UTC)
    result = asyncio.run(
        LiveDatabaseHealthReaderV1(reference, schema_range)(
            DatabaseHealthRequestV1(
                now,
                now + timedelta(seconds=2),
                OpaqueIdV1("m4-release-live-marker"),
            )
        )
    )
    if not (
        result.reachable
        and result.schema_revision == schema_range.migration_target_revision
        and result.policy_state == "passed"
        and result.compatibility_state is None
        and result.integrity_state == "not_checked"
        and result.reason_codes == ("database_health_unverified",)
    ):
        pytest.fail("BLOCKED: owner_installation_live_marker_unavailable")
    try:
        # The published registry query must be usable at the admitted schema.
        ListAccountsV1(SqliteRegistryRepositoryV1(reference)).page(
            "claude", as_of=now, limit=1
        )
    except (ValueError, RegistryQueryUnavailableV1):
        pytest.fail("BLOCKED: owner_registry_unavailable")


def test_six_explicit_owner_outcomes_bind_to_real_registry_membership() -> None:
    reference = _owner_reference()
    outcomes = _owner_outcomes()
    get_account = GetAccountV1(SqliteRegistryRepositoryV1(reference))
    for account_id, organization_id, disposition in outcomes:
        try:
            account = get_account(OpaqueIdV1(account_id))
        except ValueError:
            pytest.fail("BLOCKED: owner_account_query_unavailable")
        if (
            account is None
            or account.provider_key != "claude"
            or account.lifecycle == "archived"
            or account.organization_id is None
            or account.organization_id.value != organization_id
        ):
            pytest.fail("BLOCKED: owner_outcome_registry_mismatch")
        if disposition == "verified" and (
            account.lifecycle != "active"
            or account.identity_state not in ("matched", "owner_confirmed")
            or not account.is_effective_monitoring_enabled
        ):
            pytest.fail("BLOCKED: verified_owner_account_not_monitoring")
