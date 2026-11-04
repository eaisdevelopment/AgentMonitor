"use strict";

import { chromium } from "@playwright/test";

// Read-only API and rendered-page observations. No provider retry or setup action.
const [revision, accountId, phase, runId] = process.argv.slice(2);
const origin = "http://127.0.0.1:43110";
let browser;
let page;
let status = "blocked";

function requireEvidence(value) {
  if (!value) throw new Error("recovery_evidence_missing");
}

function metricText(field) {
  if (field?.availability !== "available" || field.value == null) {
    return field?.reason_code ?? String(field?.availability ?? "unknown").replaceAll("_", " ");
  }
  const { coefficient, scale, unit } = field.value;
  return scale === 0 ? `${coefficient} ${unit}`
    : `${coefficient} × 10^${scale > 0 ? "-" : ""}${Math.abs(scale)} ${unit}`;
}

try {
  requireEvidence(/^[a-f0-9]{40}$/.test(revision ?? "")
    && /^[A-Za-z0-9_-]{1,256}$/.test(accountId ?? "")
    && /^[A-Za-z0-9_-]{1,256}$/.test(runId ?? "")
    && ["failed", "recovered"].includes(phase));
  browser = await chromium.connectOverCDP("http://127.0.0.1:9225", { timeout: 5000 });
  const context = browser.contexts()[0];
  requireEvidence(context !== undefined);
  page = await context.newPage();
  page.setDefaultTimeout(5000);
  const responses = [];
  page.on("response", response => {
    const url = new URL(response.url());
    if (url.origin === origin && response.request().method() === "GET"
        && ["quotas/v2", "ollama-cloud-connection"].some(suffix =>
          url.pathname === `/api/v1/accounts/${accountId}/${suffix}`)) responses.push(response);
  });
  const navigation = await page.goto(`${origin}/accounts/${accountId}`, {
    waitUntil: "domcontentloaded", timeout: 10000,
  });
  requireEvidence(navigation?.status() === 200);
  await page.getByRole("button", { name: "Sign out", exact: true }).waitFor();
  const connection = page.getByRole("region", { name: "Ollama cloud connection", exact: true });
  await connection.waitFor();
  await page.locator(".usage-allowance .allowance-card").first().waitFor();
  const details = page.locator("details.quota-technical");
  if (!await details.evaluate(element => element.open)) await details.locator("summary").click();
  const table = page.getByRole("region", { name: "Quota windows table", exact: true });
  await table.waitFor();

  const read = async path => {
    const response = await page.request.get(`${origin}${path}`, {
      headers: { Origin: origin }, timeout: 5000, failOnStatusCode: false,
    });
    requireEvidence(response.status() === 200);
    return response.json();
  };
  const versions = await read("/api/v1/operations/versions");
  requireEvidence(versions?.source_revision?.availability === "available"
    && versions.source_revision.source === "build_manifest"
    && versions.source_revision.value === revision);

  // Capture the very responses that supplied the rendered account page.
  const captured = async suffix => {
    const response = [...responses].reverse().find(item =>
      new URL(item.url()).pathname.endsWith(`/${suffix}`));
    requireEvidence(response?.status() === 200);
    return response.json();
  };
  const cloud = await captured("ollama-cloud-connection");
  const quotas = await captured("quotas/v2");
  const runs = await read(`/api/v1/collection-runs?provider_key=ollama&account_id=${accountId}&limit=200`);
  const run = runs.items?.find(item => item.run_id === runId);
  status = "failed";
  requireEvidence(run?.account_id === accountId && run.provider_key === "ollama"
    && run.source_id === "ollama.cloud.balance.v1" && run.completed_at !== null
    && cloud.account_id === accountId && Array.isArray(quotas.items)
    && quotas.items.length > 0 && quotas.page?.has_more === false);
  // Source observation precedes its durable collection commit.
  requireEvidence(Date.parse(cloud.observed_at) >= Date.parse(run.requested_at)
    && Date.parse(cloud.observed_at) <= Date.parse(run.completed_at));
  if (phase === "failed") {
    requireEvidence(run.state === "failed" && run.observation_ids.length === 0
      && cloud.state === "retry_available");
    await connection.getByRole("heading", { name: "Last connection check failed", exact: true }).waitFor();
    requireEvidence(quotas.items.every(item => item.collection_run_id !== runId));
  } else {
    requireEvidence(["succeeded", "partial"].includes(run.state)
      && run.observation_ids.length > 0 && cloud.state === "access_valid_owner_confirmed");
    await connection.getByRole("heading", { name: "Ollama cloud access confirmed", exact: true }).waitFor();
    requireEvidence(quotas.items.every(item => item.collection_run_id === runId
      && item.freshness === "fresh" && run.observation_ids.includes(item.current_observation_id)));
  }
  const rendered = await table.locator("tbody tr").evaluateAll(rows => rows.map(row => ({
    observation: row.querySelector(".quota-observation-id")?.textContent?.trim(),
    run: row.querySelector(".quota-collection-run-id")?.textContent?.trim(),
    text: row.textContent ?? "",
  })));
  requireEvidence(rendered.length === quotas.items.length);
  for (const item of quotas.items) {
    const row = rendered.find(candidate => candidate.observation === item.current_observation_id);
    requireEvidence(item.subject?.provider_key === "ollama" && item.subject?.account_id === accountId
      && item.provenance?.source_id === "ollama.cloud.balance.v1"
      && row?.run === item.collection_run_id
      && [item.used, item.remaining, item.limit, item.remaining_ratio]
        .every(field => row.text.includes(metricText(field))));
  }
  status = "passed";
} catch {
  // Never emit page contents, account labels, browser state or credentials.
} finally {
  if (page !== undefined) await page.close().catch(() => {});
  if (browser !== undefined) await browser.close().catch(() => {});
}
console.log(JSON.stringify({
  record_type: "agentmonitor.m6_controlled_recovery_dashboard_probe.v1",
  status, source_revision: revision, observed_at: new Date().toISOString(),
}));
process.exitCode = status === "passed" ? 0 : status === "failed" ? 1 : 3;
