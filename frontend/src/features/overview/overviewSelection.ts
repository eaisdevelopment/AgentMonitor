/** Allowlisted nonsecret presentation state; never an authorization decision. */
const opaque = /^[A-Za-z0-9_-]{1,256}$/;
export function safeOverviewSearch(search: string, detail = false): string {
  const input = new URLSearchParams(search);
  const output = new URLSearchParams();
  const organizations = input.get("organization_ids");
  if (organizations !== null && organizations.length <= 25700) {
    const values = organizations === "" ? [] : organizations.split(",");
    if (values.length <= 100 && values.every(value => opaque.test(value))) output.set("organization_ids", [...new Set(values)].sort().join(","));
  }
  const ungrouped = input.get("include_ungrouped");
  if (ungrouped === "true" || ungrouped === "false") output.set("include_ungrouped", ungrouped);
  const provider = input.get("provider_key");
  if (provider !== null && ["claude", "codex", "ollama"].includes(provider)) output.set("provider_key", provider);
  const resources = input.get("resource_type");
  if (resources !== null && ["all", "subscriptions", "api"].includes(resources)) output.set("resource_type", resources);
  const range = input.get("range");
  if (range === "7" || range === "30") output.set("range", range);
  const time = (key: string): Date | null => {
    const value = input.get(key);
    if (value === null || !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{1,3})?Z$/.test(value)) return null;
    const date = new Date(value);
    return Number.isFinite(date.getTime()) ? date : null;
  };
  const start = time("period_start"), end = time("period_end"), asOf = time("as_of");
  if (start !== null && end !== null && start.getTime() % 86400000 === 0 && end.getTime() % 86400000 === 0 && [7, 30].includes((end.getTime() - start.getTime()) / 86400000)) {
    if (range !== null) output.set("range", String((end.getTime() - start.getTime()) / 86400000));
    output.set("period_start", start.toISOString());
    output.set("period_end", end.toISOString());
    if (asOf !== null && asOf >= end) output.set("as_of", asOf.toISOString());
  }
  for (const [key, keys] of [["quota_sort", ["quota", "organization", "state"]], ["financial_sort", ["state", "organization", "account"]]] as const) {
    const value = input.get(key);
    if (value !== null && keys.some(sort => value === `${sort}:ascending` || value === `${sort}:descending`)) output.set(key, value);
  }
  if (detail) {
    const keys = ["budget_resource", "budget_report", "budget_start", "budget_end", "budget_as_of"];
    const present = [...input.keys()].filter(key => key.startsWith("budget_"));
    if (present.length > 0) {
      const resource = input.get("budget_resource"), report = input.get("budget_report");
      const selectedTime = (key: string) => {
        const value = input.get(key);
        if (value === null || !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{1,6})?Z$/.test(value)) return null;
        const parsed = new Date(value);
        return Number.isFinite(parsed.getTime()) && parsed.toISOString().slice(0, 19) === value.slice(0, 19) ? parsed : null;
      };
      const selectedStart = selectedTime("budget_start"), selectedEnd = selectedTime("budget_end"), selectedAsOf = selectedTime("budget_as_of");
      const safeId = /^[A-Za-z0-9._:-]{1,256}$/;
      const valid = present.every(key => keys.includes(key) && input.getAll(key).length === 1)
        && resource !== null && safeId.test(resource) && (report === null || safeId.test(report))
        && selectedStart !== null && selectedEnd !== null && selectedAsOf !== null
        && /T00:00:00(?:\.0{1,6})?Z$/.test(input.get("budget_start") ?? "")
        && /T00:00:00(?:\.0{1,6})?Z$/.test(input.get("budget_end") ?? "")
        && selectedStart.getTime() % 86400000 === 0 && selectedEnd.getTime() % 86400000 === 0
        && [7, 30].includes((selectedEnd.getTime() - selectedStart.getTime()) / 86400000)
        && selectedEnd <= selectedAsOf;
      if (!valid) output.set("budget_selection", "invalid");
      else {
        output.set("budget_resource", resource);
        if (report !== null) output.set("budget_report", report);
        // Keep the validated source strings: Date stores only milliseconds.
        output.set("budget_start", input.get("budget_start")!);
        output.set("budget_end", input.get("budget_end")!);
        output.set("budget_as_of", input.get("budget_as_of")!);
      }
    }
  }
  return output.size === 0 ? "" : `?${output}`;
}

export function overviewSelection(search: string) {
  const params = new URLSearchParams(safeOverviewSearch(search));
  const organizations = params.get("organization_ids");
  return {
    organizationIds: organizations === null ? null : organizations === "" ? [] : organizations.split(","),
    includeUngrouped: organizations === null || params.get("include_ungrouped") !== "false",
    provider: params.get("provider_key"),
    resourceType: params.get("resource_type") ?? "all",
    days: params.get("range") === "30" || Date.parse(params.get("period_end") ?? "") - Date.parse(params.get("period_start") ?? "") === 30 * 86400000 ? 30 as const : 7 as const,
    quotaSort: params.get("quota_sort") ?? "quota:ascending",
    financialSort: params.get("financial_sort") ?? "state:ascending",
  };
}

export type OverviewSelection = ReturnType<typeof overviewSelection>;

export function changeOverviewSearch(search: string, changes: Readonly<Record<string, string | null>>): string {
  const params = new URLSearchParams(search);
  for (const [key, value] of Object.entries(changes)) {
    if (value === null) params.delete(key);
    else params.set(key, value);
  }
  return safeOverviewSearch(params.toString());
}
