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

export const ALLOWED_ROUTES = ["/", "/login", "/settings/api-tokens"] as const;
export type AllowedRoute = (typeof ALLOWED_ROUTES)[number];

export function safeRoute(path: string | null): AllowedRoute | null {
  if (path === "/" || path === "/login" || path === "/settings/api-tokens") return path;
  return null;
}

/** A login intent can resume only an idempotent authenticated page. */
export function safeReturnRoute(path: string | null): "/" | "/settings/api-tokens" {
  return path === "/settings/api-tokens" ? path : "/";
}
