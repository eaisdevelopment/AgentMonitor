"use strict";

import { chromium } from "@playwright/test";

let browser;
let page;
try {
  browser = await chromium.connectOverCDP("http://127.0.0.1:9225");
  const shared = browser.contexts().flatMap(context => context.pages()).find(item => {
    try { return new URL(item.url()).origin === "http://127.0.0.1:43110"; } catch { return false; }
  });
  if (!shared) throw new Error("signed_in_dashboard_required");
  page = await shared.context().newPage();
  await page.goto("http://127.0.0.1:43110/");
  const result = await page.evaluate(async () => {
    const organizations = await fetch("/api/v1/organizations?limit=200");
    if (!organizations.ok) return { status: "blocked", reason: "actual_organizations_unavailable" };
    const payload = await organizations.json();
    const organization = payload.items.find(item => item.lifecycle === "active");
    if (!organization) return { status: "blocked", reason: "actual_organization_required" };
    const response = await fetch(`/api/v1/organizations/${encodeURIComponent(organization.organization_id)}/provider-coverage/ollama`);
    if (!response.ok) return { status: "failed", reason: "coverage_endpoint_unavailable", http_status: response.status };
    const view = await response.json();
    const valid = view.organization_id === organization.organization_id && view.provider_key === "ollama"
      && typeof view.registry_revision === "number" && typeof view.as_of === "string"
      && (view.coverage === null || view.coverage.provenance === "owner_asserted")
      && typeof response.headers.get("etag") === "string";
    return { status: valid ? "passed" : "failed", reason: valid ? null : "coverage_response_invalid" };
  });
  console.log(JSON.stringify(result));
  process.exitCode = result.status === "passed" ? 0 : result.status === "blocked" ? 3 : 1;
} catch {
  console.log(JSON.stringify({ status: "blocked", reason: "dashboard_probe_unavailable" }));
  process.exitCode = 3;
} finally {
  if (page) await page.close();
  if (browser) await browser.close();
}
