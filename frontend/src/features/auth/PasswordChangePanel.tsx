import { useState, type FormEvent } from "react";

import {
  CsrfUnavailableError,
  iam,
  safeProblemMessage,
  type CurrentSessionViewV1,
} from "../../shared/api/client";

type PasswordChangePanelProps = Readonly<{
  onChanged: (session: CurrentSessionViewV1) => void;
  onExpired: () => void;
  onProofUnavailable: () => void;
  onUncertain: () => void;
}>;

export function PasswordChangePanel({
  onChanged, onExpired, onProofUnavailable, onUncertain,
}: PasswordChangePanelProps) {
  const [isBusy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const fields = new FormData(form);
    const current = fields.get("current");
    const next = fields.get("next");
    const confirmation = fields.get("confirmation");
    form.reset();
    if (typeof current !== "string" || typeof next !== "string" || next !== confirmation) {
      setMessage("New password and confirmation must match.");
      return;
    }
    setBusy(true);
    setMessage(null);
    try {
      const preflight = await iam.currentSession();
      if (!preflight.ok) {
        if (preflight.problem.code === "dashboard_authentication_required") onExpired();
        else setMessage(safeProblemMessage(preflight.problem));
        return;
      }
      const result = await iam.changePassword(preflight.data, current, next);
      if (!result.ok) {
        if (result.problem.code === "dashboard_authentication_required") onExpired();
        else if (result.problem.code === "csrf_validation_failed") onProofUnavailable();
        else setMessage(safeProblemMessage(result.problem));
        return;
      }
      const renewed = await iam.currentSession();
      if (!renewed.ok) {
        onExpired();
        return;
      }
      onChanged(renewed.data);
      setMessage("Password changed. Other browser sessions were revoked.");
    } catch (error) {
      if (error instanceof CsrfUnavailableError) {
        onProofUnavailable();
      } else {
        try {
          const observed = await iam.currentSession();
          if (observed.ok) {
            onChanged(observed.data);
            setMessage("Password-change outcome is unknown. Do not repeat it blindly; verify through a new sign-in.");
          } else if (observed.problem.code === "dashboard_authentication_required") {
            onExpired();
          } else {
            onUncertain();
          }
        } catch {
          onUncertain();
        }
      }
    } finally {
      setBusy(false);
    }
  }

  return (
    <section aria-labelledby="password-change-title" className="security-panel">
      <h2 id="password-change-title">Change administrator password</h2>
      <p>Changing the password revokes other browser sessions. The current session receives a new binding.</p>
      <form className="password-form" onSubmit={(event) => { void submit(event); }}>
        <label htmlFor="current-password">Current password</label>
        <input id="current-password" name="current" type="password" autoComplete="current-password" required />
        <label htmlFor="new-password">New password</label>
        <input id="new-password" name="next" type="password" autoComplete="new-password" minLength={15} required />
        <label htmlFor="confirmation-password">Confirm new password</label>
        <input id="confirmation-password" name="confirmation" type="password" autoComplete="new-password" minLength={15} required />
        <button type="submit" disabled={isBusy}>{isBusy ? "Saving…" : "Save new password"}</button>
      </form>
      {message && <p role="status" className="form-status">{message}</p>}
    </section>
  );
}
