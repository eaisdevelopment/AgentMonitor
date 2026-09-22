import { useEffect, useState } from "react";

import { LoginPage } from "../features/auth/LoginPage";
import { PasswordChangePanel } from "../features/auth/PasswordChangePanel";
import { ProtectedRoute } from "../features/auth/ProtectedRoute";
import { ApiTokensPage } from "../features/settings/security/ApiTokensPage";
import { CsrfUnavailableError, iam, safeProblemMessage, type CurrentSessionViewV1 } from "../shared/api/client";
import { safeReturnRoute, safeRoute, sessionBootstrap, type AllowedRoute, type BootstrapState } from "./sessionBootstrap";

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
    document.title = route === "/settings/api-tokens"
      ? "API tokens · AgentMonitor" : "AgentMonitor · Dashboard";
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
          <button type="button" aria-current={route === "/settings/api-tokens" ? "page" : undefined} onClick={() => navigate("/settings/api-tokens")}>API tokens</button>
        </nav>
        <main id="main-content" className="dashboard-main">
          {message && <div className="form-status" role="alert"><p>{message}</p>
            {needsProofRenewal && <button type="button" onClick={renewProof}>Sign in again</button>}
          </div>}
          {route === "/settings/api-tokens" ? (
            <ApiTokensPage onExpired={expire} onProofUnavailable={proofUnavailable} />
          ) : (
            <div className="operations-console" data-monitoring-state="unavailable">
              <section className="command-deck" aria-labelledby="page-title">
                <div>
                  <p className="eyebrow">Mission control · local node</p>
                  <h1 id="page-title" tabIndex={-1}>AgentMonitor</h1>
                  <p className="console-summary">Provider telemetry is not connected yet. The dashboard shows unavailable states instead of invented usage.</p>
                </div>
                <div className="link-state" aria-label="Dashboard service link">
                  <span className="status-light" aria-hidden="true" />
                  <span><strong>Service link</strong><small>Authenticated · local</small></span>
                </div>
              </section>

              <div className="telemetry-grid">
                <section className="telemetry-panel fleet-panel" role="region" aria-labelledby="fleet-title">
                  <div className="panel-heading"><div><p className="panel-code">FLEET / 01</p><h2 id="fleet-title">Fleet status</h2></div><span className="state-chip state-unavailable">Unavailable</span></div>
                  <div className="empty-telemetry">
                    <span className="radar-mark" aria-hidden="true" />
                    <div><strong>No monitored accounts</strong><p>Accounts will appear here only after the versioned monitoring API returns real registry data.</p></div>
                  </div>
                </section>

                <section className="telemetry-panel capacity-panel" role="region" aria-labelledby="capacity-title">
                  <div className="panel-heading"><div><p className="panel-code">CAPACITY / 02</p><h2 id="capacity-title">Capacity</h2></div><span className="state-chip state-unavailable">No signal</span></div>
                  <dl className="telemetry-readouts">
                    <div><dt>Subscription quota</dt><dd>Unavailable</dd></div>
                    <div><dt>API budget</dt><dd>Unavailable</dd></div>
                    <div><dt>Next reset</dt><dd>Unknown</dd></div>
                  </dl>
                </section>

                <section className="telemetry-panel runtime-panel" role="region" aria-labelledby="runtime-title">
                  <div className="panel-heading"><div><p className="panel-code">RUNTIME / 03</p><h2 id="runtime-title">Agent runtime</h2></div><span className="state-chip state-unavailable">Unobserved</span></div>
                  <p className="empty-copy">No process or session observation has been returned by the service.</p>
                </section>

                <section className="telemetry-panel alerts-panel" role="region" aria-labelledby="alerts-title">
                  <div className="panel-heading"><div><p className="panel-code">ALERTS / 04</p><h2 id="alerts-title">Alerts</h2></div><span className="state-chip state-warning">1 notice</span></div>
                  <div className="notice-row"><span aria-hidden="true">!</span><div><strong>Monitoring data unavailable</strong><p>Authentication is working; provider collection is not connected to this view yet.</p></div></div>
                </section>

                <section className="telemetry-panel activity-panel" role="region" aria-labelledby="activity-title">
                  <div className="panel-heading"><div><p className="panel-code">EVENTS / 05</p><h2 id="activity-title">Recent activity</h2></div><span className="state-chip state-unavailable">No data</span></div>
                  <p className="empty-copy">No provider collection activity has been recorded.</p>
                </section>
              </div>

              <section className="account-security" aria-labelledby="security-title">
                <div><p className="panel-code">LOCAL CONTROL</p><h2 id="security-title">Dashboard security</h2></div>
                <button type="button" className="quiet-button" onClick={() => setShowPasswordForm((visible) => !visible)}>Change password</button>
              </section>
            </div>
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
