import { useEffect, useRef, useState } from "react";

import { LoginPage } from "../features/auth/LoginPage";
import { PasswordChangePanel } from "../features/auth/PasswordChangePanel";
import { ProtectedRoute } from "../features/auth/ProtectedRoute";
import { ApiTokensPage } from "../features/settings/security/ApiTokensPage";
import { OverviewPage } from "../features/overview/OverviewPage";
import { ProductPromotion } from "../features/overview/ProductPromotion";
import { AccountPage } from "../features/accounts/AccountPage";
import { OrganizationsPage } from "../features/organizations/OrganizationsPage";
import { CollectionRunPanel } from "../features/collectors/CollectionRunPanel";
import { ProviderPage } from "../features/providers/ProviderPage";
import { SessionPanel } from "../features/sessions/SessionPanel";
import { OperationsPage } from "../features/operations/OperationsPage";
import { AlertRulesPage } from "../features/alerts/AlertRulesPage";
import { AlertsPage } from "../features/alerts/AlertsPage";
import { CsrfUnavailableError, iam, safeProblemMessage, type CurrentSessionViewV1 } from "../shared/api/client";
import { accountIdFromRoute, accountRoute, safeReturnRoute, safeRoute, sessionBootstrap, type AllowedRoute, type BootstrapState } from "./sessionBootstrap";

type PasswordLifecycle = "closed" | "draining" | "ready" | "submitting";
type PasswordCloseFocus = "change-control" | "success-status" | null;
type HeaderSessionActionKind = "idle" | "checking" | "logging-out";
type HeaderSessionAction = Readonly<{
  kind: HeaderSessionActionKind;
  token: number;
  protectedFeatureGeneration: number;
}>;

const passwordChangedMessage = "Password changed. Other browser sessions were revoked.";

function initialRoute(): AllowedRoute {
  const direct = safeRoute(window.location.pathname);
  if (direct !== null) return direct;
  return "/";
}

export function DashboardApp() {
  const [bootstrap, setBootstrap] = useState<BootstrapState | null>(null);
  const [route, setRoute] = useState<AllowedRoute>(initialRoute);
  const [loginBusy, setLoginBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [session, setSession] = useState<CurrentSessionViewV1 | null>(null);
  const [passwordLifecycle, setPasswordLifecycle] = useState<PasswordLifecycle>("closed");
  const [passwordCleanupAcknowledged, setPasswordCleanupAcknowledged] = useState(false);
  const [passwordCloseFocus, setPasswordCloseFocus] = useState<PasswordCloseFocus>(null);
  const [messageRole, setMessageRole] = useState<"alert" | "status">("alert");
  const [headerSessionAction, setHeaderSessionAction] = useState<HeaderSessionActionKind>("idle");
  const [needsProofRenewal, setNeedsProofRenewal] = useState(false);
  const [lockedMessage, setLockedMessage] = useState<string | null>(null);
  const passwordLifecycleRef = useRef<PasswordLifecycle>("closed");
  const protectedFeatureGenerationRef = useRef(0);
  const headerSessionActionSequenceRef = useRef(0);
  const headerSessionActionRef = useRef<HeaderSessionAction>({
    kind: "idle",
    token: 0,
    protectedFeatureGeneration: 0,
  });
  const [returnRoute] = useState<AllowedRoute>(() => {
    const query = new URLSearchParams(window.location.search);
    const direct = initialRoute();
    return direct === "/settings/api-tokens"
      ? direct : safeReturnRoute(query.get("next"));
  });

  useEffect(() => {
    if (window.location.search || window.location.hash) {
      window.history.replaceState(null, "", window.location.pathname);
    }
    let active = true;
    void sessionBootstrap().then((state) => {
      if (!active) return;
      setBootstrap(state);
      setSession(state.kind === "authenticated" ? state.session : null);
      if (state.kind === "authenticated" && initialRoute() === "/login") {
        window.history.replaceState(null, "", returnRoute);
        setRoute(returnRoute);
      }
    });
    return () => { active = false; };
  }, []);

  useEffect(() => {
    const onPopState = () => {
      if (passwordLifecycleRef.current !== "closed") {
        window.history.replaceState(null, "", "/");
        setRoute("/");
        return;
      }
      setRoute(initialRoute());
    };
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, []);

  useEffect(() => {
    if (passwordLifecycle !== "draining") return;
    setPasswordCleanupAcknowledged(true);
  }, [passwordLifecycle]);

  useEffect(() => {
    if (passwordLifecycle !== "draining" || !passwordCleanupAcknowledged) return;
    passwordLifecycleRef.current = "ready";
    setPasswordLifecycle("ready");
  }, [passwordCleanupAcknowledged, passwordLifecycle]);

  useEffect(() => {
    const routeTitle = route === "/settings/api-tokens" ? "API tokens"
      : route === "/organizations" ? "Organizations"
      : route.startsWith("/accounts") ? "Accounts"
      : route === "/providers" ? "Providers"
      : route === "/collectors" ? "Collection / History"
      : route === "/sessions" ? "Sessions"
      : route === "/operations" ? "Operations"
      : route === "/alert-rules" ? "Alert rules"
      : route === "/alerts" ? "Alerts"
      : "AgentMonitor";
    document.title = `${routeTitle} · AgentMonitor`;
    if (session !== null && passwordLifecycle === "closed") document.getElementById("page-title")?.focus();
    else if (bootstrap?.kind === "login") document.getElementById("login-title")?.focus();
  }, [route, session, bootstrap, passwordLifecycle]);

  useEffect(() => {
    if (passwordLifecycle !== "closed" || passwordCloseFocus === null) return;
    const target = passwordCloseFocus === "success-status"
      ? document.getElementById("dashboard-status")
      : Array.from(document.querySelectorAll<HTMLButtonElement>("button"))
        .find((button) => button.textContent?.trim() === "Change password") ?? null;
    target?.focus();
    setPasswordCloseFocus(null);
  }, [passwordCloseFocus, passwordLifecycle]);

  function navigate(next: AllowedRoute, replace = false) {
    if (passwordLifecycleRef.current !== "closed") {
      window.history.replaceState(null, "", "/");
      setRoute("/");
      return;
    }
    if (replace) window.history.replaceState(null, "", next);
    else window.history.pushState(null, "", next);
    setRoute(next);
  }

  function resetPasswordLifecycle() {
    passwordLifecycleRef.current = "closed";
    setPasswordLifecycle("closed");
    setPasswordCleanupAcknowledged(false);
  }

  function canonicalizePasswordRoute() {
    window.history.replaceState(null, "", "/");
    setRoute("/");
  }

  function beginHeaderSessionAction(kind: Exclude<HeaderSessionActionKind, "idle">): HeaderSessionAction | null {
    if (passwordLifecycleRef.current !== "closed" || headerSessionActionRef.current.kind !== "idle") return null;
    const action: HeaderSessionAction = {
      kind,
      token: headerSessionActionSequenceRef.current + 1,
      protectedFeatureGeneration: protectedFeatureGenerationRef.current,
    };
    headerSessionActionSequenceRef.current = action.token;
    headerSessionActionRef.current = action;
    setHeaderSessionAction(kind);
    return action;
  }

  function headerSessionActionIsCurrent(action: HeaderSessionAction): boolean {
    return headerSessionActionRef.current.token === action.token
      && headerSessionActionRef.current.kind === action.kind
      && passwordLifecycleRef.current === "closed"
      && protectedFeatureGenerationRef.current === action.protectedFeatureGeneration;
  }

  function finishHeaderSessionAction(action: HeaderSessionAction) {
    if (headerSessionActionRef.current.token !== action.token
      || headerSessionActionRef.current.kind !== action.kind) return;
    headerSessionActionRef.current = {
      kind: "idle",
      token: action.token,
      protectedFeatureGeneration: protectedFeatureGenerationRef.current,
    };
    setHeaderSessionAction("idle");
  }

  function invalidateHeaderSessionAction() {
    const token = headerSessionActionSequenceRef.current + 1;
    headerSessionActionSequenceRef.current = token;
    headerSessionActionRef.current = {
      kind: "idle",
      token,
      protectedFeatureGeneration: protectedFeatureGenerationRef.current,
    };
    setHeaderSessionAction("idle");
  }

  function openPasswordChange() {
    if (passwordLifecycleRef.current !== "closed") return;
    if (headerSessionActionRef.current.kind === "logging-out") {
      setMessage("Sign-out is in progress.");
      setMessageRole("status");
      return;
    }
    if (headerSessionActionRef.current.kind === "checking") invalidateHeaderSessionAction();
    if (needsProofRenewal) {
      setMessage("Security proof unavailable. The session remains active; sign in again to renew it.");
      setMessageRole("alert");
      return;
    }
    protectedFeatureGenerationRef.current += 1;
    setPasswordCleanupAcknowledged(false);
    passwordLifecycleRef.current = "draining";
    setPasswordLifecycle("draining");
    setPasswordCloseFocus(null);
    setMessage(null);
    setMessageRole("alert");
    canonicalizePasswordRoute();
  }

  function beginPasswordSubmit(): boolean {
    if (passwordLifecycleRef.current !== "ready") return false;
    passwordLifecycleRef.current = "submitting";
    setPasswordLifecycle("submitting");
    return true;
  }

  function resumePasswordForm() {
    if (passwordLifecycleRef.current !== "submitting") return;
    passwordLifecycleRef.current = "ready";
    setPasswordLifecycle("ready");
  }

  function cancelPasswordChange() {
    if (passwordLifecycleRef.current !== "ready") return;
    resetPasswordLifecycle();
    canonicalizePasswordRoute();
    setPasswordCloseFocus("change-control");
  }

  function completePasswordChange(renewed: CurrentSessionViewV1) {
    if (passwordLifecycleRef.current !== "submitting") return;
    setSession(renewed);
    setNeedsProofRenewal(false);
    setMessage(passwordChangedMessage);
    setMessageRole("status");
    resetPasswordLifecycle();
    canonicalizePasswordRoute();
    setPasswordCloseFocus("success-status");
  }

  function expire() {
    protectedFeatureGenerationRef.current += 1;
    invalidateHeaderSessionAction();
    resetPasswordLifecycle();
    setSession(null);
    setNeedsProofRenewal(false);
    setBootstrap({ kind: "login" });
    setMessage("Your dashboard session ended. Sign in again.");
    setMessageRole("alert");
    window.history.replaceState(null, "", "/login");
    setRoute("/login");
  }

  function lockProtectedView(reason: string) {
    protectedFeatureGenerationRef.current += 1;
    invalidateHeaderSessionAction();
    resetPasswordLifecycle();
    setSession(null);
    setLockedMessage(reason);
  }

  async function login(credential: string) {
    setLoginBusy(true);
    setMessage(null);
    try {
      const response = await iam.login(credential);
      if (!response.ok) {
        const retryValue = Number(response.headers.get("Retry-After"));
        const retryGuidance = response.problem.code === "login_throttled" &&
          Number.isInteger(retryValue) && retryValue >= 1 && retryValue <= 900
          ? ` Try again in ${retryValue} seconds.` : "";
        setMessage(safeProblemMessage(response.problem) + retryGuidance);
        return;
      }
      const current = await iam.currentSession();
      if (!current.ok) {
        setMessage("Sign-in succeeded, but the session could not be opened. Try again.");
        return;
      }
      setSession(current.data);
      setLockedMessage(null);
      setBootstrap({ kind: "authenticated", session: current.data });
      setNeedsProofRenewal(false);
      navigate(returnRoute, true);
    } catch {
      setMessage("The local service is unavailable. Try again.");
    } finally {
      setLoginBusy(false);
    }
  }

  async function logout() {
    if (session === null) return;
    const action = beginHeaderSessionAction("logging-out");
    if (action === null) return;
    try {
      const latest = await iam.currentSession();
      if (!headerSessionActionIsCurrent(action)) return;
      if (!latest.ok) {
        if (latest.problem.code === "dashboard_authentication_required") expire();
        else setMessage(safeProblemMessage(latest.problem));
        return;
      }
      const result = await iam.logout(latest.data);
      if (!headerSessionActionIsCurrent(action)) return;
      if (!result.ok && result.problem.code !== "dashboard_authentication_required") {
        if (result.problem.code === "csrf_validation_failed") proofUnavailable();
        else setMessage(safeProblemMessage(result.problem));
        return;
      }
      expire();
      setMessage(null);
    } catch (error) {
      if (!headerSessionActionIsCurrent(action)) return;
      if (error instanceof CsrfUnavailableError) {
        proofUnavailable();
      } else {
        try {
          const current = await iam.currentSession();
          if (!headerSessionActionIsCurrent(action)) return;
          if (current.ok) {
            setSession(current.data);
            setMessage("Sign-out was not confirmed. The server session is still active; you may explicitly try Sign out again.");
          } else if (current.problem.code === "dashboard_authentication_required") {
            expire();
          } else {
            lockProtectedView("Sign-out status is unknown. The protected view is locked locally; server revocation was not confirmed. Restore the service before checking your session again.");
          }
        } catch {
          if (!headerSessionActionIsCurrent(action)) return;
          lockProtectedView("Sign-out status is unknown. The protected view is locked locally; server revocation was not confirmed. Restore the service before checking your session again.");
        }
      }
    } finally {
      finishHeaderSessionAction(action);
    }
  }

  function proofUnavailable() {
    setNeedsProofRenewal(true);
    setMessage("Security proof unavailable. The session remains active; sign in again to renew it.");
    setMessageRole("alert");
  }

  function passwordProofUnavailable() {
    resetPasswordLifecycle();
    canonicalizePasswordRoute();
    proofUnavailable();
  }

  function renewProof() {
    protectedFeatureGenerationRef.current += 1;
    invalidateHeaderSessionAction();
    resetPasswordLifecycle();
    setSession(null);
    setBootstrap({ kind: "login" });
    setNeedsProofRenewal(false);
    setMessage("Sign in to renew the security proof. The previous session remains active until expiry.");
    navigate("/login", true);
  }

  async function checkSession() {
    const action = beginHeaderSessionAction("checking");
    if (action === null) return;
    try {
      const result = await iam.currentSession();
      if (!headerSessionActionIsCurrent(action)) return;
      if (!result.ok) {
        if (result.problem.code === "dashboard_authentication_required") {
          expire();
        } else {
          setMessage(safeProblemMessage(result.problem));
        }
        return;
      }
      setSession(result.data);
      setMessage("Dashboard session is active.");
      setMessageRole("status");
    } catch {
      if (!headerSessionActionIsCurrent(action)) return;
      setMessage("The local service is unavailable. Try again.");
      setMessageRole("alert");
    } finally {
      finishHeaderSessionAction(action);
    }
  }

  if (lockedMessage !== null) return (
    <main className="auth-stage"><section className="auth-card" role="alert"><h1>Identity status unknown</h1><p>{lockedMessage}</p></section></main>
  );
  if (bootstrap === null) return <main className="auth-stage" role="status">Connecting to the local service…</main>;
  if (bootstrap.kind === "setup") return (
    <main className="auth-stage">
      <section className="auth-card">
        <p className="eyebrow">Local setup</p>
        <h1>Administrator setup required</h1>
        <p>Initialize the local administrator in your terminal, then reload this page. Web-based password setup is not available.</p>
        <p>Open <code>docs/modules/identity-access.md</code> in this checkout and follow “Fresh local administrator bootstrap”. The operator command uses a private data-root you choose; do not put the password in a command line.</p>
      </section>
    </main>
  );
  if (bootstrap.kind === "error") return (
    <main className="auth-stage"><section className="auth-card"><h1>Local service unavailable</h1><p>Check the AgentMonitor service and reload.</p></section></main>
  );
  if (session === null) return <LoginPage onLogin={login} isBusy={loginBusy} message={message} />;

  const protectedFeatureGeneration = protectedFeatureGenerationRef.current;
  const protectedCallbackAllowed = () => (
    passwordLifecycleRef.current === "closed"
    && protectedFeatureGenerationRef.current === protectedFeatureGeneration
  );
  const protectedExpire = () => { if (protectedCallbackAllowed()) expire(); };
  const protectedProofUnavailable = () => { if (protectedCallbackAllowed()) proofUnavailable(); };
  const protectedOpenAccount = (accountId: string) => {
    if (protectedCallbackAllowed()) navigate(accountRoute(accountId));
  };
  const protectedOpenRules = () => { if (protectedCallbackAllowed()) navigate("/alert-rules"); };
  const passwordFlowOpen = passwordLifecycle !== "closed";
  const headerSessionActionOpen = headerSessionAction !== "idle";

  return (
    <ProtectedRoute session={session}>
      <a className="skip-link" href="#main-content">Skip to main content</a>
      <div
        className="dashboard-frame"
        data-password-cleanup-acknowledged={passwordCleanupAcknowledged}
        data-password-lifecycle={passwordLifecycle}
        data-session-action={headerSessionAction}
      >
        <header className="dashboard-header">
          <div><p className="eyebrow">Local operations console</p><span className="brand">AgentMonitor</span></div>
          <ProductPromotion />
          <div className="header-actions">
            <button type="button" className="quiet-button" disabled={passwordFlowOpen || headerSessionActionOpen} onClick={() => { void checkSession(); }}>{headerSessionAction === "checking" ? "Checking…" : "Check session"}</button>
            <button type="button" className="quiet-button" disabled={passwordFlowOpen || headerSessionActionOpen} onClick={() => { void logout(); }}>{headerSessionAction === "logging-out" ? "Signing out…" : "Sign out"}</button>
          </div>
        </header>
        <nav aria-label="Primary" className="dashboard-nav">
          <button type="button" disabled={passwordFlowOpen} aria-current={route === "/" ? "page" : undefined} onClick={() => navigate("/")}>Overview</button>
          <button type="button" disabled={passwordFlowOpen} aria-current={route.startsWith("/accounts") ? "page" : undefined} onClick={() => navigate("/accounts")}>Accounts</button>
          <button type="button" disabled={passwordFlowOpen} aria-current={route === "/organizations" ? "page" : undefined} onClick={() => navigate("/organizations")}>Organizations</button>
          <button type="button" disabled={passwordFlowOpen} aria-current={route === "/providers" ? "page" : undefined} onClick={() => navigate("/providers")}>Providers</button>
          <button type="button" disabled={passwordFlowOpen} aria-current={route === "/collectors" ? "page" : undefined} onClick={() => navigate("/collectors")}>Collection / History</button>
          <button type="button" disabled={passwordFlowOpen} aria-current={route === "/sessions" ? "page" : undefined} onClick={() => navigate("/sessions")}>Sessions</button>
          <button type="button" disabled={passwordFlowOpen} aria-current={route === "/operations" ? "page" : undefined} onClick={() => navigate("/operations")}>Operations</button>
          <button type="button" disabled={passwordFlowOpen} aria-current={route === "/alert-rules" ? "page" : undefined} onClick={() => navigate("/alert-rules")}>Alert rules</button>
          <button type="button" disabled={passwordFlowOpen} aria-current={route === "/alerts" ? "page" : undefined} onClick={() => navigate("/alerts")}>Alerts</button>
          <button type="button" disabled={passwordFlowOpen} aria-current={route === "/settings/api-tokens" ? "page" : undefined} onClick={() => navigate("/settings/api-tokens")}>API tokens</button>
        </nav>
        <main id="main-content" className="dashboard-main">
          {message && <div id="dashboard-status" className="form-status" role={messageRole} tabIndex={-1}><p>{message}</p>
            {needsProofRenewal && <button type="button" onClick={renewProof}>Sign in again</button>}
          </div>}
          {passwordLifecycle === "draining" ? (
            <section className="security-panel" role="status" aria-live="polite" aria-labelledby="password-preparation-title">
              <h2 id="password-preparation-title">Preparing secure password change</h2>
              <p>Finishing protected dashboard reads before the password form opens…</p>
            </section>
          ) : passwordLifecycle !== "closed" ? (
            <PasswordChangePanel
              phase={passwordLifecycle}
              onSubmitting={beginPasswordSubmit}
              onReady={resumePasswordForm}
              onCancel={cancelPasswordChange}
              onChanged={completePasswordChange}
              onExpired={expire}
              onProofUnavailable={passwordProofUnavailable}
              onUncertain={() => lockProtectedView("Password-change status is unknown. The protected view is locked locally. Do not repeat the change blindly; restore the service and verify by signing in.")}
            />
          ) : route === "/settings/api-tokens" ? (
            <ApiTokensPage onExpired={protectedExpire} onProofUnavailable={protectedProofUnavailable} />
          ) : route === "/organizations" ? (
            <OrganizationsPage onExpired={protectedExpire} onProofUnavailable={protectedProofUnavailable} />
          ) : route.startsWith("/accounts") ? (
            <AccountPage
              accountId={accountIdFromRoute(route) ?? undefined}
              onExpired={protectedExpire}
              onOpenAccount={protectedOpenAccount}
              onProofUnavailable={protectedProofUnavailable}
            />
          ) : route === "/providers" ? (
            <ProviderPage onExpired={protectedExpire} />
          ) : route === "/collectors" ? (
            <CollectionRunPanel onExpired={protectedExpire} />
          ) : route === "/sessions" ? (
            <SessionPanel onExpired={protectedExpire} />
          ) : route === "/operations" ? (
            <OperationsPage onExpired={protectedExpire} />
          ) : route === "/alert-rules" ? (
            <AlertRulesPage onExpired={protectedExpire} onProofUnavailable={protectedProofUnavailable} />
          ) : route === "/alerts" ? (
            <AlertsPage onExpired={protectedExpire} onProofUnavailable={protectedProofUnavailable}
              onOpenAccount={protectedOpenAccount}
              onOpenRules={protectedOpenRules} />
          ) : (
            <OverviewPage
              onExpired={protectedExpire}
              onOpenAccount={protectedOpenAccount}
              onTogglePassword={openPasswordChange}
              onProofUnavailable={protectedProofUnavailable}
            />
          )}
          <footer className="dashboard-company-footer">Developed and delivered by <a href="https://essentialai.uk/" target="_blank" rel="noopener noreferrer">Essential AI Solutions Ltd</a> · © {new Date().getFullYear()}</footer>
        </main>
      </div>
    </ProtectedRoute>
  );
}
