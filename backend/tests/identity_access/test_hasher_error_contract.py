"""A real Argon2 failure crosses the M01 application port, not an adapter seam."""

import pytest
from agentmonitor.adapters.identity_access.argon2_password import Argon2PasswordV1
from agentmonitor.modules.identity_access.application.errors import (
    PasswordHasherUnavailableV1,
)


def test_malformed_real_argon2_material_uses_safe_m01_port_error() -> None:
    with pytest.raises(
        PasswordHasherUnavailableV1, match="password_hasher_unavailable"
    ):
        Argon2PasswordV1().verify("$argon2id$invalid", "bounded-candidate")
