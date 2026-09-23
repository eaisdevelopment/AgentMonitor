import { iam, type CurrentSessionViewV1 } from "../shared/api/client";

export type BootstrapState =
  | Readonly<{ kind: "setup" }>
  | Readonly<{ kind: "login" }>
  | Readonly<{ kind: "authenticated"; session: CurrentSessionViewV1 }>
  | Readonly<{ kind: "error" }>;

/** Safe GET-only bootstrap; no login credential or server data is cached. */
export async function sessionBootstrap(): Promise<BootstrapState> {
  try {
    const initialization = await iam.initialization();
    if (!initialization.ok) return { kind: "error" };
    if (initialization.data.state === "uninitialized") return { kind: "setup" };
    if (initialization.data.state !== "initialized") return { kind: "error" };
    const session = await iam.currentSession();
    if (session.ok) return { kind: "authenticated", session: session.data };
    if (session.problem.code === "dashboard_authentication_required") {
      return { kind: "login" };
    }
    return { kind: "error" };
  } catch {
    return { kind: "error" };
  }
}

export const ALLOWED_ROUTES = [
  "/", "/login", "/accounts", "/providers", "/collectors", "/sessions",
  "/settings/api-tokens",
] as const;
export type FixedRoute = (typeof ALLOWED_ROUTES)[number];
export type AllowedRoute = FixedRoute | `/accounts/${string}`;

export function accountRoute(accountId: string): `/accounts/${string}` {
  return `/accounts/${encodeURIComponent(accountId)}`;
}

export function accountIdFromRoute(path: AllowedRoute): string | null {
  if (!path.startsWith("/accounts/")) return null;
  try {
    const accountId = decodeURIComponent(path.slice("/accounts/".length));
    return accountId.length > 0 && accountId.length <= 256 && !/[\u0000-\u001f\u007f]/.test(accountId)
      ? accountId : null;
  } catch {
    return null;
  }
}

export function safeRoute(path: string | null): AllowedRoute | null {
  if (path !== null && ALLOWED_ROUTES.some((route) => route === path)) return path as FixedRoute;
  if (path !== null && /^\/accounts\/[^/]{1,512}$/.test(path)) {
    const candidate = path as `/accounts/${string}`;
    return accountIdFromRoute(candidate) === null ? null : candidate;
  }
  return null;
}

/** A login intent can resume only an idempotent authenticated page. */
export function safeReturnRoute(path: string | null): AllowedRoute {
  const route = safeRoute(path);
  return route === "/login" || route === null ? "/" : route;
}
