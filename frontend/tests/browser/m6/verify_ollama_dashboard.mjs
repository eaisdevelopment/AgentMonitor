"use strict";

import { chromium } from "@playwright/test";
import { createHash } from "node:crypto";

const endpoint = "http://127.0.0.1:9225";
const origin = "http://127.0.0.1:43110";
const expectedRevision = process.argv[2];
const results = {
  account_admin: { status: "not_run", reason_code: "signed_in_dashboard_unavailable" },
  cloud_capacity: { status: "not_run", reason_code: "signed_in_dashboard_unavailable" },
  capacity_history: { status: "not_run", reason_code: "signed_in_dashboard_unavailable" },
  process_visibility: { status: "not_run", reason_code: "signed_in_dashboard_unavailable" },
  dashboard_continuity: { status: "not_run", reason_code: "signed_in_dashboard_unavailable" },
};
const facts = {
  confirmed_cloud_targets: 0,
  current_lineage_targets: 0,
  current_balance_lineage_sha256: createHash("sha256").digest("hex"),
  history_lineage_targets: 0,
  current_history_lineage_sha256: createHash("sha256").digest("hex"),
};

function setResult(name, status, reasonCode) {
  results[name] = { status, reason_code: reasonCode };
}

let verificationPage;
async function finish() {
  if (verificationPage !== undefined) await verificationPage.close().catch(() => {});
  console.log(JSON.stringify({
    schema_version: "1.0.0",
    record_type: "agentmonitor.m6_ollama_dashboard_check.v1",
    results,
    facts,
  }));
  const statuses = Object.values(results).map(result => result.status);
  process.exit(statuses.includes("failed") ? 1 : statuses.every(status => status === "passed") ? 0 : 3);
}

function exactMetricValue(field) {
  if (field?.availability !== "available" || field?.value === null || field?.value === undefined) {
    return field?.reason_code ?? String(field?.availability ?? "unknown").replaceAll("_", " ");
  }
  const { coefficient, scale, unit } = field.value;
  if (scale === 0) return `${coefficient} ${unit}`;
  return scale > 0
    ? `${coefficient} × 10^-${scale} ${unit}`
    : `${coefficient} × 10^${Math.abs(scale)} ${unit}`;
}

function boundedPage(payload) {
  return Array.isArray(payload?.items)
    && typeof payload?.page?.has_more === "boolean";
}

function lineageDigest(rows) {
  const digest = createHash("sha256");
  for (const row of [...new Set(rows.map(item => item.join("\0")))].sort()) {
    digest.update(row, "utf8");
    digest.update("\n", "ascii");
  }
  return digest.digest("hex");
}

async function reconcileQuotaDom(page, accountId, quotas) {
  if (!boundedPage(quotas) || quotas.page.has_more || quotas.items.length < 1) return false;
  const table = page.getByRole("region", { name: "Quota windows table", exact: true });
  if (!await table.isVisible()) return false;
  const quotaRows = await table.locator("tbody tr").evaluateAll(rows => rows.map(row => ({
    key: row.dataset.windowKey ?? "",
    role: row.dataset.semanticRole ?? "",
    observation: row.querySelector(".quota-observation-id")?.textContent?.trim() ?? "",
    text: row.textContent ?? "",
  })));
  if (quotaRows.length !== quotas.items.length) return false;
  const nativeKeys = new Set();
  for (const item of quotas.items) {
    if (item?.subject?.provider_key !== "ollama"
        || item?.subject?.provider_target_kind !== "cloud_service"
        || item?.subject?.account_id !== accountId
        || item?.freshness !== "fresh"
        || item?.provenance?.source_id !== "ollama.cloud.balance.v1"
        || typeof item?.observed_at !== "string") return false;
    const nativeKey = `${item.window_key}\u0000${item.semantic_role ?? "unknown"}`;
    if (nativeKeys.has(nativeKey)) return false;
    nativeKeys.add(nativeKey);
    const row = quotaRows.find(candidate => candidate.key === item.window_key
      && candidate.role === (item.semantic_role ?? "unknown")
      && candidate.observation === item.current_observation_id);
    if (row === undefined
        || !row.text.includes(new Date(item.observed_at).toLocaleString())
        || ![item.used, item.remaining, item.limit, item.remaining_ratio]
          .every(field => row.text.includes(exactMetricValue(field)))) return false;
  }
  return true;
}

async function reconcileHistoryDom(page, accountId, history) {
  if (!boundedPage(history) || history.items.length < 2) return false;
  if (!await page.getByRole("table", { name: "Capacity history exact values", exact: true }).isVisible()) return false;
  const historyRows = await page.locator('table[aria-label="Capacity history exact values"] tbody tr').evaluateAll(rows => rows.map(row => ({
    key: row.dataset.windowKey ?? "",
    role: row.dataset.semanticRole ?? "",
    observation: row.querySelector(".history-observation-id")?.textContent?.trim() ?? "",
    text: row.textContent ?? "",
  })));
  if (historyRows.length !== history.items.length) return false;
  const observationIds = new Set();
  const collectionRunIds = new Set();
  for (const item of history.items) {
    if (item?.subject?.provider_key !== "ollama"
        || item?.subject?.provider_target_kind !== "cloud_service"
        || item?.subject?.account_id !== accountId
        || item?.provenance?.source_id !== "ollama.cloud.balance.v1"
        || item?.series_kind !== "poll_snapshot"
        || observationIds.has(item.observation_id)) return false;
    observationIds.add(item.observation_id);
    collectionRunIds.add(item.collection_run_id);
    const row = historyRows.find(candidate => candidate.key === item.window_key
      && candidate.role === item.semantic_role
      && candidate.observation === item.observation_id);
    if (row === undefined
        || !row.text.includes(new Date(item.observed_at).toLocaleString())
        || !row.text.includes(exactMetricValue(item.value))) return false;
  }
  return collectionRunIds.size >= 2;
}

function quotaLineageRows(accountId, quotas) {
  return quotas.items.map(item => [
    accountId,
    item.subject.resource_id,
    item.subject.provider_target_id,
    item.window_id,
    item.current_observation_id,
    item.collection_run_id,
  ]);
}

function currentHistoryLineageRows(accountId, quotas, history) {
  const rows = [];
  for (const quota of quotas.items) {
    const matches = history.items.filter(item => item.window_id === quota.window_id
      && item.observation_id === quota.current_observation_id
      && item.collection_run_id === quota.collection_run_id);
    if (matches.length === 1) {
      rows.push([
        accountId,
        quota.subject.resource_id,
        quota.subject.provider_target_id,
        quota.window_id,
        quota.current_observation_id,
        quota.collection_run_id,
      ]);
    }
  }
  return rows;
}

async function openAccountWithCapacityResponses(page, card) {
  const observed = [];
  const onResponse = response => {
    try {
      const url = new URL(response.url());
      if (url.origin === origin && response.request().method() === "GET"
          && (/^\/api\/v1\/accounts\/[^/]+\/quotas\/v2$/.test(url.pathname)
            || url.pathname === "/api/v1/capacity/history/v2")) observed.push(response);
    } catch { /* A non-URL response cannot be capacity evidence. */ }
  };
  page.on("response", onResponse);
  try {
    await card.getByRole("button", { name: "Open account" }).click();
    await page.getByRole("region", { name: "Ollama cloud connection" }).waitFor();
    await page.getByText("Reading account capacity…", { exact: true }).waitFor({ state: "detached" });
    // Positive readiness avoids accepting an absent loading label before mount.
    await page.locator(".usage-allowance").waitFor({ state: "visible" });
    for (const selector of ["details.quota-technical", "details.quota-history"]) {
      const details = page.locator(selector);
      if (!await details.evaluate(element => element.open)) await details.locator("summary").click();
    }
  } finally {
    page.off("response", onResponse);
  }
  const match = new URL(page.url()).pathname.match(/^\/accounts\/([^/]+)$/);
  if (match === null) return null;
  const accountId = decodeURIComponent(match[1]);
  const quotaResponse = [...observed].reverse().find(response => {
    const url = new URL(response.url());
    return url.pathname === `/api/v1/accounts/${encodeURIComponent(accountId)}/quotas/v2`;
  });
  const historyResponse = [...observed].reverse().find(response => {
    const url = new URL(response.url());
    return url.pathname === "/api/v1/capacity/history/v2"
      && url.searchParams.get("subject_id") === accountId;
  });
  let quotas = null;
  let history = null;
  try {
    if (quotaResponse?.status() === 200) quotas = await quotaResponse.json();
    if (historyResponse?.status() === 200) history = await historyResponse.json();
  } catch { return null; }
  return { accountId, quotas, history };
}

async function exactRunningRevision(page) {
  const response = await page.request.get(`${origin}/api/v1/operations/versions`, {
    headers: { Origin: origin }, failOnStatusCode: false,
  });
  if (!response.ok()) return { status: "blocked", reason_code: "dashboard_revision_unavailable" };
  let payload;
  try { payload = await response.json(); } catch {
    return { status: "failed", reason_code: "dashboard_revision_invalid" };
  }
  if (payload?.source_revision?.availability !== "available") {
    return { status: "blocked", reason_code: "dashboard_revision_unavailable" };
  }
  if (payload?.source_revision?.source !== "build_manifest"
      || payload?.source_revision?.value !== expectedRevision) {
    return { status: "failed", reason_code: "dashboard_revision_mismatch" };
  }
  return { status: "passed", reason_code: null };
}

async function registryDigest(page) {
  const documents = [];
  for (const path of ["/api/v1/accounts?limit=200", "/api/v1/organizations?limit=200"]) {
    const response = await page.request.get(origin + path, {
      headers: { Origin: origin }, failOnStatusCode: false,
    });
    if (!response.ok()) throw new Error("registry_snapshot_unavailable");
    const payload = await response.json();
    if (!Array.isArray(payload?.items) || payload?.page?.has_more === true) {
      throw new Error("registry_snapshot_incomplete");
    }
    documents.push(payload.items);
  }
  return createHash("sha256").update(JSON.stringify(documents)).digest("hex");
}

async function dashboardContinuity(page) {
  const promotion = page.getByRole("region", { name: "Discover the Essential AI product family" });
  if (!await promotion.isVisible().catch(() => false)) return false;
  const expectedLinks = new Set([
    "https://cogent.tools/", "https://all2wiki.com/", "https://clonedetector.com/",
    "https://marvinpda.com/", "https://klaire.pro/", "https://megaprompting.com/",
    "https://github.com/eaisdevelopment/jevmcp",
    "https://github.com/eaisdevelopment/skills",
    "https://github.com/eaisdevelopment/mcp-multi-edit",
  ]);
  const observedLinks = new Set();
  for (let index = 0; index < expectedLinks.size; index += 1) {
    const href = await promotion.locator("a").getAttribute("href");
    if (href === null) return false;
    observedLinks.add(href);
    await promotion.getByRole("button", { name: "Next product" }).click();
  }
  if (observedLinks.size !== expectedLinks.size
      || [...observedLinks].some(link => !expectedLinks.has(link))) return false;
  await page.emulateMedia({ reducedMotion: "reduce" });
  if (!await page.evaluate(() => matchMedia("(prefers-reduced-motion: reduce)").matches)) return false;
  const viewports = [
    [1920, 1080], [1440, 900], [1280, 720],
    [1024, 768], [768, 1024], [390, 844],
  ];
  for (const [width, height] of viewports) {
    await page.setViewportSize({ width, height });
    if (await page.evaluate(() => document.documentElement.scrollWidth > innerWidth + 1)) return false;
    const accounts = page.getByRole("button", { name: "Accounts", exact: true });
    await accounts.focus();
    if (!await accounts.evaluate(element => document.activeElement === element)) return false;
    if (width === 390) {
      const checkSession = page.getByRole("button", { name: "Check session" });
      const signOut = page.getByRole("button", { name: "Sign out" });
      if (!await checkSession.isVisible().catch(() => false)
          || !await signOut.isVisible().catch(() => false)) return false;
      await checkSession.focus();
      await page.keyboard.press("Tab");
      if (!await signOut.evaluate(element => document.activeElement === element)) return false;
    }
  }
  return true;
}

let signedIn = false;
try {
  if (!/^[0-9a-f]{40}$/.test(expectedRevision ?? "")) await finish();
  const browser = await chromium.connectOverCDP(endpoint);
  const pages = browser.contexts().flatMap(context => context.pages());
  const sharedPage = pages.find(candidate => {
    try { return new URL(candidate.url()).origin === origin; } catch { return false; }
  });
  if (sharedPage === undefined) await finish();
  // The application name is branding, not an authenticated-page heading.
  if (!await sharedPage.getByRole("button", { name: "Sign out", exact: true }).isVisible().catch(() => false)) await finish();
  signedIn = true;
  verificationPage = await sharedPage.context().newPage();
  const page = verificationPage;
  let mutationRequests = 0;
  page.on("request", request => {
    try {
      if (new URL(request.url()).origin === origin && !["GET", "HEAD"].includes(request.method())) {
        mutationRequests += 1;
      }
    } catch { /* A non-URL browser request cannot satisfy the same-origin mutation check. */ }
  });
  await page.goto(origin + "/");
  const revisionResult = await exactRunningRevision(page);
  if (revisionResult.status !== "passed") {
    for (const name of Object.keys(results)) setResult(name, revisionResult.status, revisionResult.reason_code);
    await finish();
  }
  const registryBefore = await registryDigest(page);

  const continuity = await dashboardContinuity(page);
  setResult("dashboard_continuity", continuity ? "passed" : "failed", continuity ? null : "dashboard_continuity_unavailable");

  await page.getByRole("button", { name: "Accounts", exact: true }).click();
  await page.getByRole("heading", { name: "Accounts", exact: true }).waitFor();
  const providerInput = page.getByLabel("Provider", { exact: true });
  const accountFormVisible = await providerInput.waitFor({ state: "visible", timeout: 15_000 }).then(() => true, () => false);
  if (!accountFormVisible
      || !await page.locator('datalist#provider-options option[value="ollama"]').count()) {
    setResult("account_admin", "failed", "ollama_account_form_unavailable");
    setResult("cloud_capacity", "failed", "ollama_account_form_unavailable");
    setResult("capacity_history", "failed", "ollama_account_form_unavailable");
    await finish();
  }

  const cards = page.locator("article.record-card").filter({
    has: page.locator("p", { hasText: /^ollama ·/ }),
  });
  const count = await cards.count();
  if (count < 1) {
    setResult("account_admin", "passed", null);
    setResult("cloud_capacity", "not_run", "real_ollama_accounts_unavailable");
    setResult("capacity_history", "not_run", "real_ollama_accounts_unavailable");
  } else {
    await cards.first().getByRole("button", { name: "Open account" }).click();
    const settings = page.locator("details.account-settings");
    if (!await settings.evaluate(element => element.open).catch(() => false)) await settings.locator("summary").click();
    const admin = await page.getByRole("button", { name: "Edit account" }).isVisible().catch(() => false)
      && await page.getByRole("button", { name: "Archive account" }).isVisible().catch(() => false);
    setResult("account_admin", admin ? "passed" : "failed", admin ? null : "ollama_account_controls_unavailable");
    await page.getByRole("link", { name: "Accounts", exact: true }).click();
    await page.getByRole("heading", { name: "Accounts", exact: true }).waitFor();

    const currentLineage = [];
    const currentHistoryLineage = [];
    let currentMismatch = false;
    let currentUnavailable = false;
    let historyMismatch = false;
    let historyUnavailable = false;
    for (let index = 0; index < count; index += 1) {
      const captured = await openAccountWithCapacityResponses(page, cards.nth(index));
      const confirmed = await page.getByRole("heading", { name: "Ollama cloud access confirmed", exact: true }).isVisible().catch(() => false);
      const monitoring = await page.getByText(/^(Monitoring scheduled|Reading now)$/).isVisible().catch(() => false);
      if (confirmed && monitoring) {
        facts.confirmed_cloud_targets += 1;
        if (captured === null || !boundedPage(captured.quotas)
            || captured.quotas.items.length < 1) {
          currentUnavailable = true;
          historyUnavailable = true;
        } else if (!await reconcileQuotaDom(page, captured.accountId, captured.quotas)) {
          currentMismatch = true;
          historyUnavailable = true;
        } else {
          facts.current_lineage_targets += 1;
          currentLineage.push(...quotaLineageRows(captured.accountId, captured.quotas));
          if (captured.history === null || !boundedPage(captured.history)
              || captured.history.items.length < 2) {
            historyUnavailable = true;
          } else if (!await reconcileHistoryDom(
            page, captured.accountId, captured.history,
          )) {
            historyMismatch = true;
          } else {
            const lineage = currentHistoryLineageRows(
              captured.accountId, captured.quotas, captured.history,
            );
            if (lineage.length < 1) {
              historyMismatch = true;
            } else {
              facts.history_lineage_targets += 1;
              currentHistoryLineage.push(...lineage);
            }
          }
        }
      }
      await page.getByRole("link", { name: "Accounts", exact: true }).click();
      await page.getByRole("heading", { name: "Accounts", exact: true }).waitFor();
    }
    facts.current_balance_lineage_sha256 = lineageDigest(currentLineage);
    facts.current_history_lineage_sha256 = lineageDigest(currentHistoryLineage);
    if (currentMismatch) {
      setResult("cloud_capacity", "failed", "ollama_dashboard_lineage_mismatch");
    } else if (facts.confirmed_cloud_targets === 0 || currentUnavailable
        || facts.current_lineage_targets !== facts.confirmed_cloud_targets) {
      setResult("cloud_capacity", "not_run", "real_ollama_balance_unavailable");
    } else {
      setResult("cloud_capacity", "passed", null);
    }
    if (historyMismatch) {
      setResult("capacity_history", "failed", "ollama_history_lineage_mismatch");
    } else if (facts.confirmed_cloud_targets === 0 || historyUnavailable
        || facts.history_lineage_targets !== facts.confirmed_cloud_targets) {
      setResult("capacity_history", "not_run", "real_ollama_history_unavailable");
    } else {
      setResult("capacity_history", "passed", null);
    }
  }

  let processStage = "transport";
  try {
    const processResponse = page.waitForResponse(response => {
      const url = new URL(response.url());
      return url.origin === origin && url.pathname === "/api/v1/process-metrics" && response.request().method() === "GET";
    }, { timeout: 15_000 });
    await page.getByRole("button", { name: "Sessions", exact: true }).click();
    const response = await processResponse;
    if (!response.ok()) {
      setResult("process_visibility", "not_run", "real_ollama_process_unavailable");
    } else {
      processStage = "payload";
      const payload = await response.json();
      if (!boundedPage(payload)) throw new Error("process_page_invalid");
      processStage = "transport";
      const filteredResponse = await page.request.get(
        `${origin}/api/v1/process-metrics?provider_key=ollama&limit=200`,
        { headers: { Origin: origin } },
      );
      if (!filteredResponse.ok()) throw new Error("process_filter_unavailable");
      processStage = "payload";
      const filtered = await filteredResponse.json();
      if (!boundedPage(filtered) || filtered.items.some(item => item.provider_key !== "ollama")) throw new Error("process_filter_invalid");
      const filteredIds = new Set(filtered.items.filter(item => item.presence === "running" && item.provenance?.source_id === "linux.proc.process.v1").map(item => item.process_id));
      const observed = payload.items.filter(item => item.provider_key === "ollama" && item.presence === "running" && item.provenance?.source_id === "linux.proc.process.v1" && filteredIds.has(item.process_id));
      const table = page.getByRole("region", { name: "Process observations table" });
      if (observed.length === 0) {
        setResult("process_visibility", "not_run", payload.page.has_more
          ? "ollama_process_not_in_displayed_page" : "real_ollama_process_unavailable");
      } else {
        processStage = "dom";
        const visible = await table.waitFor({ state: "visible", timeout: 15_000 }).then(() => true, () => false);
        if (!visible) {
          setResult("process_visibility", "failed", "ollama_process_ui_missing");
        } else {
          const rows = table.locator('tbody tr[data-process-row="true"]').filter({
            has: page.getByRole("rowheader", { name: "ollama", exact: true }),
          });
          const expectedIds = new Set(observed.map(item => item.process_id));
          let foundRow = false;
          let foundLabels = false;
          for (const row of await rows.all()) {
            const processId = await row.getAttribute("data-process-id");
            if (!expectedIds.has(processId)) continue;
            foundRow = true;
            const account = await row.getByText("Account unresolved", { exact: true }).isVisible();
            const model = await row.getByText("Model unresolved", { exact: true }).isVisible();
            if (account && model) foundLabels = true;
          }
          if (!foundRow) setResult("process_visibility", "failed", "ollama_process_ui_missing");
          else if (!foundLabels) setResult("process_visibility", "failed", "ollama_process_relationship_state_missing");
          else setResult("process_visibility", "passed", null);
        }
      }
    }
  } catch {
    if (processStage === "transport") setResult("process_visibility", "not_run", "ollama_process_evidence_unavailable");
    else if (processStage === "payload") setResult("process_visibility", "failed", "ollama_process_response_invalid");
    else setResult("process_visibility", "failed", "ollama_process_ui_evaluation_failed");
  }
  if (mutationRequests !== 0) {
    for (const name of Object.keys(results)) setResult(name, "failed", "dashboard_mutation_request_observed");
  } else if (await registryDigest(page) !== registryBefore) {
    for (const name of Object.keys(results)) setResult(name, "blocked", "dashboard_registry_changed_concurrently");
  }
  await finish();
} catch {
  if (signedIn) {
    for (const name of Object.keys(results)) {
      if (results[name].status !== "passed") setResult(name, "failed", "dashboard_verification_failed");
    }
  }
  await finish();
}
