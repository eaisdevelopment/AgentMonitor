"""Static negative-drift checks on the real M2 FastAPI schema declaration."""

from copy import deepcopy

import pytest
from agentmonitor.composition.bootstrap import create_iam_schema_application
from fastapi.openapi.models import OpenAPI

from tooling.foundation.openapi_client import (
    OpenApiGenerationError,
    validate_iam_openapi,
)

EXPECTED_SUCCESS = {
    "runtime_set_process_account_association_v1": ("200", "LiveProcessLocationViewV1"),
    "provider_get_connection_v1": ("200", "ProviderConnectionViewV1"),
    "provider_start_connection_v1": ("202", "ProviderConnectionViewV1"),
    "provider_cancel_connection_v1": ("200", "ProviderConnectionViewV1"),
    "provider_get_observed_account_identity_v1": (
        "200",
        "ObservedAccountIdentityViewV1",
    ),
    "provider_get_account_identity_v1": ("200", "ProviderAccountIdentityViewV1"),
    "runtime_list_process_locations_v1": ("200", "LiveProcessLocationPageV1"),
    "registry_register_account_v1": ("201", "AccountViewV1"),
    "registry_get_account_v1": ("200", "AccountViewV1"),
    "registry_rename_account_v1": ("200", "AccountViewV1"),
    "registry_assign_account_organization_v1": ("200", "AccountViewV1"),
    "registry_set_account_monitoring_v1": ("200", "AccountViewV1"),
    "registry_archive_account_v1": ("200", "AccountViewV1"),
    "registry_restore_account_v1": ("200", "AccountViewV1"),
    "registry_list_organizations_v1": ("200", "OrganizationPageV1"),
    "registry_create_organization_v1": ("201", "OrganizationViewV1"),
    "registry_get_organization_v1": ("200", "OrganizationViewV1"),
    "registry_rename_organization_v1": ("200", "OrganizationViewV1"),
    "registry_reorder_organizations_v1": ("200", "OrganizationOrderingViewV1"),
    "registry_archive_organization_v1": ("200", "OrganizationViewV1"),
    "registry_restore_organization_v1": ("200", "OrganizationViewV1"),
    "registry_list_accounts_v1": ("200", "AccountPageV1"),
    "registry_list_provider_installations_v1": ("200", "ProviderInstallationPageV1"),
    "provider_get_capabilities_v1": ("200", "ProviderCapabilityDeclarationPageV1"),
    "collection_list_runs_v1": ("200", "CollectionRunPageV1"),
    "capacity_get_account_v1": ("200", "AccountCapacityViewV1"),
    "capacity_list_quota_windows_v1": ("200", "QuotaWindowPageV1"),
    "capacity_list_history_v1": ("200", "CapacityHistoryPageV1"),
    "runtime_list_processes_v1": ("200", "AgentProcessPageV1"),
    "runtime_list_process_metrics_v1": ("200", "AgentProcessMetricPageV1"),
    "runtime_list_sessions_v1": ("200", "AgentSessionPageV1"),
    "runtime_get_session_v1": ("200", "AgentSessionViewV1"),
    "runtime_get_session_tree_v1": ("200", "SessionTreeViewV1"),
    "iam_get_initialization_v1": ("200", "IamInitializationStateV1"),
    "iam_login_v1": ("204", None),
    "iam_get_current_session_v1": ("200", "CurrentSessionViewV1"),
    "iam_logout_v1": ("204", None),
    "iam_change_password_v1": ("204", None),
    "iam_list_sessions_v1": ("200", "BrowserSessionPageV1"),
    "iam_revoke_session_v1": ("204", None),
    "iam_revoke_other_sessions_v1": ("200", "SessionRevocationSummaryV1"),
    "iam_list_api_tokens_v1": ("200", "ApiTokenPageV1"),
    "iam_create_api_token_v1": ("201", "ApiTokenCredentialIssueV1"),
    "iam_rotate_api_token_v1": ("201", "ApiTokenCredentialIssueV1"),
    "iam_revoke_api_token_v1": ("204", None),
    "iam_list_security_events_v1": ("200", "IamSecurityEventPageV1"),
    "alert_acknowledge_v1": ("200", "AlertCommandWireV1"),
    "alert_archive_rule_v1": ("200", "AlertRuleCommandWireV1"),
    "alert_create_rule_v1": ("201", "AlertRuleCommandWireV1"),
    "alert_get_alert_v1": ("200", "AlertWireV1"),
    "alert_get_notification_counts_v1": ("200", "AlertNotificationCountsWireV1"),
    "alert_get_rule_v1": ("200", "AlertRuleWireV1"),
    "alert_list_alerts_v1": ("200", "AlertPageV1"),
    "alert_list_history_v1": ("200", "AlertHistoryPageV1"),
    "alert_list_notifications_v1": ("200", "AlertNotificationPageV1"),
    "alert_list_rules_v1": ("200", "AlertRulePageV1"),
    "alert_mark_read_v1": ("200", "AlertCommandWireV1"),
    "alert_snooze_v1": ("200", "AlertCommandWireV1"),
    "alert_unsnooze_v1": ("200", "AlertCommandWireV1"),
    "alert_update_rule_v1": ("200", "AlertRuleCommandWireV1"),
    "capacity_get_scope_v1": ("200", "CapacityScopeViewV1"),
    "capacity_list_forecasts_v1": ("200", "CapacityForecastPageV1"),
    "operations_get_diagnostics_v1": ("200", "OperationsDiagnosticsWireV1"),
    "operations_get_health_v1": ("200", "OperationsHealthWireV1"),
    "operations_get_liveness_v1": ("200", "OperationsLivenessWireV1"),
    "operations_get_readiness_v1": ("200", "OperationsReadinessWireV1"),
    "operations_get_versions_v1": ("200", "OperationsVersionsWireV1"),
}
EXPECTED_ERRORS = frozenset(
    {
        "400",
        "401",
        "403",
        "404",
        "405",
        "409",
        "412",
        "413",
        "415",
        "422",
        "428",
        "429",
        "500",
        "503",
        "504",
    }
)
EXPECTED_REQUESTS = {
    "runtime_set_process_account_association_v1": "SetProcessAccountAssociationInputV1",
    "provider_start_connection_v1": "StartProviderConnectionInputV1",
    "provider_cancel_connection_v1": "CancelProviderConnectionInputV1",
    "registry_register_account_v1": "RegisterAccountInputV1",
    "registry_rename_account_v1": "RenameAccountInputV1",
    "registry_assign_account_organization_v1": "AssignAccountOrganizationInputV1",
    "registry_set_account_monitoring_v1": "SetAccountMonitoringInputV1",
    "registry_archive_account_v1": "ArchiveAccountInputV1",
    "registry_create_organization_v1": "CreateOrganizationInputV1",
    "registry_reorder_organizations_v1": "ReorderOrganizationsInputV1",
    "registry_rename_organization_v1": "RenameOrganizationInputV1",
    "registry_archive_organization_v1": "ArchiveOrganizationInputV1",
    "iam_login_v1": "LoginInputV1",
    "iam_change_password_v1": "ChangeAdministratorPasswordInputV1",
    "iam_create_api_token_v1": "CreateApiTokenInputV1",
    "iam_rotate_api_token_v1": "RotateApiTokenInputV1",
    "alert_create_rule_v1": "AlertRuleInputV1",
    "alert_snooze_v1": "SnoozeAlertInputV1",
    "alert_update_rule_v1": "AlertRuleInputV1",
}


def test_generator_rejects_changed_policy_on_every_frozen_operation() -> None:
    schema = create_iam_schema_application().openapi()
    assert len(validate_iam_openapi(schema)) == len(EXPECTED_SUCCESS)
    mutations: tuple[tuple[str, object], ...] = (
        ("x-agentmonitor-auth-profile", "preauth_loopback"),
        ("x-agentmonitor-required-permission", "read:diagnostics"),
        ("x-agentmonitor-application-port", "UnknownPortV1"),
        ("x-agentmonitor-replay-policy", "unknown_replay"),
        ("x-agentmonitor-error-schema", "OtherProblemV1"),
        ("security", [{"BearerTokenV1": []}]),
    )
    tested = 0
    for path, methods in schema["paths"].items():
        for method, operation in methods.items():
            for field, replacement in mutations:
                if operation[field] == replacement:
                    continue
                changed = deepcopy(schema)
                changed["paths"][path][method][field] = replacement
                with pytest.raises(OpenApiGenerationError):
                    validate_iam_openapi(changed)
                tested += 1
    assert tested >= 60


def test_generator_rejects_success_schema_drift_for_all_operations() -> None:
    schema = create_iam_schema_application().openapi()
    assert len(validate_iam_openapi(schema)) == len(EXPECTED_SUCCESS) == 67
    seen: set[str] = set()
    for path, methods in schema["paths"].items():
        for method, operation in methods.items():
            identifier = operation["operationId"]
            seen.add(identifier)
            expected_status, expected_model = EXPECTED_SUCCESS[identifier]
            success = {
                status: response
                for status, response in operation["responses"].items()
                if status.startswith("2")
            }
            assert list(success) == [expected_status]
            if expected_model is None:
                assert "content" not in success[expected_status]
                changed = deepcopy(schema)
                changed["paths"][path][method]["responses"][expected_status][
                    "content"
                ] = {
                    "application/json": {
                        "schema": {"$ref": "#/components/schemas/CurrentSessionViewV1"}
                    }
                }
            else:
                assert success[expected_status]["content"]["application/json"][
                    "schema"
                ] == {"$ref": f"#/components/schemas/{expected_model}"}
                changed = deepcopy(schema)
                changed["paths"][path][method]["responses"][expected_status]["content"][
                    "application/json"
                ]["schema"] = {
                    "$ref": "#/components/schemas/CurrentSessionViewV1"
                    if expected_model != "CurrentSessionViewV1"
                    else "#/components/schemas/ApiTokenPageV1"
                }
            with pytest.raises(OpenApiGenerationError, match="success_schema_mismatch"):
                validate_iam_openapi(changed)
            status_changed = deepcopy(schema)
            responses = status_changed["paths"][path][method]["responses"]
            success_response = responses.pop(expected_status)
            responses["201" if expected_status == "200" else "200"] = success_response
            with pytest.raises(OpenApiGenerationError, match="success_schema_mismatch"):
                validate_iam_openapi(status_changed)
    assert seen == set(EXPECTED_SUCCESS)


def test_iam_request_component_names_match_approved_catalog() -> None:
    schema = create_iam_schema_application().openapi()
    assert len(validate_iam_openapi(schema)) == len(EXPECTED_SUCCESS)
    seen: set[str] = set()
    for path, methods in schema["paths"].items():
        for method, operation in methods.items():
            identifier = operation["operationId"]
            seen.add(identifier)
            expected = EXPECTED_REQUESTS.get(identifier)
            if expected is None:
                assert "requestBody" not in operation
            else:
                assert operation["requestBody"]["content"]["application/json"][
                    "schema"
                ] == {"$ref": f"#/components/schemas/{expected}"}
            changed = deepcopy(schema)
            wrong = (
                "CreateApiTokenInputV1"
                if expected == "LoginInputV1"
                else "LoginInputV1"
            )
            changed["paths"][path][method]["requestBody"] = {
                "content": {
                    "application/json": {
                        "schema": {"$ref": f"#/components/schemas/{wrong}"}
                    }
                },
                "required": True,
            }
            with pytest.raises(OpenApiGenerationError, match="request_schema_mismatch"):
                validate_iam_openapi(changed)
    assert seen == set(EXPECTED_SUCCESS)


def test_generator_validates_openapi_structure_with_fastapi_model() -> None:
    schema = create_iam_schema_application().openapi()
    OpenAPI.model_validate(schema)
    changed = deepcopy(schema)
    changed["info"]["termsOfService"] = 42
    with pytest.raises(OpenApiGenerationError, match="openapi_schema_invalid"):
        validate_iam_openapi(changed)


def test_operations_source_revision_is_an_additive_optional_v1_response_field() -> None:
    """M5-CDX-GATE-007: old V1 clients may ignore the service revision fact."""

    schema = create_iam_schema_application().openapi()
    versions = schema["components"]["schemas"]["OperationsVersionsWireV1"]
    assert versions["properties"]["source_revision"] == {
        "$ref": "#/components/schemas/OperationsVersionValueWireV1"
    }
    assert "source_revision" not in versions["required"]


def test_generator_rejects_missing_safe_error_statuses_on_every_operation() -> None:
    schema = create_iam_schema_application().openapi()
    assert len(validate_iam_openapi(schema)) == len(EXPECTED_SUCCESS)
    deleted_all = deepcopy(schema)
    responses = deleted_all["paths"]["/api/v1/session"]["get"]["responses"]
    for status in EXPECTED_ERRORS:
        responses.pop(status)
    with pytest.raises(OpenApiGenerationError, match="error_status_missing"):
        validate_iam_openapi(deleted_all)
    checked = 0
    for path, methods in schema["paths"].items():
        for method, operation in methods.items():
            assert EXPECTED_ERRORS <= set(operation["responses"])
            for status in EXPECTED_ERRORS:
                changed = deepcopy(schema)
                changed["paths"][path][method]["responses"].pop(status)
                with pytest.raises(
                    OpenApiGenerationError, match="error_status_missing"
                ):
                    validate_iam_openapi(changed)
                checked += 1
    assert checked == len(EXPECTED_SUCCESS) * len(EXPECTED_ERRORS)
