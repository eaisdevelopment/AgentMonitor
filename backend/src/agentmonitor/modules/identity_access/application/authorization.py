"""M01 explicit permission decisions, independent of transport and providers."""

from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.identity_access_v1 import (
    AuthorizationDecisionV1,
    PrincipalV1,
)

BROWSER_PERMISSIONS_V1: tuple[str, ...] = (
    "read:self",
    "write:self",
    "write:sessions",
    "write:tokens",
    "read:diagnostics",
    "read:telemetry",
    "read:accounts",
    "write:accounts",
    "read:status",
)
BEARER_PERMISSIONS_V1 = frozenset(
    {
        "read:accounts",
        "write:accounts",
        "read:diagnostics",
        "read:status",
        "read:telemetry",
        "write:tokens",
    }
)


class AuthorizePrincipalV1:
    """Single-admin does not bypass explicit route permission checks."""

    def __call__(
        self,
        principal: PrincipalV1,
        required_permission: str,
        *,
        correlation_id: OpaqueIdV1,
    ) -> AuthorizationDecisionV1:
        allowed = required_permission in principal.effective_permissions and (
            (
                principal.authentication_method == "browser_session"
                and required_permission in BROWSER_PERMISSIONS_V1
            )
            or (
                principal.authentication_method == "api_bearer"
                and required_permission in BEARER_PERMISSIONS_V1
            )
        )
        return AuthorizationDecisionV1(
            allowed,
            "allowed" if allowed else "permission_denied",
            required_permission,
            principal.principal_id,
            correlation_id,
        )
