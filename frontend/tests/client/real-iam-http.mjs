// Real generated-client transport check. Input is a pipe, never argv or env.
import { randomBytes } from 'node:crypto';
import { apiClient, operationIds } from '../../src/generated/api/index.ts';

function requireResult(condition, code) {
  if (!condition) throw new Error(code);
}

async function run() {
  const chunks = [];
  for await (const chunk of process.stdin) chunks.push(chunk);
  const { origin, password } = JSON.parse(Buffer.concat(chunks).toString('utf8'));
  requireResult(typeof origin === 'string' && typeof password === 'string', 'input_invalid');

  const state = await apiClient.iam_get_initialization_v1({ baseUrl: origin });
  requireResult(state.ok && state.data.state === 'initialized', 'initialization_failed');

  const unauthenticated = await apiClient.iam_get_current_session_v1({ baseUrl: origin });
  requireResult(!unauthenticated.ok && unauthenticated.status === 401, 'authentication_denial_failed');
  requireResult(unauthenticated.problem.code === 'dashboard_authentication_required', 'authentication_problem_decode_failed');
  requireResult(typeof unauthenticated.problem.correlation_id === 'string' && unauthenticated.problem.correlation_id.length > 0, 'authentication_correlation_missing');

  const login = await apiClient.iam_login_v1({
    baseUrl: origin,
    body: { password },
    headers: { Origin: origin },
  });
  requireResult(login.ok && login.status === 204, 'login_failed');
  const cookiePairs = login.headers.getSetCookie().map((value) => value.split(';', 1)[0]);
  requireResult(cookiePairs.length === 2, 'cookie_issue_failed');
  const cookie = cookiePairs.join('; ');
  const csrfPair = cookiePairs.find((pair) => pair.startsWith('agentmonitor_csrf='));
  requireResult(typeof csrfPair === 'string', 'csrf_cookie_missing');
  const csrf = csrfPair.slice('agentmonitor_csrf='.length);
  requireResult(csrf.length > 0, 'csrf_cookie_empty');

  const current = await apiClient.iam_get_current_session_v1({
    baseUrl: origin,
    headers: { Cookie: cookie },
  });
  requireResult(current.ok && current.data.state === 'active', 'current_session_failed');

  const token = await apiClient.iam_create_api_token_v1({
    baseUrl: origin,
    body: { name: 'generated-client-check', scopes: ['write:tokens'] },
    headers: {
      Cookie: cookie,
      Origin: origin,
      'X-CSRF-Token': csrf,
      'Idempotency-Key': randomBytes(24).toString('base64url'),
    },
  });
  requireResult(token.ok && token.status === 201, 'token_issue_failed');

  const bearer = `Bearer ${token.data.bearer_credential}`;
  const listed = await apiClient.iam_list_api_tokens_v1({
    baseUrl: origin,
    headers: { Authorization: bearer, Cookie: cookie, 'X-CSRF-Token': csrf },
  });
  requireResult(listed.ok && listed.data.items.length > 0, 'bearer_list_failed');
  const denied = await apiClient.iam_list_security_events_v1({
    baseUrl: origin,
    headers: { Authorization: bearer },
  });
  requireResult(!denied.ok && denied.status === 403, 'scope_denial_failed');
  requireResult(denied.problem.code === 'permission_denied', 'problem_decode_failed');
  requireResult(typeof denied.problem.correlation_id === 'string', 'correlation_missing');
  requireResult(operationIds.length === 13, 'operation_count_mismatch');
  process.stdout.write('{"status":"passed","operations":13}\n');
}

run().catch((error) => {
  const code = error instanceof Error && /^[a-z_]+$/.test(error.message)
    ? error.message
    : 'unknown_failure';
  process.stderr.write(`real_client_failed:${code}\n`);
  process.exitCode = 1;
});
