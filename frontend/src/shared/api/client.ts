import {
  apiClient,
  apiVersion,
  type ApiResultV1,
  type ApiTokenCredentialIssueV1,
  type ApiTokenPageV1,
  type ApiTokenSummaryV1,
  type CurrentSessionViewV1,
  type IamInitializationStateV1,
  type SafeProblemV1,
} from "../../generated/api";

export type {
  ApiTokenCredentialIssueV1,
  ApiTokenPageV1,
  ApiTokenSummaryV1,
  CurrentSessionViewV1,
  IamInitializationStateV1,
  SafeProblemV1,
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
  if (idempotent) headers["Idempotency-Key"] = crypto.randomUUID().replaceAll("-", "");
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
