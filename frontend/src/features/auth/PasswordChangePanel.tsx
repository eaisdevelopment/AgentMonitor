import { useEffect, useRef, useState, type FormEvent } from "react";

import {
  CsrfUnavailableError,
  iam,
  safeProblemMessage,
  type CurrentSessionViewV1,
  type SafeProblemV1,
} from "../../shared/api/client";

type PasswordChangePhase = "ready" | "submitting";

type PasswordChangePanelProps = Readonly<{
  phase: PasswordChangePhase;
  onSubmitting: () => boolean;
  onReady: () => void;
  onCancel: () => void;
  onChanged: (session: CurrentSessionViewV1) => void;
  onExpired: () => void;
  onProofUnavailable: () => void;
  onUncertain: () => void;
}>;

const noncommittedPasswordFailures = Object.freeze({
  credential_state_conflict: 409,
  idempotency_key_reused: 409,
  invalid_dashboard_credentials: 401,
  login_throttled: 429,
  password_policy_violation: 422,
  precondition_failed: 412,
  session_not_found: 404,
} satisfies Readonly<Record<string, number>>);

function isKnownNoncommittedFailure(status: number, problem: SafeProblemV1): boolean {
  return Object.prototype.hasOwnProperty.call(noncommittedPasswordFailures, problem.code)
    && noncommittedPasswordFailures[
      problem.code as keyof typeof noncommittedPasswordFailures
    ] === status;
}

export function PasswordChangePanel({
  phase,
  onSubmitting,
  onReady,
  onCancel,
  onChanged,
  onExpired,
  onProofUnavailable,
  onUncertain,
}: PasswordChangePanelProps) {
  const [message, setMessage] = useState<string | null>(null);
  const currentPassword = useRef<HTMLInputElement>(null);
  const submissionStarted = useRef(false);

  useEffect(() => {
    if (phase !== "ready") return;
    submissionStarted.current = false;
    currentPassword.current?.focus();
  }, [phase]);

  function returnToReady(nextMessage: string) {
    setMessage(nextMessage);
    submissionStarted.current = false;
    onReady();
  }

  async function classifyUnknownMutation() {
    try {
      const observed = await iam.currentSession();
      if (!observed.ok && observed.problem.code === "dashboard_authentication_required") {
        onExpired();
        return;
      }
      onUncertain();
    } catch {
      onUncertain();
    }
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (phase !== "ready" || submissionStarted.current) return;
    const form = event.currentTarget;
    const fields = new FormData(form);
    const current = fields.get("current");
    const next = fields.get("next");
    const confirmation = fields.get("confirmation");
    form.reset();
    if (typeof current !== "string" || typeof next !== "string" || next !== confirmation) {
      setMessage("New password and confirmation must match.");
      currentPassword.current?.focus();
      return;
    }

    submissionStarted.current = true;
    if (!onSubmitting()) {
      submissionStarted.current = false;
      return;
    }
    setMessage(null);

    let preflight: Awaited<ReturnType<typeof iam.currentSession>>;
    try {
      preflight = await iam.currentSession();
    } catch {
      returnToReady("The local service is unavailable. The password change was not started; try again.");
      return;
    }
    if (!preflight.ok) {
      if (preflight.problem.code === "dashboard_authentication_required") onExpired();
      else returnToReady(safeProblemMessage(preflight.problem));
      return;
    }
    if (preflight.status !== 200) {
      returnToReady("The password change was not started. Check local diagnostics and try again.");
      return;
    }

    let result: Awaited<ReturnType<typeof iam.changePassword>>;
    try {
      result = await iam.changePassword(preflight.data, current, next);
    } catch (error) {
      if (error instanceof CsrfUnavailableError) onProofUnavailable();
      else await classifyUnknownMutation();
      return;
    }

    if (!result.ok) {
      if (result.problem.code === "dashboard_authentication_required") {
        onExpired();
      } else if (result.problem.code === "csrf_validation_failed") {
        onProofUnavailable();
      } else if (isKnownNoncommittedFailure(result.status, result.problem)) {
        returnToReady(safeProblemMessage(result.problem));
      } else {
        await classifyUnknownMutation();
      }
      return;
    }
    if (result.status !== 204) {
      await classifyUnknownMutation();
      return;
    }

    let renewed: Awaited<ReturnType<typeof iam.currentSession>>;
    try {
      renewed = await iam.currentSession();
    } catch {
      onUncertain();
      return;
    }
    if (!renewed.ok) {
      if (renewed.problem.code === "dashboard_authentication_required") onExpired();
      else onUncertain();
      return;
    }
    if (renewed.status !== 200) {
      onUncertain();
      return;
    }
    onChanged(renewed.data);
  }

  const isSubmitting = phase === "submitting";
  return (
    <section
      aria-labelledby="password-change-title"
      aria-busy={isSubmitting}
      className="security-panel"
      data-password-lifecycle={phase}
    >
      <h2 id="password-change-title" tabIndex={-1}>Change administrator password</h2>
      <p>Changing the password revokes other browser sessions. The current session receives a new binding.</p>
      <form className="password-form" onSubmit={(event) => { void submit(event); }}>
        <label htmlFor="current-password">Current password</label>
        <input ref={currentPassword} id="current-password" name="current" type="password" autoComplete="current-password" required disabled={isSubmitting} />
        <label htmlFor="new-password">New password</label>
        <input id="new-password" name="next" type="password" autoComplete="new-password" minLength={15} required disabled={isSubmitting} />
        <label htmlFor="confirmation-password">Confirm new password</label>
        <input id="confirmation-password" name="confirmation" type="password" autoComplete="new-password" minLength={15} required disabled={isSubmitting} />
        <button type="submit" disabled={isSubmitting}>{isSubmitting ? "Saving…" : "Save new password"}</button>
      </form>
      {phase === "ready" && <button type="button" className="quiet-button" onClick={onCancel}>Cancel</button>}
      {message && <p role="status" className="form-status">{message}</p>}
    </section>
  );
}
