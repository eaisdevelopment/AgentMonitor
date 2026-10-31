import { useState, type FormEvent } from "react";

type LoginPageProps = Readonly<{
  onLogin: (credential: string) => Promise<void>;
  isBusy: boolean;
  message: string | null;
}>;

export function LoginPage({ onLogin, isBusy, message }: LoginPageProps) {
  const [credential, setCredential] = useState("");

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const presented = credential;
    setCredential("");
    await onLogin(presented);
  }

  return (
    <main id="main-content" className="auth-stage">
      <section className="auth-card" aria-labelledby="login-title">
        <p className="eyebrow">AgentMonitor · Local access</p>
        <h1 id="login-title">Sign in</h1>
        <p>Enter the dashboard administrator password.</p>
        <form onSubmit={(event) => { void submit(event); }}>
          <label htmlFor="administrator-password">Administrator password</label>
          <input
            id="administrator-password"
            name="credential"
            type="password"
            autoComplete="current-password"
            required
            value={credential}
            onChange={(event) => setCredential(event.target.value)}
          />
          {message && <p className="form-status" role="alert">{message}</p>}
          <button type="submit" disabled={isBusy}>{isBusy ? "Signing in…" : "Sign in"}</button>
        </form>
      </section>
    </main>
  );
}
