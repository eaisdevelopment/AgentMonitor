import {
  apiClient,
  apiVersion,
  type AccountCapacityViewV1,
  type AccountPageV1,
  type AccountViewV1,
  type AlertRuleCommandWireV1,
  type AlertRuleInputV1,
  type AlertRulePageV1,
  type AlertRuleWireV1,
  type AlertCommandWireV1,
  type AlertHistoryPageV1,
  type AlertNotificationCountsWireV1,
  type AlertNotificationPageV1,
  type AlertWireV1,
  type AgentProcessPageV1,
  type AgentProcessViewV1,
  type AgentSessionPageV1,
  type AgentSessionViewV1,
  type ApiResultV1,
  type ApiTokenCredentialIssueV1,
  type ApiTokenPageV1,
  type ApiTokenSummaryV1,
  type AvailabilityV1,
  type AgentProcessMetricPageV1,
  type AgentProcessMetricViewV1,
  type CapacityHistoryPageV1,
  type CapacityHistoryPointV1,
  type CollectionRunPageV1,
  type CollectionRunViewV1,
  type CurrentSessionViewV1,
  type ExactMetricFieldWireV1,
  type IamInitializationStateV1,
  type OrganizationPageV1,
  type OrganizationOrderingViewV1,
  type OrganizationViewV1,
  type OllamaLocalCatalogViewV1,
  type ProviderCapabilityDeclarationPageV1,
  type ProviderAccountIdentityViewV1,
  type ProviderConnectionViewV1,
  type ObservedAccountIdentityViewV1,
  type LiveProcessLocationPageV1,
  type LiveProcessLocationViewV1,
  type ProviderInstallationPageV1,
  type ProviderInstallationViewV1,
  type QuotaWindowPageV1,
  type QuotaWindowViewV1,
  type SafeProblemV1,
  type SessionTreeNodeV1,
  type SessionTreeViewV1,
} from "../../generated/api";

export type {
  ApiTokenCredentialIssueV1,
  ApiTokenPageV1,
  ApiTokenSummaryV1,
  AccountCapacityViewV1,
  AccountPageV1,
  AccountViewV1,
  AlertRuleCommandWireV1,
  AlertRuleInputV1,
  AlertRulePageV1,
  AlertRuleWireV1,
  AlertCommandWireV1,
  AlertHistoryPageV1,
  AlertNotificationCountsWireV1,
  AlertNotificationPageV1,
  AlertWireV1,
  AgentProcessPageV1,
  AgentProcessViewV1,
  AgentProcessMetricPageV1,
  AgentProcessMetricViewV1,
  AgentSessionPageV1,
  AgentSessionViewV1,
  AvailabilityV1,
  CapacityHistoryPageV1,
  CapacityHistoryPointV1,
  CollectionRunPageV1,
  CollectionRunViewV1,
  CurrentSessionViewV1,
  ExactMetricFieldWireV1,
  IamInitializationStateV1,
  OrganizationPageV1,
  OrganizationOrderingViewV1,
  OrganizationViewV1,
  OllamaLocalCatalogViewV1,
  ProviderCapabilityDeclarationPageV1,
  ProviderAccountIdentityViewV1,
  ProviderConnectionViewV1,
  ObservedAccountIdentityViewV1,
  LiveProcessLocationPageV1,
  LiveProcessLocationViewV1,
  ProviderInstallationPageV1,
  ProviderInstallationViewV1,
  QuotaWindowPageV1,
  QuotaWindowViewV1,
  SafeProblemV1,
  SessionTreeNodeV1,
  SessionTreeViewV1,
};

export type FoundationShellState = Readonly<{
  apiContractVersion: typeof apiVersion;
  message: string;
}>;

/**
 * Preserve the M1 foundation display while the P02 IAM shell uses the same
 * generated-client boundary for its approved M2 operations.
 */
export function getFoundationShellState(): FoundationShellState {
  return {
    apiContractVersion: apiVersion,
    message:
      "The local foundation is ready. Monitoring data will appear only after an approved provider integration is available.",
  };
}

export type ClientResult<T> = ApiResultV1<T>;

export type CapacityHistoryContinuation =
  | Readonly<{ kind: "available"; cursor: string }>
  | Readonly<{ kind: "complete" }>
  | Readonly<{ kind: "invalid" }>;

export type CapacityHistoryAppendResult =
  | Readonly<{ ok: true; pages: readonly CapacityHistoryPageV1[] }>
  | Readonly<{
      ok: false;
      reason:
        | "history_page_sequence_missing"
        | "history_page_query_mismatch"
        | "history_page_duplicate_observation";
    }>;

/** Interpret the generated cursor contract without guessing a missing cursor. */
export function capacityHistoryContinuation(
  page: CapacityHistoryPageV1["page"],
): CapacityHistoryContinuation {
  if (!page.has_more) return page.next_cursor === null ? { kind: "complete" } : { kind: "invalid" };
  if (page.next_cursor === null || page.next_cursor.trim().length === 0) return { kind: "invalid" };
  return { kind: "available", cursor: page.next_cursor };
}

/**
 * Append exactly one bounded API page while preserving every returned point.
 * Query drift and repeated observations fail closed instead of corrupting the
 * chart or making the retained-history count misleading.
 */
export function appendCapacityHistoryPage(
  pages: readonly CapacityHistoryPageV1[],
  nextPage: CapacityHistoryPageV1,
): CapacityHistoryAppendResult {
  const firstPage = pages[0];
  if (firstPage === undefined) return { ok: false, reason: "history_page_sequence_missing" };

  const sameQuery = (page: CapacityHistoryPageV1) =>
    page.subject_id === firstPage.subject_id &&
    page.metric === firstPage.metric &&
    page.series_kind === firstPage.series_kind;
  if (!pages.every(sameQuery) || !sameQuery(nextPage)) {
    return { ok: false, reason: "history_page_query_mismatch" };
  }

  const observationIds = new Set<string>();
  for (const page of [...pages, nextPage]) {
    for (const point of page.items) {
      if (observationIds.has(point.observation_id)) {
        return { ok: false, reason: "history_page_duplicate_observation" };
      }
      observationIds.add(point.observation_id);
    }
  }
  return { ok: true, pages: [...pages, nextPage] };
}

export class CsrfUnavailableError extends Error {
  constructor() { super("csrf_unavailable"); }
}

/** This is the sole handwritten transport boundary over generated IAM calls. */
function csrfHeader(): Readonly<Record<string, string>> {
  const cookie = document.cookie
    .split(";")
    .map((entry) => entry.trim())
    .find((entry) => entry.startsWith("agentmonitor_csrf="));
  if (cookie === undefined) throw new CsrfUnavailableError();
  return { "X-CSRF-Token": decodeURIComponent(cookie.slice("agentmonitor_csrf=".length)) };
}

function mutationHeaders(
  subject?: Readonly<{ id: string; recordVersion: number }>,
  idempotent = false,
): Readonly<Record<string, string>> {
  const headers: Record<string, string> = { ...csrfHeader() };
  if (subject !== undefined) {
    if (!/^[A-Za-z0-9_-]{1,64}$/.test(subject.id) ||
        !Number.isSafeInteger(subject.recordVersion) || subject.recordVersion < 1) {
      throw new Error("invalid_resource_version");
    }
    headers["If-Match"] = `"${subject.id}.${subject.recordVersion}"`;
  }
  if (idempotent) headers["Idempotency-Key"] = Array.from(crypto.getRandomValues(new Uint8Array(16)), byte => byte.toString(16).padStart(2, "0")).join("");
  return headers;
}

export const iam = Object.freeze({
  initialization: (): Promise<ClientResult<IamInitializationStateV1>> =>
    apiClient.iam_get_initialization_v1({}),
  currentSession: (): Promise<ClientResult<CurrentSessionViewV1>> =>
    apiClient.iam_get_current_session_v1({}),
  login: (credential: string): Promise<ClientResult<undefined>> =>
    apiClient.iam_login_v1({ body: { password: credential } }),
  logout: (session: CurrentSessionViewV1): Promise<ClientResult<undefined>> =>
    apiClient.iam_logout_v1({
      headers: mutationHeaders({ id: session.session_id, recordVersion: session.record_version }),
    }),
  changePassword: (
    session: CurrentSessionViewV1, currentCredential: string, nextCredential: string,
  ): Promise<ClientResult<undefined>> =>
    apiClient.iam_change_password_v1({
      body: { current_password: currentCredential, new_password: nextCredential },
      headers: mutationHeaders(
        { id: session.session_id, recordVersion: session.record_version }, true,
      ),
    }),
  listTokens: (cursor?: string): Promise<ClientResult<ApiTokenPageV1>> =>
    apiClient.iam_list_api_tokens_v1({ query: { limit: 50, ...(cursor ? { cursor } : {}) } }),
  createToken: (
    name: string, scopes: readonly string[], lifetimeSeconds: number | null,
  ): Promise<ClientResult<ApiTokenCredentialIssueV1>> =>
    apiClient.iam_create_api_token_v1({
      body: { name, scopes, lifetime_seconds: lifetimeSeconds },
      headers: mutationHeaders(undefined, true),
    }),
  rotateToken: (
    existing: ApiTokenSummaryV1,
  ): Promise<ClientResult<ApiTokenCredentialIssueV1>> =>
    apiClient.iam_rotate_api_token_v1({
      path: { token_id: existing.api_token_id }, body: {},
      headers: mutationHeaders(
        { id: existing.api_token_id, recordVersion: existing.record_version }, true,
      ),
    }),
  revokeToken: (existing: ApiTokenSummaryV1): Promise<ClientResult<undefined>> =>
    apiClient.iam_revoke_api_token_v1({
      path: { token_id: existing.api_token_id },
      headers: mutationHeaders(
        { id: existing.api_token_id, recordVersion: existing.record_version },
      ),
    }),
});

export const registry = Object.freeze({
  organizations: (signal?: AbortSignal): Promise<ClientResult<OrganizationPageV1>> =>
    apiClient.registry_list_organizations_v1({ query: { limit: 200 }, signal }),
  createOrganization: (
    name: string, description: string | null,
  ): Promise<ClientResult<OrganizationViewV1>> =>
    apiClient.registry_create_organization_v1({
      body: { name, description },
      headers: mutationHeaders(undefined, true),
    }),
  reorderOrganizations: (
    orderedOrganizationIds: readonly string[], expectedRegistryRevision: number,
  ): Promise<ClientResult<OrganizationOrderingViewV1>> =>
    apiClient.registry_reorder_organizations_v1({
      body: {
        ordered_organization_ids: [...orderedOrganizationIds],
        expected_registry_revision: expectedRegistryRevision,
      },
      headers: mutationHeaders(undefined, true),
    }),
  renameOrganization: (
    organization: OrganizationViewV1, name: string,
  ): Promise<ClientResult<OrganizationViewV1>> =>
    apiClient.registry_rename_organization_v1({
      path: { organization_id: organization.organization_id },
      body: { name },
      headers: mutationHeaders({ id: organization.organization_id, recordVersion: organization.record_version }),
    }),
  archiveOrganization: (
    organization: OrganizationViewV1,
  ): Promise<ClientResult<OrganizationViewV1>> =>
    apiClient.registry_archive_organization_v1({
      path: { organization_id: organization.organization_id }, body: {},
      headers: mutationHeaders({ id: organization.organization_id, recordVersion: organization.record_version }, true),
    }),
  restoreOrganization: (
    organization: OrganizationViewV1,
  ): Promise<ClientResult<OrganizationViewV1>> =>
    apiClient.registry_restore_organization_v1({
      path: { organization_id: organization.organization_id },
      headers: mutationHeaders({ id: organization.organization_id, recordVersion: organization.record_version }),
    }),
  registerAccount: (
    providerKey: string, friendlyName: string, organizationId: string | null,
  ): Promise<ClientResult<AccountViewV1>> =>
    apiClient.registry_register_account_v1({
      body: { provider_key: providerKey, friendly_name: friendlyName, organization_id: organizationId },
      headers: mutationHeaders(undefined, true),
    }),
  renameAccount: (
    account: AccountViewV1, friendlyName: string,
  ): Promise<ClientResult<AccountViewV1>> =>
    apiClient.registry_rename_account_v1({
      path: { account_id: account.account_id },
      body: { friendly_name: friendlyName },
      headers: mutationHeaders({ id: account.account_id, recordVersion: account.record_version }),
    }),
  assignAccount: (
    account: AccountViewV1, organizationId: string | null,
  ): Promise<ClientResult<AccountViewV1>> =>
    apiClient.registry_assign_account_organization_v1({
      path: { account_id: account.account_id },
      body: { organization_id: organizationId },
      headers: mutationHeaders({ id: account.account_id, recordVersion: account.record_version }),
    }),
  setAccountMonitoring: (
    account: AccountViewV1, preference: "enabled" | "disabled",
  ): Promise<ClientResult<AccountViewV1>> =>
    apiClient.registry_set_account_monitoring_v1({
      path: { account_id: account.account_id },
      body: { monitoring_preference: preference },
      headers: mutationHeaders({ id: account.account_id, recordVersion: account.record_version }),
    }),
  archiveAccount: (account: AccountViewV1): Promise<ClientResult<AccountViewV1>> =>
    apiClient.registry_archive_account_v1({
      path: { account_id: account.account_id }, body: {},
      headers: mutationHeaders({ id: account.account_id, recordVersion: account.record_version }, true),
    }),
  restoreAccount: (account: AccountViewV1): Promise<ClientResult<AccountViewV1>> =>
    apiClient.registry_restore_account_v1({
      path: { account_id: account.account_id },
      headers: mutationHeaders({ id: account.account_id, recordVersion: account.record_version }),
    }),
  accounts: (
    signal?: AbortSignal,
    cursor?: string,
  ): Promise<ClientResult<AccountPageV1>> =>
    apiClient.registry_list_accounts_v1({
      query: { limit: 200, ...(cursor ? { cursor } : {}) },
      signal,
    }),
  account: (
    accountId: string,
    signal?: AbortSignal,
  ): Promise<ClientResult<AccountViewV1>> =>
    apiClient.registry_get_account_v1({ path: { account_id: accountId }, signal }),
  providerInstallations: (
    signal?: AbortSignal,
  ): Promise<ClientResult<ProviderInstallationPageV1>> =>
    apiClient.registry_list_provider_installations_v1({ query: { limit: 200 }, signal }),
});

export const providers = Object.freeze({
  ollamaLocalCatalog: (signal?: AbortSignal): Promise<ClientResult<OllamaLocalCatalogViewV1>> =>
    apiClient.provider_get_ollama_local_catalog_v1({ signal }),
  connection: (accountId: string, signal?: AbortSignal): Promise<ClientResult<ProviderConnectionViewV1>> =>
    apiClient.provider_get_connection_v1({ path: { account_id: accountId }, signal }),
  connect: (account: AccountViewV1, expectedEmail: string): Promise<ClientResult<ProviderConnectionViewV1>> =>
    apiClient.provider_start_connection_v1({
      path: { account_id: account.account_id }, body: { expected_email: expectedEmail },
      headers: mutationHeaders({ id: account.account_id, recordVersion: account.record_version }, true),
    }),
  cancelConnection: (accountId: string, flowId: string): Promise<ClientResult<ProviderConnectionViewV1>> =>
    apiClient.provider_cancel_connection_v1({
      path: { account_id: accountId }, body: { flow_id: flowId }, headers: mutationHeaders(),
    }),
  observedAccountIdentity: (
    accountId: string,
    signal?: AbortSignal,
  ): Promise<ClientResult<ObservedAccountIdentityViewV1>> =>
    apiClient.provider_get_observed_account_identity_v1({ path: { account_id: accountId }, signal }),
  accountIdentity: (
    accountId: string,
    signal?: AbortSignal,
  ): Promise<ClientResult<ProviderAccountIdentityViewV1>> =>
    apiClient.provider_get_account_identity_v1({ path: { account_id: accountId }, signal }),
  capabilities: (
    providerKey: string,
    signal?: AbortSignal,
  ): Promise<ClientResult<ProviderCapabilityDeclarationPageV1>> =>
    apiClient.provider_get_capabilities_v1({ path: { provider_key: providerKey }, signal }),
});

export const collections = Object.freeze({
  runs: (signal?: AbortSignal): Promise<ClientResult<CollectionRunPageV1>> =>
    apiClient.collection_list_runs_v1({ query: { limit: 50 }, signal }),
});

export const alerts = Object.freeze({
  notifications: (
    scope?: Readonly<{ kind: "organization"; id: string }>, cursor?: string,
    signal?: AbortSignal,
  ): Promise<ClientResult<AlertNotificationPageV1>> =>
    apiClient.alert_list_notifications_v1({
      query: { limit: 100, ...(scope ? { scope_kind: scope.kind, scope_id: scope.id } : {}),
        ...(cursor ? { cursor } : {}) }, signal,
    }),
  counts: (
    scope?: Readonly<{ kind: "organization"; id: string }>, signal?: AbortSignal,
  ): Promise<ClientResult<AlertNotificationCountsWireV1>> =>
    apiClient.alert_get_notification_counts_v1({
      query: scope ? { scope_kind: scope.kind, scope_id: scope.id } : {}, signal,
    }),
  history: (
    alertId: string, cursor?: string, signal?: AbortSignal,
  ): Promise<ClientResult<AlertHistoryPageV1>> =>
    apiClient.alert_list_history_v1({
      path: { alert_id: alertId },
      query: { limit: 200, ...(cursor === undefined ? {} : { cursor }) },
      signal,
    }),
  acknowledge: (alert: AlertWireV1): Promise<ClientResult<AlertCommandWireV1>> =>
    apiClient.alert_acknowledge_v1({
      path: { alert_id: alert.alert_id },
      headers: mutationHeaders({ id: alert.alert_id, recordVersion: alert.record_version }, true),
    }),
  snooze: (alert: AlertWireV1, durationSeconds: number): Promise<ClientResult<AlertCommandWireV1>> =>
    apiClient.alert_snooze_v1({
      path: { alert_id: alert.alert_id }, body: { duration_seconds: durationSeconds },
      headers: mutationHeaders({ id: alert.alert_id, recordVersion: alert.record_version }, true),
    }),
  unsnooze: (alert: AlertWireV1): Promise<ClientResult<AlertCommandWireV1>> =>
    apiClient.alert_unsnooze_v1({
      path: { alert_id: alert.alert_id },
      headers: mutationHeaders({ id: alert.alert_id, recordVersion: alert.record_version }, true),
    }),
  markRead: (alert: AlertWireV1): Promise<ClientResult<AlertCommandWireV1>> =>
    apiClient.alert_mark_read_v1({
      path: { alert_id: alert.alert_id },
      headers: mutationHeaders({ id: alert.alert_id, recordVersion: alert.notification_revision }, true),
    }),
  rules: (cursor?: string, signal?: AbortSignal): Promise<ClientResult<AlertRulePageV1>> =>
    apiClient.alert_list_rules_v1({ query: { limit: 200, ...(cursor ? { cursor } : {}) }, signal }),
  createRule: (input: AlertRuleInputV1): Promise<ClientResult<AlertRuleCommandWireV1>> =>
    apiClient.alert_create_rule_v1({ body: input, headers: mutationHeaders(undefined, true) }),
  updateRule: (
    rule: AlertRuleWireV1, input: AlertRuleInputV1,
  ): Promise<ClientResult<AlertRuleCommandWireV1>> => {
    if (rule.rule_id === null) throw new Error("builtin_rule_cannot_be_updated");
    return apiClient.alert_update_rule_v1({
      path: { rule_id: rule.rule_id }, body: input,
      headers: mutationHeaders({ id: rule.rule_id, recordVersion: rule.record_version }, true),
    });
  },
  archiveRule: (rule: AlertRuleWireV1): Promise<ClientResult<AlertRuleCommandWireV1>> => {
    if (rule.rule_id === null) throw new Error("builtin_rule_cannot_be_archived");
    return apiClient.alert_archive_rule_v1({
      path: { rule_id: rule.rule_id },
      headers: mutationHeaders({ id: rule.rule_id, recordVersion: rule.record_version }, true),
    });
  },
});

export const capacity = Object.freeze({
  account: (
    accountId: string,
    signal?: AbortSignal,
  ): Promise<ClientResult<AccountCapacityViewV1>> =>
    apiClient.capacity_get_account_v1({ path: { account_id: accountId }, signal }),
  quotaWindows: (
    accountId: string,
    signal?: AbortSignal,
  ): Promise<ClientResult<QuotaWindowPageV1>> =>
    apiClient.capacity_list_quota_windows_v1({
      path: { account_id: accountId }, query: { limit: 200 }, signal,
    }),
  history: (
    options: Readonly<{
      accountId: string;
      rangeFrom: string;
      before: string;
      metric?: "used" | "remaining" | "limit" | "remaining_ratio";
      seriesKind?: "raw_provider" | "poll_snapshot" | "derived";
      cursor?: string;
      signal?: AbortSignal;
    }>,
  ): Promise<ClientResult<CapacityHistoryPageV1>> =>
    apiClient.capacity_list_history_v1({
      query: {
        subject_id: options.accountId,
        from: options.rangeFrom,
        before: options.before,
        metric: options.metric ?? "remaining_ratio",
        series_kind: options.seriesKind ?? "poll_snapshot",
        limit: 200,
        ...(options.cursor === undefined ? {} : { cursor: options.cursor }),
      },
      signal: options.signal,
    }),
});

export const runtime = Object.freeze({
  processLocations: (signal?: AbortSignal): Promise<ClientResult<LiveProcessLocationPageV1>> =>
    apiClient.runtime_list_process_locations_v1({ signal }),
  setProcessAccount: (process: LiveProcessLocationViewV1, accountId: string | null): Promise<ClientResult<LiveProcessLocationViewV1>> => {
    const key = process.association_key;
    const version = process.association_record_version ?? 0;
    if (!key || !/^[a-f0-9]{64}$/.test(key) || !Number.isSafeInteger(version) || version < 0) throw new Error("invalid_process_revision");
    return apiClient.runtime_set_process_account_association_v1({
      path: { association_key: key },
      body: { account_id: accountId, owner_confirmed: true },
      headers: { ...csrfHeader(), "If-Match": '"' + key + "." + version + '"' },
    });
  },
  processes: (signal?: AbortSignal): Promise<ClientResult<AgentProcessPageV1>> =>
    apiClient.runtime_list_processes_v1({ query: { limit: 200 }, signal }),
  processMetrics: (
    signal?: AbortSignal,
  ): Promise<ClientResult<AgentProcessMetricPageV1>> =>
    apiClient.runtime_list_process_metrics_v1({ query: { limit: 200 }, signal }),
  sessions: (
    options: Readonly<{ accountId?: string; signal?: AbortSignal }> = {},
  ): Promise<ClientResult<AgentSessionPageV1>> =>
    apiClient.runtime_list_sessions_v1({
      query: { limit: 200, ...(options.accountId === undefined ? {} : { account_id: options.accountId }) },
      signal: options.signal,
    }),
  session: (
    sessionId: string,
    signal?: AbortSignal,
  ): Promise<ClientResult<AgentSessionViewV1>> =>
    apiClient.runtime_get_session_v1({ path: { session_id: sessionId }, signal }),
  sessionTree: (
    sessionId: string,
    signal?: AbortSignal,
  ): Promise<ClientResult<SessionTreeViewV1>> =>
    apiClient.runtime_get_session_tree_v1({
      path: { session_id: sessionId },
      query: { depth_limit: 8, node_limit: 200 },
      signal,
    }),
});

/** Only the versioned safe code/correlation is rendered, never rejected input. */
export function safeProblemMessage(problem: SafeProblemV1): string {
  let explanation: string;
  switch (problem.code) {
    case "invalid_dashboard_credentials": explanation = "Sign-in failed. Check the password and try again."; break;
    case "login_throttled": explanation = "Too many attempts. Wait before trying again."; break;
    case "csrf_validation_failed": explanation = "Security proof rejected. Sign in again; the action was not completed."; break;
    case "precondition_failed": explanation = "This item changed. Refresh before trying again."; break;
    case "one_time_secret_not_replayable": explanation = "This action was already committed. The secret cannot be shown again."; break;
    case "scope_escalation_denied": explanation = "Those scopes exceed this caller's permission."; break;
    case "dashboard_authentication_required": explanation = "Your dashboard session ended. Sign in again."; break;
    default: explanation = "The request could not be completed. Try again or check local diagnostics.";
  }
  const code = /^[a-z][a-z0-9_]{0,63}$/.test(problem.code) ? problem.code : "unknown";
  const reference = /^[A-Za-z0-9._:-]{1,64}$/.test(problem.correlation_id)
    ? problem.correlation_id : "unavailable";
  return `${explanation} Code: ${code}. Reference: ${reference}.`;
}
