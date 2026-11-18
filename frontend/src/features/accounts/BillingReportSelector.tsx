import { useEffect, useState } from "react";
import { registry, type AccountViewV1, type BillingConnectionViewV1, type BillingReportContextV2, type BillingCollectionEligibilityWireV2 } from "../../shared/api/client";
import { collectionContext, sameCollectionContext } from "./billingCollectPresentation";

type Option = NonNullable<BillingCollectionEligibilityWireV2["collection_options"]>[number];

/** Choices come from the admitted API catalog; selection only reads stored data. */
export function BillingReportSelector({ account, connection, context, periodStart, periodEnd, onSelect, onExpired }: Readonly<{
  account: AccountViewV1; connection: BillingConnectionViewV1; context: BillingReportContextV2 | null; periodStart: string; periodEnd: string;
  onSelect: (option: Option) => void; onExpired: () => void;
}>) {
  const [options, setOptions] = useState<readonly Option[]>([]);
  const [error, setError] = useState(false);
  const [revision, setRevision] = useState(0);
  const requestContext = context ?? collectionContext(periodStart, periodEnd);
  const identity = JSON.stringify([account.account_id, account.record_version, connection.resource_id, connection.record_version, requestContext]);
  useEffect(() => {
    const controller = new AbortController();
    setOptions([]); setError(false);
    void registry.billingCollectionEligibility(account.account_id, connection.resource_id, requestContext, controller.signal).then(result => {
      if (controller.signal.aborted) return;
      if (!result.ok) {
        if (result.problem.code === "dashboard_authentication_required") onExpired();
        else setError(true);
        return;
      }
      const value = result.data;
      if (value.account_id !== account.account_id || value.resource_id !== connection.resource_id ||
          value.account_record_version !== account.record_version || value.connection_record_version !== connection.record_version ||
          value.scope_generation !== connection.scope_generation || !sameCollectionContext(requestContext, value.report_context)) { setError(true); return; }
      setOptions(value.collection_options ?? []);
    }).catch(() => { if (!controller.signal.aborted) setError(true); });
    return () => controller.abort();
  }, [identity, revision]);
  const selected = context === null ? -1 : options.findIndex(option => option.source_category === context.source_category && JSON.stringify(option.grouping) === JSON.stringify(context.grouping ?? []));
  return <div>
    <label>Report view <select aria-label="Report view" value={selected < 0 ? "" : String(selected)} disabled={options.length === 0} onChange={event => {
      const option = options[Number(event.target.value)];
      if (option) onSelect(option);
    }}>
      {selected < 0 && <option value="" disabled>{options.length === 0 ? "Report choices unavailable" : context === null ? "Choose view for a new request" : "Selected view is not supported for collection"}</option>}
      {options.map((option, index) => <option key={`${option.source_category}.${option.grouping.join(".")}`} value={index}>{option.label}</option>)}
    </select></label>
    <p>Changing the report view reads stored data. Use Collect now to request a new report.</p>
    {account.provider_key === "codex" && <p>Reports are collected in turn. A full automatic cycle can take about six hours or longer; check the selected report’s collection time. Collect now shares the same request limit.</p>}
    {error && <p role="status">Report choices could not be loaded. <button type="button" className="quiet-button" onClick={() => setRevision(value => value + 1)}>Retry report choices</button></p>}
  </div>;
}
