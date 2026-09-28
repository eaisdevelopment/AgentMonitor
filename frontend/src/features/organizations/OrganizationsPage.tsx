import { useCallback, useEffect, useState, type FormEvent } from "react";

import {
  CsrfUnavailableError,
  registry,
  type ClientResult,
  type OrganizationPageV1,
  type OrganizationViewV1,
} from "../../shared/api/client";

type OrganizationsState =
  | Readonly<{ kind: "loading" }>
  | Readonly<{ kind: "error"; message: string }>
  | Readonly<{ kind: "ready"; page: OrganizationPageV1 }>;

export function OrganizationsPage({
  onExpired,
  onProofUnavailable,
}: Readonly<{
  onExpired: () => void;
  onProofUnavailable: () => void;
}>) {
  const [state, setState] = useState<OrganizationsState>({ kind: "loading" });
  const [name, setName] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const load = useCallback(async (signal?: AbortSignal) => {
    setState({ kind: "loading" });
    try {
      const result = await registry.organizations(signal);
      if (!result.ok) {
        if (result.problem.code === "dashboard_authentication_required") onExpired();
        else setState({ kind: "error", message: "Organizations could not be loaded from the local service." });
        return;
      }
      setState({ kind: "ready", page: result.data });
    } catch (error) {
      if (error instanceof DOMException && error.name === "AbortError") return;
      setState({ kind: "error", message: "The local organization registry is unavailable." });
    }
  }, [onExpired]);

  useEffect(() => {
    const controller = new AbortController();
    void load(controller.signal);
    return () => controller.abort();
  }, [load]);

  async function create(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const submitted = name.trim();
    if (!submitted || busy) return;
    setBusy(true);
    setMessage(null);
    try {
      const result = await registry.createOrganization(submitted, null);
      if (!result.ok) {
        if (result.problem.code === "dashboard_authentication_required") onExpired();
        else if (result.problem.code === "csrf_validation_failed") onProofUnavailable();
        else if (result.problem.code === "registry_name_conflict") setMessage("An active organization already has that name.");
        else setMessage("The organization could not be created. Check the name and try again.");
        return;
      }
      setName("");
      setMessage("Organization created.");
      await load();
    } catch (error) {
      if (error instanceof CsrfUnavailableError) onProofUnavailable();
      else setMessage("The local service is unavailable. Try again.");
    } finally {
      setBusy(false);
    }
  }

  async function edit(
    operation: () => Promise<ClientResult<OrganizationViewV1>>,
    successMessage: string,
  ) {
    if (busy) return;
    setBusy(true);
    setMessage(null);
    try {
      const result = await operation();
      if (!result.ok) {
        if (result.problem.code === "dashboard_authentication_required") onExpired();
        else if (result.problem.code === "csrf_validation_failed") onProofUnavailable();
        else if (result.problem.status === 412) {
          setMessage("The organization changed. Refresh its current version and try again.");
          await load();
        } else if (result.problem.code === "registry_organization_not_empty") {
          setMessage("Move or archive its accounts before archiving this organization.");
        } else setMessage("The organization change was rejected. Check the value and try again.");
        return;
      }
      await load();
      setMessage(successMessage);
    } catch (error) {
      if (error instanceof CsrfUnavailableError) onProofUnavailable();
      else setMessage("The local service is unavailable. Try again.");
    } finally {
      setBusy(false);
    }
  }

  async function move(organizationId: string, direction: -1 | 1) {
    if (busy || state.kind !== "ready" || state.page.page.has_more) return;
    const active = state.page.items.filter((item) => item.lifecycle === "active");
    const current = active.findIndex((item) => item.organization_id === organizationId);
    const target = current + direction;
    if (current < 0 || target < 0 || target >= active.length) return;
    const ids = active.map((item) => item.organization_id);
    const currentId = ids[current];
    const targetId = ids[target];
    const first = active[0];
    if (currentId === undefined || targetId === undefined || first === undefined) return;
    ids[current] = targetId;
    ids[target] = currentId;
    setBusy(true);
    setMessage(null);
    try {
      const result = await registry.reorderOrganizations(ids, first.registry_revision);
      if (!result.ok) {
        if (result.problem.code === "dashboard_authentication_required") onExpired();
        else if (result.problem.code === "csrf_validation_failed") onProofUnavailable();
        else if (result.problem.status === 412) {
          setMessage("The organization list changed. Refresh and try again.");
          await load();
        } else setMessage("The organization order could not be saved.");
        return;
      }
      await load();
      setMessage("Organization order saved.");
    } catch (error) {
      if (error instanceof CsrfUnavailableError) onProofUnavailable();
      else setMessage("The local service is unavailable. Try again.");
    } finally {
      setBusy(false);
    }
  }

  const activeCount = state.kind === "ready"
    ? state.page.items.filter((item) => item.lifecycle === "active").length
    : 0;

  return (
    <div className="feature-page">
      <section className="command-deck" aria-labelledby="page-title">
        <div>
          <p className="eyebrow">Registry / organization administration</p>
          <h1 id="page-title" tabIndex={-1}>Organizations</h1>
          <p className="console-summary">Create groups here, then assign monitored accounts from the account registry.</p>
        </div>
      </section>
      <section className="telemetry-panel" aria-labelledby="create-organization-title">
        <div className="panel-heading"><h2 id="create-organization-title">Create organization</h2></div>
        <form onSubmit={(event) => { void create(event); }}>
          <label htmlFor="organization-name">Organization name</label>
          <input
            id="organization-name"
            type="text"
            maxLength={256}
            required
            value={name}
            onChange={(event) => setName(event.target.value)}
            autoComplete="off"
          />
          <button type="submit" disabled={busy || !name.trim()}>Create organization</button>
        </form>
        {message && <p role="status">{message}</p>}
      </section>
      <section className="telemetry-panel" aria-labelledby="organization-list-title">
        <div className="panel-heading"><h2 id="organization-list-title">Organization registry</h2></div>
        {state.kind === "loading" && <p role="status">Reading organizations…</p>}
        {state.kind === "error" && <p role="alert">{state.message}</p>}
        {state.kind === "ready" && state.page.items.length === 0 && (
          <p>No organizations have been created.</p>
        )}
        {state.kind === "ready" && state.page.items.length > 0 && (
          <div className="record-grid">
            {state.page.items.map((organization, index) => (
              <article className="record-card" key={organization.organization_id}>
                <strong>{organization.name}</strong>
                <p>{organization.active_account_count} active accounts</p>
                <p className="record-meta">{organization.lifecycle}</p>
                {organization.lifecycle === "active" && (
                  <div>
                    <button type="button" className="quiet-button" aria-label={`Move ${organization.name} up`} disabled={busy || state.page.page.has_more || index === 0} onClick={() => { void move(organization.organization_id, -1); }}>Move up</button>
                    <button type="button" className="quiet-button" aria-label={`Move ${organization.name} down`} disabled={busy || state.page.page.has_more || index >= activeCount - 1} onClick={() => { void move(organization.organization_id, 1); }}>Move down</button>
                  </div>
                )}
                <form key={organization.record_version} onSubmit={(event) => {
                  event.preventDefault();
                  const submitted = new FormData(event.currentTarget).get("name");
                  if (typeof submitted === "string") void edit(
                    () => registry.renameOrganization(organization, submitted.trim()),
                    "Organization name saved.",
                  );
                }}>
                  <label htmlFor={`rename-organization-${organization.organization_id}`}>Rename organization</label>
                  <input id={`rename-organization-${organization.organization_id}`} name="name" defaultValue={organization.name} maxLength={256} required />
                  <button type="submit" disabled={busy}>Save organization name</button>
                </form>
                {organization.lifecycle === "archived" ? (
                  <button type="button" disabled={busy} onClick={() => { void edit(() => registry.restoreOrganization(organization), "Organization restored."); }}>Restore organization</button>
                ) : (
                  <button type="button" disabled={busy || organization.active_account_count > 0} onClick={() => { void edit(() => registry.archiveOrganization(organization), "Organization archived."); }}>Archive organization</button>
                )}
              </article>
            ))}
          </div>
        )}
        {state.kind === "ready" && state.page.page.has_more && (
          <p role="status">More organizations are available beyond this page.</p>
        )}
      </section>
    </div>
  );
}
