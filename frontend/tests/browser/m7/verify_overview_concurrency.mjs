"use strict";

// Reproduce the installed multi-page failure using the existing read-only probes.
// All children settle before exit; never retry a failure into a pass.
import { spawn } from "node:child_process";
import { fileURLToPath } from "node:url";

const expectedRevision = process.argv[2];
const validRevision = /^[a-f0-9]{40}$/.test(expectedRevision ?? "");
const jobs = [
  ["overview", "verify_overview.mjs", []],
  ["setup", "verify_setup.mjs", [expectedRevision]],
  ["cloud_controls", "verify_cloud_collect.mjs", []],
];

// Only known stage/error labels and structural diagnostics cross this boundary.
// Never forward URLs, identifiers, exception text or arbitrary child payloads.
const stages = new Set(["tooling", "browser", "authentication", "revision", "overview", "setup_form", "account_layout", "scope_contract", "continuity", "financial_entry", "source_history", "retained_refresh", "initial_window", "previous_window", "refresh_window", "next_window", "wide_window", "latest_window", "period_only_reload", "ordinary_account_entry", "overview_back", "controls", "eligibility", "collection", "rendered_summary", "financial_panel_settle"]);
const setupSteps = new Set(["accounts_navigation", "add_api_control", "add_api_heading", "provider_choices", "create_control"]);
const families = new Set(["accounts", "organizations", "budget_summary", "account_detail", "cloud_eligibility", "cloud_run", "other"]);
const networkErrors = new Set(["net::ERR_NETWORK_CHANGED", "net::ERR_INTERNET_DISCONNECTED", "net::ERR_CONNECTION_REFUSED", "net::ERR_CONNECTION_RESET", "net::ERR_CONNECTION_CLOSED", "net::ERR_TIMED_OUT", "net::ERR_ABORTED", "net::ERR_FAILED", "network_error_other"]);
const httpStatus = value => Number.isInteger(value) && value >= 100 && value <= 599 ? value : null;
const booleanFields = (value, names) => Object.fromEntries(names.filter(name => typeof value?.[name] === "boolean").map(name => [name, value[name]]));
function diagnostics(value) {
  const render = value.render_diagnostic;
  const rows = value.row_set_diagnostic;
  const availability = value.availability_diagnostic;
  const availabilityFamily = { "/api/v1/budgets": "budget_overview", "/api/v1/accounts": "accounts", "/api/v1/organizations": "organizations" }[availability?.path] ?? "other";
  return {
    stage: stages.has(value.stage) ? value.stage : null,
    setup_step: setupSteps.has(value.setup_step) ? value.setup_step : null,
    error_kind: ["timeout", "assertion_or_error"].includes(value.error_kind) ? value.error_kind : null,
    render_diagnostic: render == null ? null : {
      phase: ["entry", "reload", "collection_reload"].includes(render.phase) ? render.phase : null,
      summary_status: httpStatus(render.summary_status),
      ...booleanFields(render, ["resource_present", "panel_settled"]),
      page_state: render.page_state == null ? null : booleanFields(render.page_state, ["signed_out", "financial_panel_present", "financial_panel_busy", "alert_visible", "invalid_selection"]),
    },
    response_diagnostics: Array.isArray(value.response_diagnostics) ? value.response_diagnostics.slice(0, 40).map(item => ({ family: families.has(item?.family) ? item.family : "other", status: httpStatus(item?.status) })) : [],
    failed_requests: Array.isArray(value.failed_requests) ? value.failed_requests.slice(0, 40).map(item => ({
      family: typeof item === "object" && families.has(item?.family) ? item.family : "other",
      error: networkErrors.has(typeof item === "string" ? item : item?.error) ? typeof item === "string" ? item : item.error : "network_error_other",
    })) : [],
    row_set_diagnostic: rows == null ? null : {
      ...Object.fromEntries(["expected_rows", "rendered_rows"].filter(name => Number.isSafeInteger(rows[name]) && rows[name] >= 0).map(name => [name, rows[name]])),
      ...booleanFields(rows, ["refresh_error_visible"]),
      overview_response_statuses: Array.isArray(rows.overview_response_statuses) ? rows.overview_response_statuses.slice(0, 40).map(httpStatus) : [],
    },
    availability_diagnostic: availability == null ? null : { family: availabilityFamily, state: ["available", "partial", "unavailable", "stale", "unsupported", "unknown"].includes(availability.state) ? availability.state : null },
  };
}

function run([name, file, args]) {
  return new Promise(resolve => {
    const child = spawn(process.execPath, [fileURLToPath(new URL(file, import.meta.url)), ...args], {
      stdio: ["ignore", "pipe", "pipe"],
    });
    let output = "", stderr = false, overflow = false, expired = false;
    child.stdout.on("data", chunk => {
      if (output.length + chunk.length > 16384) { overflow = true; child.kill("SIGTERM"); }
      else output += chunk.toString();
    });
    child.stderr.on("data", () => { stderr = true; });
    const timer = setTimeout(() => { expired = true; child.kill("SIGTERM"); }, 180000);
    child.on("error", () => { clearTimeout(timer); resolve({ name, status: "blocked", reason: "probe_launch_failed" }); });
    child.on("close", code => {
      clearTimeout(timer);
      let value;
      try { value = JSON.parse(output); } catch { /* No raw child output in diagnostics. */ }
      if (expired || overflow || stderr || value === undefined) {
        resolve({ name, status: "failed", reason: expired ? "probe_deadline" : "probe_output_invalid" });
        return;
      }
      const revision = value.source_revision ?? value.revision;
      const unsafe = value.unsafe_requests ?? value.unsafe;
      const expectedCode = { passed: 0, failed: 1, blocked: 3 }[value.status];
      const reason = value.reason_code ?? value.reason;
      const safeReason = typeof reason === "string" && /^[a-z0-9_]+$/.test(reason) ? reason : null;
      const valid = code === expectedCode && unsafe === 0 && revision === expectedRevision;
      resolve({ name, status: valid ? value.status : "failed", reason: valid ? safeReason : "probe_revision_or_result_mismatch", ...diagnostics(value) });
    });
  });
}

const results = validRevision ? await Promise.all(jobs.map(run)) : [];
const status = !validRevision || results.some(item => item.status === "failed") ? "failed"
  : results.every(item => item.status === "passed") ? "passed" : "blocked";
process.stdout.write(JSON.stringify({
  record_type: "agentmonitor.m7_concurrent_overview_probe.v1", status,
  expected_revision: validRevision ? expectedRevision : null,
  checks: results, observed_at: new Date().toISOString(),
  scope: "concurrent_real_overview_setup_cloud_reads_no_mutations",
}) + "\n", () => process.exit({ passed: 0, failed: 1, blocked: 3 }[status]));
