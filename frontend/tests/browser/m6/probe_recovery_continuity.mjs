"use strict";

import { chromium } from "@playwright/test";

const revision = process.argv[2];
const origin = "http://127.0.0.1:43110";
let browser;
let page;
let status = "blocked";
let stage = "revision_input";
try {
  if (!/^[a-f0-9]{40}$/.test(revision ?? "")) throw new Error("revision_required");
  stage = "browser_connect";
  browser = await chromium.connectOverCDP("http://127.0.0.1:9225", { timeout: 5000 });
  stage = "browser_context";
  const context = browser.contexts()[0];
  if (context === undefined) throw new Error("browser_context_required");
  stage = "page_create";
  page = await context.newPage();
  page.setDefaultTimeout(5000);
  stage = "navigation";
  const navigation = await page.goto(origin, { waitUntil: "domcontentloaded", timeout: 10000 });
  if (navigation?.status() !== 200) throw new Error("dashboard_unavailable");
  stage = "authenticated_shell";
  await page.getByRole("button", { name: "Accounts", exact: true }).waitFor({ state: "visible" });
  stage = "revision_read";
  const response = await page.request.get(`${origin}/api/v1/operations/versions`, {
    headers: { Origin: origin }, timeout: 5000, failOnStatusCode: false,
  });
  if (response.status() !== 200) throw new Error("revision_unavailable");
  stage = "revision_match";
  const payload = await response.json();
  status = payload?.source_revision?.availability === "available"
    && payload.source_revision.source === "build_manifest"
    && payload.source_revision.value === revision ? "passed" : "failed";
} catch {
  // Only a closed result leaves this boundary, never browser or account data.
} finally {
  if (page !== undefined) await page.close().catch(() => {});
  if (browser !== undefined) await browser.close().catch(() => {});
}
if (status !== "passed") console.error(`M6 DASHBOARD PROBE: ${stage}`);
console.log(JSON.stringify({
  record_type: "agentmonitor.m6_recovery_dashboard_probe.v1",
  status, source_revision: revision, observed_at: new Date().toISOString(),
}));
process.exitCode = status === "passed" ? 0 : status === "failed" ? 1 : 3;
