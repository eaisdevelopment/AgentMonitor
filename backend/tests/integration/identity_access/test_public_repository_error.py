"""M01 public unavailable error over a real migrated SQLite installation."""

import stat

import pytest
from agentmonitor.adapters.persistence._shared.sqlite.core.policy import DatabaseRefV1
from agentmonitor.adapters.persistence.identity_access.sqlite.repository import (
    SqliteIdentityAccessRepositoryV1,
)
from agentmonitor.modules.identity_access.application.bootstrap import (
    GetIamInitializationStateV1,
)
from agentmonitor.modules.identity_access.application.errors import (
    IamRepositoryUnavailableV1,
)


def test_public_use_case_exposes_safe_unavailable_on_real_file_mode_denial(
    real_iam_installation: tuple[DatabaseRefV1, str],
) -> None:
    reference, _owner_credential = real_iam_installation
    repository = SqliteIdentityAccessRepositoryV1(reference)
    use_case = GetIamInitializationStateV1(repository)
    assert use_case().state == "initialized"
    path = reference._path
    prior_mode = stat.S_IMODE(path.stat().st_mode)
    assert prior_mode == 0o600
    path.chmod(0o000)
    try:
        with pytest.raises(IamRepositoryUnavailableV1) as denied:
            use_case()
        assert str(denied.value) == "iam_repository_unavailable"
    finally:
        path.chmod(prior_mode)
    assert use_case().state == "initialized"
