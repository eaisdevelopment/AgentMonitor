import { useId, useState, type CSSProperties } from "react";

import type { BudgetHistoryWireV1 } from "../../shared/api/client";
import { exactMoneyText, exactUsageText } from "./budgetPresentation";
import "./BudgetHistoryChart.css";

type Props = Readonly<{
  items: BudgetHistoryWireV1["items"];
  hasMore: boolean;
  busy: boolean;
  failed: boolean;
}>;

/** Render published source-entry magnitudes; never aggregate or rescale facts. */
export function BudgetHistoryChart({ items, hasMore, busy, failed }: Props) {
  const selectorId = useId();
  const [selectedSeries, setSelectedSeries] = useState<string | null>(null);
  const [selectedEntry, setSelectedEntry] = useState<string | null>(null);
  const series = new Map<string, string>();
  const unavailable = new Set<string>();
  for (const item of items) {
    if (item.chart != null) series.set(item.chart.series_key, item.chart.label);
    else unavailable.add(item.chart_unavailable_reason?.replaceAll("_", " ") ?? "Chart metadata unavailable");
  }
  const activeSeries = selectedSeries !== null && series.has(selectedSeries) ? selectedSeries : series.keys().next().value;
  const points = items.flatMap(item => {
    const point = item.chart;
    const bucket = item.kind === "cost" ? item.cost : item.usage;
    if (point == null || point.series_key !== activeSeries || bucket === null) return [];
    const value = item.kind === "cost" && item.cost !== null ? exactMoneyText(item.cost.amount)
      : item.usage !== null ? exactUsageText(item.usage.quantity) : "Unavailable";
    const period = `${bucket.period.start.slice(0, 10)} to ${bucket.period.end.slice(0, 10)} UTC (end exclusive)`;
    const meaning = item.kind === "cost" && item.cost?.kind === "adjustment" ? "Adjustment" : item.kind === "cost" ? "Charge" : "Usage";
    const direction = point.direction === "zero" ? "Zero" : point.direction === "negative" ? "Negative" : "Positive";
    return [{ point, bucket, kind: item.kind, identity: `${item.kind}:${bucket.bucket_key}`,
      description: `${point.label} · ${period} · ${value} · ${meaning} · ${direction}` }];
  });
  const selected = points.find(point => point.identity === selectedEntry);

  return <section className="budget-history-chart" aria-label="History chart">
    <div className="budget-history-chart-heading">
      <h4>History chart</h4>
      {series.size > 0 && <label htmlFor={selectorId}>Series
        <select id={selectorId} aria-label="History chart series" value={activeSeries} onChange={event => setSelectedSeries(event.target.value)}>
          {[...series].map(([key, label]) => <option key={key} value={key}>{label}</option>)}
        </select>
      </label>}
    </div>
    <p>Source entries, not daily totals · gaps not filled · fixed scale per series · exact table below.
      {hasMore && " More history available; unloaded intervals are unknown."}</p>
    {busy && <p>Reading history; loaded entries unchanged.</p>}
    {failed && <p>History read failed; chart and table retain their original report and times.</p>}
    {unavailable.size > 0 && <p>Table-only entries: {[...unavailable].join("; ")}.</p>}
    {series.size > 0 && <>
      <ul className="budget-history-chart-entries" data-chart-plot>
        {points.map(({ point, bucket, kind, identity, description }) => {
          const style: CSSProperties & { "--chart-magnitude": number } = { "--chart-magnitude": point.magnitude_basis_points };
          return <li key={identity}>
            <button type="button" className="budget-history-chart-entry" aria-pressed={selectedEntry === identity}
              onClick={() => setSelectedEntry(identity)} title={description} aria-label={description}
              data-chart-bucket-key={bucket.bucket_key} data-chart-kind={kind}
              data-chart-direction={point.direction} data-chart-magnitude={point.magnitude_basis_points}>
              <span className="budget-history-chart-track" aria-hidden="true">
                <span data-chart-bar className={`budget-history-chart-bar budget-history-chart-bar-${point.direction}`} style={style} />
              </span>
              <span className="budget-history-chart-entry-label" aria-hidden="true">{bucket.period.start.slice(5, 10)} {point.direction === "zero" ? "0" : point.direction === "negative" ? "−" : "+"}</span>
            </button>
          </li>;
        })}
      </ul>
      <p data-chart-selection aria-live="polite">{selected?.description ?? "Select a bar for its exact value and UTC interval."}</p>
    </>}
  </section>;
}
