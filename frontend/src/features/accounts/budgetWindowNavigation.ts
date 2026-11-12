/** Fixed stored-data windows; never initiates collection or computes money. */
export type BudgetWindow = Readonly<{ period_start: string; period_end: string; as_of: string }>;
const DAY = 86400000;

function timestamp(value: string): number {
  if (!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{1,6})?Z$/.test(value)) throw new Error("budget_window_invalid");
  const parsed = Date.parse(value);
  if (!Number.isFinite(parsed) || new Date(parsed).toISOString().slice(0, 19) !== value.slice(0, 19)) throw new Error("budget_window_invalid");
  return parsed;
}

export function budgetWindowDays(query: BudgetWindow): 7 | 30 {
  const start = timestamp(query.period_start), end = timestamp(query.period_end), asOf = timestamp(query.as_of);
  const days = (end - start) / DAY;
  if ((days !== 7 && days !== 30) || end > asOf ||
      !/T00:00:00(?:\.0{1,6})?Z$/.test(query.period_start) ||
      !/T00:00:00(?:\.0{1,6})?Z$/.test(query.period_end)) throw new Error("budget_window_invalid");
  return days;
}

export function shiftBudgetWindow(query: BudgetWindow, direction: -1 | 1): BudgetWindow | null {
  const days = budgetWindowDays(query);
  const end = timestamp(query.period_end) + direction * days * DAY;
  if (end > Math.floor(timestamp(query.as_of) / DAY) * DAY) return null;
  return { period_start: new Date(end - days * DAY).toISOString(), period_end: new Date(end).toISOString(), as_of: query.as_of };
}

export function resizeBudgetWindow(query: BudgetWindow, days: 7 | 30): BudgetWindow {
  budgetWindowDays(query);
  return { period_start: new Date(timestamp(query.period_end) - days * DAY).toISOString(), period_end: query.period_end, as_of: query.as_of };
}

export function latestBudgetWindow(days: 7 | 30, asOf: string): BudgetWindow {
  const end = Math.floor(timestamp(asOf) / DAY) * DAY;
  return { period_start: new Date(end - days * DAY).toISOString(), period_end: new Date(end).toISOString(), as_of: asOf };
}

/** Explicit navigation drops a report selection while retaining its resource filter. */
export function budgetWindowSearch(search: string, query: BudgetWindow, resourceId: string | null): string {
  budgetWindowDays(query);
  if (resourceId !== null && !/^[A-Za-z0-9._:-]{1,256}$/.test(resourceId)) throw new Error("budget_window_invalid");
  const params = new URLSearchParams(search);
  for (const key of [...params.keys()]) if (key.startsWith("budget_")) params.delete(key);
  if (resourceId !== null) params.set("budget_resource", resourceId);
  params.set("budget_start", query.period_start);
  params.set("budget_end", query.period_end);
  params.set("budget_as_of", query.as_of);
  return `?${params}`;
}
