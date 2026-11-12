import { useEffect, useRef, useState } from "react";

import { budgets, type BudgetForecastWireV1 } from "../../shared/api/client";
import { historyContextKey, historyPageMatches, type HistoryContext } from "./budgetHistoryPagination";
import { exactMoneyText } from "./budgetPresentation";

type Props = Readonly<{ context: HistoryContext; onExpired: () => void }>;
const readable = (value: string) => value.replaceAll("_", " ");
const time = (value: string) => new Date(value).toLocaleString(undefined, { timeZoneName: "short" });

function ObservedRate({ context, onExpired }: Props) {
  const key = historyContextKey(context);
  const [value, setValue] = useState<BudgetForecastWireV1 | null>(null);
  const [busy, setBusy] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);
  const expired = useRef(onExpired);
  expired.current = onExpired;

  useEffect(() => {
    const controller = new AbortController();
    setBusy(true);
    setError(null);
    void (async () => {
      try {
        const result = await budgets.forecast(context.resourceId, { account_id: context.accountId,
          report_id: context.reportId, period_start: context.periodStart, period_end: context.periodEnd,
          as_of: context.asOf }, controller.signal);
        if (controller.signal.aborted) return;
        if (!result.ok) {
          if (result.problem.code === "dashboard_authentication_required") expired.current();
          else if (result.problem.status === 404 || result.problem.status === 410) setError("Analysis for this selected report is unavailable or no longer retained. Spend and history remain separate; choose a retained report or refresh the view.");
          else setError("Analysis could not be read. Spend, balances and history remain unchanged. Retry analysis reads this same stored selection.");
          return;
        }
        if (!historyPageMatches(context, result.data.report, result.data.as_of)) throw new Error("forecast_context_mismatch");
        setValue(result.data);
      } catch {
        if (!controller.signal.aborted) setError("Analysis could not be read consistently. Spend, balances and history remain unchanged. Retry analysis reads this same stored selection.");
      } finally {
        if (!controller.signal.aborted) setBusy(false);
      }
    })();
    return () => controller.abort();
  }, [key, attempt]);

  const rate = value?.rate;
  return <section aria-label="Observed spending rate" data-budget-rate={context.reportId}
    data-rate-as-of={value?.as_of ?? context.asOf} aria-busy={busy} style={{ padding: ".65rem", marginBlock: ".65rem", minWidth: 0, overflowWrap: "anywhere" }}>
    {busy && <p role="status">Reading observed spending rate…</p>}
    {error !== null && <p role="alert">{error}</p>}
    {value !== null && <>
      <p><strong>Observed spending rate: </strong>{rate == null ? `Unavailable — ${readable(value.rate_reason)}` : <>
        {rate.display_text ?? `${exactMoneyText(rate.cost)} / ${rate.covered_seconds} seconds`}
        {" · Sample "}<time dateTime={rate.period.start}>{rate.period.start.slice(0, 10)}</time> to <time dateTime={rate.period.end}>{rate.period.end.slice(0, 10)}</time> UTC (end exclusive)
        {value.rate_reason === "no_consumption" && ". No consumption in observed interval."}
      </>}</p>
      <p>{value.exhaustion_at === null ? `Estimate unavailable — ${readable(value.exhaustion_reason)}.` : <>
        Estimated at the observed rate: <time data-exhaustion-at dateTime={value.exhaustion_at}>{time(value.exhaustion_at)}</time>
        {value.funds_observed_at !== null && <> · As of funds observed <time dateTime={value.funds_observed_at}>{time(value.funds_observed_at)}</time></>}. This is an as-of estimate, not a service-stop promise.
      </>}</p>
      <details><summary>Calculation details</summary>
        <dl className="telemetry-readouts">
          <div><dt>Read snapshot</dt><dd><time dateTime={value.as_of}>{time(value.as_of)}</time></dd></div>
          <div><dt>Provider scope</dt><dd>{value.report.scope_id ?? "Not established"} · {readable(value.report.scope_evidence)} · Scope generation {value.report.scope_generation}</dd></div>
          <div><dt>Cost basis</dt><dd>{readable(value.report.cost_basis)}</dd></div>
          {rate != null && <>
            <div><dt>Exact cost numerator</dt><dd>{exactMoneyText(rate.cost)}</dd></div>
            <div><dt>Covered duration</dt><dd>{rate.covered_seconds} seconds · {rate.day_count} complete UTC days</dd></div>
            <div><dt>Rate display</dt><dd>{rate.display_rounding === null ? "Exact cost / duration; no guessed currency precision" : `${readable(rate.display_rounding)}${rate.display_decimal_places === null ? "" : ` · ${rate.display_decimal_places} decimal places`}`}</dd></div>
            <div><dt>Input reports</dt><dd>{rate.input_report_ids.join(", ")}</dd></div>
            <div><dt>Input entries</dt><dd>{rate.input_bucket_keys.join(", ")}</dd></div>
          </>}
          <div><dt>Method</dt><dd>{value.method_id} · {value.method_version}</dd></div>
          <div><dt>Source policy</dt><dd>{value.source_policy_id ?? "Not reported"}{value.source_policy_version === null ? "" : ` · ${value.source_policy_version}`}</dd></div>
          {value.input_observation_ids.length > 0 && <div><dt>Funds observations</dt><dd>{value.input_observation_ids.join(", ")}</dd></div>}
          {value.time_left_numerator !== null && value.time_left_denominator !== null && <div><dt>Exact time-left fraction</dt><dd>{value.time_left_numerator} / {value.time_left_denominator} · {readable(value.time_rounding)}</dd></div>}
        </dl>
      </details>
    </>}
    {error !== null && <button type="button" className="quiet-button" disabled={busy} onClick={() => setAttempt(current => current + 1)}>Retry analysis</button>}
  </section>;
}

export function BudgetObservedRate(props: Props) {
  return <ObservedRate key={historyContextKey(props.context)} {...props} />;
}
