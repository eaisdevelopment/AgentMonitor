import { useEffect, useState } from "react";

import { LoginPage } from "../features/auth/LoginPage";
import { PasswordChangePanel } from "../features/auth/PasswordChangePanel";
import { ProtectedRoute } from "../features/auth/ProtectedRoute";
import { ApiTokensPage } from "../features/settings/security/ApiTokensPage";
import { OverviewPage } from "../features/overview/OverviewPage";
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
  const [showPasswordForm, setShowPasswordForm] = useState(false);
  const [needsProofRenewal, setNeedsProofRenewal] = useState(false);
  const [lockedMessage, setLockedMessage] = useState<string | null>(null);
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
    const onPopState = () => setRoute(initialRoute());
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, []);

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
    if (session !== null) document.getElementById("page-title")?.focus();
    else if (bootstrap?.kind === "login") document.getElementById("login-title")?.focus();
  }, [route, session, bootstrap]);

  function navigate(next: AllowedRoute, replace = false) {
    if (replace) window.history.replaceState(null, "", next);
    else window.history.pushState(null, "", next);
    setRoute(next);
  }

  function expire() {
    setSession(null);
    setShowPasswordForm(false);
    setNeedsProofRenewal(false);
    setBootstrap({ kind: "login" });
    setMessage("Your dashboard session ended. Sign in again.");
    window.history.replaceState(null, "", "/login");
    setRoute("/login");
  }

  function lockProtectedView(reason: string) {
    setSession(null);
    setShowPasswordForm(false);
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
    try {
      const latest = await iam.currentSession();
      if (!latest.ok) {
        if (latest.problem.code === "dashboard_authentication_required") expire();
        else setMessage(safeProblemMessage(latest.problem));
        return;
      }
      const result = await iam.logout(latest.data);
      if (!result.ok && result.problem.code !== "dashboard_authentication_required") {
        if (result.problem.code === "csrf_validation_failed") proofUnavailable();
        else setMessage(safeProblemMessage(result.problem));
        return;
      }
      expire();
      setMessage(null);
    } catch (error) {
      if (error instanceof CsrfUnavailableError) {
        proofUnavailable();
      } else {
        try {
          const current = await iam.currentSession();
          if (current.ok) {
            setSession(current.data);
            setMessage("Sign-out was not confirmed. The server session is still active; you may explicitly try Sign out again.");
          } else if (current.problem.code === "dashboard_authentication_required") {
            expire();
          } else {
            lockProtectedView("Sign-out status is unknown. The protected view is locked locally; server revocation was not confirmed. Restore the service before checking your session again.");
          }
        } catch {
          lockProtectedView("Sign-out status is unknown. The protected view is locked locally; server revocation was not confirmed. Restore the service before checking your session again.");
        }
      }
    }
  }

  function proofUnavailable() {
    setNeedsProofRenewal(true);
    setMessage("Security proof unavailable. The session remains active; sign in again to renew it.");
  }

  function renewProof() {
    setSession(null);
    setShowPasswordForm(false);
    setBootstrap({ kind: "login" });
    setNeedsProofRenewal(false);
    setMessage("Sign in to renew the security proof. The previous session remains active until expiry.");
    navigate("/login", true);
  }

  async function checkSession() {
    try {
      const result = await iam.currentSession();
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
    } catch {
      setMessage("The local service is unavailable. Try again.");
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

  return (
    <ProtectedRoute session={session}>
      <a className="skip-link" href="#main-content">Skip to main content</a>
      <div className="dashboard-frame">
        <header className="dashboard-header">
          <div><p className="eyebrow">Local operations console</p><span className="brand">AgentMonitor</span></div>
          <div className="header-actions">
            <button type="button" className="quiet-button" onClick={() => { void checkSession(); }}>Check session</button>
            <button type="button" className="quiet-button" onClick={() => { void logout(); }}>Sign out</button>
          </div>
        </header>
        <nav aria-label="Primary" className="dashboard-nav">
          <button type="button" aria-current={route === "/" ? "page" : undefined} onClick={() => navigate("/")}>Overview</button>
          <button type="button" aria-current={route.startsWith("/accounts") ? "page" : undefined} onClick={() => navigate("/accounts")}>Accounts</button>
          <button type="button" aria-current={route === "/organizations" ? "page" : undefined} onClick={() => navigate("/organizations")}>Organizations</button>
          <button type="button" aria-current={route === "/providers" ? "page" : undefined} onClick={() => navigate("/providers")}>Providers</button>
          <button type="button" aria-current={route === "/collectors" ? "page" : undefined} onClick={() => navigate("/collectors")}>Collection / History</button>
          <button type="button" aria-current={route === "/sessions" ? "page" : undefined} onClick={() => navigate("/sessions")}>Sessions</button>
          <button type="button" aria-current={route === "/operations" ? "page" : undefined} onClick={() => navigate("/operations")}>Operations</button>
          <button type="button" aria-current={route === "/alert-rules" ? "page" : undefined} onClick={() => navigate("/alert-rules")}>Alert rules</button>
          <button type="button" aria-current={route === "/alerts" ? "page" : undefined} onClick={() => navigate("/alerts")}>Alerts</button>
          <button type="button" aria-current={route === "/settings/api-tokens" ? "page" : undefined} onClick={() => navigate("/settings/api-tokens")}>API tokens</button>
        </nav>
        <main id="main-content" className="dashboard-main">
          {message && <div className="form-status" role="alert"><p>{message}</p>
            {needsProofRenewal && <button type="button" onClick={renewProof}>Sign in again</button>}
          </div>}
          {route === "/settings/api-tokens" ? (
            <ApiTokensPage onExpired={expire} onProofUnavailable={proofUnavailable} />
          ) : route === "/organizations" ? (
            <OrganizationsPage onExpired={expire} onProofUnavailable={proofUnavailable} />
          ) : route.startsWith("/accounts") ? (
            <AccountPage
              accountId={accountIdFromRoute(route) ?? undefined}
              onExpired={expire}
              onOpenAccount={(accountId) => navigate(accountRoute(accountId))}
              onProofUnavailable={proofUnavailable}
            />
          ) : route === "/providers" ? (
            <ProviderPage onExpired={expire} />
          ) : route === "/collectors" ? (
            <CollectionRunPanel onExpired={expire} />
          ) : route === "/sessions" ? (
            <SessionPanel onExpired={expire} />
          ) : route === "/operations" ? (
            <OperationsPage onExpired={expire} />
          ) : route === "/alert-rules" ? (
            <AlertRulesPage onExpired={expire} onProofUnavailable={proofUnavailable} />
          ) : route === "/alerts" ? (
            <AlertsPage onExpired={expire} onProofUnavailable={proofUnavailable}
              onOpenAccount={(accountId) => navigate(accountRoute(accountId))}
              onOpenRules={() => navigate("/alert-rules")} />
          ) : (
            <OverviewPage
              onExpired={expire}
              onOpenAccount={(accountId) => navigate(accountRoute(accountId))}
              onTogglePassword={() => setShowPasswordForm((visible) => !visible)}
              onProofUnavailable={proofUnavailable}
            />
          )}
          {route === "/" && showPasswordForm && (
            <PasswordChangePanel
              onChanged={(renewed) => setSession(renewed)}
              onExpired={expire}
              onProofUnavailable={proofUnavailable}
              onUncertain={() => lockProtectedView("Password-change status is unknown. The protected view is locked locally. Do not repeat the change blindly; restore the service and verify by signing in.")}
            />
          )}
        </main>
      </div>
    </ProtectedRoute>
  );
}
