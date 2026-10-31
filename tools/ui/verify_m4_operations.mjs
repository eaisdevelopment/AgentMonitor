/** ST-OPS-001: compare the built Operations page with its real API response. */
import { chromium } from "../../frontend/node_modules/@playwright/test/index.mjs";

const endpoint = process.env.AGENTMONITOR_TEST_DASHBOARD_CDP_ENDPOINT;
const origin = process.env.AGENTMONITOR_TEST_DASHBOARD_ORIGIN;
let stage = "prerequisites";

class VerificationError extends Error {
  constructor(code, blocked = false) {
    super(code);
    this.blocked = blocked;
  }
}
function verify(condition, code) {
  if (!condition) throw new VerificationError(code);
}
function requireLive(condition, code) {
  if (!condition) throw new VerificationError(code, true);
}
function codeOnly(error) {
  return error instanceof VerificationError ? error.message : "browser_verification_unavailable";
}

const componentNames = {
  foundation: "Service", configuration: "Configuration", database: "Database",
  identity_access: "Dashboard sign-in", registry: "Account registry",
  provider_system: "Provider connections", collection_control: "Quota collector",
  capacity: "Capacity", runtime_observation: "Agent activity", alerting: "Alerts",
  "provider.claude": "Claude",
};
const versionNames = [
  ["Application", "application_version"], ["Database", "schema_version"],
  ["API", "api_version"], ["OpenAPI", "openapi_version"],
  ["Generated client", "client_version"], ["Dashboard", "frontend_version"],
];

try {
  requireLive(
    endpoint && origin && new URL(endpoint).hostname === "127.0.0.1"
      && new URL(origin).hostname === "127.0.0.1" && new URL(origin).protocol === "http:",
    "explicit_loopback_dashboard_required",
  );
  const browser = await chromium.connectOverCDP(endpoint);
  const page = browser.contexts()[0]?.pages()[0];
  requireLive(page && await page.evaluate(() => location.origin) === origin, "shared_dashboard_required");

  let mutations = 0;
  page.on("request", (request) => {
    if (new URL(request.url()).origin === origin
      && request.url().includes("/api/v1/")
      && !["GET", "HEAD"].includes(request.method())) mutations += 1;
  });
  stage = "authenticated_api";
  const initial = await page.evaluate(async () => {
    const paths = ["liveness", "health", "readiness", "versions"];
    const results = await Promise.all(paths.map(async (name) => {
      const response = await fetch(`/api/v1/operations/${name}`);
      return [name, response.status, response.ok ? await response.json() : null];
    }));
    return results;
  });
  requireLive(initial.every(([, status]) => status === 200), "authenticated_operations_api_required");
  const byName = Object.fromEntries(initial.map(([name, , value]) => [name, value]));
  verify(byName.liveness?.state === "healthy", "operations_liveness_mismatch");
  verify(byName.readiness?.state === "ready", "operations_readiness_mismatch");
  const required = ["foundation", "configuration", "database", "identity_access", "registry"];
  const healthComponents = new Map(byName.health?.components?.map((item) => [item.component_key, item]) ?? []);
  verify(required.every((key) => healthComponents.get(key)?.sample?.state === "healthy"), "required_component_not_healthy");
  verify(byName.versions?.schema_version?.value && byName.versions.schema_version.availability === "available", "real_schema_version_unavailable");

  stage = "built_page";
  await page.goto(origin);
  const responsePromise = page.waitForResponse(
    (response) => new URL(response.url()).pathname === "/api/v1/operations/diagnostics"
      && response.request().method() === "GET",
    { timeout: 15_000 },
  );
  await page.getByRole("button", { name: "Operations", exact: true }).click();
  const response = await responsePromise;
  requireLive(response.status() === 200, "authenticated_diagnostics_required");
  const diagnostics = await response.json();
  const wire = JSON.stringify(diagnostics);
  verify(!/[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+/.test(wire), "diagnostics_identity_disclosure");
  verify(!/\/(?:home|Users|tmp)\//.test(wire), "diagnostics_path_disclosure");
  verify(!/"(?:password|token|email|prompt|profile_path|working_directory)"\s*:/.test(wire), "diagnostics_forbidden_field");
  verify(
    JSON.stringify(Object.keys(diagnostics).sort()) === JSON.stringify([
      "availability", "configuration_presence", "correlation_id", "generated_at",
      "health", "readiness", "reason_codes", "valid_until", "versions",
    ].sort()),
    "diagnostics_contract_unbounded",
  );
  verify(diagnostics.readiness.state === "ready", "diagnostics_readiness_mismatch");
  verify(diagnostics.versions.schema_version.value === byName.versions.schema_version.value, "schema_version_changed_between_reads");

  const table = page.getByRole("table", { name: "Component health", exact: true });
  await table.waitFor({ timeout: 10_000 });
  verify(await page.getByRole("heading", { name: "Operations", exact: true }).count() === 1, "operations_heading_missing");
  const summary = page.locator('.operations-summary[aria-label="Service status"]');
  verify(await summary.count() === 1, "service_summary_missing");
  const chips = await summary.locator(".state-chip").allTextContents();
  verify(chips.length === 2, "service_state_chips_missing");
  verify(chips[0].trim() === diagnostics.health.state, "service_health_state_mismatch");
  verify(chips[1].trim() === diagnostics.readiness.state, "service_readiness_state_mismatch");
  const summaryText = await summary.innerText();
  const expectedChecks = `${diagnostics.health.components.filter((item) => item.outcome === "available").length}/${diagnostics.health.components.length}`;
  verify(summaryText.includes(expectedChecks), "component_counts_not_authoritative");
  const rows = table.locator("tbody tr");
  verify(await rows.count() === diagnostics.health.components.length, "component_rows_missing");
  for (let index = 0; index < diagnostics.health.components.length; index += 1) {
    const item = diagnostics.health.components[index];
    const row = rows.nth(index);
    verify(await row.getByRole("rowheader").innerText() === (componentNames[item.component_key] ?? item.component_key), "component_name_mismatch");
    const displayedState = await row.locator(".state-chip").textContent();
    const expectedState = (item.sample?.state ?? item.outcome).replaceAll("_", " ");
    const visibleState = (displayedState ?? "").trim();
    verify(
      visibleState === expectedState,
      `component_state_mismatch_${item.component_key.replaceAll(".", "_")}`,
    );
    verify(await row.locator("time").count() === 1, "component_check_time_missing");
  }
  await page.getByText("Versions and configuration", { exact: true }).click();
  const versions = page.locator(".operations-versions");
  for (const [label, field] of versionNames) {
    const value = diagnostics.versions[field];
    verify(value && await versions.getByText(label, { exact: true }).count() === 1, "version_label_missing");
    const expected = value.value ?? `Not reported (${value.availability.replaceAll("_", " ")})`;
    verify(await versions.getByText(expected, { exact: true }).count() >= 1, "version_value_mismatch");
  }
  const availability = diagnostics.availability.state === "available"
    ? "All diagnostics reported." : "Some diagnostics are unavailable.";
  verify(await page.getByText(availability, { exact: true }).count() === 1, "diagnostic_availability_hidden");

  stage = "refresh_and_responsive";
  const refreshResponse = page.waitForResponse(
    (item) => new URL(item.url()).pathname === "/api/v1/operations/diagnostics"
      && item.request().method() === "GET",
    { timeout: 15_000 },
  );
  await page.getByRole("button", { name: "Refresh status", exact: true }).click();
  const refreshed = await refreshResponse;
  verify(refreshed.status() === 200, "operations_refresh_failed");
  const current = await refreshed.json();
  verify(Date.parse(current.generated_at) >= Date.parse(diagnostics.generated_at), "operations_refresh_regressed");
  const priorViewport = page.viewportSize();
  try {
    await page.setViewportSize({ width: 390, height: 844 });
    verify(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), "operations_mobile_overflow");
    verify(await table.isVisible(), "operations_mobile_table_missing");
  } finally {
    if (priorViewport) await page.setViewportSize(priorViewport);
  }
  verify(mutations === 0, "operations_read_started_mutation");
  console.log(`M4 OPERATIONS: PASSED — real authenticated API, ${diagnostics.health.components.length} component rows, authoritative versions, refresh, narrow layout and read-only navigation`);
  process.exit(0);
} catch (error) {
  const blocked = error instanceof VerificationError && error.blocked;
  console.log(`M4 OPERATIONS: ${blocked ? "BLOCKED" : "FAILED"} — ${stage}: ${codeOnly(error)}`);
  process.exit(blocked ? 3 : 1);
}
