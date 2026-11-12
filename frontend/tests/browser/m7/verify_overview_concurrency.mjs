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
      resolve({ name, status: valid ? value.status : "failed", reason: valid ? safeReason : "probe_revision_or_result_mismatch" });
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
