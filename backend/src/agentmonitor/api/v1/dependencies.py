"""P01's explicit application-port bundles and per-request auth chain."""

from dataclasses import dataclass

from fastapi import Request

from agentmonitor.api.problem import ProblemError
from agentmonitor.api.v1.ollama_cloud_port import OllamaCloudConnectionPortV1
from agentmonitor.contracts.capacity_v1 import CapacityHealthPolicyV1
from agentmonitor.contracts.common_v1 import OpaqueIdV1
from agentmonitor.contracts.identity_access_v1 import (
    PrincipalV1,
    SecretInputV1,
    SessionSummaryV1,
    TokenCallerProofV1,
)
from agentmonitor.contracts.ollama_local_catalog_v1 import (
    LocalCatalogPortV1,
)
from agentmonitor.contracts.provider_system_v1 import ProviderConnectionPortV1
from agentmonitor.contracts.registry_billing_v1 import BillingConnectionPortV1
from agentmonitor.contracts.registry_coverage_v1 import (
    OrganizationProviderCoverageReadPortV1,
    OrganizationProviderCoverageWritePortV1,
)
from agentmonitor.modules.alerting.application.commands import (
    AcknowledgeAlertV1,
    MarkAlertReadV1,
    SnoozeAlertV1,
    UnsnoozeAlertV1,
)
from agentmonitor.modules.alerting.application.queries import (
    GetAlertV1,
    GetDashboardNotificationCountsV1,
    ListAlertHistoryV1,
    ListAlertsV1,
    ListDashboardNotificationsV1,
)
from agentmonitor.modules.alerting.application.rules import (
    ArchiveAlertRuleOverrideV1,
    CreateAlertRuleV1,
    GetAlertRuleV1,
    ListAlertRulesV1,
    UpdateAlertRuleV1,
)
from agentmonitor.modules.capacity.application.queries import (
    GetAccountCapacityV1,
    GetCapacityAggregateV1,
    GetCapacityAggregateV2,
    ListCapacityForecastsV1,
    ListCapacityHistoryV1,
    ListQuotaWindowsV1,
)
from agentmonitor.modules.collection_control.application.queries import (
    ListCollectionRunsV1,
)
from agentmonitor.modules.identity_access.application.api_tokens import (
    CreateApiTokenV1,
    ListApiTokensV1,
    ListIamSecurityEventsV1,
    ResolveBearerTokenV1,
    RevokeApiTokenV1,
    RotateApiTokenV1,
)
from agentmonitor.modules.identity_access.application.authorization import (
    AuthorizePrincipalV1,
)
from agentmonitor.modules.identity_access.application.bootstrap import (
    GetIamInitializationStateV1,
)
from agentmonitor.modules.identity_access.application.sessions import (
    AuthenticateAdministratorV1,
    ChangeAdministratorPasswordV1,
    ListSessionsV1,
    LogoutSessionV1,
    ResolveBrowserSessionV1,
    RevokeAllSessionsV1,
    RevokeSessionV1,
    VerifyCsrfV1,
)
from agentmonitor.modules.provider_system.application.queries import (
    GetProviderCapabilitiesV1,
    GetVerifiedQuotaIdentityV1,
)
from agentmonitor.modules.registry.application.accounts import (
    AlertScopeAndSubjectQueryV1,
    CapacityScopeMembershipQueryV2,
    EditAccountV1,
    GetAccountV1,
    ListAccountResourcesV1,
    ListAccountsV1,
    RegisterAccountV1,
)
from agentmonitor.modules.registry.application.discovery import (
    ListProviderInstallationsV1,
)
from agentmonitor.modules.registry.application.organizations import (
    CreateOrganizationV1,
    EditOrganizationV1,
    GetOrganizationV1,
    ListOrganizationsV1,
    ReorderOrganizationsV1,
)
from agentmonitor.modules.runtime_observation.application.owner_associations import (
    OwnerProcessAccountAssociationsV1,
)
from agentmonitor.modules.runtime_observation.application.queries import (
    GetAgentSessionV1,
    GetSessionTreeV1,
    ListAgentProcessesV1,
    ListAgentSessionsV1,
    ListLiveProcessLocationsV1,
)

SESSION_COOKIE = "agentmonitor_session"
CSRF_COOKIE = "agentmonitor_csrf"


@dataclass(frozen=True, slots=True)
class IamApiPortsV1:
    initialization: GetIamInitializationStateV1
    login: AuthenticateAdministratorV1
    resolve_session: ResolveBrowserSessionV1
    verify_csrf: VerifyCsrfV1
    authorize: AuthorizePrincipalV1
    logout: LogoutSessionV1
    change_password: ChangeAdministratorPasswordV1
    list_sessions: ListSessionsV1
    revoke_session: RevokeSessionV1
    revoke_other_sessions: RevokeAllSessionsV1
    resolve_bearer: ResolveBearerTokenV1
    list_tokens: ListApiTokensV1
    create_token: CreateApiTokenV1
    rotate_token: RotateApiTokenV1
    revoke_token: RevokeApiTokenV1
    list_events: ListIamSecurityEventsV1


@dataclass(frozen=True, slots=True)
class ObservationApiPortsV1:
    create_organization: CreateOrganizationV1
    edit_organization: EditOrganizationV1
    get_organization: GetOrganizationV1
    list_organizations: ListOrganizationsV1
    reorder_organizations: ReorderOrganizationsV1
    register_account: RegisterAccountV1
    edit_account: EditAccountV1
    get_account: GetAccountV1
    list_accounts: ListAccountsV1
    list_provider_installations: ListProviderInstallationsV1
    get_provider_capabilities: GetProviderCapabilitiesV1
    list_collection_runs: ListCollectionRunsV1
    get_account_capacity: GetAccountCapacityV1
    list_quota_windows: ListQuotaWindowsV1
    list_capacity_history: ListCapacityHistoryV1
    list_processes: ListAgentProcessesV1
    list_sessions: ListAgentSessionsV1
    get_session: GetAgentSessionV1
    get_session_tree: GetSessionTreeV1
    get_verified_quota_identity: GetVerifiedQuotaIdentityV1 | None = None
    list_live_process_locations: ListLiveProcessLocationsV1 | None = None
    provider_connections: ProviderConnectionPortV1 | None = None
    owner_process_associations: OwnerProcessAccountAssociationsV1 | None = None
    get_capacity_aggregate: GetCapacityAggregateV1 | None = None
    get_capacity_aggregate_v2: GetCapacityAggregateV2 | None = None
    list_capacity_forecasts: ListCapacityForecastsV1 | None = None
    registry_scope: AlertScopeAndSubjectQueryV1 | None = None
    registry_scope_v2: CapacityScopeMembershipQueryV2 | None = None
    list_account_resources: ListAccountResourcesV1 | None = None
    capacity_health_policy: CapacityHealthPolicyV1 | None = None
    ollama_local_catalog: LocalCatalogPortV1 | None = None
    ollama_cloud_connection: OllamaCloudConnectionPortV1 | None = None
    organization_coverage_read: OrganizationProviderCoverageReadPortV1 | None = None
    organization_coverage_write: OrganizationProviderCoverageWritePortV1 | None = None
    billing_connections: BillingConnectionPortV1 | None = None


@dataclass(frozen=True, slots=True)
class AlertApiPortsV1:
    create_rule: CreateAlertRuleV1
    update_rule: UpdateAlertRuleV1
    archive_rule: ArchiveAlertRuleOverrideV1
    get_rule: GetAlertRuleV1
    list_rules: ListAlertRulesV1
    get_alert: GetAlertV1
    list_alerts: ListAlertsV1
    list_alert_history: ListAlertHistoryV1
    list_notifications: ListDashboardNotificationsV1
    notification_counts: GetDashboardNotificationCountsV1
    acknowledge_alert: AcknowledgeAlertV1
    snooze_alert: SnoozeAlertV1
    unsnooze_alert: UnsnoozeAlertV1
    mark_alert_read: MarkAlertReadV1


@dataclass(frozen=True, slots=True)
class AuthorizedCallerV1:
    principal: PrincipalV1
    proof: TokenCallerProofV1
    session: SessionSummaryV1 | None


def ports(request: Request) -> IamApiPortsV1:
    available: IamApiPortsV1 | None = request.app.state.iam_ports
    if available is None:
        raise ProblemError(503, "iam_repository_unavailable")
    return available


def observation_ports(request: Request) -> ObservationApiPortsV1:
    available: ObservationApiPortsV1 | None = request.app.state.observation_ports
    if available is None:
        raise ProblemError(503, "observation_data_unavailable")
    return available


def alert_ports(request: Request) -> AlertApiPortsV1:
    available: AlertApiPortsV1 | None = getattr(request.app.state, "alert_ports", None)
    if available is None:
        raise ProblemError(503, "alert_repository_unavailable")
    return available


def correlation_id(request: Request) -> str:
    value = request.state.correlation_id
    if not isinstance(value, str):
        raise ProblemError(500, "internal_error")
    return value


def _secret(value: str | None) -> SecretInputV1 | None:
    return SecretInputV1(value) if value is not None else None


def authorize_request(
    request: Request,
    required_permission: str | None,
    *,
    cookie_only: bool = False,
    require_csrf: bool = False,
) -> AuthorizedCallerV1:
    services = ports(request)
    cookie = request.cookies.get(SESSION_COOKIE)
    header = request.headers.get("authorization")
    if cookie is not None and header is not None:
        raise ProblemError(400, "ambiguous_credentials")
    if cookie_only and header is not None:
        raise ProblemError(401, "dashboard_authentication_required")
    if header is not None:
        if not header.startswith("Bearer ") or len(header) > 519:
            raise ProblemError(401, "dashboard_authentication_required")
        credential = header[7:]
        bearer_result = services.resolve_bearer(
            SecretInputV1(credential), correlation_id=correlation_id(request)
        )
        if bearer_result.code != "authenticated" or bearer_result.principal is None:
            raise ProblemError(401, "dashboard_authentication_required")
        principal = bearer_result.principal
        proof = TokenCallerProofV1("api_bearer", SecretInputV1(credential))
        session = None
    else:
        if cookie is None or len(cookie) > 512 or not cookie.isascii():
            raise ProblemError(401, "dashboard_authentication_required")
        session_result = services.resolve_session(
            SecretInputV1(cookie), correlation_id=correlation_id(request)
        )
        if session_result.code != "authenticated" or session_result.principal is None:
            raise ProblemError(401, "dashboard_authentication_required")
        principal = session_result.principal
        session = session_result.session
        csrf_cookie = request.cookies.get(CSRF_COOKIE)
        csrf_header = request.headers.get("x-csrf-token")
        proof = TokenCallerProofV1(
            "browser_session",
            SecretInputV1(cookie),
            _secret(csrf_cookie),
            _secret(csrf_header),
        )
        if require_csrf:
            if session is None:
                raise ProblemError(401, "dashboard_authentication_required")
            csrf_decision = services.verify_csrf(
                session.session_id,
                _secret(csrf_cookie),
                _secret(csrf_header),
                correlation_id=correlation_id(request),
            )
            if csrf_decision.code != "valid":
                raise ProblemError(403, "csrf_validation_failed")
    if required_permission is not None:
        auth_decision = services.authorize(
            principal,
            required_permission,
            correlation_id=OpaqueIdV1(correlation_id(request)),
        )
        if not auth_decision.allowed:
            raise ProblemError(403, "permission_denied")
    return AuthorizedCallerV1(principal, proof, session)


def authenticate_documentation_request(request: Request) -> None:
    """Documentation discloses only the public schema to any valid M2 caller."""
    authorize_request(request, None)
