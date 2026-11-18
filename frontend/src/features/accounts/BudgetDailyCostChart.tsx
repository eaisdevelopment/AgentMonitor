import { useState, type CSSProperties } from "react";

import type { BudgetHistoryWireV1 } from "../../shared/api/client";
import { exactMoneyText } from "./budgetPresentation";
import "./BudgetHistoryChart.css";

type Props = Readonly<{ value: NonNullable<BudgetHistoryWireV1["daily_costs"]> }>;
const readable = (value: string) => value.replaceAll("_", " ");

/** API-derived totals over the full selected report, separate from source pages. */
export function BudgetDailyCostChart({ value }: Props) {
  const [selectedDay, setSelectedDay] = useState<string | null>(null);
  const points = value.items.map(row => ({ row, description: [
    `${row.period.start.slice(0, 10)} UTC`, exactMoneyText(row.amount),
    readable(row.chart.direction),
    row.derived_zero ? "Zero established by source coverage" : `${row.source_entry_count} source entries`,
    ...(row.has_adjustment ? ["Includes adjustment"] : []),
  ].join(" · ") }));
  const selected = points.find(point => point.row.period.start === selectedDay);
  return <section className="budget-history-chart" aria-label="Daily cost totals">
    <h4>Daily cost totals</h4>
    {value.state !== "available" && <p role="status">{value.state === "partial" ? "Partial totals" : "Daily totals unavailable"}: {readable(value.reason_code)}.</p>}
    {points.length > 0 && <>
      <p>Full selected report · UTC days · fixed scale · unreported days stay unknown.</p>
      <ul className="budget-history-chart-entries" data-daily-plot>
        {points.map(({ row, description }) => {
          const style: CSSProperties & { "--chart-magnitude": number } = { "--chart-magnitude": row.chart.magnitude_basis_points };
          return <li key={row.period.start}>
            <button type="button" className="budget-history-chart-entry" aria-pressed={selectedDay === row.period.start}
              onClick={() => setSelectedDay(row.period.start)} title={description} aria-label={description}
              data-daily-start={row.period.start} data-chart-direction={row.chart.direction} data-chart-magnitude={row.chart.magnitude_basis_points}>
              <span className="budget-history-chart-track" aria-hidden="true">
                <span data-chart-bar className={`budget-history-chart-bar budget-history-chart-bar-${row.chart.direction}`} style={style} />
              </span>
              <span className="budget-history-chart-entry-label" aria-hidden="true">{row.period.start.slice(5, 10)} {row.chart.direction === "zero" ? "0" : row.chart.direction === "negative" ? "−" : "+"}</span>
            </button>
          </li>;
        })}
      </ul>
      <p data-chart-selection aria-live="polite">{selected?.description ?? "Select a day for its exact total."}</p>
      <details>
        <summary>Exact daily totals</summary>
        <div className="table-scroll" tabIndex={0} role="region" aria-label="Exact daily cost totals">
          <table><caption>Daily totals calculated from this report</caption>
            <thead><tr><th scope="col">Day (UTC)</th><th scope="col">Amount</th><th scope="col">Basis</th></tr></thead>
            <tbody>{points.map(({ row }) => <tr key={row.period.start} data-daily-start={row.period.start}>
              <td>{row.period.start.slice(0, 10)}</td><td>{exactMoneyText(row.amount)}</td>
              <td>{row.derived_zero ? "Source coverage establishes zero" : `${row.source_entry_count} source entries`}{row.has_adjustment && " · includes adjustment"}</td>
            </tr>)}</tbody>
          </table>
        </div>
        <p>Source policy: {value.policy_id} · {value.policy_version}</p>
      </details>
    </>}
  </section>;
}
