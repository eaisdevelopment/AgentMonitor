import { useCallback, useEffect, useMemo, useState, type FormEvent } from "react";

import {
  alerts, CsrfUnavailableError, registry,
  type AccountViewV1, type AlertRuleCommandWireV1, type AlertRuleInputV1,
  type AlertRulePageV1, type AlertRuleWireV1, type ClientResult,
  type OrganizationViewV1,
} from "../../shared/api/client";

type Condition = AlertRuleInputV1["condition_type"];
const conditionNames: Readonly<Record<Condition, string>> = {
  capacity_remaining: "Capacity remaining",
  capacity_exhausted: "Capacity exhausted",
  capacity_unavailable: "Capacity unavailable",
  forecasted_exhaustion: "Forecasted exhaustion",
  authentication_attention: "Authentication attention",
  data_stale: "Data stale",
  collector_failure: "Collector failure",
  possible_stall: "Possible stall",
};
const conditions = Object.keys(conditionNames) as Condition[];

type ReadyState = Readonly<{
  kind: "ready";
  page: AlertRulePageV1;
  organizations: readonly OrganizationViewV1[];
  accounts: readonly AccountViewV1[];
}>;
type PageState = ReadyState | Readonly<{ kind: "loading" | "error" }>;

function scopeName(rule: AlertRuleWireV1, state: ReadyState): string {
  const { scope_kind: kind, scope_id: id } = rule.scope;
  if (kind === "global") return "Global";
  if (kind === "organization") {
    return state.organizations.find((item) => item.organization_id === id)?.name ?? "Unknown organization";
  }
  if (kind === "account") {
    return state.accounts.find((item) => item.account_id === id)?.friendly_name ?? "Unknown account";
  }
  return id ?? "Unknown provider";
}

function ruleInput(rule: AlertRuleWireV1, enabled: boolean): AlertRuleInputV1 {
  return {
    condition_type: rule.condition_type,
    scope_kind: rule.scope.scope_kind,
    scope_id: rule.scope.scope_id,
    configuration: rule.configuration,
    enabled,
  };
}

function thresholdDescription(rule: AlertRuleWireV1): string {
  if (rule.condition_type !== "capacity_remaining" ||
      !("warning_remaining_basis_points" in rule.configuration)) return "Current source condition";
  return `${rule.configuration.warning_remaining_basis_points / 100}% warning · ${rule.configuration.critical_remaining_basis_points / 100}% critical`;
}

export function AlertRulesPage({
  onExpired, onProofUnavailable,
}: Readonly<{ onExpired: () => void; onProofUnavailable: () => void }>) {
  const [state, setState] = useState<PageState>({ kind: "loading" });
  const [condition, setCondition] = useState<Condition>("capacity_remaining");
  const [scopeSelection, setScopeSelection] = useState("global");
  const [warning, setWarning] = useState("20");
  const [critical, setCritical] = useState("10");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const load = useCallback(async (signal?: AbortSignal) => {
    try {
      const [ruleResult, organizationResult, accountResult] = await Promise.all([
        alerts.rules(undefined, signal), registry.organizations(signal), registry.accounts(signal),
      ]);
      if (!ruleResult.ok || !organizationResult.ok || !accountResult.ok) {
        const errors = [ruleResult, organizationResult, accountResult].filter((item) => !item.ok);
        if (errors.some((item) => !item.ok && item.problem.code === "dashboard_authentication_required")) onExpired();
        else setState({ kind: "error" });
        return;
      }
      setState({ kind: "ready", page: ruleResult.data,
        organizations: organizationResult.data.items,
        accounts: accountResult.data.items,
      });
    } catch (error) {
      if (error instanceof DOMException && error.name === "AbortError") return;
      setState({ kind: "error" });
    }
  }, [onExpired]);

  useEffect(() => {
    const controller = new AbortController();
    void load(controller.signal);
    return () => controller.abort();
  }, [load]);

  const providers = useMemo(() => state.kind === "ready"
    ? [...new Set(state.accounts.map((item) => item.provider_key))].sort() : [], [state]);
  const customRules = state.kind === "ready"
    ? state.page.items.filter((item) => item.rule_id !== null && item.archived_at === null) : [];

  async function act(
    action: () => Promise<ClientResult<AlertRuleCommandWireV1>>,
    success: string,
  ) {
    if (busy) return;
    setBusy(true);
    setMessage(null);
    try {
      const result = await action();
      if (!result.ok) {
        if (result.problem.code === "dashboard_authentication_required") onExpired();
        else if (result.problem.code === "csrf_validation_failed") onProofUnavailable();
        else if (result.problem.status === 412) {
          setMessage("This rule changed. The current version is being loaded.");
          await load();
        } else setMessage("The rule change was rejected. Check its values and try again.");
        return;
      }
      await load();
      setMessage(success);
    } catch (error) {
      if (error instanceof CsrfUnavailableError) onProofUnavailable();
      else setMessage("The local service is unavailable. Try again.");
    } finally {
      setBusy(false);
    }
  }

  function create(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const warningPercent = Number(warning);
    const criticalPercent = Number(critical);
    if (condition === "capacity_remaining" && (
      !Number.isFinite(warningPercent) || !Number.isFinite(criticalPercent) ||
      criticalPercent < 0 || warningPercent > 100 || criticalPercent > warningPercent
    )) {
      setMessage("Set percentages from 0 to 100, with critical no higher than warning.");
      return;
    }
    const separator = scopeSelection.indexOf(":");
    const kind = separator === -1 ? "global" : scopeSelection.slice(0, separator);
    const id = separator === -1 ? null : scopeSelection.slice(separator + 1);
    if (!["global", "organization", "provider", "account"].includes(kind) ||
        (kind !== "global" && !id)) {
      setMessage("Choose an available scope.");
      return;
    }
    const input: AlertRuleInputV1 = {
      condition_type: condition,
      scope_kind: kind as AlertRuleInputV1["scope_kind"],
      scope_id: id,
      enabled: true,
      configuration: condition === "capacity_remaining"
        ? { schema_major: 1,
            warning_remaining_basis_points: Math.round(warningPercent * 100),
            critical_remaining_basis_points: Math.round(criticalPercent * 100) }
        : { schema_major: 1 },
    };
    void act(() => alerts.createRule(input), "Rule created.");
  }

  function archive(rule: AlertRuleWireV1) {
    if (!window.confirm("Archive this alert rule? Its history will remain available.")) return;
    void act(() => alerts.archiveRule(rule), "Rule archived.");
  }

  return <section className="telemetry-panel rules-page" aria-labelledby="page-title" aria-busy={state.kind === "loading"}>
    <div className="panel-heading"><h1 id="page-title" tabIndex={-1}>Alert rules</h1>
      <button type="button" className="quiet-button" onClick={() => { void load(); }}>Refresh rules</button></div>
    <p className="rules-intro">Choose when an account, provider, or organization needs attention. Rules use current collected evidence.</p>
    {message && <p role="status" className="form-status">{message}</p>}
    {state.kind === "loading" && <p role="status">Loading alert rules…</p>}
    {state.kind === "error" && <p role="alert">Alert rules could not be loaded. Refresh to try again.</p>}
    {state.kind === "ready" && <>
      <form className="rules-create" onSubmit={create}>
        <h2>Create a rule</h2>
        <label>Condition
          <select value={condition} onChange={(event) => setCondition(event.target.value as Condition)}>
            {conditions.map((item) => <option key={item} value={item}>{conditionNames[item]}</option>)}
          </select>
        </label>
        <label>Applies to
          <select value={scopeSelection} onChange={(event) => setScopeSelection(event.target.value)}>
            <option value="global">All accounts</option>
            {state.organizations.filter((item) => item.lifecycle === "active").map((item) =>
              <option key={item.organization_id} value={`organization:${item.organization_id}`}>Organization · {item.name}</option>)}
            {providers.map((key) => <option key={key} value={`provider:${key}`}>Provider · {key}</option>)}
            {state.accounts.filter((item) => item.lifecycle !== "archived").map((item) =>
              <option key={item.account_id} value={`account:${item.account_id}`}>Account · {item.friendly_name}</option>)}
          </select>
        </label>
        {condition === "capacity_remaining" && <>
          <label>Warning when left is at or below
            <span className="rules-percent"><input type="number" min="0" max="100" step="0.01" required value={warning} onChange={(event) => setWarning(event.target.value)} /><span>%</span></span>
          </label>
          <label>Critical when left is at or below
            <span className="rules-percent"><input type="number" min="0" max="100" step="0.01" required value={critical} onChange={(event) => setCritical(event.target.value)} /><span>%</span></span>
          </label>
        </>}
        <button type="submit" disabled={busy}>Create rule</button>
      </form>
      <div className="rules-list-heading"><h2>Current rules</h2><span>{customRules.length} shown</span></div>
      {customRules.length === 0 ? <p>No custom alert rules yet.</p> :
        <div className="operations-table-scroll"><table className="operations-table rules-table" aria-label="Current alert rules">
          <thead><tr><th scope="col">Condition</th><th scope="col">Scope</th><th scope="col">Threshold</th><th scope="col">State</th><th scope="col">Actions</th></tr></thead>
          <tbody>{customRules.map((rule) => <tr key={rule.rule_id}>
            <th scope="row">{conditionNames[rule.condition_type]}</th>
            <td>{scopeName(rule, state)}</td>
            <td>{thresholdDescription(rule)}</td>
            <td>{rule.enabled ? "Enabled" : "Disabled"}</td>
            <td className="rules-actions">
              <button type="button" disabled={busy} onClick={() => { void act(() => alerts.updateRule(rule, ruleInput(rule, !rule.enabled)), rule.enabled ? "Rule disabled." : "Rule enabled."); }}>{rule.enabled ? "Disable rule" : "Enable rule"}</button>
              <button type="button" disabled={busy} onClick={() => archive(rule)}>Archive rule</button>
            </td>
          </tr>)}</tbody>
        </table></div>}
      {state.page.page.has_more && <p role="status">More rules exist. This page currently shows the first 200.</p>}
    </>}
  </section>;
}
