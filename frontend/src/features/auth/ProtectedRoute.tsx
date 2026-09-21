import type { ReactNode } from "react";
import type { CurrentSessionViewV1 } from "../../shared/api/client";

type ProtectedRouteProps = Readonly<{
  session: CurrentSessionViewV1 | null;
  children: ReactNode;
}>;

export function ProtectedRoute({ session, children }: ProtectedRouteProps) {
  return session === null ? null : <>{children}</>;
}
