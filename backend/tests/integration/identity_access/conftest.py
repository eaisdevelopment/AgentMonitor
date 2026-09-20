"""Real M01 installation fixture: production migration and bootstrap, no seeded rows."""

import secrets
from pathlib import Path

import pytest
from agentmonitor.adapters.identity_access.argon2_password import Argon2PasswordV1
from agentmonitor.adapters.persistence._shared.sqlite.core.policy import DatabaseRefV1
from agentmonitor.adapters.persistence._shared.sqlite.schema.compatibility import (
    migrate_to_head,
)
from agentmonitor.adapters.persistence.identity_access.sqlite.repository import (
    SqliteIdentityAccessRepositoryV1,
)
from agentmonitor.contracts.identity_access_v1 import SecretInputV1
from agentmonitor.modules.identity_access.application.bootstrap import (
    BootstrapAdministratorV1,
)


@pytest.fixture
def real_iam_installation(
    tmp_path: Path,
) -> tuple[DatabaseRefV1, str]:
    reference = DatabaseRefV1(tmp_path / "agentmonitor.db", tmp_path)
    migrate_to_head(reference)
    owner_credential = secrets.token_urlsafe(32)
    outcome = BootstrapAdministratorV1(
        SqliteIdentityAccessRepositoryV1(reference), Argon2PasswordV1()
    )(SecretInputV1(owner_credential), correlation_id="m01-story2-bootstrap")
    assert outcome.code == "created"
    return reference, owner_credential
